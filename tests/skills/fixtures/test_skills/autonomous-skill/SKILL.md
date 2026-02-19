---
name: autonomous-skill
description: A skill for testing autonomous execution mode
execution-mode: autonomous
allowed-tools:
  - read
  - write
  - grep
max-iterations: 15
priority: 5
---

# Autonomous Skill

This skill explicitly tests autonomous execution mode with ReAct loop.

## Task

$ARGUMENTS

## Instructions

Use the ReAct pattern to complete this task:
1. Reason about what needs to be done
2. Act by using appropriate tools
3. Observe the results
4. Repeat until task completion

You have access to read, write, and grep tools.
