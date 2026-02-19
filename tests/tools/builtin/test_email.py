"""Tests for EmailTool."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from omniforge.tools.base import ToolCallContext
from omniforge.tools.builtin.email import EmailTool
from omniforge.tools.types import ToolType


@pytest.fixture
def tool() -> EmailTool:
    return EmailTool(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="user@example.com",
        password="secret",
        default_from="user@example.com",
    )


@pytest.fixture
def context() -> ToolCallContext:
    return ToolCallContext(
        correlation_id="corr-1",
        task_id="task-1",
        agent_id="agent-1",
    )


# ---------------------------------------------------------------------------
# Definition
# ---------------------------------------------------------------------------


def test_definition_name(tool):
    assert tool.definition.name == "send_email"


def test_definition_type(tool):
    assert tool.definition.type == ToolType.OTHER


def test_definition_required_params(tool):
    required = {p.name for p in tool.definition.parameters if p.required}
    assert required == {"to", "subject", "body"}


def test_definition_optional_params(tool):
    optional = {p.name for p in tool.definition.parameters if not p.required}
    assert optional == {"from_email", "cc", "html_body"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_to_returns_error(tool, context):
    result = await tool.execute(context=context, arguments={"subject": "Hi", "body": "Hello"})
    assert result.success is False
    assert "'to'" in result.error


@pytest.mark.asyncio
async def test_missing_subject_returns_error(tool, context):
    result = await tool.execute(
        context=context, arguments={"to": "a@b.com", "body": "Hello"}
    )
    assert result.success is False
    assert "'subject'" in result.error


@pytest.mark.asyncio
async def test_missing_body_returns_error(tool, context):
    result = await tool.execute(
        context=context, arguments={"to": "a@b.com", "subject": "Hi"}
    )
    assert result.success is False
    assert "'body'" in result.error


@pytest.mark.asyncio
async def test_no_sender_returns_error(context):
    tool_no_from = EmailTool(smtp_host="smtp.example.com", default_from=None)
    result = await tool_no_from.execute(
        context=context,
        arguments={"to": "a@b.com", "subject": "Hi", "body": "Hello"},
    )
    assert result.success is False
    assert "sender" in result.error.lower() or "from_email" in result.error


# ---------------------------------------------------------------------------
# Successful send (plain text)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_plain_text_email(tool, context):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = await tool.execute(
            context=context,
            arguments={
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "body": "Test body",
            },
        )

    assert result.success is True
    assert result.result["to"] == ["recipient@example.com"]
    assert result.result["subject"] == "Test Subject"
    assert result.result["has_html"] is False
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user@example.com", "secret")
    mock_smtp.sendmail.assert_called_once()


# ---------------------------------------------------------------------------
# HTML email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_html_email(tool, context):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = await tool.execute(
            context=context,
            arguments={
                "to": "recipient@example.com",
                "subject": "HTML Email",
                "body": "Fallback plain text",
                "html_body": "<h1>Hello</h1>",
            },
        )

    assert result.success is True
    assert result.result["has_html"] is True


# ---------------------------------------------------------------------------
# Multiple recipients and CC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_recipients_and_cc(tool, context):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = await tool.execute(
            context=context,
            arguments={
                "to": "a@example.com, b@example.com",
                "subject": "Group email",
                "body": "Hello everyone",
                "cc": "c@example.com",
            },
        )

    assert result.success is True
    assert result.result["to"] == ["a@example.com", "b@example.com"]
    assert result.result["cc"] == ["c@example.com"]

    # All three addresses should be in the sendmail recipients list
    _, call_args, _ = mock_smtp.sendmail.mock_calls[0]
    recipients = call_args[1]
    assert set(recipients) == {"a@example.com", "b@example.com", "c@example.com"}


# ---------------------------------------------------------------------------
# Custom from_email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_from_email(tool, context):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = await tool.execute(
            context=context,
            arguments={
                "to": "r@example.com",
                "subject": "Hi",
                "body": "Body",
                "from_email": "custom@example.com",
            },
        )

    assert result.success is True
    assert result.result["from"] == "custom@example.com"


# ---------------------------------------------------------------------------
# TLS disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_tls(context):
    tool_no_tls = EmailTool(
        smtp_host="smtp.example.com",
        smtp_port=25,
        username="u",
        password="p",
        default_from="u@example.com",
        use_tls=False,
    )
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = await tool_no_tls.execute(
            context=context,
            arguments={"to": "r@example.com", "subject": "Hi", "body": "Body"},
        )

    assert result.success is True
    mock_smtp.starttls.assert_not_called()


# ---------------------------------------------------------------------------
# SMTP failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_smtp_failure_returns_error(tool, context):
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("Connection refused")):
        result = await tool.execute(
            context=context,
            arguments={"to": "r@example.com", "subject": "Hi", "body": "Body"},
        )

    assert result.success is False
    assert "Failed to send email" in result.error
