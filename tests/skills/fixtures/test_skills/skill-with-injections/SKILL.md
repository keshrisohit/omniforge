---
name: skill-with-injections
description: A skill for testing dynamic injections
execution-mode: autonomous
allowed-tools:
  - read
  - write
max-iterations: 10
priority: 5
---

# Skill With Dynamic Injections

This skill tests dynamic content injection.

## Task

$ARGUMENTS

## Current Information

Current date: !`date +%Y-%m-%d`

## Instructions

Use the injected date information to complete the task.
The date should be dynamically injected at execution time.
