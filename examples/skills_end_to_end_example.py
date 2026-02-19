"""End-to-End Skills System Example

This example demonstrates the complete skills workflow:
1. Creating a custom skill
2. Discovering available skills
3. Activating skills via SkillTool
4. Executing tools with skill restrictions
5. Managing skill lifecycle (activation/deactivation)

This is a practical example showing how to use the skills system in OmniForge.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.skills.tool import SkillTool
from omniforge.tasks.models import Task, TaskMessage, TaskState
from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType


# ============================================================================
# Step 1: Create Sample Skills
# ============================================================================


def create_sample_skills(skills_dir: Path) -> None:
    """Create sample skills for demonstration.

    Creates three skills:
    1. data-analyzer: Unrestricted skill for data analysis
    2. safe-researcher: Restricted to read-only operations
    3. code-helper: Skill with Python code generation focus
    """
    print("📁 Creating sample skills...")

    # Skill 1: Data Analyzer (Unrestricted)
    data_analyzer_dir = skills_dir / "data-analyzer"
    data_analyzer_dir.mkdir(parents=True)
    (data_analyzer_dir / "SKILL.md").write_text(
        """---
name: data-analyzer
description: Analyze data files and generate insights with full tool access
priority: 10
tags:
  - data
  - analysis
---

# Data Analyzer Skill

You are a data analysis expert. Your role is to:

1. Read data files in various formats
2. Perform statistical analysis
3. Generate insights and visualizations
4. Create summary reports

## Capabilities

- Read CSV, JSON, and text files
- Perform data validation
- Calculate statistics (mean, median, mode, etc.)
- Identify patterns and anomalies

## Output Format

Provide analysis results in a structured format:
- Summary statistics
- Key findings
- Recommendations

Use all available tools to complete the analysis effectively.
"""
    )

    # Skill 2: Safe Researcher (Restricted)
    safe_researcher_dir = skills_dir / "safe-researcher"
    safe_researcher_dir.mkdir(parents=True)
    (safe_researcher_dir / "SKILL.md").write_text(
        """---
name: safe-researcher
description: Research information with read-only access for safety
allowed-tools:
  - read
  - grep
  - glob
priority: 8
tags:
  - research
  - safe
  - read-only
---

# Safe Researcher Skill

You are a research assistant with read-only access. Your role is to:

1. Search for information in existing files
2. Find patterns and extract insights
3. Summarize findings
4. Provide references to source files

## Tool Restrictions

You can ONLY use:
- `read`: Read file contents
- `grep`: Search for patterns
- `glob`: Find files by pattern

You CANNOT:
- Write or modify files
- Execute bash commands
- Delete anything

## Best Practices

- Always cite sources (file paths and line numbers)
- Verify information before reporting
- Provide context with quotes
- Be thorough but concise
"""
    )

    # Skill 3: Code Helper (Unrestricted, code-focused)
    code_helper_dir = skills_dir / "code-helper"
    code_helper_dir.mkdir(parents=True)

    # Create a sample reference file
    (code_helper_dir / "python-best-practices.md").write_text(
        """# Python Best Practices

- Use type hints for function parameters and return values
- Follow PEP 8 style guidelines
- Write docstrings for all public functions
- Use f-strings for string formatting
- Prefer list comprehensions for simple transformations
"""
    )

    (code_helper_dir / "SKILL.md").write_text(
        """---
name: code-helper
description: Help with Python code generation and best practices
priority: 9
tags:
  - python
  - code-generation
  - programming
---

# Code Helper Skill

You are an expert Python developer. Your role is to:

1. Generate clean, well-documented Python code
2. Follow best practices and PEP 8 guidelines
3. Use type hints and proper error handling
4. Write comprehensive docstrings

## Reference Materials

See `python-best-practices.md` in this skill directory for coding guidelines.

## Code Style

Always:
- Use type hints: `def func(x: int) -> str:`
- Add docstrings with Args, Returns, Raises sections
- Handle errors gracefully
- Write readable, self-documenting code

## Example

```python
def calculate_average(numbers: list[float]) -> float:
    \"\"\"Calculate the average of a list of numbers.

    Args:
        numbers: List of numeric values

    Returns:
        The average of all numbers

    Raises:
        ValueError: If the list is empty
    \"\"\"
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")
    return sum(numbers) / len(numbers)
```
"""
    )

    print("✓ Created 3 sample skills:")
    print("  - data-analyzer (unrestricted)")
    print("  - safe-researcher (read-only)")
    print("  - code-helper (Python code focus)")


# ============================================================================
# Step 2: Create Mock Tools for Testing
# ============================================================================


class MockReadTool(BaseTool):
    """Mock read tool for demonstration."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read",
            type=ToolType.FILE_READ,
            description="Read file contents",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Path to file",
                    required=True,
                )
            ],
        )

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        file_path = arguments.get("file_path", "")
        return ToolResult(
            success=True,
            result={
                "content": f"[Mock] Contents of {file_path}:\nSample data line 1\nSample data line 2"
            },
            duration_ms=10,
        )


class MockWriteTool(BaseTool):
    """Mock write tool for demonstration."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write",
            type=ToolType.FILE_WRITE,
            description="Write to file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Path to file",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="Content to write",
                    required=True,
                ),
            ],
        )

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        file_path = arguments.get("file_path", "")
        return ToolResult(
            success=True,
            result={"message": f"[Mock] Successfully wrote to {file_path}"},
            duration_ms=15,
        )


class MockGrepTool(BaseTool):
    """Mock grep tool for demonstration."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="grep",
            type=ToolType.GREP,
            description="Search for patterns in files",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type=ParameterType.STRING,
                    description="Search pattern",
                    required=True,
                ),
                ToolParameter(
                    name="path",
                    type=ParameterType.STRING,
                    description="Path to search",
                    required=False,
                ),
            ],
        )

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        pattern = arguments.get("pattern", "")
        return ToolResult(
            success=True,
            result={
                "matches": [
                    "file1.py:10: matching line with pattern",
                    "file2.py:25: another match here",
                ]
            },
            duration_ms=20,
        )


class MockGlobTool(BaseTool):
    """Mock glob tool for demonstration."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="glob",
            type=ToolType.GLOB,
            description="Find files by pattern",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type=ParameterType.STRING,
                    description="File pattern",
                    required=True,
                )
            ],
        )

    async def execute(self, context: ToolCallContext, arguments: dict) -> ToolResult:
        pattern = arguments.get("pattern", "")
        return ToolResult(
            success=True,
            result={"files": ["file1.py", "file2.py", "data.json"]},
            duration_ms=12,
        )


# ============================================================================
# Step 3: Main Demonstration
# ============================================================================


async def demonstrate_skills_workflow():
    """Run complete skills workflow demonstration."""

    print("\n" + "=" * 80)
    print(" OmniForge Skills System - End-to-End Example")
    print("=" * 80 + "\n")

    # Create temporary directory for skills
    with tempfile.TemporaryDirectory() as tmp_dir:
        skills_dir = Path(tmp_dir) / "skills"
        skills_dir.mkdir()

        # Step 1: Create sample skills
        create_sample_skills(skills_dir)

        # Step 2: Setup skill loader
        print("\n📚 Setting up skill loader...")
        config = StorageConfig(project_path=skills_dir)
        loader = SkillLoader(config)

        # Build skill index
        count = loader.build_index()
        print(f"✓ Indexed {count} skills\n")

        # Step 3: List available skills
        print("📋 Available Skills:")
        for skill_entry in loader.list_skills():
            print(f"  • {skill_entry.name}")
            print(f"    Description: {skill_entry.description}")
            print(f"    Priority: {skill_entry.priority}")
            print(f"    Tags: {', '.join(skill_entry.tags or [])}")
            print()

        # Step 4: Create SkillTool
        print("🔧 Creating SkillTool...")
        skill_tool = SkillTool(loader)
        definition = skill_tool.definition

        print(f"✓ Tool created: {definition.name}")
        print(f"  Description preview: {definition.description[:100]}...")
        print()

        # Step 5: Create tool registry with mock tools + skill tool
        print("🛠️  Setting up tool registry...")
        registry = ToolRegistry()
        registry.register(MockReadTool())
        registry.register(MockWriteTool())
        registry.register(MockGrepTool())
        registry.register(MockGlobTool())
        registry.register(skill_tool)

        tool_names = registry.list_tools()
        print(f"✓ Registered {len(tool_names)} tools:")
        for tool_name in tool_names:
            print(f"  • {tool_name}")
        print()

        # Step 6: Create tool context
        context = ToolCallContext(
            correlation_id="demo-correlation-1",
            task_id="demo-task-1",
            agent_id="skill-demo-agent",
        )

        # ====================================================================
        # DEMO 1: Unrestricted Skill (data-analyzer)
        # ====================================================================

        print("\n" + "=" * 80)
        print(" DEMO 1: Unrestricted Skill - Data Analyzer")
        print("=" * 80 + "\n")

        print("🔓 Activating unrestricted 'data-analyzer' skill...")
        result = await skill_tool.execute(
            context=context, arguments={"skill_name": "data-analyzer"}
        )

        if result.success:
            print("✓ Skill activated successfully!")
            print(f"  Skill name: {result.result['skill_name']}")
            print(f"  Base path: {result.result['base_path']}")
            print(f"  Content preview: {result.result['content'][:100]}...")
            print(f"  Tool restrictions: None (unrestricted)")

            # Load and activate skill in executor
            skill = loader.load_skill("data-analyzer")
            print(f"\n  Skill allows all tools: {skill.metadata.allowed_tools is None}")
        else:
            print(f"✗ Failed: {result.error}")

        # ====================================================================
        # DEMO 2: Restricted Skill (safe-researcher)
        # ====================================================================

        print("\n" + "=" * 80)
        print(" DEMO 2: Restricted Skill - Safe Researcher")
        print("=" * 80 + "\n")

        print("🔒 Activating restricted 'safe-researcher' skill...")
        result = await skill_tool.execute(
            context=context, arguments={"skill_name": "safe-researcher"}
        )

        if result.success:
            print("✓ Skill activated successfully!")
            print(f"  Skill name: {result.result['skill_name']}")
            print(f"  Base path: {result.result['base_path']}")
            print(f"  Allowed tools: {result.result['allowed_tools']}")
            print(
                f"  Content preview: {result.result['content'][:150].replace(chr(10), ' ')}..."
            )

            # Load skill for restriction testing
            skill = loader.load_skill("safe-researcher")
            print(f"\n  Tool restrictions active: {skill.metadata.allowed_tools}")
        else:
            print(f"✗ Failed: {result.error}")

        # ====================================================================
        # DEMO 3: Skill with Reference Files (code-helper)
        # ====================================================================

        print("\n" + "=" * 80)
        print(" DEMO 3: Skill with Reference Files - Code Helper")
        print("=" * 80 + "\n")

        print("📝 Activating 'code-helper' skill with reference files...")
        result = await skill_tool.execute(
            context=context, arguments={"skill_name": "code-helper"}
        )

        if result.success:
            print("✓ Skill activated successfully!")
            print(f"  Skill name: {result.result['skill_name']}")
            base_path = Path(result.result["base_path"])
            print(f"  Base path: {base_path}")

            # Show reference files
            ref_file = base_path / "python-best-practices.md"
            if ref_file.exists():
                print(f"\n  📄 Reference file found: {ref_file.name}")
                print(f"     Absolute path: {ref_file}")
                print("     Agent can read this file using the base_path!")

            print(f"\n  Content preview: {result.result['content'][:150]}...")
        else:
            print(f"✗ Failed: {result.error}")

        # ====================================================================
        # DEMO 4: Error Handling (Non-existent skill)
        # ====================================================================

        print("\n" + "=" * 80)
        print(" DEMO 4: Error Handling - Non-existent Skill")
        print("=" * 80 + "\n")

        print("❌ Attempting to activate non-existent skill...")
        result = await skill_tool.execute(
            context=context, arguments={"skill_name": "non-existent-skill"}
        )

        if not result.success:
            print(f"✓ Correctly handled error!")
            print(f"  Error message: {result.error}")
            print(f"  Duration: {result.duration_ms}ms")
        else:
            print("✗ Unexpected success")

        # ====================================================================
        # DEMO 5: Skill with Arguments
        # ====================================================================

        print("\n" + "=" * 80)
        print(" DEMO 5: Skill Activation with Arguments")
        print("=" * 80 + "\n")

        print("⚙️  Activating skill with custom arguments...")
        result = await skill_tool.execute(
            context=context,
            arguments={
                "skill_name": "data-analyzer",
                "args": "format=json output=detailed",
            },
        )

        if result.success:
            print("✓ Skill activated with arguments!")
            print(f"  Skill name: {result.result['skill_name']}")
            print(f"  Arguments passed: {result.result.get('args', 'None')}")
        else:
            print(f"✗ Failed: {result.error}")

        # ====================================================================
        # DEMO 6: Tool Execution with ToolExecutor
        # ====================================================================

        print("\n" + "=" * 80)
        print(" DEMO 6: Tool Restriction Enforcement with ToolExecutor")
        print("=" * 80 + "\n")

        from omniforge.agents.cot.chain import ReasoningChain
        from omniforge.tools.executor import ToolExecutor

        # Create executor
        executor = ToolExecutor(registry)

        # Create a reasoning chain for tracking tool calls
        chain = ReasoningChain(
            task_id=context.task_id,
            agent_id=context.agent_id,
        )

        # Activate safe-researcher skill (restricted)
        safe_researcher_skill = loader.load_skill("safe-researcher")
        executor.activate_skill(safe_researcher_skill)

        print("🔒 Activated 'safe-researcher' skill with restrictions")
        print(f"  Allowed tools: {safe_researcher_skill.metadata.allowed_tools}\n")

        # Test 1: Try allowed tool (read)
        print("Test 1: Using allowed tool 'read'...")
        read_result = await executor.execute(
            "read",
            {"file_path": "data.txt"},
            context,
            chain,
        )
        if read_result.success:
            print(f"  ✓ Success: {read_result.result.get('content', '')[:50]}...")
        else:
            print(f"  ✗ Failed: {read_result.error}")

        # Test 2: Try disallowed tool (write)
        print("\nTest 2: Using disallowed tool 'write'...")
        write_result = await executor.execute(
            "write",
            {"file_path": "output.txt", "content": "test"},
            context,
            chain,
        )
        if write_result.success:
            print(f"  ✗ Unexpected success: {write_result.result}")
        else:
            print(f"  ✓ Correctly blocked: {write_result.error[:80]}...")

        # Test 3: Deactivate skill and try again
        print("\nTest 3: Deactivate skill and retry 'write'...")
        executor.deactivate_skill("safe-researcher")
        print("  Deactivated skill")

        write_result2 = await executor.execute(
            "write",
            {"file_path": "output.txt", "content": "test"},
            context,
            chain,
        )
        if write_result2.success:
            print(f"  ✓ Success after deactivation: {write_result2.result.get('message', '')}")
        else:
            print(f"  ✗ Failed: {write_result2.error}")

        # ====================================================================
        # Summary
        # ====================================================================

        print("\n" + "=" * 80)
        print(" Summary: Skills System Features Demonstrated")
        print("=" * 80 + "\n")

        print("✅ Features Demonstrated:")
        print("  1. ✓ Skill creation with YAML frontmatter")
        print("  2. ✓ Skill discovery and indexing")
        print("  3. ✓ Progressive disclosure (metadata → full content)")
        print("  4. ✓ Tool restriction enforcement (allowed-tools)")
        print("  5. ✓ Base path resolution for reference files")
        print("  6. ✓ Priority-based conflict resolution")
        print("  7. ✓ Error handling and suggestions")
        print("  8. ✓ Argument passing to skills")
        print("  9. ✓ ToolExecutor integration with restrictions")
        print(" 10. ✓ Skill activation/deactivation lifecycle")
        print()

        print("📖 Next Steps:")
        print("  • Create your own skills in .claude/skills/ directory")
        print("  • Use SkillTool in your agents via ToolRegistry")
        print("  • Implement skill activation in your reasoning logic")
        print("  • Test tool restrictions with ToolExecutor")
        print()

        print("📚 Key Classes:")
        print("  • StorageConfig: Configure skill storage paths")
        print("  • SkillLoader: Load and cache skills")
        print("  • SkillTool: Tool for discovering/activating skills")
        print("  • ToolExecutor: Enforce skill tool restrictions")
        print()


# ============================================================================
# Run the demonstration
# ============================================================================


async def main():
    """Main entry point."""
    try:
        await demonstrate_skills_workflow()
        print("=" * 80)
        print(" ✅ Example completed successfully!")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
