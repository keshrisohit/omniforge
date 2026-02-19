"""Tests for model governance."""

import pytest

from omniforge.enterprise.model_governance import (
    ModelGovernance,
    ModelNotApprovedError,
    ModelPolicy,
)


def test_model_policy_defaults():
    """Test ModelPolicy default values."""
    policy = ModelPolicy()

    assert policy.approved_models == []
    assert policy.blocked_models == []
    assert policy.require_approval is False
    assert policy.max_cost_per_call_usd is None


def test_model_policy_custom():
    """Test ModelPolicy with custom values."""
    policy = ModelPolicy(
        approved_models=["claude-3-5-sonnet", "gpt-4"],
        blocked_models=["gpt-3.5-turbo"],
        require_approval=True,
        max_cost_per_call_usd=1.0,
    )

    assert len(policy.approved_models) == 2
    assert "claude-3-5-sonnet" in policy.approved_models
    assert len(policy.blocked_models) == 1
    assert policy.require_approval is True
    assert policy.max_cost_per_call_usd == 1.0


def test_model_governance_initialization():
    """Test ModelGovernance initializes correctly."""
    governance = ModelGovernance()

    assert governance._default_policy is not None
    assert len(governance._tenant_policies) == 0


def test_model_governance_with_default_policy():
    """Test ModelGovernance with default policy."""
    default_policy = ModelPolicy(approved_models=["claude-*"])
    governance = ModelGovernance(default_policy)

    assert governance._default_policy == default_policy


def test_configure_tenant():
    """Test tenant configuration."""
    governance = ModelGovernance()
    policy = ModelPolicy(approved_models=["gpt-4"])

    governance.configure_tenant("tenant-1", policy)

    assert "tenant-1" in governance._tenant_policies
    assert governance._tenant_policies["tenant-1"] == policy


def test_get_policy_configured_tenant():
    """Test getting policy for configured tenant."""
    governance = ModelGovernance()
    policy = ModelPolicy(approved_models=["gpt-4"])

    governance.configure_tenant("tenant-1", policy)
    retrieved_policy = governance.get_policy("tenant-1")

    assert retrieved_policy == policy


def test_get_policy_unconfigured_tenant():
    """Test getting policy for unconfigured tenant returns default."""
    default_policy = ModelPolicy(approved_models=["claude-*"])
    governance = ModelGovernance(default_policy)

    policy = governance.get_policy("tenant-1")

    assert policy == default_policy


def test_is_model_allowed_approved():
    """Test model allowed when in approved list."""
    policy = ModelPolicy(approved_models=["claude-3-5-sonnet"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is True


def test_is_model_allowed_not_approved():
    """Test model not allowed when not in approved list."""
    policy = ModelPolicy(approved_models=["claude-3-5-sonnet"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "gpt-4") is False


def test_is_model_allowed_blocked():
    """Test blocked model rejected even if in approved list."""
    policy = ModelPolicy(
        approved_models=["gpt-*"],
        blocked_models=["gpt-3.5-turbo"],
    )
    governance = ModelGovernance(policy)

    # gpt-4 matches gpt-* pattern
    assert governance.is_model_allowed("tenant-1", "gpt-4") is True

    # gpt-3.5-turbo is explicitly blocked
    assert governance.is_model_allowed("tenant-1", "gpt-3.5-turbo") is False


def test_is_model_allowed_wildcard_pattern():
    """Test wildcard patterns in approved models."""
    policy = ModelPolicy(approved_models=["claude-*"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is True
    assert governance.is_model_allowed("tenant-1", "claude-opus") is True
    assert governance.is_model_allowed("tenant-1", "gpt-4") is False


def test_is_model_allowed_no_policy():
    """Test all models allowed when no policy restrictions."""
    governance = ModelGovernance()

    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is True
    assert governance.is_model_allowed("tenant-1", "gpt-4") is True
    assert governance.is_model_allowed("tenant-1", "any-model") is True


def test_is_model_allowed_require_approval():
    """Test require_approval enforces approval list."""
    policy = ModelPolicy(
        approved_models=["claude-3-5-sonnet"],
        require_approval=True,
    )
    governance = ModelGovernance(policy)

    # Approved model allowed
    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is True

    # Non-approved model rejected
    assert governance.is_model_allowed("tenant-1", "gpt-4") is False


def test_get_approved_models():
    """Test getting approved models list."""
    policy = ModelPolicy(approved_models=["claude-3-5-sonnet", "gpt-4"])
    governance = ModelGovernance(policy)

    approved = governance.get_approved_models("tenant-1")

    assert len(approved) == 2
    assert "claude-3-5-sonnet" in approved
    assert "gpt-4" in approved


def test_validate_model_call_allowed():
    """Test validate_model_call succeeds for allowed model."""
    policy = ModelPolicy(approved_models=["claude-3-5-sonnet"])
    governance = ModelGovernance(policy)

    # Should not raise exception
    governance.validate_model_call("tenant-1", "claude-3-5-sonnet")


def test_validate_model_call_blocked():
    """Test validate_model_call raises error for blocked model."""
    policy = ModelPolicy(blocked_models=["gpt-3.5-turbo"])
    governance = ModelGovernance(policy)

    with pytest.raises(ModelNotApprovedError) as exc_info:
        governance.validate_model_call("tenant-1", "gpt-3.5-turbo")

    assert "explicitly blocked" in str(exc_info.value)
    assert exc_info.value.model == "gpt-3.5-turbo"
    assert exc_info.value.tenant_id == "tenant-1"


def test_validate_model_call_not_approved():
    """Test validate_model_call raises error for non-approved model."""
    policy = ModelPolicy(approved_models=["claude-3-5-sonnet"])
    governance = ModelGovernance(policy)

    with pytest.raises(ModelNotApprovedError) as exc_info:
        governance.validate_model_call("tenant-1", "gpt-4")

    assert "not in approved list" in str(exc_info.value)
    assert exc_info.value.model == "gpt-4"


def test_validate_model_call_requires_approval():
    """Test validate_model_call with require_approval."""
    policy = ModelPolicy(
        approved_models=["claude-3-5-sonnet"],
        require_approval=True,
    )
    governance = ModelGovernance(policy)

    # Approved model succeeds
    governance.validate_model_call("tenant-1", "claude-3-5-sonnet")

    # Non-approved model fails
    with pytest.raises(ModelNotApprovedError) as exc_info:
        governance.validate_model_call("tenant-1", "gpt-4")

    assert "requires explicit approval" in str(exc_info.value)


def test_validate_model_call_cost_limit():
    """Test validate_model_call enforces cost limits."""
    policy = ModelPolicy(
        approved_models=["gpt-4"],
        max_cost_per_call_usd=1.0,
    )
    governance = ModelGovernance(policy)

    # Cost under limit succeeds
    governance.validate_model_call("tenant-1", "gpt-4", estimated_cost=0.5)

    # Cost over limit fails
    with pytest.raises(ModelNotApprovedError) as exc_info:
        governance.validate_model_call("tenant-1", "gpt-4", estimated_cost=1.5)

    assert "exceeds limit" in str(exc_info.value)
    assert "$1.5000" in str(exc_info.value)
    assert "$1.0000" in str(exc_info.value)


def test_validate_model_call_exact_cost_limit():
    """Test validate_model_call at exact cost limit."""
    policy = ModelPolicy(
        approved_models=["gpt-4"],
        max_cost_per_call_usd=1.0,
    )
    governance = ModelGovernance(policy)

    # Exact limit succeeds
    governance.validate_model_call("tenant-1", "gpt-4", estimated_cost=1.0)


def test_wildcard_pattern_prefix():
    """Test wildcard pattern at start."""
    policy = ModelPolicy(approved_models=["claude-*"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is True
    assert governance.is_model_allowed("tenant-1", "claude-opus") is True
    assert governance.is_model_allowed("tenant-1", "gpt-claude") is False


def test_wildcard_pattern_suffix():
    """Test wildcard pattern at end."""
    policy = ModelPolicy(approved_models=["*-turbo"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "gpt-3.5-turbo") is True
    assert governance.is_model_allowed("tenant-1", "claude-turbo") is True
    assert governance.is_model_allowed("tenant-1", "gpt-4") is False


def test_wildcard_pattern_middle():
    """Test wildcard pattern in middle."""
    policy = ModelPolicy(approved_models=["gpt-*-turbo"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "gpt-3.5-turbo") is True
    assert governance.is_model_allowed("tenant-1", "gpt-4-turbo") is True
    assert governance.is_model_allowed("tenant-1", "gpt--turbo") is True  # Empty match is valid
    assert governance.is_model_allowed("tenant-1", "gpt-4") is False
    assert governance.is_model_allowed("tenant-1", "turbo-gpt") is False


def test_exact_match_with_wildcard_present():
    """Test exact match still works when wildcards present."""
    policy = ModelPolicy(approved_models=["claude-*", "gpt-4"])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "gpt-4") is True
    assert governance.is_model_allowed("tenant-1", "gpt-3.5") is False


def test_per_tenant_policies():
    """Test different policies for different tenants."""
    default_policy = ModelPolicy(approved_models=["claude-*"])
    governance = ModelGovernance(default_policy)

    # Configure specific policy for tenant-1
    tenant1_policy = ModelPolicy(approved_models=["gpt-4"])
    governance.configure_tenant("tenant-1", tenant1_policy)

    # Tenant-1 uses its own policy
    assert governance.is_model_allowed("tenant-1", "gpt-4") is True
    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is False

    # Tenant-2 uses default policy
    assert governance.is_model_allowed("tenant-2", "claude-3-5-sonnet") is True
    assert governance.is_model_allowed("tenant-2", "gpt-4") is False


def test_model_not_approved_error_attributes():
    """Test ModelNotApprovedError has correct attributes."""
    error = ModelNotApprovedError(
        model="gpt-4",
        tenant_id="tenant-1",
        reason="Test reason",
    )

    assert error.model == "gpt-4"
    assert error.tenant_id == "tenant-1"
    assert error.reason == "Test reason"
    assert "gpt-4" in str(error)
    assert "tenant-1" in str(error)
    assert "Test reason" in str(error)


def test_empty_approved_list_allows_all():
    """Test empty approved list with no other restrictions allows all models."""
    policy = ModelPolicy(approved_models=[])
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "any-model") is True
    assert governance.is_model_allowed("tenant-1", "another-model") is True


def test_blocked_takes_precedence_over_wildcard():
    """Test blocked list takes precedence over wildcard approval."""
    policy = ModelPolicy(
        approved_models=["*"],  # Approve all
        blocked_models=["gpt-3.5-turbo"],  # But block this one
    )
    governance = ModelGovernance(policy)

    assert governance.is_model_allowed("tenant-1", "gpt-4") is True
    assert governance.is_model_allowed("tenant-1", "claude-3-5-sonnet") is True
    assert governance.is_model_allowed("tenant-1", "gpt-3.5-turbo") is False
