"""Simple server startup script for OmniForge API.

This script starts the FastAPI server with uvicorn, registers the EchoAgent,
and provides a ready-to-use development server.
"""

import asyncio

import uvicorn
from echo_agent import EchoAgent

from omniforge.agents.registry import AgentRegistry
from omniforge.api.routes.agents import _agent_repository


async def register_demo_agent() -> None:
    """Register the EchoAgent on server startup."""
    registry = AgentRegistry(_agent_repository)
    echo_agent = EchoAgent()
    await registry.register(echo_agent)
    print(f"✅ Registered {echo_agent.identity.name} (ID: {echo_agent.identity.id})")


def main() -> None:
    """Start the OmniForge API server with EchoAgent registered."""
    print("=" * 80)
    print("OmniForge API Server")
    print("=" * 80)
    print()
    print("📦 Registering demo agent...")

    # Register the EchoAgent
    asyncio.run(register_demo_agent())

    print()
    print("🚀 Starting server...")
    print("   API docs: http://localhost:8000/docs")
    print("   Health check: http://localhost:8000/health")
    print()
    print("Available endpoints:")
    print("   GET  /.well-known/agent-card.json - Platform agent card")
    print("   GET  /api/v1/agents - List all agents")
    print("   GET  /api/v1/agents/{agent_id} - Get agent card")
    print("   POST /api/v1/agents/{agent_id}/tasks - Create task (SSE stream)")
    print("   GET  /api/v1/agents/{agent_id}/tasks/{task_id} - Get task status")
    print("   POST /api/v1/agents/{agent_id}/tasks/{task_id}/send - Send message (SSE)")
    print()

    # Start uvicorn server
    uvicorn.run(
        "omniforge.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
