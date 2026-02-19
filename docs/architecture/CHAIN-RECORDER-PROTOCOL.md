# ChainRecorder Protocol Architecture

**Date:** 2026-01-14
**Status:** ✅ Implemented
**Related:** Priority 1 Refactoring

## Overview

The `ChainRecorder` protocol is a foundational architectural pattern that enables the tools layer to record reasoning steps without depending on the concrete `ReasoningChain` implementation in the agents layer. This follows the **Dependency Inversion Principle** and eliminates cross-boundary coupling.

## Problem Statement

### Before Refactoring

```python
# ❌ VIOLATION: Tools layer importing from Agents layer
# src/omniforge/tools/executor.py
from omniforge.agents.cot.chain import ReasoningChain

class ToolExecutor:
    async def execute(
        self,
        chain: ReasoningChain,  # Direct dependency on concrete class
        ...
    ) -> ToolResult:
        chain.add_step(step)
```

**Issues:**
1. **Layering Violation**: Tools (lower level) depends on Agents (higher level)
2. **Tight Coupling**: Cannot use ToolExecutor without ReasoningChain
3. **Testing Difficulty**: Must instantiate full chain for tool executor tests
4. **Flexibility Loss**: Cannot create alternative chain implementations

## Solution: Protocol Pattern

### New Architecture

```
┌─────────────────────────┐
│   Agents Layer          │  ← High-level module
│  (agents/cot/chain.py)  │
│                         │
│  ReasoningChain         │
│    implements           │
│    ChainRecorder ✓      │
└───────────┬─────────────┘
            │ implements
            ▼
┌─────────────────────────┐
│   Core Layer            │  ← Abstraction
│  (core/protocols.py)    │
│                         │
│  ChainRecorder ◊        │  ← Protocol (interface)
└───────────▲─────────────┘
            │ depends on
            │
┌───────────┴─────────────┐
│   Tools Layer           │  ← Low-level module
│  (tools/executor.py)    │
│                         │
│  ToolExecutor           │
└─────────────────────────┘
```

### Protocol Definition

```python
# src/omniforge/core/protocols.py
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omniforge.agents.cot.chain import ReasoningStep


class ChainRecorder(Protocol):
    """Protocol for recording reasoning steps in a chain.

    This protocol allows the tools layer to record steps without depending
    on the concrete ReasoningChain implementation in the agents layer.

    The protocol defines the minimal interface needed for step recording,
    following the dependency inversion principle.

    The actual implementation is omniforge.agents.cot.chain.ReasoningChain,
    which automatically satisfies this protocol through structural typing.
    """

    def add_step(self, step: "ReasoningStep") -> None:
        """Add a step to the reasoning chain.

        Args:
            step: The reasoning step to add
        """
        ...
```

### Key Design Decisions

#### 1. TYPE_CHECKING Import

```python
if TYPE_CHECKING:
    from omniforge.agents.cot.chain import ReasoningStep
```

**Why?**
- Avoids runtime circular import
- Type checker can still validate types
- No performance penalty at runtime

#### 2. Minimal Interface

The protocol defines **only** what `ToolExecutor` needs:
- `add_step(step: ReasoningStep) -> None`

**Benefits:**
- Focused contract
- Easy to implement
- Clear responsibilities

#### 3. Structural Typing

Python's Protocol uses **structural typing** (duck typing), not nominal typing:

```python
# ReasoningChain doesn't need to explicitly inherit from ChainRecorder
class ReasoningChain(BaseModel):
    def add_step(self, step: ReasoningStep) -> None:  # ← Automatically satisfies protocol
        # Implementation
```

**Benefits:**
- No changes needed to existing code
- Backward compatible
- Works with any class that has `add_step()` method

## Implementation

### Updated ToolExecutor

```python
# src/omniforge/tools/executor.py
from omniforge.core.protocols import ChainRecorder  # ← Protocol import

class ToolExecutor:
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain: ChainRecorder,  # ← Protocol type hint
    ) -> ToolResult:
        # Create step
        step = ReasoningStep(...)

        # Record step (works with any ChainRecorder implementation)
        chain.add_step(step)

        return result
```

### ReasoningChain Implementation

```python
# src/omniforge/agents/cot/chain.py
class ReasoningChain(BaseModel):
    """A complete chain of reasoning for a task.

    Automatically satisfies ChainRecorder protocol through
    structural typing.
    """

    def add_step(self, step: ReasoningStep) -> None:
        """Add a step to the chain and update metrics."""
        # Implementation
```

**No changes required!** The existing `ReasoningChain` already satisfies the protocol.

## Benefits Achieved

### 1. ✅ Dependency Inversion

**Before:**
```
Tools Layer → (depends on) → Agents Layer
```

**After:**
```
Tools Layer → (depends on) → Core Protocol ← (implemented by) ← Agents Layer
```

Both layers now depend on abstraction, not concrete implementation.

### 2. ✅ Improved Testability

**Before:**
```python
# Must create full ReasoningChain
chain = ReasoningChain(task_id="...", agent_id="...")
executor = ToolExecutor(registry=registry)
await executor.execute(..., chain=chain)
```

**After:**
```python
# Can use simple mock
class MockChainRecorder:
    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)

mock_chain = MockChainRecorder()
executor = ToolExecutor(registry=registry)
await executor.execute(..., chain=mock_chain)
```

### 3. ✅ Enhanced Flexibility

Can create alternative implementations:

```python
class AuditedChainRecorder:
    """Chain recorder with audit logging."""

    def add_step(self, step: ReasoningStep) -> None:
        audit_logger.log(f"Step added: {step.type}")
        self.chain.add_step(step)


class CachedChainRecorder:
    """Chain recorder with caching."""

    def add_step(self, step: ReasoningStep) -> None:
        cache.store(step)
        self.chain.add_step(step)
```

### 4. ✅ Better Separation of Concerns

| Layer | Responsibility | Dependencies |
|-------|---------------|--------------|
| **Agents** | Chain implementation, business logic | Core protocols |
| **Core** | Protocol definitions, contracts | None |
| **Tools** | Tool execution, recording | Core protocols |

### 5. ✅ Type Safety Maintained

```bash
$ mypy src/omniforge/core/ src/omniforge/tools/executor.py
Success: no issues found in 3 source files
```

Full type checking support with no runtime overhead.

## Usage Patterns

### For Application Code

Use `ReasoningChain` (concrete class):

```python
from omniforge.agents.cot.chain import ReasoningChain

chain = ReasoningChain(task_id="task-123", agent_id="agent-456")
engine = ReasoningEngine(chain=chain, executor=executor, task=task)
```

### For Library/Infrastructure Code

Use `ChainRecorder` (protocol):

```python
from omniforge.core.protocols import ChainRecorder

def record_tool_execution(
    tool_name: str,
    result: ToolResult,
    chain: ChainRecorder  # ← Protocol type
) -> None:
    """Record tool execution to any chain recorder."""
    step = create_tool_result_step(tool_name, result)
    chain.add_step(step)
```

### For Testing

Use lightweight mocks:

```python
from omniforge.core.protocols import ChainRecorder
from omniforge.agents.cot.chain import ReasoningStep

class SimpleChainRecorder:
    """Minimal chain recorder for testing."""

    def __init__(self) -> None:
        self.steps: list[ReasoningStep] = []

    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)


def test_tool_executor():
    chain = SimpleChainRecorder()
    executor = ToolExecutor(registry=registry)

    await executor.execute("llm", {...}, context, chain)

    assert len(chain.steps) == 2  # TOOL_CALL + TOOL_RESULT
```

## Migration Guide

### For Existing Code

**No changes required!** All existing code continues to work:

```python
# This still works perfectly
chain = ReasoningChain(task_id="...", agent_id="...")
executor = ToolExecutor(registry=registry)
await executor.execute(..., chain=chain)
```

### For New Code

Prefer protocol types in signatures:

```python
# ✅ Good: Use protocol in function signature
def my_function(chain: ChainRecorder) -> None:
    step = create_step()
    chain.add_step(step)

# ❌ Avoid: Using concrete class in signature
def my_function(chain: ReasoningChain) -> None:
    step = create_step()
    chain.add_step(step)
```

## Design Principles Applied

### 1. Dependency Inversion Principle (DIP)

> High-level modules should not depend on low-level modules. Both should depend on abstractions.

✅ **Applied:** Both Tools and Agents layers depend on Core protocol.

### 2. Interface Segregation Principle (ISP)

> Clients should not be forced to depend on interfaces they don't use.

✅ **Applied:** Protocol defines only `add_step()`, not the entire ReasoningChain API.

### 3. Open/Closed Principle (OCP)

> Software entities should be open for extension, closed for modification.

✅ **Applied:** Can create new chain recorders without modifying existing code.

### 4. Liskov Substitution Principle (LSP)

> Objects of a supertype should be replaceable with objects of subtypes.

✅ **Applied:** Any `ChainRecorder` implementation can replace another.

## Performance Impact

**Zero runtime overhead:**
- Protocol checking happens at type-check time (mypy), not runtime
- `TYPE_CHECKING` import eliminated at runtime
- No additional function calls or wrappers

## Testing Results

### Test Coverage

```bash
$ pytest tests/tools/test_executor.py tests/agents/cot/test_engine.py -v
======================== 86 passed ========================

Coverage:
- src/omniforge/core/protocols.py: 100%
- src/omniforge/tools/executor.py: 70%
- src/omniforge/agents/cot/chain.py: 100%
- src/omniforge/agents/cot/engine.py: 100%
```

### Type Checking

```bash
$ mypy src/omniforge/core/ src/omniforge/tools/ src/omniforge/agents/cot/
Success: no issues found
```

### Code Quality

```bash
$ black --check src/omniforge/core/ src/omniforge/tools/executor.py
All done! ✨ 🍰 ✨

$ ruff check src/omniforge/core/ src/omniforge/tools/executor.py
All checks passed!
```

## Future Enhancements

### Potential Protocol Extensions

```python
class ChainRecorder(Protocol):
    """Extended protocol with additional capabilities."""

    def add_step(self, step: "ReasoningStep") -> None:
        """Add a step to the chain."""
        ...

    def get_metrics(self) -> "ChainMetrics":
        """Get current chain metrics."""
        ...

    def get_step_count(self) -> int:
        """Get total number of steps."""
        ...
```

### Alternative Implementations

```python
class DistributedChainRecorder:
    """Chain recorder that distributes steps across multiple storage backends."""

    def add_step(self, step: ReasoningStep) -> None:
        # Distribute to Kafka, Redis, etc.
        ...


class StreamingChainRecorder:
    """Chain recorder that streams steps to clients via WebSocket."""

    def add_step(self, step: ReasoningStep) -> None:
        # Stream to connected clients
        ...
```

## Related Documentation

- [REFACTORING-COMPLETED.md](../REFACTORING-COMPLETED.md) - Implementation details
- [REFACTORING-RECOMMENDATIONS.md](../REFACTORING-RECOMMENDATIONS.md) - Full refactoring plan
- [class-dependencies-lld.md](../class-dependencies-lld.md) - Low-level design
- [dependency-graph-visual.md](../dependency-graph-visual.md) - Visual diagrams

## Conclusion

The `ChainRecorder` protocol successfully eliminates the critical cross-boundary dependency while:
- ✅ Maintaining 100% backward compatibility
- ✅ Improving testability and flexibility
- ✅ Following SOLID principles
- ✅ Achieving zero runtime overhead
- ✅ Preserving full type safety

This pattern serves as a template for future refactoring work, particularly the extraction of `SkillManager` (Priority 2).

---

**Last Updated:** 2026-01-14
**Author:** Architectural Refactoring Team
**Status:** Production Ready
