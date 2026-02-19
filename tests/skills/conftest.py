"""Shared fixtures for skills integration tests."""

from pathlib import Path
from typing import Any

import pytest

from omniforge.agents.cot.chain import ChainStatus, ReasoningChain
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.skills.tool import SkillTool
from omniforge.tools import BaseTool, ToolCallContext, ToolDefinition, ToolResult
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for integration testing."""

    def __init__(self, name: str = "mock_tool") -> None:
        """Initialize mock tool with given name."""
        from omniforge.tools.base import ToolParameter

        self._definition = ToolDefinition(
            name=name,
            type="function",
            description=f"Mock {name} tool for testing",
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
        """Execute the mock tool successfully."""
        return ToolResult(
            success=True,
            result={"output": f"executed {self._definition.name}", "arguments": arguments},
            duration_ms=10,
        )


@pytest.fixture
def skill_directory(tmp_path: Path) -> Path:
    """Create a temporary skill directory structure with test skills.

    Creates:
        - unrestricted-skill: No tool restrictions
        - restricted-skill: Only allows read and grep tools
        - script-skill: Has pre-hook script and tool restrictions
        - debug-skill: Sample debug skill with priority

    Returns:
        Path to the skills directory
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create unrestricted skill
    unrestricted_dir = skills_dir / "unrestricted-skill"
    unrestricted_dir.mkdir()
    (unrestricted_dir / "SKILL.md").write_text(
        """---
name: unrestricted-skill
description: A skill with no tool restrictions
priority: 5
---

# Unrestricted Skill

This skill can use any tool available in the system.

## Instructions

You have full access to all tools.
"""
    )

    # Create restricted skill
    restricted_dir = skills_dir / "restricted-skill"
    restricted_dir.mkdir()
    (restricted_dir / "SKILL.md").write_text(
        """---
name: restricted-skill
description: A skill with tool restrictions
allowed-tools:
  - read
  - grep
priority: 10
---

# Restricted Skill

This skill can only use read and grep tools.

## Instructions

You are limited to reading files and searching content.
"""
    )

    # Create skill with scripts
    script_dir = skills_dir / "script-skill"
    script_dir.mkdir()
    scripts_subdir = script_dir / "scripts"
    scripts_subdir.mkdir()
    (script_dir / "SKILL.md").write_text(
        """---
name: script-skill
description: A skill with hook scripts
allowed-tools:
  - read
  - write
  - bash
hooks:
  pre: scripts/pre-hook.py
  post: scripts/post-hook.py
---

# Script Skill

This skill has pre and post hook scripts.

## Instructions

Scripts will run automatically. Do not try to read them.
"""
    )
    (scripts_subdir / "pre-hook.py").write_text(
        """#!/usr/bin/env python3
# Pre-hook script
print("Pre-hook executed")
"""
    )
    (scripts_subdir / "post-hook.py").write_text(
        """#!/usr/bin/env python3
# Post-hook script
print("Post-hook executed")
"""
    )

    # Create debug skill
    debug_dir = skills_dir / "debug-skill"
    debug_dir.mkdir()
    (debug_dir / "SKILL.md").write_text(
        """---
name: debug-skill
description: Debug agent behavior
allowed-tools:
  - read
  - write
  - grep
  - bash
priority: 8
tags:
  - debug
  - testing
---

# Debug Skill

Use this skill to debug agent behavior.

## Instructions

1. Read relevant files
2. Search for patterns
3. Write debug output
"""
    )

    return skills_dir


@pytest.fixture
def storage_config(skill_directory: Path) -> StorageConfig:
    """Create a configured StorageConfig for testing.

    Args:
        skill_directory: Temporary skill directory fixture

    Returns:
        Configured StorageConfig instance
    """
    return StorageConfig(project_path=skill_directory)


@pytest.fixture
def skill_loader(storage_config: StorageConfig) -> SkillLoader:
    """Create and initialize a SkillLoader for testing.

    Args:
        storage_config: Configured storage config fixture

    Returns:
        SkillLoader with built index
    """
    loader = SkillLoader(storage_config)
    loader.build_index()
    return loader


@pytest.fixture
def skill_tool(skill_loader: SkillLoader) -> SkillTool:
    """Create a configured SkillTool for testing.

    Args:
        skill_loader: Initialized skill loader fixture

    Returns:
        SkillTool instance
    """
    return SkillTool(skill_loader, timeout_ms=5000)


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a tool registry with mock tools for testing.

    Returns:
        ToolRegistry with read, write, grep, and bash tools
    """
    registry = ToolRegistry()
    registry.register(MockTool("read"))
    registry.register(MockTool("write"))
    registry.register(MockTool("grep"))
    registry.register(MockTool("bash"))
    return registry


@pytest.fixture
def executor_with_skills(tool_registry: ToolRegistry) -> ToolExecutor:
    """Create a ToolExecutor with skill support for testing.

    Args:
        tool_registry: Tool registry with mock tools

    Returns:
        ToolExecutor instance ready for skill integration testing
    """
    return ToolExecutor(tool_registry)


@pytest.fixture
def tool_context() -> ToolCallContext:
    """Create a test tool call context.

    Returns:
        ToolCallContext with test IDs
    """
    return ToolCallContext(
        correlation_id="test-correlation-123",
        task_id="test-task-456",
        agent_id="test-agent-789",
        tenant_id="test-tenant-001",
        chain_id="test-chain-111",
    )


@pytest.fixture
def reasoning_chain() -> ReasoningChain:
    """Create a test reasoning chain.

    Returns:
        ReasoningChain in RUNNING status
    """
    return ReasoningChain(
        task_id="test-task-456",
        agent_id="test-agent-789",
        tenant_id="test-tenant-001",
        status=ChainStatus.RUNNING,
    )
