"""Repository layer for database operations.

Provides async CRUD operations for AgentConfig, Credential, AgentExecution,
and PublicSkill with built-in tenant isolation.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omniforge.builder.models import (
    AgentConfig,
    AgentExecution,
    Credential,
    PublicSkill,
)
from omniforge.builder.models.orm import (
    AgentConfigModel,
    AgentExecutionModel,
    CredentialModel,
    PublicSkillModel,
)


class AgentConfigRepository:
    """Repository for AgentConfig CRUD operations with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(self, config: AgentConfig) -> AgentConfig:
        """Create a new agent configuration.

        Args:
            config: AgentConfig to create

        Returns:
            Created AgentConfig with generated ID and timestamps
        """
        model = AgentConfigModel(
            tenant_id=config.tenant_id,
            name=config.name,
            description=config.description,
            status=config.status.value,
            trigger=config.trigger.value,
            schedule=config.schedule,
            skills_json=json.dumps([skill.model_dump() for skill in config.skills]),
            integrations_json=json.dumps(config.integrations),
            sharing_level=config.sharing_level.value,
            created_by=config.created_by,
        )

        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        return self._to_pydantic(model)

    async def get_by_id(self, agent_id: str, tenant_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID with tenant isolation.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID for isolation

        Returns:
            AgentConfig if found and belongs to tenant, None otherwise
        """
        result = await self.session.execute(
            select(AgentConfigModel).where(
                and_(
                    AgentConfigModel.id == agent_id,
                    AgentConfigModel.tenant_id == tenant_id,
                )
            )
        )
        model = result.scalar_one_or_none()
        return self._to_pydantic(model) if model else None

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentConfig]:
        """List agent configurations for a tenant.

        Args:
            tenant_id: Tenant ID
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of AgentConfig objects
        """
        query = select(AgentConfigModel).where(AgentConfigModel.tenant_id == tenant_id)

        if status:
            query = query.where(AgentConfigModel.status == status)

        query = query.limit(limit).offset(offset).order_by(AgentConfigModel.created_at.desc())

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_pydantic(model) for model in models]

    async def update(self, config: AgentConfig) -> AgentConfig:
        """Update an existing agent configuration.

        Args:
            config: AgentConfig with updated values

        Returns:
            Updated AgentConfig

        Raises:
            ValueError: If agent not found or doesn't belong to tenant
        """
        if not config.id:
            raise ValueError("Cannot update agent without ID")

        await self.session.execute(
            update(AgentConfigModel)
            .where(
                and_(
                    AgentConfigModel.id == config.id,
                    AgentConfigModel.tenant_id == config.tenant_id,
                )
            )
            .values(
                name=config.name,
                description=config.description,
                status=config.status.value,
                trigger=config.trigger.value,
                schedule=config.schedule,
                skills_json=json.dumps([skill.model_dump() for skill in config.skills]),
                integrations_json=json.dumps(config.integrations),
                sharing_level=config.sharing_level.value,
                updated_at=datetime.now(timezone.utc),
            )
        )

        await self.session.flush()

        # Fetch updated model
        updated = await self.get_by_id(config.id, config.tenant_id)
        if not updated:
            raise ValueError(f"Agent {config.id} not found after update")

        return updated

    async def delete(self, agent_id: str, tenant_id: str) -> bool:
        """Delete an agent configuration.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID for isolation

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(AgentConfigModel).where(
                and_(
                    AgentConfigModel.id == agent_id,
                    AgentConfigModel.tenant_id == tenant_id,
                )
            )
        )

        await self.session.flush()

        return result.rowcount > 0  # type: ignore

    async def list_scheduled_agents(
        self,
        tenant_id: Optional[str] = None,
    ) -> list[AgentConfig]:
        """List all scheduled agents that are active.

        Args:
            tenant_id: Optional tenant ID filter (None for all tenants)

        Returns:
            List of AgentConfig objects with trigger=SCHEDULED and status=ACTIVE
        """
        query = select(AgentConfigModel).where(
            and_(
                AgentConfigModel.trigger == "scheduled",
                AgentConfigModel.status == "active",
            )
        )

        if tenant_id:
            query = query.where(AgentConfigModel.tenant_id == tenant_id)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_pydantic(model) for model in models]

    def _to_pydantic(self, model: AgentConfigModel) -> AgentConfig:
        """Convert ORM model to Pydantic model.

        Args:
            model: AgentConfigModel instance

        Returns:
            AgentConfig instance
        """
        data = model.to_dict()
        return AgentConfig(**data)


class CredentialRepository:
    """Repository for Credential CRUD operations with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(self, credential: Credential, encrypted_data: str) -> Credential:
        """Create a new credential.

        Args:
            credential: Credential metadata
            encrypted_data: Pre-encrypted credential data

        Returns:
            Created Credential with generated ID and timestamps
        """
        model = CredentialModel(
            tenant_id=credential.tenant_id,
            integration_type=credential.integration_type.value,
            integration_name=credential.integration_name,
            encrypted_credentials=encrypted_data,
        )

        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        return self._to_pydantic(model)

    async def get_by_id(
        self, credential_id: str, tenant_id: str
    ) -> Optional[tuple[Credential, str]]:
        """Get credential by ID with tenant isolation.

        Args:
            credential_id: Credential ID
            tenant_id: Tenant ID for isolation

        Returns:
            Tuple of (Credential, encrypted_data) if found, None otherwise
        """
        result = await self.session.execute(
            select(CredentialModel).where(
                and_(
                    CredentialModel.id == credential_id,
                    CredentialModel.tenant_id == tenant_id,
                )
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return (self._to_pydantic(model), model.encrypted_credentials)

    async def list_by_tenant(
        self,
        tenant_id: str,
        integration_type: Optional[str] = None,
    ) -> list[Credential]:
        """List credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            integration_type: Optional integration type filter

        Returns:
            List of Credential objects (without encrypted data)
        """
        query = select(CredentialModel).where(CredentialModel.tenant_id == tenant_id)

        if integration_type:
            query = query.where(CredentialModel.integration_type == integration_type)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_pydantic(model) for model in models]

    async def update_last_used(self, credential_id: str, tenant_id: str) -> None:
        """Update last_used_at timestamp.

        Args:
            credential_id: Credential ID
            tenant_id: Tenant ID for isolation
        """
        await self.session.execute(
            update(CredentialModel)
            .where(
                and_(
                    CredentialModel.id == credential_id,
                    CredentialModel.tenant_id == tenant_id,
                )
            )
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.session.flush()

    async def delete(self, credential_id: str, tenant_id: str) -> bool:
        """Delete a credential.

        Args:
            credential_id: Credential ID
            tenant_id: Tenant ID for isolation

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(CredentialModel).where(
                and_(
                    CredentialModel.id == credential_id,
                    CredentialModel.tenant_id == tenant_id,
                )
            )
        )

        await self.session.flush()

        return result.rowcount > 0  # type: ignore

    def _to_pydantic(self, model: CredentialModel) -> Credential:
        """Convert ORM model to Pydantic model (without decrypted credentials).

        Args:
            model: CredentialModel instance

        Returns:
            Credential instance with empty credentials dict
        """
        data = model.to_dict()
        data["credentials"] = {}  # Don't expose encrypted data
        return Credential(**data)


class AgentExecutionRepository:
    """Repository for AgentExecution CRUD operations with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(self, execution: AgentExecution) -> AgentExecution:
        """Create a new agent execution log.

        Args:
            execution: AgentExecution to create

        Returns:
            Created AgentExecution with generated ID
        """
        model = AgentExecutionModel(
            agent_id=execution.agent_id,
            tenant_id=execution.tenant_id,
            status=execution.status.value,
            trigger_type=execution.trigger_type,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            duration_ms=execution.duration_ms,
            output_json=json.dumps(execution.output) if execution.output else None,
            error=execution.error,
            skill_executions_json=json.dumps(execution.skill_executions),
            metadata_json=json.dumps(execution.metadata),
        )

        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        return self._to_pydantic(model)

    async def get_by_id(self, execution_id: str, tenant_id: str) -> Optional[AgentExecution]:
        """Get execution by ID with tenant isolation.

        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID for isolation

        Returns:
            AgentExecution if found, None otherwise
        """
        result = await self.session.execute(
            select(AgentExecutionModel).where(
                and_(
                    AgentExecutionModel.id == execution_id,
                    AgentExecutionModel.tenant_id == tenant_id,
                )
            )
        )
        model = result.scalar_one_or_none()
        return self._to_pydantic(model) if model else None

    async def list_by_agent(
        self,
        agent_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentExecution]:
        """List executions for an agent.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID for isolation
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of AgentExecution objects
        """
        result = await self.session.execute(
            select(AgentExecutionModel)
            .where(
                and_(
                    AgentExecutionModel.agent_id == agent_id,
                    AgentExecutionModel.tenant_id == tenant_id,
                )
            )
            .limit(limit)
            .offset(offset)
            .order_by(AgentExecutionModel.started_at.desc())
        )

        models = result.scalars().all()
        return [self._to_pydantic(model) for model in models]

    async def update_status(
        self,
        execution_id: str,
        tenant_id: str,
        status: str,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        output: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> Optional[AgentExecution]:
        """Update execution status and completion details.

        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID for isolation
            status: New status
            completed_at: Completion timestamp
            duration_ms: Execution duration
            output: Execution output
            error: Error message if failed

        Returns:
            Updated AgentExecution if found, None otherwise
        """
        values = {"status": status}
        if completed_at:
            values["completed_at"] = completed_at
        if duration_ms is not None:
            values["duration_ms"] = duration_ms
        if output is not None:
            values["output_json"] = json.dumps(output)
        if error is not None:
            values["error"] = error

        await self.session.execute(
            update(AgentExecutionModel)
            .where(
                and_(
                    AgentExecutionModel.id == execution_id,
                    AgentExecutionModel.tenant_id == tenant_id,
                )
            )
            .values(**values)
        )

        await self.session.flush()

        return await self.get_by_id(execution_id, tenant_id)

    def _to_pydantic(self, model: AgentExecutionModel) -> AgentExecution:
        """Convert ORM model to Pydantic model.

        Args:
            model: AgentExecutionModel instance

        Returns:
            AgentExecution instance
        """
        data = model.to_dict()
        return AgentExecution(**data)


class PublicSkillRepository:
    """Repository for PublicSkill CRUD and discovery operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(self, skill: PublicSkill) -> PublicSkill:
        """Create a new public skill.

        Args:
            skill: PublicSkill to create

        Returns:
            Created PublicSkill with timestamps

        Raises:
            IntegrityError: If skill with same name and version already exists
        """
        model = PublicSkillModel(
            id=skill.id,
            name=skill.name,
            version=skill.version,
            description=skill.description,
            content=skill.content,
            author_id=skill.author_id,
            tags_json=json.dumps(skill.tags),
            integrations_json=json.dumps(skill.integrations),
            usage_count=skill.usage_count,
            rating_avg=skill.rating_avg,
            status=skill.status.value,
        )

        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        return self._to_pydantic(model)

    async def get_by_id(self, skill_id: str) -> Optional[PublicSkill]:
        """Get public skill by ID.

        Args:
            skill_id: Skill ID

        Returns:
            PublicSkill if found, None otherwise
        """
        result = await self.session.execute(
            select(PublicSkillModel).where(PublicSkillModel.id == skill_id)
        )
        model = result.scalar_one_or_none()
        return self._to_pydantic(model) if model else None

    async def get_by_name(self, name: str, version: Optional[str] = None) -> Optional[PublicSkill]:
        """Get public skill by name and optional version.

        Args:
            name: Skill name
            version: Optional version (if None, returns latest version)

        Returns:
            PublicSkill if found, None otherwise
        """
        if version:
            # Get specific version
            result = await self.session.execute(
                select(PublicSkillModel).where(
                    and_(
                        PublicSkillModel.name == name,
                        PublicSkillModel.version == version,
                    )
                )
            )
            model = result.scalar_one_or_none()
        else:
            # Get latest version
            result = await self.session.execute(
                select(PublicSkillModel)
                .where(PublicSkillModel.name == name)
                .order_by(PublicSkillModel.version.desc())  # type: ignore
            )
            model = result.first()
            if model:
                model = model[0]

        return self._to_pydantic(model) if model else None

    async def get_versions(self, name: str, status: str = "approved") -> list[str]:
        """Get all versions for a skill name.

        Args:
            name: Skill name
            status: Filter by status (default: approved)

        Returns:
            List of version strings sorted in descending order
        """
        result = await self.session.execute(
            select(PublicSkillModel.version)
            .where(
                and_(
                    PublicSkillModel.name == name,
                    PublicSkillModel.status == status,
                )
            )
            .order_by(PublicSkillModel.version.desc())  # type: ignore
        )
        versions = result.scalars().all()
        return list(versions)

    async def search(
        self,
        keyword: Optional[str] = None,
        tags: Optional[list[str]] = None,
        status: str = "approved",
        limit: int = 20,
        offset: int = 0,
    ) -> list[PublicSkill]:
        """Search public skills by keyword and filters.

        Performs full-text search on name, description, and tags.

        Args:
            keyword: Search term for name/description/tags
            tags: Filter by specific tags (OR condition)
            status: Filter by status (default: approved)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching PublicSkill objects ordered by usage_count DESC
        """
        query = select(PublicSkillModel).where(PublicSkillModel.status == status)

        # Full-text search on name, description
        if keyword:
            keyword_lower = keyword.lower()
            query = query.where(
                or_(
                    PublicSkillModel.name.ilike(f"%{keyword_lower}%"),  # type: ignore
                    PublicSkillModel.description.ilike(f"%{keyword_lower}%"),  # type: ignore
                )
            )

        # Filter by tags (OR condition)
        if tags:
            # For JSON column, we need to check if any tag is in the list
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(
                    PublicSkillModel.tags_json.contains(tag.lower())  # type: ignore
                )
            query = query.where(or_(*tag_conditions))

        # Order by popularity
        query = query.order_by(PublicSkillModel.usage_count.desc())  # type: ignore
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_pydantic(model) for model in models]

    async def get_by_integration(
        self,
        integration: str,
        status: str = "approved",
        limit: int = 20,
    ) -> list[PublicSkill]:
        """Get public skills that use a specific integration.

        Args:
            integration: Integration type (e.g., "notion", "slack")
            status: Filter by status (default: approved)
            limit: Maximum number of results

        Returns:
            List of PublicSkill objects ordered by usage_count DESC
        """
        integration_lower = integration.lower()

        query = (
            select(PublicSkillModel)
            .where(
                and_(
                    PublicSkillModel.status == status,
                    PublicSkillModel.integrations_json.contains(integration_lower),  # type: ignore
                )
            )
            .order_by(PublicSkillModel.usage_count.desc())  # type: ignore
            .limit(limit)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_pydantic(model) for model in models]

    async def get_top_skills(
        self,
        limit: int = 10,
        status: str = "approved",
    ) -> list[PublicSkill]:
        """Get top skills by usage count.

        Args:
            limit: Maximum number of results
            status: Filter by status (default: approved)

        Returns:
            List of PublicSkill objects ordered by usage_count DESC
        """
        query = (
            select(PublicSkillModel)
            .where(PublicSkillModel.status == status)
            .order_by(PublicSkillModel.usage_count.desc())  # type: ignore
            .limit(limit)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_pydantic(model) for model in models]

    async def increment_usage_count(
        self, name: str, version: Optional[str] = None
    ) -> Optional[PublicSkill]:
        """Increment usage count when skill is added to an agent.

        Args:
            name: Skill name
            version: Optional version (if None, increments latest version)

        Returns:
            Updated PublicSkill if found, None otherwise
        """
        if version:
            await self.session.execute(
                update(PublicSkillModel)
                .where(
                    and_(
                        PublicSkillModel.name == name,
                        PublicSkillModel.version == version,
                    )
                )
                .values(usage_count=PublicSkillModel.usage_count + 1)  # type: ignore
            )
        else:
            # Increment latest version
            skill = await self.get_by_name(name)
            if not skill:
                return None

            await self.session.execute(
                update(PublicSkillModel)
                .where(
                    and_(
                        PublicSkillModel.name == name,
                        PublicSkillModel.version == skill.version,
                    )
                )
                .values(usage_count=PublicSkillModel.usage_count + 1)  # type: ignore
            )

        await self.session.flush()

        return await self.get_by_name(name, version)

    async def update_rating(
        self,
        skill_id: str,
        new_rating_avg: float,
    ) -> Optional[PublicSkill]:
        """Update average rating for a skill.

        Args:
            skill_id: Skill ID
            new_rating_avg: New average rating (0.0-5.0)

        Returns:
            Updated PublicSkill if found, None otherwise
        """
        await self.session.execute(
            update(PublicSkillModel)
            .where(PublicSkillModel.id == skill_id)
            .values(rating_avg=new_rating_avg)
        )

        await self.session.flush()

        return await self.get_by_id(skill_id)

    async def update_status(
        self,
        skill_id: str,
        status: str,
    ) -> Optional[PublicSkill]:
        """Update skill approval status.

        Args:
            skill_id: Skill ID
            status: New status (pending/approved/rejected/archived)

        Returns:
            Updated PublicSkill if found, None otherwise
        """
        await self.session.execute(
            update(PublicSkillModel).where(PublicSkillModel.id == skill_id).values(status=status)
        )

        await self.session.flush()

        return await self.get_by_id(skill_id)

    async def delete(self, skill_id: str) -> bool:
        """Delete a public skill.

        Args:
            skill_id: Skill ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(PublicSkillModel).where(PublicSkillModel.id == skill_id)
        )

        await self.session.flush()

        return result.rowcount > 0  # type: ignore

    def _to_pydantic(self, model: PublicSkillModel) -> PublicSkill:
        """Convert ORM model to Pydantic model.

        Args:
            model: PublicSkillModel instance

        Returns:
            PublicSkill instance
        """
        data = model.to_dict()
        return PublicSkill(**data)
