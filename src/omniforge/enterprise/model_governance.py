"""Model governance for enterprise compliance.

This module provides model governance capabilities that enforce which LLM models
can be used in production environments, supporting enterprise compliance and cost control.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ModelNotApprovedError(Exception):
    """Raised when a model is not approved for use.

    Attributes:
        model: The model name that was rejected
        tenant_id: The tenant attempting to use the model
        reason: Reason for rejection
    """

    def __init__(self, model: str, tenant_id: str, reason: str):
        self.model = model
        self.tenant_id = tenant_id
        self.reason = reason
        super().__init__(f"Model '{model}' not approved for tenant '{tenant_id}': {reason}")


@dataclass
class ModelPolicy:
    """Model usage policy for a tenant.

    Attributes:
        approved_models: List of approved model names or patterns (e.g., "claude-*")
        blocked_models: List of explicitly blocked models (takes precedence)
        require_approval: Whether all model usage requires explicit approval
        max_cost_per_call_usd: Maximum cost per individual model call
    """

    approved_models: List[str] = field(default_factory=list)
    blocked_models: List[str] = field(default_factory=list)
    require_approval: bool = False
    max_cost_per_call_usd: Optional[float] = None


class ModelGovernance:
    """Model governance system for enterprise compliance.

    Manages which LLM models can be used per tenant, enforcing approved lists,
    blocked lists, and cost limits for compliance and cost control.

    Example:
        >>> default_policy = ModelPolicy(
        ...     approved_models=["claude-*", "gpt-4"],
        ...     blocked_models=["gpt-3.5-turbo"],
        ...     max_cost_per_call_usd=1.0
        ... )
        >>> governance = ModelGovernance(default_policy)
        >>> governance.configure_tenant("tenant-1", ModelPolicy(approved_models=["claude-3-5-sonnet"]))
        >>> governance.is_model_allowed("tenant-1", "claude-3-5-sonnet")
        True
    """

    def __init__(self, default_policy: Optional[ModelPolicy] = None):
        """Initialize model governance with default policy.

        Args:
            default_policy: Default policy for tenants without specific configuration
        """
        self._default_policy = default_policy or ModelPolicy()
        self._tenant_policies: Dict[str, ModelPolicy] = {}

    def configure_tenant(self, tenant_id: str, policy: ModelPolicy) -> None:
        """Configure model policy for a specific tenant.

        Args:
            tenant_id: Unique tenant identifier
            policy: Model policy for this tenant
        """
        self._tenant_policies[tenant_id] = policy

    def get_policy(self, tenant_id: str) -> ModelPolicy:
        """Get the policy for a tenant.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Model policy for the tenant (default if not configured)
        """
        return self._tenant_policies.get(tenant_id, self._default_policy)

    def is_model_allowed(self, tenant_id: str, model: str) -> bool:
        """Check if a model is allowed for a tenant.

        Args:
            tenant_id: Unique tenant identifier
            model: Model name to check

        Returns:
            True if model is allowed, False otherwise
        """
        policy = self.get_policy(tenant_id)

        # Check blocked list first (takes precedence)
        if self._matches_any_pattern(model, policy.blocked_models):
            return False

        # If require_approval is set and model not in approved list, reject
        if policy.require_approval and not self._matches_any_pattern(model, policy.approved_models):
            return False

        # If approved list exists and model not in it, reject
        if policy.approved_models and not self._matches_any_pattern(model, policy.approved_models):
            return False

        return True

    def get_approved_models(self, tenant_id: str) -> List[str]:
        """Get list of approved models for a tenant.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            List of approved model names or patterns
        """
        policy = self.get_policy(tenant_id)
        return policy.approved_models.copy()

    def validate_model_call(
        self, tenant_id: str, model: str, estimated_cost: Optional[float] = None
    ) -> None:
        """Validate a model call against policy.

        Args:
            tenant_id: Unique tenant identifier
            model: Model name to validate
            estimated_cost: Estimated cost of the call in USD (optional)

        Raises:
            ModelNotApprovedError: If model is not allowed or exceeds cost limits
        """
        policy = self.get_policy(tenant_id)

        # Check if model is blocked
        if self._matches_any_pattern(model, policy.blocked_models):
            raise ModelNotApprovedError(
                model=model,
                tenant_id=tenant_id,
                reason="Model is explicitly blocked by policy",
            )

        # Check if model requires approval
        if policy.require_approval and not self._matches_any_pattern(model, policy.approved_models):
            raise ModelNotApprovedError(
                model=model,
                tenant_id=tenant_id,
                reason="Model requires explicit approval but is not in approved list",
            )

        # Check if model is in approved list (if list exists)
        if policy.approved_models and not self._matches_any_pattern(model, policy.approved_models):
            raise ModelNotApprovedError(
                model=model,
                tenant_id=tenant_id,
                reason=f"Model not in approved list. Approved models: {', '.join(policy.approved_models)}",
            )

        # Check cost limit
        if estimated_cost is not None and policy.max_cost_per_call_usd is not None:
            if estimated_cost > policy.max_cost_per_call_usd:
                raise ModelNotApprovedError(
                    model=model,
                    tenant_id=tenant_id,
                    reason=f"Estimated cost ${estimated_cost:.4f} exceeds limit of ${policy.max_cost_per_call_usd:.4f}",
                )

    def _matches_any_pattern(self, model: str, patterns: List[str]) -> bool:
        """Check if a model name matches any pattern in a list.

        Supports wildcards:
        - "claude-*" matches any model starting with "claude-"
        - "*-turbo" matches any model ending with "-turbo"
        - "gpt-4" matches exactly "gpt-4"

        Args:
            model: Model name to check
            patterns: List of patterns to match against

        Returns:
            True if model matches any pattern, False otherwise
        """
        for pattern in patterns:
            # Convert wildcard pattern to regex
            if "*" in pattern:
                regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
                if re.match(regex_pattern, model):
                    return True
            elif pattern == model:
                # Exact match
                return True

        return False
