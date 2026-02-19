"""Tests for agent CLI commands."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from omniforge.builder.models import (
    AgentConfig,
    AgentExecution,
    AgentStatus,
    ExecutionStatus,
    SkillReference,
    TriggerType,
)
from omniforge.cli.agent import agent


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_agent_config() -> AgentConfig:
    """Create mock agent configuration."""
    return AgentConfig(
        id="agent-123",
        tenant_id="tenant-456",
        name="Test Agent",
        description="Test agent description",
        status=AgentStatus.ACTIVE,
        trigger=TriggerType.ON_DEMAND,
        skills=[
            SkillReference(
                skill_id="test-skill",
                name="Test Skill",
                source="custom",
                order=1,
            )
        ],
        created_by="user-789",
        created_at=datetime(2026, 1, 25, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_execution() -> AgentExecution:
    """Create mock agent execution."""
    return AgentExecution(
        id="exec-123",
        agent_id="agent-123",
        tenant_id="tenant-456",
        status=ExecutionStatus.SUCCESS,
        trigger_type="on_demand",
        started_at=datetime(2026, 1, 25, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 25, 10, 0, 5, tzinfo=timezone.utc),
        duration_ms=5000,
        output={"result": "success"},
    )


class TestListAgents:
    """Tests for agent list command."""

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    def test_list_agents_table_format(
        self,
        mock_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test listing agents in table format."""
        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_tenant.return_value = [mock_agent_config]
        mock_repo_class.return_value = mock_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["list", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        assert "Test Agent" in result.output
        assert "agent-123" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    def test_list_agents_json_format(
        self,
        mock_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test listing agents in JSON format."""
        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_tenant.return_value = [mock_agent_config]
        mock_repo_class.return_value = mock_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["list", "--format", "json", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == "agent-123"
        assert output[0]["name"] == "Test Agent"
        assert output[0]["status"] == "active"

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    def test_list_agents_with_status_filter(
        self,
        mock_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test listing agents with status filter."""
        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_tenant.return_value = [mock_agent_config]
        mock_repo_class.return_value = mock_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["list", "--status", "active", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        mock_repo.list_by_tenant.assert_called_once()
        call_kwargs = mock_repo.list_by_tenant.call_args.kwargs
        assert call_kwargs["status"] == "active"

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    def test_list_agents_empty(
        self,
        mock_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test listing agents when none exist."""
        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.list_by_tenant.return_value = []
        mock_repo_class.return_value = mock_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["list", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        assert "No agents found" in result.output


class TestRunAgent:
    """Tests for agent run command."""

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    @patch("omniforge.cli.agent.SkillMdGenerator")
    @patch("omniforge.cli.agent.AgentExecutor")
    @patch("omniforge.cli.agent.AgentExecutionService")
    def test_run_agent_success(
        self,
        mock_service_class: MagicMock,
        mock_executor_class: MagicMock,
        mock_generator_class: MagicMock,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_execution: AgentExecution,
    ) -> None:
        """Test successful agent execution."""
        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup mock service
        mock_service = AsyncMock()
        mock_service.execute_agent_by_id.return_value = mock_execution
        mock_service_class.return_value = mock_service

        result = cli_runner.invoke(
            agent,
            ["run", "agent-123", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        assert "Execution successful" in result.output
        assert "exec-123" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    @patch("omniforge.cli.agent.SkillMdGenerator")
    @patch("omniforge.cli.agent.AgentExecutor")
    @patch("omniforge.cli.agent.AgentExecutionService")
    def test_run_agent_failure(
        self,
        mock_service_class: MagicMock,
        mock_executor_class: MagicMock,
        mock_generator_class: MagicMock,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test failed agent execution."""
        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Create failed execution
        failed_execution = AgentExecution(
            id="exec-456",
            agent_id="agent-123",
            tenant_id="tenant-456",
            status=ExecutionStatus.FAILED,
            trigger_type="on_demand",
            started_at=datetime(2026, 1, 25, 10, 0, 0, tzinfo=timezone.utc),
            error="Test error",
        )

        # Setup mock service
        mock_service = AsyncMock()
        mock_service.execute_agent_by_id.return_value = failed_execution
        mock_service_class.return_value = mock_service

        result = cli_runner.invoke(
            agent,
            ["run", "agent-123", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 1
        assert "Execution failed" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    @patch("omniforge.cli.agent.SkillMdGenerator")
    @patch("omniforge.cli.agent.AgentExecutor")
    @patch("omniforge.cli.agent.AgentExecutionService")
    def test_run_agent_not_found(
        self,
        mock_service_class: MagicMock,
        mock_executor_class: MagicMock,
        mock_generator_class: MagicMock,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test running non-existent agent."""
        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup mock service
        mock_service = AsyncMock()
        mock_service.execute_agent_by_id.side_effect = ValueError("Agent not found")
        mock_service_class.return_value = mock_service

        result = cli_runner.invoke(
            agent,
            ["run", "nonexistent", "--tenant", "tenant-456"],
        )

        assert result.exit_code != 0
        assert "Agent not found" in result.output


class TestTestAgent:
    """Tests for agent test command."""

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    def test_test_agent_dry_run(
        self,
        mock_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test agent in dry-run mode."""
        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_agent_config
        mock_repo_class.return_value = mock_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["test", "agent-123", "--dry-run", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        assert "Test Agent" in result.output
        assert "Dry-run mode" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    def test_test_agent_not_found(
        self,
        mock_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test testing non-existent agent."""
        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_repo_class.return_value = mock_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["test", "nonexistent", "--dry-run", "--tenant", "tenant-456"],
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_test_agent_requires_dry_run_flag(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that --dry-run flag is required."""
        result = cli_runner.invoke(
            agent,
            ["test", "agent-123", "--tenant", "tenant-456"],
        )

        assert result.exit_code != 0


class TestAgentStatus:
    """Tests for agent status command."""

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    def test_agent_status_with_executions(
        self,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
        mock_execution: AgentExecution,
    ) -> None:
        """Test showing agent status with execution history."""
        # Setup mock repositories
        mock_agent_repo = AsyncMock()
        mock_agent_repo.get_by_id.return_value = mock_agent_config
        mock_agent_repo_class.return_value = mock_agent_repo

        mock_exec_repo = AsyncMock()
        mock_exec_repo.list_by_agent.return_value = [mock_execution]
        mock_exec_repo_class.return_value = mock_exec_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["status", "agent-123", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        assert "Test Agent" in result.output
        assert "exec-123" in result.output
        assert "success" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    def test_agent_status_no_executions(
        self,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test showing agent status with no execution history."""
        # Setup mock repositories
        mock_agent_repo = AsyncMock()
        mock_agent_repo.get_by_id.return_value = mock_agent_config
        mock_agent_repo_class.return_value = mock_agent_repo

        mock_exec_repo = AsyncMock()
        mock_exec_repo.list_by_agent.return_value = []
        mock_exec_repo_class.return_value = mock_exec_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["status", "agent-123", "--tenant", "tenant-456"],
        )

        assert result.exit_code == 0
        assert "No execution history" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    def test_agent_status_not_found(
        self,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test showing status for non-existent agent."""
        # Setup mock repository
        mock_agent_repo = AsyncMock()
        mock_agent_repo.get_by_id.return_value = None
        mock_agent_repo_class.return_value = mock_agent_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["status", "nonexistent", "--tenant", "tenant-456"],
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("omniforge.cli.agent.get_session")
    @patch("omniforge.cli.agent.AgentConfigRepository")
    @patch("omniforge.cli.agent.AgentExecutionRepository")
    def test_agent_status_custom_limit(
        self,
        mock_exec_repo_class: MagicMock,
        mock_agent_repo_class: MagicMock,
        mock_get_session: MagicMock,
        cli_runner: CliRunner,
        mock_agent_config: AgentConfig,
    ) -> None:
        """Test showing agent status with custom limit."""
        # Setup mock repositories
        mock_agent_repo = AsyncMock()
        mock_agent_repo.get_by_id.return_value = mock_agent_config
        mock_agent_repo_class.return_value = mock_agent_repo

        mock_exec_repo = AsyncMock()
        mock_exec_repo.list_by_agent.return_value = []
        mock_exec_repo_class.return_value = mock_exec_repo

        # Setup mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None

        result = cli_runner.invoke(
            agent,
            ["status", "agent-123", "--tenant", "tenant-456", "--limit", "20"],
        )

        assert result.exit_code == 0
        mock_exec_repo.list_by_agent.assert_called_once()
        call_kwargs = mock_exec_repo.list_by_agent.call_args.kwargs
        assert call_kwargs["limit"] == 20


class TestTenantHandling:
    """Tests for tenant ID handling."""

    def test_tenant_from_flag(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test tenant ID provided via --tenant flag."""
        from omniforge.cli.agent import get_tenant_id

        tenant = get_tenant_id("tenant-123")
        assert tenant == "tenant-123"

    @patch.dict("os.environ", {"OMNIFORGE_TENANT_ID": "env-tenant"})
    def test_tenant_from_environment(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test tenant ID from environment variable."""
        from omniforge.cli.agent import get_tenant_id

        tenant = get_tenant_id(None)
        assert tenant == "env-tenant"

    @patch.dict("os.environ", {}, clear=True)
    def test_tenant_default(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test default tenant ID."""
        from omniforge.cli.agent import get_tenant_id

        tenant = get_tenant_id(None)
        assert tenant == "default"
