# Chain of Thought Agent with Unified Tool Calling Interface

**Created**: 2026-01-11
**Last Updated**: 2026-01-11
**Version**: 1.1
**Status**: Draft

---

## Overview

The Chain of Thought (CoT) Agent is a reasoning-first agent architecture for OmniForge where the thinking process is first-class and visible. Every operation the agent performs - whether calling an LLM for reasoning, invoking an external API, executing a skill, delegating to a sub-agent, or querying a database - flows through a unified tool interface that treats each call as a visible step in the agent's reasoning chain. This design serves a dual audience: developers who need to debug and understand agent behavior, and end-users who need to trust and audit what the agent is doing on their behalf.

The unified tool interface eliminates the conceptual divide between "thinking" and "doing" by making all operations explicit reasoning steps. Even LLM calls for reasoning flow through this interface via LiteLLM, enabling complete visibility, cost tracking, multi-model support, and enterprise-grade control. When an agent calls an LLM to analyze a request, queries a database for data, invokes a skill to process documents, or delegates to another agent, each action is a transparent link in the chain of thought that users can inspect, audit, and trust.

---

## Alignment with Product Vision

This specification directly advances OmniForge's core vision:

- **Agents Build Agents**: CoT agents can spawn and orchestrate sub-agents through the unified tool interface, with full visibility into the delegation chain
- **Enterprise-Ready from Day One**: The transparent reasoning chain provides built-in compliance and auditability without additional tooling
- **Simplicity Over Flexibility**: One unified interface for all tool types reduces cognitive load for developers while maintaining power
- **Reliability Over Speed**: Explicit reasoning steps make agent behavior predictable and debuggable, prioritizing trustworthy outcomes over raw performance
- **Dual Deployment Support**: The CoT architecture works identically in the open-source SDK and premium platform, with configurable visibility levels for different audiences

---

## User Personas

### Primary Users

#### SDK Developer (Technical Builder)

A software developer using the Python SDK to create custom agents with chain of thought capabilities.

**Context**: Working in their IDE, writing Python code to build agents that need to perform complex multi-step tasks.

**Goals**:
- Understand exactly why an agent made specific decisions
- Debug agent behavior when it produces unexpected results
- Build agents that users can trust by making reasoning visible
- Create reliable agents that handle edge cases gracefully

**Pain Points**:
- "Black box" agents where failures are impossible to diagnose
- Having to instrument agents manually to understand their behavior
- Different interfaces for different types of operations (tools, skills, sub-agents)
- Difficulty explaining to stakeholders why an agent behaved a certain way

**Key Quote**: "I need to know exactly what my agent was thinking when it decided to call that API. When something goes wrong, I can't spend hours guessing."

---

#### End-User (Agent Consumer)

A business user or customer interacting with agents built on OmniForge, either through a UI or through the premium chatbot interface.

**Context**: Using agents to accomplish tasks - processing documents, analyzing data, automating workflows - without understanding the underlying technology.

**Goals**:
- Trust that the agent is doing what they asked
- Understand why the agent took specific actions
- Feel confident the agent isn't making mistakes or misusing data
- Have visibility into long-running operations

**Pain Points**:
- Not knowing if the agent understood their request correctly
- Anxiety during long operations ("Is it still working? Did it forget what I asked?")
- Difficulty verifying that sensitive operations were handled correctly
- Feeling out of control when agents make autonomous decisions

**Key Quote**: "I asked it to analyze our quarterly data, and five minutes later it gave me a result. I have no idea if it actually looked at the right files or just made something up."

---

#### Enterprise Administrator (Compliance and Governance)

A technical administrator responsible for deploying, monitoring, and governing agent usage within an organization.

**Context**: Managing agent deployments across teams, ensuring compliance with policies, and investigating issues when they arise.

**Goals**:
- Audit trail for all agent actions
- Enforce policies on what agents can do
- Investigate incidents and explain agent behavior to stakeholders
- Demonstrate compliance to regulators or auditors

**Pain Points**:
- Agents operating as opaque black boxes
- Lack of standardized logging across different agent types
- Difficulty explaining agent decisions to non-technical stakeholders
- No way to enforce policies at the reasoning level

**Key Quote**: "When the board asks why the AI system made a particular decision, I need to show them exactly what it was thinking, not just what it did."

---

### Secondary Users

#### External Agent Developer (Interoperability)

A developer building A2A-compliant agents on another platform who wants their agents to collaborate with OmniForge CoT agents.

**Goals**: Understand the reasoning chain structure for interoperability, trust delegated tasks.

---

#### QA/Testing Engineer

Responsible for validating agent behavior meets requirements.

**Goals**: Reproduce agent decisions, verify reasoning quality, catch edge case failures before production.

---

## Problem Statement

### The Opacity Problem

Current AI agents operate as black boxes. Users send a request and receive a response, but the journey between input and output is invisible. This creates multiple cascading problems:

**For Developers**: When an agent produces incorrect output, developers cannot determine whether the problem was in the prompt understanding, the decision to use certain tools, the tool execution itself, or the synthesis of results. Debugging becomes guesswork.

**For End-Users**: Users cannot verify that the agent understood their request or that it took appropriate actions. This erodes trust, especially for high-stakes operations involving sensitive data or important decisions.

**For Enterprises**: Without an audit trail of agent reasoning, organizations cannot demonstrate compliance, investigate incidents, or explain decisions to stakeholders. This blocks enterprise adoption.

### The Fragmented Interface Problem

Current agent architectures treat different types of operations differently:
- External tools have one calling convention
- Internal skills have another
- Sub-agent delegation has yet another
- Database operations are often completely separate

This fragmentation creates cognitive overhead for developers, inconsistent logging and observability, and difficulty building unified governance policies.

### The Trust Gap

Users fundamentally do not trust AI agents for important tasks because they cannot see what the agent is doing. The CoT Agent with Unified Tools solves this by making the agent's reasoning chain explicit and visible, transforming opacity into transparency.

---

## Core Design Philosophy

### Tool Calls ARE Reasoning Steps

The fundamental insight of this design is that there is no meaningful distinction between "thinking" and "acting" for an agent. When an agent decides to call a weather API, that decision IS a reasoning step. The call, its parameters, and its results are all part of the agent's chain of thought.

This means:
- Every tool call is automatically a visible step in the reasoning chain
- The reasoning chain is not just text - it includes structured actions and their outcomes
- Users can inspect the full journey from question to answer
- Debugging is natural because the failure point is visible in the chain

### One Interface to Rule Them All

All operations flow through the same unified tool interface, **including LLM calls for reasoning**:

| Operation Type | Traditional Approach | Unified Tool Approach |
|---------------|---------------------|----------------------|
| LLM reasoning | Direct LLM API calls | `tool.call("llm", {"model": "claude-sonnet", "prompt": "..."})` |
| External API call | HTTP client with custom handling | `tool.call("weather_api", {...})` |
| Skill invocation | Direct method call | `tool.call("document_processor", {...})` |
| Sub-agent delegation | A2A message passing | `tool.call("research_agent", {...})` |
| Database query | ORM or SQL | `tool.call("database", {...})` |
| File operations | Direct filesystem access | `tool.call("file_system", {...})` |

The unified interface provides:
- Consistent logging and observability across ALL operations (including LLM calls)
- Uniform permission and policy enforcement
- Standardized error handling and retry logic
- Natural chain of thought integration
- **Complete cost tracking** - every LLM call attributed to specific task/tenant
- **Multi-provider support** - LiteLLM handles provider routing and fallbacks

### Visibility by Default, Configurable by Design

All reasoning steps are visible by default. This ensures:
- Developers always have full debugging capability
- Audit trails are complete without additional configuration
- Trust is the default state, not something users must opt into

However, visibility is configurable at multiple levels:
- **Per-Agent**: Some agents may have simplified views for non-technical users
- **Per-Operation-Type**: Organizations may hide internal skill details while showing external calls
- **Per-User-Role**: Administrators see everything; end-users see summaries
- **Per-Deployment**: Production may have different visibility than development

### LLM as a Tool: The Ultimate Unification

**The agent's reasoning engine itself is a tool.** This is a radical departure from traditional agent architectures where the LLM is "special" or treated differently.

**Why this matters:**

**Complete Cost Visibility**: Every LLM call appears in the reasoning chain with full cost attribution.
```
Step 5: [TOOL: llm/gpt-4]
  Prompt: "Analyze the sales trends..."
  Response: "The data shows..."
  Tokens: 1,247 (input: 850, output: 397)
  Cost: $0.0156
  Duration: 1.2s
  Model: gpt-4-turbo-2024-04-09
```

**Multi-Model Intelligence**: Agents can strategically choose models based on task complexity, cost, and privacy requirements.
```python
# Fast, cheap model for simple analysis
tool.call("llm", {"model": "gpt-3.5-turbo", "prompt": "Summarize..."})

# Powerful model for complex reasoning
tool.call("llm", {"model": "claude-opus", "prompt": "Deep analysis..."})

# Local model for sensitive data
tool.call("llm", {"model": "local/llama3", "prompt": "Process PII..."})
```

**Provider Flexibility**: LiteLLM integration enables:
- Automatic provider fallbacks (Claude down? Switch to GPT-4)
- Load balancing across providers
- Cost optimization (route to cheapest provider for task)
- Regional compliance (use EU-hosted models for GDPR data)

**Enterprise Control**: The unified interface becomes a control plane for ALL agent operations:
- Rate limiting: "Max 1000 LLM calls per hour per tenant"
- Cost budgets: "Stop agent if task exceeds $5 in LLM costs"
- Model governance: "Only allow approved models in production"
- Audit trails: "Show every LLM call this agent made with full prompts"

**This is not just an implementation detail - it's a fundamental architectural choice that enables enterprise-grade control and transparency.**

---

## User Journeys

### Journey 1: Developer Debugging Agent Behavior

**Persona**: SDK Developer
**Context**: The agent produced an incorrect analysis of sales data. The developer needs to understand why.

1. **Developer reviews task output** - They see the final result is wrong (projected revenue is impossibly high)

2. **Developer opens reasoning chain** - The SDK provides access to the full chain of thought for the task

3. **Developer examines tool calls** - They see the sequence:
   ```
   Step 1: [TOOL: llm/claude-sonnet] "Analyze this sales data request"
          → "I need to fetch Q4 sales data from the database"
          Cost: $0.0012 | 450 tokens

   Step 2: [TOOL: database] query="SELECT * FROM sales WHERE quarter='Q4'"
          → 1,247 rows returned

   Step 3: [TOOL: llm/gpt-3.5-turbo] "Calculate revenue projection"
          → "Multiplying total sales by growth rate: $847M"
          Cost: $0.0003 | 280 tokens

   Step 4: [TOOL: llm/claude-sonnet] "Verify this projection seems reasonable"
          → "The growth rate of 847 seems unusually high, let me verify"
          Cost: $0.0008 | 320 tokens

   Step 5: [TOOL: database] query="SELECT growth_rate FROM metrics"
          → 847 (should be 8.47%)
   ```

4. **Developer identifies the bug** - The growth rate was stored as a percentage integer (847) but used as a multiplier. The reasoning chain shows exactly where the logic went wrong.

5. **Developer fixes the issue** - They add data validation in the tool call to detect unreasonable values

**Key Experience**: The developer never had to guess. The reasoning chain showed the exact sequence of decisions and data that led to the error. **Crucially, they could see which LLM calls were made, what models were used, and exactly what each LLM concluded** - providing complete transparency into the agent's reasoning process. They also noticed the agent switched from Claude to GPT-3.5 for the calculation (cheaper model for simple math), demonstrating the multi-model optimization in action.

---

### Journey 2: End-User Monitoring a Sensitive Operation

**Persona**: End-User (Finance Manager)
**Context**: User asked the agent to analyze expense reports and flag anomalies. They need to trust the results.

1. **User submits request** - "Review all expense reports from Q3 and flag anything suspicious"

2. **Agent begins processing** - User sees real-time reasoning updates:
   ```
   Analyzing your request...
   - Accessing expense report database
   - Retrieved 342 expense reports from Q3
   - Examining report patterns...
   ```

3. **User sees tool calls in progress** - Each database access and analysis step appears as a visible step:
   ```
   Step 3/12: Checking employee expense patterns
   [Querying: expense_reports WHERE submitted_by='user_xxx']
   [Found: 47 reports, total: $23,450]
   ```

4. **Agent flags anomalies with reasoning** - Results include not just flags but why:
   ```
   FLAGGED: Report #4521 - $4,200 dinner expense
   Reasoning: This is 8x the typical dinner expense for this employee.
   The receipt was submitted 3 weeks after the expense date.
   Similar anomaly found in 2 other reports from same employee.
   ```

5. **User trusts the result** - They can see the agent examined the right data, used reasonable logic, and explained its reasoning

**Key Experience**: The user never felt anxious about what the agent was doing. They could see it working, understand its logic, and trust the output.

---

### Journey 3: Compliance Officer Auditing Agent Decisions

**Persona**: Enterprise Administrator
**Context**: An agent made loan recommendations. Regulators require explanation of AI-assisted decisions.

1. **Compliance officer accesses audit log** - They query the system for all loan recommendation tasks

2. **Officer reviews specific decision** - For a denied loan application:
   ```
   Task: Loan Application Review - Application #78291
   Outcome: Recommendation = DENY

   Reasoning Chain:
   ├─ Step 1: Received application data
   ├─ Step 2: [TOOL: credit_check] applicant_id=78291 -> score=580
   ├─ Step 3: [THINKING] "Credit score is below threshold (620)"
   ├─ Step 4: [TOOL: income_verification] -> annual_income=$42,000
   ├─ Step 5: [TOOL: debt_calculator] -> debt_to_income=0.48
   ├─ Step 6: [THINKING] "DTI ratio exceeds maximum (0.43)"
   ├─ Step 7: [SKILL: risk_assessment] -> risk_level=HIGH
   └─ Step 8: Final decision based on: credit_score < 620, DTI > 0.43
   ```

3. **Officer verifies compliance** - The chain shows only approved data sources were used, no prohibited factors were considered, and the decision followed the documented policy

4. **Officer generates report** - The audit trail exports to a compliance report format

**Key Experience**: The compliance officer can definitively prove what data the agent used and how it reached its decision, satisfying regulatory requirements.

---

### Journey 4: Agent Orchestrating Sub-Agents

**Persona**: SDK Developer building a research agent
**Context**: A research agent needs to delegate tasks to specialized sub-agents

1. **User requests comprehensive research** - "Research the competitive landscape for AI agent platforms"

2. **Primary agent plans delegation** - Its chain of thought shows the plan:
   ```
   [THINKING] "This requires multiple specialized analyses"
   [THINKING] "I will delegate to: market_research_agent, tech_analysis_agent, news_agent"
   ```

3. **Sub-agent calls appear as tool calls**:
   ```
   [TOOL: market_research_agent]
     query="AI agent platform market size and growth"
     -> Delegated task created: task_id=abc123

   [TOOL: tech_analysis_agent]
     query="Technical comparison of agent platforms"
     -> Delegated task created: task_id=def456
   ```

4. **Sub-agent results flow back** - Each sub-agent's response appears in the chain:
   ```
   [TOOL: market_research_agent] task_id=abc123 COMPLETED
     result: {market_size: "$2.3B", growth_rate: "34% CAGR", ...}
     sub_agent_reasoning: [collapsible chain of 12 steps]
   ```

5. **Primary agent synthesizes** - The final reasoning shows how results were combined:
   ```
   [THINKING] "Combining insights from 3 sub-agents..."
   [TOOL: synthesizer] inputs=[market_data, tech_analysis, news_summary]
   ```

**Key Experience**: The developer sees exactly how work was delegated, can drill into sub-agent reasoning if needed, and can debug issues at any level of the hierarchy.

---

### Journey 5: User Configuring Visibility Preferences

**Persona**: End-User (Non-Technical)
**Context**: User finds detailed reasoning overwhelming and wants a simpler view

1. **User sees default detailed view** - Every tool call and thinking step is visible

2. **User feels overwhelmed** - "I don't need to see every database query, I just want to know it's working"

3. **User accesses visibility settings** - Through the UI, they can configure:
   ```
   Reasoning visibility:
   [x] Show progress summary
   [ ] Show detailed thinking steps
   [x] Show external API calls
   [ ] Show internal skill calls
   [x] Show final reasoning for decisions
   ```

4. **User sees simplified view** - Future interactions show:
   ```
   Analyzing your data...
   - Checked 3 external sources
   - Processed 247 records

   Result: [summary]
   Why: [brief reasoning explanation]
   ```

5. **User retains ability to drill down** - A "Show details" option reveals the full chain when needed

**Key Experience**: Users control their own experience - experts see everything, casual users see summaries, everyone can access full details when needed.

---

## Core Capabilities

### 1. Chain of Thought Engine

The CoT Engine manages the agent's reasoning process and maintains the chain of thought as a first-class data structure.

**Responsibilities**:
- Maintain the reasoning chain state during task execution
- Emit reasoning events for streaming to clients
- Persist completed chains for debugging and audit
- Support branching reasoning (multiple hypotheses explored)

**Reasoning Chain Structure**:
```
ReasoningChain {
  task_id: UUID
  agent_id: UUID
  started_at: DateTime
  status: thinking | tool_calling | waiting | completed | failed

  steps: [
    ReasoningStep {
      step_id: UUID
      step_number: int
      type: thinking | tool_call | tool_result | synthesis
      timestamp: DateTime

      // For thinking steps
      thought?: string
      confidence?: float  // Optional confidence indicator

      // For tool calls
      tool_call?: {
        tool_type: external | skill | sub_agent | database | file_system
        tool_name: string
        arguments: dict
        correlation_id: UUID  // Links call to result
      }

      // For tool results
      tool_result?: {
        correlation_id: UUID
        success: bool
        result: any
        error?: string
        duration_ms: int
      }

      // For synthesis
      synthesis?: {
        sources: [step_id, ...]  // Which steps informed this
        conclusion: string
      }

      // Visibility metadata
      visibility: {
        level: full | summary | hidden
        summary?: string  // Human-readable summary for non-technical users
      }
    }
  ]

  // Hierarchical chains for sub-agent delegation
  child_chains?: [ReasoningChain, ...]
}
```

---

### 2. Unified Tool Interface

All external operations flow through a single, consistent interface.

**Tool Registration**:
```
ToolDefinition {
  name: string                    // Unique identifier
  type: external | skill | sub_agent | database | file_system | custom
  description: string             // What this tool does

  // Input specification
  parameters: {
    [param_name]: {
      type: string | int | bool | object | array
      description: string
      required: bool
      default?: any
    }
  }

  // Output specification
  returns: {
    type: any
    description: string
  }

  // Execution configuration
  config: {
    timeout_ms: int
    retry_policy: {retries: int, backoff_ms: int}
    cache_ttl_seconds?: int       // Optional result caching
  }

  // Visibility configuration
  visibility: {
    default_level: full | summary | hidden
    summary_template?: string     // Template for generating summaries
  }

  // Security and permissions
  permissions: {
    required_roles: [string, ...]
    audit_level: none | basic | full
  }
}
```

**Tool Call Flow**:
```
1. Agent decides to call tool
   -> Thinking step added: "I need to check the weather"

2. Tool call initiated
   -> Tool call step added with arguments
   -> Permissions checked against caller context
   -> Request routed to appropriate handler

3. Tool execution
   -> Handler executes (external API, skill, sub-agent, etc.)
   -> Timeout and retry policies applied
   -> Result or error captured

4. Result integrated
   -> Tool result step added to chain
   -> Agent continues reasoning with result
```

---

### 3. Built-in Tool Types

#### LLM (Language Model) - Powered by LiteLLM
The agent's reasoning engine, exposed as a tool for complete transparency and control.

```python
llm.call("llm", {
  "model": "claude-sonnet-4",
  "prompt": "Analyze the user's request and determine next steps",
  "temperature": 0.7,
  "max_tokens": 2000
})

// Appears in chain as:
Step N: [TOOL: llm/claude-sonnet-4]
  Prompt: "Analyze the user's request and determine next steps"
  Response: "The user wants a sales report. I should: 1) Query database..."
  Tokens: 1,247 (input: 850, output: 397)
  Cost: $0.0156
  Duration: 1,234ms
  Provider: anthropic
  Model: claude-sonnet-4-20250514
```

**Key Capabilities:**
- **Multi-Model Support**: Route to 100+ models via LiteLLM (Claude, GPT, Gemini, Llama, etc.)
- **Provider Fallbacks**: Automatic failover if primary provider is down
- **Cost Optimization**: Choose cheapest model for task complexity
- **Streaming**: Stream LLM responses token-by-token through tool interface
- **Caching**: Cache LLM responses to avoid redundant calls
- **Prompt Management**: Version and track prompts in reasoning chain

**Enterprise Features:**
- **Cost Attribution**: Every LLM call tagged with tenant/task/agent ID
- **Rate Limiting**: Per-tenant quotas on tokens/calls/cost
- **Model Governance**: Restrict which models can be used in production
- **Regional Compliance**: Route to region-specific endpoints (EU, US, etc.)
- **Audit Trails**: Full prompt and response logging for compliance

**Multi-Model Patterns:**
```python
# Use cheap model for simple tasks
if task.complexity == "low":
    tool.call("llm", {"model": "gpt-3.5-turbo", ...})

# Use powerful model for complex reasoning
elif task.complexity == "high":
    tool.call("llm", {"model": "claude-opus", ...})

# Use local model for sensitive data
elif task.has_pii:
    tool.call("llm", {"model": "local/llama-3-70b", ...})

# Consensus across multiple models
results = [
    tool.call("llm", {"model": "claude-opus", "prompt": prompt}),
    tool.call("llm", {"model": "gpt-4", "prompt": prompt}),
]
consensus = analyze_agreement(results)
```

#### External Tools
External API integrations (weather APIs, search engines, third-party services).

```
external_tool.call("weather_api", {
  location: "San Francisco",
  units: "celsius"
})

// Appears in chain as:
Step N: [TOOL: external/weather_api]
  Request: {location: "San Francisco", units: "celsius"}
  Response: {temperature: 18, conditions: "partly cloudy"}
  Duration: 234ms
```

#### Skills
Internal capabilities registered with the agent.

```
skill.call("document_processor", {
  document_url: "s3://bucket/doc.pdf",
  extract: ["tables", "key_points"]
})

// Appears in chain as:
Step N: [TOOL: skill/document_processor]
  Request: {document_url: "...", extract: [...]}
  Response: {tables: [...], key_points: [...]}
  Duration: 1,247ms
```

#### Sub-Agent Delegation
Delegating tasks to other agents via A2A protocol.

```
sub_agent.call("research_agent", {
  query: "Latest AI safety research papers",
  depth: "comprehensive"
})

// Appears in chain as:
Step N: [TOOL: sub_agent/research_agent]
  Delegated Task: task_id=xyz789
  Query: "Latest AI safety research papers"
  Status: COMPLETED
  Result: {papers: [...], summary: "..."}
  Duration: 8,432ms
  Sub-Chain: [collapsible - 23 steps]
```

#### Database Operations
Structured data access with full query visibility.

```
database.call("query", {
  sql: "SELECT * FROM customers WHERE region = ?",
  params: ["west"]
})

// Appears in chain as:
Step N: [TOOL: database/query]
  Query: SELECT * FROM customers WHERE region = 'west'
  Rows Returned: 1,247
  Duration: 89ms
```

#### File System Operations
File read/write operations with security controls.

```
file_system.call("read", {
  path: "/data/config.json",
  encoding: "utf-8"
})

// Appears in chain as:
Step N: [TOOL: file_system/read]
  Path: /data/config.json
  Size: 2.3KB
  Duration: 12ms
```

---

### 4. Visibility Control System

Configurable visibility at multiple levels.

**Visibility Levels**:
- `full`: Complete details including all parameters and results
- `summary`: Human-readable summary hiding implementation details
- `hidden`: Step exists in chain but not shown to user (still in audit log)

**Configuration Hierarchy** (most specific wins):
```
1. Per-step override (agent can mark specific steps)
2. Per-tool-type configuration
3. Per-agent configuration
4. Per-user-role configuration
5. Platform default (full visibility)
```

**Example Configuration**:
```yaml
visibility_config:
  default: full

  by_tool_type:
    database:
      default: summary
      summary_template: "Queried {table_name}, returned {row_count} rows"

    skill:
      default: hidden  # Internal implementation details

    sub_agent:
      default: full
      child_chain: summary  # Show sub-agent chain as summary

  by_role:
    end_user:
      thinking: summary
      tool_call: summary
      tool_result: summary

    developer:
      # Full visibility for all

    auditor:
      # Full visibility, including hidden steps
```

---

### 5. Streaming Reasoning Events

Real-time streaming of the reasoning chain as it unfolds.

**Event Types**:
```
ReasoningEvent (extends TaskEvent):
  type: "reasoning"
  task_id: UUID
  step: ReasoningStep
  chain_status: thinking | tool_calling | waiting | completed | failed
```

**SSE Stream Example**:
```
event: reasoning
data: {
  "type": "reasoning",
  "task_id": "abc123",
  "step": {
    "step_id": "step001",
    "type": "thinking",
    "thought": "I need to analyze the sales data first",
    "visibility": {"level": "full"}
  },
  "chain_status": "thinking"
}

event: reasoning
data: {
  "type": "reasoning",
  "task_id": "abc123",
  "step": {
    "step_id": "step002",
    "type": "tool_call",
    "tool_call": {
      "tool_type": "database",
      "tool_name": "query",
      "arguments": {"sql": "SELECT..."}
    },
    "visibility": {"level": "full"}
  },
  "chain_status": "tool_calling"
}

event: reasoning
data: {
  "type": "reasoning",
  "task_id": "abc123",
  "step": {
    "step_id": "step003",
    "type": "tool_result",
    "tool_result": {
      "correlation_id": "step002",
      "success": true,
      "result": {"row_count": 1247},
      "duration_ms": 89
    },
    "visibility": {"level": "summary", "summary": "Retrieved 1,247 sales records"}
  },
  "chain_status": "thinking"
}
```

---

## Success Criteria

### User Outcomes

#### For SDK Developers
- **Debug Time Reduction**: Developers can identify the root cause of agent errors in under 5 minutes by examining the reasoning chain
- **Full Visibility**: 100% of agent decisions and operations are visible in the reasoning chain
- **Self-Documenting Behavior**: The reasoning chain serves as documentation for why the agent behaved as it did

#### For End-Users
- **Trust Score**: Users report significantly higher trust in CoT agents vs. black-box agents (measurable via survey)
- **Anxiety Reduction**: Users never feel "left in the dark" during operations - they always know what the agent is doing
- **Verifiable Results**: Users can verify that the agent examined the right data and used appropriate logic

#### For Enterprise Administrators
- **Complete Audit Trail**: 100% of agent operations are logged with full reasoning context
- **Compliance Ready**: Reasoning chains can be exported in formats suitable for regulatory review
- **Policy Enforcement**: All tool calls pass through the unified interface where policies can be enforced

### Technical Outcomes

- **Unified Interface Adoption**: 100% of operations (external, skills, sub-agents, database) use the unified tool interface
- **Streaming Reliability**: 99%+ of reasoning event streams complete successfully
- **Chain Persistence**: Completed reasoning chains are persisted and retrievable for at least 90 days
- **Performance**: Reasoning chain overhead adds less than 50ms to task processing time

### Business Outcomes

- **Enterprise Adoption**: The transparency features directly address enterprise concerns about AI accountability
- **Differentiation**: CoT visibility becomes a key differentiator vs. competitors
- **Developer Productivity**: Reduced debugging time accelerates agent development

---

## Key Experiences

### The "Aha" Moment of Transparency

When a user first sees an agent's chain of thought, they should have a moment of revelation: "Oh, THAT'S why it did that!" This moment transforms the agent from a mysterious black box into an understandable collaborator.

**What makes this moment great**:
- The reasoning is presented in natural language, not technical jargon
- The connection between thinking and action is obvious
- Users feel empowered, not intimidated

### The Debugging Breakthrough

When a developer examines a reasoning chain to debug an issue, they should find the problem quickly and obviously. The chain should tell a story that makes the bug's location self-evident.

**What makes this moment great**:
- Steps are numbered and correlated (tool call -> result)
- Data flows are visible (what inputs led to what outputs)
- The failure point is highlighted, not buried

### The Trust-Building Moment

When an end-user sees the agent working on their request, with visible progress and reasoning, they should feel confident - not anxious. They should think "It's doing exactly what I'd do if I had time."

**What makes this moment great**:
- Progress is visible and meaningful (not just "processing...")
- Decisions are explained as they happen
- The user could stop and take over at any point if they wanted

### The Audit Trail Satisfaction

When a compliance officer reviews an agent's decision, they should be able to definitively answer "why did the AI make this decision?" and prove it to regulators.

**What makes this moment great**:
- Complete chain from input to output
- All data sources and operations documented
- Exportable in compliance-friendly formats

---

## Edge Cases and Considerations

### Long Reasoning Chains

**Scenario**: Agent reasoning chain exceeds hundreds of steps.

**Handling**:
- Implement progressive loading - show recent steps, lazy-load historical
- Provide chain summarization for long chains
- Allow filtering by step type, time range, or search
- Warn users when chains exceed typical lengths

### Parallel Tool Calls

**Scenario**: Agent calls multiple tools simultaneously.

**Handling**:
- Steps can have same step_number if truly parallel
- Correlation IDs link calls to results regardless of order
- UI shows parallel operations in split view
- Chain maintains causal ordering where dependencies exist

### Sensitive Data in Chains

**Scenario**: Tool calls or results contain sensitive data (PII, credentials, etc.).

**Handling**:
- Tool definitions include sensitivity classification
- Sensitive fields are redacted in user-facing views
- Audit logs maintain full data with appropriate access controls
- Data masking rules are configurable per tool and per tenant

### Sub-Agent Failures

**Scenario**: Delegated sub-agent fails or times out.

**Handling**:
- Parent chain shows sub-agent status at each poll/update
- Failure becomes a visible step with error details
- Parent agent can reason about the failure and decide next action
- Partial results from sub-agents are captured if available

### Circular Delegation

**Scenario**: Agent A delegates to Agent B, which tries to delegate back to Agent A.

**Handling**:
- Track delegation chain in tool call context
- Detect cycles and prevent with clear error
- Maximum delegation depth is configurable
- Cycle detection appears as reasoning step explaining the block

### Visibility Configuration Conflicts

**Scenario**: Tool wants `full` visibility, but user role only allows `summary`.

**Resolution Order**:
1. Security/compliance requirements (always hidden if required)
2. User role restrictions (most restrictive wins)
3. User preferences (within allowed levels)
4. Tool defaults
5. Platform defaults

### Chain Replay and Debugging

**Scenario**: Developer wants to replay a chain to reproduce a bug.

**Handling**:
- Chains can be exported and imported
- Tool call inputs are preserved for replay
- Results can be mocked for deterministic debugging
- "Time travel" debugging shows chain state at any step

---

## Open Questions

### Reasoning Quality Signals

- Should the chain include confidence scores for thinking steps?
- How do we measure and report reasoning quality?
- Should users see when the agent is "uncertain"?

### Caching and Deduplication

- Should identical tool calls be cached within a chain?
- How do we handle cache invalidation for time-sensitive data?
- Should caching be visible in the chain or transparent?

### Real-Time Intervention

- Can users intervene mid-chain to correct the agent's course?
- How do we handle user corrections - as new input or chain modification?
- Should there be "breakpoints" where human approval is required?

### Multi-Modal Reasoning

- How do we represent image analysis or audio processing in the chain?
- Should we display embedded previews of non-text artifacts?
- How do we summarize multi-modal tool results?

### Reasoning Chain Storage

- How long should chains be retained by default?
- Should chain storage be configurable per tenant?
- How do we handle chain storage for real-time vs. batch operations?

### Cross-Tenant Sub-Agent Delegation

- Can agents delegate to agents in different tenants?
- How do we handle visibility across tenant boundaries?
- What permissions are required for cross-tenant delegation?

### LLM Tool Specific Questions

- **Prompt Privacy**: Should prompts containing sensitive data be redacted in reasoning chains?
- **Model Selection Strategy**: Should agents auto-select models based on complexity, or require explicit configuration?
- **Cost Alerts**: Should agents stop execution if LLM costs exceed a threshold mid-task?
- **Streaming vs Batch**: When should LLM calls use streaming vs waiting for complete response?
- **Prompt Versioning**: How do we version and track prompt templates used in LLM calls?
- **Multi-Model Consensus**: How many models constitute valid consensus? What's the tie-breaking strategy?
- **Local Model Fallback**: Should agents automatically fallback to local models when cloud providers fail?

---

## Out of Scope (For Now)

### Chain Modification After Completion
Editing or redacting chain steps after the fact is not supported in v1. Chains are immutable records of what happened.

### Natural Language Chain Querying
"Show me all chains where the agent called the weather API" requires specialized tooling beyond v1 scope.

### Automated Reasoning Quality Assessment
ML-based evaluation of reasoning quality is a future enhancement.

### Chain-Based Learning
Using successful chains to improve agent behavior is not in v1 scope.

### Visual Chain Builder
A drag-and-drop interface for designing reasoning patterns is a premium platform feature for the future.

### Real-Time Collaborative Debugging
Multiple users viewing and annotating a chain in real-time is not in v1.

---

## Technical Constraints

### Integration with Existing Architecture

The CoT Agent must integrate with:
- **BaseAgent Interface**: Extends BaseAgent, implementing process_task to emit reasoning events
- **A2A Protocol**: Reasoning chains are A2A-compatible task artifacts
- **Existing Streaming**: Reasoning events flow through existing SSE infrastructure
- **Task Lifecycle**: Chain status maps to A2A task states
- **LiteLLM Integration**: Unified LLM tool wraps LiteLLM for multi-provider support

### LiteLLM Integration Requirements

**Core Dependencies:**
- `litellm >= 1.30.0` - Multi-provider LLM gateway
- Support for 100+ LLM providers (OpenAI, Anthropic, Azure, AWS Bedrock, local models)
- Streaming support for real-time token delivery
- Built-in retry logic and fallback handling

**Configuration:**
```python
llm_tool_config = {
    "default_model": "claude-sonnet-4",
    "fallback_models": ["gpt-4", "gpt-3.5-turbo"],
    "timeout_ms": 30000,
    "max_retries": 3,
    "cache_ttl_seconds": 3600,

    # Cost tracking
    "track_costs": True,
    "cost_per_tenant": True,

    # Rate limiting
    "rate_limits": {
        "calls_per_minute": 60,
        "tokens_per_minute": 100000,
        "cost_per_hour": 10.0  # USD
    },

    # Provider routing
    "provider_config": {
        "anthropic": {"api_key": "...", "api_base": "..."},
        "openai": {"api_key": "...", "organization": "..."},
        "azure": {"api_key": "...", "api_base": "...", "api_version": "..."},
        "local": {"api_base": "http://localhost:8000"}
    }
}
```

**Integration Points:**
- Tool interface registers LLM as first-class tool type
- LiteLLM handles all provider-specific logic (authentication, endpoints, formats)
- Cost tracking integrated with tenant billing system
- Streaming responses flow through SSE infrastructure
- Prompt/response logging for audit compliance

### Performance Requirements

- Reasoning chain overhead: < 50ms per task
- Event streaming latency: < 100ms from step completion to client delivery
- Chain retrieval: < 500ms for chains up to 1000 steps
- Concurrent chains: Support 1000+ active chains per agent instance

### Storage Requirements

- Average chain size: ~50KB (100 steps with typical tool results)
- Retention: Configurable, default 90 days
- Must support both in-memory (SDK standalone) and persistent (platform) storage

---

## Evolution Notes

### 2026-01-11 v1.1 (LLM-as-Tool Architecture)

**Major architectural decision**: LLM reasoning calls flow through the unified tool interface via LiteLLM.

**Why this change**:
After analysis and brainstorming, we determined that treating LLM calls as tools (rather than treating the LLM as "special") provides significant enterprise benefits:
1. **Complete cost visibility** - Every LLM call appears in reasoning chain with full token/cost attribution
2. **Multi-model flexibility** - Agents can strategically choose models (cheap for simple, powerful for complex, local for sensitive)
3. **Enterprise control plane** - Unified interface enables rate limiting, cost budgets, model governance across ALL operations
4. **Provider resilience** - LiteLLM provides automatic fallbacks and multi-provider support
5. **Simplicity** - One interface for everything, no special cases

**Trade-offs accepted**:
- Slight architectural complexity (agent calls LLM via tool interface)
- Minimal latency overhead (~10-15ms via LiteLLM, <1% of typical LLM call time)
- Benefits vastly outweigh costs at enterprise scale

**Updated sections**:
- Overview: Added LLM calls to unified interface description
- Core Design Philosophy: Added "LLM as a Tool" subsection with rationale
- Built-in Tool Types: Added LLM/LiteLLM as first tool type with full capabilities
- User Journeys: Updated Journey 1 to show LLM calls in reasoning chain
- Technical Constraints: Added LiteLLM integration requirements
- Open Questions: Added LLM-specific considerations

### 2026-01-11 v1.0 (Initial Draft)

Created specification based on user requirements:

**Key Design Decisions**:
1. **Tool calls as reasoning steps**: Rather than separating thinking and acting, all operations are unified as steps in the reasoning chain
2. **Unified interface for all tool types**: External APIs, skills, sub-agents, and database calls all use the same interface
3. **Visibility by default, configurable by design**: Full transparency as the default, with fine-grained controls for different audiences
4. **Dual audience focus**: Designed for both developers (debugging) and end-users (trust), not just one or the other

**Alignment with Product Vision**:
- Supports "agents build agents" through visible sub-agent delegation
- Embeds enterprise compliance through built-in audit trails
- Maintains simplicity through unified interface
- Prioritizes reliability through debuggable, transparent behavior

**Next Steps**:
1. Technical planning phase to define implementation architecture
2. Integration design with existing BaseAgent interface
3. Define tool registration and discovery mechanism (including LLM tool)
4. Design chain storage and retrieval system
5. LiteLLM integration for multi-provider LLM support

---

## References

**OmniForge Internal:**
- [OmniForge Product Vision](/Users/sohitkumar/code/omniforge/specs/product-vision.md)
- [Base Agent Interface Specification](/Users/sohitkumar/code/omniforge/specs/base-agent-interface-spec.md)
- [Base Agent Interface Technical Plan](/Users/sohitkumar/code/omniforge/specs/base-agent-interface-plan.md)
- [Core Chatbot Agent Specification](/Users/sohitkumar/code/omniforge/specs/core-chatbot-agent.md)

**External Standards & Libraries:**
- [A2A Protocol Specification v0.3](https://a2a-protocol.org/latest/specification/)
- [LiteLLM Documentation](https://docs.litellm.ai/) - Multi-provider LLM gateway
- [LiteLLM GitHub](https://github.com/BerriAI/litellm) - Open source LLM proxy
