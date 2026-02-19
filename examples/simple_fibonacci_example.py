"""Simple example demonstrating Fibonacci numbers without rate limit issues.

This example shows how to use the autonomous agent with retry logic
to handle Groq's rate limits gracefully.
"""

import asyncio
import time
from omniforge.agents.autonomous_simple import run_autonomous_agent


async def example_with_retry():
    """Run autonomous agent with retry logic for rate limits."""
    print("=== Fibonacci Numbers with Autonomous Agent ===\n")
    print("Note: Groq free tier has rate limits. This may take a minute...\n")

    max_retries = 5
    retry_delay = 10  # seconds

    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}...")

            result = await run_autonomous_agent(
                "Write and execute a Python program to print the first 10 Fibonacci numbers"
            )

            print(f"\n=== Result ===")
            print(result)
            return

        except Exception as e:
            error_msg = str(e)

            # Check if it's a rate limit error
            if "rate_limit" in error_msg.lower() or "RateLimitError" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"\nFailed after {max_retries} attempts due to rate limits.")
                    print("\nSuggestions:")
                    print("1. Wait a minute and try again")
                    print("2. Upgrade your Groq account at https://console.groq.com/settings/billing")
                    print("3. Use a different LLM provider (OpenAI, Anthropic, etc.)")
            else:
                print(f"Error: {error_msg}")
                raise


async def direct_bash_example():
    """Direct example using bash tool without LLM (no rate limits)."""
    print("\n=== Direct Fibonacci Example (No Rate Limits) ===\n")

    from omniforge.tools.builtin.bash import BashTool
    from omniforge.tools.base import ToolCallContext

    tool = BashTool()
    context = ToolCallContext(
        correlation_id='fib-1',
        task_id='fib-task',
        agent_id='direct'
    )

    # Execute Fibonacci program
    result = await tool.execute(context, {
        'command': '''python -c "
a, b = 0, 1
print('First 10 Fibonacci numbers:')
for i in range(10):
    print(f'{i+1}. {a}')
    a, b = b, a + b
"'''
    })

    if result.success:
        print(result.result['stdout'])
    else:
        print(f"Error: {result.error}")


async def main():
    """Run examples."""
    # Run direct example first (always works, no rate limits)
    await direct_bash_example()

    print("\n" + "="*60 + "\n")

    # Then try autonomous agent (may hit rate limits)
    await example_with_retry()


if __name__ == "__main__":
    asyncio.run(main())
