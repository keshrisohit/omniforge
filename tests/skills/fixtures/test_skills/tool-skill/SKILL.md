---
name: tool-skill
description: A skill that uses tools for testing tool execution
execution-mode: autonomous
allowed-tools:
  - read
  - write
  - grep
max-iterations: 10
priority: 5
---

# Tool Skill

This skill tests tool usage within autonomous execution.

## Task

$ARGUMENTS

## Instructions

You should use the available tools to complete the task:
- Use `read` to read files
- Use `write` to write results
- Use `grep` to search content

Complete the task step by step using the tools available to you.
