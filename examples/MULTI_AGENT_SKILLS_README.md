# Multi-Agent Skills Orchestration - End-to-End Demo

This demo shows the complete flow of how agents can intelligently pick and use skills at runtime through multi-agent orchestration.

## What This Demo Shows

```
┌─────────────────────────────────────────────────────────────┐
│                        USER REQUEST                          │
│    "Search for market trends, analyze data, and generate     │
│              a comprehensive report"                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   COORDINATOR AGENT                          │
│  • Analyzes request                                          │
│  • Selects skills: [web-search, data-analysis, doc-gen]      │
│  • Chooses strategy: SEQUENTIAL (dependencies)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATION MANAGER                           │
│  • Creates agent cards for each skill                        │
│  • Delegates tasks using chosen strategy                    │
│  • Collects results from all agents                         │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  Research │  │   Data    │  │ Document  │
        │   Agent   │  │  Analyst  │  │  Generator│
        │           │  │   Agent   │  │   Agent   │
        └───────────┘  └───────────┘  └───────────┘
                │             │             │
                └─────────────┼─────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           RESPONSE SYNTHESIS                                 │
│  Combines all agent outputs into unified response           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        FINAL RESPONSE
```

## Quick Start

### Run the Demo

```bash
# Non-interactive mode (auto-runs all test cases)
python examples/multi_agent_skills_demo.py

# Interactive mode (press Enter between test cases)
# Edit the file and uncomment the input() line, comment out asyncio.sleep()
python examples/multi_agent_skills_demo.py
```

### Test Cases

The demo runs 4 test cases:

1. **Single Skill - Data Analysis**
   - Request: "Analyze the sales data from last quarter"
   - Skills Selected: Data Analysis
   - Strategy: PARALLEL

2. **Multiple Skills - Research + Document**
   - Request: "Research best practices for Python async programming and create a summary"
   - Skills Selected: Web Search, Document Generation, Code Review
   - Strategy: PARALLEL

3. **Single Skill - Code Review**
   - Request: "Review the authentication code and suggest security improvements"
   - Skills Selected: Code Review
   - Strategy: PARALLEL

4. **All Skills - Complex Request**
   - Request: "Search for market trends, analyze the data, review code, and generate report"
   - Skills Selected: All 4 skills
   - Strategy: SEQUENTIAL (because "analyze" + "generate" implies dependencies)

## Available Skills

### 1. Data Analysis
- **Agent:** `data-analyst-agent`
- **Keywords:** analyze, data, statistics, pattern, trend, csv, numbers
- **Capabilities:** Calculate stats, identify patterns, detect anomalies

### 2. Web Search & Research
- **Agent:** `research-agent`
- **Keywords:** search, web, research, find, lookup, google, information
- **Capabilities:** Search web, gather info, summarize findings

### 3. Document Generation
- **Agent:** `document-agent`
- **Keywords:** generate, create, document, report, summary, write, draft
- **Capabilities:** Create documents, reports, presentations

### 4. Code Review
- **Agent:** `code-reviewer-agent`
- **Keywords:** code, review, bug, improve, refactor, python, javascript
- **Capabilities:** Review code, suggest improvements, identify bugs

## How It Works

### 1. Skill Selection (Coordinator Agent)

```python
class CoordinatorAgent:
    def select_skills(self, message: str) -> list[Skill]:
        """Analyze message and select appropriate skills.

        In production:
        - Use LLM-based intent classification
        - Semantic similarity search
        - Skill capability matching

        In demo: Simple keyword matching
        """
        message_lower = message.lower()
        selected_skills = []

        for skill in AVAILABLE_SKILLS:
            if any(keyword in message_lower for keyword in skill.keywords):
                selected_skills.append(skill)

        return selected_skills or [default_skill]
```

### 2. Strategy Selection

```python
# Determine delegation strategy
strategy = DelegationStrategy.PARALLEL  # Default: run all concurrently

if "analyze" in message.lower() and "generate" in message.lower():
    # Sequential: generate needs analyze results
    strategy = DelegationStrategy.SEQUENTIAL
```

### 3. Agent Delegation

```python
# Create agent cards for selected skills
target_agent_cards = [create_agent_card(skill) for skill in selected_skills]

# Delegate using OrchestrationManager
results = await orchestration_manager.delegate_to_agents(
    thread_id=thread_id,
    tenant_id=tenant_id,
    user_id=user_id,
    message=message,
    target_agent_cards=target_agent_cards,
    strategy=strategy,
    timeout_ms=30000
)
```

### 4. Response Synthesis

```python
# Synthesize all agent responses
final_response = orchestration_manager.synthesize_responses(results)

# Single successful result → return directly
# Multiple results → format as "From agent-id: response"
# All failed → return error message
```

## Delegation Strategies

### PARALLEL (Default)
- Executes all agents simultaneously
- Best for: Independent tasks, fastest total time
- Example: "Search web AND analyze data" (both independent)

### SEQUENTIAL
- Executes agents one at a time, in order
- Best for: Dependent tasks where later agents need earlier results
- Example: "Analyze data THEN generate report" (report needs analysis)

### FIRST_SUCCESS
- Executes all agents simultaneously, returns first successful response
- Best for: Redundant agents, fallback scenarios
- Example: Multiple research agents, need answer ASAP

## Architecture Components

### 1. OrchestrationManager
- **File:** `src/omniforge/orchestration/manager.py`
- **Purpose:** Coordinates multi-agent delegation
- **Methods:**
  - `delegate_to_agents()` - Delegate to multiple agents
  - `synthesize_responses()` - Combine results

### 2. A2AClient
- **File:** `src/omniforge/orchestration/client.py`
- **Purpose:** HTTP/SSE communication between agents
- **Protocol:** Agent-to-Agent (A2A) protocol

### 3. AgentCard
- **File:** `src/omniforge/agents/models.py`
- **Purpose:** Agent identity, capabilities, and skills
- **Contains:** Identity, skills, service endpoint, security config

## Extending This Demo

### Add a New Skill

1. **Define the skill:**
   ```python
   new_skill = Skill(
       id="translation",
       name="Language Translation",
       description="Translate text between languages",
       keywords=["translate", "language", "español", "français"],
       agent_id="translator-agent"
   )
   AVAILABLE_SKILLS.append(new_skill)
   ```

2. **Create the agent:**
   ```python
   class TranslatorAgent(MockSkillAgent):
       async def execute(self, message: str) -> str:
           # Your translation logic here
           return f"Translated: {message}"
   ```

3. **Register the agent:**
   ```python
   skill_agents["translator-agent"] = TranslatorAgent(new_skill)
   ```

### Make Agents Real (Not Mocked)

Replace `MockSkillAgent` with actual implementations:

```python
class RealDataAnalystAgent:
    async def execute(self, message: str) -> str:
        # Parse task from message
        task = parse_task(message)

        # Load actual data
        data = load_data(task.dataset_path)

        # Perform real analysis
        stats = calculate_statistics(data)
        trends = detect_trends(data)
        anomalies = find_anomalies(data)

        # Format results
        return format_analysis_report(stats, trends, anomalies)
```

### Add LLM-Based Skill Selection

Replace keyword matching with LLM:

```python
async def select_skills_with_llm(self, message: str) -> list[Skill]:
    """Use LLM to intelligently select skills."""
    prompt = f"""Given this user request: "{message}"

    Available skills:
    {format_skills_for_llm(AVAILABLE_SKILLS)}

    Which skills are needed? Return as JSON array.
    """

    response = await llm.complete(prompt)
    selected_skill_ids = parse_llm_response(response)

    return [skill for skill in AVAILABLE_SKILLS
            if skill.id in selected_skill_ids]
```

### Deploy as HTTP Services

Convert mock agents to HTTP endpoints:

```python
# agents/data_analyst_service.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/v1/tasks")
async def handle_task(request: TaskCreateRequest):
    """HTTP endpoint for data analysis agent."""
    # Execute data analysis
    result = await analyze_data(request.message)

    # Stream results back
    return StreamingResponse(
        stream_results(result),
        media_type="text/event-stream"
    )
```

Then update agent cards with real endpoints:

```python
agent_card = AgentCard(
    # ...
    service_endpoint="http://data-analyst.prod.com:8000",
    security=SecurityConfig(
        auth_scheme=AuthScheme.BEARER,
        require_https=True
    )
)
```

## Production Considerations

### 1. Authentication
```python
# Add security to agent cards
security = SecurityConfig(
    auth_scheme=AuthScheme.BEARER,
    require_https=True
)

# A2AClient will include auth headers automatically
```

### 2. Error Handling
```python
results = await orchestration_manager.delegate_to_agents(...)

# Check for failures
failed_agents = [r for r in results if not r.success]
if failed_agents:
    logger.error(f"{len(failed_agents)} agents failed")
    # Handle gracefully - maybe retry or use fallback
```

### 3. Timeout Management
```python
# Increase timeout for long-running tasks
results = await orchestration_manager.delegate_to_agents(
    # ...
    timeout_ms=120000  # 2 minutes
)
```

### 4. RBAC Permissions
```python
from omniforge.security.rbac import Permission, has_permission

# Check permissions before delegating
if not await has_permission(user_id, tenant_id, Permission.ORCHESTRATION_DELEGATE):
    raise PermissionError("User cannot delegate tasks")
```

### 5. Tenant Isolation
```python
from omniforge.orchestration.thread import ThreadManager

thread_manager = ThreadManager(conversation_repo)

# Always validate thread belongs to tenant
is_valid = await thread_manager.validate_thread(
    thread_id=thread_id,
    tenant_id=tenant_id
)
if not is_valid:
    raise PermissionError("Invalid thread access")
```

## Related Documentation

- **Orchestration Usage Guide:** `docs/orchestration-usage-guide.md`
- **Technical Plan:** `specs/technical-plan-orchestrator-handoff.md`
- **Product Spec:** `specs/orchestrator-handoff-patterns-spec.md`
- **API Tests:** `tests/orchestration/`

## Summary

This demo demonstrates a **complete multi-agent system** where:

✅ **Coordinator agent** analyzes requests and selects skills
✅ **Multiple specialized agents** execute their skills in parallel or sequentially
✅ **OrchestrationManager** handles all delegation and coordination
✅ **Responses are synthesized** into a unified final answer
✅ **System scales** to any number of skills and agents

The architecture is production-ready with:
- Multi-tenancy support
- RBAC permission checks
- Timeout management
- Error handling
- Response synthesis
- Both parallel and sequential execution

**Next step:** Replace mock agents with real implementations that make actual API calls, process data, or invoke LLMs!
