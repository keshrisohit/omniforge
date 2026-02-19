"""Unit tests for SkillTool class."""

from pathlib import Path

import pytest

from omniforge.skills.errors import SkillNotFoundError
from omniforge.skills.loader import SkillLoader
from omniforge.skills.models import Skill, SkillIndexEntry, SkillMetadata
from omniforge.skills.storage import StorageConfig
from omniforge.skills.tool import SkillTool
from omniforge.tools.base import ToolCallContext
from omniforge.tools.types import ToolType


class MockSkillLoader:
    """Mock SkillLoader for testing without file system dependencies."""

    def __init__(self) -> None:
        """Initialize mock loader with test data."""
        self._skills: dict[str, Skill] = {}
        self._index: list[SkillIndexEntry] = []

    def add_skill(
        self,
        name: str,
        description: str,
        content: str,
        base_path: str = "/test/skills",
        allowed_tools: list[str] | None = None,
    ) -> None:
        """Add a skill to the mock loader."""
        metadata = SkillMetadata(
            name=name,
            description=description,
            allowed_tools=allowed_tools,
        )

        skill = Skill(
            metadata=metadata,
            content=content,
            path=Path(f"{base_path}/{name}/SKILL.md"),
            base_path=Path(base_path) / name,
            storage_layer="test",
        )

        self._skills[name] = skill
        self._index.append(
            SkillIndexEntry(
                name=name,
                description=description,
                path=Path(f"{base_path}/{name}/SKILL.md"),
                storage_layer="test",
            )
        )

    def list_skills(self) -> list[SkillIndexEntry]:
        """Return list of available skills."""
        return self._index

    def load_skill(self, name: str) -> Skill:
        """Load a skill by name."""
        if name not in self._skills:
            raise SkillNotFoundError(name)
        return self._skills[name]


class TestSkillToolInitialization:
    """Tests for SkillTool initialization."""

    def test_init_with_default_timeout(self) -> None:
        """SkillTool should initialize with default timeout."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        assert tool._skill_loader is loader
        assert tool._timeout_ms == 30000

    def test_init_with_custom_timeout(self) -> None:
        """SkillTool should initialize with custom timeout."""
        loader = MockSkillLoader()
        tool = SkillTool(loader, timeout_ms=5000)

        assert tool._timeout_ms == 5000


class TestSkillToolDefinition:
    """Tests for SkillTool definition property."""

    def test_definition_basic_properties(self) -> None:
        """Tool definition should have correct name, type, and parameters."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        definition = tool.definition

        assert definition.name == "skill"
        assert definition.type == ToolType.SKILL
        assert definition.timeout_ms == 30000
        assert len(definition.parameters) == 2

    def test_definition_parameters(self) -> None:
        """Tool definition should have skill_name and args parameters."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        definition = tool.definition
        params_by_name = {p.name: p for p in definition.parameters}

        # Check skill_name parameter
        assert "skill_name" in params_by_name
        skill_name_param = params_by_name["skill_name"]
        assert skill_name_param.required is True
        assert "skill to activate" in skill_name_param.description.lower()

        # Check args parameter
        assert "args" in params_by_name
        args_param = params_by_name["args"]
        assert args_param.required is False
        assert "argument" in args_param.description.lower()

    def test_definition_description_no_skills(self) -> None:
        """Tool description should indicate when no skills are available."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        definition = tool.definition
        description = definition.description

        assert "No skills currently available" in description
        assert "PROGRESSIVE DISCLOSURE" in description
        assert "PATH RESOLUTION" in description

    def test_definition_description_with_skills(self) -> None:
        """Tool description should list available skills."""
        loader = MockSkillLoader()
        loader.add_skill("debug-agent", "Debug agent execution", "Debug content")
        loader.add_skill("test-runner", "Run automated tests", "Test content")

        tool = SkillTool(loader)
        definition = tool.definition
        description = definition.description

        # Check skills are listed
        assert "debug-agent: Debug agent execution" in description
        assert "test-runner: Run automated tests" in description

        # Check structure sections are present
        assert "PROGRESSIVE DISCLOSURE" in description
        assert "AVAILABLE SKILLS" in description
        assert "USAGE" in description
        assert "PATH RESOLUTION" in description

    def test_definition_regenerated_dynamically(self) -> None:
        """Tool definition should be regenerated to reflect skill changes."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        # First access - no skills
        definition1 = tool.definition
        assert "No skills currently available" in definition1.description

        # Add a skill
        loader.add_skill("new-skill", "Newly added skill", "Content")

        # Second access - should include new skill
        definition2 = tool.definition
        assert "new-skill: Newly added skill" in definition2.description


class TestSkillToolExecution:
    """Tests for SkillTool execution."""

    @pytest.fixture
    def context(self) -> ToolCallContext:
        """Create a test execution context."""
        return ToolCallContext(
            correlation_id="test-corr-1",
            task_id="test-task-1",
            agent_id="test-agent-1",
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, context: ToolCallContext) -> None:
        """Successful skill loading should return complete skill data."""
        loader = MockSkillLoader()
        loader.add_skill(
            name="test-skill",
            description="Test skill description",
            content="This is the skill content.",
            base_path="/test/skills",
            allowed_tools=["read", "write"],
        )

        tool = SkillTool(loader)
        result = await tool.execute(
            context=context,
            arguments={"skill_name": "test-skill"},
        )

        assert result.success is True
        assert result.error is None
        assert result.result is not None

        # Check result data
        assert result.result["skill_name"] == "test-skill"
        assert result.result["base_path"] == "/test/skills/test-skill"
        assert result.result["content"] == "This is the skill content."
        assert result.result["allowed_tools"] == ["read", "write"]

    @pytest.mark.asyncio
    async def test_execute_success_no_allowed_tools(self, context: ToolCallContext) -> None:
        """Skill without allowed_tools should not include that field in result."""
        loader = MockSkillLoader()
        loader.add_skill(
            name="unrestricted-skill",
            description="Skill with no tool restrictions",
            content="Skill content here.",
        )

        tool = SkillTool(loader)
        result = await tool.execute(
            context=context,
            arguments={"skill_name": "unrestricted-skill"},
        )

        assert result.success is True
        assert "allowed_tools" not in result.result

    @pytest.mark.asyncio
    async def test_execute_with_args(self, context: ToolCallContext) -> None:
        """Arguments should be passed through in the result."""
        loader = MockSkillLoader()
        loader.add_skill("test-skill", "Test description", "Test content")

        tool = SkillTool(loader)
        result = await tool.execute(
            context=context,
            arguments={"skill_name": "test-skill", "args": "custom-arg-value"},
        )

        assert result.success is True
        assert result.result["args"] == "custom-arg-value"

    @pytest.mark.asyncio
    async def test_execute_missing_skill_name(self, context: ToolCallContext) -> None:
        """Execution without skill_name should return error."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        result = await tool.execute(context=context, arguments={})

        assert result.success is False
        assert "skill_name is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_empty_skill_name(self, context: ToolCallContext) -> None:
        """Execution with empty skill_name should return error."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        result = await tool.execute(
            context=context,
            arguments={"skill_name": "   "},
        )

        assert result.success is False
        assert "skill_name is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(self, context: ToolCallContext) -> None:
        """Execution with non-existent skill should return helpful error."""
        loader = MockSkillLoader()
        loader.add_skill("real-skill", "A real skill", "Content")

        tool = SkillTool(loader)
        result = await tool.execute(
            context=context,
            arguments={"skill_name": "fake-skill"},
        )

        assert result.success is False
        assert "fake-skill" in result.error
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_skill_not_found_with_suggestion(self, context: ToolCallContext) -> None:
        """Error for non-existent skill should suggest similar names."""
        loader = MockSkillLoader()
        loader.add_skill("debug-agent", "Debug functionality", "Content")

        tool = SkillTool(loader)
        result = await tool.execute(
            context=context,
            arguments={"skill_name": "debag-agent"},  # Typo
        )

        assert result.success is False
        assert "not found" in result.error.lower()
        assert "debug-agent" in result.error  # Should suggest correct name

    @pytest.mark.asyncio
    async def test_execute_duration_tracking(self, context: ToolCallContext) -> None:
        """Execution should track duration in milliseconds."""
        loader = MockSkillLoader()
        loader.add_skill("test-skill", "Test", "Content")

        tool = SkillTool(loader)
        result = await tool.execute(
            context=context,
            arguments={"skill_name": "test-skill"},
        )

        assert result.duration_ms >= 0
        assert result.duration_ms < 1000  # Should be very fast for mock

    @pytest.mark.asyncio
    async def test_execute_performance_target(self, context: ToolCallContext) -> None:
        """Skill activation should complete in under 50ms (NFR-2)."""
        loader = MockSkillLoader()
        loader.add_skill("perf-test", "Performance test", "Content")

        tool = SkillTool(loader)

        # Run multiple times to get reliable measurement
        durations = []
        for _ in range(5):
            result = await tool.execute(
                context=context,
                arguments={"skill_name": "perf-test"},
            )
            durations.append(result.duration_ms)

        # Average should be under 50ms
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 50, f"Average activation time {avg_duration}ms exceeds 50ms target"


class TestSkillToolSimilarityMatching:
    """Tests for _find_similar method."""

    def test_find_similar_exact_match(self) -> None:
        """Exact match should be returned."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        available = ["debug-agent", "test-runner"]
        result = tool._find_similar("debug-agent", available)

        assert result == "debug-agent"

    def test_find_similar_close_match(self) -> None:
        """Close match with typo should be found."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        available = ["debug-agent", "test-runner"]

        # Test various typos
        assert tool._find_similar("debag-agent", available) == "debug-agent"
        assert tool._find_similar("debug-agen", available) == "debug-agent"
        assert tool._find_similar("test-runer", available) == "test-runner"

    def test_find_similar_no_match_below_threshold(self) -> None:
        """Very different name should return None."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        available = ["debug-agent", "test-runner"]
        result = tool._find_similar("completely-different", available)

        assert result is None

    def test_find_similar_empty_available(self) -> None:
        """Empty available list should return None."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        result = tool._find_similar("any-name", [])

        assert result is None

    def test_find_similar_case_insensitive(self) -> None:
        """Similarity matching should be case insensitive."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        available = ["debug-agent"]
        result = tool._find_similar("DEBUG-AGENT", available)

        assert result == "debug-agent"

    def test_find_similar_best_match(self) -> None:
        """Should return the best match among multiple candidates."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        available = ["debug-agent", "debug-tool", "test-agent"]
        result = tool._find_similar("debug-agen", available)

        # "debug-agent" is closer than "debug-tool"
        assert result == "debug-agent"

    def test_find_similar_custom_threshold(self) -> None:
        """Custom threshold should be respected."""
        loader = MockSkillLoader()
        tool = SkillTool(loader)

        available = ["debug-agent"]

        # High threshold - no match
        result_high = tool._find_similar("debag", available, threshold=0.9)
        assert result_high is None

        # Low threshold - match
        result_low = tool._find_similar("debag", available, threshold=0.5)
        assert result_low == "debug-agent"


class TestSkillToolIntegration:
    """Integration tests with real SkillLoader (using temp directories)."""

    @pytest.fixture
    def temp_skill_dir(self, tmp_path: Path) -> Path:
        """Create temporary skill directory with test skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create test skill
        skill_dir = skills_dir / "test-integration"
        skill_dir.mkdir()

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-integration
description: Integration test skill
allowed-tools:
  - read
  - write
---

# Test Integration Skill

This is the skill content for integration testing.
"""
        )

        return skills_dir

    @pytest.mark.asyncio
    async def test_integration_with_real_loader(self, temp_skill_dir: Path) -> None:
        """SkillTool should work with real SkillLoader and filesystem."""
        # Use enterprise_path which has highest priority
        config = StorageConfig(enterprise_path=temp_skill_dir)
        loader = SkillLoader(config)

        # Build index to discover skills
        skill_count = loader.build_index()
        assert skill_count == 1, "Should have found 1 skill in temp directory"

        tool = SkillTool(loader)

        # Check definition includes skill
        definition = tool.definition
        assert "test-integration" in definition.description

        # Execute skill loading
        context = ToolCallContext(
            correlation_id="int-test-1",
            task_id="int-task-1",
            agent_id="int-agent-1",
        )

        result = await tool.execute(
            context=context,
            arguments={"skill_name": "test-integration"},
        )

        # Verify result
        assert result.success is True
        assert result.result["skill_name"] == "test-integration"
        assert "Test Integration Skill" in result.result["content"]
        assert result.result["allowed_tools"] == ["read", "write"]
        assert str(temp_skill_dir / "test-integration") in result.result["base_path"]


class TestSkillToolErrorHandling:
    """Tests for error handling in SkillTool."""

    @pytest.mark.asyncio
    async def test_execute_handles_loader_exception(self) -> None:
        """Unexpected exceptions from loader should be caught and returned as errors."""

        class FailingLoader:
            """Mock loader that raises unexpected exceptions."""

            def list_skills(self) -> list[SkillIndexEntry]:
                return []

            def load_skill(self, name: str) -> Skill:
                raise RuntimeError("Unexpected loader failure")

        tool = SkillTool(FailingLoader())  # type: ignore
        context = ToolCallContext(
            correlation_id="err-test-1",
            task_id="err-task-1",
            agent_id="err-agent-1",
        )

        result = await tool.execute(
            context=context,
            arguments={"skill_name": "any-skill"},
        )

        assert result.success is False
        assert "Failed to load skill" in result.error
        assert "Unexpected loader failure" in result.error
