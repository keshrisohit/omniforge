"""Agent execution service.

Executes agents by loading and running their skills.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from omniforge.builder.models import AgentConfig, AgentExecution, ExecutionStatus
from omniforge.builder.repository import AgentConfigRepository, AgentExecutionRepository
from omniforge.builder.skill_generator import SkillMdGenerator
from omniforge.skills.parser import SkillParser


class AgentExecutor:
    """Executes agents by running their skills."""

    def __init__(
        self,
        skill_generator: SkillMdGenerator,
        skills_dir: Path,
    ) -> None:
        """Initialize executor.

        Args:
            skill_generator: Generator for creating SKILL.md files
            skills_dir: Directory where skills are stored
        """
        self.skill_generator = skill_generator
        self.skills_dir = skills_dir
        self.skill_parser = SkillParser()

    async def execute_agent(
        self,
        agent_config: AgentConfig,
        execution_repo: AgentExecutionRepository,
        trigger_type: str = "on_demand",
    ) -> AgentExecution:
        """Execute an agent by running its skills.

        Args:
            agent_config: Agent configuration to execute
            execution_repo: Repository for tracking execution
            trigger_type: How execution was triggered

        Returns:
            Execution record with results
        """
        # Create execution record
        started_at = datetime.now(timezone.utc)
        execution = AgentExecution(
            agent_id=agent_config.id or "unknown",
            tenant_id=agent_config.tenant_id,
            trigger_type=trigger_type,
            started_at=started_at,
            status=ExecutionStatus.RUNNING,
        )

        created_execution = await execution_repo.create(execution)

        try:
            # Execute skills in order
            skill_results = []
            for skill_ref in sorted(agent_config.skills, key=lambda s: s.order):
                skill_result = await self._execute_skill(
                    agent_config.tenant_id,
                    skill_ref.skill_id,
                    skill_ref.config,
                )

                skill_results.append(skill_result)

            # Update execution as successful
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            await execution_repo.update_status(
                created_execution.id or "",
                agent_config.tenant_id,
                status="success",
                completed_at=completed_at,
                duration_ms=duration_ms,
                output={"skill_results": skill_results},
            )

            return (
                await execution_repo.get_by_id(
                    created_execution.id or "", agent_config.tenant_id
                )
            ) or created_execution  # type: ignore

        except Exception as e:
            # Update execution as failed
            await execution_repo.update_status(
                created_execution.id or "",
                agent_config.tenant_id,
                status="failed",
                completed_at=datetime.now(timezone.utc),
                error=str(e),
            )

            return (
                await execution_repo.get_by_id(
                    created_execution.id or "", agent_config.tenant_id
                )
            ) or created_execution  # type: ignore

    async def _execute_skill(
        self,
        tenant_id: str,
        skill_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single skill.

        Args:
            tenant_id: Tenant context
            skill_id: Skill identifier
            config: Skill configuration

        Returns:
            Skill execution result

        Raises:
            FileNotFoundError: If skill file not found
            Exception: If skill execution fails
        """
        # Build skill path
        skill_path = self.skills_dir / tenant_id / "skills" / f"{skill_id}.md"

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_path}")

        # Parse skill
        skill = self.skill_parser.parse_full(skill_path, "custom")

        # For MVP, return simulated execution result
        # In production, this would use SkillTool to actually execute
        return {
            "skill_id": skill_id,
            "status": "success",
            "output": {
                "message": f"Skill {skill.metadata.name} executed successfully",
                "config": config,
            },
        }

    async def prepare_agent_skills(
        self,
        agent_config: AgentConfig,
        skill_requests: list[Any],
    ) -> None:
        """Prepare agent skills by generating SKILL.md files.

        Args:
            agent_config: Agent configuration
            skill_requests: List of SkillGenerationRequest objects
        """
        # Create skills directory for this tenant
        agent_skills_dir = self.skills_dir / agent_config.tenant_id / "skills"
        agent_skills_dir.mkdir(parents=True, exist_ok=True)

        # Generate SKILL.md files
        for skill_request in skill_requests:
            self.skill_generator.save(skill_request, agent_skills_dir)


class AgentExecutionService:
    """High-level service for agent execution with database integration."""

    def __init__(
        self,
        executor: AgentExecutor,
        agent_repo: AgentConfigRepository,
        execution_repo: AgentExecutionRepository,
    ) -> None:
        """Initialize execution service.

        Args:
            executor: Agent executor
            agent_repo: Agent configuration repository
            execution_repo: Execution repository
        """
        self.executor = executor
        self.agent_repo = agent_repo
        self.execution_repo = execution_repo

    async def execute_agent_by_id(
        self,
        agent_id: str,
        tenant_id: str,
        trigger_type: str = "on_demand",
    ) -> AgentExecution:
        """Execute an agent by ID.

        Args:
            agent_id: Agent ID to execute
            tenant_id: Tenant context
            trigger_type: How execution was triggered

        Returns:
            Execution record

        Raises:
            ValueError: If agent not found
        """
        # Load agent config
        agent_config = await self.agent_repo.get_by_id(agent_id, tenant_id)
        if not agent_config:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Execute agent
        return await self.executor.execute_agent(
            agent_config,
            self.execution_repo,
            trigger_type,
        )

    async def execute_agent_test(
        self,
        agent_config: AgentConfig,
        skill_requests: list[Any],
    ) -> dict[str, Any]:
        """Test execute an agent before deployment.

        Args:
            agent_config: Agent configuration
            skill_requests: Skill generation requests

        Returns:
            Test execution results
        """
        # Prepare skills
        await self.executor.prepare_agent_skills(agent_config, skill_requests)

        # Execute in test mode (don't save to execution log)
        try:
            skill_results = []
            for skill_ref in sorted(agent_config.skills, key=lambda s: s.order):
                result = await self.executor._execute_skill(
                    agent_config.tenant_id,
                    skill_ref.skill_id,
                    skill_ref.config,
                )
                skill_results.append(result)

            return {
                "status": "success",
                "skills_executed": len(skill_results),
                "results": skill_results,
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }
