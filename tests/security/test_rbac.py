"""Tests for Role-Based Access Control (RBAC)."""

from omniforge.security.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
    check_permission,
)


class TestPermissionEnum:
    """Tests for Permission enum."""

    def test_permission_values(self) -> None:
        """Permission enum should have expected values."""
        assert Permission.AGENT_CREATE.value == "agent:create"
        assert Permission.AGENT_READ.value == "agent:read"
        assert Permission.AGENT_UPDATE.value == "agent:update"
        assert Permission.AGENT_DELETE.value == "agent:delete"
        assert Permission.TASK_CREATE.value == "task:create"
        assert Permission.TASK_READ.value == "task:read"
        assert Permission.TASK_CANCEL.value == "task:cancel"
        assert Permission.SKILL_INVOKE.value == "skill:invoke"

    def test_prompt_permission_values(self) -> None:
        """Permission enum should have prompt-related values."""
        assert Permission.PROMPT_CREATE.value == "prompt:create"
        assert Permission.PROMPT_READ.value == "prompt:read"
        assert Permission.PROMPT_UPDATE.value == "prompt:update"
        assert Permission.PROMPT_DELETE.value == "prompt:delete"
        assert Permission.PROMPT_COMPOSE.value == "prompt:compose"

    def test_experiment_permission_values(self) -> None:
        """Permission enum should have experiment-related values."""
        assert Permission.EXPERIMENT_CREATE.value == "experiment:create"
        assert Permission.EXPERIMENT_READ.value == "experiment:read"
        assert Permission.EXPERIMENT_UPDATE.value == "experiment:update"
        assert Permission.EXPERIMENT_DELETE.value == "experiment:delete"

    def test_cache_permission_values(self) -> None:
        """Permission enum should have cache-related values."""
        assert Permission.CACHE_CLEAR.value == "cache:clear"
        assert Permission.CACHE_STATS.value == "cache:stats"


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_values(self) -> None:
        """Role enum should have expected values."""
        assert Role.VIEWER.value == "viewer"
        assert Role.OPERATOR.value == "operator"
        assert Role.DEVELOPER.value == "developer"
        assert Role.ADMIN.value == "admin"


class TestRolePermissions:
    """Tests for ROLE_PERMISSIONS mapping."""

    def test_viewer_permissions(self) -> None:
        """Viewer role should have read-only permissions."""
        permissions = ROLE_PERMISSIONS[Role.VIEWER]

        assert Permission.AGENT_READ in permissions
        assert Permission.TASK_READ in permissions
        assert Permission.PROMPT_READ in permissions
        assert Permission.EXPERIMENT_READ in permissions
        assert Permission.AGENT_CREATE not in permissions
        assert Permission.TASK_CREATE not in permissions
        assert Permission.PROMPT_CREATE not in permissions

    def test_operator_permissions(self) -> None:
        """Operator role should have task execution permissions."""
        permissions = ROLE_PERMISSIONS[Role.OPERATOR]

        assert Permission.AGENT_READ in permissions
        assert Permission.TASK_CREATE in permissions
        assert Permission.TASK_READ in permissions
        assert Permission.TASK_CANCEL in permissions
        assert Permission.SKILL_INVOKE in permissions
        assert Permission.PROMPT_READ in permissions
        assert Permission.PROMPT_COMPOSE in permissions
        assert Permission.EXPERIMENT_READ in permissions
        assert Permission.AGENT_CREATE not in permissions
        assert Permission.PROMPT_CREATE not in permissions
        assert Permission.PROMPT_DELETE not in permissions

    def test_developer_permissions(self) -> None:
        """Developer role should have agent management permissions."""
        permissions = ROLE_PERMISSIONS[Role.DEVELOPER]

        assert Permission.AGENT_CREATE in permissions
        assert Permission.AGENT_READ in permissions
        assert Permission.AGENT_UPDATE in permissions
        assert Permission.AGENT_DELETE in permissions
        assert Permission.TASK_CREATE in permissions
        assert Permission.SKILL_INVOKE in permissions
        assert Permission.PROMPT_CREATE in permissions
        assert Permission.PROMPT_READ in permissions
        assert Permission.PROMPT_UPDATE in permissions
        assert Permission.PROMPT_COMPOSE in permissions
        assert Permission.EXPERIMENT_CREATE in permissions
        assert Permission.EXPERIMENT_READ in permissions
        assert Permission.EXPERIMENT_UPDATE in permissions
        assert Permission.PROMPT_DELETE not in permissions
        assert Permission.EXPERIMENT_DELETE not in permissions
        assert Permission.CACHE_CLEAR not in permissions

    def test_admin_permissions(self) -> None:
        """Admin role should have all permissions."""
        permissions = ROLE_PERMISSIONS[Role.ADMIN]

        # Admin should have all permissions
        for permission in Permission:
            assert permission in permissions


class TestCheckPermission:
    """Tests for check_permission function."""

    def test_viewer_can_read_agents(self) -> None:
        """Viewer should be able to read agents."""
        assert check_permission(Role.VIEWER, Permission.AGENT_READ) is True

    def test_viewer_cannot_create_agents(self) -> None:
        """Viewer should not be able to create agents."""
        assert check_permission(Role.VIEWER, Permission.AGENT_CREATE) is False

    def test_operator_can_create_tasks(self) -> None:
        """Operator should be able to create tasks."""
        assert check_permission(Role.OPERATOR, Permission.TASK_CREATE) is True

    def test_operator_cannot_create_agents(self) -> None:
        """Operator should not be able to create agents."""
        assert check_permission(Role.OPERATOR, Permission.AGENT_CREATE) is False

    def test_developer_can_create_agents(self) -> None:
        """Developer should be able to create agents."""
        assert check_permission(Role.DEVELOPER, Permission.AGENT_CREATE) is True

    def test_developer_can_delete_agents(self) -> None:
        """Developer should be able to delete agents."""
        assert check_permission(Role.DEVELOPER, Permission.AGENT_DELETE) is True

    def test_admin_has_all_permissions(self) -> None:
        """Admin should have all permissions."""
        for permission in Permission:
            assert check_permission(Role.ADMIN, permission) is True

    def test_none_role_has_no_permissions(self) -> None:
        """None role should have no permissions."""
        for permission in Permission:
            assert check_permission(None, permission) is False


class TestPromptPermissions:
    """Tests for prompt-specific permissions."""

    def test_viewer_can_read_prompts(self) -> None:
        """Viewer should be able to read prompts."""
        assert check_permission(Role.VIEWER, Permission.PROMPT_READ) is True

    def test_viewer_cannot_create_prompts(self) -> None:
        """Viewer should not be able to create prompts."""
        assert check_permission(Role.VIEWER, Permission.PROMPT_CREATE) is False

    def test_viewer_cannot_compose_prompts(self) -> None:
        """Viewer should not be able to compose prompts."""
        assert check_permission(Role.VIEWER, Permission.PROMPT_COMPOSE) is False

    def test_operator_can_read_prompts(self) -> None:
        """Operator should be able to read prompts."""
        assert check_permission(Role.OPERATOR, Permission.PROMPT_READ) is True

    def test_operator_can_compose_prompts(self) -> None:
        """Operator should be able to compose prompts."""
        assert check_permission(Role.OPERATOR, Permission.PROMPT_COMPOSE) is True

    def test_operator_cannot_create_prompts(self) -> None:
        """Operator should not be able to create prompts."""
        assert check_permission(Role.OPERATOR, Permission.PROMPT_CREATE) is False

    def test_developer_can_create_prompts(self) -> None:
        """Developer should be able to create prompts."""
        assert check_permission(Role.DEVELOPER, Permission.PROMPT_CREATE) is True

    def test_developer_can_update_prompts(self) -> None:
        """Developer should be able to update prompts."""
        assert check_permission(Role.DEVELOPER, Permission.PROMPT_UPDATE) is True

    def test_developer_cannot_delete_prompts(self) -> None:
        """Developer should not be able to delete prompts."""
        assert check_permission(Role.DEVELOPER, Permission.PROMPT_DELETE) is False

    def test_admin_can_delete_prompts(self) -> None:
        """Admin should be able to delete prompts."""
        assert check_permission(Role.ADMIN, Permission.PROMPT_DELETE) is True

    def test_admin_can_clear_cache(self) -> None:
        """Admin should be able to clear cache."""
        assert check_permission(Role.ADMIN, Permission.CACHE_CLEAR) is True

    def test_developer_cannot_clear_cache(self) -> None:
        """Developer should not be able to clear cache."""
        assert check_permission(Role.DEVELOPER, Permission.CACHE_CLEAR) is False


class TestExperimentPermissions:
    """Tests for experiment-specific permissions."""

    def test_viewer_can_read_experiments(self) -> None:
        """Viewer should be able to read experiments."""
        assert check_permission(Role.VIEWER, Permission.EXPERIMENT_READ) is True

    def test_viewer_cannot_create_experiments(self) -> None:
        """Viewer should not be able to create experiments."""
        assert check_permission(Role.VIEWER, Permission.EXPERIMENT_CREATE) is False

    def test_developer_can_create_experiments(self) -> None:
        """Developer should be able to create experiments."""
        assert check_permission(Role.DEVELOPER, Permission.EXPERIMENT_CREATE) is True

    def test_developer_can_update_experiments(self) -> None:
        """Developer should be able to update experiments."""
        assert check_permission(Role.DEVELOPER, Permission.EXPERIMENT_UPDATE) is True

    def test_developer_cannot_delete_experiments(self) -> None:
        """Developer should not be able to delete experiments."""
        assert check_permission(Role.DEVELOPER, Permission.EXPERIMENT_DELETE) is False

    def test_admin_can_delete_experiments(self) -> None:
        """Admin should be able to delete experiments."""
        assert check_permission(Role.ADMIN, Permission.EXPERIMENT_DELETE) is True


class TestOrchestrationPermissions:
    """Tests for orchestration and handoff permissions."""

    def test_orchestration_permission_values(self) -> None:
        """Orchestration permissions should have expected values."""
        assert Permission.ORCHESTRATION_DELEGATE.value == "orchestration:delegate"
        assert Permission.HANDOFF_INITIATE.value == "handoff:initiate"
        assert Permission.HANDOFF_CANCEL.value == "handoff:cancel"

    def test_end_user_can_initiate_handoff(self) -> None:
        """End user should be able to initiate handoffs."""
        assert check_permission(Role.END_USER, Permission.HANDOFF_INITIATE) is True

    def test_end_user_cannot_delegate(self) -> None:
        """End user should not be able to delegate orchestration."""
        assert check_permission(Role.END_USER, Permission.ORCHESTRATION_DELEGATE) is False

    def test_end_user_cannot_cancel_handoff(self) -> None:
        """End user should not be able to cancel handoffs."""
        assert check_permission(Role.END_USER, Permission.HANDOFF_CANCEL) is False

    def test_viewer_cannot_initiate_handoff(self) -> None:
        """Viewer should not be able to initiate handoffs."""
        assert check_permission(Role.VIEWER, Permission.HANDOFF_INITIATE) is False

    def test_viewer_cannot_delegate(self) -> None:
        """Viewer should not be able to delegate orchestration."""
        assert check_permission(Role.VIEWER, Permission.ORCHESTRATION_DELEGATE) is False

    def test_viewer_cannot_cancel_handoff(self) -> None:
        """Viewer should not be able to cancel handoffs."""
        assert check_permission(Role.VIEWER, Permission.HANDOFF_CANCEL) is False

    def test_operator_can_delegate(self) -> None:
        """Operator should be able to delegate orchestration."""
        assert check_permission(Role.OPERATOR, Permission.ORCHESTRATION_DELEGATE) is True

    def test_operator_can_initiate_handoff(self) -> None:
        """Operator should be able to initiate handoffs."""
        assert check_permission(Role.OPERATOR, Permission.HANDOFF_INITIATE) is True

    def test_operator_can_cancel_handoff(self) -> None:
        """Operator should be able to cancel handoffs."""
        assert check_permission(Role.OPERATOR, Permission.HANDOFF_CANCEL) is True

    def test_developer_can_delegate(self) -> None:
        """Developer should be able to delegate orchestration."""
        assert check_permission(Role.DEVELOPER, Permission.ORCHESTRATION_DELEGATE) is True

    def test_developer_can_initiate_handoff(self) -> None:
        """Developer should be able to initiate handoffs."""
        assert check_permission(Role.DEVELOPER, Permission.HANDOFF_INITIATE) is True

    def test_developer_can_cancel_handoff(self) -> None:
        """Developer should be able to cancel handoffs."""
        assert check_permission(Role.DEVELOPER, Permission.HANDOFF_CANCEL) is True

    def test_admin_can_delegate(self) -> None:
        """Admin should be able to delegate orchestration."""
        assert check_permission(Role.ADMIN, Permission.ORCHESTRATION_DELEGATE) is True

    def test_admin_can_initiate_handoff(self) -> None:
        """Admin should be able to initiate handoffs."""
        assert check_permission(Role.ADMIN, Permission.HANDOFF_INITIATE) is True

    def test_admin_can_cancel_handoff(self) -> None:
        """Admin should be able to cancel handoffs."""
        assert check_permission(Role.ADMIN, Permission.HANDOFF_CANCEL) is True

    def test_orchestration_permissions_in_role_mappings(self) -> None:
        """Orchestration permissions should be correctly mapped to roles."""
        # END_USER has only HANDOFF_INITIATE
        end_user_perms = ROLE_PERMISSIONS[Role.END_USER]
        assert Permission.HANDOFF_INITIATE in end_user_perms
        assert Permission.ORCHESTRATION_DELEGATE not in end_user_perms
        assert Permission.HANDOFF_CANCEL not in end_user_perms

        # VIEWER has none
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.HANDOFF_INITIATE not in viewer_perms
        assert Permission.ORCHESTRATION_DELEGATE not in viewer_perms
        assert Permission.HANDOFF_CANCEL not in viewer_perms

        # OPERATOR has all three
        operator_perms = ROLE_PERMISSIONS[Role.OPERATOR]
        assert Permission.ORCHESTRATION_DELEGATE in operator_perms
        assert Permission.HANDOFF_INITIATE in operator_perms
        assert Permission.HANDOFF_CANCEL in operator_perms

        # DEVELOPER has all three
        developer_perms = ROLE_PERMISSIONS[Role.DEVELOPER]
        assert Permission.ORCHESTRATION_DELEGATE in developer_perms
        assert Permission.HANDOFF_INITIATE in developer_perms
        assert Permission.HANDOFF_CANCEL in developer_perms

        # ADMIN has all three
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.ORCHESTRATION_DELEGATE in admin_perms
        assert Permission.HANDOFF_INITIATE in admin_perms
        assert Permission.HANDOFF_CANCEL in admin_perms
