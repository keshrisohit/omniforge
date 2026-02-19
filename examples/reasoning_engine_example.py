"""Example: Building a simple agent using ReasoningEngine.

This example demonstrates:
1. Creating a reasoning chain
2. Using ReasoningEngine to record thoughts and execute tools
3. Building a complete reasoning process with synthesis
4. Tracking costs and metrics
"""

import asyncio
from omniforge.agents.cot.chain import ReasoningChain, ChainStatus, StepType
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.setup import get_default_tool_registry


async def simple_data_analysis_agent(user_query: str) -> str:
    """A simple agent that analyzes data using LLM.

    Args:
        user_query: User's data analysis question

    Returns:
        The agent's final answer
    """
    # 1. Create reasoning chain
    print("📋 Creating reasoning chain...")
    chain = ReasoningChain(
        task_id="task-example-001",
        agent_id="data-analyst-agent",
        status=ChainStatus.RUNNING,
    )

    # 2. Set up tool executor with default tools (includes LLM)
    print("🔧 Setting up tool executor...")
    registry = get_default_tool_registry()
    executor = ToolExecutor(registry=registry)

    # 3. Create reasoning engine
    print("🧠 Creating reasoning engine...")
    engine = ReasoningEngine(
        chain=chain,
        executor=executor,
        task={
            "id": "task-example-001",
            "agent_id": "data-analyst-agent",
            "max_cost_usd": 0.10,  # Budget limit
        },
        default_llm_model="claude-sonnet-4",
    )

    print(f"\n💭 Processing query: '{user_query}'\n")

    # 4. Start reasoning process
    # Step 1: Initial thinking
    print("Step 1: Recording initial thought...")
    engine.add_thinking(f"User wants to know: {user_query}. I'll analyze this.")

    # Step 2: Call LLM for analysis
    print("Step 2: Calling LLM for analysis...")
    analysis_result = await engine.call_llm(
        prompt=f"""Analyze this query and provide insights:

Query: {user_query}

Provide a detailed analysis with key points.""",
        model="claude-sonnet-4",
        temperature=0.7,
    )

    # Check if LLM call succeeded
    if not analysis_result.success:
        print(f"❌ LLM call failed: {analysis_result.error}")
        return "Sorry, I couldn't analyze the query."

    # Extract analysis
    analysis_content = analysis_result.value["content"]
    print(f"✅ Analysis received: {analysis_content[:100]}...")

    # Step 3: Record thinking about the analysis
    print("Step 3: Recording thoughts on analysis...")
    engine.add_thinking(
        f"LLM provided analysis. The key insights seem valid. "
        f"Confidence level: high",
        confidence=0.9,
    )

    # Step 4: Call LLM again to format final answer
    print("Step 4: Formatting final answer...")
    final_result = await engine.call_llm(
        prompt=f"""Based on this analysis, provide a concise final answer:

Analysis: {analysis_content}

Provide a clear, concise answer (2-3 sentences max).""",
        model="claude-sonnet-4",
        temperature=0.5,
    )

    if not final_result.success:
        print(f"❌ Final answer generation failed: {final_result.error}")
        return "Sorry, I couldn't generate a final answer."

    final_answer = final_result.value["content"]

    # Step 5: Synthesize the conclusion
    print("Step 5: Creating synthesis...")
    engine.add_synthesis(
        conclusion=final_answer,
        sources=[analysis_result.step_id, final_result.step_id],
    )

    # 6. Mark chain as completed
    chain.status = ChainStatus.COMPLETED
    print("\n✨ Reasoning complete!\n")

    # 7. Display chain metrics
    print("📊 Chain Metrics:")
    print(f"  Total steps: {chain.metrics.total_steps}")
    print(f"  LLM calls: {chain.metrics.llm_calls}")
    print(f"  Tool calls: {chain.metrics.tool_calls}")
    print(f"  Total tokens: {chain.metrics.total_tokens}")
    print(f"  Total cost: ${chain.metrics.total_cost:.6f}")

    # 8. Display chain steps
    print("\n🔍 Reasoning Chain Steps:")
    for step in chain.steps:
        print(f"\n  Step {step.step_number}: {step.type}")
        if step.type == StepType.THINKING:
            content = step.thinking.content[:80] + "..." if len(step.thinking.content) > 80 else step.thinking.content
            print(f"    💭 {content}")
            if step.thinking.confidence:
                print(f"    Confidence: {step.thinking.confidence:.2f}")
        elif step.type == StepType.TOOL_CALL:
            print(f"    🔧 Tool: {step.tool_call.tool_name}")
            print(f"    Correlation ID: {step.tool_call.correlation_id}")
        elif step.type == StepType.TOOL_RESULT:
            status = "✅" if step.tool_result.success else "❌"
            print(f"    {status} Success: {step.tool_result.success}")
            if step.tokens_used > 0:
                print(f"    Tokens: {step.tokens_used}, Cost: ${step.cost:.6f}")
        elif step.type == StepType.SYNTHESIS:
            content = step.synthesis.content[:80] + "..." if len(step.synthesis.content) > 80 else step.synthesis.content
            print(f"    📊 {content}")
            print(f"    Sources: {len(step.synthesis.sources)} steps")

    return final_answer


async def react_loop_example(query: str, max_iterations: int = 3) -> str:
    """Example of ReAct (Reasoning + Acting) loop.

    This demonstrates how autonomous agents use ReasoningEngine
    to implement the ReAct pattern.

    Args:
        query: User's query
        max_iterations: Maximum reasoning iterations

    Returns:
        Final answer
    """
    print(f"\n🤖 ReAct Loop Example")
    print(f"Query: {query}")
    print(f"Max iterations: {max_iterations}\n")

    # Setup
    chain = ReasoningChain(
        task_id="task-react-001",
        agent_id="react-agent",
        status=ChainStatus.RUNNING,
    )

    registry = get_default_tool_registry()
    executor = ToolExecutor(registry=registry)

    engine = ReasoningEngine(
        chain=chain,
        executor=executor,
        task={"id": "task-react-001", "agent_id": "react-agent"},
        default_llm_model="claude-sonnet-4",
    )

    # Build conversation history
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": query},
    ]

    # ReAct loop
    for iteration in range(max_iterations):
        print(f"\n🔄 Iteration {iteration + 1}/{max_iterations}")

        # Add thinking step
        engine.add_thinking(f"ReAct iteration {iteration + 1}")

        # Call LLM to decide next action
        llm_result = await engine.call_llm(
            messages=conversation,
            model="claude-sonnet-4",
            temperature=0.0,  # Deterministic
        )

        response = llm_result.value["content"]
        print(f"💭 LLM Response: {response[:200]}...")

        # In a real ReAct implementation, you would:
        # 1. Parse the response for Thought/Action/Final Answer
        # 2. If Final Answer found, return it
        # 3. If Action found, execute the tool
        # 4. Add observation to conversation
        # 5. Continue loop

        # For this example, we'll just check if it looks like a final answer
        if "final answer" in response.lower() or iteration == max_iterations - 1:
            engine.add_synthesis(
                conclusion=response, sources=[llm_result.step_id]
            )
            chain.status = ChainStatus.COMPLETED
            print(f"\n✅ Final answer reached!")
            return response

        # Add response to conversation
        conversation.append({"role": "assistant", "content": response})
        conversation.append(
            {"role": "user", "content": "Continue your reasoning."}
        )

    return "Max iterations reached without final answer"


async def main():
    """Run examples."""
    print("=" * 70)
    print("ReasoningEngine Examples")
    print("=" * 70)

    # Example 1: Simple data analysis
    print("\n" + "=" * 70)
    print("Example 1: Simple Data Analysis Agent")
    print("=" * 70)

    answer = await simple_data_analysis_agent(
        "What are the benefits of using chain of thought reasoning in AI agents?"
    )

    print(f"\n🎯 Final Answer:")
    print(f"{answer}")

    # Example 2: ReAct loop (simplified)
    print("\n" + "=" * 70)
    print("Example 2: ReAct Loop (Simplified)")
    print("=" * 70)

    react_answer = await react_loop_example(
        "What is the capital of France?", max_iterations=2
    )

    print(f"\n🎯 Final Answer:")
    print(f"{react_answer}")


if __name__ == "__main__":
    # Check if LLM API keys are configured
    import os

    if not os.getenv("OMNIFORGE_ANTHROPIC_API_KEY") and not os.getenv(
        "ANTHROPIC_API_KEY"
    ):
        print("⚠️  Warning: No Anthropic API key found.")
        print("Set OMNIFORGE_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY")
        print("\nRunning in demo mode (will show structure only)...\n")

    # Run examples
    asyncio.run(main())
