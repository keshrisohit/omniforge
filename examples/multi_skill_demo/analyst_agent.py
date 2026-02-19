"""
Analyst Agent - Multi-Skill Demo

This agent demonstrates how an agent can dynamically use multiple skills
based on the user's prompt to accomplish complex tasks.

The agent uses:
1. data-processor skill: For data analysis and processing
2. report-generator skill: For creating professional reports
"""

from omniforge.agents.simple import SimpleAgent
from omniforge.agents.models import AgentIdentity, AgentCapabilities


class AnalystAgent(SimpleAgent):
    """
    An analyst agent that processes data and generates reports using multiple skills.

    This agent demonstrates:
    - Dynamic skill selection based on task requirements
    - Multi-skill orchestration for complex workflows
    - Professional data analysis and reporting capabilities
    """

    # Agent Configuration
    name = "AnalystAgent"
    description = (
        "An intelligent analyst that processes data and generates professional reports. "
        "Capable of analyzing datasets, identifying trends, and creating comprehensive reports."
    )
    version = "1.0.0"

    # Capabilities
    streaming = True
    multi_turn = True

    # Skills this agent can use
    # The agent will dynamically select which skills to use based on the task
    available_skills = [
        "data-processor",  # For data analysis
        "report-generator",  # For report creation
    ]

    def handle(self, message: str) -> str:
        """
        Handle user messages and determine which skills to use.

        The agent analyzes the user's request and decides:
        - If only data processing is needed
        - If only report generation is needed
        - If both skills should be used in sequence

        Args:
            message: User's request

        Returns:
            Response from processing the request
        """
        # In a real implementation, this would use an LLM to understand the request
        # and dynamically invoke the appropriate skills via the SkillTool

        # For this demo, we'll use simple keyword matching to demonstrate the concept
        message_lower = message.lower()

        # Determine which skills are needed
        needs_data_processing = any(
            keyword in message_lower
            for keyword in ["analyze", "process", "filter", "calculate", "find", "data"]
        )

        needs_report = any(
            keyword in message_lower
            for keyword in ["report", "summary", "document", "write", "generate"]
        )

        # Build response explaining what the agent will do
        response_parts = []

        response_parts.append(f"📊 AnalystAgent received request: {message}\n")
        response_parts.append("🤖 Analyzing task requirements...\n")

        if needs_data_processing and needs_report:
            response_parts.append("✅ Task requires: DATA PROCESSING + REPORT GENERATION\n")
            response_parts.append("📋 Workflow:")
            response_parts.append("  1. Activate 'data-processor' skill to analyze data")
            response_parts.append("  2. Activate 'report-generator' skill to create report")
            response_parts.append("\n🔄 This demonstrates multi-skill orchestration!\n")

        elif needs_data_processing:
            response_parts.append("✅ Task requires: DATA PROCESSING only\n")
            response_parts.append("📋 Workflow:")
            response_parts.append("  1. Activate 'data-processor' skill")
            response_parts.append("  2. Return processed results\n")

        elif needs_report:
            response_parts.append("✅ Task requires: REPORT GENERATION only\n")
            response_parts.append("📋 Workflow:")
            response_parts.append("  1. Activate 'report-generator' skill")
            response_parts.append("  2. Create formatted report\n")

        else:
            response_parts.append("❓ Task type unclear - please clarify if you need:")
            response_parts.append("  - Data processing (analyze, filter, calculate)")
            response_parts.append("  - Report generation (create report, summary)")
            response_parts.append("  - Both (analyze data AND generate report)\n")

        response_parts.append("\n💡 In a full implementation, the agent would:")
        response_parts.append("  • Use SkillTool to discover available skills")
        response_parts.append("  • Load skill content with full instructions")
        response_parts.append("  • Execute tools restricted by skill's allowed-tools")
        response_parts.append("  • Coordinate multiple skills for complex workflows")
        response_parts.append("  • Stream results back in real-time")

        return "\n".join(response_parts)


# Create agent instance for easy testing
def create_analyst_agent() -> AnalystAgent:
    """Factory function to create an AnalystAgent instance."""
    return AnalystAgent()


async def run_demo():
    """Run the demo with async support."""
    # Quick test
    agent = create_analyst_agent()

    print("=" * 80)
    print("ANALYST AGENT - MULTI-SKILL DEMO")
    print("=" * 80)
    print()

    # Test different types of requests
    test_messages = [
        "Analyze the sales data from Q1",
        "Generate a report on customer trends",
        "Analyze Q2 data and create a comprehensive report",
        "Help me with something",
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}")
        print('=' * 80)

        event_gen = agent.process_task(message)

        # Process events (async generator)
        async for event in event_gen:
            if event.type == "message":
                print(event.data.get("content", ""))
            elif event.type == "done":
                print(f"\n✓ Task completed")

        print()

    print("=" * 80)
    print("DEMO COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_demo())
