---
name: complex-skill
description: A complex skill for testing iteration limits
execution-mode: autonomous
allowed-tools:
  - read
  - write
  - grep
  - bash
max-iterations: 5
priority: 5
---

# Complex Skill

This skill tests max iteration enforcement.

## Task

$ARGUMENTS

## Instructions

This is a complex task that requires multiple iterations.
Continue working until you complete the task or reach the iteration limit.

Note: For testing purposes, this skill has a low max-iterations value (5).
