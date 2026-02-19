"""Visibility control system for reasoning chains.

This module manages what reasoning chain information is visible to different users
based on roles, tool types, and configuration, enabling simplified views for end-users
while maintaining full detail for developers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from omniforge.agents.cot.chain import ReasoningChain, ReasoningStep, VisibilityConfig
from omniforge.security.rbac import Role
from omniforge.tools.types import ToolType, VisibilityLevel


@dataclass
class VisibilityRule:
    """Rule for determining step visibility.

    Attributes:
        role: User role this rule applies to (None = all roles)
        tool_type: Tool type this rule applies to (None = all tools)
        level: Visibility level to apply
        summary_template: Optional template for generating summaries
    """

    level: VisibilityLevel
    role: Optional[Role] = None
    tool_type: Optional[ToolType] = None
    summary_template: Optional[str] = None


@dataclass
class VisibilityConfiguration:
    """Configuration for visibility control.

    Attributes:
        default_level: Default visibility level when no rules match
        rules_by_tool_type: Tool-specific visibility rules
        rules_by_role: Role-specific visibility rules
        child_chain_visibility: Visibility level for child chains
        sensitive_fields: Field names to redact in non-full views
    """

    default_level: VisibilityLevel = VisibilityLevel.FULL
    rules_by_tool_type: Dict[ToolType, VisibilityLevel] = field(default_factory=dict)
    rules_by_role: Dict[Role, VisibilityLevel] = field(default_factory=dict)
    child_chain_visibility: VisibilityLevel = VisibilityLevel.SUMMARY
    sensitive_fields: List[str] = field(
        default_factory=lambda: ["password", "api_key", "token", "secret"]
    )


class VisibilityController:
    """Controls visibility of reasoning chain information.

    Manages what chain information is visible to users based on their role,
    tool types, and configuration. Supports filtering, redaction, and summarization.

    Resolution order (most specific wins):
    1. Step-level security visibility setting
    2. Role-specific rules
    3. Tool-type-specific rules
    4. Default level

    Example:
        >>> config = VisibilityConfiguration(
        ...     default_level=VisibilityLevel.SUMMARY,
        ...     rules_by_role={Role.END_USER: VisibilityLevel.HIDDEN}
        ... )
        >>> controller = VisibilityController(config)
        >>> filtered = controller.filter_chain(chain, Role.END_USER)
    """

    def __init__(self, config: VisibilityConfiguration):
        """Initialize visibility controller.

        Args:
            config: Visibility configuration
        """
        self.config = config

    def apply_visibility(
        self, step: ReasoningStep, user_role: Optional[Role]
    ) -> ReasoningStep:
        """Apply visibility rules to a step.

        Args:
            step: Reasoning step to filter
            user_role: User's role (None for unauthenticated)

        Returns:
            Modified step with visibility applied
        """
        effective_level = self.get_effective_level(step, user_role)

        # If FULL visibility, return as-is
        if effective_level == VisibilityLevel.FULL:
            return step

        # If HIDDEN, return minimal step
        if effective_level == VisibilityLevel.HIDDEN:
            return self._create_hidden_step(step)

        # SUMMARY level - generate summary
        return self._create_summary_step(step)

    def filter_chain(
        self, chain: ReasoningChain, user_role: Optional[Role]
    ) -> ReasoningChain:
        """Filter a chain based on user role.

        Args:
            chain: Reasoning chain to filter
            user_role: User's role (None for unauthenticated)

        Returns:
            New chain with visibility applied to all steps
        """
        # Create a copy of the chain
        filtered_chain = chain.model_copy(deep=True)

        # Filter each step
        filtered_steps = []
        for step in filtered_chain.steps:
            effective_level = self.get_effective_level(step, user_role)

            # Skip completely hidden steps
            if effective_level == VisibilityLevel.HIDDEN:
                continue

            # Apply visibility to step
            filtered_step = self.apply_visibility(step, user_role)
            filtered_steps.append(filtered_step)

        filtered_chain.steps = filtered_steps
        return filtered_chain

    def get_effective_level(
        self, step: ReasoningStep, user_role: Optional[Role]
    ) -> VisibilityLevel:
        """Get the effective visibility level for a step.

        Resolution order (most specific wins):
        1. Step-level security visibility setting
        2. Role-specific rules
        3. Tool-type-specific rules
        4. Default level

        Args:
            step: Reasoning step
            user_role: User's role

        Returns:
            Effective visibility level
        """
        # 1. Step-level visibility always takes precedence (security)
        if step.visibility.level != VisibilityLevel.FULL:
            return step.visibility.level

        # 2. Role-specific rules
        if user_role and user_role in self.config.rules_by_role:
            return self.config.rules_by_role[user_role]

        # 3. Tool-type-specific rules
        tool_type = self._get_step_tool_type(step)
        if tool_type and tool_type in self.config.rules_by_tool_type:
            return self.config.rules_by_tool_type[tool_type]

        # 4. Default level
        return self.config.default_level

    def _get_step_tool_type(self, step: ReasoningStep) -> Optional[ToolType]:
        """Extract tool type from a step.

        Args:
            step: Reasoning step

        Returns:
            Tool type if step is a tool call, None otherwise
        """
        if step.tool_call:
            return step.tool_call.tool_type
        return None

    def _create_hidden_step(self, step: ReasoningStep) -> ReasoningStep:
        """Create a minimal hidden version of a step.

        Args:
            step: Original step

        Returns:
            Hidden step with minimal information
        """
        hidden_step = step.model_copy(deep=True)

        # Clear sensitive content
        if hidden_step.thinking:
            hidden_step.thinking.content = "[Hidden]"
        if hidden_step.tool_call:
            hidden_step.tool_call.parameters = {}
        if hidden_step.tool_result:
            hidden_step.tool_result.result = None
        if hidden_step.synthesis:
            hidden_step.synthesis.content = "[Hidden]"

        # Update visibility config
        hidden_step.visibility = VisibilityConfig(
            level=VisibilityLevel.HIDDEN,
            reason=hidden_step.visibility.reason or "Hidden by policy",
        )

        return hidden_step

    def _create_summary_step(self, step: ReasoningStep) -> ReasoningStep:
        """Create a summary version of a step.

        Args:
            step: Original step

        Returns:
            Summary step with simplified information
        """
        summary_step = step.model_copy(deep=True)

        # Generate summaries based on step type
        if summary_step.thinking:
            summary_step.thinking.content = generate_summary(
                summary_step, "Performed reasoning step"
            )

        if summary_step.tool_call:
            # Redact sensitive parameters
            summary_step.tool_call.parameters = redact_sensitive_fields(
                summary_step.tool_call.parameters, self.config.sensitive_fields
            )

        if summary_step.tool_result:
            # Redact sensitive result data
            if summary_step.tool_result.result:
                summary_step.tool_result.result = redact_sensitive_fields(
                    summary_step.tool_result.result, self.config.sensitive_fields
                )

        if summary_step.synthesis:
            summary_step.synthesis.content = generate_summary(
                summary_step, "Generated synthesis"
            )

        # Update visibility config
        summary_step.visibility = VisibilityConfig(
            level=VisibilityLevel.SUMMARY,
            reason=summary_step.visibility.reason or "Summarized for user",
        )

        return summary_step


def redact_sensitive_fields(data: dict, sensitive_fields: List[str]) -> dict:
    """Redact sensitive fields from a dictionary.

    Args:
        data: Dictionary to redact
        sensitive_fields: List of field names to redact

    Returns:
        New dictionary with sensitive fields redacted
    """
    if not isinstance(data, dict):
        return data

    redacted = {}
    for key, value in data.items():
        # Check if key matches any sensitive field (case-insensitive)
        # Remove underscores for comparison to handle both snake_case and camelCase
        key_normalized = key.lower().replace("_", "")
        is_sensitive = any(
            sensitive_field.lower().replace("_", "") in key_normalized
            for sensitive_field in sensitive_fields
        )

        if is_sensitive:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            # Recursively redact nested dictionaries
            redacted[key] = redact_sensitive_fields(value, sensitive_fields)
        elif isinstance(value, list):
            # Redact list items if they're dictionaries
            redacted[key] = [
                redact_sensitive_fields(item, sensitive_fields)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            redacted[key] = value

    return redacted


def generate_summary(step: ReasoningStep, template: Optional[str] = None) -> str:
    """Generate a summary for a step.

    Args:
        step: Reasoning step to summarize
        template: Optional template for summary (uses default if None)

    Returns:
        Summary string
    """
    if template:
        return template

    # Generate default summary based on step type
    if step.thinking:
        return f"Reasoning step #{step.step_number}"

    if step.tool_call:
        return f"Called {step.tool_call.tool_name}"

    if step.tool_result:
        status = "succeeded" if step.tool_result.success else "failed"
        return f"Tool call {status}"

    if step.synthesis:
        return f"Generated synthesis from {len(step.synthesis.sources)} sources"

    return f"Step #{step.step_number}"
