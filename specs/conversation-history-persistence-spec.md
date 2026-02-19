# Conversation History Persistence for Skill Creation

**Created**: 2026-02-04
**Last Updated**: 2026-02-04
**Version**: 1.0
**Status**: Draft

## Overview

Enable persistent conversation history for the skill creation chatbot system so users never lose progress during skill creation workflows. Currently, conversation history exists only in-memory (`self.sessions` dict in `SkillCreationAgent`), which means history is lost on crashes, restarts, or errors. This specification defines how to persist conversation context to the database, ensuring seamless recovery and continuous LLM context across all scenarios.

## Alignment with Product Vision

This specification directly supports OmniForge's vision of a **chatbot-driven no-code agent creation** platform:

- **Reliability over speed**: Conversation persistence ensures users never lose progress, even during failures
- **Enterprise-ready**: Proper persistence supports the multi-tenant architecture already in place
- **Agents build agents**: The skill creation chatbot is a core agent-building experience that must be dependable
- **Simplicity over flexibility**: Auto-save/restore should "just work" without user intervention

## User Personas

### Primary Users

- **Technical Business User (Sarah)**: Uses the skill creation chatbot to define new skills without writing code. Expects her conversation to survive browser refreshes, server restarts, and network interruptions. Would be frustrated to re-explain her skill requirements after an error.

- **Developer (Marcus)**: Uses the chatbot for quick skill prototyping. Often works in long sessions with interruptions. Needs to resume exactly where he left off, with full conversation context preserved.

### Secondary Users

- **Platform Administrator (Alex)**: Manages the OmniForge deployment. Needs visibility into conversation data for troubleshooting, needs cleanup policies to manage storage, and requires audit trails for compliance.

## Problem Statement

Users who are mid-conversation in skill creation lose all their progress when:

1. **Server restarts or crashes**: The in-memory `self.sessions` dict is lost
2. **Errors during processing**: While error recovery transitions to `GATHERING_DETAILS`, message history may be incomplete
3. **Session timeout or browser close**: No way to resume where they left off
4. **Scale-out deployments**: Different server instances have different in-memory sessions

This creates frustration and wasted time, as users must re-explain their skill requirements from scratch. For complex skills requiring multiple refinement rounds, losing this context is especially painful.

**Impact**: Users lose trust in the platform's reliability. Complex skill creation becomes tedious. Enterprise adoption is hindered by the unreliable conversational experience.

## User Journeys

### Primary Journey: Uninterrupted Skill Creation with Auto-Recovery

1. **User starts skill creation** - Sarah opens the skill creation chatbot and begins describing her skill purpose
2. **Progress auto-saved** - After each message exchange, the system automatically persists the conversation state
3. **Interruption occurs** - Server restarts during the validation phase
4. **User returns** - Sarah refreshes or reconnects to the same session
5. **Context restored** - The system loads the full conversation history including gathered requirements, generated content, and FSM state
6. **Seamless continuation** - Sarah continues from the exact point of interruption; the LLM has full context
7. **Skill completed** - Sarah successfully creates her skill without re-explaining anything

### Alternative Journey: Error Recovery with Context Preservation

1. **User provides requirements** - Marcus provides detailed skill requirements including examples and workflow steps
2. **Generation fails** - An LLM error occurs during SKILL.md generation
3. **Error handled gracefully** - System transitions to `GATHERING_DETAILS` with full history preserved
4. **User provides clarification** - Marcus provides additional context
5. **Regeneration succeeds** - With full conversation history available, the LLM produces accurate output
6. **No context lost** - All previous examples and requirements remain in the conversation

### Alternative Journey: Multi-Device Continuation

1. **User starts on laptop** - Sarah begins skill creation at her desk
2. **Needs to leave** - She closes her laptop without completing the skill
3. **Continues on phone** - Later, she accesses OmniForge from her phone with the same session ID
4. **Full context available** - All conversation history and state is restored from database
5. **Completes skill** - Sarah finishes creating the skill from her phone

## Success Criteria

### User Outcomes

- **Zero lost conversations**: 100% of conversations survive server restarts, crashes, and errors
- **Instant restoration**: Conversation history loads in under 500ms when resuming a session
- **Complete LLM context**: All previous messages are available to the LLM on every request
- **Seamless experience**: Users should not notice that persistence is happening

### Business Outcomes

- **Reduced support tickets**: Fewer complaints about lost progress
- **Increased completion rate**: More skill creation conversations reach COMPLETED state
- **Enterprise confidence**: Audit trail and reliability support enterprise adoption
- **Multi-instance support**: Enables horizontal scaling of the platform

### Technical Metrics

- **Save latency**: Message persistence completes in under 100ms
- **Restore latency**: Full conversation context loads in under 500ms
- **Storage efficiency**: Conversation data compressed to minimize storage costs
- **Retention compliance**: Old conversations cleaned up per configured policy

## Key Experiences

### Auto-Save After Every Exchange

**What makes this moment great**: The user never thinks about saving. Every message exchange triggers an automatic, non-blocking persist operation. Even if they immediately lose connection, their last message and the assistant's response are preserved.

### Seamless Session Restoration

**What makes this moment great**: When a user reconnects to their session, they see their complete conversation history rendered instantly. The system state (FSM state, gathered requirements, generated content) is fully restored. The user can simply continue typing their next message.

### Error Recovery with Full Context

**What makes this moment great**: When an error occurs, the system transitions gracefully to a recovery state while preserving all accumulated context. The user provides clarification, and the LLM can reference all previous conversation turns to produce better results.

### Complete LLM Context

**What makes this moment great**: Every LLM call includes the full conversation history. This means the LLM remembers all examples, preferences, and clarifications the user has provided throughout the session, resulting in more accurate and contextual responses.

## Technical Considerations

### What Gets Persisted

The `ConversationContext` model contains all state that must be persisted:

```
ConversationContext:
  - session_id: str                    # Primary key for persistence
  - state: ConversationState           # FSM state (enum)
  - skill_name: Optional[str]
  - skill_description: Optional[str]
  - skill_purpose: Optional[str]
  - skill_capabilities: Optional[SkillCapabilities]  # Complex nested model
  - examples: list[str]
  - workflow_steps: list[str]
  - triggers: list[str]
  - references_topics: list[str]
  - scripts_needed: list[str]
  - allowed_tools: list[str]
  - storage_layer: Optional[str]
  - generated_content: Optional[str]   # Can be large (SKILL.md content)
  - generated_resources: dict[str, str]
  - validation_attempts: int
  - validation_errors: list[str]
  - validation_progress: dict[str, int]
  - message_history: list[dict[str, str]]  # All conversation turns
  - asked_questions: list[str]
  - inference_attempts: int
```

### Persistence Strategy Options

**Option A: Store Full Context as JSON (SELECTED)**
- Store entire `ConversationContext` as JSON blob per session
- Pros: Simple, atomic updates, easy to restore, single source of truth
- Cons: Large payload for long conversations, no message-level queries
- **Decision**: Selected for simplicity and ease of implementation

**Option B: Normalize Messages and Context**
- Store messages in `conversation_messages` table
- Store context metadata in `skill_creation_sessions` table
- Pros: Efficient queries, can leverage existing conversation infrastructure
- Cons: More complex restoration, requires joins

**Option C: Hybrid Approach**
- Store core conversation using existing `ConversationRepository` infrastructure
- Store skill-specific context (state, capabilities, generated content) in new table
- Pros: Reuses proven patterns, efficient for both message history and skill context
- Cons: Two tables to manage, but follows established codebase patterns

### Multi-Tenancy Considerations

The existing `ConversationRepository` enforces tenant isolation on all operations. The skill creation persistence must follow the same pattern:

- All persistence operations require `tenant_id`
- All queries filter by `tenant_id`
- No cross-tenant data access possible

### Integration Points

1. **SkillCreationAgent.handle_message()**: Save context after successful message processing
2. **SkillCreationAgent.get_session_context()**: Load from database if not in memory
3. **SkillCreationAgent._clear_session()**: Mark session as completed (not deleted for audit)
4. **Error handlers**: Ensure context is saved even when errors occur

### Existing Patterns to Leverage

The codebase already has:
- `SQLiteConversationRepository`: Proven conversation persistence with tenant isolation
- `ConversationModel` / `ConversationMessageModel`: ORM models for conversations
- `Database` class: Session management with async support
- `ConversationContext`: Pydantic model with serialization support

## Edge Cases and Considerations

### Concurrent Session Access

**Scenario**: User opens same session in two browser tabs
**Handling**: Use optimistic locking with `updated_at` timestamp. Last write wins. UI should warn user of concurrent access.

### Large Generated Content

**Scenario**: `generated_content` contains very large SKILL.md (approaching 500 lines)
**Handling**: Store as TEXT column (unlimited length in SQLite). Consider compression for very large content.

### Session ID Collisions

**Scenario**: Two users somehow get same session ID
**Handling**: Session ID must include tenant_id in the primary key, or be globally unique (UUID). Tenant isolation queries prevent cross-tenant access regardless.

### Orphaned Sessions

**Scenario**: User starts skill creation but never completes
**Handling**: Implement configurable retention policy (e.g., 30 days). Mark sessions as `ABANDONED` after timeout. Clean up old sessions via background job.

### Migration of Existing Sessions

**Scenario**: Existing in-memory sessions during deployment of persistence feature
**Handling**: In-memory sessions will continue to work until restart. Document that one-time restart may lose in-progress sessions during migration.

### Database Unavailable

**Scenario**: Database connection fails during persist operation
**Handling**: Log error but do not fail the user-facing operation. Retry persistence on next message. Consider in-memory fallback with retry queue.

### Message History Size Limits

**Scenario**: Very long conversations with hundreds of messages
**Handling**: Implement sliding window for LLM context (keep last N messages). Store all messages for audit but truncate for LLM calls. Configurable limits.

## Data Retention and Cleanup

### Retention Policy (SELECTED)

- **Active sessions**: Retained indefinitely while in non-terminal state
- **Completed sessions**: Retained for 90 days (configurable) for audit purposes - **SELECTED**
- **Abandoned sessions**: Sessions in non-terminal state with no activity for 30 days marked as ABANDONED - **SELECTED**
- **Cleanup**: Background job runs daily to delete sessions past retention period

### Audit Requirements

- All conversation messages preserved for compliance
- Session state transitions logged
- Deletion requests honored (GDPR right to erasure)

## Open Questions

1. **Compression**: Should we compress `generated_content` and `message_history` to reduce storage? What compression ratio is achievable?

2. **Partial restoration**: Should we support restoring only recent messages to LLM while keeping full history in DB? What's the optimal context window?

3. **Real-time sync**: For multi-device scenarios, should we implement real-time session sync (websockets) or is refresh-based restoration sufficient?

4. **Session continuation UI**: How should the UI indicate that a session was restored? Should it show a "Resuming your conversation..." message?

5. **Cleanup automation**: Should abandoned session cleanup be automatic or require admin approval?

## Out of Scope (For Now)

- **Real-time collaboration**: Multiple users editing same skill creation session simultaneously
- **Version history**: Ability to revert to previous conversation states
- **Session export/import**: Exporting conversation history for external use
- **Cross-tenant session sharing**: Enterprise feature for sharing skill definitions
- **Conversation branching**: Ability to fork a conversation at any point

## Evolution Notes

### 2026-02-04 - Initial Draft

- Analyzed existing codebase patterns for conversation persistence
- Identified that `SQLiteConversationRepository` and `ConversationModel` provide proven infrastructure
- Determined hybrid approach (reuse conversation tables + new skill context table) aligns best with existing patterns
- Key insight: `ConversationContext` is a Pydantic model that can be serialized to JSON for persistence
