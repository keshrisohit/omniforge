# TASK-106: Implement Reasoning-Specific SSE Events

## Description

Create the event types for streaming reasoning chain updates to clients via SSE. These events extend the base task events to support real-time visibility into agent reasoning.

## Requirements

- Create event classes extending existing BaseTaskEvent:
  - `ChainStartedEvent` with chain_id
  - `ReasoningStepEvent` with chain_id and step (ReasoningStep)
  - `ChainCompletedEvent` with chain_id and metrics (ChainMetrics)
  - `ChainFailedEvent` with chain_id, error_code, error_message
- All events should include:
  - task_id (from base)
  - timestamp
  - Literal type field for discriminated unions
- Events must be JSON serializable for SSE

## Acceptance Criteria

- [ ] All event types defined with proper Pydantic models
- [ ] Events serialize to JSON correctly
- [ ] Type field enables discriminated union pattern
- [ ] Events compatible with existing SSE streaming infrastructure
- [ ] ReasoningStepEvent correctly embeds ReasoningStep
- [ ] Unit tests verify serialization/deserialization

## Dependencies

- TASK-101 (for ReasoningStep, ChainMetrics)
- Existing agents/events.py (BaseTaskEvent)

## Files to Create/Modify

- `src/omniforge/agents/cot/events.py` (new)
- `tests/agents/cot/test_events.py` (new)

## Estimated Complexity

Simple (2-3 hours)

## Key Considerations

- Follow existing event patterns in agents/events.py
- Use Literal types for discriminated unions
- Ensure compatibility with existing SSE formatter
