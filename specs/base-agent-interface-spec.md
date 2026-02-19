# Base Agent Interface (A2A Protocol)

**Created**: 2026-01-03
**Last Updated**: 2026-01-03
**Version**: 1.0
**Status**: Draft

## Overview

The Base Agent Interface establishes a foundational abstraction for all agents in OmniForge, implementing Google's Agent2Agent (A2A) protocol to enable interoperability between agents. This interface defines how agents identify themselves, advertise capabilities, communicate with each other, and participate in task-based workflows. By adopting the A2A standard, OmniForge agents can interoperate with the broader ecosystem of A2A-compliant systems while maintaining enterprise-grade security, multi-tenancy, and human-in-the-loop capabilities.

## Alignment with Product Vision

This specification directly advances OmniForge's core vision of being an "agent-first platform where agents build agents":

- **Agents as First-Class Citizens**: The base interface treats agents as autonomous peers that can discover and collaborate with each other, not just tools to be orchestrated
- **Dual Deployment Support**: The interface works identically whether accessed via the Python SDK (open source) or the Premium Platform, enabling seamless transitions
- **Enterprise-Ready Foundation**: Multi-tenancy, RBAC, and security are embedded in the agent identity and authentication model from day one
- **Interoperability**: A2A compliance means OmniForge agents can work with agents from any A2A-compatible platform, expanding the ecosystem
- **Human-in-the-Loop**: The A2A task lifecycle includes explicit states for requiring human input, aligning with OmniForge's HITL requirements

## User Personas

### Primary Users

- **Platform Developer (SDK User)**: A software developer using the Python SDK to create custom agents. They need a clear, well-documented interface with type safety and minimal boilerplate. They want to focus on agent logic, not protocol implementation details.
  - *Context*: Working in their IDE, writing Python code
  - *Goals*: Create agents quickly, integrate with existing systems, test locally before deployment
  - *Pain Points*: Verbose configuration, unclear extension points, breaking changes between versions

- **Platform Developer (API User)**: A developer integrating OmniForge agents into their application via REST API. They need clear API contracts, predictable behavior, and comprehensive error handling.
  - *Context*: Building microservices or frontend applications that orchestrate agents
  - *Goals*: Reliable agent invocation, real-time streaming updates, proper error handling
  - *Pain Points*: Inconsistent API responses, poor documentation, difficult debugging

- **Business User (Chat Agent User)**: A non-technical user creating agents through the OmniForge chatbot interface. They describe what they want, and the platform creates the agent for them.
  - *Context*: Using the web-based chat interface
  - *Goals*: Create working agents without coding, understand what their agents can do
  - *Pain Points*: Technical jargon, unclear feedback, limited customization options

### Secondary Users

- **Platform Administrator**: Manages agent deployments, monitors usage, and enforces policies. Needs visibility into agent capabilities, usage patterns, and security compliance.
  - *Goals*: Governance, cost management, security enforcement
  - *Pain Points*: Lack of observability, inconsistent agent metadata, manual policy enforcement

- **External Agent Developer**: A developer building A2A-compliant agents on another platform who wants to integrate with OmniForge agents.
  - *Goals*: Seamless interoperability, clear capability discovery, predictable communication
  - *Pain Points*: Protocol deviations, undocumented extensions, authentication complexity

## Problem Statement

Currently, OmniForge has a single chatbot agent implementation (core-chatbot-agent) that serves as the conversational interface. As the platform grows to support multiple agent types, several problems emerge:

1. **No Standard Agent Interface**: Each new agent type would require implementing communication, streaming, and lifecycle management from scratch, leading to inconsistency and duplication

2. **No Interoperability**: Without a standard protocol, agents cannot discover or communicate with each other, limiting the "agents build agents" vision

3. **No Capability Discovery**: Clients have no way to programmatically determine what an agent can do, forcing hard-coded integrations

4. **No Standard Task Model**: Long-running operations lack a consistent lifecycle model, making it difficult to track progress, handle failures, or support human review

5. **Creation Friction**: Creating agents requires direct Python development; there is no path for API-based or chat-driven agent creation

The base agent interface solves these problems by providing a common foundation that all agents implement, enabling consistent behavior, interoperability, and multiple creation pathways.

## User Journeys

### Journey 1: SDK Developer Creates a Custom Agent

**Context**: A developer wants to create a custom agent that processes documents and extracts structured data.

1. **Developer installs SDK** - They run `pip install omniforge` and import the base agent interface
2. **Developer extends BaseAgent** - They create a new class inheriting from `BaseAgent`, implementing required methods
3. **Developer defines capabilities** - They specify skills (document processing, data extraction) using declarative decorators or configuration
4. **Developer implements logic** - They write the `process_task` method containing their custom logic
5. **Developer runs locally** - They test the agent locally using the SDK's built-in test server
6. **Agent card auto-generated** - The SDK generates a compliant A2A Agent Card from the class definition
7. **Developer deploys** - They deploy to OmniForge platform or run standalone via the SDK

**Key Experience**: The transition from "idea" to "running agent" should feel natural. The developer focuses on their domain logic while the framework handles protocol compliance.

### Journey 2: API User Invokes an Agent

**Context**: A frontend application needs to invoke an agent to complete a task and display streaming results.

1. **Client discovers agent** - They fetch the agent's Agent Card from the well-known endpoint to understand capabilities
2. **Client sends task** - They POST a message to the agent's endpoint with their request
3. **Agent acknowledges** - The agent returns immediately with a task ID and "submitted" status
4. **Client receives updates** - Via SSE stream, the client receives real-time progress updates
5. **Agent requests input** (optional) - If the agent needs clarification, it transitions to "input_required" state
6. **Client provides input** - The client sends additional information via the task endpoint
7. **Task completes** - The agent sends final artifacts and transitions to "completed" status
8. **Client processes results** - The client extracts artifacts from the final task state

**Key Experience**: The streaming updates keep the user informed without polling. The task lifecycle is predictable and self-describing.

### Journey 3: Business User Creates Agent via Chat

**Context**: A business user wants to create an agent that monitors their sales data and alerts them to anomalies.

1. **User starts conversation** - They open the OmniForge chat interface and describe what they want
2. **Chat agent asks questions** - The platform asks clarifying questions: "What data sources? What constitutes an anomaly? How should alerts be delivered?"
3. **User provides details** - They answer in natural language: "Salesforce data, any drop > 20% week-over-week, notify via Slack"
4. **Chat agent proposes agent** - The platform summarizes the agent capabilities and asks for confirmation
5. **User approves** - They confirm the proposed configuration
6. **Agent created** - The platform creates a new agent instance with the specified capabilities
7. **User receives Agent Card** - They can view their agent's capabilities and share the endpoint with their team
8. **Agent begins operating** - The agent starts monitoring and alerting as configured

**Key Experience**: The conversation feels natural and guided. The user never sees YAML, JSON, or code. The resulting agent is a first-class citizen with a proper Agent Card.

### Journey 4: Agent-to-Agent Collaboration

**Context**: A "research agent" needs to delegate a subtask to a "data analysis agent" to complete a user's request.

1. **Research agent receives task** - User asks for a market analysis report
2. **Agent discovers peers** - Research agent queries the agent registry for agents with "data-analysis" skills
3. **Agent selects collaborator** - It evaluates Agent Cards and selects the best-suited analysis agent
4. **Agent delegates task** - Research agent creates a child task on the analysis agent
5. **Agents communicate** - Analysis agent streams results back to research agent
6. **Results integrated** - Research agent incorporates analysis into its own response
7. **Task completes** - Research agent delivers the complete report to the user

**Key Experience**: Agent collaboration is transparent and traceable. The user sees a unified response but can inspect the collaboration chain if needed.

### Journey 5: Human-in-the-Loop Review

**Context**: An agent needs human approval before taking a sensitive action (sending an email, making a purchase, modifying data).

1. **Agent processes task** - Agent prepares an action (e.g., draft email to 1000 customers)
2. **Agent requires approval** - Agent transitions task to "input_required" state with a review request
3. **Human notified** - Platform notifies the appropriate human reviewer (based on RBAC)
4. **Human reviews** - Reviewer sees the proposed action in a clear, structured format
5. **Human decides** - Reviewer approves, rejects, or requests modifications
6. **Agent receives decision** - Agent resumes task based on the decision
7. **Task completes** - Action is executed (or not) based on human input

**Key Experience**: The handoff to humans is seamless. Reviewers have context and can make informed decisions quickly.

## Success Criteria

### User Outcomes

- **Developer Productivity**: A developer can create a new agent type with custom logic in under 30 minutes, including local testing
- **Time to First Response**: API clients receive initial task acknowledgment within 100ms of request
- **Streaming Reliability**: 99%+ of streaming connections complete successfully (excluding client disconnects)
- **Discovery Works**: Clients can programmatically discover all agent capabilities from the Agent Card
- **Cross-Platform Interop**: OmniForge agents can successfully communicate with external A2A-compliant agents

### Business Outcomes

- **Foundation for Scale**: The interface supports creating new agent types without modifying core platform code
- **Ecosystem Compatibility**: Adopting A2A positions OmniForge to participate in the growing multi-agent ecosystem
- **Enterprise Adoption**: Built-in RBAC, multi-tenancy, and HITL capabilities address enterprise requirements

### Technical Outcomes

- **A2A Compliance**: Interface passes A2A protocol conformance tests for version 0.3
- **Type Safety**: 100% type annotation coverage with mypy strict mode
- **Test Coverage**: Minimum 80% test coverage for base interface code
- **Backward Compatibility**: SDK maintains semantic versioning; minor versions are backward compatible

## Key Experiences

The moments that define quality for this feature:

### Agent Creation Experience
When a developer creates their first agent, the process should feel like extending a well-designed class, not wrestling with infrastructure. The SDK should provide sensible defaults for everything except the core business logic. A minimal agent should be expressible in under 20 lines of code.

### Capability Discovery Experience
When a client fetches an Agent Card, they should immediately understand what the agent can do. Skills should be descriptive, examples should be concrete, and the format should be consistent. An external system should be able to integrate with an OmniForge agent based solely on its Agent Card.

### Task Progress Experience
During long-running tasks, users should never wonder "is it still working?" The streaming updates should provide meaningful progress indicators, not just heartbeats. When a task stalls or fails, the reason should be clear and actionable.

### Error Handling Experience
When something goes wrong, the error should include enough context to diagnose and resolve the issue. Error codes should be consistent across all agents. Stack traces should be available in debug mode but hidden from end users.

### Multi-Tenancy Experience
When operating in a multi-tenant environment, agents should be completely isolated by default. A tenant should never see another tenant's agents, tasks, or data. RBAC policies should be enforceable at the agent, skill, and task levels.

## Core Concepts (A2A Alignment)

The base agent interface implements these A2A protocol concepts:

### Agent Card

A JSON metadata document describing the agent's identity, capabilities, and connection information. This is the primary discovery mechanism.

**Key Fields**:
- `id`: Unique identifier (UUID or URN)
- `name`: Human-readable agent name
- `description`: What the agent does
- `version`: Agent version
- `protocolVersion`: A2A protocol version ("0.3")
- `serviceEndpoint`: URL for agent communication
- `capabilities`: Feature flags (streaming, push notifications)
- `skills`: Array of skills the agent offers
- `security`: Authentication requirements

### Skills

Discrete capabilities that an agent offers. Each skill has:
- `id`: Unique skill identifier
- `name`: Human-readable skill name
- `description`: What the skill does
- `tags`: Categorization tags for discovery
- `examples`: Example inputs that invoke this skill
- `inputModes`: Accepted content types
- `outputModes`: Produced content types

### Tasks

The fundamental unit of work. A task represents a request from a client to an agent and tracks its progress through a defined lifecycle.

**Task States**:
- `submitted`: Task received, processing not yet started
- `working`: Agent is actively processing
- `input_required`: Agent needs additional input (HITL trigger)
- `auth_required`: Additional authentication needed
- `completed`: Task finished successfully
- `failed`: Task finished with error
- `cancelled`: Task cancelled by client
- `rejected`: Agent declined to process the task

### Messages and Parts

Communication between client and agent consists of messages containing parts:
- **TextPart**: Plain text or markdown content
- **FilePart**: File references (inline or URI-based)
- **DataPart**: Structured JSON data

### Artifacts

Outputs generated by an agent during task processing. Artifacts are composed of parts and represent deliverables (documents, data, files).

## Agent Interface Design

### Base Agent Interface (Python)

The SDK provides an abstract base class that all agents implement:

```
BaseAgent
    |
    +-- identity: AgentIdentity
    |   +-- id: UUID
    |   +-- name: str
    |   +-- description: str
    |   +-- version: str
    |
    +-- capabilities: AgentCapabilities
    |   +-- streaming: bool
    |   +-- push_notifications: bool
    |   +-- multi_turn: bool
    |   +-- hitl_support: bool
    |
    +-- skills: List[AgentSkill]
    |   +-- id, name, description, tags, examples
    |
    +-- security: SecurityConfig
    |   +-- auth_schemes: List[AuthScheme]
    |   +-- tenant_isolation: bool
    |
    +-- get_agent_card() -> AgentCard
    +-- process_task(task: Task) -> AsyncIterator[TaskEvent]
    +-- handle_message(task_id, message) -> AsyncIterator[TaskEvent]
    +-- get_task(task_id) -> Task
    +-- cancel_task(task_id) -> Task
    +-- list_tasks(filters) -> List[Task]
```

### Agent Creation Modes

#### Mode 1: SDK (Python Class)

Developers extend `BaseAgent` and implement required methods:

```
class DocumentProcessorAgent(BaseAgent):
    name = "Document Processor"
    description = "Extracts structured data from documents"
    skills = [
        Skill(
            id="extract_data",
            name="Extract Data",
            description="Extract key-value data from documents",
            tags=["extraction", "documents"],
            examples=["Extract customer info from this invoice"]
        )
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        # Implementation here
        ...
```

#### Mode 2: REST API (Agent Definition)

Platform users create agents by POSTing an agent definition:

```
POST /api/v1/agents
{
    "name": "Document Processor",
    "description": "Extracts structured data from documents",
    "skills": [...],
    "configuration": {...}
}
```

#### Mode 3: Chat Interface (Natural Language)

Users describe the agent to the OmniForge chat agent, which translates their description into an agent definition and creates it on their behalf.

## Communication Patterns

### Request/Response with Streaming (SSE)

Primary pattern for interactive use:

1. Client sends message to `/tasks/{id}/send` or creates new task
2. Server returns SSE stream
3. Stream yields events: `task_status`, `message`, `artifact`, `done`, `error`
4. Client processes events as they arrive
5. Final `done` event signals completion

### Push Notifications

For long-running or asynchronous tasks:

1. Client registers webhook endpoint
2. Server sends updates to webhook as JSON payloads
3. Client acknowledges receipt
4. Server retries on failure with exponential backoff

### Polling (Fallback)

For environments where streaming is not available:

1. Client creates task and receives task ID
2. Client periodically calls `GET /tasks/{id}`
3. Client checks status and extracts new messages/artifacts
4. Client stops polling when terminal state reached

## Enterprise Features

### Multi-Tenancy

- Each agent instance is scoped to a tenant
- Agent Cards include tenant context in authenticated requests
- Task isolation enforced at the data layer
- Cross-tenant agent sharing requires explicit federation

### RBAC Integration

- Skills can require specific permissions
- Task creation can be restricted by role
- HITL routing based on role assignments
- Agent management permissions separate from invocation permissions

### Security

- Agent Card declares supported authentication schemes
- Per-tenant API key management
- OAuth 2.0 / OIDC support for enterprise SSO
- mTLS for agent-to-agent communication
- Audit logging for all agent operations

### Human-in-the-Loop (HITL)

- `input_required` state triggers HITL workflow
- Configurable routing rules (role-based, round-robin, skills-based)
- Time-based escalation for unreviewed items
- Approval workflows with audit trail

## API Endpoints

### Agent Discovery

- `GET /.well-known/agent-card.json` - Public Agent Card
- `GET /agent-card` - Extended Agent Card (authenticated)

### Task Management

- `POST /tasks` - Create new task with initial message
- `GET /tasks/{id}` - Get task status and history
- `POST /tasks/{id}/send` - Send message to existing task (streaming response)
- `POST /tasks/{id}/cancel` - Cancel a task
- `GET /tasks` - List tasks (with filters)

### Push Notifications

- `POST /notifications/config` - Register webhook
- `GET /notifications/config` - Get current webhook config
- `DELETE /notifications/config` - Remove webhook

## Edge Cases and Considerations

### Long-Running Tasks
- Tasks may run for minutes or hours (e.g., data processing)
- Streaming connections may time out; push notifications provide reliable delivery
- Task state must be durable across agent restarts

### Agent Unavailability
- What happens when a target agent is offline during agent-to-agent communication?
- Consider retry policies, circuit breakers, and fallback agents
- Agent Card should indicate availability/health endpoints

### Message Size Limits
- Define reasonable limits for message and artifact sizes
- Large files should use URI references rather than inline content
- Consider chunked transfer for streaming large artifacts

### Rate Limiting
- Agents should support rate limiting at the task creation level
- Rate limit information should be included in Agent Card capabilities
- Error responses should include retry-after guidance

### Version Compatibility
- Agent Card includes protocol version
- Clients should handle version negotiation gracefully
- Breaking changes require major version increment

### Skill Conflicts
- What if multiple skills could match a given request?
- Consider priority, specificity, or explicit skill selection

## Open Questions

### Protocol Version
- A2A is at version 0.3 and still evolving. How do we handle protocol updates?
- Should we pin to a specific version or support multiple versions?

### Agent Registry
- How do agents discover other agents for collaboration?
- Is there a centralized registry, or do agents know their peers directly?
- How does multi-tenant discovery work?

### State Persistence
- Where is task state stored (in-memory, database, distributed cache)?
- How long should completed tasks be retained?
- How do we handle task recovery after agent restart?

### Tool/Function Integration
- A2A focuses on message passing; how do we integrate MCP-style tool calls?
- Can skills be exposed as MCP tools and vice versa?

### Streaming Backpressure
- How do we handle slow clients that cannot keep up with stream output?
- Should we buffer, pause generation, or disconnect?

### Authentication Complexity
- Supporting multiple auth schemes adds complexity
- Should we start with a subset (API key, OAuth) and expand?

### Chat Agent Creation Limits
- What agent capabilities can be created via chat vs. requiring code?
- How do we validate and sandbox user-defined logic?

## Out of Scope (For Now)

- **Agent Marketplace**: Public discovery and sharing of agents across organizations
- **Billing/Metering**: Usage-based charging for agent invocations
- **Agent Versioning**: Multiple versions of the same agent running simultaneously
- **Distributed Agents**: Agents spanning multiple nodes/regions
- **Real-Time Collaboration**: Multiple users interacting with the same task simultaneously
- **Training/Fine-Tuning**: Agents learning from feedback (this is a platform, not ML training)
- **Complex Workflow Orchestration**: Multi-step, conditional workflows (future orchestration layer)

## Evolution Notes

### 2026-01-03 (Initial Draft)

- Created specification based on A2A protocol version 0.3 research
- Aligned with existing core-chatbot-agent implementation
- Key design decisions:
  - A2A as the interoperability standard rather than a custom protocol
  - Three creation modes (SDK, API, Chat) to serve all user types
  - HITL as a first-class concept via `input_required` state
  - Multi-tenancy embedded in the security model from the start
- Identified key open questions around registry, state persistence, and version management
- Next steps: Technical planning phase to define implementation architecture

---

## References

- [Google A2A Protocol Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A Protocol Specification (Draft v1.0)](https://a2a-protocol.org/latest/specification/)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [A2A Core Concepts](https://a2a-protocol.org/latest/topics/key-concepts/)
- [A2A Agent Skills & Agent Card Tutorial](https://a2a-protocol.org/latest/tutorials/python/3-agent-skills-and-card/)
- [Linux Foundation A2A Project Announcement](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
