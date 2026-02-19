# TASK-107: CLI Commands for Agent Management

**Phase**: 1 (MVP)
**Estimated Effort**: 6 hours
**Dependencies**: TASK-105
**Priority**: P1

## Objective

Create CLI commands for managing agents from the command line. This enables developers to list, run, and test agents without using the web interface.

## Requirements

- Create `omniforge agent list` command to list all agents
- Create `omniforge agent run <agent_id>` command for manual execution
- Create `omniforge agent test <agent_id> --dry-run` for testing
- Create `omniforge agent status <agent_id>` for execution history
- Support JSON and table output formats
- Add `--tenant` flag for multi-tenant operation

## Implementation Notes

- Use Click or Typer for CLI framework (check existing CLI patterns)
- Reuse repository and execution service from previous tasks
- Format output with rich tables for readability
- Support piping JSON output to other tools
- Follow existing CLI patterns if any exist in the codebase

## Acceptance Criteria

- [ ] `omniforge agent list` displays agents in table format
- [ ] `omniforge agent list --format json` outputs JSON
- [ ] `omniforge agent run <id>` executes agent and displays result
- [ ] `omniforge agent test <id> --dry-run` runs without real API calls
- [ ] `omniforge agent status <id>` shows last 10 executions
- [ ] `--tenant` flag filters by tenant ID
- [ ] Help text is clear and complete for all commands
- [ ] Unit tests cover CLI argument parsing

## Files to Create/Modify

- `src/omniforge/cli/__init__.py` - CLI package init (create if needed)
- `src/omniforge/cli/agent.py` - Agent management commands
- `src/omniforge/cli/main.py` - Main CLI entry point (extend if exists)
- `pyproject.toml` - Add CLI entry point (extend existing)
- `tests/cli/__init__.py` - Test package
- `tests/cli/test_agent_commands.py` - CLI tests
