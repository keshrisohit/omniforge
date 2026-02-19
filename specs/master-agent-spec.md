# Master Agent (Intelligent Router)

**Created**: 2026-01-26
**Last Updated**: 2026-01-26
**Version**: 2.2 (UPDATE + Extensible Queries + BaseAgent Integration)
**Status**: Draft

---

## Overview

The Master Agent is a smart router that serves as the central entry point for all user chat interactions on the OmniForge platform. It analyzes incoming requests, routes them to the most appropriate handler (agent, query handler, or agent builder), and asks clarifying questions when the user's intent is unclear.

**Core Responsibilities:**
1. **Analyze user requests** - Detect action type (CREATE/UPDATE/EXECUTE/QUERY)
2. **Route intelligently** - Send to appropriate handler based on intent
3. **Ask clarifying questions** - When ambiguous or uncertain
4. **Stream responses** - Return handler responses to the user

**Four Action Types:**
- **CREATE** - Build new customer agent → Platform Agent Builder
- **UPDATE** - Modify existing customer agent → Platform Agent Builder (with context)
- **EXECUTE** - Run existing customer agent → Agent Discovery + Customer Agent
- **QUERY** - Answer questions → Extensible Query Handler system (LLM fallback)

**Key Principle**: One request → one handler → one response. Keep it simple.

**Integration**: Master Agent is a BaseAgent implementation that leverages the existing skills system for discovery and routing.

---

## Two Types of Agents in the System

OmniForge has two distinct types of agents, and the Master Agent must understand the difference:

### 1. Platform Agents (System-Level)

**Purpose**: Enable the platform to function. Built and maintained by OmniForge.

**Characteristics**:
- Built into the platform
- Available to all tenants
- Not configurable by customers
- Handle platform operations

**Examples**:
- **Master Agent** (this agent) - Smart router for all requests
- **Agent Builder Agent** - Creates new customer agents conversationally
- **Health Monitor Agent** - Platform health checks
- **Admin Agent** - Platform administration tasks

**Lifecycle**: Deployed with platform, updated by OmniForge team

---

### 2. Customer Agents (User-Created)

**Purpose**: Execute customer-specific tasks. Created by customers via Agent Builder.

**Characteristics**:
- Created by customers through conversation
- Configurable with SKILL.md files
- Tenant-scoped (each customer has their own)
- Maintained by the customer

**Examples**:
- **notion-reporter** - Customer's Notion integration agent
- **financial-analyzer** - Custom financial analysis with specific rules
- **slack-notifier** - Team-specific Slack notifications

**Lifecycle**: Created via Agent Builder, configured with skills, can be updated/deleted by customer

---

## Integration with BaseAgent and Skills System

The Master Agent is built on OmniForge's existing agent architecture, ensuring consistency and leveraging proven patterns.

### Master Agent as BaseAgent

The Master Agent **is a BaseAgent** implementation:

```python
class MasterAgent(BaseAgent):
    """Smart router that directs requests to appropriate agents or handlers."""

    identity = AgentIdentity(
        id="master-agent",
        name="Master Agent",
        description="Intelligent router for all platform interactions",
        version="1.0.0"
    )

    capabilities = AgentCapabilities(
        streaming=True,
        supports_hitl=False,  # Master Agent doesn't need HITL
        task_types=["routing", "analysis", "clarification"]
    )

    skills = [
        AgentSkill(
            id="intent-analysis",
            name="Intent Analysis",
            description="Analyzes user intent (CREATE/UPDATE/EXECUTE/QUERY)",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT]
        ),
        AgentSkill(
            id="agent-discovery",
            name="Agent Discovery",
            description="Discovers matching customer agents",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.JSON]
        ),
        AgentSkill(
            id="smart-routing",
            name="Smart Routing",
            description="Routes requests to appropriate handlers",
            input_modes=[SkillInputMode.TEXT, SkillInputMode.JSON],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.JSON]
        )
    ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process routing task."""
        # 1. Analyze intent
        intent = await self._analyze_intent(task.input)

        # 2. Route based on intent
        if intent.action_type == "CREATE":
            async for event in self._route_to_builder(task):
                yield event
        elif intent.action_type == "UPDATE":
            async for event in self._route_to_builder(task, update=True):
                yield event
        elif intent.action_type == "EXECUTE":
            async for event in self._route_to_agent(task, intent):
                yield event
        elif intent.action_type == "QUERY":
            async for event in self._route_to_query_handler(task, intent):
                yield event
```

**Benefits of BaseAgent Integration**:
- ✅ Consistent A2A protocol (AgentCard generation)
- ✅ Standard task processing interface
- ✅ Event streaming (TaskEvent)
- ✅ Multi-tenancy support (tenant_id)
- ✅ Can be registered in AgentRegistry like any other agent
- ✅ Compatible with existing orchestration layer

---

### Customer Agents are BaseAgent + Skills

When Agent Builder creates a customer agent, it:

1. **Generates BaseAgent subclass**:
```python
class NotionReporterAgent(BaseAgent):
    identity = AgentIdentity(
        id="notion-reporter",
        name="Notion Reporter",
        description="Generates weekly Notion project summaries",
        version="1.0.0"
    )

    capabilities = AgentCapabilities(
        streaming=True,
        supports_hitl=False
    )

    skills = [
        # Skills loaded from SKILL.md files
        notion_reader_skill,
        report_generator_skill
    ]
```

2. **Creates SKILL.md files** for each capability:
```markdown
# Notion Reader Skill

## Capabilities
- Read Notion databases
- Filter by project status
- Extract project metadata

## Configuration
- API Key: ${NOTION_API_KEY}
- Database ID: ${NOTION_DATABASE_ID}

## Hooks
PreToolUse:
  - matcher: "NotionAPI"
    hooks:
      - type: command
        command: "validate_notion_credentials"
```

3. **Registers in AgentRegistry**:
```python
await agent_registry.register(
    agent=NotionReporterAgent(),
    tenant_id="customer-123",
    tags=["notion", "reporting", "weekly"],
    skills=["notion_reader", "report_generator"]
)
```

**Skills System Benefits**:
- ✅ Skills are composable (add/remove without code changes)
- ✅ SKILL.md provides configuration and hooks
- ✅ Context modes (inherit/fork) for skill isolation
- ✅ Pre/Post hooks for integration points
- ✅ Skills can be shared across agents
- ✅ Agent Builder manages skill lifecycle

---

### Agent Discovery Uses Skills

When Master Agent discovers agents for EXECUTE intent:

```python
# Master Agent queries registry
candidates = await agent_registry.discover(
    tenant_id="customer-123",
    required_skills=["notion_reader", "report_generator"],
    tags=["reporting"]
)

# Scoring includes skill matching
for agent in candidates:
    skill_match = calculate_skill_overlap(
        required=intent.required_skills,
        available=agent.skills
    )
    agent.score = skill_match * 0.6 + ...
```

**Benefits**:
- ✅ Intent analysis extracts required skills from user request
- ✅ Discovery matches agents by skill overlap
- ✅ Skills provide semantic matching (not just keywords)
- ✅ Agents advertise capabilities via skills in AgentCard

---

## Master Agent's Three Key Decisions

The Master Agent must distinguish between three fundamentally different intents:

### Intent 1: CREATE Agent (→ Route to Platform Agent Builder)

User wants to **create a new agent** that doesn't exist yet.

```
User: "I need an agent that sends weekly Notion summaries to Slack"

Master Agent detects:
- Intent: CREATE new agent
- Reason: Describes capabilities that don't exist yet
- Keywords: "I need an agent", "create", "build"

Master Agent routes to: Platform "Agent Builder" agent

Agent Builder:
- Has conversation with user to understand requirements
- Creates customer agent with appropriate skills
- Registers agent in customer's tenant
- Returns: "Your 'notion-slack-reporter' agent is ready!"
```

---

### Intent 2: UPDATE Agent (→ Route to Platform Agent Builder)

User wants to **modify an existing agent** they've created.

```
User: "Update my Notion reporter to also post to Slack"

Master Agent detects:
- Intent: UPDATE existing agent
- Reason: Modification request for existing agent
- Keywords: "update", "modify", "change", "add to", "edit"

Master Agent routes to: Platform Agent Builder (with context of existing agent)

Agent Builder:
- Loads existing "notion-reporter" agent configuration
- Understands user wants to add Slack posting skill
- Updates agent with new Slack skill
- Returns: "Your notion-reporter now posts to Slack too!"
```

---

### Intent 3: EXECUTE Agent (→ Route to Customer's Existing Agent)

User wants to **run an existing agent** to accomplish a task.

```
User: "Generate my weekly Notion report"

Master Agent detects:
- Intent: EXECUTE existing agent
- Reason: Action request, not agent creation/modification
- Keywords: "generate", "run", "show me", "get", "send"

Master Agent discovers: Customer's "notion-reporter" agent (exists)

Master Agent routes to: Customer's "notion-reporter" agent

notion-reporter executes and returns: "Here's your report..."
```

---

## Extensible Query Handling

In addition to CREATE, UPDATE, and EXECUTE intents, users can ask various **queries** about the platform, their agents, or general information. These queries don't execute agents but need intelligent handling.

### Query Types

**Current (LLM Handler)**:
- "What agents do I have?"
- "How does this platform work?"
- "Explain what my notion-reporter does"

**Future (Extensible Query Handlers)**:
- "Show me agent usage stats" → AgentStatsQueryHandler
- "List all my scheduled agents" → AgentListQueryHandler
- "What skills does my agent use?" → SkillsQueryHandler
- "Show my API usage this month" → UsageQueryHandler

### Extensibility Design

```python
class QueryHandler(ABC):
    """Base class for query handlers."""

    @abstractmethod
    async def can_handle(self, query: str) -> bool:
        """Check if this handler can handle the query."""

    @abstractmethod
    async def handle(self, query: str, context: ConversationContext) -> str:
        """Handle the query and return response."""

# Register query handlers
QUERY_HANDLERS = [
    LLMQueryHandler(),        # Default fallback
    AgentListQueryHandler(),  # "list my agents"
    AgentStatsQueryHandler(), # "show agent stats"
    # ... more handlers as needed
]
```

**Query Routing**:
1. Try each specialized handler in order
2. If none can handle, fall back to LLM
3. Handlers can be added without modifying Master Agent core

This allows the platform to add new query capabilities (agent management, analytics, help system, etc.) without changing the Master Agent's routing logic.

---

## Routing Priority Logic

```
1. Analyze user request

2. Detect PRIMARY intent:

   a) CREATE agent?
      - "I need an agent that..."
      - "Can you build an agent to..."
      - "Create an automation for..."
      → Route to Platform Agent Builder

   b) UPDATE agent?
      - "Update my [agent] to..."
      - "Change [agent] to do..."
      - "Add [feature] to my agent"
      → Route to Platform Agent Builder (with existing agent context)

   c) EXECUTE existing agent?
      - "Generate my report"
      - "Send a Slack message"
      - "Analyze this data"
      → Discover customer agents
      → Route to matching customer agent

   d) QUERY (informational)?
      - "What agents do I have?"
      - "How does this work?"
      - "Show me stats"
      → Route to Query Handler system (extensible)
      → Falls back to LLM if no handler matches

   e) UNCLEAR?
      → Ask clarifying question

3. If EXECUTE intent:
   - Search customer agents ONLY (tenant-scoped)
   - Platform agents are not discoverable for execution
   - Only exception: explicit @agent override by power user
```

---

## Alignment with Product Vision

| Vision Principle | How Master Agent Delivers |
|------------------|---------------------------|
| **No-Code Interface** | Users describe what they want; routing happens automatically |
| **Enterprise-Ready** | Tenant-isolated routing, RBAC-aware agent discovery |
| **Simplicity Over Flexibility** | Single entry point hides agent selection complexity |
| **Reliability Over Speed** | Clear fallbacks and graceful degradation |

---

## User Personas

### Primary User: Maya (Marketing Manager)

**Context**: Non-technical user who wants to get work done through conversation.

**Goals**:
- Get things done without knowing which agent to use
- Have clear, helpful interactions
- Understand when the system needs more information

**Pain Points**:
- Doesn't know which agents exist or what they do
- Gets frustrated by confusing or unhelpful responses
- Wants quick answers, not technical complexity

**Key Quote**: "I just want to say what I need. The system should figure out how to help me."

---

### Secondary User: Derek (Operations Lead)

**Context**: Power user who understands agents but wants intelligent routing.

**Goals**:
- See what the router is doing (transparency mode)
- Override routing when needed (@agent-name syntax)
- Quick access to frequently used agents

**Pain Points**:
- Black-box routing without visibility
- Can't force specific agent selection
- No way to see why routing decisions were made

---

## Problem Statement

### The "Which Agent?" Problem

Users face a fundamental discovery burden:
- Must know which agents exist
- Must understand what each agent does
- Must manually select the right agent
- Experience breaks when they guess wrong

**Solution**: Master Agent analyzes intent and routes automatically. Users describe goals in natural language; the system handles agent selection.

### The "Ambiguous Request" Problem

Many user requests could be handled by multiple agents:
- "Generate a report" - which report? from what data?
- "Send a message" - where? to whom?
- "Analyze data" - what data? what kind of analysis?

**Solution**: Master Agent detects ambiguity and asks targeted clarifying questions before routing.

---

## User Journeys

### Journey 1: Clear Intent - Direct Routing

**Scenario**: User request clearly maps to one agent

```
User: "Generate my weekly Notion project summary"

[Master Agent Analysis]
- Intent: Report generation from Notion
- Confidence: High (95%)
- Matching Agents: ["notion-reporter" (score: 95%)]
- Decision: Route to notion-reporter

Master Agent: "I'll get your Notion summary..."

[Routes to notion-reporter]

Notion Reporter: "Here's your weekly project summary:
- 5 projects on track
- 2 projects at risk
- 12 tasks completed this week
[Full report...]"
```

**Key Experience**: Seamless. User didn't know "notion-reporter" existed. They just asked for what they wanted.

---

### Journey 2: CREATE Intent - Route to Agent Builder

**Scenario**: User wants to create a new agent that doesn't exist

```
User: "I need an agent that extracts data from our Google Sheets and
      posts summaries to our #weekly-updates Slack channel"

[Master Agent Analysis]
- Intent: CREATE new agent
- Confidence: High (92%)
- Indicators: "I need an agent", describes capabilities
- Decision: Route to Platform Agent Builder

Master Agent: "I can help you create that agent! Let me hand you over
to the Agent Builder..."

[Routes to Platform Agent Builder Agent]

Agent Builder: "Great! I'll help you create a Google Sheets to Slack agent.

Let me confirm what you need:
- **Source**: Google Sheets (which sheet?)
- **Destination**: Slack #weekly-updates channel
- **Frequency**: Weekly (what day/time?)
- **Data**: What should I extract from the sheet?

Let's start with the Google Sheet - what's it called?"

User: "It's called 'Weekly Metrics'"

Agent Builder: "Perfect! Now, what data should I extract?
- All rows?
- Specific columns?
- Filtered data?"

User: "Just the 'Status' and 'Owner' columns where Status is 'Completed'"

Agent Builder: "Got it! When should this run?"

User: "Every Monday at 9am"

Agent Builder: "Excellent! I'm creating your agent:

**Agent Name**: sheets-to-slack-reporter
**Trigger**: Scheduled (Mondays at 9am)
**Skills**:
- Google Sheets reader
- Slack poster
- Data filtering

Setting this up now... [Creates agent with skills]

Done! Your agent is ready. Would you like me to:
1. Run it now to test
2. Show you how to edit it later
3. See the agent details"
```

**Key Experience**: User naturally described a capability they needed. Master Agent detected this was a CREATE intent (not EXECUTE) and routed to Agent Builder. The new customer agent was created conversationally.

---

### Journey 3: UPDATE Intent - Modify Existing Agent

**Scenario**: User wants to add functionality to an existing agent

```
User: "I want my notion-reporter to also post summaries to Slack"

[Master Agent Analysis]
- Intent: UPDATE existing agent
- Confidence: High (88%)
- Indicators: "my notion-reporter" (existing agent), "also post" (add capability)
- Agent Referenced: notion-reporter (exists)
- Decision: Route to Platform Agent Builder with agent context

Master Agent: "I'll help you update your notion-reporter! Let me connect
you with the Agent Builder..."

[Routes to Platform Agent Builder with notion-reporter context]

Agent Builder: "I can see your 'notion-reporter' agent currently:
- Reads from Notion
- Generates project summaries

You want to add Slack posting. Let me set that up!

Which Slack channel should I post to?"

User: "#team-updates"

Agent Builder: "Perfect! I'm updating your agent:

**Updated Agent**: notion-reporter
**New Skill Added**: Slack poster
**Configuration**:
- Post to #team-updates after generating summary
- Include formatting for Slack

Testing the new skill... ✓

Done! Your notion-reporter now:
1. Generates Notion summaries (existing)
2. Posts them to #team-updates (NEW)

Would you like me to:
1. Run it now to test
2. Update the posting format
3. Add more channels"
```

**Key Experience**: User referenced an existing agent and requested modification. Master Agent detected UPDATE intent, passed the agent context to Agent Builder, which loaded the existing configuration and added the new skill seamlessly.

---

### Journey 4: Ambiguous Intent - Clarifying Questions

**Scenario**: User request matches multiple agents or is unclear

```
User: "Generate a report"

[Master Agent Analysis]
- Intent: Report generation (generic)
- Confidence: Low (45%)
- Matching Agents: [
    "notion-reporter" (score: 60%),
    "financial-reporter" (score: 55%),
    "sales-analyzer" (score: 50%)
  ]
- Decision: Ask for clarification

Master Agent: "I can help you generate a report! Which type would you like?

1. **Notion Project Status** - Summary of your Notion projects
2. **Financial Report** - Revenue, expenses, and budget analysis
3. **Sales Analysis** - Sales trends and pipeline overview

Just let me know which one!"
```

User: "The Notion one"

```
[Master Agent Analysis]
- Intent: Notion report (clarified)
- Confidence: High (98%)
- Decision: Route to notion-reporter

Master Agent: "Got it! Getting your Notion project status..."

[Routes to notion-reporter and continues]
```

**Key Experience**: System recognized ambiguity and asked a helpful question. User provided clarification naturally.

---

### Journey 5: No Matching Agent - Suggest Creating One

**Scenario**: User wants to execute an action but no agent exists

```
User: "Send an email to my team about the project update"

[Master Agent Analysis]
- Intent: EXECUTE email sending
- Confidence: High (92%)
- Matching Agents: None (no email capability)
- Decision: Offer to create agent OR provide alternatives

Master Agent: "I don't have an email agent set up yet.

I can help in two ways:

**Option 1: Create an Email Agent** (recommended)
I can build an agent that sends emails for you. This will take a few minutes
to set up, but then you can use it anytime.

**Option 2: Use Existing Alternatives**
- Send a Slack message instead
- Create a Notion page with the update
- Generate a draft you can copy

Which would you prefer?"

User: "Create the email agent"

Master Agent: "Great! Let me connect you with the Agent Builder..."

[Routes to Platform Agent Builder to create customer email agent]
```

**Key Experience**: System detected no matching agent, but instead of just failing, offered to CREATE a new agent or use alternatives. User chose to create, and was seamlessly routed to Agent Builder.

---

### Journey 6: Power User Override

**Scenario**: User explicitly specifies which agent to use

```
Derek: "@financial-reporter show me Q4 revenue"

[Master Agent Analysis]
- Explicit agent reference detected: "financial-reporter"
- Decision: Skip analysis, route directly

Master Agent: "Routing to financial-reporter..."

[Routes directly to financial-reporter]

Financial Reporter: "Q4 revenue for 2025:
- Total: $1.2M
- Growth: 15% vs Q3
[Full analysis...]"
```

**Key Experience**: Power user bypassed automatic routing. System respected the explicit request.

---

### Journey 7: CREATE vs EXECUTE Ambiguity

**Scenario**: Unclear if user wants to create or execute

```
User: "I want to set up a weekly report from Notion"

[Master Agent Analysis]
- Intent: Ambiguous - CREATE or EXECUTE?
- Could mean: "Create an agent to do this" OR "Run existing report agent"
- Confidence: Medium (65%)
- Matching Agents: ["notion-reporter" exists]
- Decision: Clarify CREATE vs EXECUTE intent

Master Agent: "I can help with that! Did you mean:

1. **Run your existing Notion report** - Generate it now
2. **Create a new automated report** - Set up a recurring weekly report

Which one?"

User: "Create a new automated one"

[Master Agent Analysis]
- Intent: CREATE (clarified)
- Decision: Route to Platform Agent Builder

Master Agent: "Perfect! Let me connect you with the Agent Builder to set
that up..."

[Routes to Agent Builder]
```

**Key Experience**: Master Agent detected ambiguity between CREATE and EXECUTE intents. Asked a targeted question to clarify. User's answer determined the routing path.

---

### Journey 8: Multi-Turn Clarification

**Scenario**: Multiple clarifications needed

```
User: "I need a summary"

Master Agent: "A summary of what? For example:
- Notion projects
- Financial data
- Sales pipeline
- Something else?"

User: "My projects"

Master Agent: "Got it! Where are your projects stored?
- Notion
- Linear
- Jira"

User: "Notion"

Master Agent: "Perfect! Getting your Notion project summary..."

[Routes to notion-reporter]
```

**Key Experience**: Patient, progressive clarification. System asked only what it needed to know.

---

## Core Capabilities

### 1. Intent Analysis

**Purpose**: Understand what the user wants from natural language input.

**Components**:
- **Primary Action Detection**: CREATE agent, EXECUTE agent, or SIMPLE query
- **Intent Classification**: Categorize request type (report, action, analysis, etc.)
- **Entity Extraction**: Identify key entities (data sources, targets, topics)
- **Confidence Scoring**: How certain are we about the intent?
- **Ambiguity Detection**: Are there multiple valid interpretations?

**Input**: User message string
**Output**: Intent object with confidence score and action type

```python
IntentAnalysis {
    action_type: "EXECUTE",  # or "CREATE" or "SIMPLE_QUERY"
    primary_intent: "generate_report",
    entities: {
        source: "notion",
        report_type: "project_summary",
        timeframe: "weekly"
    },
    confidence: 0.95,
    ambiguous: false
}
```

**Action Type Detection**:

**CREATE Intent** - User wants to create a new agent
- Keywords: "I need an agent", "create an agent", "build", "set up automation", "make an agent"
- Pattern: Describes capabilities that don't exist yet
- Example: "I need an agent that sends Slack messages when..."
- Route to: Platform Agent Builder (new agent creation)

**UPDATE Intent** - User wants to modify an existing agent
- Keywords: "update my [agent]", "modify", "change", "add to my agent", "edit", "improve"
- Pattern: References existing agent + describes modifications
- Example: "Update my notion-reporter to also post to Slack"
- Route to: Platform Agent Builder (with existing agent context)

**EXECUTE Intent** - User wants to run an existing agent
- Keywords: "generate", "run", "send", "analyze", "show me", "get", "fetch"
- Pattern: Action request without mentioning agent creation/modification
- Example: "Generate my weekly report"
- Route to: Customer's matching agent (via discovery)

**QUERY Intent** - User asking questions (extensible)
- Keywords: "what", "how", "show", "list", "explain", "tell me about"
- Pattern: Information request, not action
- Example: "What agents do I have?"
- Route to: Query Handler system (extensible, falls back to LLM)

**Confidence Thresholds**:
- **High confidence (>85%)**: Route immediately
- **Medium confidence (60-85%)**: Ask simple clarifying question
- **Low confidence (<60%)**: Ask open-ended clarifying question
- **CREATE vs EXECUTE ambiguous**: Ask specific clarification

---

### 2. Agent Discovery

**Purpose**: Find registered **customer agents** that can handle the request.

**Important**: Discovery only searches **customer agents** (tenant-scoped). Platform agents are not discoverable through this process—they are invoked directly by action type (e.g., CREATE → Agent Builder).

**Discovery Process**:
1. Query AgentRegistry for customer's agents only (tenant-scoped)
2. Match intent to agent skills/capabilities
3. Score each agent on how well they match
4. Filter by availability (health checks, circuit breakers)
5. Return ranked list of candidates

**What Gets Discovered**:
- ✅ Customer's agents (created via Agent Builder)
- ✅ Agents with SKILL.md files
- ✅ Tenant-scoped agents only
- ❌ Platform agents (not discoverable)
- ❌ Other tenant's agents

**Matching Criteria**:
- **Skill overlap**: Does agent have skills that match intent?
- **Domain alignment**: Is agent in the right domain (finance, projects, etc.)?
- **Historical performance**: Success rate, average latency
- **Recency**: When was agent last used successfully?

**Scoring Formula**:
```
score = (skill_match * 0.6) + (domain_match * 0.2) +
        (performance * 0.1) + (recency * 0.1)
```

**Output**: Ranked list of matching agents with scores

```python
[
    Agent("notion-reporter", score=0.95),
    Agent("project-manager", score=0.72),
    Agent("generic-reporter", score=0.45)
]
```

---

### 3. Clarifying Questions

**Purpose**: Resolve ambiguity when routing decision is uncertain.

**When to Ask**:
- Multiple agents match with similar scores (within 15% of each other)
- Confidence score below threshold (<85%)
- Missing critical entities (e.g., data source not specified)
- User request is too vague ("help me", "do something")

**Question Strategies**:

**A. Multiple Choice** (when several agents match)
```
"I can help with:
1. [Agent 1 capability]
2. [Agent 2 capability]
3. [Agent 3 capability]

Which one?"
```

**B. Entity Clarification** (when missing key information)
```
"Where is the data you want me to analyze?
- Notion
- Google Sheets
- Our database"
```

**C. Open-Ended** (when very uncertain)
```
"Could you tell me a bit more about what you're trying to accomplish?"
```

**Question Design Principles**:
- Be specific and actionable
- Offer clear options when possible
- Don't ask multiple things at once
- Use examples to clarify
- Keep it conversational, not technical

---

### 4. Smart Routing

**Purpose**: Send request to the best handler based on analysis.

**Primary Routing Logic** (Action Type First):

```
1. Analyze user request → Get intent + action_type + confidence

2. Check action_type:

   a) If action_type = "CREATE":
      → Route to Platform Agent Builder
      → Agent Builder creates new customer agent

   b) If action_type = "UPDATE":
      → Identify which agent to update
      → Route to Platform Agent Builder with agent context
      → Agent Builder modifies existing customer agent

   c) If action_type = "QUERY":
      → Route to Query Handler system
      → Try specialized handlers first
      → Fall back to LLM if no handler matches

   d) If action_type = "EXECUTE":
      → Proceed to agent discovery (below)

   e) If action_type is ambiguous:
      → Ask clarifying question
      → "Did you want to: create/update/run an agent?"

3. For EXECUTE intent, run agent discovery:

   a) If confidence >= 85% AND top agent score >= 85%:
      → Route to that customer agent immediately

   b) Else if 2-4 agents score within 15% of each other:
      → Ask multiple choice clarifying question

   c) Else if confidence < 60%:
      → Ask open-ended clarifying question

   d) Else if no agents match:
      → Offer to CREATE agent OR suggest alternatives

4. Special case - Explicit override:
   If user specifies @agent-name:
   → Skip all analysis, route directly to that agent
```

**Routing Targets**:
- **Platform Agent Builder** (for CREATE intent)
- **Customer Agent** (for EXECUTE intent, discovered via registry)
- **Direct LLM** (for SIMPLE_QUERY intent)
- **Clarifying Question** (for ambiguous cases)

**Routing Output**: Target agent + relevant context to pass

---

### 5. Context Management

**Purpose**: Maintain conversation history for clarifications and routing.

**What to Track**:
- **Recent messages**: Last 10 user/assistant exchanges
- **Clarification history**: What we've asked and learned
- **Entity memory**: Extracted entities (project names, dates, etc.)
- **Routing history**: Which agents were used in this session

**Context Usage**:
- Inform clarifying questions (don't ask what we already know)
- Pass relevant context to routed agents
- Understand follow-up requests ("Yes, that one")
- Improve intent analysis with session context

**Privacy**:
- Only pass relevant context to agents (not full conversation)
- Respect tenant isolation
- Log routing decisions (without message content)

---

## Technical Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────┐
│                       USER REQUEST                           │
│   "Generate my Notion summary" OR "Create a Slack agent"    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     MASTER AGENT                             │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. INTENT ANALYZER                                   │  │
│  │     - Detect action_type (CREATE/EXECUTE/QUERY)       │  │
│  │     - Classify intent (report, notification, etc.)    │  │
│  │     - Extract entities (source, target, etc.)         │  │
│  │     - Calculate confidence (0-100%)                   │  │
│  └───────────────────┬───────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  2. ACTION TYPE ROUTING                               │  │
│  │     - CREATE? → Platform Agent Builder                │  │
│  │     - SIMPLE_QUERY? → Direct LLM                      │  │
│  │     - EXECUTE? → Continue to discovery               │  │
│  │     - AMBIGUOUS? → Ask clarifying question            │  │
│  └───────────────────┬───────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  3. AGENT DISCOVERY (only for EXECUTE)                │  │
│  │     - Query AgentRegistry (customer agents only)      │  │
│  │     - Match skills to intent                          │  │
│  │     - Score candidates (0-100%)                       │  │
│  │     - Filter by availability                          │  │
│  └───────────────────┬───────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  4. ROUTING DECISION                                  │  │
│  │     - High score (>85%) → Route immediately           │  │
│  │     - Multiple matches → Ask clarifying question      │  │
│  │     - No matches → Offer CREATE or alternatives       │  │
│  └───────────────────┬───────────────────────────────────┘  │
│                      │                                       │
└──────────────────────┼───────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   PLATFORM   │ │   CUSTOMER   │ │   CLARIFY    │
│AGENT BUILDER │ │    AGENT     │ │   QUESTION   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Creates new   │ │Executes task │ │Wait for user │
│customer agent│ │& returns     │ │clarification │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                       │
                       ▼
       ┌───────────────────────────────┐
       │   STREAM RESPONSE TO USER     │
       └───────────────────────────────┘
```

---

### Component Design

#### Intent Analyzer
```python
class IntentAnalyzer:
    """Analyzes user messages to extract intent and entities."""

    async def analyze(self, message: str, context: ConversationContext) -> IntentAnalysis:
        """
        Use LLM to analyze user message.

        Returns:
            IntentAnalysis with:
            - primary_intent: str
            - entities: dict
            - confidence: float
            - ambiguous: bool
        """
```

#### Agent Discovery Service
```python
class AgentDiscoveryService:
    """Finds and scores agents that match user intent."""

    async def find_matching_agents(
        self,
        intent: IntentAnalysis,
        tenant_id: str
    ) -> list[ScoredAgent]:
        """
        Query registry and score agents.

        Returns ranked list of agents with scores.
        """
```

#### Clarification Manager
```python
class ClarificationManager:
    """Generates and manages clarifying questions."""

    async def generate_question(
        self,
        intent: IntentAnalysis,
        candidates: list[ScoredAgent]
    ) -> ClarifyingQuestion:
        """
        Create appropriate clarifying question.

        Returns question with options (if multiple choice).
        """
```

#### Router
```python
class MasterAgentRouter:
    """Routes requests to agents based on analysis."""

    async def route(
        self,
        intent: IntentAnalysis,
        candidates: list[ScoredAgent],
        context: ConversationContext
    ) -> RoutingDecision:
        """
        Decide where to route the request.

        Returns either:
        - Route to agent
        - Ask clarifying question
        - Graceful failure
        """
```

---

### Integration Points

#### With Chat API
- Master Agent handles `/api/v1/chat` endpoint
- Receives user messages
- Returns SSE stream with responses
- Manages conversation sessions

#### With Agent Registry
- Queries registered agents
- Gets agent metadata (skills, capabilities, health)
- Respects tenant scoping
- Checks agent availability

#### With Existing Agents
- Routes requests via A2A protocol
- Passes relevant context
- Streams agent responses back to user
- Handles agent errors gracefully

#### With RBAC
- Filters agents by user permissions
- Only shows agents user can access
- Logs routing decisions for audit

---

## Success Criteria

### User Experience Metrics
- **Routing Accuracy**: >85% of requests routed to appropriate agent
- **Clarification Rate**: <30% of requests require clarification
- **User Satisfaction**: >4/5 stars for routing quality
- **First-Try Success**: >80% of requests succeed without retry

### Technical Metrics
- **Analysis Latency**: <200ms for intent analysis
- **Discovery Latency**: <100ms for agent matching
- **End-to-End**: <500ms from request to agent routing
- **Availability**: 99.9% uptime for routing service

### Quality Metrics
- **False Positives**: <5% (wrong agent selected)
- **False Negatives**: <10% (didn't find available agent)
- **Question Quality**: >85% of clarifications resolved on first ask
- **Graceful Failures**: 100% of "no match" scenarios provide alternatives

---

## Edge Cases

### Ambiguous Requests
**Problem**: Multiple agents match with similar scores

**Solution**:
- Ask multiple choice question with top 3 options
- Include brief description of each option
- Remember user choice for future similar requests

---

### No Matching Agents
**Problem**: User request doesn't match any available agents

**Solution**:
- Explain limitation clearly
- Offer alternative approaches
- Suggest related agents that might help
- Log as potential feature gap

---

### Agent Unavailable
**Problem**: Best-matching agent is down or failing

**Solution**:
- Check health before routing
- Skip unhealthy agents during discovery
- Offer fallback agents if available
- Inform user of temporary unavailability

---

### Follow-Up Requests
**Problem**: User says "Yes" or "The first one" without context

**Solution**:
- Maintain conversation context
- Track last clarifying question asked
- Map user response to previous options
- Ask for clarification if still ambiguous

---

### Circular Requests
**Problem**: Agent asks Master Agent for help (infinite loop)

**Solution**:
- Track routing depth (max 2 levels)
- Break loop after threshold
- Return error to agent
- Log for debugging

---

### CREATE vs EXECUTE Confusion
**Problem**: User request could mean either "create agent" or "execute agent"

**Examples**:
- "I want to set up weekly reports" - Create new automation OR run existing report?
- "Send Slack messages" - Create Slack agent OR use existing Slack agent?

**Solution**:
- Detect ambiguity in action_type analysis
- Ask targeted question: "Did you mean: 1) Run existing agent, 2) Create new agent?"
- Present context-specific options
- Remember user's preference for similar future requests

---

## Out of Scope (Phase 1)

### Not Included
- ❌ Dynamic agent creation
- ❌ Multi-agent orchestration
- ❌ Parallel agent execution
- ❌ Complex workflows (if-then-else)
- ❌ Agent marketplace integration
- ❌ Proactive suggestions
- ❌ Learning from user feedback

### Future Phases
These features may be added later:
- **Phase 2**: Multi-agent orchestration (sequential)
- **Phase 3**: Dynamic agent creation
- **Phase 4**: Learning and optimization
- **Phase 5**: Proactive assistance

---

## Open Questions

1. **Clarification Limits**: How many clarifications before we give up?
2. **Context Size**: How much context to pass to agents?
3. **Default Behavior**: What if user says "surprise me"?
4. **Agent Scoring**: Should we use ML for scoring or keep it rules-based?
5. **Session Management**: How long to keep conversation context?
6. **Debug Mode**: Should power users see raw scores and analysis?

---

## Implementation Phases

### Phase 1: Basic Routing (MVP)
- Intent analysis with LLM
- Simple agent discovery (skill matching)
- Single-choice routing (pick best agent)
- Basic error handling

**Success**: Can route clear requests to correct agents

---

### Phase 2: Clarification
- Add clarification question generation
- Implement multi-turn clarification flow
- Context management for follow-ups
- Multiple choice questions

**Success**: Can handle ambiguous requests gracefully

---

### Phase 3: Polish
- Power user overrides (@agent syntax)
- Debug mode for transparency
- Graceful failure messages
- Performance optimization

**Success**: Production-ready with good UX

---

## References

**OmniForge Internal:**
- [Product Vision](/Users/sohitkumar/code/omniforge/specs/product-vision.md)
- [Base Agent Interface](/Users/sohitkumar/code/omniforge/src/omniforge/agents/base.py)
- [Agent Registry](/Users/sohitkumar/code/omniforge/src/omniforge/agents/registry.py)
- [Agent Discovery Service](/Users/sohitkumar/code/omniforge/src/omniforge/orchestration/discovery.py)

---

## Evolution Notes

### 2026-01-26 v2.2 (UPDATE + Extensible Queries + BaseAgent Integration)

**Added three critical capabilities:**

**1. UPDATE Intent**:
- Users can now modify existing customer agents
- UPDATE detected via keywords: "update my [agent]", "modify", "change", "add to"
- Routes to Platform Agent Builder with existing agent context
- Agent Builder loads current configuration and applies modifications
- Adds/removes skills without recreating agent
- New user journey (Journey 3) demonstrates UPDATE flow

**2. Extensible Query Handling**:
- Replaced "SIMPLE_QUERY" with extensible "QUERY" intent
- Query Handler system allows pluggable handlers for different query types
- Current: LLMQueryHandler (default fallback)
- Future: AgentListQueryHandler, AgentStatsQueryHandler, SkillsQueryHandler, etc.
- New queries can be added without modifying Master Agent core
- Examples: "list my agents", "show usage stats", "what skills does X have?"

**3. BaseAgent and Skills System Integration**:
- Master Agent **is a BaseAgent** implementation
- Has `identity`, `capabilities`, and `skills` like all agents
- Customer agents created as BaseAgent subclasses with SKILL.md files
- Agent discovery uses skill matching for semantic routing
- Skills provide composability (add/remove without code changes)
- Full integration with existing agent architecture

**Design Decisions**:
- UPDATE reuses Agent Builder (not separate update agent)
- Query handlers are extensible (open for future query types)
- Master Agent follows same patterns as all other agents
- Skills drive discovery and capabilities

**Impact**: Platform now supports full agent lifecycle (CREATE, UPDATE, EXECUTE, DELETE) and is extensible for new query types without core changes.

---

### 2026-01-26 v2.1 (CREATE vs EXECUTE)

**Added critical architectural distinction:**

**Two Types of Agents**:
1. **Platform Agents** - System-level (Agent Builder, Health Monitor, etc.)
2. **Customer Agents** - User-created with skills, tenant-scoped

**Two Primary Intents**:
1. **CREATE** - User wants to create new agent → Route to Platform Agent Builder
2. **EXECUTE** - User wants to run existing agent → Discover & route to customer agent

**Key Changes**:
- Added action_type detection (CREATE/EXECUTE/SIMPLE_QUERY) to intent analysis
- Updated agent discovery to only search customer agents (tenant-scoped)
- Platform agents are invoked directly, not discovered
- Added CREATE vs EXECUTE ambiguity handling
- Added 3 new user journeys showcasing CREATE intent
- Updated routing logic to check action_type first
- Updated flow diagrams to show CREATE/EXECUTE branching

**Design Decisions**:
- Platform Agent Builder handles all agent creation (not master agent itself)
- Customer agents are discoverable; platform agents are not
- Clear separation between "create" and "execute" use cases
- Master Agent acts as smart dispatcher to appropriate handler

**Impact**: This distinction is fundamental to how the platform works. Master Agent must correctly identify if user wants to CREATE new capabilities or EXECUTE existing ones.

---

### 2026-01-26 v2.0 (Simplified)

**Simplified from v1.0 based on feedback:**

Removed complexity to focus on core routing + clarification:
- ❌ Dynamic agent creation (deferred)
- ❌ Multi-agent orchestration (deferred)
- ❌ Complex workflows (deferred)
- ✅ Intent analysis (kept)
- ✅ Agent discovery (kept, simplified)
- ✅ Smart routing (kept, simplified)
- ✅ Clarifying questions (kept - key feature!)
- ✅ Context management (kept, simplified)

**Key Principle**: One request → one agent → one response. Keep it simple.

**Next Steps**:
1. Get spec approval ✓
2. Technical planning phase
3. Implement Phase 1 (basic routing)
4. Implement Phase 2 (clarification)
5. Implement Phase 3 (polish)
