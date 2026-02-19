# OmniForge Coding Guidelines

**Last Updated:** 2026-01-03

These guidelines ensure code quality, consistency, and alignment with OmniForge's core principles: simplicity, reliability, and enterprise-readiness.

## Core Principles

All code decisions should align with the [Product Vision](specs/product-vision.md):

- **Simplicity over flexibility** - Write clear, straightforward code over clever abstractions
- **Reliability over speed** - Correctness and maintainability matter more than optimization
- **Enterprise-ready** - Consider security, scalability, and auditability in every design

## Python Version & Dependencies

- **Minimum Python version**: 3.9+
- Add dependencies sparingly - evaluate necessity against simplicity principle
- Pin major versions in `pyproject.toml` for stability

## Code Style

### Formatting

Code formatting is automated and enforced:

```bash
# Auto-format all code
black .

# Check formatting without changes
black . --check
```

**Configuration:**
- Line length: 100 characters
- Target: Python 3.9+
- Tool: Black (see `pyproject.toml`)

### Linting

```bash
# Run linter
ruff check .

# Auto-fix issues where possible
ruff check . --fix
```

**Rules enforced:**
- E: PEP 8 errors
- F: Pyflakes (logic errors)
- I: Import sorting
- N: Naming conventions
- W: PEP 8 warnings

### Type Annotations

**All functions must have type annotations** (enforced by mypy):

```python
# ✅ Good
def create_agent(name: str, config: AgentConfig) -> Agent:
    """Create a new agent with the given configuration."""
    return Agent(name=name, config=config)

# ❌ Bad - missing types
def create_agent(name, config):
    return Agent(name=name, config=config)
```

Run type checking:
```bash
mypy src/
```

**Type hints best practices:**
- Use built-in generics (`list[str]`, not `List[str]`) for Python 3.9+
- Import from `typing` only when necessary (`Protocol`, `TypeVar`, etc.)
- Prefer concrete types over `Any`
- Use `Optional[T]` for nullable values

## Code Organization

### Project Structure

```
omniforge/
├── src/omniforge/          # Source code
│   ├── agents/             # Agent-related modules
│   ├── orchestration/      # Orchestration layer
│   ├── security/           # RBAC, auth, multi-tenancy
│   └── ...
├── tests/                  # Test files (mirrors src/)
├── specs/                  # Product specs and plans
└── pyproject.toml          # Project configuration
```

### Module Organization

- One class per file for major components
- Group related utilities in shared modules
- Keep modules focused and cohesive
- Each module should have well defined interface and implementation
- There should not be any circular dependencies
- Always follow SOLID Principles
- If there is circular depdencies please revist the architecture wand what needs to be refactored

### Imports

Organized automatically by ruff:
1. Standard library
2. Third-party packages
3. Local application imports

```python
# ✅ Good
import os
from pathlib import Path

import requests

from omniforge.agents import Agent
from omniforge.security import RBACManager
```

## Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions/methods**: `snake_case`
- **Constants**: `UPPER_CASE_WITH_UNDERSCORES`
- **Private members**: `_leading_underscore`

```python
# ✅ Good
class AgentOrchestrator:
    MAX_CONCURRENT_AGENTS = 100

    def __init__(self, config: OrchestratorConfig) -> None:
        self._running_agents: dict[str, Agent] = {}

    def start_agent(self, agent_id: str) -> None:
        """Start an agent by ID."""
        pass
```

## Documentation

### Docstrings

Use docstrings for all public modules, classes, and functions:

```python
def deploy_agent(agent_id: str, environment: str = "production") -> DeploymentResult:
    """Deploy an agent to the specified environment.

    Args:
        agent_id: Unique identifier for the agent
        environment: Target environment (default: "production")

    Returns:
        DeploymentResult containing status and deployment URL

    Raises:
        AgentNotFoundError: If agent_id does not exist
        DeploymentError: If deployment fails
    """
    pass
```

**When to document:**
- All public APIs (classes, functions, methods)
- Complex logic requiring explanation
- Non-obvious design decisions

**When NOT to document:**
- Self-evident code
- Private implementation details (use comments instead)

### Comments

Use comments sparingly - prefer self-documenting code:

```python
# ❌ Bad - obvious comment
# Increment counter
counter += 1

# ✅ Good - explains non-obvious business logic
# Retry failed agents after 30s to avoid cascading failures
retry_delay_seconds = 30
```

## Testing

### Test Coverage

- **Minimum coverage**: 80%
- Run with coverage by default: `pytest`
- Run without coverage: `pytest --no-cov`

### Test Structure

```python
# tests/test_agents.py
import pytest

from omniforge.agents import Agent, AgentConfig

class TestAgent:
    """Tests for Agent class."""

    def test_create_agent_with_valid_config(self) -> None:
        """Agent should initialize with valid configuration."""
        config = AgentConfig(name="test-agent")
        agent = Agent(config)

        assert agent.name == "test-agent"
        assert agent.status == "initialized"

    def test_create_agent_with_invalid_config_raises_error(self) -> None:
        """Agent creation should fail with invalid configuration."""
        with pytest.raises(ValueError, match="Invalid configuration"):
            Agent(AgentConfig(name=""))
```

### Test Guidelines

- **Arrange-Act-Assert** pattern
- Descriptive test names that explain behavior
- Use fixtures for shared setup
- Mock external dependencies (network, databases)

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_agents.py

# Run specific test
pytest tests/test_agents.py::TestAgent::test_create_agent_with_valid_config

# Run without coverage
pytest --no-cov
```

## Error Handling

### Custom Exceptions

Define domain-specific exceptions:

```python
# ✅ Good
class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass

class AgentNotFoundError(AgentError):
    """Raised when an agent cannot be found."""
    pass

class DeploymentError(AgentError):
    """Raised when agent deployment fails."""
    pass
```

### Exception Guidelines

- Catch specific exceptions, not broad `Exception`
- Let exceptions propagate unless you can handle them meaningfully
- Log exceptions with context before re-raising
- Use `raise ... from e` to preserve exception chains

```python
# ✅ Good
try:
    agent = agent_registry.get(agent_id)
except KeyError as e:
    logger.error(f"Agent {agent_id} not found in registry")
    raise AgentNotFoundError(f"Agent {agent_id} does not exist") from e

# ❌ Bad
try:
    agent = agent_registry.get(agent_id)
except Exception:
    pass  # Silent failure
```

## Security

### Input Validation

Always validate user input at system boundaries:

```python
def create_agent(name: str, user_id: str) -> Agent:
    """Create agent with validated inputs."""
    if not name or len(name) > 255:
        raise ValueError("Agent name must be 1-255 characters")

    if not is_valid_uuid(user_id):
        raise ValueError("Invalid user ID format")

    return Agent(name=name, owner=user_id)
```

### Secrets Management

- **Never** commit secrets, API keys, or credentials
- Use environment variables for configuration
- Document required environment variables in README
- Use `.env.example` for local development templates

### Dependency Security

- Regularly update dependencies
- Review security advisories
- Use `pip-audit` or similar tools in CI

## Git Workflow

### Branch Naming

- `feature/short-description` - New features
- `fix/short-description` - Bug fixes
- `docs/short-description` - Documentation updates
- `refactor/short-description` - Code refactoring

### Commit Messages

Follow conventional commits:

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build process, dependencies, tooling

**Examples:**
```
feat: add multi-agent orchestration support

Implements orchestration layer for coordinating multiple agents
with support for dependency management and parallel execution.

fix: prevent race condition in agent deployment

Adds locking mechanism to prevent concurrent deployments
of the same agent.

docs: update API documentation for AgentConfig
```

### Pull Requests

- Keep PRs focused and small
- Reference related issues
- Ensure CI passes (tests, linting, type checking)
- Request reviews from relevant team members

## Performance

### General Guidelines

- **Measure before optimizing** - profile to find real bottlenecks
- **Reliability first** - don't sacrifice correctness for speed
- Use appropriate data structures (sets for membership, dicts for lookups)
- Avoid premature optimization
- Dont do regex based parsing for chat and files, rely on llm based reasoning

### Async/Await


Use async for I/O-bound operations:

```python
async def deploy_agents(agent_ids: list[str]) -> list[DeploymentResult]:
    """Deploy multiple agents concurrently."""
    tasks = [deploy_agent(agent_id) for agent_id in agent_ids]
    return await asyncio.gather(*tasks)
```

## Code Review Checklist

Before submitting code for review, verify:

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black .`)
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy src/`)
- [ ] New code has tests (maintain 80%+ coverage)
- [ ] Public APIs have docstrings
- [ ] No secrets or credentials committed
- [ ] Code follows SOLID principles
- [ ] Changes align with product vision principles

## Resources

- [Product Vision](specs/product-vision.md)
- [Development Commands](CLAUDE.md#development-commands)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
