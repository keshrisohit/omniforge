"""String substitution for skill content variable replacement.

This module provides the StringSubstitutor class for replacing variables in skill
content before LLM execution. Supports standard variables ($ARGUMENTS, ${SKILL_DIR}, etc.)
and auto-appends arguments if not present in content.
"""

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SubstitutionContext:
    """Context containing variables for substitution.

    Attributes:
        arguments: User-provided arguments
        session_id: Unique session identifier
        skill_dir: Absolute path to skill directory
        workspace: Current working directory
        user: Current user name
        date: Current date in YYYY-MM-DD format
        custom_vars: Additional custom variables for substitution
    """

    arguments: str = ""
    session_id: str = ""
    skill_dir: str = ""
    workspace: str = ""
    user: str = ""
    date: str = ""
    custom_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class SubstitutedContent:
    """Result of string substitution operation.

    Attributes:
        content: Content with variables replaced
        substitutions_made: Count of substitutions performed
        undefined_vars: List of undefined variables found
    """

    content: str
    substitutions_made: int
    undefined_vars: list[str]


class StringSubstitutor:
    """Substitutes variables in skill content before execution.

    Replaces standard variables ($ARGUMENTS, ${CLAUDE_SESSION_ID}, etc.) and custom
    variables in skill content. Auto-appends arguments if not present in content.

    Example:
        >>> substitutor = StringSubstitutor()
        >>> context = SubstitutionContext(arguments="data.csv", skill_dir="/path/to/skill")
        >>> result = substitutor.substitute("Process: $ARGUMENTS from ${SKILL_DIR}", context)
        >>> print(result.content)
        Process: data.csv from /path/to/skill
    """

    # Regex pattern to match both $VAR and ${VAR} syntax
    # Matches: $VARNAME or ${VARNAME} where VARNAME starts with uppercase letter
    VAR_PATTERN = re.compile(r"\$\{?([A-Z][A-Z0-9_]*)\}?")

    def substitute(
        self,
        content: str,
        context: SubstitutionContext,
        auto_append_arguments: bool = True,
    ) -> SubstitutedContent:
        """Substitute variables in content with values from context.

        Args:
            content: Skill content with variables to replace
            context: Context containing variable values
            auto_append_arguments: If True and $ARGUMENTS not in content, append arguments

        Returns:
            SubstitutedContent with replaced content and metadata
        """
        # Build variable map from context
        var_map = self._build_variable_map(context)

        # Track substitutions and undefined variables
        substitutions_made = 0
        undefined_vars: list[str] = []

        def replace_var(match: re.Match[str]) -> str:
            """Replace a single variable match."""
            nonlocal substitutions_made
            var_name = match.group(1)

            if var_name in var_map:
                substitutions_made += 1
                return var_map[var_name]
            else:
                # Log warning for undefined variable
                if var_name not in undefined_vars:
                    undefined_vars.append(var_name)
                    logger.warning(
                        f"Undefined variable '{var_name}' in skill content. "
                        f"Leaving as-is: {match.group(0)}"
                    )
                # Leave undefined variables unchanged
                return match.group(0)

        # Perform substitution
        result_content = self.VAR_PATTERN.sub(replace_var, content)

        # Auto-append arguments if not present
        if auto_append_arguments and context.arguments:
            # Check if ARGUMENTS was in the original content
            has_arguments_var = bool(re.search(r"\$\{?ARGUMENTS\}?", content, re.IGNORECASE))
            if not has_arguments_var:
                # Append arguments at the end
                result_content = result_content.rstrip() + f"\n\nARGUMENTS: {context.arguments}"
                logger.debug(f"Auto-appended ARGUMENTS to skill content: {context.arguments}")

        return SubstitutedContent(
            content=result_content,
            substitutions_made=substitutions_made,
            undefined_vars=undefined_vars,
        )

    def build_context(
        self,
        arguments: str = "",
        session_id: Optional[str] = None,
        skill_dir: str = "",
        workspace: Optional[str] = None,
        user: Optional[str] = None,
        date: Optional[str] = None,
        custom_vars: Optional[dict[str, str]] = None,
    ) -> SubstitutionContext:
        """Build substitution context with defaults for unspecified values.

        Args:
            arguments: User-provided arguments (default: "")
            session_id: Unique session ID (auto-generated if None)
            skill_dir: Absolute path to skill directory (default: "")
            workspace: Working directory (default: current directory)
            user: Current user name (default: from USER env var)
            date: Current date (default: today in YYYY-MM-DD format)
            custom_vars: Additional custom variables (default: {})

        Returns:
            SubstitutionContext with all values populated
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = self._generate_session_id()

        # Use current working directory if workspace not provided
        if workspace is None:
            workspace = os.getcwd()

        # Get user from environment if not provided
        if user is None:
            user = os.environ.get("USER", "unknown")

        # Use current date if not provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Use empty dict if custom_vars not provided
        if custom_vars is None:
            custom_vars = {}

        return SubstitutionContext(
            arguments=arguments,
            session_id=session_id,
            skill_dir=skill_dir,
            workspace=workspace,
            user=user,
            date=date,
            custom_vars=custom_vars,
        )

    def _build_variable_map(self, context: SubstitutionContext) -> dict[str, str]:
        """Build map of variable names to values from context.

        Args:
            context: Substitution context

        Returns:
            Dictionary mapping variable names to their values
        """
        var_map = {
            "ARGUMENTS": context.arguments,
            "CLAUDE_SESSION_ID": context.session_id,
            "SESSION_ID": context.session_id,  # Alias for compatibility
            "SKILL_DIR": context.skill_dir,
            "WORKSPACE": context.workspace,
            "USER": context.user,
            "DATE": context.date,
        }

        # Add custom variables (custom vars override standard vars if names conflict)
        var_map.update(context.custom_vars)

        return var_map

    def _generate_session_id(self) -> str:
        """Generate unique session ID in format: session-{date}-{uuid[:8]}.

        Returns:
            Unique session identifier
        """
        date_str = datetime.now().strftime("%Y%m%d")
        uuid_part = str(uuid.uuid4())[:8]
        return f"session-{date_str}-{uuid_part}"
