"""Email tool for sending emails via SMTP.

This module provides the EmailTool for sending plain-text and HTML emails
through any SMTP server, using Python's built-in smtplib.
"""

import asyncio
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.types import ToolType


class EmailTool(BaseTool):
    """Tool for sending emails via SMTP.

    Supports plain-text and HTML emails, multiple recipients, CC, and
    both STARTTLS and SSL connections.

    Example:
        >>> tool = EmailTool(
        ...     smtp_host="smtp.gmail.com",
        ...     smtp_port=587,
        ...     username="user@gmail.com",
        ...     password="app-password",
        ...     default_from="user@gmail.com",
        ... )
        >>> context = ToolCallContext(
        ...     correlation_id="corr-1",
        ...     task_id="task-1",
        ...     agent_id="agent-1",
        ... )
        >>> result = await tool.execute(
        ...     context=context,
        ...     arguments={
        ...         "to": "recipient@example.com",
        ...         "subject": "Hello",
        ...         "body": "Hello from OmniForge!",
        ...     },
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        default_from: Optional[str] = None,
        use_tls: bool = True,
        timeout_ms: int = 30000,
    ) -> None:
        """Initialize EmailTool.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (default: 587 for STARTTLS)
            username: SMTP authentication username
            password: SMTP authentication password
            default_from: Default sender address (used when from_email not provided)
            use_tls: Whether to use STARTTLS (default: True). Set to False for
                     plain connections or when using port 465 (SSL).
            timeout_ms: Connection timeout in milliseconds
        """
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._default_from = default_from or username
        self._use_tls = use_tls
        self._timeout_ms = timeout_ms

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="send_email",
            type=ToolType.OTHER,
            description="Send an email via SMTP. Supports plain-text and HTML bodies.",
            parameters=[
                ToolParameter(
                    name="to",
                    type=ParameterType.STRING,
                    description="Recipient email address(es). Multiple addresses separated by commas.",
                    required=True,
                ),
                ToolParameter(
                    name="subject",
                    type=ParameterType.STRING,
                    description="Email subject line.",
                    required=True,
                ),
                ToolParameter(
                    name="body",
                    type=ParameterType.STRING,
                    description="Plain-text email body.",
                    required=True,
                ),
                ToolParameter(
                    name="from_email",
                    type=ParameterType.STRING,
                    description="Sender email address. Defaults to the configured default_from.",
                    required=False,
                ),
                ToolParameter(
                    name="cc",
                    type=ParameterType.STRING,
                    description="CC recipient email address(es). Multiple addresses separated by commas.",
                    required=False,
                ),
                ToolParameter(
                    name="html_body",
                    type=ParameterType.STRING,
                    description="HTML email body. When provided, a multipart email is sent with both "
                    "plain-text and HTML parts.",
                    required=False,
                ),
            ],
            timeout_ms=self._timeout_ms,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Send an email.

        Args:
            context: Execution context
            arguments: Email arguments (to, subject, body, from_email, cc, html_body)

        Returns:
            ToolResult indicating success or failure
        """
        start_time = time.time()

        to_raw = arguments.get("to", "").strip()
        subject = arguments.get("subject", "").strip()
        body = arguments.get("body", "").strip()
        from_email = arguments.get("from_email", "").strip() or self._default_from
        cc_raw = arguments.get("cc", "").strip()
        html_body = arguments.get("html_body", "").strip()

        if not to_raw:
            return ToolResult(
                success=False,
                error="'to' parameter is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )
        if not subject:
            return ToolResult(
                success=False,
                error="'subject' parameter is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )
        if not body:
            return ToolResult(
                success=False,
                error="'body' parameter is required",
                duration_ms=int((time.time() - start_time) * 1000),
            )
        if not from_email:
            return ToolResult(
                success=False,
                error="No sender address: provide 'from_email' or configure default_from",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        to_list = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
        cc_list = [addr.strip() for addr in cc_raw.split(",") if addr.strip()] if cc_raw else []

        msg = self._build_message(
            from_email=from_email,
            to_list=to_list,
            cc_list=cc_list,
            subject=subject,
            body=body,
            html_body=html_body or None,
        )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_smtp,
                msg,
                from_email,
                to_list + cc_list,
            )

            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=True,
                result={
                    "from": from_email,
                    "to": to_list,
                    "cc": cc_list,
                    "subject": subject,
                    "has_html": bool(html_body),
                },
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Failed to send email: {exc}",
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_message(
        self,
        from_email: str,
        to_list: list[str],
        cc_list: list[str],
        subject: str,
        body: str,
        html_body: Optional[str],
    ) -> MIMEMultipart:
        """Construct the MIME email message."""
        msg = MIMEMultipart("alternative") if html_body else MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        return msg

    def _send_smtp(
        self,
        msg: MIMEMultipart,
        from_email: str,
        recipients: list[str],
    ) -> None:
        """Send the message over SMTP (blocking — run in executor)."""
        timeout_seconds = self._timeout_ms / 1000

        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=timeout_seconds) as server:
            if self._use_tls:
                server.starttls()
            if self._username and self._password:
                server.login(self._username, self._password)
            server.sendmail(from_email, recipients, msg.as_string())
