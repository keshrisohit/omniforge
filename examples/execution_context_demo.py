"""Demo script showing ExecutionContext depth tracking for sub-agent execution.

This demonstrates how ExecutionContext prevents infinite recursion in sub-agent
spawning by enforcing a maximum depth limit.
"""

from omniforge.skills.config import ExecutionContext


def main() -> None:
    """Demonstrate ExecutionContext depth tracking."""
    print("=" * 70)
    print("ExecutionContext Depth Tracking Demo")
    print("=" * 70)
    print()

    # Create root context
    print("1. Creating root execution context (depth=0, max_depth=2)")
    root = ExecutionContext(depth=0, max_depth=2)
    print(f"   Root context: depth={root.depth}, can_spawn={root.can_spawn_sub_agent()}")
    print()

    # Create child context (sub-agent)
    print("2. Creating child context (sub-agent at depth=1)")
    try:
        child = root.create_child_context("task-1", skill_name="data-processor")
        print(f"   Child context: depth={child.depth}, can_spawn={child.can_spawn_sub_agent()}")
        print(f"   Root task ID: {child.root_task_id}")
        print(f"   Parent task ID: {child.parent_task_id}")
        print(f"   Skill chain: {' -> '.join(child.skill_chain)}")
        print("   ✅ Sub-agent successfully spawned")
    except ValueError as e:
        print(f"   ❌ Error: {e}")
    print()

    # Create grandchild context (sub-sub-agent)
    print("3. Creating grandchild context (sub-sub-agent at depth=2)")
    try:
        grandchild = child.create_child_context("task-2", skill_name="report-generator")
        print(f"   Grandchild context: depth={grandchild.depth}, can_spawn={grandchild.can_spawn_sub_agent()}")
        print(f"   Root task ID: {grandchild.root_task_id}")
        print(f"   Parent task ID: {grandchild.parent_task_id}")
        print(f"   Skill chain: {' -> '.join(grandchild.skill_chain)}")
        print("   ✅ Sub-sub-agent successfully spawned (at max depth)")
    except ValueError as e:
        print(f"   ❌ Error: {e}")
    print()

    # Try to create great-grandchild (should fail)
    print("4. Attempting to create great-grandchild context (depth=3) - SHOULD FAIL")
    try:
        great_grandchild = grandchild.create_child_context("task-3", skill_name="validator")
        print(f"   ❌ ERROR: Should not have succeeded! depth={great_grandchild.depth}")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {e}")
    print()

    # Demonstrate iteration budget reduction
    print("5. Iteration budget reduction by depth")
    print("   (Each sub-agent level gets 50% of parent's budget)")
    base_iterations = 16
    print(f"   Base iterations: {base_iterations}")
    print(f"   - Root (depth 0) child budget: {root.get_iteration_budget_for_child(base_iterations)}")
    print(f"   - Child (depth 1) child budget: {child.get_iteration_budget_for_child(base_iterations)}")
    print(f"   - Grandchild (depth 2) child budget: {grandchild.get_iteration_budget_for_child(base_iterations)}")
    print()

    # Show boundary case with max_depth=0
    print("6. Boundary case: max_depth=0 (no sub-agents allowed)")
    restricted = ExecutionContext(depth=0, max_depth=0)
    print(f"   Restricted context: depth={restricted.depth}, can_spawn={restricted.can_spawn_sub_agent()}")
    try:
        restricted.create_child_context("task-x")
        print("   ❌ ERROR: Should not have succeeded!")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {e}")
    print()

    print("=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
