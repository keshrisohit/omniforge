#!/usr/bin/env python3
"""Service-layer chat client for testing ChatService directly.

This client tests the chat service without requiring a running HTTP server.
It directly instantiates ChatService and calls its methods, making it ideal
for development, testing, and debugging at the service layer.
"""

import asyncio
import json
import sys
from typing import Optional
from uuid import UUID

from rich.console import Console
from rich.panel import Panel

from omniforge.chat.models import ChatRequest
from omniforge.chat.service import ChatService

console = Console()


async def send_message_direct(
    service: ChatService,
    message: str,
    conversation_id: Optional[UUID] = None,
) -> Optional[UUID]:
    """Send a message directly to the ChatService and stream the response.

    Args:
        service: The ChatService instance to use
        message: The message to send
        conversation_id: Optional conversation ID to continue an existing conversation

    Returns:
        The conversation ID from the response, or None if there was an error
    """
    try:
        # Create chat request
        request = ChatRequest(message=message, conversation_id=conversation_id)

        full_response = []
        response_conversation_id = None
        event_type = None

        # Process the chat request and handle SSE-formatted events
        async for event_line in service.process_chat(request):
            # Parse SSE format
            for line in event_line.split("\n"):
                line = line.strip()
                if not line:
                    continue

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
                            # Extract conversation_id and usage info
                            conv_id = parsed.get("conversation_id")
                            if conv_id:
                                response_conversation_id = UUID(conv_id)

                            # Print usage stats if available
                            usage = parsed.get("usage", {})
                            if usage:
                                tokens = usage.get("tokens", "N/A")
                                console.print(f"\n[dim]Tokens: {tokens}[/dim]")

                        elif event_type == "error":
                            error_msg = parsed.get("message", "Unknown error")
                            error_code = parsed.get("code", "unknown")
                            console.print(
                                f"\n[red]Error ({error_code}): {error_msg}[/red]"
                            )
                            return None

                    except json.JSONDecodeError:
                        console.print(f"[yellow]Failed to parse: {data}[/yellow]")
                    except ValueError as e:
                        console.print(f"[yellow]Failed to parse UUID: {e}[/yellow]")

        console.print()  # New line after response
        return response_conversation_id

    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return None


async def learn main() -> None:
    """Run the interactive service-layer chat client."""
    console.print(
        Panel.fit(
            "[bold cyan]OmniForge Service-Layer Chat Client[/bold cyan]\n"
            "Direct service layer testing without HTTP server.\n\n"
            "Commands:\n"
            "  /quit or /exit - Exit the client\n"
            "  /new - Start a new conversation\n"
            "  /help - Show this help message",
            border_style="cyan",
            title="Service Chat Client",
        )
    )

    # Initialize the chat service directly
    console.print("[dim]Initializing ChatService...[/dim]")
    try:
        service = ChatService()
        console.print("[green]✓ ChatService initialized successfully[/green]\n")
    except Exception as e:
        console.print(f"[red]Failed to initialize ChatService: {e}[/red]")
        console.print(
            "[yellow]Make sure your .env file is configured with LLM settings.[/yellow]"
        )
        sys.exit(1)

    conversation_id: Optional[UUID] = None

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

            elif user_input.lower() == "/help":
                console.print(
                    Panel.fit(
                        "Commands:\n"
                        "  /quit or /exit - Exit the client\n"
                        "  /new - Start a new conversation\n"
                        "  /help - Show this help message\n\n"
                        "Just type your message and press Enter to chat!",
                        border_style="cyan",
                        title="Help",
                    )
                )
                continue

            # Send message and get response
            console.print("[bold blue]Assistant:[/bold blue] ", end="")
            conversation_id = await send_message_direct(
                service, user_input, conversation_id
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
