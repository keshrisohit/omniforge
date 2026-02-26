#!/usr/bin/env python3
"""
OmniForge Chat — powered by the Master Agent

The Master Agent uses a ReAct (Reason-Act-Observe) loop with platform tools
to handle requests autonomously:
  - "Create an agent that..."  → calls create_agent tool
  - "List my agents"          → calls list_agents tool
  - "Create a skill for..."   → delegates to SkillCreationAgent (A2A sub-agent)
  - "Talk to <agent>"         → delegates to that agent via delegate_to_agent tool
  - Anything else             → free-form LLM reasoning

Usage:
    python examples/chat.py [DEBUG|INFO|WARNING]
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging — set OMNIFORGE_LOG=DEBUG to see full routing trace
_log_level = getattr(logging, (sys.argv[1] if len(sys.argv) > 1 else "").upper(), None)
if not isinstance(_log_level, int):
    _log_level = logging.WARNING
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)

from omniforge.agents.registry import AgentRegistry
from omniforge.chat.master_response_generator import MasterResponseGenerator
from omniforge.conversation.models import Message, MessageRole
from omniforge.storage.memory import InMemoryAgentRepository


async def chat() -> None:
    registry = AgentRegistry(repository=InMemoryAgentRepository())
    generator = MasterResponseGenerator(
        agent_registry=registry,
        tenant_id="local",
        user_id="user",
    )

    # Stable session ID so MasterResponseGenerator can track conversation flow
    session_id = str(uuid4())
    conversation_id = uuid4()
    history: list[Message] = []

    print("\nOmniForge  —  Master Agent ready")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        # Add user message to history before generating response
        history.append(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_input,
                created_at=datetime.utcnow(),
            )
        )

        print("Agent: ", end="", flush=True)
        response_chunks: list[str] = []
        try:
            async for chunk in generator.generate_stream(
                user_input,
                conversation_history=history[:-1],  # prior turns only
                session_id=session_id,
            ):
                print(chunk, end="", flush=True)
                response_chunks.append(chunk)
        except Exception as e:
            print(f"\n[Error: {e}]", end="")
        print("\n")

        # Add assistant response to history for context on next turn
        if response_chunks:
            history.append(
                Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content="".join(response_chunks),
                    created_at=datetime.utcnow(),
                )
            )


if __name__ == "__main__":
    asyncio.run(chat())

