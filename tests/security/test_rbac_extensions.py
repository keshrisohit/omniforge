"""Tests for RBAC extensions (Phase 6)."""

import pytest

from omniforge.security.rbac import Permission, Role, ROLE_PERMISSIONS, check_permission


def test_new_tool_permissions_defined():
    """Test that new tool permissions are defined."""
    assert hasattr(Permission, "TOOL_EXECUTE")
    assert hasattr(Permission, "TOOL_REGISTER")
    assert hasattr(Permission, "TOOL_CONFIGURE")

    assert Permission.TOOL_EXECUTE == "tool:execute"
    assert Permission.TOOL_REGISTER == "tool:register"
    assert Permission.TOOL_CONFIGURE == "tool:configure"


def test_new_chain_permissions_defined():
    """Test that new chain permissions are defined."""
    assert hasattr(Permission, "CHAIN_READ")
    assert hasattr(Permission, "CHAIN_READ_FULL")
    assert hasattr(Permission, "CHAIN_EXPORT")

    assert Permission.CHAIN_READ == "chain:read"
    assert Permission.CHAIN_READ_FULL == "chain:read_full"
    assert Permission.CHAIN_EXPORT == "chain:export"


def test_new_enterprise_permissions_defined():
    """Test that new enterprise permissions are defined."""
    assert hasattr(Permission, "RATE_LIMIT_CONFIGURE")
    assert hasattr(Permission, "COST_VIEW")
    assert hasattr(Permission, "COST_CONFIGURE")

    assert Permission.RATE_LIMIT_CONFIGURE == "rate_limit:configure"
    assert Permission.COST_VIEW == "cost:view"
    assert Permission.COST_CONFIGURE == "cost:configure"


def test_new_roles_defined():
    """Test that new roles are defined."""
    assert hasattr(Role, "END_USER")
    assert hasattr(Role, "AUDITOR")

    assert Role.END_USER == "end_user"
    assert Role.AUDITOR == "auditor"


def test_end_user_permissions():
    """Test END_USER role has appropriate permissions."""
    permissions = ROLE_PERMISSIONS[Role.END_USER]

    # Should have basic task and tool execution
    assert Permission.TASK_CREATE in permissions
    assert Permission.TASK_READ in permissions
    assert Permission.TOOL_EXECUTE in permissions
    assert Permission.CHAIN_READ in permissions

    # Should NOT have full chain visibility
    assert Permission.CHAIN_READ_FULL not in permissions
    assert Permission.CHAIN_EXPORT not in permissions

    # Should NOT have agent management
    assert Permission.AGENT_CREATE not in permissions
    assert Permission.AGENT_UPDATE not in permissions


def test_developer_tool_permissions():
    """Test DEVELOPER role has full tool permissions."""
    permissions = ROLE_PERMISSIONS[Role.DEVELOPER]

    assert Permission.TOOL_EXECUTE in permissions
    assert Permission.TOOL_REGISTER in permissions
    assert Permission.TOOL_CONFIGURE in permissions


def test_developer_chain_permissions():
    """Test DEVELOPER role has full chain access."""
    permissions = ROLE_PERMISSIONS[Role.DEVELOPER]

    assert Permission.CHAIN_READ in permissions
    assert Permission.CHAIN_READ_FULL in permissions
    assert Permission.CHAIN_EXPORT in permissions


def test_auditor_permissions():
    """Test AUDITOR role has read-all access."""
    permissions = ROLE_PERMISSIONS[Role.AUDITOR]

    # Should have read access to everything
    assert Permission.AGENT_READ in permissions
    assert Permission.TASK_READ in permissions
    assert Permission.CHAIN_READ in permissions
    assert Permission.CHAIN_READ_FULL in permissions
    assert Permission.CHAIN_EXPORT in permissions
    assert Permission.PROMPT_READ in permissions
    assert Permission.EXPERIMENT_READ in permissions
    assert Permission.COST_VIEW in permissions

    # Should NOT have write/modify permissions
    assert Permission.AGENT_CREATE not in permissions
    assert Permission.TASK_CREATE not in permissions
    assert Permission.TOOL_REGISTER not in permissions
    assert Permission.COST_CONFIGURE not in permissions


def test_admin_has_all_permissions():
    """Test ADMIN role has all permissions."""
    admin_permissions = ROLE_PERMISSIONS[Role.ADMIN]

    # Check tool permissions
    assert Permission.TOOL_EXECUTE in admin_permissions
    assert Permission.TOOL_REGISTER in admin_permissions
    assert Permission.TOOL_CONFIGURE in admin_permissions

    # Check chain permissions
    assert Permission.CHAIN_READ in admin_permissions
    assert Permission.CHAIN_READ_FULL in admin_permissions
    assert Permission.CHAIN_EXPORT in admin_permissions

    # Check enterprise permissions
    assert Permission.RATE_LIMIT_CONFIGURE in admin_permissions
    assert Permission.COST_VIEW in admin_permissions
    assert Permission.COST_CONFIGURE in admin_permissions


def test_viewer_chain_read():
    """Test VIEWER role can read chains but not full details."""
    permissions = ROLE_PERMISSIONS[Role.VIEWER]

    assert Permission.CHAIN_READ in permissions
    assert Permission.CHAIN_READ_FULL not in permissions
    assert Permission.CHAIN_EXPORT not in permissions


def test_operator_tool_execute():
    """Test OPERATOR role can execute tools."""
    permissions = ROLE_PERMISSIONS[Role.OPERATOR]

    assert Permission.TOOL_EXECUTE in permissions
    assert Permission.TOOL_REGISTER not in permissions
    assert Permission.TOOL_CONFIGURE not in permissions


def test_check_permission_tool_execute():
    """Test permission checking for TOOL_EXECUTE."""
    assert check_permission(Role.END_USER, Permission.TOOL_EXECUTE) is True
    assert check_permission(Role.OPERATOR, Permission.TOOL_EXECUTE) is True
    assert check_permission(Role.DEVELOPER, Permission.TOOL_EXECUTE) is True
    assert check_permission(Role.ADMIN, Permission.TOOL_EXECUTE) is True
    assert check_permission(Role.VIEWER, Permission.TOOL_EXECUTE) is False


def test_check_permission_tool_register():
    """Test permission checking for TOOL_REGISTER."""
    assert check_permission(Role.DEVELOPER, Permission.TOOL_REGISTER) is True
    assert check_permission(Role.ADMIN, Permission.TOOL_REGISTER) is True
    assert check_permission(Role.OPERATOR, Permission.TOOL_REGISTER) is False
    assert check_permission(Role.END_USER, Permission.TOOL_REGISTER) is False


def test_check_permission_chain_read_full():
    """Test permission checking for CHAIN_READ_FULL."""
    assert check_permission(Role.DEVELOPER, Permission.CHAIN_READ_FULL) is True
    assert check_permission(Role.AUDITOR, Permission.CHAIN_READ_FULL) is True
    assert check_permission(Role.ADMIN, Permission.CHAIN_READ_FULL) is True
    assert check_permission(Role.OPERATOR, Permission.CHAIN_READ_FULL) is False
    assert check_permission(Role.VIEWER, Permission.CHAIN_READ_FULL) is False
    assert check_permission(Role.END_USER, Permission.CHAIN_READ_FULL) is False


def test_check_permission_chain_export():
    """Test permission checking for CHAIN_EXPORT."""
    assert check_permission(Role.DEVELOPER, Permission.CHAIN_EXPORT) is True
    assert check_permission(Role.AUDITOR, Permission.CHAIN_EXPORT) is True
    assert check_permission(Role.ADMIN, Permission.CHAIN_EXPORT) is True
    assert check_permission(Role.OPERATOR, Permission.CHAIN_EXPORT) is False


def test_check_permission_rate_limit_configure():
    """Test permission checking for RATE_LIMIT_CONFIGURE."""
    assert check_permission(Role.ADMIN, Permission.RATE_LIMIT_CONFIGURE) is True
    assert check_permission(Role.DEVELOPER, Permission.RATE_LIMIT_CONFIGURE) is False
    assert check_permission(Role.AUDITOR, Permission.RATE_LIMIT_CONFIGURE) is False


def test_check_permission_cost_view():
    """Test permission checking for COST_VIEW."""
    assert check_permission(Role.DEVELOPER, Permission.COST_VIEW) is True
    assert check_permission(Role.AUDITOR, Permission.COST_VIEW) is True
    assert check_permission(Role.ADMIN, Permission.COST_VIEW) is True
    assert check_permission(Role.OPERATOR, Permission.COST_VIEW) is False
    assert check_permission(Role.END_USER, Permission.COST_VIEW) is False


def test_check_permission_cost_configure():
    """Test permission checking for COST_CONFIGURE."""
    assert check_permission(Role.ADMIN, Permission.COST_CONFIGURE) is True
    assert check_permission(Role.DEVELOPER, Permission.COST_CONFIGURE) is False
    assert check_permission(Role.AUDITOR, Permission.COST_CONFIGURE) is False


def test_all_roles_have_permissions():
    """Test that all roles have at least one permission."""
    for role in Role:
        assert role in ROLE_PERMISSIONS
        assert len(ROLE_PERMISSIONS[role]) > 0


def test_role_hierarchy_basic_access():
    """Test basic access permissions across role hierarchy."""
    # END_USER should have minimal access
    end_user_perms = ROLE_PERMISSIONS[Role.END_USER]
    assert len(end_user_perms) <= 5

    # VIEWER should have more read permissions
    viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
    assert Permission.AGENT_READ in viewer_perms
    assert Permission.TASK_READ in viewer_perms

    # DEVELOPER should have create permissions
    developer_perms = ROLE_PERMISSIONS[Role.DEVELOPER]
    assert Permission.AGENT_CREATE in developer_perms
    assert Permission.TOOL_REGISTER in developer_perms

    # ADMIN should have configuration permissions
    admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
    assert Permission.RATE_LIMIT_CONFIGURE in admin_perms
    assert Permission.COST_CONFIGURE in admin_perms


def test_auditor_no_write_permissions():
    """Test AUDITOR role has no write permissions."""
    auditor_perms = ROLE_PERMISSIONS[Role.AUDITOR]

    # Check no create permissions
    assert Permission.AGENT_CREATE not in auditor_perms
    assert Permission.TASK_CREATE not in auditor_perms
    assert Permission.PROMPT_CREATE not in auditor_perms

    # Check no update permissions
    assert Permission.AGENT_UPDATE not in auditor_perms
    assert Permission.PROMPT_UPDATE not in auditor_perms

    # Check no delete permissions
    assert Permission.AGENT_DELETE not in auditor_perms
    assert Permission.PROMPT_DELETE not in auditor_perms


def test_permission_string_format():
    """Test that new permissions follow naming convention."""
    # Tool permissions
    assert Permission.TOOL_EXECUTE.startswith("tool:")
    assert Permission.TOOL_REGISTER.startswith("tool:")
    assert Permission.TOOL_CONFIGURE.startswith("tool:")

    # Chain permissions
    assert Permission.CHAIN_READ.startswith("chain:")
    assert Permission.CHAIN_READ_FULL.startswith("chain:")
    assert Permission.CHAIN_EXPORT.startswith("chain:")

    # Enterprise permissions
    assert ":" in Permission.RATE_LIMIT_CONFIGURE
    assert ":" in Permission.COST_VIEW
    assert ":" in Permission.COST_CONFIGURE


def test_check_permission_none_role():
    """Test that None role has no permissions."""
    assert check_permission(None, Permission.TOOL_EXECUTE) is False
    assert check_permission(None, Permission.CHAIN_READ) is False
    assert check_permission(None, Permission.COST_VIEW) is False


def test_developer_cost_permissions():
    """Test DEVELOPER has view but not configure cost permissions."""
    developer_perms = ROLE_PERMISSIONS[Role.DEVELOPER]

    assert Permission.COST_VIEW in developer_perms
    assert Permission.COST_CONFIGURE not in developer_perms
