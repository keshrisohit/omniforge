"""Tests for prompt layer-based access control."""

import pytest

from omniforge.prompts.enums import PromptLayer
from omniforge.prompts.models import Prompt
from omniforge.prompts.security import (
    LAYER_ACCESS,
    can_access_tenant_prompts,
    can_modify_layer,
    check_prompt_access,
)
from omniforge.security.rbac import Role


class TestLayerAccess:
    """Tests for LAYER_ACCESS mapping."""

    def test_viewer_cannot_modify_any_layer(self) -> None:
        """Viewer should not be able to modify any layer."""
        assert LAYER_ACCESS[Role.VIEWER] == set()

    def test_operator_cannot_modify_any_layer(self) -> None:
        """Operator should not be able to modify any layer."""
        assert LAYER_ACCESS[Role.OPERATOR] == set()

    def test_developer_can_modify_feature_and_agent_layers(self) -> None:
        """Developer should be able to modify FEATURE and AGENT layers."""
        layers = LAYER_ACCESS[Role.DEVELOPER]
        assert PromptLayer.FEATURE in layers
        assert PromptLayer.AGENT in layers
        assert PromptLayer.SYSTEM not in layers
        assert PromptLayer.TENANT not in layers

    def test_admin_can_modify_all_layers(self) -> None:
        """Admin should be able to modify all layers."""
        layers = LAYER_ACCESS[Role.ADMIN]
        assert PromptLayer.SYSTEM in layers
        assert PromptLayer.TENANT in layers
        assert PromptLayer.FEATURE in layers
        assert PromptLayer.AGENT in layers


class TestCanModifyLayer:
    """Tests for can_modify_layer function."""

    def test_admin_can_modify_system_layer(self) -> None:
        """Admin should be able to modify SYSTEM layer."""
        assert can_modify_layer(Role.ADMIN, PromptLayer.SYSTEM) is True

    def test_developer_cannot_modify_system_layer(self) -> None:
        """Developer should not be able to modify SYSTEM layer."""
        assert can_modify_layer(Role.DEVELOPER, PromptLayer.SYSTEM) is False

    def test_admin_can_modify_tenant_layer(self) -> None:
        """Admin should be able to modify TENANT layer."""
        assert can_modify_layer(Role.ADMIN, PromptLayer.TENANT) is True

    def test_developer_cannot_modify_tenant_layer(self) -> None:
        """Developer should not be able to modify TENANT layer."""
        assert can_modify_layer(Role.DEVELOPER, PromptLayer.TENANT) is False

    def test_developer_can_modify_feature_layer(self) -> None:
        """Developer should be able to modify FEATURE layer."""
        assert can_modify_layer(Role.DEVELOPER, PromptLayer.FEATURE) is True

    def test_developer_can_modify_agent_layer(self) -> None:
        """Developer should be able to modify AGENT layer."""
        assert can_modify_layer(Role.DEVELOPER, PromptLayer.AGENT) is True

    def test_viewer_cannot_modify_any_layer(self) -> None:
        """Viewer should not be able to modify any layer."""
        for layer in PromptLayer:
            assert can_modify_layer(Role.VIEWER, layer) is False

    def test_operator_cannot_modify_any_layer(self) -> None:
        """Operator should not be able to modify any layer."""
        for layer in PromptLayer:
            assert can_modify_layer(Role.OPERATOR, layer) is False


class TestCheckPromptAccess:
    """Tests for check_prompt_access function."""

    def test_developer_can_update_feature_prompt(self) -> None:
        """Developer should be able to update FEATURE layer prompt."""
        prompt = Prompt(
            id="p1",
            layer=PromptLayer.FEATURE,
            scope_id="feature1",
            name="Test Feature",
            content="Test prompt",
        )
        assert check_prompt_access(Role.DEVELOPER, prompt, "update") is True

    def test_developer_can_update_agent_prompt(self) -> None:
        """Developer should be able to update AGENT layer prompt."""
        prompt = Prompt(
            id="p2",
            layer=PromptLayer.AGENT,
            scope_id="agent1",
            name="Test Agent",
            content="Test prompt",
        )
        assert check_prompt_access(Role.DEVELOPER, prompt, "update") is True

    def test_developer_cannot_update_system_prompt(self) -> None:
        """Developer should not be able to update SYSTEM layer prompt."""
        prompt = Prompt(
            id="p3",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content="System prompt",
        )
        assert check_prompt_access(Role.DEVELOPER, prompt, "update") is False

    def test_developer_cannot_update_tenant_prompt(self) -> None:
        """Developer should not be able to update TENANT layer prompt."""
        prompt = Prompt(
            id="p4",
            layer=PromptLayer.TENANT,
            scope_id="tenant1",
            name="Tenant",
            content="Tenant prompt",
        )
        assert check_prompt_access(Role.DEVELOPER, prompt, "update") is False

    def test_admin_can_update_system_prompt(self) -> None:
        """Admin should be able to update SYSTEM layer prompt."""
        prompt = Prompt(
            id="p5",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content="System prompt",
        )
        assert check_prompt_access(Role.ADMIN, prompt, "update") is True

    def test_admin_can_update_tenant_prompt(self) -> None:
        """Admin should be able to update TENANT layer prompt."""
        prompt = Prompt(
            id="p6",
            layer=PromptLayer.TENANT,
            scope_id="tenant1",
            name="Tenant",
            content="Tenant prompt",
        )
        assert check_prompt_access(Role.ADMIN, prompt, "update") is True

    def test_viewer_can_read_any_prompt(self) -> None:
        """Viewer should be able to read prompts at any layer."""
        for layer in PromptLayer:
            prompt = Prompt(
                id=f"p-{layer.value}",
                layer=layer,
                scope_id=f"scope-{layer.value}",
                name=f"Test {layer.value}",
                content="Test content",
            )
            assert check_prompt_access(Role.VIEWER, prompt, "read") is True

    def test_viewer_cannot_update_any_prompt(self) -> None:
        """Viewer should not be able to update prompts at any layer."""
        for layer in PromptLayer:
            prompt = Prompt(
                id=f"p-{layer.value}",
                layer=layer,
                scope_id=f"scope-{layer.value}",
                name=f"Test {layer.value}",
                content="Test content",
            )
            assert check_prompt_access(Role.VIEWER, prompt, "update") is False

    def test_operator_can_compose_any_prompt(self) -> None:
        """Operator should be able to compose prompts at any layer."""
        for layer in PromptLayer:
            prompt = Prompt(
                id=f"p-{layer.value}",
                layer=layer,
                scope_id=f"scope-{layer.value}",
                name=f"Test {layer.value}",
                content="Test content",
            )
            assert check_prompt_access(Role.OPERATOR, prompt, "compose") is True

    def test_operator_cannot_create_any_prompt(self) -> None:
        """Operator should not be able to create prompts at any layer."""
        for layer in PromptLayer:
            prompt = Prompt(
                id=f"p-{layer.value}",
                layer=layer,
                scope_id=f"scope-{layer.value}",
                name=f"Test {layer.value}",
                content="Test content",
            )
            assert check_prompt_access(Role.OPERATOR, prompt, "create") is False

    def test_developer_cannot_delete_any_prompt(self) -> None:
        """Developer should not be able to delete prompts (no delete permission)."""
        for layer in [PromptLayer.FEATURE, PromptLayer.AGENT]:
            prompt = Prompt(
                id=f"p-{layer.value}",
                layer=layer,
                scope_id=f"scope-{layer.value}",
                name=f"Test {layer.value}",
                content="Test content",
            )
            # Developer doesn't have DELETE permission at all
            assert check_prompt_access(Role.DEVELOPER, prompt, "delete") is False

    def test_admin_can_delete_any_prompt(self) -> None:
        """Admin should be able to delete prompts at any layer."""
        for layer in PromptLayer:
            prompt = Prompt(
                id=f"p-{layer.value}",
                layer=layer,
                scope_id=f"scope-{layer.value}",
                name=f"Test {layer.value}",
                content="Test content",
            )
            assert check_prompt_access(Role.ADMIN, prompt, "delete") is True

    def test_invalid_operation_raises_error(self) -> None:
        """Invalid operation should raise ValueError."""
        prompt = Prompt(
            id="p1",
            layer=PromptLayer.FEATURE,
            scope_id="feature1",
            name="Test",
            content="Test",
        )
        with pytest.raises(ValueError, match="Invalid operation"):
            check_prompt_access(Role.ADMIN, prompt, "invalid_operation")


class TestTenantIsolation:
    """Tests for tenant isolation."""

    def test_user_can_access_own_tenant_prompts(self) -> None:
        """User should be able to access prompts from their own tenant."""
        assert can_access_tenant_prompts("tenant-1", "tenant-1") is True

    def test_user_cannot_access_other_tenant_prompts(self) -> None:
        """User should not be able to access prompts from other tenants."""
        assert can_access_tenant_prompts("tenant-1", "tenant-2") is False

    def test_user_can_access_system_prompts(self) -> None:
        """All users should be able to access SYSTEM prompts (no tenant_id)."""
        assert can_access_tenant_prompts("tenant-1", None) is True
        assert can_access_tenant_prompts("tenant-2", None) is True

    def test_system_user_can_access_system_prompts(self) -> None:
        """System user (no tenant) can access SYSTEM prompts."""
        assert can_access_tenant_prompts(None, None) is True

    def test_system_user_cannot_access_tenant_prompts(self) -> None:
        """System user (no tenant) cannot access tenant-scoped prompts."""
        assert can_access_tenant_prompts(None, "tenant-1") is False

    def test_multiple_tenants_isolated(self) -> None:
        """Prompts from different tenants should be isolated."""
        tenants = ["tenant-1", "tenant-2", "tenant-3"]
        for user_tenant in tenants:
            for prompt_tenant in tenants:
                if user_tenant == prompt_tenant:
                    assert can_access_tenant_prompts(user_tenant, prompt_tenant) is True
                else:
                    assert can_access_tenant_prompts(user_tenant, prompt_tenant) is False
