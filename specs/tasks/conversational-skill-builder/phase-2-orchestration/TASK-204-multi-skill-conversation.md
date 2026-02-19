# TASK-204: Enhanced Conversation Flows for Multi-Skill

**Phase**: 2 (Multi-Skill)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-103 (Conversation Manager), TASK-201 (Sequential Orchestration)
**Priority**: P0

## Objective

Extend the ConversationManager to support creating agents with multiple skills. The chatbot should intelligently determine skill composition and guide users through configuring skill order and data flow.

## Requirements

- Extend `AgentGenerator.determine_skills_needed()` for multi-skill analysis
- Add conversation flows for skill composition decisions
- Implement public skill suggestion during conversation (integrate with TASK-203)
- Add skill ordering discussion when multiple skills detected
- Create conversation prompts for data flow configuration
- Support mixing public and custom skills in single agent

## Implementation Notes

- Reference product spec "Agent Orchestration Intelligence" section
- Chatbot explains orchestration in plain language (no "sequential" jargon)
- Example: "I'll create an agent that: 1. Generates report from Notion 2. Posts to Slack"
- User can accept suggested composition or modify
- LLM determines if user request needs 1 skill or multiple

## Acceptance Criteria

- [ ] AgentGenerator detects when request needs multiple skills
- [ ] Conversation explains multi-skill flow in plain language
- [ ] User can accept or modify suggested skill composition
- [ ] Public skill suggestions integrated into conversation
- [ ] Skill ordering captured in SkillReference.order
- [ ] Mixed public+custom skill agents work correctly
- [ ] Conversation handles user changing their mind about composition
- [ ] 80%+ test coverage for multi-skill conversation paths

## Files to Create/Modify

- `src/omniforge/builder/generation/agent_generator.py` - Extend for multi-skill
- `src/omniforge/builder/conversation/manager.py` - Multi-skill conversation flows
- `src/omniforge/builder/conversation/prompts.py` - Multi-skill prompts
- `src/omniforge/builder/conversation/skill_suggestion.py` - Public skill integration
- `tests/builder/generation/test_agent_generator.py` - Multi-skill detection tests
- `tests/builder/conversation/test_multi_skill.py` - Multi-skill flow tests
