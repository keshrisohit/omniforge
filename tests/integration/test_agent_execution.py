"""Integration tests for agent execution via API.

Tests the complete agent execution flow including skill loading, execution,
and result validation.

TODO: These integration tests need to be rewritten to work with Phase 2's
OrchestrationEngine and sequential multi-skill execution. The old AgentExecutor
API has changed significantly. Phase 2 tests in tests/execution/orchestration/
cover similar functionality.

For now, these tests are skipped to avoid collection errors.
"""

import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.builder.executor import AgentExecutor, AgentExecutionService
from omniforge.builder.models import (
    AgentConfig,
    AgentExecution,
    AgentStatus,
    ExecutionStatus,
    TriggerType,
)
from omniforge.builder.repository import AgentConfigRepository, AgentExecutionRepository
from omniforge.builder.skill_generator import SkillMdGenerator


@pytest.fixture
async def repository(db_session: AsyncSession) -> AgentConfigRepository:
    """Create a repository for testing."""
    return AgentConfigRepository(db_session)


@pytest.fixture
async def execution_repo(db_session: AsyncSession) -> AgentExecutionRepository:
    """Create an execution repository for testing."""
    return AgentExecutionRepository(db_session)


@pytest.fixture
async def executor(tmp_path: Path) -> AgentExecutor:
    """Create an agent executor for testing."""
    from unittest.mock import MagicMock

    skill_generator = MagicMock(spec=SkillMdGenerator)
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return AgentExecutor(skill_generator, skills_dir)


@pytest.fixture
async def execution_service(
    executor: AgentExecutor,
    repository: AgentConfigRepository,
    execution_repo: AgentExecutionRepository,
) -> AgentExecutionService:
    """Create an agent execution service for testing."""
    return AgentExecutionService(executor, repository, execution_repo)


# Tests are disabled pending refactor for Phase 2 orchestration
# See tests/execution/orchestration/ for Phase 2 multi-skill execution tests
