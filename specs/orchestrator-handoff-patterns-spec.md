# Orchestrator and Handoff Patterns for Multi-Agent Interaction

**Created**: 2026-02-05
**Last Updated**: 2026-02-05
**Version**: 1.0
**Status**: Draft

---

## Overview

This specification defines two fundamental interaction patterns for multi-agent collaboration in OmniForge: the **Orchestrator Pattern** and the **Handoff Pattern**. These patterns enable sophisticated agent coordination while maintaining conversation continuity through a shared thread_id. The Orchestrator Pattern keeps a main agent in control, coordinating sub-agents behind the scenes. The Handoff Pattern transfers direct control to specialized sub-agents when deep expertise or stateful workflows are needed. Both patterns support real-time streaming and integrate with Google's A2A v0.3 protocol for agent communication.

---

## Alignment with Product Vision

| Vision Principle | How This Feature Delivers |
|------------------|---------------------------|
| **Agents Build Agents** | Handoff pattern enables dedicated skill-creation agent to work directly with users |
| **Enterprise-Ready** | Thread-based isolation ensures multi-tenant security across agent interactions |
| **Reliability Over Speed** | Orchestrator pattern maintains oversight; handoff pattern provides clear accountability |
| **Simplicity Over Flexibility** | Two clear patterns (not dozens) cover the majority of multi-agent use cases |
| **Multi-Model Support** | Each sub-agent can use different models optimized for their specialty |

**Strategic Importance**: As OmniForge scales to support multiple specialized agents (skill creation, debugging, research, data analysis), clear interaction patterns become essential. Without these patterns, agent coordination devolves into ad-hoc implementations that are difficult to debug, secure, and maintain.

---

## User Personas

### Primary Users

- **Platform User (Chat Interface)**: Non-technical user interacting with OmniForge through the chatbot. They want seamless conversations regardless of which agent is responding. They should not need to understand agent architecture.
  - *Context*: Web-based chat interface
  - *Goals*: Get things done through conversation, create agents and skills, ask questions
  - *Pain Points*: Confusing agent switches, lost context, unexplained delays

- **SDK Developer**: Technical user building applications that orchestrate multiple agents. They need predictable APIs and clear control over agent delegation.
  - *Context*: IDE, writing Python code using OmniForge SDK
  - *Goals*: Programmatic agent coordination, real-time streaming, error handling
  - *Pain Points*: Unpredictable agent behavior, broken streaming, lost context

### Secondary Users

- **Platform Administrator**: Monitors agent interactions, ensures security policies are followed, tracks conversation flows for debugging and compliance.
  - *Goals*: Audit trails, security enforcement, troubleshooting
  - *Pain Points*: Unclear agent delegation chains, missing logs, cross-tenant leakage

---

## Problem Statement

OmniForge currently supports single-agent interactions and basic task delegation (TASK-009), but lacks standardized patterns for two critical scenarios:

1. **Coordinated Sub-Agent Queries**: When the main chatbot needs to query multiple sub-agents (e.g., knowledge base + research agent) and synthesize results, there is no standard pattern for maintaining conversation context and streaming intermediate results.

2. **Deep Specialized Workflows**: When a user wants to create a skill through the conversational skill builder, the current model requires the main agent to proxy every message. This adds latency, consumes main agent context, and prevents the specialized agent from maintaining its own stateful workflow (FSM).

**User Impact**:
- Without orchestrator pattern: Users wait longer for responses, see no intermediate feedback, and experience context loss when sub-agents are involved.
- Without handoff pattern: Skill creation is slower, more error-prone, and the main agent becomes a bottleneck for specialized workflows.

---

## Core Concept: thread_id as Conversation Anchor

The thread_id is the single most important concept in multi-agent interaction. It serves as the universal identifier that:

1. **Links All Agents**: Every agent in a conversation (main, orchestrated sub-agents, handed-off agents) shares the same thread_id
2. **Enables Context Retrieval**: Any agent can retrieve conversation history using thread_id + tenant_id
3. **Supports Traceability**: Audit logs can reconstruct the complete interaction flow using thread_id
4. **Maintains Security**: thread_id is always validated against tenant_id to prevent cross-tenant access

**Critical Rule**: thread_id is caller-provided and immutable throughout a conversation. The initiating client (frontend, SDK) generates the thread_id and passes it to every agent interaction.

---

## Pattern 1: Orchestrator Pattern

### When to Use

- Normal Q&A interactions
- Information retrieval from multiple sources
- Tasks where the main agent synthesizes sub-agent outputs
- Situations where users should see a unified response

### How It Works

```
User <-> Main Agent <-> Sub-Agent A
                    <-> Sub-Agent B
                    <-> Sub-Agent N
```

1. User sends message to Main Agent with thread_id
2. Main Agent decides which sub-agents to consult
3. Main Agent sends A2A messages to sub-agents (includes thread_id)
4. Sub-agents process and stream responses back to Main Agent
5. Main Agent synthesizes responses and streams to User
6. Main Agent stores synthesized response in conversation history

### User Experience: Q&A with Research Sub-Agent

**User Message**: "What are the best practices for error handling in Python agents?"

**Visible to User**:
```
[Thinking indicator: ~2s]
[Streaming response begins]

Based on my research, here are the key error handling practices for Python agents:

1. **Structured Error Types**: Define a hierarchy of custom exceptions...
[response continues streaming]
```

**Behind the Scenes** (not visible to user):
```
1. Main Agent receives message (thread_id: abc-123)
2. Main Agent identifies this as a knowledge query
3. Main Agent sends A2A task to Knowledge Sub-Agent:
   - thread_id: abc-123
   - parent_task_id: main-task-456
   - message: "error handling best practices Python agents"
4. Knowledge Sub-Agent streams results back
5. Main Agent synthesizes and formats response
6. Main Agent streams synthesized response to User
```

### Streaming Behavior

- **User sees**: Single continuous stream from Main Agent
- **Intermediate indicators**: Optional "thinking" or "researching" indicators
- **No visible agent switching**: User perceives one conversation partner
- **Error handling**: Main Agent shows graceful errors if sub-agents fail

---

## Pattern 2: Handoff Pattern

### When to Use

- Skill creation workflows (multi-step, stateful)
- Debugging sessions requiring specialized context
- Any workflow where:
  - The specialized agent needs direct user interaction
  - The workflow has multiple states (FSM)
  - The main agent would add unnecessary overhead

### How It Works

```
User <-> Main Agent -> Handoff -> Specialized Agent <-> User
                                         |
                                   [Direct interaction]
                                         |
                              Return to Main Agent (optional)
```

1. User initiates workflow (e.g., "I want to create a new skill")
2. Main Agent recognizes handoff trigger
3. Main Agent initiates handoff to Specialized Agent:
   - Passes thread_id
   - Passes conversation context summary
   - Notifies user of handoff
4. User now interacts directly with Specialized Agent
5. Specialized Agent maintains its own FSM state
6. When workflow completes (or user exits), control returns to Main Agent

### User Experience: Skill Creation Handoff

**User**: "I want to create a skill that summarizes Notion pages"

**Main Agent Response**:
```
I'll connect you with our Skill Creation Assistant who specializes
in building custom skills.

---

[Skill Creation Mode]
Hi! I'm here to help you create a skill for summarizing Notion pages.

Let's start with the basics:
1. What specific Notion pages or databases will this skill access?
2. How should the summaries be formatted (bullet points, paragraphs, etc.)?
```

**User** (now talking to Skill Creation Agent):
```
I want to summarize my project pages. Bullet points would be great.
```

**Skill Creation Agent**:
```
Got it! Let me gather a bit more information:

- Should the skill summarize all content or focus on specific sections?
- How long should each summary be?

[Current Progress: Gathering Requirements - 2/5 steps]
```

### Visual Indicators

When handoff occurs, the UI should clearly indicate:
- **Context switch notification**: "Connecting you with [Agent Name]..."
- **Agent identity**: Different avatar or name badge for specialized agent
- **Progress indicator**: For stateful workflows (e.g., "Step 2 of 5")
- **Exit option**: Clear way to return to main agent ("Exit skill creation")

### Handoff Protocol

```python
# Handoff message from Main Agent to Specialized Agent
{
    "type": "handoff",
    "thread_id": "abc-123",
    "tenant_id": "tenant-456",
    "user_id": "user-789",
    "source_agent_id": "main-chatbot",
    "target_agent_id": "skill-creation-agent",
    "context_summary": "User wants to create a Notion summarization skill",
    "conversation_history_count": 3,  # Recent messages to include
    "handoff_reason": "skill_creation_workflow"
}
```

---

## User Journeys

### Journey 1: Normal Q&A (Orchestrator Pattern)

**Context**: User asks a question that requires consulting a knowledge sub-agent.

1. **User asks question**: "How do I configure rate limiting for my agent?"
2. **Main Agent assesses**: Determines this needs knowledge base lookup
3. **Orchestration starts**: Main Agent queries Knowledge Agent (user sees "Researching...")
4. **Sub-Agent responds**: Streams relevant documentation
5. **Main Agent synthesizes**: Formats answer with examples
6. **User receives response**: Streaming response with clear, formatted answer
7. **Conversation recorded**: Full exchange stored under thread_id

**Key Experience**: User gets a complete, well-formatted answer without knowing multiple agents were involved.

### Journey 2: Skill Creation (Handoff Pattern)

**Context**: User wants to create a custom skill through conversation.

1. **User initiates**: "I want to create a skill that sends Slack alerts"
2. **Main Agent recognizes intent**: Triggers handoff to Skill Creation Agent
3. **Handoff notification**: User sees "Connecting you with Skill Creation Assistant..."
4. **Direct interaction begins**: User now talks to Skill Creation Agent
5. **FSM workflow progresses**:
   - GATHERING_REQUIREMENTS: Agent asks clarifying questions
   - DEFINING_TRIGGERS: Agent helps configure when skill runs
   - GENERATING_SKILL: Agent creates SKILL.md
   - TESTING: Agent helps validate the skill
   - COMPLETE: Skill is saved and activated
6. **Handoff return**: "Your skill is ready! Returning you to the main assistant."
7. **Main Agent confirms**: "Great, your 'Slack Alert' skill is now active."

**Key Experience**: User has a focused, guided experience with clear progress indicators.

### Journey 3: Agent-to-Agent Orchestration (SDK)

**Context**: Developer building a research application that coordinates multiple agents.

1. **Developer creates task**: Sends research query with thread_id
2. **Orchestrator receives**: Main Agent parses intent
3. **Parallel delegation**:
   - Sends task to Web Research Agent
   - Sends task to Internal Docs Agent
4. **Streaming aggregation**: Results stream back in real-time
5. **Developer receives**: Combined streaming response with source attribution
6. **Programmatic access**: Developer can access individual sub-task results

**Key Experience**: Clear API, predictable streaming, full control over orchestration.

### Journey 4: Handoff with User Cancellation

**Context**: User starts skill creation but changes their mind.

1. **Handoff initiated**: User begins skill creation workflow
2. **Mid-workflow exit**: User types "cancel" or clicks exit button
3. **Graceful termination**: Skill Creation Agent saves partial state
4. **Return to Main Agent**: "No problem! Returning you to the main assistant."
5. **Main Agent resumes**: "Let me know if you'd like to continue creating that skill later."
6. **State preserved**: Partial progress saved under thread_id for later resumption

**Key Experience**: User never feels trapped; exits are graceful with state preservation.

---

## Success Criteria

### User Outcomes

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response latency (orchestrator) | < 3s to first token | P95 latency from user message to first streamed token |
| Handoff transition time | < 1s | Time from handoff initiation to specialized agent response |
| Context preservation | 100% | No conversation history loss across handoffs |
| User confusion rate | < 5% | Users who can't tell which agent is responding (survey) |

### Technical Outcomes

| Metric | Target | Measurement |
|--------|--------|-------------|
| thread_id propagation | 100% | All agent interactions include correct thread_id |
| Cross-tenant isolation | 0 violations | Audit log review, security testing |
| Streaming reliability | 99.5% | Streams complete without dropped messages |
| A2A protocol compliance | Full v0.3 | Protocol conformance test suite |

### Business Outcomes

| Metric | Target | Measurement |
|--------|--------|-------------|
| Skill creation completion rate | > 70% | Users who complete skill creation after handoff |
| Support ticket reduction | 30% | Fewer "stuck in skill creation" tickets |
| Agent utilization | Balanced | No single agent becomes a bottleneck |

---

## Key Experiences

### Seamless Agent Transitions

When control passes between agents (orchestrator or handoff), users should experience:
- **No jarring interruptions**: Transitions feel like natural conversation flow
- **Clear context**: New agent demonstrates understanding of prior conversation
- **Consistent personality**: While agents may have different specialties, tone remains professional and helpful

### Real-Time Feedback

During multi-agent operations, users should always know:
- **Something is happening**: Typing indicators, progress bars, or status messages
- **What stage they're in**: Especially for stateful workflows (skill creation)
- **How to exit**: Clear escape hatches at every step

### Preserved Context

No matter how many agents are involved:
- **User never repeats themselves**: Context flows between agents automatically
- **History is complete**: User can scroll back and see full conversation
- **Resumption works**: User can continue where they left off after breaks

---

## Streaming Architecture

### Orchestrator Pattern Streaming

```
User Request
    |
    v
Main Agent (receives)
    |
    +---> Sub-Agent A (A2A stream) ---> Events
    |                                     |
    +---> Sub-Agent B (A2A stream) ---> Events
    |                                     |
    v                                     |
Aggregation Buffer <----------------------+
    |
    v
Synthesized Stream
    |
    v
User (SSE/WebSocket)
```

**Key Behaviors**:
- Main Agent may stream intermediate "thinking" tokens while awaiting sub-agents
- Sub-agent streams are consumed and buffered
- Final response is synthesized and streamed to user
- All events include thread_id for traceability

### Handoff Pattern Streaming

```
User Request
    |
    v
Main Agent (handoff decision)
    |
    v
Handoff Event (with thread_id)
    |
    v
Specialized Agent <---> User (direct stream)
    |
    v
Return Event (optional)
    |
    v
Main Agent (resumes)
```

**Key Behaviors**:
- During handoff, user's WebSocket/SSE connection routes to Specialized Agent
- Specialized Agent streams directly to user (no proxy through Main Agent)
- thread_id ensures conversation continuity
- Return to Main Agent is explicit (not automatic)

### Multimodal Streaming (A2A v0.3)

Both patterns support multimodal content:
- **Text**: Standard streaming tokens
- **Audio**: Chunked audio data (future)
- **Images**: Base64 or URI references
- **Files**: Artifact references with download URLs

---

## Thread ID: Design and Behavior

### Format

```
thread_id format: UUID v4
Example: "550e8400-e29b-41d4-a716-446655440000"
```

### Lifecycle

1. **Creation**: Client generates thread_id when starting new conversation
2. **Propagation**: Included in every message, task, and A2A communication
3. **Validation**: Every agent validates thread_id against tenant_id
4. **Persistence**: Stored with all conversation records
5. **Expiration**: No automatic expiration (conversation history persisted)

### Security Enforcement

```python
# Every agent operation must validate:
async def process_message(thread_id: str, tenant_id: str, message: str):
    # 1. Verify thread_id belongs to tenant_id
    conversation = await repo.get_conversation(thread_id, tenant_id)
    if not conversation:
        raise UnauthorizedError("Thread not found for tenant")

    # 2. Proceed with message processing
    ...
```

---

## A2A Protocol Integration

### Agent Card Extensions

For handoff support, Agent Cards include new capabilities:

```json
{
    "protocolVersion": "0.3",
    "identity": {
        "id": "skill-creation-agent",
        "name": "Skill Creation Assistant",
        "description": "Creates custom skills through conversation",
        "version": "1.0.0"
    },
    "capabilities": {
        "streaming": true,
        "push_notifications": false,
        "multi_turn": true,
        "hitl_support": true,
        "handoff_support": true,
        "stateful_workflows": true
    },
    "skills": [...],
    "handoff_triggers": ["create skill", "build skill", "new skill"],
    "workflow_states": ["gathering_requirements", "defining_triggers", "generating", "testing", "complete"]
}
```

### A2A Message Extensions

Handoff messages include additional metadata:

```python
class HandoffRequest(BaseModel):
    """Request to hand off conversation control to another agent."""

    thread_id: str
    tenant_id: str
    user_id: str
    source_agent_id: str
    target_agent_id: str
    context_summary: str
    recent_messages: list[Message]  # Last N messages for context
    handoff_reason: str
    preserve_state: bool = True
    return_expected: bool = True
```

---

## Edge Cases and Considerations

### Sub-Agent Unavailability (Orchestrator Pattern)

- **Scenario**: Knowledge sub-agent is down during Q&A
- **Handling**: Main Agent falls back to its own knowledge, notes limitation
- **User sees**: "I'm working with limited resources right now, but here's what I know..."

### Handoff Target Unavailable

- **Scenario**: Skill Creation Agent is down when user wants to create skill
- **Handling**: Main Agent explains situation, offers alternatives
- **User sees**: "The skill creation assistant is currently unavailable. Would you like me to help you with something else, or try again later?"

### User Abandons Handoff Mid-Workflow

- **Scenario**: User closes browser during skill creation
- **Handling**:
  - Partial state saved under thread_id
  - Next conversation resumes where they left off
- **User sees** (on return): "Welcome back! Would you like to continue creating your Slack alert skill?"

### Concurrent Handoffs Attempted

- **Scenario**: User tries to start two workflows simultaneously
- **Handling**: Second request queued or rejected with explanation
- **User sees**: "You're currently in a skill creation session. Would you like to finish that first?"

### Thread ID Mismatch

- **Scenario**: Client sends wrong thread_id
- **Handling**: Agent validates against tenant_id, rejects if mismatch
- **User sees**: Error message asking to start new conversation

### Long-Running Orchestration

- **Scenario**: Sub-agent takes > 30 seconds to respond
- **Handling**:
  - Main Agent sends periodic heartbeats
  - User sees progress indicators
  - Timeout triggers graceful degradation
- **User sees**: "This is taking longer than expected. I'll let you know when I have results..."

---

## Security and Multi-Tenancy

### Tenant Isolation

- **Rule**: All agent interactions must validate tenant_id
- **Enforcement**: Repository layer enforces tenant filtering on all queries
- **Audit**: Every cross-agent call logged with tenant context

### Authentication Flow

```
1. User authenticates with Platform
2. Platform issues session with tenant_id
3. Main Agent receives tenant_id in request context
4. Main Agent passes tenant_id to sub-agents via A2A
5. Sub-agents validate tenant_id before processing
6. Response flows back with tenant_id in audit trail
```

### RBAC Integration

- **Orchestrator Pattern**: Main Agent checks user permissions before delegating
- **Handoff Pattern**: Specialized Agent inherits user's permission context
- **Skill Creation**: User must have "skill:create" permission for handoff to succeed

### Data Handling

- **Conversation History**: Stored per tenant, never shared
- **Sub-Agent Context**: Minimal context shared (not full history)
- **Handoff Context**: Summary only, not verbatim messages (configurable)

---

## Open Questions

### Protocol Evolution

1. **A2A v0.3 vs Future Versions**: How do we handle protocol upgrades while maintaining compatibility?
2. **gRPC vs HTTP**: Should we support gRPC for internal agent communication (lower latency)?

### State Management

3. **Handoff State Location**: Should FSM state live in conversation table or separate workflow table?
4. **State Retention**: How long to keep partial workflow state after abandonment?

### User Experience

5. **Handoff Visibility**: Should users know when they're talking to a different agent?
6. **Progress Persistence**: Should workflow progress show in conversation sidebar?

### Performance

7. **Sub-Agent Caching**: Should orchestrated responses be cached for common queries?
8. **Connection Pooling**: How to manage WebSocket/SSE connections across handoffs?

---

## Out of Scope (For Now)

- **Nested Handoffs**: Agent A hands off to Agent B, which hands off to Agent C
- **Multi-User Handoffs**: Multiple users in same thread with different handoffs
- **Cross-Tenant Orchestration**: Agents from different tenants collaborating
- **Custom Handoff Triggers**: User-defined phrases that trigger handoffs
- **Agent Marketplace Integration**: Third-party agents participating in handoffs
- **Voice/Video Handoffs**: Multimodal handoffs beyond text

---

## Evolution Notes

### 2026-02-05 (Initial Draft)

- Created specification based on analysis session #S89
- Defined two core patterns: Orchestrator and Handoff
- Established thread_id as the conversation anchor
- Integrated with existing conversation persistence (orm.py, sqlite_repository.py)
- Aligned with A2A v0.3 protocol and existing orchestration infrastructure
- Key design decisions:
  - thread_id is caller-provided, immutable
  - Handoff is explicit (not automatic)
  - Streaming flows differently per pattern
  - State persistence uses existing conversation infrastructure
- Open questions documented for technical planning phase
- Next steps: Technical planning, task decomposition, implementation

---

## References

- [OmniForge Product Vision](/Users/sohitkumar/code/omniforge/specs/product-vision.md)
- [Base Agent Interface Spec](/Users/sohitkumar/code/omniforge/specs/base-agent-interface-spec.md)
- [Conversational Skill Builder Spec](/Users/sohitkumar/code/omniforge/specs/product-spec-conversational-skill-builder.md)
- [Existing Orchestration Implementation](/Users/sohitkumar/code/omniforge/src/omniforge/orchestration/)
- [Conversation Persistence Layer](/Users/sohitkumar/code/omniforge/src/omniforge/conversation/)
- [Google A2A Protocol](https://a2a-protocol.org/latest/specification/)
