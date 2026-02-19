"""Multi-Agent Skills End-to-End Demo

This demonstrates the complete flow:
1. User makes a request
2. Coordinator agent analyzes the request and picks skills
3. Coordinator delegates to skill-specific agents using orchestration
4. Skill agents execute their work
5. Coordinator synthesizes the final response

This shows how agents can intelligently route work to specialized agents
based on the skills needed to complete a task.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Optional
from uuid import uuid4

from omniforge.agents.models import AgentCard, AgentIdentity, AgentCapabilities, AgentSkill, SkillInputMode, SkillOutputMode, AuthScheme, SecurityConfig, TextPart, OrchestrationCapability
from omniforge.orchestration.manager import OrchestrationManager, DelegationStrategy, SubAgentResult
from omniforge.orchestration.client import A2AClient
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.conversation.models import ConversationType
from omniforge.storage.database import Database, DatabaseConfig
from omniforge.agents.events import TaskMessageEvent


# ============================================================================
# Step 1: Define Available Skills
# ============================================================================

@dataclass
class Skill:
    """Skill definition."""
    id: str
    name: str
    description: str
    keywords: list[str]  # Keywords for matching requests
    agent_id: str  # Which agent handles this skill


# Define 4 practical skills
AVAILABLE_SKILLS = [
    Skill(
        id="data-analysis",
        name="Data Analysis",
        description="Analyze datasets, calculate statistics, identify patterns",
        keywords=["analyze", "data", "statistics", "pattern", "trend", "csv", "numbers"],
        agent_id="data-analyst-agent"
    ),
    Skill(
        id="web-search",
        name="Web Search & Research",
        description="Search the web, gather information, summarize findings",
        keywords=["search", "web", "research", "find", "lookup", "google", "information"],
        agent_id="research-agent"
    ),
    Skill(
        id="document-generation",
        name="Document Generation",
        description="Create documents, reports, presentations, summaries",
        keywords=["generate", "create", "document", "report", "summary", "write", "draft"],
        agent_id="document-agent"
    ),
    Skill(
        id="code-review",
        name="Code Review",
        description="Review code, suggest improvements, identify bugs",
        keywords=["code", "review", "bug", "improve", "refactor", "python", "javascript"],
        agent_id="code-reviewer-agent"
    ),
]


# ============================================================================
# Step 2: Mock Skill Executor Agents
# ============================================================================

class MockSkillAgent:
    """Mock agent that executes a specific skill."""

    def __init__(self, skill: Skill):
        self.skill = skill
        self.agent_id = skill.agent_id

    async def execute(self, message: str) -> str:
        """Execute the skill based on the message.

        In a real system, this would:
        - Parse the task requirements
        - Execute actual skill logic (API calls, data processing, etc.)
        - Return structured results

        For demo purposes, we simulate the work.
        """
        await asyncio.sleep(0.5)  # Simulate work

        # Generate skill-specific response
        if self.skill.id == "data-analysis":
            return f"""Data Analysis Results:
- Dataset: Sample data from request
- Mean: 45.3, Median: 42.0, Std Dev: 12.7
- Trend: Upward trend detected (+15% over period)
- Anomalies: 3 outliers identified at indices [12, 45, 78]
- Recommendation: Focus on improving data quality in segment B
"""

        elif self.skill.id == "web-search":
            return f"""Research Findings:
- Found 5 relevant sources on: "{message[:50]}..."
- Top result: Best practices show 87% adoption rate
- Expert consensus: Recommended approach is hybrid model
- Recent trends: 23% growth in this area over last 6 months
- Key references: [source1.com, source2.org, source3.net]
"""

        elif self.skill.id == "document-generation":
            return f"""Document Generated:

# Executive Summary

Based on the request "{message[:40]}...", here are the key points:

## Overview
This document provides a comprehensive analysis of the topic.

## Key Findings
1. Primary insight: Clear correlation identified
2. Secondary insight: Supporting evidence found
3. Recommendation: Implement phased approach

## Conclusion
The analysis suggests a positive outcome with managed risk.

[Document saved as: output_report_{uuid4().hex[:8]}.pdf]
"""

        elif self.skill.id == "code-review":
            return f"""Code Review Results:

✓ Overall Quality: Good (Score: 7.5/10)

Issues Found:
1. [MINOR] Line 45: Consider using list comprehension for better readability
2. [MEDIUM] Line 78: Missing error handling for network calls
3. [MINOR] Line 102: Variable naming could be more descriptive

Suggestions:
- Add type hints to improve maintainability
- Consider extracting helper function for repeated logic (lines 45-52)
- Add docstrings to public methods

Security:
✓ No critical vulnerabilities detected
⚠ Consider sanitizing user input in function 'process_data'

Test Coverage: 82% (target: 90%)
"""

        return f"Processed request with {self.skill.name}"


# ============================================================================
# Step 3: Coordinator Agent (Skill Selector)
# ============================================================================

class CoordinatorAgent:
    """Main coordinator agent that selects skills and delegates work."""

    def __init__(self, orchestration_manager: OrchestrationManager):
        self.orchestration_manager = orchestration_manager
        self.agent_id = "coordinator-agent"

    def _determine_strategy(self, message: str, selected_skills: list[Skill]) -> DelegationStrategy:
        """Determine the optimal delegation strategy based on request analysis.

        SEQUENTIAL is chosen when:
        - Request contains dependency indicators (then, after, once, before)
        - Multiple skills where output of one feeds into another
        - Analysis -> Generation pipeline detected

        PARALLEL is chosen when:
        - Skills are independent
        - Single skill request
        - No clear dependencies
        """
        message_lower = message.lower()

        # Single skill is always parallel (no coordination needed)
        if len(selected_skills) == 1:
            return DelegationStrategy.PARALLEL

        # Check for explicit sequential indicators
        sequential_indicators = [
            "then", "after", "once", "before", "first", "next",
            "followed by", "and then", "after that"
        ]
        if any(indicator in message_lower for indicator in sequential_indicators):
            return DelegationStrategy.SEQUENTIAL

        # Check for analysis -> generation pipeline
        skill_ids = [skill.id for skill in selected_skills]
        has_analysis = any(sid in skill_ids for sid in ["data-analysis", "web-search"])
        has_generation = "document-generation" in skill_ids

        if has_analysis and has_generation:
            # If request mentions both analyzing/searching AND generating/creating
            analysis_keywords = ["analyze", "search", "research", "find", "look up"]
            generation_keywords = ["generate", "create", "write", "draft", "produce", "make"]

            has_analysis_intent = any(kw in message_lower for kw in analysis_keywords)
            has_generation_intent = any(kw in message_lower for kw in generation_keywords)

            if has_analysis_intent and has_generation_intent:
                return DelegationStrategy.SEQUENTIAL

        # Check for code review + other skills (usually sequential)
        if "code-review" in skill_ids and len(selected_skills) > 1:
            # Code review with generation suggests: review first, then document findings
            if has_generation:
                return DelegationStrategy.SEQUENTIAL

        # Default to parallel for independent tasks
        return DelegationStrategy.PARALLEL

    def _get_strategy_reason(self, message: str, selected_skills: list[Skill], strategy: DelegationStrategy) -> str:
        """Get human-readable reason for strategy selection."""
        if strategy == DelegationStrategy.SEQUENTIAL:
            if len(selected_skills) == 1:
                return "single skill"

            skill_ids = [skill.id for skill in selected_skills]
            has_analysis = any(sid in skill_ids for sid in ["data-analysis", "web-search"])
            has_generation = "document-generation" in skill_ids

            if has_analysis and has_generation:
                return "analysis feeds into generation"
            if "code-review" in skill_ids and has_generation:
                return "review feeds into documentation"

            return "detected dependencies"
        else:
            if len(selected_skills) == 1:
                return "single skill"
            return "independent tasks"

    def select_skills(self, message: str) -> list[Skill]:
        """Analyze the message and select appropriate skills.

        In a real system, this would use:
        - LLM-based intent classification
        - Semantic similarity search
        - Skill capability matching

        For demo, we use keyword matching with scoring.
        """
        message_lower = message.lower()
        skill_scores = []

        for skill in AVAILABLE_SKILLS:
            # Count how many keywords match
            matches = sum(1 for keyword in skill.keywords if keyword in message_lower)
            if matches > 0:
                # Calculate relevance score (matches / total keywords)
                score = matches / len(skill.keywords)
                skill_scores.append((skill, score, matches))

        # Sort by match count first, then by score
        skill_scores.sort(key=lambda x: (x[2], x[1]), reverse=True)

        # Select skills with at least 2 keyword matches OR top scorer if only 1 match
        selected_skills = []
        for skill, score, matches in skill_scores:
            if matches >= 2:
                selected_skills.append(skill)
            elif matches == 1 and not selected_skills and score >= 0.1:
                # Only include single-match skills if no multi-match skills found
                # and they have reasonable score
                selected_skills.append(skill)

        # If no skills matched, default to research
        if not selected_skills:
            selected_skills.append(AVAILABLE_SKILLS[1])  # web-search as fallback

        return selected_skills

    async def process_request(
        self,
        thread_id: str,
        tenant_id: str,
        user_id: str,
        message: str,
        skill_agents: dict[str, MockSkillAgent]
    ) -> str:
        """Process a user request by selecting skills and delegating work.

        This demonstrates the core orchestration pattern:
        1. Analyze request -> Select skills
        2. Create agent cards for selected skill agents
        3. Delegate to agents using orchestration manager
        4. Synthesize responses into final answer
        """
        print(f"\n{'='*80}")
        print(f"COORDINATOR: Processing request")
        print(f"{'='*80}")
        print(f"Request: {message}\n")

        # Step 1: Select skills
        selected_skills = self.select_skills(message)
        print(f"📋 Selected Skills ({len(selected_skills)}):")
        for skill in selected_skills:
            print(f"   • {skill.name} - {skill.description}")
        print()

        # Step 2: Create agent cards for selected skills
        target_agent_cards = []
        for skill in selected_skills:
            agent_card = AgentCard(
                protocol_version="1.0",
                identity=AgentIdentity(
                    id=skill.agent_id,
                    name=skill.name,
                    description=skill.description,
                    version="1.0.0"
                ),
                capabilities=AgentCapabilities(
                    streaming=True,
                    multi_turn=False,
                    orchestration=OrchestrationCapability(
                        can_be_orchestrated=True
                    )
                ),
                skills=[
                    AgentSkill(
                        id=skill.id,
                        name=skill.name,
                        description=skill.description,
                        inputModes=[SkillInputMode.TEXT],
                        outputModes=[SkillOutputMode.TEXT]
                    )
                ],
                service_endpoint=f"http://localhost:800{len(target_agent_cards)+1}",
                security=SecurityConfig(
                    auth_scheme=AuthScheme.NONE,
                    require_https=False
                )
            )
            target_agent_cards.append(agent_card)

        # Step 3: Determine delegation strategy
        strategy = self._determine_strategy(message, selected_skills)

        strategy_reason = self._get_strategy_reason(message, selected_skills, strategy)
        print(f"🔀 Strategy: {strategy.value} ({strategy_reason})")
        print(f"⚙️  Delegating to {len(target_agent_cards)} agent(s)...\n")

        # Step 4: Simulate delegation results
        # In a real system, this would call orchestration_manager.delegate_to_agents()
        # For demo, we directly call the mock agents
        results = []

        if strategy == DelegationStrategy.PARALLEL:
            # Execute all agents concurrently
            tasks = []
            for skill in selected_skills:
                agent = skill_agents[skill.agent_id]
                tasks.append(agent.execute(message))

            responses = await asyncio.gather(*tasks)
            for skill, response in zip(selected_skills, responses):
                results.append(SubAgentResult(
                    agent_id=skill.agent_id,
                    success=True,
                    response=response,
                    latency_ms=500
                ))
        else:
            # Execute agents sequentially
            for skill in selected_skills:
                agent = skill_agents[skill.agent_id]
                response = await agent.execute(message)
                results.append(SubAgentResult(
                    agent_id=skill.agent_id,
                    success=True,
                    response=response,
                    latency_ms=500
                ))

        # Step 5: Display individual results
        print(f"📊 Individual Agent Results:")
        print(f"{'-'*80}")
        for i, result in enumerate(results, 1):
            status = "✓" if result.success else "✗"
            print(f"\n{status} Agent {i}: {result.agent_id}")
            print(f"   Latency: {result.latency_ms}ms")
            if result.success:
                print(f"   Response:\n{result.response}")
            else:
                print(f"   Error: {result.error}")
            print(f"{'-'*80}")

        # Step 6: Synthesize final response
        final_response = self.orchestration_manager.synthesize_responses(results)

        print(f"\n🎯 FINAL SYNTHESIZED RESPONSE:")
        print(f"{'='*80}")
        print(final_response)
        print(f"{'='*80}\n")

        return final_response


# ============================================================================
# Step 4: Main Demo
# ============================================================================

async def run_demo():
    """Run the complete multi-agent skills demo."""

    print("\n" + "="*80)
    print(" MULTI-AGENT SKILLS ORCHESTRATION DEMO")
    print("="*80)
    print()
    print("This demo shows:")
    print("  1. Coordinator agent analyzes user requests")
    print("  2. Selects appropriate skills based on keywords")
    print("  3. Delegates work to specialized skill agents")
    print("  4. Synthesizes responses into final answer")
    print("="*80 + "\n")

    # Setup database and repositories
    database = Database(DatabaseConfig(url="sqlite+aiosqlite:///:memory:"))
    await database.create_tables()

    conversation_repo = SQLiteConversationRepository(database)
    a2a_client = A2AClient()

    # Create orchestration manager
    orchestration_manager = OrchestrationManager(
        client=a2a_client,
        conversation_repo=conversation_repo
    )

    # Create coordinator agent
    coordinator = CoordinatorAgent(orchestration_manager)

    # Create skill executor agents
    skill_agents = {
        skill.agent_id: MockSkillAgent(skill)
        for skill in AVAILABLE_SKILLS
    }

    # Create a conversation thread
    thread_id = str(uuid4())
    tenant_id = "demo-tenant"
    user_id = "demo-user"

    conversation = await conversation_repo.create_conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title="Multi-Agent Skills Demo",
        conversation_type=ConversationType.CHAT,
        conversation_id=uuid4()
    )

    # Test cases demonstrating different scenarios
    test_cases = [
        {
            "name": "Single Skill - Data Analysis",
            "message": "Analyze the sales data from last quarter and identify trends",
        },
        {
            "name": "Multiple Skills - Research + Document",
            "message": "Research best practices for Python async programming and create a summary document",
        },
        {
            "name": "Multiple Skills - Code Review + Suggestions",
            "message": "Review the authentication code and suggest security improvements",
        },
        {
            "name": "Complex Request - All Skills",
            "message": "Search for market trends, analyze the data, review our existing code, and generate a comprehensive report",
        },
    ]

    # Run each test case
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'█'*80}")
        print(f"  TEST CASE {i}: {test_case['name']}")
        print(f"{'█'*80}")

        result = await coordinator.process_request(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            message=test_case["message"],
            skill_agents=skill_agents
        )

        # Uncomment for interactive mode (pause between test cases):
        # input("\n⏸  Press Enter to continue to next test case...\n")
        # Comment out for auto-run mode:
        await asyncio.sleep(0.5)  # Small pause between test cases

    # Cleanup
    await a2a_client.close()
    # Database cleanup - engine will be closed when garbage collected

    print("\n" + "="*80)
    print(" ✅ DEMO COMPLETED SUCCESSFULLY")
    print("="*80)
    print()
    print("Key Takeaways:")
    print("  • Coordinator agent intelligently selects skills based on request")
    print("  • Multiple skill agents can work in parallel or sequentially")
    print("  • OrchestrationManager handles delegation and synthesis")
    print("  • System scales to any number of skills and agents")
    print()
    print("Next Steps:")
    print("  • Replace mock agents with real agent implementations")
    print("  • Add LLM-based skill selection (vs keyword matching)")
    print("  • Implement actual skill logic (API calls, data processing)")
    print("  • Add HTTP endpoints for remote agent communication")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
