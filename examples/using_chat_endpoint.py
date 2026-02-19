"""Example of using the simplified chat endpoint.

This example demonstrates how to use the new /api/v1/agents/{agent_id}/chat
endpoint for quick and easy agent interactions.

The chat endpoint provides two modes:
1. Streaming (SSE) - Real-time event streaming (default)
2. Non-streaming (JSON) - Simple request/response

Run this example after starting the server:
    python examples/start_server.py

Then in another terminal:
    python examples/using_chat_endpoint.py
"""

import json
from typing import Any

import requests

BASE_URL = "http://localhost:8000"


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def chat_streaming(agent_id: str, message: str) -> None:
    """Chat with agent using streaming mode (SSE).

    Args:
        agent_id: ID of the agent to chat with
        message: Message to send
    """
    print_section(f"Streaming Chat with {agent_id}")

    url = f"{BASE_URL}/api/v1/agents/{agent_id}/chat"
    payload = {
        "message": message,
        "stream": True,  # Enable streaming (default)
    }

    print(f"Sending: '{message}'")
    print("\nStreaming response:")
    print("-" * 40)

    response = requests.post(url, json=payload, stream=True)

    if response.status_code == 200:
        # Process SSE events
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                print(decoded)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

    print("-" * 40)


def chat_simple(agent_id: str, message: str) -> dict[str, Any]:
    """Chat with agent using simple JSON mode (non-streaming).

    Args:
        agent_id: ID of the agent to chat with
        message: Message to send

    Returns:
        Dictionary with task_id, response, and state
    """
    print_section(f"Simple JSON Chat with {agent_id}")

    url = f"{BASE_URL}/api/v1/agents/{agent_id}/chat"
    payload = {
        "message": message,
        "stream": False,  # Disable streaming for simple JSON response
    }

    print(f"Sending: '{message}'")

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        print("\nResponse:")
        print("-" * 40)
        print(json.dumps(data, indent=2))
        print("-" * 40)
        print(f"\nAgent Response: {data['response']}")
        print(f"Task ID: {data['task_id']}")
        print(f"State: {data['state']}")
        return data
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {}


def compare_with_traditional_approach(agent_id: str, message: str) -> None:
    """Compare chat endpoint with traditional task creation.

    Args:
        agent_id: ID of the agent
        message: Message to send
    """
    print_section("Comparison: Chat vs Traditional Task Creation")

    # Traditional approach (verbose)
    print("TRADITIONAL APPROACH (Verbose):")
    print("-" * 40)
    print("Request:")
    traditional_payload = {
        "message_parts": [{"type": "text", "text": message}],
        "tenant_id": "demo-tenant",
        "user_id": "demo-user",
    }
    print(json.dumps(traditional_payload, indent=2))
    print("\n# Must manually handle SSE stream parsing...")
    print("# Must extract message_parts from events...")
    print("# Must track task state manually...")
    print()

    # Chat approach (simple)
    print("CHAT ENDPOINT (Simple):")
    print("-" * 40)
    print("Request:")
    chat_payload = {
        "message": message,
        "stream": False,
    }
    print(json.dumps(chat_payload, indent=2))

    url = f"{BASE_URL}/api/v1/agents/{agent_id}/chat"
    response = requests.post(url, json=chat_payload)

    if response.status_code == 200:
        data = response.json()
        print("\nResponse (automatically parsed):")
        print(json.dumps(data, indent=2))
        print("\n✅ Simpler request, simpler response!")
    else:
        print(f"Error: {response.status_code}")


def main() -> None:
    """Run all chat endpoint examples."""
    agent_id = "echo-agent"

    print_section("Chat Endpoint Examples")
    print("This example demonstrates the new simplified chat endpoint")
    print("that makes it much easier to interact with agents.")

    # Example 1: Streaming mode (default)
    chat_streaming(agent_id, "Hello, streaming agent!")

    # Example 2: Simple JSON mode
    chat_simple(agent_id, "Hello, simple agent!")

    # Example 3: Custom user_id and tenant_id
    print_section("Chat with Custom User/Tenant ID")
    url = f"{BASE_URL}/api/v1/agents/{agent_id}/chat"
    payload = {
        "message": "Hello with custom IDs!",
        "stream": False,
        "user_id": "custom-user-123",
        "tenant_id": "custom-tenant-456",
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['response']}")
        print(f"✅ Custom user_id and tenant_id supported!")

    # Example 4: Compare with traditional approach
    compare_with_traditional_approach(agent_id, "Compare me!")

    print_section("Summary")
    print("The chat endpoint provides:")
    print("  ✅ Simpler request format (just a message string)")
    print("  ✅ Two modes: streaming (SSE) and simple (JSON)")
    print("  ✅ Automatic task creation internally")
    print("  ✅ No need to manually handle message_parts")
    print("  ✅ Cleaner API for simple use cases")
    print("\nFor advanced use cases, use the traditional task endpoint")
    print("at /api/v1/agents/{agent_id}/tasks")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("Make sure the server is running:")
        print("    python examples/start_server.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
