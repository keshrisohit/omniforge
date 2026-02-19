# Dependency Graph - Visual Representation

Visual diagrams showing current dependencies and proposed improvements.

## Current Architecture (With Problems)

### Complete Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL DEPENDENCIES                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Pydantic │  │ FastAPI  │  │ LiteLLM  │  │ asyncio  │  etc...   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │ uses
┌──────────────────────────────────┴──────────────────────────────────┐
│                           PRESENTATION                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                    │
│  │ API Routes │  │    CLI     │  │    Chat    │                    │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                    │
└────────┼────────────────┼────────────────┼──────────────────────────┘
         │                │                │
         └────────────────┴────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │              AgentRegistry                          │            │
│  │  ┌──────────────────────────────────────┐          │            │
│  │  │ • register(agent)                    │          │            │
│  │  │ • find_by_skill()                    │          │            │
│  │  └──────────────────────────────────────┘          │            │
│  └────────────────────────┬───────────────────────────┘            │
│                           │                                         │
│  ┌────────────────────────┴──────────────────────────┐             │
│  │               Agent Implementations                │             │
│  │  ┌──────────────────────────────────────┐         │             │
│  │  │         BaseAgent (abstract)         │         │             │
│  │  └──────────────┬───────────────────────┘         │             │
│  │                 │                                  │             │
│  │      ┌──────────┴──────────┬──────────────┐       │             │
│  │      ▼                     ▼              ▼       │             │
│  │  ┌─────────┐         ┌──────────┐   ┌────────┐   │             │
│  │  │CoTAgent │         │Simple    │   │Custom  │   │             │
│  │  │         │         │Agent     │   │Agents  │   │             │
│  │  └────┬────┘         └──────────┘   └────────┘   │             │
│  │       │                                           │             │
│  │       │ extends                                   │             │
│  │       ▼                                           │             │
│  │  ┌─────────────────┐                             │             │
│  │  │AutonomousCoTAgent│                            │             │
│  │  └────┬────────────┘                             │             │
│  └───────┼──────────────────────────────────────────┘             │
│          │                                                         │
│          │ creates & uses                                          │
│          ▼                                                         │
│  ┌─────────────────────────────────────────────────┐              │
│  │         ReasoningEngine                          │              │
│  │  ┌────────────────────────────────────┐         │              │
│  │  │ • _chain: ReasoningChain           │         │              │
│  │  │ • _executor: ToolExecutor          │         │              │
│  │  │ • add_thinking()                   │         │              │
│  │  │ • call_llm()                       │         │              │
│  │  │ • call_tool()                      │         │              │
│  │  │ • add_synthesis()                  │         │              │
│  │  └────────────────────────────────────┘         │              │
│  └────────┬──────────────┬─────────────────────────┘              │
│           │              │                                         │
│           │ uses         │ uses                                    │
│           ▼              ▼                                         │
│  ┌────────────────┐  ┌────────────────────┐                       │
│  │ReasoningChain  │  │  ToolCallResult    │                       │
│  │• steps[]       │  │  • result          │                       │
│  │• metrics       │  │  • call_step       │                       │
│  │• add_step()    │  │  • result_step     │                       │
│  └────────────────┘  └────────────────────┘                       │
└──────────┬──────────────────────────────────────────────────────── ┘
           │
           │ delegates to
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          TOOLS LAYER                                  │
│                                                                       │
│  ┌─────────────────────────────────────────────────┐                 │
│  │             ToolExecutor                         │                 │
│  │  ┌────────────────────────────────────┐         │                 │
│  │  │ • _registry: ToolRegistry          │         │                 │
│  │  │ • _rate_limiter                    │         │                 │
│  │  │ • _cost_tracker                    │         │                 │
│  │  │ • _skill_stack  ⚠️                │         │                 │
│  │  │ • _skill_contexts  ⚠️             │         │                 │
│  │  │                                    │         │                 │
│  │  │ • execute(tool, args, ctx, chain) │ ⚠️      │                 │
│  │  │ • activate_skill()  ⚠️            │         │                 │
│  │  └────────────────────────────────────┘         │                 │
│  └────────┬──────────────────┬──────────────────────┘                 │
│           │                  │                                        │
│           │ uses             │ IMPORTS ⚠️ PROBLEM!                   │
│           │                  │                                        │
│           ▼                  ▼                                        │
│  ┌────────────────┐  ┌──────────────────────────┐                    │
│  │  ToolRegistry  │  │ agents/cot/chain.py:     │ ← BAD!             │
│  │  (Singleton)   │  │ • ReasoningChain         │                    │
│  │  • register()  │  │ • ReasoningStep          │                    │
│  │  • get()       │  │ • StepType               │                    │
│  └────────┬───────┘  │ • ToolCallInfo           │                    │
│           │          │ • ToolResultInfo         │                    │
│           │          └──────────────────────────┘                    │
│           │ provides                                                 │
│           ▼                                                          │
│  ┌─────────────────────────────────────────────────┐                │
│  │         Tool Implementations                     │                │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │                │
│  │  │ LLMTool  │  │  DBTool  │  │FileSystem│ ...  │                │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘      │                │
│  └───────┼─────────────┼─────────────┼─────────────┘                │
│          │             │             │                               │
│          │ extends     │ extends     │ extends                       │
│          └─────────────┴─────────────┴───────┐                       │
│                                              ▼                       │
│  ┌──────────────────────────────────────────────────┐               │
│  │          BaseTool (abstract)                      │               │
│  │  • definition: ToolDefinition                    │               │
│  │  • execute(ctx, args) → ToolResult              │               │
│  └──────────────────────────────────────────────────┘               │
│                          ▲                                           │
│                          │ uses                                      │
│  ┌──────────────────────┴──────────────────────────┐               │
│  │         LLMTool (special)                        │               │
│  │  • _config: LLMConfig                           │               │
│  │  • _setup_litellm()                             │               │
│  └──────────────────────┬──────────────────────────┘               │
│                         │ uses                                       │
└─────────────────────────┼────────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          LLM LAYER                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   LLMConfig     │  │ ProviderConfig  │  │  Cost Utils     │     │
│  │  • providers    │  │ • api_key       │  │ • estimate_cost │     │
│  │  • default_model│  │ • api_base      │  │ • track_cost    │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
                          ▲
                          │ uses
                          ▼
                    ┌──────────┐
                    │ LiteLLM  │
                    └──────────┘
```

### Problem Highlighted

```
┌────────────────────────┐
│    AGENTS LAYER        │
│  agents/cot/chain.py   │
│  • ReasoningChain      │
│  • ReasoningStep       │
└───────────┬────────────┘
            │
            │ ⚠️ IMPORTED BY (Cross-boundary!)
            │
            ▼
┌────────────────────────┐
│    TOOLS LAYER         │
│  tools/executor.py     │
│  • ToolExecutor        │
└────────────────────────┘

This violates the dependency rule:
High-level (Agents) should NOT be imported by low-level (Tools)
```

---

## Proposed Architecture (After Refactoring)

### Clean Dependency Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │         ReasoningEngine                             │            │
│  │  • Creates ReasoningChainRecorder (adapter)        │            │
│  │  • Passes adapter to ToolExecutor                  │            │
│  └────────────────────┬───────────────────────────────┘            │
│                       │                                             │
│                       │ creates adapter                             │
│                       ▼                                             │
│  ┌────────────────────────────────────────────────────┐            │
│  │     ReasoningChainRecorder (Adapter)               │            │
│  │  implements ChainRecorder ─────────────┐           │            │
│  │  • record_tool_call()                  │           │            │
│  │  • record_tool_result()                │           │            │
│  │  wraps ReasoningChain                  │           │            │
│  └────────────────────────────────────────┘           │            │
└────────────────────────────────────────────────────────┼────────────┘
                                                         │
                                                         │ implements
                                                         │ (interface only)
                                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          TOOLS LAYER                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │       ChainRecorder (Protocol) ← INTERFACE         │            │
│  │  • record_tool_call(...)                           │            │
│  │  • record_tool_result(...)                         │            │
│  └────────────────────┬───────────────────────────────┘            │
│                       ▲                                             │
│                       │ uses (optional)                             │
│  ┌────────────────────┴───────────────────────────────┐            │
│  │             ToolExecutor                            │            │
│  │  • _recorder: Optional[ChainRecorder]  ← Optional! │            │
│  │  • _skill_manager: Optional[SkillManager]          │            │
│  │                                                     │            │
│  │  • execute(tool, args, ctx)  ← No chain param!    │            │
│  │                                                     │            │
│  │  if self._recorder:                                │            │
│  │      self._recorder.record_tool_call(...)          │            │
│  └─────────────────────────────────────────────────────┘            │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │         SkillManager (NEW - Separated)             │            │
│  │  • activate_skill(skill)                           │            │
│  │  • deactivate_skill(name)                          │            │
│  │  • check_tool_allowed(tool_name)                   │            │
│  └────────────────────────────────────────────────────┘            │
│                                                                      │
│  ✅ No dependency on agents/ layer!                                │
│  ✅ Can be used standalone!                                         │
└──────────────────────────────────────────────────────────────────────┘
```

### Dependency Direction (Fixed)

```
┌──────────────────┐
│  AGENTS LAYER    │
│  (High-level)    │
└────────┬─────────┘
         │
         │ depends on (Protocol only) ✅
         │
         ▼
┌──────────────────┐
│  TOOLS LAYER     │
│  (Low-level)     │
└──────────────────┘

✅ Correct: High-level depends on low-level
✅ Low-level defines interface
✅ High-level implements interface
```

---

## Module Dependency Matrix

### Current State

| Module | Depends On | Dependency Count | Issues |
|--------|------------|------------------|--------|
| `agents/base` | `tasks/models`, `agents/models`, `agents/events` | 3 | ✅ OK |
| `agents/cot/chain` | `tools/types` | 1 | ✅ OK |
| `agents/cot/engine` | `agents/cot/chain`, `tools/base` | 2 | ✅ OK |
| `agents/cot/agent` | `agents/base`, `agents/cot/chain`, `agents/cot/engine`, `tools/registry` | 4 | ✅ OK |
| `tools/base` | `tools/types` | 1 | ✅ OK |
| `tools/registry` | `tools/base` | 1 | ✅ OK |
| `tools/executor` | `tools/registry`, `tools/base`, **`agents/cot/chain`** ⚠️, `skills/*` ⚠️ | 5 | ❌ **BAD** |
| `tools/builtin/llm` | `tools/base`, `llm/config`, `llm/cost` | 3 | ✅ OK |
| `llm/config` | `pydantic` | 1 | ✅ OK |
| `llm/cost` | (none) | 0 | ✅ OK |

### After Refactoring

| Module | Depends On | Dependency Count | Issues |
|--------|------------|------------------|--------|
| `agents/cot/chain_adapter` | `agents/cot/chain`, `tools/chain_recorder` | 2 | ✅ OK |
| `tools/executor` | `tools/registry`, `tools/base`, `tools/chain_recorder` ✅ | 3 | ✅ **FIXED** |
| `tools/chain_recorder` | (interface only) | 0 | ✅ **NEW** |
| `tools/skill_manager` | `skills/*` | 1 | ✅ **NEW** |

**Improvements**:
- ❌ Removed: `tools/executor` → `agents/cot/chain` dependency
- ❌ Removed: `tools/executor` → `skills/*` dependency
- ✅ Added: `tools/chain_recorder` (Protocol)
- ✅ Added: `tools/skill_manager` (Extracted)

---

## Call Flow Comparison

### Current Flow (Problematic)

```
1. Agent creates ReasoningEngine
        ↓
2. Agent creates ToolExecutor
        ↓
3. Agent: engine.call_tool("database", {...})
        ↓
4. ReasoningEngine: executor.execute(tool, args, context, chain) ← Passes chain
        ↓
5. ToolExecutor: chain.add_step(TOOL_CALL)  ← Directly uses ReasoningChain!
        ↓
6. ToolExecutor: tool.execute(...)
        ↓
7. ToolExecutor: chain.add_step(TOOL_RESULT)  ← Directly uses ReasoningChain!
        ↓
8. Returns ToolResult

⚠️ Problem: ToolExecutor knows about ReasoningChain structure
```

### Proposed Flow (Clean)

```
1. Agent creates ReasoningEngine
        ↓
2. Agent creates ReasoningChain
        ↓
3. Agent creates ReasoningChainRecorder(chain)  ← Adapter
        ↓
4. Agent creates ToolExecutor(registry, recorder=adapter)  ← Injection
        ↓
5. Agent: engine.call_tool("database", {...})
        ↓
6. ReasoningEngine: executor.execute(tool, args, context)  ← No chain!
        ↓
7. ToolExecutor: if self._recorder:
                    self._recorder.record_tool_call(...)  ← Uses interface
        ↓
8. ToolExecutor: tool.execute(...)
        ↓
9. ToolExecutor: if self._recorder:
                    self._recorder.record_tool_result(...)  ← Uses interface
        ↓
10. Returns ToolResult

✅ Benefit: ToolExecutor only knows about ChainRecorder interface
✅ Benefit: Can use ToolExecutor without any recorder
✅ Benefit: Easy to add new recorders (database, file, etc.)
```

---

## Circular Dependency Analysis

### Current (Potential Circular Dependencies)

```
agents/cot/engine.py
    ↓ imports
tools/executor.py  (TYPE_CHECKING) ✅ Safe
    ↓ imports
agents/cot/chain.py  ❌ Real import
    ↓ imports
tools/types.py  ✅ OK (types only)
```

**Risk**: If `agents/cot/chain.py` ever imports from `tools/executor.py`, we have a cycle!

### After Refactoring (No Risk)

```
agents/cot/engine.py
    ↓ imports
tools/executor.py  (TYPE_CHECKING) ✅ Safe
    ↓ imports
tools/chain_recorder.py  ✅ Protocol only
    ↓ (no imports)

agents/cot/chain_adapter.py  ← Separate file
    ↓ imports
agents/cot/chain.py  ✅ OK
    ↓ imports
tools/chain_recorder.py  ✅ Protocol
```

**No circular dependency possible!**

---

## Testing Impact

### Current (Difficult to Test)

```python
# Testing ToolExecutor requires ReasoningChain
from omniforge.agents.cot.chain import ReasoningChain
from omniforge.tools.executor import ToolExecutor

def test_tool_executor():
    chain = ReasoningChain(task_id="test", agent_id="test")  # Required!
    executor = ToolExecutor(registry)

    result = await executor.execute(
        tool_name="test_tool",
        arguments={},
        context=context,
        chain=chain  # Must provide
    )

    # Check chain was updated
    assert len(chain.steps) == 2
```

**Problems**:
- ❌ Must create ReasoningChain for testing
- ❌ ToolExecutor tightly coupled to agent concepts
- ❌ Can't test tool execution in isolation

### After Refactoring (Easy to Test)

```python
# Testing ToolExecutor without any recorder
from omniforge.tools.executor import ToolExecutor

def test_tool_executor_standalone():
    executor = ToolExecutor(registry)  # No recorder!

    result = await executor.execute(
        tool_name="test_tool",
        arguments={},
        context=context
        # No chain parameter!
    )

    # Just test tool execution
    assert result.success


# Testing with mock recorder
class MockRecorder:
    def __init__(self):
        self.calls = []
        self.results = []

    def record_tool_call(self, **kwargs):
        self.calls.append(kwargs)

    def record_tool_result(self, **kwargs):
        self.results.append(kwargs)


def test_tool_executor_with_recording():
    recorder = MockRecorder()
    executor = ToolExecutor(registry, recorder=recorder)

    result = await executor.execute(...)

    # Verify recording happened
    assert len(recorder.calls) == 1
    assert len(recorder.results) == 1
```

**Benefits**:
- ✅ Can test ToolExecutor standalone
- ✅ Easy to mock recorder
- ✅ Test tool execution separately from recording
- ✅ Faster tests (no need to create full chain)

---

## Performance Impact

### Current

```
Every tool execution:
  1. Create TOOL_CALL step (allocates ReasoningStep object)
  2. Add to chain (list append, metrics update)
  3. Execute tool
  4. Create TOOL_RESULT step (allocates ReasoningStep object)
  5. Add to chain (list append, metrics update)

✅ Fine for normal use
❌ Overhead if you just want to execute tools without recording
```

### After Refactoring

```
With recorder:
  (Same as before)

Without recorder:
  1. Execute tool  ← That's it!

✅ No overhead when recording not needed
✅ Faster for simple tool execution
✅ Less memory allocation
```

**Use cases**:
- Testing tools in isolation
- CLI tools that don't need reasoning chains
- Simple scripts
- Performance-critical paths

---

## Migration Path

### Phase 1: Add New Code (Backward Compatible)
1. Create `tools/chain_recorder.py` with Protocol
2. Create `agents/cot/chain_adapter.py` with adapter
3. Create `tools/skill_manager.py`
4. Update `ToolExecutor` to accept optional recorder and skill_manager
5. Keep old API working (pass chain and convert internally)

### Phase 2: Update Callsites
1. Update `agents/cot/engine.py` to use adapter
2. Update `agents/cot/agent.py` to create adapter
3. Update tests to use new API

### Phase 3: Deprecate Old API
1. Mark old `execute(chain=...)` as deprecated
2. Add deprecation warnings
3. Update documentation

### Phase 4: Remove Old Code
1. Remove old `execute(chain=...)` parameter
2. Remove direct chain imports from `tools/executor.py`
3. Clean up deprecated code

**Timeline**: 2-3 weeks for full migration

---

## Summary

### Current Issues
1. ❌ **Cross-boundary dependency**: `tools/` imports from `agents/`
2. ❌ **Tight coupling**: ToolExecutor knows about ReasoningChain structure
3. ❌ **Mixed responsibilities**: ToolExecutor handles both execution and skills
4. ❌ **Hard to test**: Can't test tools without creating chains
5. ❌ **Duplicate singletons**: Two registry singletons

### Proposed Solutions
1. ✅ **Protocol extraction**: `ChainRecorder` interface
2. ✅ **Adapter pattern**: `ReasoningChainRecorder` adapts chain to protocol
3. ✅ **Separation of concerns**: Extract `SkillManager`
4. ✅ **Dependency inversion**: Tools layer owns interface
5. ✅ **Consolidate singletons**: Single registry source of truth

### Benefits
1. ✅ **Clean architecture**: Proper dependency flow
2. ✅ **Better testability**: Can test in isolation
3. ✅ **More flexibility**: Easy to add new recorders
4. ✅ **Better performance**: Optional recording
5. ✅ **SOLID principles**: Follows best practices
