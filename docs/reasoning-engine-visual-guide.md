# ReasoningEngine Visual Guide

Visual diagrams showing how the ReasoningEngine works.

## Complete Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
│                  "What is the weather in NYC?"                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT START                               │
│  • Creates ReasoningChain                                        │
│  • Initializes ReasoningEngine                                   │
│  • Gets ToolExecutor with tool registry                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 0: THINKING                                                 │
│ engine.add_thinking("User wants weather for NYC")               │
│                                                                  │
│ Chain State:                                                     │
│  [Step 0: THINKING - "User wants weather for NYC"]              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT DECIDES: Need to call weather API                         │
│ await engine.call_tool("weather", {"city": "NYC"})              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ REASONINGENGINE.call_tool()                                     │
│  1. Creates ToolCallContext                                      │
│     - correlation_id: "corr-abc-123"                             │
│     - task_id, agent_id, tenant_id                               │
│  2. Delegates to ToolExecutor                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ TOOLEXECUTOR.execute()                                          │
│                                                                  │
│ Step 1: GET TOOL FROM REGISTRY                                   │
│   tool = registry.get("weather")  → WeatherTool instance         │
│                                                                  │
│ Step 2: VALIDATE ARGUMENTS                                       │
│   tool.validate_arguments({"city": "NYC"})  → OK                 │
│                                                                  │
│ Step 3: CHECK RATE LIMITS (if configured)                        │
│   rate_limiter.check_limit(tenant_id, "weather")  → OK           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: TOOL_CALL                                                │
│ Executor adds step to chain:                                     │
│   step = ReasoningStep(                                          │
│       type=StepType.TOOL_CALL,                                   │
│       tool_call=ToolCallInfo(                                    │
│           tool_name="weather",                                   │
│           parameters={"city": "NYC"},                            │
│           correlation_id="corr-abc-123"                          │
│       )                                                          │
│   )                                                              │
│   chain.add_step(step)                                           │
│                                                                  │
│ Chain State:                                                     │
│  [Step 0: THINKING]                                              │
│  [Step 1: TOOL_CALL - weather(city="NYC")]                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTE TOOL WITH RETRIES                                        │
│                                                                  │
│ Attempt 1:                                                       │
│   result = await tool.execute(context, arguments)               │
│   → Calls weather API                                            │
│   → Returns ToolResult(success=True, result={...})               │
│                                                                  │
│ [If failed, would retry with exponential backoff]                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ TRACK COST (if configured)                                       │
│   cost_tracker.track_cost(                                       │
│       task_id="task-123",                                        │
│       tool_name="weather",                                       │
│       cost_usd=0.001,                                            │
│       tokens_used=0                                              │
│   )                                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: TOOL_RESULT                                              │
│ Executor adds result step to chain:                              │
│   step = ReasoningStep(                                          │
│       type=StepType.TOOL_RESULT,                                 │
│       tool_result=ToolResultInfo(                                │
│           correlation_id="corr-abc-123",  ← Links to Step 1      │
│           success=True,                                          │
│           result={"temp": 72, "condition": "sunny"}              │
│       ),                                                         │
│       tokens_used=0,                                             │
│       cost=0.001                                                 │
│   )                                                              │
│   chain.add_step(step)                                           │
│                                                                  │
│ Chain State:                                                     │
│  [Step 0: THINKING]                                              │
│  [Step 1: TOOL_CALL - weather(city="NYC")]                      │
│  [Step 2: TOOL_RESULT - success=True, temp=72]                  │
│                                                                  │
│ Metrics Updated:                                                 │
│  • total_steps: 3                                                │
│  • tool_calls: 1                                                 │
│  • total_cost: 0.001                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ RETURN TO REASONINGENGINE                                        │
│  • Finds last 2 steps: call_step (Step 1), result_step (Step 2) │
│  • Wraps in ToolCallResult                                       │
│  • Returns to agent                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT PROCESSES RESULT                                           │
│   result = ToolCallResult(...)                                  │
│   if result.success:                                             │
│       weather = result.value                                     │
│       # {"temp": 72, "condition": "sunny"}                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: SYNTHESIS                                                │
│ engine.add_synthesis(                                            │
│     conclusion="The weather in NYC is 72°F and sunny",          │
│     sources=[result.step_id]  # References Step 2                │
│ )                                                                │
│                                                                  │
│ Final Chain State:                                               │
│  [Step 0: THINKING - "User wants weather for NYC"]              │
│  [Step 1: TOOL_CALL - weather(city="NYC")]                      │
│  [Step 2: TOOL_RESULT - {temp: 72, condition: "sunny"}]         │
│  [Step 3: SYNTHESIS - "The weather in NYC is 72°F and sunny"]   │
│                                                                  │
│ Final Metrics:                                                   │
│  • total_steps: 4                                                │
│  • llm_calls: 1  (synthesis counts as LLM call)                  │
│  • tool_calls: 1                                                 │
│  • total_cost: 0.001                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT RETURNS ANSWER                                             │
│ return "The weather in NYC is 72°F and sunny"                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ USER RECEIVES RESPONSE                                           │
│ "The weather in NYC is 72°F and sunny"                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## LLM Call Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ AGENT: engine.call_llm(prompt="What is 2+2?")                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ REASONINGENGINE.call_llm()                                      │
│  • Converts prompt to messages format                            │
│    messages = [{"role": "user", "content": "What is 2+2?"}]     │
│  • Builds arguments for LLM tool                                 │
│    arguments = {                                                 │
│        "model": "claude-sonnet-4",                               │
│        "messages": messages,                                     │
│        "temperature": 0.7                                        │
│    }                                                             │
│  • Delegates to call_tool("llm", arguments)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ REASONINGENGINE.call_tool("llm", {...})                         │
│  • Creates ToolCallContext                                       │
│  • Calls executor.execute(...)                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ TOOLEXECUTOR.execute()                                          │
│  • Gets LLMTool from registry                                    │
│  • Adds TOOL_CALL step (Step N)                                 │
│  • Executes LLMTool                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LLMTOOL.execute()                                               │
│  1. Check approved models                                        │
│  2. Estimate cost                                                │
│  3. Check budget                                                 │
│  4. Call litellm.acompletion(                                    │
│        model="claude-sonnet-4",                                  │
│        messages=[...]                                            │
│     )                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LITELLM                                                          │
│  • Detects provider (Anthropic)                                  │
│  • Uses ANTHROPIC_API_KEY                                        │
│  • Calls Anthropic API                                           │
│  • Returns unified response                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LLMTOOL.execute() (continued)                                   │
│  5. Extract content from response                                │
│     content = response.choices[0].message.content                │
│  6. Calculate actual cost                                        │
│     cost = calculate_cost_from_response(response)                │
│  7. Return ToolResult(                                           │
│        success=True,                                             │
│        result={"content": "2+2 equals 4", ...},                  │
│        tokens_used=50,                                           │
│        cost_usd=0.00001                                          │
│    )                                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ TOOLEXECUTOR.execute() (continued)                              │
│  • Adds TOOL_RESULT step (Step N+1)                             │
│  • Returns ToolResult to ReasoningEngine                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ REASONINGENGINE.call_tool() (continued)                         │
│  • Wraps as ToolCallResult                                       │
│  • Returns to agent                                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT GETS RESULT                                                │
│   result.value["content"]  → "2+2 equals 4"                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## ReAct Loop Visualization

The ReAct (Reasoning + Acting) pattern in autonomous agents:

```
┌─────────────────────────────────────────────────────────────────┐
│                    START: User gives task                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  ITERATION 1         │
                  └──────────┬───────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌─────────┐            ┌──────────┐            ┌──────────┐
│THINKING │            │   LLM    │            │  PARSE   │
│  Step   │   ────►    │   CALL   │   ────►    │ RESPONSE │
└─────────┘            └──────────┘            └─────┬────┘
                                                     │
                                        ┌────────────┴──────────┐
                                        │                       │
                                        ▼                       ▼
                                  ┌──────────┐          ┌─────────────┐
                                  │  FINAL   │          │   ACTION    │
                                  │ ANSWER?  │          │  DETECTED   │
                                  └────┬─────┘          └──────┬──────┘
                                       │                       │
                                 YES   │                       │
                                       │                       ▼
                                       │                 ┌──────────┐
                                       │                 │ EXECUTE  │
                                       │                 │   TOOL   │
                                       │                 └─────┬────┘
                                       │                       │
                                       │                       ▼
                                       │                 ┌──────────┐
                                       │                 │  OBSERVE │
                                       │                 │  RESULT  │
                                       │                 └─────┬────┘
                                       │                       │
                                       │         ┌─────────────┘
                                       │         │
                                       │         ▼
                                       │   ┌──────────────┐
                                       │   │  ITERATION 2 │
                                       │   └──────────────┘
                                       │         │
                                       │        ...
                                       │
                                       ▼
                             ┌──────────────────┐
                             │  RETURN ANSWER   │
                             └──────────────────┘
```

**Example Iteration**:

```
Iteration 1:
  Thought: "I need to search for weather data"
  Action: weather_api
  Action Input: {"city": "NYC"}
  Observation: {"temp": 72, "condition": "sunny"}

Iteration 2:
  Thought: "I have the weather data, I can answer"
  Final Answer: "The weather in NYC is 72°F and sunny"
```

---

## Chain Building Process

```
TIME →

Step 0:  [THINKING]
         "User wants to analyze sales data"
         ↓

Step 1:  [TOOL_CALL]
         tool: "database"
         params: {query: "SELECT..."}
         correlation_id: "corr-1"
         ↓

Step 2:  [TOOL_RESULT]
         correlation_id: "corr-1" ← Links to Step 1
         success: true
         result: {rows: [...]}
         tokens: 0
         cost: 0.001
         ↓

Step 3:  [THINKING]
         "Data retrieved, now analyzing trends"
         ↓

Step 4:  [TOOL_CALL]
         tool: "llm"
         params: {prompt: "Analyze trends..."}
         correlation_id: "corr-2"
         ↓

Step 5:  [TOOL_RESULT]
         correlation_id: "corr-2" ← Links to Step 4
         success: true
         result: {content: "Sales increasing..."}
         tokens: 200
         cost: 0.0004
         ↓

Step 6:  [SYNTHESIS]
         "Sales are increasing by 15% month-over-month"
         sources: [step-2-uuid, step-5-uuid]

═══════════════════════════════════════════════════════════

CHAIN METRICS (Auto-updated):
  total_steps:  7
  llm_calls:    2  (Step 4 LLM call + Step 6 synthesis)
  tool_calls:   2  (Step 1 + Step 4)
  total_tokens: 200
  total_cost:   $0.0014
```

---

## Data Flow Diagram

```
┌──────────────┐
│    Agent     │
│              │
└──────┬───────┘
       │ creates
       ▼
┌──────────────────────┐
│  ReasoningEngine     │
│  ┌────────────────┐  │
│  │ ReasoningChain │  │
│  │  steps: []     │  │
│  │  metrics: {}   │  │
│  └────────────────┘  │
│                      │
│  ┌────────────────┐  │
│  │ ToolExecutor   │  │
│  │   registry     │  │
│  └────────────────┘  │
└──────────┬───────────┘
           │ uses
           ▼
┌────────────────────────┐
│     ToolRegistry       │
│  ┌──────────────────┐  │
│  │ "llm" → LLMTool  │  │
│  │ "db"  → DBTool   │  │
│  │ ...              │  │
│  └──────────────────┘  │
└────────────────────────┘
```

---

## Step Correlation Diagram

Shows how tool calls link to results:

```
TOOL_CALL Step                    TOOL_RESULT Step
┌─────────────────────┐          ┌─────────────────────┐
│ step_number: 5      │          │ step_number: 6      │
│ type: TOOL_CALL     │          │ type: TOOL_RESULT   │
│ tool_call:          │          │ tool_result:        │
│   tool_name: "db"   │          │   correlation_id: ──┼──┐
│   correlation_id: ──┼──────────┼─→ "corr-xyz"        │  │
│   "corr-xyz"        │          │   success: true     │  │
└─────────────────────┘          │   result: {...}     │  │
                                 └─────────────────────┘  │
                                                          │
  This allows finding the result for a specific call: ────┘
    chain.get_step_by_correlation_id("corr-xyz")
```

---

## Cost Tracking Flow

```
┌─────────────────────────────────────────────────────────────┐
│ BEFORE TOOL EXECUTION                                        │
│  • estimate_cost_before_call(model, messages, max_tokens)   │
│  • Check against budget limit                                │
│  • Reject if exceeds budget                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Execute tool
                     │
┌────────────────────┴────────────────────────────────────────┐
│ AFTER TOOL EXECUTION                                         │
│  • calculate_cost_from_response(response, model)             │
│  • Update step.cost and step.tokens_used                     │
│  • Add to chain.metrics.total_cost                           │
│  • Track via cost_tracker (if configured)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Visibility Levels

```
┌─────────────────────────────────────────────────────────────┐
│                     VISIBILITY LEVELS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FULL        ████████████████  Everyone can see             │
│              (Default)                                       │
│                                                              │
│  EXTERNAL    ████████████      External users can see       │
│              (Hide sensitive details)                        │
│                                                              │
│  INTERNAL    ████████          Only internal users          │
│              (PII, sensitive data)                           │
│                                                              │
│  DEBUG       ████              Debug mode only              │
│              (Verbose logs)                                  │
│                                                              │
│  HIDDEN      ██                Never shown                   │
│              (Secrets, credentials)                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Example:
```python
# Public LLM call
await engine.call_llm(
    prompt="Public question",
    visibility=VisibilityLevel.FULL
)

# Internal database query
await engine.call_tool(
    "database",
    {"query": "SELECT * FROM users WHERE ssn=..."},
    visibility=VisibilityLevel.INTERNAL  # Hide from external users
)
```

---

## Summary

The ReasoningEngine provides:

1. **Structured Recording**: Every thought, action, and result is captured
2. **Automatic Correlation**: Tool calls linked to results via correlation IDs
3. **Cost Tracking**: Token usage and costs tracked at every step
4. **Enterprise Features**: Rate limiting, visibility control, multi-tenancy
5. **Streaming Support**: Steps can be streamed in real-time
6. **Audit Trail**: Complete history for debugging and compliance

All of this happens **automatically** as agents use the high-level API!
