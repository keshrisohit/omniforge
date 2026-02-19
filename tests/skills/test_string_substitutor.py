"""Tests for string substitution in skill content.

This module tests the StringSubstitutor class for variable replacement in skill
content before LLM execution.
"""

import logging
import os
import re
from datetime import datetime
from unittest.mock import patch

import pytest

from omniforge.skills.string_substitutor import (
    StringSubstitutor,
    SubstitutedContent,
    SubstitutionContext,
)


class TestSubstitutionContext:
    """Tests for SubstitutionContext dataclass."""

    def test_create_context_with_defaults(self) -> None:
        """Context should initialize with default empty values."""
        context = SubstitutionContext()

        assert context.arguments == ""
        assert context.session_id == ""
        assert context.skill_dir == ""
        assert context.workspace == ""
        assert context.user == ""
        assert context.date == ""
        assert context.custom_vars == {}

    def test_create_context_with_values(self) -> None:
        """Context should store all provided values."""
        context = SubstitutionContext(
            arguments="data.csv",
            session_id="session-20260127-abc123",
            skill_dir="/path/to/skill",
            workspace="/workspace",
            user="testuser",
            date="2026-01-27",
            custom_vars={"CUSTOM": "value"},
        )

        assert context.arguments == "data.csv"
        assert context.session_id == "session-20260127-abc123"
        assert context.skill_dir == "/path/to/skill"
        assert context.workspace == "/workspace"
        assert context.user == "testuser"
        assert context.date == "2026-01-27"
        assert context.custom_vars == {"CUSTOM": "value"}


class TestSubstitutedContent:
    """Tests for SubstitutedContent dataclass."""

    def test_create_substituted_content(self) -> None:
        """SubstitutedContent should store all result data."""
        result = SubstitutedContent(
            content="Processed content",
            substitutions_made=3,
            undefined_vars=["UNDEFINED1", "UNDEFINED2"],
        )

        assert result.content == "Processed content"
        assert result.substitutions_made == 3
        assert result.undefined_vars == ["UNDEFINED1", "UNDEFINED2"]


class TestStringSubstitutorBasics:
    """Tests for basic StringSubstitutor functionality."""

    def test_substitute_arguments_dollar_syntax(self) -> None:
        """Should substitute $ARGUMENTS with provided arguments."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute("Process: $ARGUMENTS", context)

        assert result.content == "Process: data.csv"
        assert result.substitutions_made == 1
        assert result.undefined_vars == []

    def test_substitute_arguments_braces_syntax(self) -> None:
        """Should substitute ${ARGUMENTS} with provided arguments."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute("Process: ${ARGUMENTS}", context)

        assert result.content == "Process: data.csv"
        assert result.substitutions_made == 1
        assert result.undefined_vars == []

    def test_substitute_multiple_variables(self) -> None:
        """Should substitute multiple variables in content."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(
            arguments="data.csv",
            skill_dir="/path/to/skill",
            workspace="/workspace",
            user="testuser",
            date="2026-01-27",
        )

        content = "User: $USER on $DATE processing $ARGUMENTS from ${SKILL_DIR} in ${WORKSPACE}"
        result = substitutor.substitute(content, context)

        expected = (
            "User: testuser on 2026-01-27 processing data.csv from " "/path/to/skill in /workspace"
        )
        assert result.content == expected
        assert result.substitutions_made == 5
        assert result.undefined_vars == []

    def test_substitute_session_id(self) -> None:
        """Should substitute both CLAUDE_SESSION_ID and SESSION_ID."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(session_id="session-20260127-abc123")

        result = substitutor.substitute("Session: ${CLAUDE_SESSION_ID} or $SESSION_ID", context)

        assert result.content == "Session: session-20260127-abc123 or session-20260127-abc123"
        assert result.substitutions_made == 2
        assert result.undefined_vars == []


class TestStringSubstitutorAutoAppend:
    """Tests for auto-append arguments functionality."""

    def test_auto_append_arguments_when_not_present(self) -> None:
        """Should auto-append arguments when not present in content."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="test.txt")

        result = substitutor.substitute("Process file", context, auto_append_arguments=True)

        assert "ARGUMENTS: test.txt" in result.content
        assert result.content.endswith("ARGUMENTS: test.txt")

    def test_no_auto_append_when_arguments_present(self) -> None:
        """Should not auto-append when $ARGUMENTS already in content."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="test.txt")

        result = substitutor.substitute(
            "Process $ARGUMENTS file", context, auto_append_arguments=True
        )

        assert result.content == "Process test.txt file"
        # Should not have appended again
        assert result.content.count("test.txt") == 1

    def test_no_auto_append_when_arguments_braces_present(self) -> None:
        """Should not auto-append when ${ARGUMENTS} already in content."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="test.txt")

        result = substitutor.substitute(
            "Process ${ARGUMENTS} file", context, auto_append_arguments=True
        )

        assert result.content == "Process test.txt file"
        # Should not have appended again
        assert result.content.count("test.txt") == 1

    def test_no_auto_append_when_disabled(self) -> None:
        """Should not auto-append when auto_append_arguments is False."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="test.txt")

        result = substitutor.substitute("Process file", context, auto_append_arguments=False)

        assert "ARGUMENTS" not in result.content
        assert result.content == "Process file"

    def test_no_auto_append_when_no_arguments(self) -> None:
        """Should not auto-append when arguments is empty."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="")

        result = substitutor.substitute("Process file", context, auto_append_arguments=True)

        assert "ARGUMENTS" not in result.content
        assert result.content == "Process file"


class TestStringSubstitutorUndefinedVariables:
    """Tests for handling undefined variables."""

    def test_undefined_variable_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log warning for undefined variables and leave them unchanged."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext()

        with caplog.at_level(logging.WARNING):
            result = substitutor.substitute("Value: ${UNDEFINED_VAR}", context)

        assert result.content == "Value: ${UNDEFINED_VAR}"
        assert result.substitutions_made == 0
        assert "UNDEFINED_VAR" in result.undefined_vars
        assert "Undefined variable 'UNDEFINED_VAR'" in caplog.text

    def test_multiple_undefined_variables(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should track multiple undefined variables."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext()

        with caplog.at_level(logging.WARNING):
            result = substitutor.substitute("${VAR1} and $VAR2 and ${VAR3}", context)

        assert result.content == "${VAR1} and $VAR2 and ${VAR3}"
        assert result.substitutions_made == 0
        assert set(result.undefined_vars) == {"VAR1", "VAR2", "VAR3"}

    def test_mix_defined_and_undefined_variables(self) -> None:
        """Should substitute defined variables and leave undefined ones."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute("Process $ARGUMENTS with ${UNDEFINED}", context)

        assert result.content == "Process data.csv with ${UNDEFINED}"
        assert result.substitutions_made == 1
        assert "UNDEFINED" in result.undefined_vars


class TestStringSubstitutorCustomVariables:
    """Tests for custom variable substitution."""

    def test_substitute_custom_variables(self) -> None:
        """Should substitute custom variables from context."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(custom_vars={"CUSTOM1": "value1", "CUSTOM2": "value2"})

        result = substitutor.substitute("Values: $CUSTOM1 and ${CUSTOM2}", context)

        assert result.content == "Values: value1 and value2"
        assert result.substitutions_made == 2
        assert result.undefined_vars == []

    def test_custom_variables_override_standard(self) -> None:
        """Custom variables should override standard variables if names conflict."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(user="defaultuser", custom_vars={"USER": "customuser"})

        result = substitutor.substitute("User: $USER", context)

        assert result.content == "User: customuser"
        assert result.substitutions_made == 1


class TestStringSubstitutorBuildContext:
    """Tests for build_context method."""

    def test_build_context_with_all_values(self) -> None:
        """Should build context with all provided values."""
        substitutor = StringSubstitutor()

        context = substitutor.build_context(
            arguments="data.csv",
            session_id="session-123",
            skill_dir="/skill",
            workspace="/workspace",
            user="testuser",
            date="2026-01-27",
            custom_vars={"CUSTOM": "value"},
        )

        assert context.arguments == "data.csv"
        assert context.session_id == "session-123"
        assert context.skill_dir == "/skill"
        assert context.workspace == "/workspace"
        assert context.user == "testuser"
        assert context.date == "2026-01-27"
        assert context.custom_vars == {"CUSTOM": "value"}

    def test_build_context_generates_session_id(self) -> None:
        """Should auto-generate session ID if not provided."""
        substitutor = StringSubstitutor()

        context = substitutor.build_context()

        assert context.session_id != ""
        assert context.session_id.startswith("session-")
        # Format: session-YYYYMMDD-xxxxxxxx
        assert re.match(r"^session-\d{8}-[a-f0-9]{8}$", context.session_id)

    def test_build_context_uses_current_directory(self) -> None:
        """Should use current working directory if workspace not provided."""
        substitutor = StringSubstitutor()

        context = substitutor.build_context()

        assert context.workspace == os.getcwd()

    def test_build_context_uses_env_user(self) -> None:
        """Should get user from environment if not provided."""
        substitutor = StringSubstitutor()

        with patch.dict(os.environ, {"USER": "envuser"}):
            context = substitutor.build_context()

        assert context.user == "envuser"

    def test_build_context_uses_unknown_user_if_no_env(self) -> None:
        """Should use 'unknown' if USER not in environment."""
        substitutor = StringSubstitutor()

        with patch.dict(os.environ, {}, clear=True):
            context = substitutor.build_context()

        assert context.user == "unknown"

    def test_build_context_uses_current_date(self) -> None:
        """Should use current date if not provided."""
        substitutor = StringSubstitutor()

        context = substitutor.build_context()

        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert context.date == expected_date

    def test_build_context_with_defaults(self) -> None:
        """Should populate all fields with defaults when nothing provided."""
        substitutor = StringSubstitutor()

        context = substitutor.build_context()

        assert context.arguments == ""
        assert context.session_id != ""  # Auto-generated
        assert context.skill_dir == ""
        assert context.workspace != ""  # Current directory
        assert context.user != ""  # From env or 'unknown'
        assert context.date != ""  # Current date
        assert context.custom_vars == {}


class TestStringSubstitutorSessionIdGeneration:
    """Tests for session ID generation."""

    def test_generate_session_id_format(self) -> None:
        """Session ID should match expected format."""
        substitutor = StringSubstitutor()

        session_id = substitutor._generate_session_id()

        # Format: session-YYYYMMDD-xxxxxxxx (8 hex chars)
        assert re.match(r"^session-\d{8}-[a-f0-9]{8}$", session_id)

    def test_generate_session_id_uniqueness(self) -> None:
        """Each generated session ID should be unique."""
        substitutor = StringSubstitutor()

        session_ids = {substitutor._generate_session_id() for _ in range(100)}

        # All 100 should be unique
        assert len(session_ids) == 100

    def test_generate_session_id_contains_date(self) -> None:
        """Session ID should contain current date."""
        substitutor = StringSubstitutor()

        session_id = substitutor._generate_session_id()
        date_part = datetime.now().strftime("%Y%m%d")

        assert date_part in session_id


class TestStringSubstitutorEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_substitute_empty_content(self) -> None:
        """Should handle empty content gracefully."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute("", context)

        # Auto-append should add arguments
        assert result.content == "\n\nARGUMENTS: data.csv"
        assert result.substitutions_made == 0

    def test_substitute_no_variables(self) -> None:
        """Should handle content with no variables."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute("This is plain text", context, auto_append_arguments=False)

        assert result.content == "This is plain text"
        assert result.substitutions_made == 0
        assert result.undefined_vars == []

    def test_substitute_same_variable_multiple_times(self) -> None:
        """Should substitute same variable appearing multiple times."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(user="testuser")

        result = substitutor.substitute("$USER and $USER and ${USER}", context)

        assert result.content == "testuser and testuser and testuser"
        assert result.substitutions_made == 3

    def test_substitute_with_special_characters_in_values(self) -> None:
        """Should handle special characters in variable values."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(
            arguments="file-name_with.special$chars",
            skill_dir="/path/with spaces/and-dashes",
        )

        result = substitutor.substitute("$ARGUMENTS in ${SKILL_DIR}", context)

        assert result.content == "file-name_with.special$chars in /path/with spaces/and-dashes"
        assert result.substitutions_made == 2

    def test_substitute_lowercase_variable_not_matched(self) -> None:
        """Should not match lowercase variable names."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(custom_vars={"lowercase": "value"})

        result = substitutor.substitute("Value: $lowercase", context)

        # Should not substitute (pattern requires uppercase)
        assert result.content == "Value: $lowercase"
        assert result.substitutions_made == 0

    def test_substitute_variable_with_underscores_and_numbers(self) -> None:
        """Should match variables with underscores and numbers."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(custom_vars={"VAR_123": "value1", "MY_VAR_2": "value2"})

        result = substitutor.substitute("$VAR_123 and ${MY_VAR_2}", context)

        assert result.content == "value1 and value2"
        assert result.substitutions_made == 2

    def test_substitute_preserves_whitespace(self) -> None:
        """Should preserve whitespace and newlines in content."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext(user="testuser")

        content = "Line 1\n  $USER  \n\nLine 3"
        result = substitutor.substitute(content, context, auto_append_arguments=False)

        assert result.content == "Line 1\n  testuser  \n\nLine 3"

    def test_substitute_duplicate_undefined_vars_logged_once(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should only log warning once per unique undefined variable."""
        substitutor = StringSubstitutor()
        context = SubstitutionContext()

        with caplog.at_level(logging.WARNING):
            result = substitutor.substitute("$UNDEF1 $UNDEF1 ${UNDEF1}", context)

        # Variable appears multiple times but should only be in list once
        assert result.undefined_vars.count("UNDEF1") == 1
        # Check that warning appears once (may have multiple log lines but same var)
        warning_count = sum(1 for record in caplog.records if "UNDEF1" in record.message)
        assert warning_count == 1
