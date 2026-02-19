---
name: skill-with-variables
description: A skill for testing variable substitution
execution-mode: autonomous
allowed-tools:
  - read
  - write
max-iterations: 10
priority: 5
---

# Skill With Variables

This skill tests variable substitution in the preprocessing pipeline.

## Task

Process request: $ARGUMENTS

## Configuration

Skill directory: ${SKILL_DIR}

## Instructions

1. The $ARGUMENTS variable should contain the user's request
2. The ${SKILL_DIR} variable should point to this skill's directory
3. Use the variables to complete the task
