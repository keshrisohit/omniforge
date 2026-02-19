# TASK-205: Implement AutonomousCoTAgent with ReAct Pattern

## Description

Create the AutonomousCoTAgent class that implements fully autonomous reasoning using the ReAct pattern. Users provide a task description, and the agent autonomously decides actions, generates prompts, and determines completion.

## Requirements

- Create `MaxIterationsError` exception
- Create `AutonomousCoTAgent` class extending CoTAgent:
  - Class-level identity attribute (id, name, description, version)
  - Constructor parameters:
    - max_iterations: int = 10
    - reasoning_model: str = "claude-sonnet-4"
    - temperature: float = 0.0
    - **kwargs passed to CoTAgent
  - Store ReActParser instance
  - Implement `reason(task, engine)` method:
    - Build system prompt with available tools
    - Initialize conversation with system and user messages
    - Execute ReAct loop for max_iterations:
      - Add thinking step for iteration tracking
      - Call LLM via engine.call_llm() with conversation
      - Parse response with ReActParser
      - Add thought to chain if present
      - If is_final: add synthesis and return
      - If no action: raise ValueError
      - Execute action via engine.call_tool()
      - Append assistant/user messages to conversation
      - Handle tool execution errors gracefully
    - Raise MaxIterationsError if loop exhausts
  - Implement `_build_system_prompt(engine)` using prompts module
  - Implement `_format_tool_descriptions(tools)` helper

## Acceptance Criteria

- [ ] Agent completes simple single-tool tasks autonomously
- [ ] Agent completes multi-step tasks (multiple tool calls)
- [ ] Agent terminates on "Final Answer"
- [ ] Agent terminates on max_iterations with MaxIterationsError
- [ ] Tool execution errors captured as observations, not crashes
- [ ] Conversation history maintained correctly across iterations
- [ ] Thinking steps logged for each iteration
- [ ] Integration test with mocked LLM and tools

## Dependencies

- TASK-202 (for CoTAgent base class)
- TASK-201 (for ReasoningEngine)
- TASK-203 (for ReActParser)
- TASK-204 (for prompts)

## Files to Create/Modify

- `src/omniforge/agents/cot/autonomous.py` (new)
- `tests/agents/cot/test_autonomous.py` (new)

## Estimated Complexity

Complex (6-8 hours)

## Key Considerations

- Use temperature=0.0 for deterministic reasoning
- Conversation format: [{"role": "system/user/assistant", "content": "..."}]
- Observation format: "Observation: {tool_result or error}"
- Test with various mock scenarios (success, failure, multi-step)
