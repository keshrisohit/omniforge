"""Tests for ToolExecutor skill stack integration."""

import logging
from pathlib import Path
from typing import Any

import pytest

from omniforge.agents.cot.chain import ChainStatus, ReasoningChain
from omniforge.skills.context import SkillContext
from omniforge.skills.errors import (
    SkillActivationError,
    SkillError,
)
from omniforge.skills.models import Skill, SkillHooks, SkillMetadata
from omniforge.tools import BaseTool, ToolCallContext, ToolDefinition, ToolResult
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name: str = "mock_tool") -> None:
        """Initialize mock tool."""
        from omniforge.tools.base import ToolParameter

        self._definition = ToolDefinition(
            name=name,
            type="function",
            description="Mock tool for testing",
            timeout_ms=30000,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input parameter",
                    required=False,
                ),
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="File path parameter",
                    required=False,
                ),
            ],
        )

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return self._definition

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        return ToolResult(
            success=True,
            result={"output": f"executed {self._definition.name}"},
            duration_ms=100,
        )


@pytest.fixture
def registry() -> ToolRegistry:
    """Create a fresh tool registry with mock tools."""
    reg = ToolRegistry()
    reg.register(MockTool("read"))
    reg.register(MockTool("write"))
    reg.register(MockTool("grep"))
    return reg


@pytest.fixture
def context() -> ToolCallContext:
    """Create a test execution context."""
    return ToolCallContext(
        correlation_id="test-correlation-123",
        task_id="test-task-456",
        agent_id="test-agent-789",
        tenant_id="test-tenant-001",
        chain_id="test-chain-111",
    )


@pytest.fixture
def chain() -> ReasoningChain:
    """Create a test reasoning chain."""
    return ReasoningChain(
        task_id="test-task-456",
        agent_id="test-agent-789",
        tenant_id="test-tenant-001",
        status=ChainStatus.RUNNING,
    )


@pytest.fixture
def unrestricted_skill() -> Skill:
    """Create a skill with no tool restrictions."""
    return Skill(
        metadata=SkillMetadata(
            name="unrestricted-skill",
            description="A skill with no tool restrictions",
            allowed_tools=None,  # No restrictions
        ),
        content="# Unrestricted Skill\nCan use any tool.",
        path=Path("/tmp/unrestricted-skill.md"),
        base_path=Path("/tmp"),
        storage_layer="global",
    )


@pytest.fixture
def restricted_skill() -> Skill:
    """Create a skill with tool restrictions."""
    return Skill(
        metadata=SkillMetadata(
            name="restricted-skill",
            description="A skill with tool restrictions",
            allowed_tools=["read", "grep"],  # Only read and grep allowed
        ),
        content="# Restricted Skill\nCan only use read and grep tools.",
        path=Path("/tmp/restricted-skill.md"),
        base_path=Path("/tmp"),
        storage_layer="global",
    )


@pytest.fixture
def skill_with_script() -> Skill:
    """Create a skill with hook scripts."""
    skill_path = Path("/tmp/skill-with-script.md")
    pre_script_path = Path("/tmp/pre-hook.py")

    return Skill(
        metadata=SkillMetadata(
            name="skill-with-script",
            description="A skill with hook scripts",
            allowed_tools=["read", "write", "grep"],  # Include read so we can test script blocking
            hooks=SkillHooks(pre="pre-hook.py"),
        ),
        content="# Skill With Script\nHas pre-hook script.",
        path=skill_path,
        base_path=Path("/tmp"),
        storage_layer="global",
        script_paths={"pre": pre_script_path},
    )


class TestToolExecutorSkillStack:
    """Tests for skill stack management in ToolExecutor."""

    def test_active_skill_property_returns_none_when_empty(self, registry: ToolRegistry) -> None:
        """Should return None when skill stack is empty."""
        executor = ToolExecutor(registry)
        assert executor.active_skill is None

    def test_active_skill_property_returns_top_of_stack(
        self, registry: ToolRegistry, restricted_skill: Skill
    ) -> None:
        """Should return the skill at the top of the stack."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)
        assert executor.active_skill == restricted_skill
        assert executor.active_skill.metadata.name == "restricted-skill"

    def test_activate_skill_adds_to_stack(
        self, registry: ToolRegistry, restricted_skill: Skill
    ) -> None:
        """Should add skill to stack and create context."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        assert len(executor._skill_stack) == 1
        assert executor._skill_stack[0] == restricted_skill
        assert "restricted-skill" in executor._skill_contexts
        assert isinstance(executor._skill_contexts["restricted-skill"], SkillContext)

    def test_activate_skill_raises_error_if_already_active(
        self, registry: ToolRegistry, restricted_skill: Skill
    ) -> None:
        """Should raise SkillActivationError if skill is already active."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        with pytest.raises(SkillActivationError) as exc_info:
            executor.activate_skill(restricted_skill)

        assert "already active" in str(exc_info.value)
        assert exc_info.value.skill_name == "restricted-skill"

    def test_activate_multiple_skills_stacks_correctly(
        self, registry: ToolRegistry, restricted_skill: Skill, unrestricted_skill: Skill
    ) -> None:
        """Should stack multiple skills correctly."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)
        executor.activate_skill(unrestricted_skill)

        assert len(executor._skill_stack) == 2
        assert executor._skill_stack[0] == restricted_skill
        assert executor._skill_stack[1] == unrestricted_skill
        assert executor.active_skill == unrestricted_skill

    def test_deactivate_skill_removes_from_top(
        self, registry: ToolRegistry, restricted_skill: Skill
    ) -> None:
        """Should remove skill from top of stack."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)
        executor.deactivate_skill("restricted-skill")

        assert len(executor._skill_stack) == 0
        assert "restricted-skill" not in executor._skill_contexts
        assert executor.active_skill is None

    def test_deactivate_skill_enforces_lifo_order(
        self, registry: ToolRegistry, restricted_skill: Skill, unrestricted_skill: Skill
    ) -> None:
        """Should enforce LIFO deactivation order."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)
        executor.activate_skill(unrestricted_skill)

        # Try to deactivate the bottom skill (should fail)
        with pytest.raises(SkillError) as exc_info:
            executor.deactivate_skill("restricted-skill")

        assert "not at top of stack" in str(exc_info.value)
        assert "unrestricted-skill" in str(exc_info.value)

        # Should still have both skills active
        assert len(executor._skill_stack) == 2

    def test_deactivate_skill_raises_error_if_not_active(self, registry: ToolRegistry) -> None:
        """Should raise SkillError if skill is not active."""
        executor = ToolExecutor(registry)

        with pytest.raises(SkillError) as exc_info:
            executor.deactivate_skill("nonexistent-skill")

        assert "not active" in str(exc_info.value)

    def test_deactivate_multiple_skills_in_order(
        self, registry: ToolRegistry, restricted_skill: Skill, unrestricted_skill: Skill
    ) -> None:
        """Should deactivate multiple skills in LIFO order."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)
        executor.activate_skill(unrestricted_skill)

        # Deactivate top skill first
        executor.deactivate_skill("unrestricted-skill")
        assert len(executor._skill_stack) == 1
        assert executor.active_skill == restricted_skill

        # Then deactivate remaining skill
        executor.deactivate_skill("restricted-skill")
        assert len(executor._skill_stack) == 0
        assert executor.active_skill is None


class TestToolExecutorSkillRestrictions:
    """Tests for skill restriction enforcement during tool execution."""

    @pytest.mark.asyncio
    async def test_execute_without_skill_allows_all_tools(
        self, registry: ToolRegistry, context: ToolCallContext, chain: ReasoningChain
    ) -> None:
        """Should allow all tools when no skill is active."""
        executor = ToolExecutor(registry)

        # Should succeed
        result = await executor.execute("read", {"input": "test"}, context, chain)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_unrestricted_skill_allows_all_tools(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        unrestricted_skill: Skill,
    ) -> None:
        """Should allow all tools when skill has no restrictions."""
        executor = ToolExecutor(registry)
        executor.activate_skill(unrestricted_skill)

        # Should succeed
        result = await executor.execute("read", {"input": "test"}, context, chain)
        assert result.success is True

        result = await executor.execute("write", {"input": "test"}, context, chain)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_restricted_skill_blocks_disallowed_tool(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        restricted_skill: Skill,
    ) -> None:
        """Should block tools not in allowed_tools list."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        # Write tool is not allowed (only read and grep are allowed)
        result = await executor.execute("write", {"input": "test"}, context, chain)

        # Should return error result instead of executing
        assert result.success is False
        assert "cannot use tool 'write'" in result.error.lower()
        assert "read, grep" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_restricted_skill_allows_allowed_tool(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        restricted_skill: Skill,
    ) -> None:
        """Should allow tools in allowed_tools list."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        # Read tool is allowed
        result = await executor.execute("read", {"input": "test"}, context, chain)
        assert result.success is True

        # Grep tool is allowed
        result = await executor.execute("grep", {"input": "test"}, context, chain)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_blocks_script_read_attempts(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        skill_with_script: Skill,
    ) -> None:
        """Should block attempts to read skill hook scripts."""
        executor = ToolExecutor(registry)
        executor.activate_skill(skill_with_script)

        # Try to read the pre-hook script
        result = await executor.execute("read", {"file_path": "/tmp/pre-hook.py"}, context, chain)

        # Should return error result
        assert result.success is False
        assert "cannot read their own hook scripts" in result.error.lower()
        assert "context efficiency" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_allows_reading_non_script_files(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        skill_with_script: Skill,
    ) -> None:
        """Should allow reading non-script files."""
        executor = ToolExecutor(registry)
        executor.activate_skill(skill_with_script)

        # Try to read a different file
        result = await executor.execute(
            "write", {"file_path": "/tmp/other-file.txt"}, context, chain
        )

        # Should succeed
        assert result.success is True

    @pytest.mark.asyncio
    async def test_restrictions_survive_exceptions(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        restricted_skill: Skill,
    ) -> None:
        """Should maintain restrictions even after tool execution errors."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        # First execution that gets blocked
        result1 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result1.success is False

        # Second execution should still be blocked (restrictions persist)
        result2 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result2.success is False
        assert "cannot use tool 'write'" in result2.error.lower()

    @pytest.mark.asyncio
    async def test_restrictions_cleared_after_deactivation(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        restricted_skill: Skill,
    ) -> None:
        """Should clear restrictions after skill deactivation."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        # Write tool is blocked
        result1 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result1.success is False

        # Deactivate skill
        executor.deactivate_skill("restricted-skill")

        # Write tool should now be allowed
        result2 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_nested_skills_use_top_skill_restrictions(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        unrestricted_skill: Skill,
        restricted_skill: Skill,
    ) -> None:
        """Should enforce restrictions from the top skill in stack."""
        executor = ToolExecutor(registry)

        # Activate unrestricted skill first (bottom of stack)
        executor.activate_skill(unrestricted_skill)

        # Write tool should be allowed
        result1 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result1.success is True

        # Activate restricted skill on top
        executor.activate_skill(restricted_skill)

        # Write tool should now be blocked (top skill has restrictions)
        result2 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result2.success is False

        # Deactivate top skill
        executor.deactivate_skill("restricted-skill")

        # Write tool should be allowed again (back to unrestricted skill)
        result3 = await executor.execute("write", {"input": "test"}, context, chain)
        assert result3.success is True


class TestToolExecutorAuditLogging:
    """Tests for audit logging in skill activation/deactivation."""

    def test_activate_skill_logs_activation(
        self, registry: ToolRegistry, restricted_skill: Skill, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log skill activation with metadata."""
        executor = ToolExecutor(registry)

        with caplog.at_level(logging.INFO):
            executor.activate_skill(restricted_skill)

        # Check that activation was logged
        assert any(
            "Skill activated: restricted-skill" in record.message for record in caplog.records
        )

    def test_deactivate_skill_logs_deactivation(
        self, registry: ToolRegistry, restricted_skill: Skill, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log skill deactivation."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        with caplog.at_level(logging.INFO):
            executor.deactivate_skill("restricted-skill")

        # Check that deactivation was logged
        assert any(
            "Skill deactivated: restricted-skill" in record.message for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_blocked_tool_execution_logs_warning(
        self,
        registry: ToolRegistry,
        context: ToolCallContext,
        chain: ReasoningChain,
        restricted_skill: Skill,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should log warning when tool execution is blocked."""
        executor = ToolExecutor(registry)
        executor.activate_skill(restricted_skill)

        with caplog.at_level(logging.WARNING):
            await executor.execute("write", {"input": "test"}, context, chain)

        # Check that blocking was logged
        assert any(
            "Skill restriction blocked tool execution" in record.message
            for record in caplog.records
        )
