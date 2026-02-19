---
name: skill-with-supporting-files
description: A skill for testing context loading
execution-mode: autonomous
allowed-tools:
  - read
  - write
max-iterations: 10
priority: 5
---

# Skill With Supporting Files

This skill tests loading of supporting files.

## Task

$ARGUMENTS

## Supporting Files

This skill has a reference file: `reference.md`

Use the `read` tool to access the reference file for additional context.

## Instructions

1. Read the reference.md file in this skill's directory
2. Use the information from the reference file
3. Complete the task using the supporting context
