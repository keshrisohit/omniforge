"""Examples for using SimpleAutonomousAgent.

This file demonstrates how to use the SimpleAutonomousAgent for various tasks.
The agent autonomously decides which tools to use based on the task.
"""

import asyncio
from omniforge.agents.autonomous_simple import (
    SimpleAutonomousAgent,
    run_autonomous_agent,
)
from omniforge.tools.setup import get_default_tool_registry


# =============================================================================
# Example 1: Simplest Usage - Just Run a Prompt
# =============================================================================

async def example_1_simplest():
    """Simplest possible usage - one line!"""
    print("=== Example 1: Simplest Usage ===\n")

    # Just call the function with a prompt
    result = await run_autonomous_agent(
        "Run a python program to print fibonnaci series, print first 10 number in the series"
    )

    print(f"Result: {result}\n")


# =============================================================================
# Example 2: Basic Agent Creation
# =============================================================================

async def example_2_basic():
    """Create agent and run multiple tasks."""
    print("=== Example 2: Basic Agent Creation ===\n")

    # Create agent once
    agent = SimpleAutonomousAgent()

    # Run multiple tasks
    tasks = [
        "List all directories in the current folder",
        "Find files containing 'TODO' comments",
        "Show me the first 5 lines of README.md",
    ]

    for task in tasks:
        print(f"Task: {task}")
        result = await agent.run(task)
        print(f"Result: {result}\n")


# =============================================================================
# Example 3: Custom System Prompt
# =============================================================================

async def example_3_custom_system_prompt():
    """Use custom system prompt to guide agent behavior."""
    print("=== Example 3: Custom System Prompt ===\n")

    # Create agent with specific personality/behavior
    agent = SimpleAutonomousAgent(
        system_prompt="""You are a senior software engineer with expertise in Python.

When analyzing code:
- Focus on code quality, maintainability, and best practices
- Be concise but thorough
- Provide specific line numbers when referencing issues
- Suggest improvements where appropriate"""
    )

    result = await agent.run(
        "Analyze the code quality of src/omniforge/agents/base.py"
    )

    print(f"Analysis:\n{result}\n")


# =============================================================================
# Example 4: Configuration Options
# =============================================================================

async def example_4_configuration():
    """Configure agent with different parameters."""
    print("=== Example 4: Configuration Options ===\n")

    # Agent with custom configuration
    agent = SimpleAutonomousAgent(
        system_prompt="You are a DevOps expert.",
        max_iterations=20,  # More iterations for complex tasks
        model="claude-sonnet-4",  # Specify LLM model
        temperature=0.0,  # Deterministic (0.0) vs creative (0.7+)
    )

    result = await agent.run(
        "Check if pytest is installed and show me the version"
    )

    print(f"Result: {result}\n")


# =============================================================================
# Example 5: File Operations
# =============================================================================

async def example_5_file_operations():
    """Agent autonomously handles file operations."""
    print("=== Example 5: File Operations ===\n")

    agent = SimpleAutonomousAgent(
        system_prompt="You are a file system expert. Be precise and thorough."
    )

    # Agent will automatically use read, write, bash tools
    result = await agent.run(
        """Do the following:
        1. Create a file called test_output.txt
        2. Write 'Hello from autonomous agent' to it
        3. Read it back and confirm the content
        4. Delete the file
        """
    )

    print(f"Result: {result}\n")


# =============================================================================
# Example 6: Code Analysis
# =============================================================================

async def example_6_code_analysis():
    """Agent analyzes codebase structure."""
    print("=== Example 6: Code Analysis ===\n")

    agent = SimpleAutonomousAgent(
        system_prompt="""You are a code structure analyst.

Focus on:
- File organization
- Module dependencies
- Code patterns
- Architecture insights"""
    )

    result = await agent.run(
        "Analyze the structure of the agents module in src/omniforge/agents/"
    )

    print(f"Analysis:\n{result}\n")


# =============================================================================
# Example 7: Search and Find
# =============================================================================

async def example_7_search():
    """Agent performs search operations."""
    print("=== Example 7: Search and Find ===\n")

    agent = SimpleAutonomousAgent()

    # Agent will use grep/glob tools automatically
    result = await agent.run(
        "Find all files that import 'asyncio' and list them with line numbers"
    )

    print(f"Search Results:\n{result}\n")


# =============================================================================
# Example 8: Data Processing
# =============================================================================

async def example_8_data_processing():
    """Agent processes and analyzes data."""
    print("=== Example 8: Data Processing ===\n")

    agent = SimpleAutonomousAgent(
        system_prompt="You are a data analyst. Present findings clearly with numbers."
    )

    result = await agent.run(
        """Analyze the Python files in src/:
        - Count total files
        - Calculate average file size
        - Find the largest file
        - List files over 10KB"""
    )

    print(f"Data Analysis:\n{result}\n")


# =============================================================================
# Example 9: Testing and Validation
# =============================================================================

async def example_9_testing():
    """Agent runs tests and validates code."""
    print("=== Example 9: Testing and Validation ===\n")

    agent = SimpleAutonomousAgent(
        system_prompt="You are a QA engineer focused on test coverage and quality."
    )

    result = await agent.run(
        "Run the tests for the agents module and summarize the results"
    )

    print(f"Test Results:\n{result}\n")


# =============================================================================
# Example 10: Multi-Step Complex Task
# =============================================================================

async def example_10_complex():
    """Agent handles complex multi-step tasks."""
    print("=== Example 10: Complex Multi-Step Task ===\n")

    agent = SimpleAutonomousAgent(
        max_iterations=25,  # Complex task needs more iterations
        system_prompt="""You are a senior developer.

For complex tasks:
1. Break them down into clear steps
2. Execute each step carefully
3. Verify results at each stage
4. Provide a clear summary at the end"""
    )

    result = await agent.run(
        """Complete code quality audit:
        1. Find all Python files in src/omniforge/
        2. Check which files have corresponding tests in tests/
        3. For files without tests, list them
        4. Calculate test coverage percentage
        5. Provide recommendations for improving coverage
        """
    )

    print(f"Audit Results:\n{result}\n")


# =============================================================================
# Example 11: Using Custom Tools
# =============================================================================

async def example_11_custom_tools():
    """Agent with custom tool registry."""
    print("=== Example 11: Custom Tools ===\n")

    # Get default registry with all built-in tools registered
    registry = get_default_tool_registry()
    # Registry already has all built-in tools (bash, read, write, grep, glob, llm)

    agent = SimpleAutonomousAgent(
        tool_registry=registry,
        system_prompt="You have access to bash, file operations, and LLM tools."
    )

    result = await agent.run(
        "Use git to show me the last 5 commit messages"
    )

    print(f"Git History:\n{result}\n")


# =============================================================================
# Example 12: Streaming Events (Advanced)
# =============================================================================

async def example_12_streaming():
    """Watch agent reasoning in real-time."""
    print("=== Example 12: Streaming Events ===\n")

    from omniforge.agents.helpers import create_simple_task

    agent = SimpleAutonomousAgent(max_iterations=10)

    # Create task
    task = create_simple_task(
        message="Find and count all TypeScript files",
        agent_id=agent.identity.id,
    )

    # Stream events to see reasoning steps
    async for event in agent.process_task(task):
        if hasattr(event, "step"):
            step = event.step
            if step.type == "thinking":
                print(f"💭 Thinking: {step.thinking.content}")
            elif step.type == "tool_call":
                print(f"🔧 Tool: {step.tool_call.tool_name}")
                print(f"   Args: {step.tool_call.arguments}")
            elif step.type == "tool_result":
                if step.tool_result.success:
                    print(f"✅ Success")
                else:
                    print(f"❌ Error: {step.tool_result.error}")
        elif hasattr(event, "message_parts"):
            print(f"\n📝 Final Answer:")
            for part in event.message_parts:
                if hasattr(part, "text"):
                    print(f"{part.text}")

    print()


# =============================================================================
# Example 13: Error Handling
# =============================================================================

async def example_13_error_handling():
    """Handle errors gracefully."""
    print("=== Example 13: Error Handling ===\n")

    agent = SimpleAutonomousAgent(
        max_iterations=5,  # Low limit to trigger timeout
    )

    try:
        # Impossible task that will hit iteration limit
        result = await agent.run(
            "Keep searching forever for a file that doesn't exist"
        )
        print(f"Result: {result}\n")

    except RuntimeError as e:
        print(f"⚠️  Caught expected error: {e}\n")
        print("Tip: Increase max_iterations for complex tasks\n")


# =============================================================================
# Example 14: Batch Processing
# =============================================================================

async def example_14_batch():
    """Process multiple prompts in batch."""
    print("=== Example 14: Batch Processing ===\n")

    agent = SimpleAutonomousAgent(
        system_prompt="You are a file analyst. Be concise."
    )

    prompts = [
        "Count Python files in src/",
        "Count test files in tests/",
        "Find the largest Python file",
        "Find files with 'TODO' comments",
    ]

    results = await asyncio.gather(*[agent.run(prompt) for prompt in prompts])

    for prompt, result in zip(prompts, results):
        print(f"Q: {prompt}")
        print(f"A: {result}\n")


# =============================================================================
# Example 15: Different Models
# =============================================================================

async def example_15_models():
    """Use different LLM models."""
    print("=== Example 15: Different Models ===\n")

    models = ["claude-sonnet-4", "gpt-4", "claude-opus-4"]
    prompt = "What Python files are in src/omniforge/agents/?"

    for model in models:
        print(f"Using model: {model}")

        agent = SimpleAutonomousAgent(
            model=model,
            temperature=0.0,  # Deterministic
        )

        try:
            result = await agent.run(prompt)
            print(f"Result: {result}\n")
        except Exception as e:
            print(f"Error with {model}: {e}\n")


# =============================================================================
# Run All Examples
# =============================================================================

async def main():
    """Run all examples."""
    examples = [
        ("Simplest Usage", example_1_simplest),
        ("Basic Agent", example_2_basic),
        ("Custom System Prompt", example_3_custom_system_prompt),
        ("Configuration", example_4_configuration),
        ("File Operations", example_5_file_operations),
        ("Code Analysis", example_6_code_analysis),
        ("Search and Find", example_7_search),
        ("Data Processing", example_8_data_processing),
        ("Testing", example_9_testing),
        ("Complex Task", example_10_complex),
        ("Custom Tools", example_11_custom_tools),
        ("Streaming", example_12_streaming),
        ("Error Handling", example_13_error_handling),
        ("Batch Processing", example_14_batch),
        ("Different Models", example_15_models),
    ]

    print("=" * 70)
    print("SimpleAutonomousAgent Examples")
    print("=" * 70)
    print()

    for i, (name, example_func) in enumerate(examples, 1):
        print(f"\n{'=' * 70}")
        print(f"Example {i}: {name}")
        print(f"{'=' * 70}\n")

        try:
            await example_func()
        except Exception as e:
            print(f"⚠️  Example failed: {e}\n")

        print()


if __name__ == "__main__":
    # Run a single example
    asyncio.run(example_1_simplest())

    # Or run all examples
    # asyncio.run(main())
