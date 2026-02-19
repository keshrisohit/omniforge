"""Demo of selective truncation feature for tool results.

This example demonstrates how the Glob tool uses truncatable_fields
to preserve metadata while truncating large result lists to save context.
"""

import asyncio
from pathlib import Path

from omniforge.tools.base import ToolCallContext, ToolResult
from omniforge.tools.builtin.glob import GlobTool


async def main() -> None:
    """Demonstrate selective truncation of tool results."""
    # Create a GlobTool instance
    glob_tool = GlobTool(max_results=100)

    # Create execution context
    context = ToolCallContext(
        correlation_id="demo-corr-1",
        task_id="demo-task-1",
        agent_id="demo-agent-1",
    )

    # Execute glob search for Python files
    result = await glob_tool.execute(
        arguments={"pattern": "**/*.py", "base_path": str(Path.cwd())}, context=context
    )

    print("\n=== Original Result ===")
    print(f"Success: {result.success}")
    print(f"Match Count: {result.result['match_count']}")
    print(f"Pattern: {result.result['pattern']}")
    print(f"Base Path: {result.result['base_path']}")
    print(f"Number of matches returned: {len(result.result['matches'])}")
    print(f"Truncatable fields: {result.truncatable_fields}")

    # Demonstrate truncation
    truncated_result = result.truncate_for_context(max_items=5)

    print("\n=== Truncated Result (max_items=5) ===")
    print(f"Success: {truncated_result.success}")
    print(f"Match Count: {truncated_result.result['match_count']}")  # Preserved!
    print(f"Pattern: {truncated_result.result['pattern']}")  # Preserved!
    print(f"Base Path: {truncated_result.result['base_path']}")  # Preserved!
    print(f"Number of matches returned: {len(truncated_result.result['matches'])}")  # Truncated!

    if "matches_truncation_note" in truncated_result.result:
        print(f"Truncation Note: {truncated_result.result['matches_truncation_note']}")

    print("\n=== First 5 Matches ===")
    for i, match in enumerate(truncated_result.result["matches"][:5], 1):
        print(f"{i}. {match['name']} - {match['path']}")

    print("\n✓ Metadata preserved while matches truncated to save context!")


if __name__ == "__main__":
    asyncio.run(main())
