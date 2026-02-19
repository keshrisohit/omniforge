"""
Simple Analyst Agent Demo

This is a simplified version that demonstrates the concept of multi-skill agents
without the complexity of async execution and task objects.
"""

from omniforge.agents.simple import SimpleAgent


class AnalystAgent(SimpleAgent):
    """
    An intelligent analyst that processes data and generates professional reports.

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

    async def handle(self, message: str) -> str:
        """
        Handle user messages and determine which skills to use.

        Args:
            message: User's request

        Returns:
            Response explaining the skill selection
        """
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

        response_parts.append(f"📊 AnalystAgent received: '{message}'\n")
        response_parts.append("🤖 Analyzing task requirements...\n")

        if needs_data_processing and needs_report:
            response_parts.append("✅ Task requires: DATA PROCESSING + REPORT GENERATION\n")
            response_parts.append("📋 Workflow:")
            response_parts.append("  1. Activate 'data-processor' skill to analyze data")
            response_parts.append("  2. Activate 'report-generator' skill to create report")
            response_parts.append("\n🔄 This demonstrates multi-skill orchestration!")

        elif needs_data_processing:
            response_parts.append("✅ Task requires: DATA PROCESSING only\n")
            response_parts.append("📋 Workflow:")
            response_parts.append("  1. Activate 'data-processor' skill")
            response_parts.append("  2. Return processed results")

        elif needs_report:
            response_parts.append("✅ Task requires: REPORT GENERATION only\n")
            response_parts.append("📋 Workflow:")
            response_parts.append("  1. Activate 'report-generator' skill")
            response_parts.append("  2. Create formatted report")

        else:
            response_parts.append("❓ Task type unclear - please clarify:")
            response_parts.append("  - Data processing (analyze, filter, calculate)")
            response_parts.append("  - Report generation (create report, summary)")
            response_parts.append("  - Both (analyze data AND generate report)")

        return "\n".join(response_parts)


def demo_skill_selection():
    """Demonstrate how the agent selects skills based on different prompts."""

    print("=" * 80)
    print("ANALYST AGENT - SKILL SELECTION DEMO")
    print("=" * 80)
    print()

    agent = AnalystAgent()

    # Test different types of requests
    test_messages = [
        "Analyze the sales data from Q1",
        "Generate a report on customer trends",
        "Analyze Q2 data and create a comprehensive report",
        "Help me with something",
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"{'=' * 80}")
        print(f"TEST {i}: {message}")
        print('=' * 80)
        print()

        # Simulate skill selection (synchronous for demo)
        message_lower = message.lower()

        needs_data_processing = any(
            keyword in message_lower
            for keyword in ["analyze", "process", "filter", "calculate", "find", "data"]
        )

        needs_report = any(
            keyword in message_lower
            for keyword in ["report", "summary", "document", "write", "generate"]
        )

        if needs_data_processing and needs_report:
            print("🎯 DECISION: Use BOTH skills sequentially")
            print("   1️⃣  data-processor (analyze data)")
            print("   2️⃣  report-generator (create report)")
            print()
            print("💡 In a real implementation:")
            print("   • Load data-processor skill via SkillTool")
            print("   • Execute with Read, Glob, Bash tools (restricted)")
            print("   • Load report-generator skill via SkillTool")
            print("   • Execute with Write, Edit, Read tools (restricted)")
            print("   • Return final report to user")

        elif needs_data_processing:
            print("🎯 DECISION: Use data-processor skill only")
            print()
            print("💡 In a real implementation:")
            print("   • Load data-processor skill via SkillTool")
            print("   • Execute analysis with restricted tools")
            print("   • Return processed data to user")

        elif needs_report:
            print("🎯 DECISION: Use report-generator skill only")
            print()
            print("💡 In a real implementation:")
            print("   • Load report-generator skill via SkillTool")
            print("   • Generate formatted report")
            print("   • Return report to user")

        else:
            print("🎯 DECISION: Cannot determine required skills")
            print("   • Ask user for clarification")
            print("   • Provide examples of what the agent can do")

        print()

    print("=" * 80)
    print("KEY CONCEPTS")
    print("=" * 80)
    print()
    print("1️⃣  SKILL DISCOVERY")
    print("   • Agent knows available skills: data-processor, report-generator")
    print("   • Skills are defined in src/omniforge/skills/*/SKILL.md")
    print()
    print("2️⃣  DYNAMIC SELECTION")
    print("   • Agent analyzes user prompt keywords")
    print("   • Determines which skill(s) are needed")
    print("   • Can use multiple skills in sequence")
    print()
    print("3️⃣  SKILL ACTIVATION")
    print("   • SkillTool loads full skill content on demand")
    print("   • Progressive disclosure (lightweight metadata → full content)")
    print()
    print("4️⃣  TOOL RESTRICTIONS")
    print("   • Each skill specifies allowed tools")
    print("   • ToolExecutor enforces restrictions")
    print("   • Provides security boundaries")
    print()
    print("5️⃣  MULTI-SKILL ORCHESTRATION")
    print("   • Complex tasks can use multiple skills")
    print("   • Skills execute sequentially or in parallel")
    print("   • Output from one skill feeds into next")
    print()


if __name__ == "__main__":
    demo_skill_selection()
