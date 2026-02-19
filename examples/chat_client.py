#!/usr/bin/env python3
"""Simple CLI chat client for OmniForge API.

This script provides an interactive chat interface that connects to the
OmniForge chat API, eliminating the need to manually craft POST requests.
"""

import asyncio
import json
import sys
from typing import Optional

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


async def send_message(
    message: str, conversation_id: Optional[str] = None, base_url: str = "http://localhost:8000"
) -> Optional[str]:
    """Send a message to the chat API and stream the response.

    Args:
        message: The message to send
        conversation_id: Optional conversation ID to continue an existing conversation
        base_url: Base URL of the API (default: http://localhost:8000)

    Returns:
        The conversation ID from the response, or None if there was an error
    """
    url = f"{base_url}/api/v1/chat"
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    console.print(
                        f"[red]Error: {response.status_code} - {response.text}[/red]"
                    )
                    return None

                full_response = []
                response_conversation_id = None

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Parse SSE format
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        try:
                            parsed = json.loads(data)

                            if event_type == "chunk":
                                # Print content as it arrives
                                content = parsed.get("content", "")
                                console.print(content, end="")
                                full_response.append(content)
                            elif event_type == "done":
                                response_conversation_id = parsed.get("conversation_id")
                                # Print usage stats if available
                                usage = parsed.get("usage", {})
                                if usage:
                                    console.print(
                                        f"\n[dim]Tokens: {usage.get('total_tokens', 'N/A')}[/dim]"
                                    )
                            elif event_type == "error":
                                console.print(f"\n[red]Error: {parsed.get('error')}[/red]")
                                return None
                        except json.JSONDecodeError:
                            console.print(f"[yellow]Failed to parse: {data}[/yellow]")

                console.print()  # New line after response
                return response_conversation_id

    except httpx.ConnectError:
        console.print("[red]Error: Could not connect to the server.[/red]")
        console.print("[yellow]Make sure the server is running on {base_url}[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        return None


async def main() -> None:
    """Run the interactive chat client."""
    console.print(
        Panel.fit(
            "[bold cyan]OmniForge Chat Client[/bold cyan]\n"
            "Type your messages and press Enter to send.\n"
            "Commands: /quit or /exit to quit, /new to start a new conversation",
            border_style="cyan",
        )
    )

    conversation_id = None

    while True:
        try:
            # Get user input
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["/quit", "/exit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif user_input.lower() == "/new":
                conversation_id = None
                console.print("[yellow]Started a new conversation[/yellow]")
                continue

            # Send message and get response
            console.print("[bold blue]Assistant:[/bold blue] ", end="")
            conversation_id = await send_message(user_input, conversation_id)

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
