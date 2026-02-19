---
name: flaky-skill
description: A skill for testing error recovery
execution-mode: autonomous
allowed-tools:
  - read
  - write
  - flaky_tool
max-iterations: 15
max-retries-per-tool: 3
priority: 5
---

# Flaky Skill

This skill tests error recovery with retries.

## Task

$ARGUMENTS

## Instructions

Use the flaky_tool which may fail initially but should succeed on retry.
Keep trying until the task completes successfully.
