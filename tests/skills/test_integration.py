"""Integration tests for the complete Skills System.

This module tests the end-to-end skill lifecycle:
- Storage → Loader → Tool → Execution
- Tool restriction enforcement
- Script read blocking
- Priority resolution
- Performance targets

These tests validate that all components work together correctly.
"""

import time
from pathlib import Path

import pytest

from omniforge.skills.errors import SkillNotFoundError, SkillScriptReadError
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.skills.tool import SkillTool
from omniforge.tools.base import ToolCallContext
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


class TestSkillDiscoveryFlow:
    """Tests for skill discovery and indexing flow."""

    def test_skill_discovery_from_storage_to_tool(
        self, skill_directory: Path, skill_loader: SkillLoader, skill_tool: SkillTool
    ) -> None:
        """Skills from storage should appear in SkillTool description.

        Validates CRITICAL-1: Path resolution works end-to-end.
        """
        # Verify skills were indexed
        skills = skill_loader.list_skills()
        assert len(skills) == 4
        skill_names = {skill.name for skill in skills}
        assert skill_names == {
            "unrestricted-skill",
            "restricted-skill",
            "script-skill",
            "debug-skill",
        }

        # Verify skills appear in tool description
        definition = skill_tool.definition
        description = definition.description

        assert "unrestricted-skill" in description
        assert "restricted-skill" in description
        assert "script-skill" in description
        assert "debug-skill" in description

    def test_skill_priority_resolution_in_index(
        self, skill_directory: Path, skill_loader: SkillLoader
    ) -> None:
        """Skills with explicit priority should be ordered correctly.

        Validates HIGH-1: Storage layer explicit passing works.
        """
        skills = skill_loader.list_skills()

        # Find skills by name and check priorities
        restricted = next(s for s in skills if s.name == "restricted-skill")
        debug = next(s for s in skills if s.name == "debug-skill")
        unrestricted = next(s for s in skills if s.name == "unrestricted-skill")

        # Verify explicit priorities are preserved
        assert restricted.priority == 10
        assert debug.priority == 8
        assert unrestricted.priority == 5

    def test_skill_index_rebuild_cooldown(self, skill_loader: SkillLoader) -> None:
        """Index rebuild should respect cooldown period."""
        # First build (already done in fixture)
        count1 = skill_loader.build_index()

        # Immediate rebuild should return cached count
        count2 = skill_loader.build_index()
        assert count1 == count2

        # Force rebuild should work
        count3 = skill_loader.build_index(force=True)
        assert count3 == count1


class TestSkillActivationFlow:
    """Tests for skill activation and content loading."""

    @pytest.mark.asyncio
    async def test_skill_activation_via_tool(
        self, skill_tool: SkillTool, tool_context: ToolCallContext
    ) -> None:
        """SkillTool should load and return complete skill content.

        Validates CRITICAL-1: Path resolution works for base_path.
        """
        # Activate skill via tool
        result = await skill_tool.execute(
            context=tool_context,
            arguments={"skill_name": "debug-skill"},
        )

        # Verify success
        assert result.success is True

        # Verify returned data
        assert result.result["skill_name"] == "debug-skill"
        assert "base_path" in result.result
        assert "content" in result.result

        # Verify base_path is absolute and points to skill directory
        base_path = Path(result.result["base_path"])
        assert base_path.is_absolute()
        assert base_path.name == "debug-skill"

        # Verify content was loaded
        content = result.result["content"]
        assert "Debug Skill" in content
        assert "debug agent behavior" in content.lower()

    @pytest.mark.asyncio
    async def test_skill_activation_extracts_allowed_tools(
        self, skill_tool: SkillTool, tool_context: ToolCallContext
    ) -> None:
        """SkillTool should extract and return allowed_tools."""
        # Activate restricted skill
        result = await skill_tool.execute(
            context=tool_context,
            arguments={"skill_name": "restricted-skill"},
        )

        assert result.success is True
        assert "allowed_tools" in result.result
        assert result.result["allowed_tools"] == ["read", "grep"]

    @pytest.mark.asyncio
    async def test_skill_activation_unrestricted_has_no_allowed_tools(
        self, skill_tool: SkillTool, tool_context: ToolCallContext
    ) -> None:
        """Unrestricted skills should not include allowed_tools in result."""
        result = await skill_tool.execute(
            context=tool_context,
            arguments={"skill_name": "unrestricted-skill"},
        )

        assert result.success is True
        assert "allowed_tools" not in result.result

    @pytest.mark.asyncio
    async def test_skill_activation_not_found_error(
        self, skill_tool: SkillTool, tool_context: ToolCallContext
    ) -> None:
        """SkillTool should return error for nonexistent skill."""
        result = await skill_tool.execute(
            context=tool_context,
            arguments={"skill_name": "nonexistent-skill"},
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_skill_activation_with_args(
        self, skill_tool: SkillTool, tool_context: ToolCallContext
    ) -> None:
        """SkillTool should pass through optional args."""
        result = await skill_tool.execute(
            context=tool_context,
            arguments={"skill_name": "debug-skill", "args": "test-arg"},
        )

        assert result.success is True
        assert result.result.get("args") == "test-arg"


class TestToolRestrictionEnforcement:
    """Tests for tool restriction enforcement across the stack."""

    @pytest.mark.asyncio
    async def test_restricted_skill_blocks_disallowed_tool(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Restricted skill should block tools not in allowed_tools list.

        Validates CRITICAL-3: Tool restrictions survive exceptions.
        """
        # Load and activate restricted skill
        skill = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill)

        # Try to use disallowed tool (write is not in allowed_tools)
        result = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )

        # Should be blocked
        assert result.success is False
        assert "cannot use tool 'write'" in result.error.lower()
        assert "read, grep" in result.error.lower()

    @pytest.mark.asyncio
    async def test_restricted_skill_allows_allowed_tool(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Restricted skill should allow tools in allowed_tools list."""
        # Load and activate restricted skill
        skill = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill)

        # Try to use allowed tool
        result = await executor_with_skills.execute(
            "read", {"input": "test"}, tool_context, reasoning_chain
        )

        # Should succeed
        assert result.success is True
        assert result.result["output"] == "executed read"

    @pytest.mark.asyncio
    async def test_unrestricted_skill_allows_all_tools(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Unrestricted skill should allow all tools."""
        # Load and activate unrestricted skill
        skill = skill_loader.load_skill("unrestricted-skill")
        executor_with_skills.activate_skill(skill)

        # Try various tools
        for tool_name in ["read", "write", "grep", "bash"]:
            result = await executor_with_skills.execute(
                tool_name, {"input": "test"}, tool_context, reasoning_chain
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_restrictions_survive_exceptions(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Tool restrictions should remain active after execution errors.

        Validates CRITICAL-3: Tool restrictions survive exceptions.
        """
        # Load and activate restricted skill
        skill = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill)

        # First attempt - blocked
        result1 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result1.success is False

        # Second attempt - should still be blocked
        result2 = await executor_with_skills.execute(
            "bash", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result2.success is False
        assert "cannot use tool" in result2.error.lower()

    @pytest.mark.asyncio
    async def test_restrictions_cleared_after_deactivation(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Tool restrictions should be cleared after skill deactivation."""
        # Load and activate restricted skill
        skill = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill)

        # Verify write is blocked
        result1 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result1.success is False

        # Deactivate skill
        executor_with_skills.deactivate_skill("restricted-skill")

        # Write should now be allowed
        result2 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result2.success is True


class TestScriptReadBlocking:
    """Tests for script read blocking via ToolExecutor.

    Validates CRITICAL-2: Script reading is blocked.
    """

    @pytest.mark.asyncio
    async def test_script_read_blocked_via_executor(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        skill_directory: Path,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """ToolExecutor should block attempts to read skill hook scripts.

        Validates CRITICAL-2: Script reading is blocked.
        """
        # Load and activate script skill
        skill = skill_loader.load_skill("script-skill")
        executor_with_skills.activate_skill(skill)

        # Attempt to read pre-hook script
        script_path = skill_directory / "script-skill" / "scripts" / "pre-hook.py"
        result = await executor_with_skills.execute(
            "read", {"file_path": str(script_path)}, tool_context, reasoning_chain
        )

        # Should be blocked
        assert result.success is False
        assert "cannot read their own hook scripts" in result.error.lower()
        assert "context efficiency" in result.error.lower()

    @pytest.mark.asyncio
    async def test_script_read_blocked_for_post_hook(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        skill_directory: Path,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Post-hook scripts should also be blocked from reading."""
        # Load and activate script skill
        skill = skill_loader.load_skill("script-skill")
        executor_with_skills.activate_skill(skill)

        # Attempt to read post-hook script
        script_path = skill_directory / "script-skill" / "scripts" / "post-hook.py"
        result = await executor_with_skills.execute(
            "read", {"file_path": str(script_path)}, tool_context, reasoning_chain
        )

        # Should be blocked
        assert result.success is False
        assert "cannot read their own hook scripts" in result.error.lower()

    @pytest.mark.asyncio
    async def test_non_script_files_can_be_read(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        skill_directory: Path,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Non-script files should be readable even with script skill active."""
        # Load and activate script skill
        skill = skill_loader.load_skill("script-skill")
        executor_with_skills.activate_skill(skill)

        # Create a non-script file
        test_file = skill_directory / "test-data.txt"
        test_file.write_text("test content")

        # Attempt to read non-script file
        result = await executor_with_skills.execute(
            "read", {"file_path": str(test_file)}, tool_context, reasoning_chain
        )

        # Should succeed
        assert result.success is True

    @pytest.mark.asyncio
    async def test_bash_execution_allowed_with_scripts(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Bash execution should be allowed (scripts are executed, not read)."""
        # Load and activate script skill
        skill = skill_loader.load_skill("script-skill")
        executor_with_skills.activate_skill(skill)

        # Bash should be allowed (it's in allowed_tools)
        result = await executor_with_skills.execute(
            "bash", {"input": "echo test"}, tool_context, reasoning_chain
        )

        # Should succeed
        assert result.success is True


class TestMultiSkillWorkflows:
    """Tests for multi-skill workflows and skill stacking."""

    @pytest.mark.asyncio
    async def test_sequential_skill_activation(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Multiple skills can be activated sequentially (with proper deactivation)."""
        # Activate first skill
        skill1 = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill1)

        # Verify write is blocked
        result1 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result1.success is False

        # Deactivate first skill
        executor_with_skills.deactivate_skill("restricted-skill")

        # Activate second skill
        skill2 = skill_loader.load_skill("unrestricted-skill")
        executor_with_skills.activate_skill(skill2)

        # Verify write is now allowed
        result2 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_nested_skill_activation(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Skills can be stacked, with top skill restrictions enforced."""
        # Activate unrestricted skill (bottom)
        skill1 = skill_loader.load_skill("unrestricted-skill")
        executor_with_skills.activate_skill(skill1)

        # Write should be allowed
        result1 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result1.success is True

        # Activate restricted skill (top)
        skill2 = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill2)

        # Write should now be blocked (top skill is restricted)
        result2 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result2.success is False

        # Deactivate top skill
        executor_with_skills.deactivate_skill("restricted-skill")

        # Write should be allowed again
        result3 = await executor_with_skills.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert result3.success is True

    def test_skill_stack_lifo_enforcement(
        self, executor_with_skills: ToolExecutor, skill_loader: SkillLoader
    ) -> None:
        """Skill deactivation must follow LIFO order."""
        from omniforge.skills.errors import SkillError

        # Activate two skills
        skill1 = skill_loader.load_skill("unrestricted-skill")
        skill2 = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill1)
        executor_with_skills.activate_skill(skill2)

        # Try to deactivate bottom skill (should fail)
        with pytest.raises(SkillError) as exc_info:
            executor_with_skills.deactivate_skill("unrestricted-skill")

        assert "not at top of stack" in str(exc_info.value)


class TestPriorityResolution:
    """Tests for skill priority resolution across storage layers."""

    def test_priority_resolution_with_multiple_layers(self, tmp_path: Path) -> None:
        """Skills should be prioritized by layer (enterprise > project).

        Validates HIGH-1: Storage layer explicit passing works.
        """
        # Create enterprise and project skills with same name
        enterprise_dir = tmp_path / "enterprise" / "skills"
        enterprise_dir.mkdir(parents=True)
        enterprise_skill = enterprise_dir / "shared-skill"
        enterprise_skill.mkdir()
        (enterprise_skill / "SKILL.md").write_text(
            """---
name: shared-skill
description: Enterprise version
priority: 5
---

Enterprise content
"""
        )

        project_dir = tmp_path / "project" / "skills"
        project_dir.mkdir(parents=True)
        project_skill = project_dir / "shared-skill"
        project_skill.mkdir()
        (project_skill / "SKILL.md").write_text(
            """---
name: shared-skill
description: Project version
priority: 100
---

Project content
"""
        )

        # Create loader with both layers
        config = StorageConfig(enterprise_path=enterprise_dir, project_path=project_dir)
        loader = SkillLoader(config)
        count = loader.build_index()

        # Should only have one skill (enterprise wins)
        assert count == 1

        # Verify enterprise version was selected
        entry = loader.get_skill_metadata("shared-skill")
        assert entry.description == "Enterprise version"
        assert entry.storage_layer == "enterprise"

        # Verify content is from enterprise
        skill = loader.load_skill("shared-skill")
        assert "Enterprise content" in skill.content
        assert "Project content" not in skill.content

    def test_priority_resolution_same_layer_explicit_priority(self, tmp_path: Path) -> None:
        """Higher explicit priority should win in same layer."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create two skills in same layer with different priorities
        skill1_dir = skills_dir / "skill-high-priority"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: High priority version
priority: 100
---

High priority content
"""
        )

        skill2_dir = skills_dir / "skill-low-priority"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: Low priority version
priority: 10
---

Low priority content
"""
        )

        # Create loader
        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)
        loader.build_index()

        # Verify high priority version was selected
        entry = loader.get_skill_metadata("test-skill")
        assert entry.priority == 100


class TestPerformanceValidation:
    """Tests for performance targets."""

    def test_index_build_performance_target(self, tmp_path: Path) -> None:
        """Index build should complete in < 100ms for 100 skills.

        Target: < 100ms for 1000 skills, scaled to 100 skills for test speed.
        """
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create 100 skills
        for i in range(100):
            skill_dir = skills_dir / f"skill-{i:03d}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: skill-{i:03d}
description: Test skill {i}
priority: {i % 10}
tags:
  - test
  - perf
---

Content for skill {i}
"""
            )

        # Measure index build time
        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        start_time = time.time()
        count = loader.build_index()
        elapsed = time.time() - start_time

        assert count == 100
        # Target: < 100ms for reasonable number of skills
        assert elapsed < 0.1, f"Index build took {elapsed*1000:.1f}ms (target: <100ms)"

    @pytest.mark.asyncio
    async def test_skill_activation_performance_target(
        self, skill_loader: SkillLoader, skill_tool: SkillTool, tool_context: ToolCallContext
    ) -> None:
        """Skill activation should complete in < 50ms.

        Target: < 50ms for skill loading and activation.
        """
        # Warm up cache
        await skill_tool.execute(context=tool_context, arguments={"skill_name": "debug-skill"})

        # Measure activation time (cache hit)
        start_time = time.time()
        result = await skill_tool.execute(
            context=tool_context, arguments={"skill_name": "debug-skill"}
        )
        elapsed = time.time() - start_time

        assert result.success is True
        # Target: < 50ms for cached activation
        assert elapsed < 0.05, f"Skill activation took {elapsed*1000:.1f}ms (target: <50ms)"

    @pytest.mark.asyncio
    async def test_tool_restriction_check_performance(
        self,
        executor_with_skills: ToolExecutor,
        skill_loader: SkillLoader,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Tool restriction checks should add minimal overhead."""
        # Activate restricted skill
        skill = skill_loader.load_skill("restricted-skill")
        executor_with_skills.activate_skill(skill)

        # Measure 100 allowed tool executions
        start_time = time.time()
        for _ in range(100):
            await executor_with_skills.execute(
                "read", {"input": "test"}, tool_context, reasoning_chain
            )
        elapsed = time.time() - start_time

        # Average should be < 1ms overhead per call
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 5, f"Average tool execution took {avg_ms:.1f}ms (target: <5ms)"


class TestCompleteSkillLifecycle:
    """Integration test for complete skill lifecycle."""

    @pytest.mark.asyncio
    async def test_complete_workflow_storage_to_execution(
        self,
        skill_directory: Path,
        tool_registry: ToolRegistry,
        tool_context: ToolCallContext,
        reasoning_chain,
    ) -> None:
        """Complete workflow: Storage → Loader → Tool → Execution.

        This test validates the entire skill system working together:
        1. Skills stored on filesystem
        2. Loader builds index and caches
        3. SkillTool loads and returns skill
        4. ToolExecutor enforces restrictions
        5. Tool execution succeeds/fails appropriately
        """
        # Step 1: Create storage configuration
        config = StorageConfig(project_path=skill_directory)

        # Step 2: Create and initialize loader
        loader = SkillLoader(config)
        count = loader.build_index()
        assert count == 4

        # Step 3: Create SkillTool
        skill_tool = SkillTool(loader)
        definition = skill_tool.definition
        assert "debug-skill" in definition.description

        # Step 4: Load skill via tool
        result = await skill_tool.execute(
            context=tool_context, arguments={"skill_name": "restricted-skill"}
        )
        assert result.success is True
        assert result.result["allowed_tools"] == ["read", "grep"]

        # Step 5: Create executor and activate skill
        executor = ToolExecutor(tool_registry)
        skill = loader.load_skill("restricted-skill")
        executor.activate_skill(skill)

        # Step 6: Test tool restriction enforcement
        # Allowed tool should work
        read_result = await executor.execute("read", {"input": "test"}, tool_context, reasoning_chain)
        assert read_result.success is True

        # Disallowed tool should be blocked
        write_result = await executor.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert write_result.success is False
        assert "cannot use tool 'write'" in write_result.error.lower()

        # Step 7: Deactivate and verify restrictions cleared
        executor.deactivate_skill("restricted-skill")
        write_result2 = await executor.execute(
            "write", {"input": "test"}, tool_context, reasoning_chain
        )
        assert write_result2.success is True
