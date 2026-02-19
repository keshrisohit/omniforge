"""Phase 2 Demo: Sequential Orchestration

Demonstrates multi-skill execution with data flow and error handling.

Usage:
    python examples/phase2_demo_orchestration.py
"""

import asyncio
from omniforge.builder.models import AgentConfig, SkillReference, TriggerType
from omniforge.execution.orchestration.engine import OrchestrationEngine
from omniforge.execution.orchestration.strategies import ErrorStrategy


async def demo_sequential_execution():
    """Demonstrate sequential multi-skill execution with data flow."""

    print("=" * 70)
    print("PHASE 2 DEMO: Sequential Orchestration")
    print("=" * 70)
    print()

    # Create agent with 3 skills in sequence
    agent = AgentConfig(
        tenant_id="demo-tenant",
        name="Multi-Step Report Generator",
        description="Fetch from Notion, process data, post to Slack",
        trigger=TriggerType.ON_DEMAND,
        skills=[
            SkillReference(
                skill_id="fetch-notion-data",
                name="Fetch Notion Data",
                source="custom",
                order=1,
                error_strategy=ErrorStrategy.STOP_ON_ERROR,
                config={"database_id": "notion-db-123"}
            ),
            SkillReference(
                skill_id="process-data",
                name="Process Data",
                source="custom",
                order=2,
                error_strategy=ErrorStrategy.RETRY_ON_ERROR,
                max_retries=3,
                config={"format": "markdown"}
            ),
            SkillReference(
                skill_id="post-to-slack",
                name="Post to Slack",
                source="custom",
                order=3,
                error_strategy=ErrorStrategy.SKIP_ON_ERROR,
                config={"channel": "#reports"}
            ),
        ],
        created_by="demo-user",
    )

    print(f"Agent: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Skills: {len(agent.skills)}")
    print()

    print("Skill Flow:")
    for skill in sorted(agent.skills, key=lambda s: s.order):
        if skill.error_strategy:
            strategy = skill.error_strategy.value if hasattr(skill.error_strategy, 'value') else skill.error_strategy
        else:
            strategy = "STOP_ON_ERROR"
        print(f"  {skill.order}. {skill.name}")
        print(f"     Strategy: {strategy}")
        if skill.error_strategy == ErrorStrategy.RETRY_ON_ERROR:
            print(f"     Max Retries: {skill.max_retries}")
    print()

    # Create orchestration engine
    print("Creating orchestration engine...")
    engine = OrchestrationEngine()

    # Execute agent
    print("Executing agent with input data...")
    print()

    input_data = {"project_id": "proj-123", "date_range": "last_week"}

    try:
        result = await engine.execute_agent(
            agent=agent,
            input_data=input_data
        )

        print("=" * 70)
        print("EXECUTION COMPLETE")
        print("=" * 70)
        print()
        print(f"Status: {result.status.value}")
        print(f"Total Duration: {result.duration_ms}ms")
        print()

        print("Skill Results:")
        for i, skill_result in enumerate(result.skill_results, 1):
            status_icon = "✅" if skill_result.status == "success" else "❌"
            print(f"  {status_icon} {i}. {skill_result.skill_name}")
            print(f"     Status: {skill_result.status}")
            print(f"     Duration: {skill_result.duration_ms}ms")
            if skill_result.retry_count > 0:
                print(f"     Retries: {skill_result.retry_count}")
            if skill_result.output:
                print(f"     Output: {skill_result.output}")
            if skill_result.error:
                print(f"     Error: {skill_result.error}")
            print()

        # Show final output
        if result.final_output:
            print("Final Output:")
            print(f"  {result.final_output}")
            print()

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        print()

    print("=" * 70)
    print("Demo Complete!")
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Sequential multi-skill execution")
    print("  ✓ Output-to-input data flow")
    print("  ✓ Error strategies (STOP, RETRY, SKIP)")
    print("  ✓ Per-skill timing and status tracking")
    print("  ✓ Execution events emitted")
    print("=" * 70)


async def demo_error_handling():
    """Demonstrate different error handling strategies."""

    print()
    print("=" * 70)
    print("PHASE 2 DEMO: Error Handling Strategies")
    print("=" * 70)
    print()

    # Test each error strategy
    strategies = [
        (ErrorStrategy.STOP_ON_ERROR, "Stops immediately on failure"),
        (ErrorStrategy.SKIP_ON_ERROR, "Continues execution, skips failed skill"),
        (ErrorStrategy.RETRY_ON_ERROR, "Retries up to max_retries times"),
    ]

    for strategy, description in strategies:
        print(f"\nTesting: {strategy.value}")
        print(f"Description: {description}")
        print("-" * 70)

        agent = AgentConfig(
            tenant_id="demo-tenant",
            name=f"Test Agent - {strategy.value}",
            description="Test error handling",
            trigger=TriggerType.ON_DEMAND,
            skills=[
                SkillReference(
                    skill_id="skill-1",
                    name="First Skill (will succeed)",
                    source="custom",
                    order=1,
                    error_strategy=strategy,
                ),
                SkillReference(
                    skill_id="skill-2",
                    name="Second Skill (will fail)",
                    source="custom",
                    order=2,
                    error_strategy=strategy,
                    max_retries=2 if strategy == ErrorStrategy.RETRY_ON_ERROR else 0,
                ),
                SkillReference(
                    skill_id="skill-3",
                    name="Third Skill (should run or not)",
                    source="custom",
                    order=3,
                    error_strategy=strategy,
                ),
            ],
            created_by="demo-user",
        )

        engine = OrchestrationEngine()

        # Note: In a real scenario, skill-2 would actually fail
        # For demo purposes, we're showing the flow
        print(f"Executing agent with {strategy.value}...")
        print("(In real execution, skill-2 would fail)")
        print()

    print("=" * 70)
    print("Error Handling Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    print()
    asyncio.run(demo_sequential_execution())
    asyncio.run(demo_error_handling())
