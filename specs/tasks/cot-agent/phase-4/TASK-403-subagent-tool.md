# TASK-403: Implement Sub-Agent Delegation Tool

## Description

Create the sub-agent delegation tool that enables parent agents to delegate tasks to child agents via A2A protocol. This supports hierarchical agent orchestration with full reasoning chain visibility.

## Requirements

- Create `SubAgentTool` class extending BaseTool:
  - Constructor accepting:
    - agent_registry: AgentRegistry (lookup for available agents)
    - timeout_ms: int = 300000 (5 minutes default for sub-tasks)
  - Implement `definition` property:
    - name: "sub_agent"
    - type: ToolType.SUB_AGENT
    - Parameters: agent_id, task_description, context (optional dict)
  - Implement `execute()` method:
    - Look up agent by ID in registry
    - Create Task from description
    - Call agent.process_task() and collect results
    - Capture sub-agent's reasoning chain ID
    - Return result with:
      - Sub-agent's final output
      - Sub-chain ID for linking
      - Duration and status
  - Handle sub-agent failures gracefully
  - Support cycle detection (prevent A -> B -> A)

## Acceptance Criteria

- [ ] Sub-agent executes and returns results
- [ ] Sub-chain ID captured for parent chain linking
- [ ] Agent lookup works from registry
- [ ] Timeout enforced for sub-agent execution
- [ ] Cycle detection prevents infinite loops
- [ ] Errors from sub-agent returned as ToolResult error
- [ ] Integration test with mock agents

## Dependencies

- TASK-102 (for BaseTool, ToolDefinition)
- Existing AgentRegistry (or BaseAgent lookup mechanism)
- Existing Task models

## Files to Create/Modify

- `src/omniforge/tools/builtin/subagent.py` (new)
- `tests/tools/builtin/test_subagent.py` (new)

## Estimated Complexity

Complex (5-6 hours)

## Key Considerations

- A2A protocol compliance for cross-platform agents
- Cycle detection via context tracking
- Consider streaming sub-agent events to parent
