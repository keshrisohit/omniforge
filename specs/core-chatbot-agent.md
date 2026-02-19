# Core Chatbot Agent

**Created**: 2026-01-03
**Last Updated**: 2026-01-03
**Version**: 1.0
**Status**: Draft

## Overview

The Core Chatbot Agent is the primary conversational interface for the OmniForge platform. It provides a streaming API endpoint that accepts user messages and returns real-time responses using Server-Sent Events (SSE). This agent serves as the foundation for all user interactions with the platform and will eventually orchestrate other agents and tasks. The initial implementation focuses on basic request/response with streaming capability.

## Alignment with Product Vision

This specification directly supports OmniForge's vision of being an "agent-first platform where agents build agents":

- **Primary interface**: This chatbot is the main touchpoint for users to interact with OmniForge, making the platform accessible without requiring code
- **Foundation for orchestration**: Designed to evolve into the orchestrator that helps users create and manage other agents
- **Simplicity first**: Starting with minimal viable functionality aligns with the principle of "simplicity over flexibility"
- **Enterprise-ready**: The API design supports future multi-tenancy and authentication requirements

## User Personas

### Primary Users

- **Platform Developer**: A software developer integrating OmniForge into their application. They need a reliable, well-documented API with predictable streaming behavior. They care about latency, error handling, and ease of integration.

- **Business User (Future)**: A non-technical user who will interact with the chatbot through a UI to create agents and orchestrate tasks. For v1, they are not the direct consumer but their needs inform the design.

### Secondary Users

- **Platform Administrator**: Needs to monitor chatbot usage, performance, and errors. Requires observability hooks and consistent logging.

## Problem Statement

Users need a way to interact with the OmniForge platform conversationally. Currently, there is no interface for sending requests and receiving responses. Without this foundational component:

- Users cannot communicate with the platform
- There is no mechanism for real-time feedback during long-running operations
- Future agent orchestration has no entry point
- The platform cannot fulfill its vision of being accessible to non-technical users

The chatbot must stream responses because users expect immediate feedback, and agent operations may take significant time to complete.

## User Journeys

### Primary Journey: Basic Chat Interaction

**Context**: A developer wants to test the platform's conversational capabilities.

1. **Developer sends a message** - They POST a JSON payload with their message to the chat endpoint
2. **Connection established** - The server accepts the request and opens an SSE stream
3. **Response streams in real-time** - The user sees tokens/chunks arrive progressively
4. **Stream completes** - A final event signals the response is complete
5. **Developer processes the result** - They have the full response and can take next action

### Alternative Journey: Error Handling

**Context**: Something goes wrong during the chat interaction.

1. **Developer sends a message** - They POST to the chat endpoint
2. **Error occurs** - The server encounters an issue (invalid request, internal error, etc.)
3. **Error event sent** - An error event is streamed with relevant details
4. **Stream closes** - The connection terminates gracefully
5. **Developer can retry** - They have enough information to diagnose and retry

### Alternative Journey: Connection Interruption

**Context**: The client loses connection mid-stream.

1. **Developer sends a message** - Chat begins normally
2. **Partial response received** - Some chunks have been delivered
3. **Connection drops** - Network issue or client disconnect
4. **Server cleans up** - Resources are released appropriately
5. **Developer reconnects** - They can send a new request (no resume in v1)

## Success Criteria

### User Outcomes

- **Time to first token < 500ms**: Users perceive the system as responsive
- **Streaming works reliably**: 99%+ of started streams complete successfully (excluding client disconnects)
- **Clear error messages**: When something fails, users understand why and what to do

### Technical Outcomes

- **API is well-documented**: Developers can integrate without support
- **Consistent SSE format**: Events follow a predictable schema
- **Graceful degradation**: Server handles malformed requests without crashing

### Business Outcomes

- **Foundation established**: This component unblocks future agent orchestration work
- **Developer adoption**: External developers can successfully integrate with the API

## Key Experiences

The moments that define quality for this feature:

- **First Response Chunk**: The moment the first token arrives should feel instant. This sets the user's perception of the entire platform's responsiveness.

- **Streaming Flow**: Text should appear smoothly and progressively. Choppy or delayed chunks break the conversational illusion.

- **Completion Signal**: Users should know definitively when the response is finished. Ambiguity about "is it still thinking?" creates anxiety.

- **Error Clarity**: When something breaks, the error message should be actionable. Generic "something went wrong" messages are unacceptable.

## API Design (Conceptual)

### Request

```
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Hello, help me create an agent",
  "conversation_id": "optional-uuid-for-context"
}
```

### Response (SSE Stream)

```
Content-Type: text/event-stream

event: chunk
data: {"content": "Hello! I'd be happy to "}

event: chunk
data: {"content": "help you create an agent. "}

event: chunk
data: {"content": "What would you like it to do?"}

event: done
data: {"conversation_id": "uuid", "usage": {"tokens": 42}}

OR on error:

event: error
data: {"code": "invalid_request", "message": "Message cannot be empty"}
```

### Event Types

| Event | Purpose |
|-------|---------|
| `chunk` | Partial response content |
| `done` | Successful completion with metadata |
| `error` | Error occurred, stream will close |

## Edge Cases and Considerations

- **Empty message**: Return 400 error immediately, do not open stream
- **Very long message**: Define a reasonable limit (e.g., 10,000 characters), return error if exceeded
- **Client disconnect mid-stream**: Server should detect and clean up resources
- **Slow client**: Server should handle backpressure gracefully
- **Concurrent requests**: Each request is independent; no shared state in v1
- **Special characters / Unicode**: Full UTF-8 support required
- **Rate limiting**: Not in v1, but API design should accommodate future rate limit headers

## Open Questions

- **LLM Backend**: Which LLM will power responses? Need to determine provider and model.
- **Conversation Context**: How much history should be maintained? For v1, consider stateless with optional conversation_id for future use.
- **Authentication**: How will requests be authenticated? Placeholder for future RBAC integration.
- **Response Format**: Should the chatbot support structured output (JSON) in addition to plain text?
- **Retry Semantics**: Should failed requests be idempotent? What makes a request unique?

## Out of Scope (For Now)

- **Agent orchestration**: v1 is basic chat only; orchestration comes later
- **Multi-turn memory**: No persistent conversation history in v1
- **User authentication**: v1 is unauthenticated or uses simple API key
- **Rate limiting**: Deferred to future iteration
- **Streaming cancellation**: Client cannot cancel mid-stream in v1
- **Multiple response formats**: Plain text only; no structured output
- **File attachments**: Text messages only
- **Tool/function calling**: No external tool integration in v1

## Technical Constraints

- **Python 3.9+**: Must work with project's Python version requirement
- **Framework agnostic initially**: Specification does not mandate a specific web framework
- **Stateless**: No server-side session state in v1
- **SSE over WebSockets**: SSE chosen for simplicity and HTTP compatibility

## Evolution Notes

### 2026-01-03 (Initial Draft)

- Created initial specification based on requirements
- Deliberately kept scope minimal for incremental build approach
- Key decisions: SSE for streaming, stateless design, simple JSON request format
- Identified open questions around LLM backend and authentication
- Designed API with future extensibility in mind (conversation_id, event types)
