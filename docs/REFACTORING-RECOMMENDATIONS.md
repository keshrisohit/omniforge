# Refactoring Recommendations Summary

Quick reference for architectural improvements based on dependency analysis.

**Status Update (2026-01-14):** ✅ Priority 1 refactoring completed! See `REFACTORING-COMPLETED.md` for details.

## Critical Issues Found

### ✅ Issue #1: Cross-Boundary Dependency (COMPLETED)

**Location**: `src/omniforge/tools/executor.py:13-20`

```python
# ❌ PROBLEM: Tools layer importing from Agents layer
from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    ToolCallInfo,
    ToolResultInfo,
    VisibilityConfig,
)
```

**Why it's bad**:
- Violates layered architecture
- Tools (low-level) depend on Agents (high-level)
- Can't use tools without agent context
- Prevents tool reuse in other contexts

**Impact**: HIGH - Affects architecture, testing, flexibility

---

### 🟡 Issue #2: Mixed Responsibilities in ToolExecutor (MEDIUM)

**Location**: `src/omniforge/tools/executor.py:66-96`

```python
class ToolExecutor:
    def __init__(self, ...):
        # Tool execution stuff
        self._registry = registry
        self._rate_limiter = rate_limiter

        # ❌ Skill management stuff (different responsibility)
        self._skill_stack: List[Skill] = []
        self._skill_contexts: Dict[str, SkillContext] = {}
```

**Why it's bad**:
- Single Responsibility Principle violation
- ToolExecutor has two jobs: execute tools AND manage skills
- Harder to test and maintain

**Impact**: MEDIUM - Affects maintainability, testability

---

### 🟡 Issue #3: Duplicate Singleton Registries (MEDIUM)

**Locations**:
- `src/omniforge/tools/registry.py:60-70`
- `src/omniforge/tools/setup.py:14-16`

```python
# tools/registry.py
_default_registry: Optional[ToolRegistry] = None

def get_default_registry() -> ToolRegistry:
    global _default_registry
    ...

# tools/setup.py
_default_registry: Optional[ToolRegistry] = None  # ❌ Duplicate!

def get_default_tool_registry() -> ToolRegistry:
    global _default_registry
    ...
```

**Why it's bad**:
- Confusing API: which one to use?
- Potential bugs: two different singletons
- Inconsistent patterns

**Impact**: MEDIUM - Affects clarity, consistency

---

## Recommended Solutions

### ✅ Solution #1: Extract ChainRecorder Protocol (PRIORITY 1)

**Create new interface in tools layer**:

```python
# src/omniforge/tools/chain_recorder.py (NEW FILE)
from typing import Protocol, Any, Optional

class ChainRecorder(Protocol):
    """Protocol for recording tool execution steps.

    This allows different recording implementations without
    coupling ToolExecutor to specific chain implementations.
    """

    def record_tool_call(
        self,
        tool_name: str,
        tool_type: str,
        parameters: dict[str, Any],
        correlation_id: str,
    ) -> None:
        """Record a tool call step."""
        ...

    def record_tool_result(
        self,
        correlation_id: str,
        success: bool,
        result: Optional[dict[str, Any]],
        error: Optional[str],
        tokens_used: int,
        cost: float,
    ) -> None:
        """Record a tool result step."""
        ...
```

**Update ToolExecutor**:

```python
# src/omniforge/tools/executor.py (MODIFY)
from omniforge.tools.chain_recorder import ChainRecorder

class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        recorder: Optional[ChainRecorder] = None,  # ✅ Optional!
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self._registry = registry
        self._recorder = recorder  # ✅ Store recorder
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        # ❌ Remove: chain: ReasoningChain
    ) -> ToolResult:
        """Execute tool with optional recording."""
        # ... validation ...

        # ✅ Record if recorder provided
        if self._recorder:
            self._recorder.record_tool_call(
                tool_name=tool_name,
                tool_type=tool.definition.type.value,
                parameters=arguments,
                correlation_id=context.correlation_id,
            )

        # Execute tool
        result = await self._execute_with_retries(tool, arguments, context)

        # ✅ Record result if recorder provided
        if self._recorder:
            self._recorder.record_tool_result(
                correlation_id=context.correlation_id,
                success=result.success,
                result=result.result,
                error=result.error,
                tokens_used=result.tokens_used,
                cost=result.cost_usd,
            )

        return result
```

**Create adapter in agents layer**:

```python
# src/omniforge/agents/cot/chain_adapter.py (NEW FILE)
from omniforge.tools.chain_recorder import ChainRecorder
from omniforge.agents.cot.chain import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    ToolCallInfo,
    ToolResultInfo,
)
from omniforge.tools.types import ToolType

class ReasoningChainRecorder(ChainRecorder):
    """Adapts ReasoningChain to ChainRecorder protocol."""

    def __init__(self, chain: ReasoningChain):
        self._chain = chain

    def record_tool_call(
        self,
        tool_name: str,
        tool_type: str,
        parameters: dict,
        correlation_id: str,
    ) -> None:
        """Record tool call as a ReasoningStep."""
        step = ReasoningStep(
            step_number=0,  # Auto-assigned by chain
            type=StepType.TOOL_CALL,
            tool_call=ToolCallInfo(
                tool_name=tool_name,
                tool_type=ToolType(tool_type),
                parameters=parameters,
                correlation_id=correlation_id,
            ),
        )
        self._chain.add_step(step)

    def record_tool_result(
        self,
        correlation_id: str,
        success: bool,
        result: dict | None,
        error: str | None,
        tokens_used: int,
        cost: float,
    ) -> None:
        """Record tool result as a ReasoningStep."""
        step = ReasoningStep(
            step_number=0,  # Auto-assigned by chain
            type=StepType.TOOL_RESULT,
            tool_result=ToolResultInfo(
                correlation_id=correlation_id,
                success=success,
                result=result,
                error=error,
            ),
            tokens_used=tokens_used,
            cost=cost,
        )
        self._chain.add_step(step)
```

**Update ReasoningEngine**:

```python
# src/omniforge/agents/cot/engine.py (MODIFY)
from omniforge.agents.cot.chain_adapter import ReasoningChainRecorder

class ReasoningEngine:
    def __init__(
        self,
        chain: ReasoningChain,
        executor: ToolExecutor,
        task: dict[str, Any],
        default_llm_model: str = "claude-sonnet-4",
    ):
        self._chain = chain
        self._executor = executor
        self._task = task
        self._default_llm_model = default_llm_model

        # ✅ Create adapter for chain recording
        self._recorder = ReasoningChainRecorder(chain)

    async def call_tool(...) -> ToolCallResult:
        # Build context
        context = ToolCallContext(...)

        # ✅ Pass recorder via executor's recorder field (set it if needed)
        # Or pass to execute method if we add that parameter
        result = await self._executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
            # ❌ Remove: chain=self._chain
        )
        ...
```

**Alternative: Set recorder during executor creation**:

```python
# src/omniforge/agents/cot/agent.py (MODIFY)
def _build_engine(self, chain: ReasoningChain) -> ReasoningEngine:
    """Build reasoning engine with chain adapter."""
    # Create recorder adapter
    recorder = ReasoningChainRecorder(chain)

    # Create executor with recorder
    executor = ToolExecutor(
        registry=self._tool_registry,
        recorder=recorder,  # ✅ Inject adapter
    )

    # Create engine
    return ReasoningEngine(
        chain=chain,
        executor=executor,
        task=self._current_task_context,
    )
```

**Benefits**:
- ✅ Removes cross-boundary dependency
- ✅ ToolExecutor can work standalone (no recorder)
- ✅ Easy to add new recorders (database, file, etc.)
- ✅ Follows Dependency Inversion Principle
- ✅ Better testability

**Files to create**:
- `src/omniforge/tools/chain_recorder.py`
- `src/omniforge/agents/cot/chain_adapter.py`

**Files to modify**:
- `src/omniforge/tools/executor.py`
- `src/omniforge/agents/cot/engine.py`
- `src/omniforge/agents/cot/agent.py`

**Backward compatibility**: ✅ Yes (via adapter)

**Estimated effort**: 4-6 hours

---

### ✅ Solution #2: Extract SkillManager (PRIORITY 2)

**Create separate skill manager**:

```python
# src/omniforge/tools/skill_manager.py (NEW FILE)
from typing import Dict, List, Optional
from omniforge.skills.models import Skill
from omniforge.skills.context import SkillContext
from omniforge.skills.errors import SkillActivationError, SkillError

class SkillManager:
    """Manages skill activation and tool restrictions.

    Separated from ToolExecutor for Single Responsibility Principle.
    """

    def __init__(self):
        self._skill_stack: List[Skill] = []
        self._skill_contexts: Dict[str, SkillContext] = {}

    @property
    def active_skill(self) -> Optional[Skill]:
        """Get currently active skill."""
        return self._skill_stack[-1] if self._skill_stack else None

    def activate_skill(self, skill: Skill, executor: "ToolExecutor") -> None:
        """Activate a skill."""
        skill_name = skill.metadata.name

        if skill_name in self._skill_contexts:
            raise SkillActivationError(
                skill_name=skill_name,
                reason="Skill already active"
            )

        context = SkillContext(skill, executor=executor)
        context.__enter__()

        self._skill_stack.append(skill)
        self._skill_contexts[skill_name] = context

    def deactivate_skill(self, skill_name: str) -> None:
        """Deactivate a skill."""
        if skill_name not in self._skill_contexts:
            return

        context = self._skill_contexts[skill_name]
        context.__exit__(None, None, None)

        del self._skill_contexts[skill_name]
        self._skill_stack = [s for s in self._skill_stack if s.metadata.name != skill_name]

    def check_tool_allowed(self, tool_name: str) -> tuple[bool, Optional[str]]:
        """Check if tool is allowed by active skill.

        Returns:
            (allowed: bool, error_message: Optional[str])
        """
        if not self.active_skill:
            return (True, None)

        context = self._skill_contexts[self.active_skill.metadata.name]
        try:
            context.check_tool_allowed(tool_name)
            return (True, None)
        except SkillError as e:
            return (False, e.message)

    def check_arguments(self, tool_name: str, arguments: dict) -> tuple[bool, Optional[str]]:
        """Check if arguments are allowed.

        Returns:
            (allowed: bool, error_message: Optional[str])
        """
        if not self.active_skill:
            return (True, None)

        context = self._skill_contexts[self.active_skill.metadata.name]
        try:
            context.check_tool_arguments(tool_name, arguments)
            return (True, None)
        except SkillError as e:
            return (False, e.message)
```

**Update ToolExecutor**:

```python
# src/omniforge/tools/executor.py (MODIFY)
from omniforge.tools.skill_manager import SkillManager

class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        recorder: Optional[ChainRecorder] = None,
        skill_manager: Optional[SkillManager] = None,  # ✅ Optional!
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self._registry = registry
        self._recorder = recorder
        self._skill_manager = skill_manager  # ✅ Inject skill manager
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker

    async def execute(...) -> ToolResult:
        # ... validation ...

        # ✅ Check skills if manager provided
        if self._skill_manager:
            allowed, error = self._skill_manager.check_tool_allowed(tool_name)
            if not allowed:
                return ToolResult(success=False, error=error, duration_ms=0)

            allowed, error = self._skill_manager.check_arguments(tool_name, arguments)
            if not allowed:
                return ToolResult(success=False, error=error, duration_ms=0)

        # ... rest of execution ...
```

**Benefits**:
- ✅ Single Responsibility Principle
- ✅ ToolExecutor simpler and focused
- ✅ Skill management is optional
- ✅ Easier to test both independently

**Files to create**:
- `src/omniforge/tools/skill_manager.py`

**Files to modify**:
- `src/omniforge/tools/executor.py`

**Backward compatibility**: ✅ Yes (skill_manager is optional)

**Estimated effort**: 2-3 hours

---

### ✅ Solution #3: Consolidate Singleton Registries (PRIORITY 3)

**Keep single source of truth**:

```python
# src/omniforge/tools/registry.py (KEEP THIS)
_default_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()

def get_default_registry() -> ToolRegistry:
    """Get the default singleton tool registry.

    This is the ONLY way to get the default registry.
    """
    global _default_registry

    if _default_registry is not None:
        return _default_registry

    with _registry_lock:
        if _default_registry is None:
            _default_registry = ToolRegistry()
        return _default_registry
```

**Update setup to use it**:

```python
# src/omniforge/tools/setup.py (MODIFY - Remove duplicate)
from omniforge.llm.config import LLMConfig, load_config_from_env
from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.registry import get_default_registry  # ✅ Import from registry

# ❌ Remove duplicate singleton
# _default_registry = None
# _registry_lock = threading.Lock()

def setup_default_tools(config: Optional[LLMConfig] = None) -> ToolRegistry:
    """Set up default built-in tools.

    Uses the singleton registry from tools.registry module.
    """
    registry = get_default_registry()  # ✅ Use single source of truth

    llm_config = config or load_config_from_env()
    llm_tool = LLMTool(config=llm_config)
    registry.register(llm_tool)

    return registry

# ❌ Remove: get_default_tool_registry() - use get_default_registry() instead
```

**Update imports**:

```python
# Before:
from omniforge.tools.setup import get_default_tool_registry

# After:
from omniforge.tools.registry import get_default_registry
```

**Benefits**:
- ✅ Single source of truth
- ✅ No confusion
- ✅ Clearer API

**Files to modify**:
- `src/omniforge/tools/setup.py`
- All files importing `get_default_tool_registry`

**Backward compatibility**: ❌ Breaking (but easy migration)

**Migration**: Add deprecation wrapper:

```python
# src/omniforge/tools/setup.py
import warnings
from omniforge.tools.registry import get_default_registry

def get_default_tool_registry() -> ToolRegistry:
    """DEPRECATED: Use get_default_registry() instead."""
    warnings.warn(
        "get_default_tool_registry() is deprecated. "
        "Use get_default_registry() from omniforge.tools.registry instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_default_registry()
```

**Estimated effort**: 1-2 hours

---

## Implementation Plan

### Phase 1: ChainRecorder Protocol (Week 1)
- [ ] Create `tools/chain_recorder.py` with Protocol
- [ ] Update `ToolExecutor` to accept optional `recorder`
- [ ] Create `agents/cot/chain_adapter.py`
- [ ] Update `ReasoningEngine` to use adapter
- [ ] Add tests for new code
- [ ] Keep backward compatibility

### Phase 2: Extract SkillManager (Week 1)
- [ ] Create `tools/skill_manager.py`
- [ ] Move skill logic from `ToolExecutor`
- [ ] Update `ToolExecutor` to use optional `SkillManager`
- [ ] Add tests
- [ ] Update documentation

### Phase 3: Consolidate Registries (Week 2)
- [ ] Add deprecation warning to `get_default_tool_registry()`
- [ ] Update all imports to use `get_default_registry()`
- [ ] Remove duplicate singleton after deprecation period

### Phase 4: Cleanup (Week 2)
- [ ] Remove deprecated code
- [ ] Update all documentation
- [ ] Run full test suite
- [ ] Performance benchmarks

---

## Testing Strategy

### Unit Tests

```python
# Test ToolExecutor without recorder
def test_executor_standalone():
    executor = ToolExecutor(registry)
    result = await executor.execute(...)
    assert result.success

# Test ToolExecutor with mock recorder
def test_executor_with_recorder():
    recorder = MockRecorder()
    executor = ToolExecutor(registry, recorder=recorder)
    result = await executor.execute(...)
    assert len(recorder.calls) == 1

# Test ToolExecutor with skill manager
def test_executor_with_skills():
    skill_mgr = SkillManager()
    executor = ToolExecutor(registry, skill_manager=skill_mgr)
    # Test skill restrictions
```

### Integration Tests

```python
# Test full flow with ReasoningEngine
def test_reasoning_engine_integration():
    chain = ReasoningChain(...)
    recorder = ReasoningChainRecorder(chain)
    executor = ToolExecutor(registry, recorder=recorder)
    engine = ReasoningEngine(chain, executor, ...)

    result = await engine.call_tool(...)
    assert len(chain.steps) == 2  # TOOL_CALL + TOOL_RESULT
```

---

## Success Metrics

- ✅ Zero circular dependencies
- ✅ Tools layer has no imports from agents layer
- ✅ ToolExecutor can be used standalone
- ✅ All existing tests pass
- ✅ Test coverage maintained or improved
- ✅ Documentation updated

---

## Questions?

See detailed diagrams:
- [class-dependencies-lld.md](./class-dependencies-lld.md) - Full LLD
- [dependency-graph-visual.md](./dependency-graph-visual.md) - Visual diagrams

For implementation questions, refer to code examples above or ask the team!
