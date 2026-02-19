"""Tests for prompt management API endpoints.

This module provides comprehensive tests for all prompt management REST API endpoints
including CRUD, versioning, composition, experiments, and cache management.
"""

import pytest
from fastapi.testclient import TestClient

from omniforge.api.app import app
from omniforge.prompts.enums import MergeBehavior, PromptLayer

# Create test client
client = TestClient(app)


class TestPromptCRUD:
    """Tests for prompt CRUD endpoints."""

    def test_create_prompt_success(self) -> None:
        """Should successfully create a prompt with valid data."""
        request_data = {
            "layer": "agent",
            "name": "test-agent",
            "content": "You are a helpful assistant. {{ context }}",
            "scope_id": "agent-123",
            "created_by": "user-1",
            "merge_points": [
                {
                    "name": "context",
                    "behavior": "append",
                    "required": False,
                    "locked": False,
                }
            ],
            "variables_schema": {
                "properties": {"context": {"type": "string"}},
                "required": ["context"],
            },
        }

        response = client.post("/api/v1/prompts", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-agent"
        assert data["layer"] == "agent"
        assert data["version"] == 1
        assert "id" in data
        assert "created_at" in data

    def test_create_prompt_invalid_template(self) -> None:
        """Should fail to create prompt with invalid template syntax."""
        request_data = {
            "layer": "agent",
            "name": "test-agent",
            "content": "Invalid template {{ unclosed",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }

        response = client.post("/api/v1/prompts", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "code" in data["detail"]
        assert data["detail"]["code"] == "prompt_validation_error"

    def test_get_prompt_success(self) -> None:
        """Should successfully retrieve a prompt by ID."""
        # First create a prompt
        create_data = {
            "layer": "agent",
            "name": "get-test",
            "content": "Test content",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        # Get the prompt
        response = client.get(f"/api/v1/prompts/{prompt_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prompt_id
        assert data["name"] == "get-test"

    def test_get_prompt_not_found(self) -> None:
        """Should return 404 for non-existent prompt."""
        response = client.get("/api/v1/prompts/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "code" in data["detail"]
        assert data["detail"]["code"] == "prompt_not_found"

    def test_update_prompt_success(self) -> None:
        """Should successfully update a prompt."""
        # Create a prompt
        create_data = {
            "layer": "agent",
            "name": "update-test",
            "content": "Original content",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        # Update the prompt
        update_data = {
            "content": "Updated content",
            "change_message": "Fixed typo",
            "changed_by": "user-1",
        }
        response = client.put(f"/api/v1/prompts/{prompt_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["version"] == 2

    def test_delete_prompt_success(self) -> None:
        """Should successfully delete a prompt."""
        # Create a prompt
        create_data = {
            "layer": "agent",
            "name": "delete-test",
            "content": "Test content",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        # Delete the prompt
        response = client.delete(f"/api/v1/prompts/{prompt_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/prompts/{prompt_id}")
        assert get_response.status_code == 404

    def test_list_prompts(self) -> None:
        """Should list prompts with pagination."""
        # Create some prompts
        for i in range(3):
            create_data = {
                "layer": "agent",
                "name": f"list-test-{i}",
                "content": "Test content",
                "scope_id": "agent-123",
                "created_by": "user-1",
            }
            client.post("/api/v1/prompts", json=create_data)

        # List prompts
        response = client.get("/api/v1/prompts?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestVersioning:
    """Tests for versioning endpoints."""

    def test_list_versions(self) -> None:
        """Should list all versions of a prompt."""
        # Create a prompt
        create_data = {
            "layer": "agent",
            "name": "version-test",
            "content": "Version 1",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        # Update to create version 2
        update_data = {
            "content": "Version 2",
            "change_message": "Updated to v2",
            "changed_by": "user-1",
        }
        client.put(f"/api/v1/prompts/{prompt_id}", json=update_data)

        # List versions
        response = client.get(f"/api/v1/prompts/{prompt_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["version_number"] == 2
        assert data[1]["version_number"] == 1

    def test_get_specific_version(self) -> None:
        """Should retrieve a specific version."""
        # Create and update a prompt
        create_data = {
            "layer": "agent",
            "name": "version-get-test",
            "content": "Version 1",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        update_data = {
            "content": "Version 2",
            "change_message": "Updated",
            "changed_by": "user-1",
        }
        client.put(f"/api/v1/prompts/{prompt_id}", json=update_data)

        # Get version 1
        response = client.get(f"/api/v1/prompts/{prompt_id}/versions/1")

        assert response.status_code == 200
        data = response.json()
        assert data["version_number"] == 1
        assert data["content"] == "Version 1"

    def test_rollback_prompt(self) -> None:
        """Should rollback prompt to a previous version."""
        # Create and update a prompt
        create_data = {
            "layer": "agent",
            "name": "rollback-test",
            "content": "Version 1",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        update_data = {
            "content": "Version 2",
            "change_message": "Updated",
            "changed_by": "user-1",
        }
        client.put(f"/api/v1/prompts/{prompt_id}", json=update_data)

        # Rollback to version 1
        rollback_data = {"to_version": 1, "rolled_back_by": "user-1"}
        response = client.post(f"/api/v1/prompts/{prompt_id}/rollback", json=rollback_data)

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Version 1"
        assert data["version"] == 3  # New version created by rollback


class TestComposition:
    """Tests for composition endpoints."""

    def test_compose_prompt_basic(self) -> None:
        """Should compose a prompt for an agent."""
        # Create prompts for composition
        platform_data = {
            "layer": "platform",
            "name": "platform-prompt",
            "content": "Platform instructions",
            "scope_id": "platform",
            "created_by": "system",
        }
        client.post("/api/v1/prompts", json=platform_data)

        tenant_data = {
            "layer": "tenant",
            "name": "tenant-prompt",
            "content": "Tenant instructions",
            "scope_id": "tenant-123",
            "created_by": "admin",
        }
        client.post("/api/v1/prompts", json=tenant_data)

        agent_data = {
            "layer": "agent",
            "name": "agent-prompt",
            "content": "Agent instructions",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        client.post("/api/v1/prompts", json=agent_data)

        # Compose prompt
        compose_data = {
            "agent_id": "agent-123",
            "tenant_id": "tenant-123",
            "user_input": "Hello!",
        }
        response = client.post("/api/v1/prompts/compose", json=compose_data)

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "layers_used" in data
        assert "cache_hit" in data
        assert "composition_time_ms" in data

    def test_preview_prompt(self) -> None:
        """Should preview a composed prompt without caching."""
        # Create prompts
        agent_data = {
            "layer": "agent",
            "name": "preview-agent",
            "content": "Preview agent instructions",
            "scope_id": "agent-preview",
            "created_by": "user-1",
        }
        client.post("/api/v1/prompts", json=agent_data)

        # Preview prompt
        preview_data = {"agent_id": "agent-preview", "user_input": "Test"}
        response = client.post("/api/v1/prompts/preview", json=preview_data)

        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is False  # Preview should not use cache

    def test_validate_template(self) -> None:
        """Should validate template syntax."""
        # Valid template
        valid_data = {"content": "Hello {{ name }}"}
        response = client.post("/api/v1/prompts/validate", json=valid_data)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0

        # Invalid template
        invalid_data = {"content": "Hello {{ unclosed"}
        response = client.post("/api/v1/prompts/validate", json=invalid_data)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0


class TestExperiments:
    """Tests for experiment endpoints."""

    def test_create_experiment(self) -> None:
        """Should create a new experiment."""
        # Create a prompt
        create_data = {
            "layer": "agent",
            "name": "experiment-test",
            "content": "Version 1",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        # Create experiment
        experiment_data = {
            "name": "Test Experiment",
            "description": "Testing conciseness",
            "success_metric": "user_satisfaction",
            "variants": [
                {
                    "id": "var-1",
                    "name": "Control",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "Treatment",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
            "created_by": "user-1",
        }
        response = client.post(f"/api/v1/prompts/{prompt_id}/experiments", json=experiment_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Experiment"
        assert data["status"] == "draft"
        assert len(data["variants"]) == 2

    def test_list_experiments(self) -> None:
        """Should list experiments for a prompt."""
        # Create a prompt
        create_data = {
            "layer": "agent",
            "name": "list-exp-test",
            "content": "Test",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        # Create experiment
        experiment_data = {
            "name": "Test Experiment",
            "description": "Testing",
            "success_metric": "metric",
            "variants": [
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        }
        client.post(f"/api/v1/prompts/{prompt_id}/experiments", json=experiment_data)

        # List experiments
        response = client.get(f"/api/v1/prompts/{prompt_id}/experiments")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_experiment(self) -> None:
        """Should retrieve an experiment by ID."""
        # Create prompt and experiment
        create_data = {
            "layer": "agent",
            "name": "get-exp-test",
            "content": "Test",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        experiment_data = {
            "name": "Get Test Experiment",
            "description": "Testing",
            "success_metric": "metric",
            "variants": [
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        }
        exp_response = client.post(f"/api/v1/prompts/{prompt_id}/experiments", json=experiment_data)
        experiment_id = exp_response.json()["id"]

        # Get experiment
        response = client.get(f"/api/v1/prompts/experiments/{experiment_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == experiment_id
        assert data["name"] == "Get Test Experiment"

    def test_start_experiment(self) -> None:
        """Should start a DRAFT experiment."""
        # Create prompt and experiment
        create_data = {
            "layer": "agent",
            "name": "start-exp-test",
            "content": "Test",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        experiment_data = {
            "name": "Start Test",
            "description": "Testing",
            "success_metric": "metric",
            "variants": [
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        }
        exp_response = client.post(f"/api/v1/prompts/{prompt_id}/experiments", json=experiment_data)
        experiment_id = exp_response.json()["id"]

        # Start experiment
        response = client.post(f"/api/v1/prompts/experiments/{experiment_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_stop_experiment(self) -> None:
        """Should stop a RUNNING experiment."""
        # Create, start, then stop experiment
        create_data = {
            "layer": "agent",
            "name": "stop-exp-test",
            "content": "Test",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        experiment_data = {
            "name": "Stop Test",
            "description": "Testing",
            "success_metric": "metric",
            "variants": [
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        }
        exp_response = client.post(f"/api/v1/prompts/{prompt_id}/experiments", json=experiment_data)
        experiment_id = exp_response.json()["id"]

        # Start then stop
        client.post(f"/api/v1/prompts/experiments/{experiment_id}/start")
        response = client.post(f"/api/v1/prompts/experiments/{experiment_id}/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"


class TestCache:
    """Tests for cache management endpoints."""

    def test_get_cache_stats(self) -> None:
        """Should retrieve cache statistics."""
        response = client.get("/api/v1/prompts/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data

    def test_clear_cache(self) -> None:
        """Should clear the cache."""
        response = client.delete("/api/v1/prompts/cache")

        assert response.status_code == 204


class TestErrorHandling:
    """Tests for error handling."""

    def test_validation_error_format(self) -> None:
        """Should return properly formatted validation errors."""
        # Missing required fields
        invalid_data = {"layer": "agent"}
        response = client.post("/api/v1/prompts", json=invalid_data)

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data

    def test_not_found_error_format(self) -> None:
        """Should return properly formatted 404 errors."""
        response = client.get("/api/v1/prompts/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == "prompt_not_found"

    def test_experiment_state_error(self) -> None:
        """Should return 409 for invalid state transitions."""
        # Try to stop a DRAFT experiment (should fail)
        create_data = {
            "layer": "agent",
            "name": "state-error-test",
            "content": "Test",
            "scope_id": "agent-123",
            "created_by": "user-1",
        }
        create_response = client.post("/api/v1/prompts", json=create_data)
        prompt_id = create_response.json()["id"]

        experiment_data = {
            "name": "State Error Test",
            "description": "Testing",
            "success_metric": "metric",
            "variants": [
                {
                    "id": "var-1",
                    "name": "A",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
                {
                    "id": "var-2",
                    "name": "B",
                    "prompt_version_id": f"{prompt_id}-v1",
                    "traffic_percentage": 50.0,
                },
            ],
        }
        exp_response = client.post(f"/api/v1/prompts/{prompt_id}/experiments", json=experiment_data)
        experiment_id = exp_response.json()["id"]

        # Try to stop a DRAFT experiment
        response = client.post(f"/api/v1/prompts/experiments/{experiment_id}/stop")

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "experiment_state_error"
