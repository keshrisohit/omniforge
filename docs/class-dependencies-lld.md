# Low-Level Design (LLD) - Class Dependencies

Comprehensive class diagram showing dependencies, relationships, and architectural issues.

## Core Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ API Routes   │  │ CLI Commands │  │ Chat Service │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                     APPLICATION LAYER                            │
│                             ▼                                     │
│  ┌──────────────────────────────────────────────────────┐       │
│  │               Agent Hierarchy                         │       │
│  │  ┌─────────────┐                                     │       │
│  │  │  BaseAgent  │ (abstract)                          │       │
│  │  └──────┬──────┘                                     │       │
│  │         │                                             │       │
│  │         ├─────────┬────────────┬──────────┐          │       │
│  │         ▼         ▼            ▼          ▼          │       │
│  │   ┌─────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐  │       │
│  │   │CoTAgent │ │ Simple │ │Autonomous│ │Custom   │  │       │
│  │   │         │ │Agent   │ │CoTAgent  │ │Agents   │  │       │
│  │   └────┬────┘ └────────┘ └─────┬────┘ └─────────┘  │       │
│  └────────┼──────────────────────┼─────────────────────┘       │
│           │                      │                              │
│           │ creates & uses       │ creates & uses               │
│           ▼                      ▼                              │
│  ┌──────────────────────────────────────────┐                  │
│  │       ReasoningEngine                     │                  │
│  │  ┌────────────────┐  ┌────────────────┐  │                  │
│  │  │ReasoningChain  │  │ToolCallResult  │  │                  │
│  │  └────────────────┘  └────────────────┘  │                  │
│  └───────────┬──────────────────────────────┘                  │
└──────────────┼─────────────────────────────────────────────────┘
               │ delegates to
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     TOOL EXECUTION LAYER                          │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              ToolExecutor                             │        │
│  │  • Manages tool execution                            │        │
│  │  • Handles retries, timeouts                         │        │
│  │  • Records steps in ReasoningChain  ⚠️ COUPLING     │        │
│  │  • Skill activation/deactivation    ⚠️ COUPLING     │        │
│  └───────────┬──────────────────────────────────────────┘        │
│              │ uses                                               │
│              ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐        │
│  │           ToolRegistry (Singleton)                    │        │
│  │  • Stores tool instances                             │        │
│  │  • Thread-safe registration                          │        │
│  └───────────┬──────────────────────────────────────────┘        │
│              │ provides                                           │
│              ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐        │
│  │               Tool Implementations                    │        │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │        │
│  │  │ LLMTool  │  │ DBTool   │  │FileSysTool│  ...    │        │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘          │        │
│  └───────┼─────────────┼─────────────┼─────────────────┘        │
│          │ extends     │ extends     │ extends                  │
│          └─────────────┴─────────────┴──────────────┐           │
│                                                      ▼           │
│  ┌──────────────────────────────────────────────────────┐       │
│  │             BaseTool (abstract)                       │       │
│  │  • definition: ToolDefinition                        │       │
│  │  • execute(context, args) → ToolResult              │       │
│  │  • validate_arguments()                              │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      DOMAIN MODELS LAYER                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  ReasoningChain │  │ ToolDefinition  │  │  ToolResult     │ │
│  │  ReasoningStep  │  │ ToolParameter   │  │  ToolContext    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │  Task           │  │  AgentIdentity  │                      │
│  │  TaskMessage    │  │  AgentCard      │                      │
│  └─────────────────┘  └─────────────────┘                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Detailed Class Dependencies

### 1. Agent Layer

```
BaseAgent (abstract)
├── identity: AgentIdentity                      [composition]
├── capabilities: AgentCapabilities              [composition]
├── skills: List[AgentSkill]                     [composition]
├── process_task(Task) → AsyncIterator[Event]    [abstract method]
└── get_agent_card() → AgentCard                 [method]

CoTAgent extends BaseAgent
├── _tool_registry: ToolRegistry                 [dependency]
├── reason(Task, ReasoningEngine) → str          [abstract method]
├── process_task(Task) → AsyncIterator[Event]    [override]
│   └── creates ReasoningEngine                   [factory]
│   └── creates ReasoningChain                    [factory]
│   └── creates ToolExecutor                      [factory]
└── _build_engine(chain, executor) → Engine      [private]

AutonomousCoTAgent extends CoTAgent
├── _max_iterations: int
├── _reasoning_model: str
├── _temperature: float
├── _parser: ReActParser                         [composition]
└── reason(Task, ReasoningEngine) → str          [override]
```

**Dependencies**:
- `agents/cot/agent.py` → `agents/base.py`
- `agents/cot/agent.py` → `agents/cot/chain.py`
- `agents/cot/agent.py` → `agents/cot/engine.py`
- `agents/cot/agent.py` → `tools/registry.py`
- `agents/cot/autonomous.py` → `agents/cot/agent.py`
- `agents/cot/autonomous.py` → `agents/cot/parser.py`

### 2. ReasoningEngine & Chain Layer

```
ReasoningEngine
├── _chain: ReasoningChain                       [composition]
├── _executor: ToolExecutor                      [dependency injection]
├── _task: dict[str, Any]                        [data]
├── _default_llm_model: str                      [config]
│
├── add_thinking(thought, confidence)            [method]
├── add_synthesis(conclusion, sources)           [method]
├── call_llm(...) → ToolCallResult              [method]
├── call_tool(...) → ToolCallResult             [method]
└── get_available_tools() → List[ToolDef]       [method]

ToolCallResult
├── result: ToolResult                           [composition]
├── call_step: ReasoningStep                     [reference]
├── result_step: ReasoningStep                   [reference]
└── [convenience properties]                     [computed]

ReasoningChain (Pydantic model)
├── id: UUID
├── task_id: str
├── agent_id: str
├── status: ChainStatus                          [enum]
├── steps: List[ReasoningStep]                   [composition]
├── metrics: ChainMetrics                        [composition]
├── add_step(step: ReasoningStep)               [method]
└── _update_metrics(step)                        [private]

ReasoningStep (Pydantic model)
├── id: UUID
├── step_number: int
├── type: StepType                               [enum]
├── timestamp: datetime
├── visibility: VisibilityConfig
├── thinking: Optional[ThinkingInfo]             [union type]
├── tool_call: Optional[ToolCallInfo]            [union type]
├── tool_result: Optional[ToolResultInfo]        [union type]
├── synthesis: Optional[SynthesisInfo]           [union type]
├── tokens_used: int
└── cost: float
```

**Dependencies**:
- `agents/cot/engine.py` → `agents/cot/chain.py` ✅ **OK (same module)**
- `agents/cot/engine.py` → `tools/base.py` ✅ **OK**
- `agents/cot/chain.py` → `tools/types.py` ✅ **OK (types only)**

### 3. Tool Execution Layer

```
ToolExecutor
├── _registry: ToolRegistry                      [dependency injection]
├── _rate_limiter: Optional[RateLimiter]         [dependency injection]
├── _cost_tracker: Optional[CostTracker]         [dependency injection]
├── _skill_stack: List[Skill]                    [state] ⚠️
├── _skill_contexts: Dict[str, SkillContext]     [state] ⚠️
│
├── execute(tool_name, args, context, chain)     [method] ⚠️
├── _execute_with_retries(tool, args, context)   [private]
├── activate_skill(skill: Skill)                 [method] ⚠️
└── deactivate_skill(skill_name: str)            [method] ⚠️

ToolRegistry (Singleton)
├── _tools: Dict[str, BaseTool]                  [state]
├── _lock: threading.Lock                        [thread-safety]
│
├── register(tool: BaseTool)                     [method]
├── get(name: str) → BaseTool                    [method]
├── list_tools() → List[str]                     [method]
└── get_definition(name) → ToolDefinition        [method]

BaseTool (abstract)
├── definition: ToolDefinition                   [abstract property]
├── execute(context, args) → ToolResult          [abstract method]
└── validate_arguments(args)                     [method]

LLMTool extends BaseTool
├── _config: LLMConfig                           [composition]
├── _setup_litellm()                             [private]
├── definition → ToolDefinition                  [property]
├── execute(context, args) → ToolResult          [override]
└── execute_streaming(...) → AsyncIterator       [method]
```

**Dependencies** (⚠️ = Issues):
- `tools/executor.py` → `tools/registry.py` ✅ **OK**
- `tools/executor.py` → `tools/base.py` ✅ **OK**
- `tools/executor.py` → `agents/cot/chain.py` ⚠️ **CROSS-BOUNDARY**
- `tools/executor.py` → `skills/models.py` ⚠️ **TIGHT COUPLING**
- `tools/executor.py` → `skills/context.py` ⚠️ **TIGHT COUPLING**
- `tools/executor.py` → `skills/errors.py` ⚠️ **TIGHT COUPLING**

### 4. LLM Layer

```
LLMConfig (Pydantic model)
├── default_model: str
├── fallback_models: List[str]
├── timeout_ms: int
├── max_retries: int
├── cache_enabled: bool
├── approved_models: Optional[List[str]]
└── providers: Dict[str, ProviderConfig]

ProviderConfig (Pydantic model)
├── api_key: Optional[str]
├── api_base: Optional[str]
├── api_version: Optional[str]
└── organization: Optional[str]
```

**Dependencies**:
- `llm/config.py` → `pydantic` ✅ **OK**
- `llm/cost.py` → (no internal deps) ✅ **OK**
- `tools/builtin/llm.py` → `llm/config.py` ✅ **OK**
- `tools/builtin/llm.py` → `llm/cost.py` ✅ **OK**

---

## Identified Issues & Problems

### 🔴 CRITICAL: Cross-Boundary Dependency

**Issue**: `ToolExecutor` imports from `agents/cot/chain.py`

```python
# tools/executor.py
from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    ToolCallInfo,
    ToolResultInfo,
    VisibilityConfig,
)
```

**Problem**:
- Tools layer depends on Agents layer
- Violates dependency inversion principle
- Makes tools tightly coupled to CoT agents
- Prevents using tools without agent context

**Impact**:
```
tools/ (low-level)
  ↓ imports from
agents/ (high-level)
```

This creates a **circular conceptual dependency**:
- Agents depend on Tools (to execute)
- Tools depend on Agents (for chain recording)

### 🟡 MEDIUM: Skills Coupling in ToolExecutor

**Issue**: `ToolExecutor` tightly coupled to Skills module

```python
# tools/executor.py
from omniforge.skills.context import SkillContext
from omniforge.skills.errors import SkillActivationError, SkillError
from omniforge.skills.models import Skill

class ToolExecutor:
    def __init__(...):
        self._skill_stack: List[Skill] = []
        self._skill_contexts: Dict[str, SkillContext] = {}

    def activate_skill(self, skill: Skill) -> None: ...
    def deactivate_skill(self, skill_name: str) -> None: ...
```

**Problem**:
- Skill management mixed with tool execution
- Single Responsibility Principle violation
- ToolExecutor has two responsibilities:
  1. Execute tools (primary)
  2. Manage skills (secondary)

### 🟡 MEDIUM: Singleton Pattern Duplication

**Issue**: Multiple singleton registries

```python
# tools/registry.py
_default_registry: Optional[ToolRegistry] = None

def get_default_registry() -> ToolRegistry:
    global _default_registry
    ...

# tools/setup.py
_default_registry: Optional[ToolRegistry] = None

def get_default_tool_registry() -> ToolRegistry:
    global _default_registry
    ...
```

**Problem**:
- Two different singletons for tool registry
- Confusing API: which one to use?
- Inconsistent patterns

### 🟢 MINOR: TYPE_CHECKING Pattern Underused

**Good**: Some files use `TYPE_CHECKING` to avoid circular imports:

```python
# agents/cot/engine.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omniforge.tools.executor import ToolExecutor
```

**Problem**: Not consistently applied everywhere

---

## Dependency Graph

### Current Dependencies (Problematic)

```
┌─────────────┐
│   agents/   │
│     cot/    │
│   chain.py  │
└──────┬──────┘
       │
       │ imported by (BAD!)
       │
       ▼
┌─────────────┐
│   tools/    │
│ executor.py │
└─────────────┘
```

### Current Flow (What Happens)

```
1. Agent creates ReasoningEngine
        ↓
2. Agent creates ToolExecutor
        ↓
3. Agent calls engine.call_tool()
        ↓
4. Engine delegates to executor.execute()
        ↓
5. Executor adds TOOL_CALL step to chain ← Uses ReasoningStep (from agents!)
        ↓
6. Executor executes tool
        ↓
7. Executor adds TOOL_RESULT step to chain ← Uses ReasoningStep (from agents!)
        ↓
8. Returns to engine
```

---

## Recommended Refactoring

### Solution 1: Extract Chain Recording Interface (Recommended)

**Create abstraction in tools layer**:

```
src/omniforge/tools/
├── chain_recorder.py (NEW)
│   └── ChainRecorder (Protocol/Interface)
│       - record_tool_call(...)
│       - record_tool_result(...)
```

**Implementation**:

```python
# tools/chain_recorder.py
from typing import Protocol, Any

class ChainRecorder(Protocol):
    """Protocol for recording tool execution steps."""

    def record_tool_call(
        self,
        tool_name: str,
        tool_type: str,
        parameters: dict,
        correlation_id: str
    ) -> None:
        """Record a tool call."""
        ...

    def record_tool_result(
        self,
        correlation_id: str,
        success: bool,
        result: Any,
        error: Optional[str],
        tokens_used: int,
        cost: float
    ) -> None:
        """Record a tool result."""
        ...

# tools/executor.py
class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        recorder: Optional[ChainRecorder] = None,  # Optional!
        ...
    ):
        self._recorder = recorder

    async def execute(...):
        # Record if recorder provided
        if self._recorder:
            self._recorder.record_tool_call(...)

        # Execute tool
        result = await tool.execute(...)

        # Record result if recorder provided
        if self._recorder:
            self._recorder.record_tool_result(...)
```

**Adapter in agents layer**:

```python
# agents/cot/chain_adapter.py
from omniforge.tools.chain_recorder import ChainRecorder
from omniforge.agents.cot.chain import ReasoningChain, ReasoningStep, StepType

class ReasoningChainRecorder(ChainRecorder):
    """Adapts ReasoningChain to ChainRecorder protocol."""

    def __init__(self, chain: ReasoningChain):
        self._chain = chain

    def record_tool_call(self, tool_name, tool_type, parameters, correlation_id):
        step = ReasoningStep(
            type=StepType.TOOL_CALL,
            tool_call=ToolCallInfo(...)
        )
        self._chain.add_step(step)

    def record_tool_result(self, correlation_id, success, result, error, tokens, cost):
        step = ReasoningStep(
            type=StepType.TOOL_RESULT,
            tool_result=ToolResultInfo(...)
        )
        self._chain.add_step(step)
```

**Benefits**:
- ✅ Removes cross-boundary dependency
- ✅ Tools layer no longer knows about agents
- ✅ Follows Dependency Inversion Principle
- ✅ ToolExecutor can be used standalone
- ✅ Easy to add other recording mechanisms

### Solution 2: Extract Skills Management (Recommended)

**Create separate SkillManager**:

```python
# tools/skill_manager.py (NEW)
class SkillManager:
    """Manages skill activation and restrictions."""

    def __init__(self):
        self._skill_stack: List[Skill] = []
        self._skill_contexts: Dict[str, SkillContext] = {}

    def activate_skill(self, skill: Skill) -> None: ...
    def deactivate_skill(self, skill_name: str) -> None: ...
    def check_tool_allowed(self, tool_name: str) -> bool: ...
    def check_arguments(self, tool_name: str, args: dict) -> bool: ...

# tools/executor.py
class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        skill_manager: Optional[SkillManager] = None,  # Optional!
        ...
    ):
        self._skill_manager = skill_manager

    async def execute(...):
        # Check skills if manager provided
        if self._skill_manager:
            if not self._skill_manager.check_tool_allowed(tool_name):
                return ToolResult(success=False, error="Not allowed")
```

**Benefits**:
- ✅ Single Responsibility Principle
- ✅ ToolExecutor focuses on execution only
- ✅ Skills are optional feature
- ✅ Easier to test

### Solution 3: Consolidate Singleton Registries

**Single source of truth**:

```python
# tools/registry.py
_default_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()

def get_default_registry() -> ToolRegistry:
    """Get or create the default singleton registry."""
    global _default_registry
    if _default_registry is not None:
        return _default_registry

    with _registry_lock:
        if _default_registry is None:
            _default_registry = ToolRegistry()
        return _default_registry

# tools/setup.py - Remove duplicate, use registry.py instead
from omniforge.tools.registry import get_default_registry

def setup_default_tools(config: Optional[LLMConfig] = None) -> ToolRegistry:
    """Setup default tools on the singleton registry."""
    registry = get_default_registry()  # Reuse existing

    llm_config = config or load_config_from_env()
    llm_tool = LLMTool(config=llm_config)
    registry.register(llm_tool)

    return registry
```

**Benefits**:
- ✅ Single point of truth
- ✅ No confusion about which registry to use
- ✅ Clearer API

---

## Improved Architecture

### After Refactoring

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                               │
│  ┌──────────────────────────────────────────────────┐           │
│  │  ReasoningEngine                                 │           │
│  │  • Uses ToolExecutor with ChainRecorder adapter │           │
│  └───────────────────┬──────────────────────────────┘           │
│                      │                                           │
│  ┌──────────────────┴──────────────────────────────┐           │
│  │  ReasoningChainRecorder (Adapter)               │           │
│  │  • Implements ChainRecorder protocol            │           │
│  │  • Wraps ReasoningChain                         │           │
│  └──────────────────────────────────────────────────┘           │
└────────────────────────┬────────────────────────────────────────┘
                         │ depends on (interface only)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        TOOLS LAYER                               │
│  ┌──────────────────────────────────────────────────┐           │
│  │  ChainRecorder (Protocol) ← Interface            │           │
│  │  • record_tool_call(...)                         │           │
│  │  • record_tool_result(...)                       │           │
│  └──────────────────────────────────────────────────┘           │
│                      ▲                                           │
│                      │ implements                                │
│  ┌──────────────────┴──────────────────────────────┐           │
│  │  ToolExecutor                                    │           │
│  │  • Uses ChainRecorder (optional)                │           │
│  │  • No dependency on agents/                     │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │  SkillManager (Optional)                         │           │
│  │  • Manages skill activation                      │           │
│  │  • Separated from ToolExecutor                   │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

**Dependency Flow**:
```
Agents (high-level)
    ↓ depends on (via Protocol)
Tools (low-level)
```

No reverse dependency!

---

## Summary of Recommendations

### Priority 1 (Critical)
1. ✅ **Extract ChainRecorder Protocol**
   - Create `tools/chain_recorder.py` with Protocol
   - Make ToolExecutor accept optional `ChainRecorder`
   - Create adapter in `agents/cot/chain_adapter.py`
   - Remove direct import of `ReasoningChain` from `tools/executor.py`

### Priority 2 (High)
2. ✅ **Extract SkillManager**
   - Create `tools/skill_manager.py`
   - Move skill logic from ToolExecutor
   - Make it optional dependency

3. ✅ **Consolidate Registry Singletons**
   - Keep only `tools/registry.py::get_default_registry()`
   - Update `tools/setup.py` to use it
   - Remove duplicate singleton

### Priority 3 (Medium)
4. ✅ **Consistent TYPE_CHECKING Usage**
   - Use TYPE_CHECKING for circular import prevention
   - Apply consistently across codebase

5. ✅ **Extract Common Protocols**
   - Create `tools/protocols.py` for RateLimiter, CostTracker
   - Move from inline definitions to reusable protocols

### Priority 4 (Nice to Have)
6. ✅ **Registry Interface**
   - Create `Registry[T]` generic interface
   - Both ToolRegistry and AgentRegistry implement it
   - Reduces code duplication

---

## File Changes Required

### New Files
```
src/omniforge/tools/
├── chain_recorder.py          (NEW - Protocol)
├── skill_manager.py           (NEW - Extract from executor)
└── protocols.py               (NEW - Common protocols)

src/omniforge/agents/cot/
└── chain_adapter.py           (NEW - Adapter)
```

### Modified Files
```
src/omniforge/tools/
├── executor.py                (MODIFY - Remove chain imports, use protocol)
├── registry.py                (MODIFY - Consolidate singleton)
└── setup.py                   (MODIFY - Use single registry)

src/omniforge/agents/cot/
├── agent.py                   (MODIFY - Use chain adapter)
└── engine.py                  (MODIFY - Pass adapter to executor)
```

### Impact
- 🔴 **Breaking Changes**: None (backward compatible via adapter)
- 🟢 **New APIs**: ChainRecorder protocol, SkillManager class
- 🟡 **Deprecations**: Duplicate registry functions

---

## Benefits After Refactoring

1. **Cleaner Dependencies**
   - Tools layer independent of agents
   - Can use tools without agents

2. **Better Testability**
   - Mock ChainRecorder easily
   - Test ToolExecutor in isolation

3. **More Flexibility**
   - Add new recorders (database, file, etc.)
   - Use tools in different contexts

4. **Follows SOLID Principles**
   - Single Responsibility
   - Dependency Inversion
   - Open/Closed Principle

5. **Reduced Coupling**
   - Modules can evolve independently
   - Easier to maintain

6. **Better Performance**
   - Optional recording (skip if not needed)
   - Optional skill checking

Would you like me to implement any of these refactorings?
