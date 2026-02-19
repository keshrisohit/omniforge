---
name: forked-skill
description: A skill for testing forked context (sub-agent spawning)
execution-mode: autonomous
context: fork
allowed-tools:
  - read
  - write
  - grep
max-iterations: 10
priority: 5
---

# Forked Skill

This skill tests sub-agent spawning with forked context.

## Task

$ARGUMENTS

## Instructions

This skill runs in a forked context, meaning it spawns a sub-agent
with its own isolated execution environment.

The sub-agent has:
- Reduced iteration budget
- Isolated context
- Parent task tracking

Use the available tools to complete the task.
