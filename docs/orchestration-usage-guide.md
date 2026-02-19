# Orchestration Usage Guide

This guide shows you how to use the orchestrator and handoff patterns for multi-agent coordination in OmniForge.

## Table of Contents

1. [Orchestrator Pattern](#orchestrator-pattern) - Coordinate multiple sub-agents
2. [Handoff Pattern](#handoff-pattern) - Transfer control to specialized agents
3. [Stream Router](#stream-router) - Route messages based on state
4. [Complete Example](#complete-example) - End-to-end integration
5. [Best Practices](#best-practices)

---

## Orchestrator Pattern

Use the orchestrator pattern when you need to query multiple sub-agents and synthesize their responses.

### Basic Usage

```python
from omniforge.orchestration.manager import OrchestrationManager, DelegationStrategy
from omniforge.orchestration.client import A2AClient
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.agents.models import AgentCard, AgentIdentity
from omniforge.storage.database import Database

# Initialize dependencies
database = Database("sqlite+aiosqlite:///omniforge.db")
await database.initialize()

conversation_repo = SQLiteConversationRepository(database)
a2a_client = A2AClient()

# Create orchestration manager
orchestrator = OrchestrationManager(
    a2a_client=a2a_client,
    conversation_repo=conversation_repo
)

# Define sub-agents to query
knowledge_agent = AgentCard(
    identity=AgentIdentity(
        id="knowledge-agent",
        name="Knowledge Base Agent",
        description="Searches internal documentation"
    ),
    service={"endpoint": "http://localhost:8001"}
)

research_agent = AgentCard(
    identity=AgentIdentity(
        id="research-agent",
        name="Research Agent",
        description="Searches external sources"
    ),
    service={"endpoint": "http://localhost:8002"}
)

# Delegate to multiple agents in parallel
results = await orchestrator.delegate_to_agents(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456",
    user_id="user-789",
    message="What are the best practices for error handling in Python agents?",
    target_agent_cards=[knowledge_agent, research_agent],
    strategy=DelegationStrategy.PARALLEL,  # Run simultaneously
    timeout_ms=30000
)

# Synthesize responses
final_response = orchestrator.synthesize_responses(results)
print(final_response)
# Output:
# From knowledge-agent:
# Based on our internal docs, key practices include...
#
# From research-agent:
# External research shows that...
```

### Delegation Strategies

#### 1. Parallel (Default)
Query all agents simultaneously, wait for all to complete:

```python
results = await orchestrator.delegate_to_agents(
    thread_id="thread-123",
    tenant_id="tenant-456",
    user_id="user-789",
    message="Your query here",
    target_agent_cards=[agent1, agent2, agent3],
    strategy=DelegationStrategy.PARALLEL
)
```

**Use when:** All agents provide independent insights you want to combine.

#### 2. Sequential
Query agents one at a time, in order:

```python
results = await orchestrator.delegate_to_agents(
    thread_id="thread-123",
    tenant_id="tenant-456",
    user_id="user-789",
    message="Your query here",
    target_agent_cards=[agent1, agent2, agent3],
    strategy=DelegationStrategy.SEQUENTIAL
)
```

**Use when:** Later agents need results from earlier agents (chained processing).

#### 3. First Success
Query all agents simultaneously, return first successful response:

```python
results = await orchestrator.delegate_to_agents(
    thread_id="thread-123",
    tenant_id="tenant-456",
    user_id="user-789",
    message="Your query here",
    target_agent_cards=[agent1, agent2, agent3],
    strategy=DelegationStrategy.FIRST_SUCCESS
)
```

**Use when:** Agents are redundant/fallbacks, first valid response is sufficient.

### Handling Results

```python
results = await orchestrator.delegate_to_agents(...)

# Check individual results
for result in results:
    if result.success:
        print(f"{result.agent_id}: {result.response}")
        print(f"Latency: {result.latency_ms}ms")
    else:
        print(f"{result.agent_id} failed: {result.error}")

# Synthesize all successful responses
synthesized = orchestrator.synthesize_responses(results)
```

---

## Handoff Pattern

Use the handoff pattern when you need to transfer control to a specialized agent for a stateful workflow.

### Basic Usage

```python
from omniforge.orchestration.handoff import HandoffManager, HandoffState
from omniforge.orchestration.client import A2AClient
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.agents.models import AgentCard, AgentIdentity

# Initialize dependencies
a2a_client = A2AClient()
conversation_repo = SQLiteConversationRepository(database)

# Create handoff manager
handoff_manager = HandoffManager(
    a2a_client=a2a_client,
    conversation_repo=conversation_repo
)

# Define specialized agent
skill_creation_agent = AgentCard(
    identity=AgentIdentity(
        id="skill-creation-agent",
        name="Skill Creation Assistant",
        description="Creates custom skills through conversation"
    ),
    service={"endpoint": "http://localhost:8003"}
)

# Initiate handoff
acceptance = await handoff_manager.initiate_handoff(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456",
    user_id="user-789",
    source_agent_id="main-chatbot",
    target_agent_card=skill_creation_agent,
    context_summary="User wants to create a skill for Slack alerts",
    handoff_reason="skill_creation_workflow"
)

if acceptance.accepted:
    print(f"Handoff accepted! Estimated duration: {acceptance.estimated_duration_seconds}s")
    # User now talks directly to skill-creation-agent
else:
    print(f"Handoff rejected: {acceptance.rejection_reason}")
```

### Check Active Handoff

```python
# Check if there's an active handoff for a thread
active_handoff = await handoff_manager.get_active_handoff(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456"
)

if active_handoff:
    print(f"Handoff active with {active_handoff.target_agent_id}")
    print(f"State: {active_handoff.state}")
    print(f"Reason: {active_handoff.handoff_reason}")
else:
    print("No active handoff")
```

### Complete Handoff

```python
from omniforge.orchestration.a2a_models import HandoffReturn

# When specialized agent finishes its work
handoff_return = HandoffReturn(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456",
    source_agent_id="skill-creation-agent",
    target_agent_id="main-chatbot",
    completion_status="completed",
    result_summary="Successfully created Slack alert skill",
    artifacts_created=["skill-slack-alerts.md"]
)

await handoff_manager.complete_handoff(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456",
    handoff_return=handoff_return
)

print("Control returned to main agent")
```

### Cancel Handoff

```python
# User wants to cancel mid-workflow
await handoff_manager.cancel_handoff(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456",
    reason="User cancelled skill creation"
)

print("Handoff cancelled, returned to main agent")
```

---

## Stream Router

Use the stream router to automatically route messages based on whether a handoff is active.

### Basic Usage

```python
from omniforge.orchestration.stream_router import StreamRouter
from omniforge.orchestration.handoff import HandoffManager
from omniforge.orchestration.manager import OrchestrationManager

# Create router with both managers
router = StreamRouter(
    handoff_manager=handoff_manager,
    orchestration_manager=orchestration_manager
)

# Route a message - automatically checks handoff state
async for chunk in router.route_message(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456",
    user_id="user-789",
    message="Help me configure the webhook URL"
):
    print(chunk, end="", flush=True)

# If handoff is active: routes to specialized agent
# If no handoff: routes to orchestration manager
```

### Check Handoff State

```python
# Check if handoff is active (helper method)
is_active = await router.is_handoff_active(
    thread_id="thread-uuid-123",
    tenant_id="tenant-456"
)

if is_active:
    print("Messages will route to specialized agent")
else:
    print("Messages will route to normal orchestration")
```

---

## Complete Example

Here's a full example showing orchestration and handoff working together:

```python
import asyncio
from uuid import uuid4
from omniforge.storage.database import Database
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.conversation.models import ConversationType
from omniforge.orchestration.client import A2AClient
from omniforge.orchestration.manager import OrchestrationManager, DelegationStrategy
from omniforge.orchestration.handoff import HandoffManager
from omniforge.orchestration.stream_router import StreamRouter
from omniforge.agents.models import AgentCard, AgentIdentity


async def main():
    # Setup
    database = Database("sqlite+aiosqlite:///omniforge.db")
    await database.initialize()

    conversation_repo = SQLiteConversationRepository(database)
    a2a_client = A2AClient()

    # Create managers
    orchestration_manager = OrchestrationManager(a2a_client, conversation_repo)
    handoff_manager = HandoffManager(a2a_client, conversation_repo)
    router = StreamRouter(handoff_manager, orchestration_manager)

    # Create conversation thread
    thread_id = str(uuid4())
    tenant_id = "acme-corp"
    user_id = "john-doe"

    await conversation_repo.create_conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title="Multi-agent Demo",
        conversation_type=ConversationType.CHAT,
        conversation_id=uuid4()
    )

    # Define agents
    knowledge_agent = AgentCard(
        identity=AgentIdentity(
            id="knowledge-agent",
            name="Knowledge Base",
            description="Internal docs"
        ),
        service={"endpoint": "http://localhost:8001"}
    )

    skill_agent = AgentCard(
        identity=AgentIdentity(
            id="skill-creation-agent",
            name="Skill Creator",
            description="Creates skills"
        ),
        service={"endpoint": "http://localhost:8002"}
    )

    # Scenario 1: Normal Q&A with orchestration
    print("\n=== Scenario 1: Q&A with Orchestration ===")
    results = await orchestration_manager.delegate_to_agents(
        thread_id=thread_id,
        tenant_id=tenant_id,
        user_id=user_id,
        message="What are the rate limits for our API?",
        target_agent_cards=[knowledge_agent],
        strategy=DelegationStrategy.PARALLEL
    )
    response = orchestration_manager.synthesize_responses(results)
    print(f"Response: {response}")

    # Scenario 2: User wants to create a skill (handoff)
    print("\n=== Scenario 2: Handoff to Skill Creation ===")
    acceptance = await handoff_manager.initiate_handoff(
        thread_id=thread_id,
        tenant_id=tenant_id,
        user_id=user_id,
        source_agent_id="main-agent",
        target_agent_card=skill_agent,
        context_summary="User wants to create a Slack notification skill",
        handoff_reason="skill_creation"
    )
    print(f"Handoff accepted: {acceptance.accepted}")

    # Scenario 3: User messages during handoff
    print("\n=== Scenario 3: Message Routing During Handoff ===")
    async for chunk in router.route_message(
        thread_id=thread_id,
        tenant_id=tenant_id,
        user_id=user_id,
        message="I want to send alerts to #engineering channel"
    ):
        print(f"Routed: {chunk}")

    # Scenario 4: Complete handoff
    print("\n=== Scenario 4: Complete Handoff ===")
    from omniforge.orchestration.a2a_models import HandoffReturn

    handoff_return = HandoffReturn(
        thread_id=thread_id,
        tenant_id=tenant_id,
        source_agent_id="skill-creation-agent",
        target_agent_id="main-agent",
        completion_status="completed",
        result_summary="Skill created successfully",
        artifacts_created=["slack-notifications.md"]
    )

    await handoff_manager.complete_handoff(
        thread_id=thread_id,
        tenant_id=tenant_id,
        handoff_return=handoff_return
    )
    print("Handoff completed, control returned to main agent")

    # Cleanup
    await a2a_client.close()
    await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Best Practices

### 1. Thread ID Management

```python
from uuid import uuid4

# Always use UUIDs for thread IDs
thread_id = str(uuid4())

# Thread ID must be consistent across all operations
# Pass it to every orchestration/handoff call
```

### 2. Tenant Isolation

```python
# ALWAYS validate thread belongs to tenant
from omniforge.orchestration.thread import ThreadManager

thread_manager = ThreadManager(conversation_repo)

is_valid = await thread_manager.validate_thread(
    thread_id=thread_id,
    tenant_id=tenant_id,
    user_id=user_id  # Optional: also validate user ownership
)

if not is_valid:
    raise PermissionError("Invalid thread access")
```

### 3. Error Handling

```python
from omniforge.orchestration.a2a_models import HandoffError, DelegationError

try:
    results = await orchestration_manager.delegate_to_agents(...)
except DelegationError as e:
    print(f"Delegation failed: {e}")
    # Handle gracefully - maybe use fallback agent

try:
    await handoff_manager.initiate_handoff(...)
except HandoffError as e:
    print(f"Handoff failed: {e}")
    # Maybe there's already an active handoff
```

### 4. Context Sanitization

```python
from omniforge.orchestration.sanitizer import ContextSanitizer

sanitizer = ContextSanitizer()

# Sanitize context before passing to sub-agents
safe_context = sanitizer.sanitize(
    "User's email is john@example.com and password is MyP@ssw0rd"
)
print(safe_context)
# Output: "User's email is [EMAIL] and password is [REDACTED]"
```

### 5. RBAC Permission Checks

```python
from omniforge.security.rbac import Permission, has_permission

# Check user has permission before delegating
if not await has_permission(user_id, tenant_id, Permission.ORCHESTRATION_DELEGATE):
    raise PermissionError("User cannot delegate tasks")

# Check user can initiate handoff
if not await has_permission(user_id, tenant_id, Permission.HANDOFF_INITIATE):
    raise PermissionError("User cannot initiate handoffs")
```

### 6. Logging

```python
import logging

logger = logging.getLogger("omniforge.orchestration")

# The managers already log internally, but you can add custom logs
logger.info(
    "Starting multi-agent workflow",
    extra={
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "workflow_type": "research_and_summarize"
    }
)
```

### 7. Resource Cleanup

```python
# Always close A2AClient when done
async def cleanup():
    await a2a_client.close()
    await database.dispose()

# Or use context managers
async with A2AClient() as client:
    # Use client
    pass
```

---

## Common Patterns

### Pattern 1: Main Agent with Sub-Agents

```python
class MainChatbot:
    def __init__(self, orchestrator: OrchestrationManager):
        self.orchestrator = orchestrator

    async def handle_message(self, thread_id: str, tenant_id: str,
                           user_id: str, message: str) -> str:
        # Determine intent
        if "search docs" in message.lower():
            # Use knowledge agent
            results = await self.orchestrator.delegate_to_agents(
                thread_id=thread_id,
                tenant_id=tenant_id,
                user_id=user_id,
                message=message,
                target_agent_cards=[self.knowledge_agent],
                strategy=DelegationStrategy.PARALLEL
            )
            return self.orchestrator.synthesize_responses(results)
        else:
            # Handle directly
            return "I can help with that..."
```

### Pattern 2: Stateful Workflow Agent

```python
class SkillCreationAgent:
    def __init__(self, handoff_manager: HandoffManager):
        self.handoff_manager = handoff_manager
        self.state_machine = SkillCreationFSM()

    async def accept_handoff(self, handoff_request):
        # Specialized agent accepts control
        # Start FSM workflow
        self.state_machine.start()
        return HandoffAccept(accepted=True)

    async def complete_workflow(self, thread_id: str, tenant_id: str):
        # Workflow finished
        handoff_return = HandoffReturn(
            thread_id=thread_id,
            tenant_id=tenant_id,
            source_agent_id="skill-creation-agent",
            target_agent_id="main-agent",
            completion_status="completed",
            result_summary="Skill created",
            artifacts_created=["skill.md"]
        )
        await self.handoff_manager.complete_handoff(
            thread_id, tenant_id, handoff_return
        )
```

### Pattern 3: Intelligent Router

```python
class SmartRouter:
    def __init__(self, router: StreamRouter, handoff_manager: HandoffManager):
        self.router = router
        self.handoff_manager = handoff_manager

    async def route_message(self, thread_id: str, tenant_id: str,
                          user_id: str, message: str):
        # Check for exit commands during handoff
        if message.lower() in ["exit", "cancel", "quit"]:
            active = await self.handoff_manager.get_active_handoff(
                thread_id, tenant_id
            )
            if active:
                await self.handoff_manager.cancel_handoff(
                    thread_id, tenant_id, "User requested exit"
                )
                return "Exited workflow, returned to main agent"

        # Normal routing
        async for chunk in self.router.route_message(
            thread_id, tenant_id, user_id, message
        ):
            yield chunk
```

---

## Next Steps

1. **Explore the tests** - See `tests/orchestration/` for more examples
2. **Read the technical plan** - `specs/technical-plan-orchestrator-handoff.md`
3. **Check the product spec** - `specs/orchestrator-handoff-patterns-spec.md`
4. **Build your agents** - Create agents that support orchestration and handoff
5. **Integrate with your app** - Add orchestration to your FastAPI endpoints

Happy orchestrating! 🚀
