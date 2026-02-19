# Smart Master Agent: LLM-Powered Intent Detection and Conversation Context

**Created**: 2026-01-30
**Last Updated**: 2026-01-30
**Version**: 1.0
**Status**: Draft

---

## Overview

The Smart Master Agent enhancement upgrades three foundational capabilities of the OmniForge chat experience: (1) replacing the current keyword-based intent detection with LLM-powered intent analysis that truly understands user requests, (2) adding persistent conversation storage so that chat history survives across sessions, and (3) passing relevant conversation context to the master agent so it can maintain coherent multi-turn interactions. Together, these changes transform the master agent from a stateless keyword matcher into a context-aware, intelligent orchestrator that understands nuance, remembers what users said, and responds with natural conversational fluency.

---

## Alignment with Product Vision

This specification directly advances several core OmniForge vision principles:

- **"Agents build agents" / No-Code Interface**: Users describe what they want in natural language. LLM-powered intent detection makes this reliable for ambiguous, complex, and multi-step requests -- not just keyword matches.
- **Simplicity over flexibility**: Users should not need to learn magic phrases to trigger the right action. The LLM understands intent regardless of phrasing.
- **Reliability over speed**: Persistent conversation history means the system never "forgets" mid-conversation, even across page refreshes or session interruptions.
- **Enterprise-ready**: Conversation storage is tenant-scoped and user-scoped, maintaining strict data isolation.
- **Cost**: The specification includes a tiered LLM strategy (fast/cheap model for intent classification, optional richer model for response generation) to keep costs manageable.

---

## User Personas

### Primary User: Maya (Marketing Manager)

**Context**: Non-technical user who interacts with OmniForge through the chatbot interface to create and run agents.

**Goals**:
- Describe what she needs in her own words and have the system understand
- Pick up conversations where she left off, even after closing the browser
- Not repeat herself when the system should already know what she is working on

**Pain Points (Today)**:
- The system only understands exact phrases like "create agent" -- slight variations like "I want to build a bot" or "set up an automation" fail silently or misroute
- Every new message is treated as a fresh conversation with no memory of what was discussed moments ago
- Multi-turn flows (like agent creation wizards) break if she navigates away

**Key Quote**: "I told it what I wanted three messages ago. Why is it asking me again?"

### Secondary User: Derek (Operations Lead)

**Context**: Power user who uses the chatbot frequently and manages multiple agents across projects.

**Goals**:
- Have fluid multi-turn conversations about complex agent configurations
- Resume previous conversations to check on or modify agents discussed earlier
- Get accurate routing even for nuanced requests like "run the same thing as last time but for Q1 data"

**Pain Points (Today)**:
- Cannot reference previous conversations ("remember when we set up the Notion reporter?")
- System cannot distinguish between similar intents without keyword crutches
- Context from earlier in a conversation is lost, forcing him to re-explain

### Tertiary User: Platform (System)

**Context**: The OmniForge platform itself benefits from stored conversations for analytics, debugging, and future features (conversation search, audit trails, agent usage patterns).

**Goals**:
- Audit trail of all user-agent interactions per tenant
- Data foundation for future features (conversation search, analytics, agent improvement feedback loops)
- Debugging support when routing goes wrong

---

## Problem Statement

### Problem 1: Brittle Intent Detection

**Current state**: The master agent's `_analyze_intent()` method uses a hardcoded list of keyword phrases (e.g., `"create agent"`, `"build agent"`, `"new agent"`) to classify user intent into one of seven action types. This approach fails for:
- **Paraphrased requests**: "I want to set up an automation that monitors our Jira board" -- no keyword match for CREATE_AGENT
- **Implicit intent**: "Our weekly reports are always late" -- the user wants a solution (likely CREATE_AGENT) but expresses a problem, not a command
- **Nuanced disambiguation**: "Create a summary of my data" -- is this CREATE_SKILL, EXECUTE_TASK, or QUERY_INFO? Keywords overlap
- **Contextual intent**: "Yes, do that" -- requires understanding of prior conversation to resolve

**Impact**: Users who do not use the exact expected phrases get misrouted or receive "I'm not sure what you'd like me to do" responses, undermining the no-code promise of the platform.

### Problem 2: Stateless Conversations

**Current state**: The `ChatService` generates a `conversation_id` for each request but never stores messages. The `MasterResponseGenerator` accepts a bare string message with no history. The master agent has an empty `_conversation_context` dict that is never populated.

**Impact**:
- Multi-turn flows are impossible -- the agent creation wizard asks questions but cannot remember answers
- Users must re-explain context every time
- Follow-up messages like "yes", "the first one", or "actually, change that to weekly" have no referent
- The platform cannot provide conversation history in the UI

### Problem 3: No Context Flow Between Components

**Current state**: The chat service calls `generate_stream(message: str)` with only the current message. No conversation history, no user context, no session state flows from the chat service into the master agent.

**Impact**: Even if we add LLM-based intent detection, the LLM would only see the current message without the conversational context needed to resolve ambiguity, handle follow-ups, or maintain coherent multi-turn interactions.

---

## User Journeys

### Journey 1: Natural Language Intent Detection (New)

**Scenario**: Maya uses natural phrasing that the current keyword system would miss.

```
Maya: "Our team wastes hours every Monday compiling project updates from Notion.
       Can the platform help with that?"

[Current System - FAILS]
- Keyword match: "what" not found, "how" not found...
- Matches "help" -> QUERY_INFO (wrong!)
- Response: generic help text listing capabilities

[Smart Master Agent - SUCCEEDS]
- LLM analyzes: User describes a recurring pain point (manual Notion compilation)
  and asks if platform can solve it
- Intent: CREATE_AGENT (confidence: 0.88)
- Entities: { source: "notion", task: "project updates", frequency: "weekly/Monday" }
- Reasoning: User describes a workflow problem and asks for platform help,
  indicating they want to create an automation

Master Agent: "It sounds like you want to automate your weekly project
updates from Notion. I can help you create an agent that does this
automatically every Monday. Want me to set that up?"
```

**Key Experience**: The system understands the *problem* Maya described and proposes the right solution, rather than requiring her to say "create an agent."

---

### Journey 2: Multi-Turn Conversation with Context (New)

**Scenario**: Derek is setting up a new agent and the conversation spans multiple exchanges.

```
Derek: "Create an agent that monitors our Jira board for overdue tickets"

Master Agent: "I'll help you create a Jira monitoring agent. A few questions:
1. Which Jira project(s) should it monitor?
2. How do you define 'overdue' -- past the due date, or past a custom SLA?
3. What should happen when overdue tickets are found -- Slack alert, email, or both?"

Derek: "The PLATFORM project, past due date, and Slack alerts"

[Context from previous messages flows to LLM]
Master Agent: "Got it! Setting up your agent:
- Monitor: PLATFORM project in Jira
- Trigger: Tickets past their due date
- Action: Send Slack alerts

How often should it check -- every hour, daily, or real-time?"

Derek: "Every morning at 9am"

[Full conversation history available]
Master Agent: "Perfect. Creating your agent now:
- Name: jira-overdue-monitor
- Source: Jira (PLATFORM project)
- Check: Daily at 9:00 AM
- Alert: Slack notification for overdue tickets

Setting this up..."
```

**Key Experience**: Each message builds on the previous ones. The agent remembers all prior answers and synthesizes them into a complete configuration.

---

### Journey 3: Conversation Resumption (New)

**Scenario**: Maya was setting up an agent yesterday but had to leave mid-conversation. She returns today.

```
[Yesterday's conversation stored in database]
Maya (yesterday): "I want to create an agent for weekly financial reports"
Master Agent (yesterday): "I'll help! Where does your financial data live?"
Maya (yesterday): "Google Sheets"
Master Agent (yesterday): "Great! What specific data should the report include?"
[Maya closed browser]

[Today - Maya opens chat, same conversation_id loaded]
Maya: "Sorry, I had to step away. Where were we?"

[Master Agent receives conversation history as context]
Master Agent: "No problem! We were setting up your weekly financial report agent.
So far we have:
- Source: Google Sheets
- Type: Weekly financial report

I was asking: What specific data should the report include from your spreadsheet?"
```

**Key Experience**: The conversation picks up exactly where it left off. Maya does not need to start over.

---

### Journey 4: Contextual Follow-Up Resolution (New)

**Scenario**: Derek gives a short follow-up that only makes sense with conversation history.

```
Derek: "List my agents"

Master Agent: "Here are your agents:
1. notion-reporter - Weekly Notion project summaries
2. jira-overdue-monitor - Daily overdue ticket alerts
3. financial-analyzer - Monthly financial analysis"

Derek: "Run the first one"

[Without context: "Run the first one" is meaningless]
[With context: LLM sees previous exchange, resolves "the first one" to "notion-reporter"]

Master Agent: "Running notion-reporter to generate your weekly Notion summary..."
```

**Key Experience**: Short, natural follow-ups work because the system has conversational context.

---

### Journey 5: Ambiguous Intent Resolved by LLM (New)

**Scenario**: A request that keyword matching would misclassify.

```
User: "I need to analyze our customer churn data and put together
       a presentation for the board meeting next week"

[Keyword system would match: "analyze" -> EXECUTE_TASK]

[LLM analysis with full understanding]:
- This is a complex request with two parts: analysis + presentation
- No existing agent likely handles both
- User probably needs a new agent or a task execution

LLM Intent: EXECUTE_TASK (confidence: 0.72)
  - Ambiguity flag: true
  - Alternative: CREATE_AGENT (confidence: 0.55)
  - Entities: { data: "customer churn", output: "presentation", deadline: "next week" }

Master Agent: "I can help with that! Let me check if you have an agent
that handles churn analysis...

I found your 'financial-analyzer' agent, but it focuses on revenue data,
not churn. Would you like me to:

1. Run financial-analyzer anyway (it may partially help)
2. Create a new agent specifically for churn analysis and presentations
3. Help you approach this differently"
```

**Key Experience**: The LLM detects ambiguity, checks available agents, and presents thoughtful options rather than silently misrouting.

---

## Success Criteria

### User Outcomes

- **Intent accuracy**: 90%+ of user requests are routed to the correct action type on the first attempt, compared to the current keyword system (estimated ~60% for natural language requests)
- **Conversation continuity**: Users can resume any conversation within the last 30 days and the system correctly recalls context
- **Follow-up resolution**: 85%+ of contextual follow-ups ("yes", "the first one", "do that again") are correctly resolved using conversation history
- **Reduced clarification rate**: Clarification requests drop from ~40% (keyword system) to <20% (LLM system) for clear user intents
- **User satisfaction**: Users report that the system "understands what I mean" rather than requiring specific phrasing

### Business Outcomes

- **Engagement**: Average conversation length increases (users trust multi-turn flows)
- **Completion rate**: Agent creation wizards complete more often (context is not lost mid-flow)
- **Audit capability**: All conversations are stored and queryable per tenant for compliance and debugging
- **Foundation for future features**: Conversation data enables analytics, feedback loops, and conversation search

### Technical Outcomes

- **Intent analysis latency**: LLM intent classification completes in <1 second (p95)
- **Storage reliability**: Zero conversation data loss under normal operations
- **Context window efficiency**: Conversation history passed to LLM stays within token budget without losing critical context
- **Cost per interaction**: Intent classification cost stays below $0.005 per request using a fast/cheap model

---

## Key Experiences

### "It Just Understands Me"

The most important experience is that users feel the system understands their intent regardless of how they phrase it. This means:
- No more learning magic keywords
- No more "I'm not sure what you'd like me to do" for reasonable requests
- The system proposes solutions to described problems, not just reacts to commands

### "It Remembers Our Conversation"

The second critical experience is conversational continuity:
- Multi-turn flows feel natural and stateful
- Returning to a conversation feels like picking up with a colleague
- Short follow-ups work without re-explaining context

### "It Gives Me Intelligent Options"

When the system is uncertain, it presents thoughtful choices based on genuine understanding rather than generic menus:
- Options are contextualized to what the user actually asked
- The system explains WHY it is presenting options
- Each option describes what would happen, not just a label

---

## Core Capabilities (What to Build)

### Capability 1: LLM-Powered Intent Analysis

**What it does**: Replaces the keyword-matching `_analyze_intent()` method with an LLM call that classifies user intent using structured output.

**User-facing behavior**:
- Users describe what they want in natural language
- The system correctly identifies the action type (CREATE, UPDATE, EXECUTE, QUERY, MANAGE_PLATFORM)
- The system extracts relevant entities (data sources, agent names, timeframes, etc.)
- The system reports confidence and flags ambiguity
- When ambiguous, the system asks a contextually relevant clarifying question (not a generic menu)

**What the LLM receives**:
- The current user message
- A system prompt describing the available action types, the user's tenant context, and instructions for structured output
- Recent conversation history (for contextual follow-ups)
- List of the user's available agents and skills (so the LLM knows what exists)

**What the LLM returns** (structured output):
- `action_type`: One of the defined action types
- `confidence`: 0.0 to 1.0
- `entities`: Key-value pairs extracted from the message (agent_name, data_source, frequency, etc.)
- `reasoning`: Brief explanation of why this intent was chosen
- `is_ambiguous`: Boolean flag
- `alternative_action`: Second-best action type if ambiguous
- `clarifying_question`: Suggested question if confidence is below threshold

**Model selection**: Use a fast, inexpensive model for intent classification (e.g., GPT-4o-mini, Claude Haiku, or a Groq-hosted open model). Intent classification is a structured, well-bounded task that does not require the most capable model. The existing `litellm` integration should be reused for provider flexibility.

**Fallback**: If the LLM call fails (timeout, rate limit, API error), fall back to the existing keyword-based classifier. This ensures the system degrades gracefully rather than failing entirely.

---

### Capability 2: Persistent Conversation Storage

**What it does**: Stores all chat messages (user and assistant) in a persistent database, associated with a conversation ID, user ID, and tenant ID.

**User-facing behavior**:
- Conversations persist across page refreshes, browser closures, and sessions
- Users can return to previous conversations and see full history
- The chat UI can display conversation history on load

**Data model**:
- **Conversation**: `id`, `tenant_id`, `user_id`, `title` (auto-generated or user-set), `created_at`, `updated_at`, `metadata`
- **Message**: `id`, `conversation_id`, `role` (user/assistant/system), `content`, `created_at`, `metadata` (intent analysis results, routing decisions, etc.)

**Storage backend**: Start with SQLite using an abstract repository interface (`ConversationRepository`) so the backend can be swapped to PostgreSQL or another database as the platform scales. SQLite is sufficient for the current single-process development stage and avoids introducing infrastructure dependencies.

**Repository interface**:
- `create_conversation(tenant_id, user_id) -> Conversation`
- `get_conversation(conversation_id) -> Conversation`
- `list_conversations(tenant_id, user_id, limit, offset) -> List[Conversation]`
- `add_message(conversation_id, role, content, metadata) -> Message`
- `get_messages(conversation_id, limit, before_id) -> List[Message]`
- `get_recent_messages(conversation_id, limit) -> List[Message]`

**Retention**: Store conversations for at least 30 days. Retention policy can be configurable per tenant in the future.

---

### Capability 3: Context-Aware Orchestration

**What it does**: The chat service retrieves relevant conversation history and passes it to the master agent (and through to the LLM) so that every response is informed by prior context.

**User-facing behavior**:
- The master agent understands follow-up messages in the context of the conversation
- Multi-turn flows (agent creation wizards, clarification sequences) maintain state
- Users can reference earlier messages naturally ("the report we discussed", "that agent")

**Context assembly strategy**:
- When a new message arrives with a `conversation_id`, the chat service retrieves recent messages from storage
- A context window is assembled: the last N messages (default: 10 exchanges / 20 messages) OR the most recent messages that fit within a token budget (default: 2000 tokens of history)
- The context window is passed to the master agent alongside the current message
- The master agent includes this context when calling the LLM for intent analysis

**What flows through the system**:
```
ChatService.process_chat(request)
  -> Retrieve conversation history from storage
  -> Call response_generator.generate_stream(message, conversation_history)
     -> MasterResponseGenerator.generate_stream(message, conversation_history)
        -> Build Task with conversation history in messages
        -> MasterAgent.process_task(task)  [task now contains history]
           -> _analyze_intent(message, conversation_history)
              -> LLM call with system prompt + history + current message
```

**Context filtering**: Not all history is relevant. The context assembler should:
- Always include the last 3 exchanges (for immediate continuity)
- Include messages from the current "topic" if detectable
- Exclude very old messages that exceed the token budget
- Include metadata about routing decisions (so the LLM knows what agents were previously invoked)

---

## Edge Cases and Considerations

### LLM Latency and Cost

**Scenario**: LLM intent classification adds latency to every request.

**Approach**: Use a fast model (GPT-4o-mini class) that responds in <500ms for structured classification tasks. The existing keyword classifier can serve as a fast-path for obviously clear intents (e.g., explicit "@agent-name" override) to skip the LLM call entirely. Monitor cost per request and alert if it exceeds budget.

### LLM Failures

**Scenario**: The LLM API is down, rate-limited, or returns malformed output.

**Approach**: Fall back to keyword-based classification. Log the failure for monitoring. The user experience degrades slightly (less accurate routing) but does not break. Implement retry with exponential backoff for transient failures.

### Conversation History Too Long

**Scenario**: A conversation has 100+ messages and cannot all be sent to the LLM.

**Approach**: Use a sliding window of recent messages that fits within the token budget. For very long conversations, include a summary of earlier context (future enhancement -- out of scope for v1, just truncate). Always include the most recent 3 exchanges.

### Conversation Isolation

**Scenario**: User starts a new topic but the old conversation context bleeds in.

**Approach**: Users can start a "new conversation" which creates a fresh conversation_id with no history. The UI should make this easy (a "New Chat" button). Within a conversation, the LLM should detect topic shifts and weight recent messages more heavily.

### Concurrent Messages

**Scenario**: User sends multiple messages before the first response completes.

**Approach**: Messages are stored in order of receipt. The response generator processes them sequentially within a conversation. Out-of-order responses should not corrupt conversation state.

### Storage Failures

**Scenario**: Database write fails when storing a message.

**Approach**: The chat response should still be delivered to the user (do not block the response on storage success). Log the storage failure and retry asynchronously. If storage is completely unavailable, the system operates in a degraded stateless mode.

### Sensitive Data in Conversations

**Scenario**: Users may share API keys, passwords, or sensitive data in chat messages.

**Approach**: Store conversations encrypted at rest (SQLite encryption or application-level encryption). Mark messages containing detected sensitive patterns for redaction in logs. Do not include sensitive message content in analytics or debugging outputs.

### LLM Structured Output Parsing

**Scenario**: The LLM returns output that does not match the expected structured format.

**Approach**: Use JSON mode or function calling to constrain LLM output format. Implement robust parsing with fallback to keyword classification if parsing fails. Validate all fields (action_type must be a known enum, confidence must be 0-1, etc.).

---

## Open Questions

1. **Context summarization**: For very long conversations, should we implement LLM-based summarization of older messages to maintain context within token budgets? (Deferred to future version -- start with simple truncation.)

2. **Conversation search**: Should users be able to search across their conversation history? (Useful but out of scope for this spec -- it is a separate feature that builds on the storage foundation.)

3. **Response generation model**: Should the master agent use the LLM to generate conversational responses (replacing hardcoded template strings), or should we keep templates for predictable, fast responses and only use LLM for intent classification? Recommendation: Start with LLM for intent only, keep templates for responses. Migrate to LLM-generated responses in a follow-up.

4. **Token budget tuning**: What is the optimal token budget for conversation history context? This likely needs experimentation. Start with 2000 tokens and adjust based on intent accuracy metrics.

5. **Multi-conversation support**: Should the chat service support listing and switching between conversations in the UI? (Yes, eventually, but the storage model supports it from day one -- the UI is a separate concern.)

6. **Streaming with LLM intent**: The current master agent streams response events. Adding an LLM call for intent analysis adds a synchronous step before streaming begins. Should we show a "thinking" indicator during intent analysis, or is <1 second fast enough to skip it?

---

## Out of Scope (For Now)

- **Conversation search and filtering** -- The storage foundation supports this, but building a search UI is a separate effort
- **LLM-generated conversational responses** -- Start with LLM for intent classification only; keep template-based responses for predictability
- **Long-term memory / summarization** -- Summarizing old conversations into a compressed context is deferred
- **Conversation sharing** -- Sharing conversations between users is not included
- **Voice or multimodal input** -- Text-only for now
- **Conversation analytics dashboard** -- Storing data enables this, but building the dashboard is separate
- **Real-time collaborative conversations** -- Single user per conversation for now

---

## Implementation Considerations

### Phase 1: Conversation Storage (Foundation)

Build the conversation storage layer first because it is a prerequisite for context-aware orchestration.

- Define `Conversation` and `Message` data models
- Implement `ConversationRepository` abstract interface
- Implement `SQLiteConversationRepository`
- Integrate storage into `ChatService` (store messages on send/receive)
- Ensure tenant and user scoping on all queries

**Done when**: Every chat message (user and assistant) is persisted and retrievable by conversation_id.

### Phase 2: Context Passing (Plumbing)

Wire conversation history through the system so the master agent has access to prior messages.

- Update `ChatService.process_chat()` to retrieve history before generating response
- Update `ResponseGenerator` and `MasterResponseGenerator` to accept conversation history
- Update `MasterAgent.process_task()` to include history in task messages
- Implement context window assembly (recent N messages within token budget)

**Done when**: The master agent receives relevant conversation history for every request with an existing conversation_id.

### Phase 3: LLM Intent Analysis (Intelligence)

Replace keyword matching with LLM-powered classification.

- Design the intent analysis system prompt (action types, entity extraction, structured output format)
- Implement `LLMIntentAnalyzer` using litellm (reuse existing provider configuration)
- Wire into `MasterAgent._analyze_intent()` as primary classifier with keyword fallback
- Include conversation history in the intent analysis prompt
- Parse and validate structured LLM output
- Implement fallback to keyword classifier on LLM failure

**Done when**: Intent classification uses an LLM call with conversation context and produces structured output with action type, entities, confidence, and reasoning.

---

## References

- [Product Vision](/Users/sohitkumar/code/omniforge/specs/product-vision.md)
- [Master Agent Spec](/Users/sohitkumar/code/omniforge/specs/master-agent-spec.md)
- [Current Master Agent Implementation](/Users/sohitkumar/code/omniforge/src/omniforge/agents/master_agent.py)
- [Current Chat Service](/Users/sohitkumar/code/omniforge/src/omniforge/chat/service.py)
- [LLM Generator (litellm integration)](/Users/sohitkumar/code/omniforge/src/omniforge/chat/llm_generator.py)

---

## Evolution Notes

### 2026-01-30 v1.0 (Initial Draft)

**Context**: The master agent currently uses keyword-based intent detection (`_analyze_intent()` with hardcoded phrase lists), has no conversation storage, and receives only the current message with no history. This spec addresses all three gaps.

**Key Design Decisions**:
- **LLM for intent only (not responses)**: Keep template-based responses for v1 to maintain predictability and speed. LLM-generated responses are a natural follow-up but add complexity around tone consistency, hallucination risk, and latency.
- **SQLite with abstract repository**: Avoids infrastructure dependencies during early development while ensuring the storage backend can be swapped later. The repository pattern is the important part, not the database choice.
- **Keyword fallback on LLM failure**: The existing keyword classifier becomes a fallback rather than being removed. This ensures graceful degradation and gives us a safety net during the transition.
- **Token-budgeted context window**: Rather than a fixed message count, use a token budget for conversation history. This handles both short and long conversations gracefully.
- **Phased implementation (Storage -> Context -> LLM)**: Storage must exist before context can flow. Context must flow before LLM intent analysis can use it. This ordering minimizes integration risk.

**Assumptions to Validate**:
- Fast LLM models (GPT-4o-mini class) can reliably produce structured intent classification output with >90% accuracy for OmniForge's action types
- 2000 tokens of conversation history is sufficient for resolving most contextual follow-ups
- SQLite performance is adequate for the current development stage (single-process, moderate message volume)
- Users will naturally adopt multi-turn conversation patterns once the system supports them

**Risks**:
- LLM intent classification accuracy may be lower than expected for domain-specific OmniForge actions -- mitigation: extensive prompt engineering and evaluation against a test set of user messages
- Adding LLM latency to every request may feel slow -- mitigation: fast model selection, fast-path for explicit intents, "thinking" indicator
- Conversation storage adds data management responsibility (backups, retention, privacy) -- mitigation: start simple, add policies incrementally
