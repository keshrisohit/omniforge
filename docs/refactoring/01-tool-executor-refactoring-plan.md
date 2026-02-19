# Refactoring Plan: ToolExecutor (SRP Violation)

## Current State Analysis

### File: `src/omniforge/tools/executor.py`

### Problem Summary
`ToolExecutor` violates Single Responsibility Principle by handling 5+ distinct responsibilities:

1. **Tool Execution** - Core tool invocation with timeout/retry logic
2. **Skill Management** - Skill activation/deactivation and stack management
3. **Rate Limiting** - Quota checking and enforcement
4. **Cost Tracking** - Recording execution costs
5. **Chain Integration** - Creating and recording reasoning chain steps

### Current Architecture (Lines 79-270)

```python
class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self._registry = registry
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker
        self._active_skills: dict[UUID, list[str]] = {}  # Skill stack management

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolCallContext,
        chain_recorder: Optional[ReasoningChain] = None,
    ) -> ToolResult:
        # Handles ALL 5 responsibilities in one method!
        # Lines 173-270: 97 lines of mixed concerns
```

### Impact Metrics
- **Cyclomatic Complexity**: 15+ (lines 173-270)
- **Dependencies**: 6 (registry, limiter, tracker, chain, skill stack, context)
- **Test Complexity**: Very High (requires mocking all dependencies)
- **Coupling**: Very High (referenced by ReasoningEngine, agents, tests)

---

## Refactoring Strategy

### Phase 1: Extract Skill Management (2-3 hours)

#### Step 1.1: Create SkillManager Class

**New File**: `src/omniforge/tools/skill_manager.py`

```python
"""Skill lifecycle and stack management."""

from typing import Dict, List, Optional
from uuid import UUID

from omniforge.tools.base import BaseTool, ToolCallContext
from omniforge.tools.errors import ToolExecutionError
from omniforge.tools.registry import ToolRegistry


class SkillManager:
    """Manages skill activation, deactivation, and execution stack.

    Responsibilities:
    - Track active skills per agent
    - Enforce skill activation before use
    - Manage skill execution stack (for nested skills)
    - Clean up skills on context exit
    """

    def __init__(self, registry: ToolRegistry) -> None:
        """Initialize skill manager.

        Args:
            registry: Tool registry for skill lookup
        """
        self._registry = registry
        self._active_skills: Dict[UUID, List[str]] = {}

    async def activate_skill(
        self,
        skill_name: str,
        context: ToolCallContext,
    ) -> None:
        """Activate a skill for use by an agent.

        Args:
            skill_name: Name of skill to activate
            context: Tool call context with agent ID

        Raises:
            ToolNotFoundError: If skill doesn't exist
        """
        # Get skill tool from registry (validates existence)
        skill_tool = self._registry.get(skill_name)

        # Initialize skill stack for agent if needed
        agent_id = context.agent_id
        if agent_id not in self._active_skills:
            self._active_skills[agent_id] = []

        # Add to active skills if not already active
        if skill_name not in self._active_skills[agent_id]:
            self._active_skills[agent_id].append(skill_name)

    async def deactivate_skill(
        self,
        skill_name: str,
        context: ToolCallContext,
    ) -> None:
        """Deactivate a skill.

        Args:
            skill_name: Name of skill to deactivate
            context: Tool call context with agent ID
        """
        agent_id = context.agent_id
        if agent_id in self._active_skills:
            if skill_name in self._active_skills[agent_id]:
                self._active_skills[agent_id].remove(skill_name)

    def is_skill_active(
        self,
        skill_name: str,
        agent_id: UUID,
    ) -> bool:
        """Check if skill is active for agent.

        Args:
            skill_name: Skill name to check
            agent_id: Agent ID

        Returns:
            True if skill is active
        """
        if agent_id not in self._active_skills:
            return False
        return skill_name in self._active_skills[agent_id]

    def validate_skill_access(
        self,
        tool: BaseTool,
        context: ToolCallContext,
    ) -> None:
        """Validate that skill tools are activated before use.

        Args:
            tool: Tool being executed
            context: Execution context

        Raises:
            ToolExecutionError: If skill not activated
        """
        # Only check skill tools
        if tool.definition.type.value != "skill":
            return

        skill_name = tool.definition.name
        if not self.is_skill_active(skill_name, context.agent_id):
            raise ToolExecutionError(
                tool_name=skill_name,
                message=f"Skill '{skill_name}' must be activated before use",
            )

    def cleanup_agent_skills(self, agent_id: UUID) -> None:
        """Remove all active skills for an agent.

        Args:
            agent_id: Agent ID to cleanup
        """
        if agent_id in self._active_skills:
            del self._active_skills[agent_id]

    def get_active_skills(self, agent_id: UUID) -> List[str]:
        """Get list of active skills for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of active skill names
        """
        return self._active_skills.get(agent_id, []).copy()
```

#### Step 1.2: Create Tests

**New File**: `tests/tools/test_skill_manager.py`

```python
"""Tests for SkillManager."""

import pytest
from uuid import uuid4

from omniforge.tools.base import ToolCallContext
from omniforge.tools.errors import ToolExecutionError, ToolNotFoundError
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.skill_manager import SkillManager

# Import mock skill tool for testing
from tests.tools.test_executor import MockSkillTool


@pytest.fixture
def registry():
    """Create registry with test skill."""
    reg = ToolRegistry()
    skill = MockSkillTool("test_skill")
    reg.register(skill)
    return reg


@pytest.fixture
def manager(registry):
    """Create skill manager."""
    return SkillManager(registry)


@pytest.fixture
def context():
    """Create test context."""
    return ToolCallContext(
        agent_id=uuid4(),
        tenant_id="test-tenant",
        user_id="test-user",
    )


class TestSkillManager:
    """Tests for SkillManager class."""

    async def test_activate_skill_success(self, manager, context):
        """Should activate skill successfully."""
        await manager.activate_skill("test_skill", context)

        assert manager.is_skill_active("test_skill", context.agent_id)
        assert "test_skill" in manager.get_active_skills(context.agent_id)

    async def test_activate_nonexistent_skill_raises_error(self, manager, context):
        """Should raise error for nonexistent skill."""
        with pytest.raises(ToolNotFoundError):
            await manager.activate_skill("nonexistent", context)

    async def test_deactivate_skill(self, manager, context):
        """Should deactivate active skill."""
        await manager.activate_skill("test_skill", context)
        await manager.deactivate_skill("test_skill", context)

        assert not manager.is_skill_active("test_skill", context.agent_id)

    async def test_deactivate_inactive_skill_is_safe(self, manager, context):
        """Deactivating inactive skill should not error."""
        # Should not raise
        await manager.deactivate_skill("test_skill", context)

    def test_validate_skill_access_success(self, manager, context, registry):
        """Should allow access to activated skill."""
        skill = registry.get("test_skill")

        # Activate skill
        manager._active_skills[context.agent_id] = ["test_skill"]

        # Should not raise
        manager.validate_skill_access(skill, context)

    def test_validate_skill_access_raises_for_inactive(self, manager, context, registry):
        """Should raise error for inactive skill."""
        skill = registry.get("test_skill")

        with pytest.raises(ToolExecutionError, match="must be activated"):
            manager.validate_skill_access(skill, context)

    def test_cleanup_agent_skills(self, manager, context):
        """Should cleanup all skills for agent."""
        manager._active_skills[context.agent_id] = ["skill1", "skill2"]

        manager.cleanup_agent_skills(context.agent_id)

        assert context.agent_id not in manager._active_skills
        assert manager.get_active_skills(context.agent_id) == []

    def test_get_active_skills_returns_copy(self, manager, context):
        """get_active_skills should return copy, not reference."""
        manager._active_skills[context.agent_id] = ["skill1"]

        skills = manager.get_active_skills(context.agent_id)
        skills.append("skill2")

        # Original should be unchanged
        assert manager.get_active_skills(context.agent_id) == ["skill1"]
```

---

### Phase 2: Extract Chain Integration (1-2 hours)

#### Step 2.1: Create ChainRecorder Class

**New File**: `src/omniforge/tools/chain_recorder.py`

```python
"""Chain integration for tool execution recording."""

from typing import Any, Dict, Optional
from uuid import UUID

from omniforge.agents.cot.chain import ReasoningChain
from omniforge.agents.cot.chain import (
    ReasoningStep,
    StepType,
    ThinkingStep,
    ToolCallStep,
    ToolResultStep,
)
from omniforge.tools.base import ToolCallContext, ToolDefinition, ToolResult


class ChainRecorder:
    """Records tool execution steps in reasoning chains.

    Responsibilities:
    - Create tool call steps
    - Create tool result steps
    - Add steps to reasoning chain
    - Format step metadata
    """

    @staticmethod
    def record_tool_call(
        chain: ReasoningChain,
        tool_definition: ToolDefinition,
        arguments: Dict[str, Any],
        context: ToolCallContext,
    ) -> UUID:
        """Record tool call in reasoning chain.

        Args:
            chain: Reasoning chain to record in
            tool_definition: Definition of tool being called
            arguments: Tool arguments
            context: Call context

        Returns:
            Step ID of created tool call step
        """
        step = ReasoningStep(
            type=StepType.TOOL_CALL,
            tool_call=ToolCallStep(
                tool_name=tool_definition.name,
                arguments=arguments,
                context={
                    "agent_id": str(context.agent_id),
                    "tenant_id": context.tenant_id,
                    "user_id": context.user_id,
                },
            ),
        )

        chain.add_step(step)
        return step.id

    @staticmethod
    def record_tool_result(
        chain: ReasoningChain,
        result: ToolResult,
        call_step_id: UUID,
    ) -> UUID:
        """Record tool result in reasoning chain.

        Args:
            chain: Reasoning chain to record in
            result: Tool execution result
            call_step_id: ID of corresponding call step

        Returns:
            Step ID of created result step
        """
        step = ReasoningStep(
            type=StepType.TOOL_RESULT,
            tool_result=ToolResultStep(
                success=result.success,
                result=result.result,
                error=result.error,
                duration_ms=result.duration_ms,
                call_step_id=call_step_id,
            ),
        )

        chain.add_step(step)
        return step.id
```

---

### Phase 3: Extract Rate Limit Checking (1 hour)

#### Step 3.1: Create RateLimitChecker Class

**New File**: `src/omniforge/tools/rate_limit_checker.py`

```python
"""Rate limiting checks for tool execution."""

from typing import Optional

from omniforge.enterprise.rate_limiter import RateLimiter
from omniforge.tools.base import ToolCallContext
from omniforge.tools.errors import RateLimitExceededError


class RateLimitChecker:
    """Checks rate limits before tool execution.

    Responsibilities:
    - Check if tool execution allowed under quota
    - Raise appropriate errors when limit exceeded
    - Handle optional rate limiter (no-op when disabled)
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None) -> None:
        """Initialize rate limit checker.

        Args:
            rate_limiter: Optional rate limiter for quota enforcement
        """
        self._rate_limiter = rate_limiter

    async def check_rate_limit(
        self,
        tool_name: str,
        context: ToolCallContext,
    ) -> None:
        """Check if tool execution is allowed under rate limits.

        Args:
            tool_name: Name of tool being executed
            context: Execution context with tenant/user info

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        if self._rate_limiter is None:
            # No rate limiting configured - allow execution
            return

        allowed = await self._rate_limiter.check_limit(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            resource=f"tool:{tool_name}",
        )

        if not allowed:
            raise RateLimitExceededError(
                tool_name=tool_name,
                tenant_id=context.tenant_id,
                user_id=context.user_id,
            )
```

---

### Phase 4: Extract Cost Tracking (1 hour)

#### Step 4.1: Create CostRecorder Class

**New File**: `src/omniforge/tools/cost_recorder.py`

```python
"""Cost tracking for tool execution."""

from typing import Optional

from omniforge.enterprise.cost_tracker import CostTracker
from omniforge.tools.base import ToolCallContext, ToolResult


class CostRecorder:
    """Records execution costs for tool calls.

    Responsibilities:
    - Record cost when tool execution completes
    - Handle optional cost tracker (no-op when disabled)
    - Extract cost metadata from results
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None) -> None:
        """Initialize cost recorder.

        Args:
            cost_tracker: Optional cost tracker for recording
        """
        self._cost_tracker = cost_tracker

    async def record_cost(
        self,
        tool_name: str,
        result: ToolResult,
        context: ToolCallContext,
    ) -> None:
        """Record cost of tool execution.

        Args:
            tool_name: Name of tool executed
            result: Tool execution result with cost metadata
            context: Execution context
        """
        if self._cost_tracker is None:
            # No cost tracking configured
            return

        # Extract cost from result metadata if available
        cost = result.metadata.get("cost", 0.0) if result.metadata else 0.0

        if cost > 0:
            await self._cost_tracker.record_cost(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                agent_id=context.agent_id,
                resource=f"tool:{tool_name}",
                cost=cost,
            )
```

---

### Phase 5: Refactor Core ToolExecutor (2-3 hours)

#### Step 5.1: Update ToolExecutor to Use Components

**Modified File**: `src/omniforge/tools/executor.py`

```python
"""Simplified tool executor using component composition."""

from typing import Any, Dict, Optional

from omniforge.agents.cot.chain import ReasoningChain
from omniforge.tools.base import BaseTool, ToolCallContext, ToolResult
from omniforge.tools.chain_recorder import ChainRecorder
from omniforge.tools.cost_recorder import CostRecorder
from omniforge.tools.rate_limit_checker import RateLimitChecker
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.skill_manager import SkillManager


class ToolExecutor:
    """Executes tools with retry, timeout, and validation.

    This is now a clean orchestrator that delegates responsibilities:
    - Skill management → SkillManager
    - Rate limiting → RateLimitChecker
    - Cost tracking → CostRecorder
    - Chain recording → ChainRecorder
    - Core execution → execute_with_retry()

    Responsibilities:
    - Coordinate tool execution flow
    - Handle retries and timeouts
    - Orchestrate component interactions
    """

    def __init__(
        self,
        registry: ToolRegistry,
        rate_limiter: Optional[RateLimiter] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        """Initialize tool executor with components.

        Args:
            registry: Tool registry for tool lookup
            rate_limiter: Optional rate limiter for quota enforcement
            cost_tracker: Optional cost tracker for recording usage
        """
        self._registry = registry

        # Component delegation
        self._skill_manager = SkillManager(registry)
        self._rate_checker = RateLimitChecker(rate_limiter)
        self._cost_recorder = CostRecorder(cost_tracker)
        self._chain_recorder = ChainRecorder()

    # Public API for skill management
    async def activate_skill(self, skill_name: str, context: ToolCallContext) -> None:
        """Activate a skill for use."""
        await self._skill_manager.activate_skill(skill_name, context)

    async def deactivate_skill(self, skill_name: str, context: ToolCallContext) -> None:
        """Deactivate a skill."""
        await self._skill_manager.deactivate_skill(skill_name, context)

    def get_active_skills(self, agent_id: UUID) -> list[str]:
        """Get active skills for an agent."""
        return self._skill_manager.get_active_skills(agent_id)

    # Core execution
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ToolCallContext,
        chain: Optional[ReasoningChain] = None,
    ) -> ToolResult:
        """Execute a tool with all orchestration.

        Flow:
        1. Get tool from registry
        2. Check rate limits
        3. Validate skill access
        4. Record call in chain (if provided)
        5. Execute with retry/timeout
        6. Record result in chain (if provided)
        7. Record cost
        8. Return result

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            context: Execution context
            chain: Optional reasoning chain for recording

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If tool doesn't exist
            RateLimitExceededError: If rate limit exceeded
            ToolExecutionError: If skill not activated
            ToolTimeoutError: If execution times out
        """
        # 1. Get tool
        tool = self._registry.get(tool_name)

        # 2. Check rate limits
        await self._rate_checker.check_rate_limit(tool_name, context)

        # 3. Validate skill access
        self._skill_manager.validate_skill_access(tool, context)

        # 4. Record call (if chain provided)
        call_step_id = None
        if chain:
            call_step_id = self._chain_recorder.record_tool_call(
                chain, tool.definition, arguments, context
            )

        # 5. Execute with retry/timeout
        result = await self._execute_with_retry(tool, arguments, context)

        # 6. Record result (if chain provided)
        if chain and call_step_id:
            self._chain_recorder.record_tool_result(chain, result, call_step_id)

        # 7. Record cost
        await self._cost_recorder.record_cost(tool_name, result, context)

        # 8. Return result
        return result

    async def _execute_with_retry(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        context: ToolCallContext,
    ) -> ToolResult:
        """Execute tool with retry and timeout logic.

        This method contains ONLY execution concerns:
        - Retry logic based on tool's retry config
        - Timeout enforcement
        - Error handling

        Args:
            tool: Tool to execute
            arguments: Tool arguments
            context: Execution context

        Returns:
            Tool execution result
        """
        # Implementation stays same as current lines 195-245
        # This is pure execution logic - single responsibility!
        ...
```

---

### Phase 6: Update Dependents (2-3 hours)

#### Step 6.1: Update ReasoningEngine

**File**: `src/omniforge/agents/cot/engine.py`

```python
# OLD (Line 279):
registry = self._executor._registry  # BAD: Accessing private member

# NEW:
# Add public method to ToolExecutor:
def get_registry(self) -> ToolRegistry:
    """Get the tool registry."""
    return self._registry

# Then in ReasoningEngine:
registry = self._executor.get_registry()  # GOOD: Public API
```

#### Step 6.2: Update Tests

```python
# tests/tools/test_executor.py

# Old tests still work - ToolExecutor interface unchanged
# Add new tests for components:

def test_skill_manager_integration():
    """Test that ToolExecutor uses SkillManager correctly."""

def test_rate_limit_integration():
    """Test that rate limiting is checked before execution."""

def test_cost_recording_integration():
    """Test that costs are recorded after execution."""
```

---

## Migration Path

### Step-by-Step Migration

1. **Create new component files** (Phases 1-4)
   - No breaking changes
   - New classes can be developed in parallel
   - Tests can be written before integration

2. **Update ToolExecutor to use components** (Phase 5)
   - Maintain existing public API
   - Internal refactoring only
   - Existing tests should still pass

3. **Update ReasoningEngine** (Phase 6)
   - Add public `get_registry()` method
   - Update line 279 to use public API
   - No breaking changes to external callers

4. **Deploy and monitor**
   - All existing code continues to work
   - Components can be tested independently
   - Performance impact should be negligible

### Backward Compatibility

**Maintained:**
- All public methods of ToolExecutor
- Method signatures unchanged
- Return types unchanged
- Exception types unchanged

**Added:**
- New `get_registry()` public method
- New component classes (internal)

**Removed:**
- None (fully backward compatible)

---

## Testing Strategy

### Unit Tests (Per Component)
- SkillManager: 10 tests
- ChainRecorder: 6 tests
- RateLimitChecker: 5 tests
- CostRecorder: 5 tests

### Integration Tests
- ToolExecutor with all components
- Error propagation through stack
- Chain recording end-to-end

### Performance Tests
- Execution time should be unchanged
- Memory overhead < 5%
- Component overhead negligible

---

## Success Metrics

### Code Quality
- ✅ Cyclomatic complexity < 10 per method
- ✅ Each class has 1-2 responsibilities
- ✅ Test coverage > 90%
- ✅ No private member access from external classes

### Maintainability
- ✅ Can add new skill behavior without modifying ToolExecutor
- ✅ Can swap rate limiting strategies
- ✅ Can add new cost tracking backends
- ✅ Components testable in isolation

### Performance
- ✅ Execution time unchanged (< 5% variance)
- ✅ Memory overhead < 5%
- ✅ No additional async overhead

---

## Timeline

- **Phase 1** (SkillManager): 2-3 hours
- **Phase 2** (ChainRecorder): 1-2 hours
- **Phase 3** (RateLimitChecker): 1 hour
- **Phase 4** (CostRecorder): 1 hour
- **Phase 5** (Refactor ToolExecutor): 2-3 hours
- **Phase 6** (Update dependents): 2-3 hours

**Total: 9-13 hours** (approximately 2 work days)

---

## Risk Assessment

### Low Risk
- New components don't affect existing code
- Public API unchanged
- Backward compatible

### Medium Risk
- ReasoningEngine update (line 279) needs careful testing
- Chain recording logic must maintain exact behavior

### Mitigation
- Write comprehensive tests before refactoring
- Use feature flag for new component usage
- Deploy to staging first
- Monitor performance metrics

---

## Next Steps

1. Review this plan with team
2. Create GitHub issue/epic for tracking
3. Implement Phase 1 (SkillManager) first
4. Get code review and merge
5. Continue with remaining phases

This refactoring will make ToolExecutor:
- ✅ Single responsibility (orchestration only)
- ✅ Easier to test (components mockable)
- ✅ More maintainable (concerns separated)
- ✅ More extensible (components swappable)
