"""Tests for AgentConfig Pydantic model."""

import pytest
from pydantic import ValidationError

from omniforge.builder.models import (
    AgentConfig,
    AgentStatus,
    SharingLevel,
    SkillReference,
    TriggerType,
)


class TestSkillReference:
    """Tests for SkillReference model."""

    def test_valid_skill_reference(self) -> None:
        """Test creating a valid skill reference."""
        skill = SkillReference(
            skill_id="notion-weekly-report",
            name="Notion Weekly Summary",
            source="public",
            order=1,
            config={"databases": ["Projects"], "timeframe": "7d"},
        )

        assert skill.skill_id == "notion-weekly-report"
        assert skill.name == "Notion Weekly Summary"
        assert skill.source == "public"
        assert skill.order == 1
        assert skill.config["databases"] == ["Projects"]

    def test_skill_id_validation_kebab_case(self) -> None:
        """Test skill_id must be kebab-case alphanumeric."""
        # Valid: kebab-case
        SkillReference(
            skill_id="valid-skill-name", name="Test", order=1
        )

        # Valid: with underscores
        SkillReference(skill_id="valid_skill_name", name="Test", order=1)

        # Invalid: special characters
        with pytest.raises(ValidationError, match="kebab-case alphanumeric"):
            SkillReference(
                skill_id="invalid@skill", name="Test", order=1
            )

        # Invalid: spaces
        with pytest.raises(ValidationError, match="kebab-case alphanumeric"):
            SkillReference(
                skill_id="invalid skill", name="Test", order=1
            )

    def test_source_validation(self) -> None:
        """Test source must be custom/public/community."""
        # Valid sources
        for source in ["custom", "public", "community"]:
            SkillReference(
                skill_id="test", name="Test", source=source, order=1
            )

        # Invalid source
        with pytest.raises(ValidationError):
            SkillReference(
                skill_id="test", name="Test", source="invalid", order=1
            )


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_minimal_valid_config(self) -> None:
        """Test creating minimal valid agent config."""
        config = AgentConfig(
            tenant_id="tenant-123",
            name="Test Agent",
            description="Test description",
            skills=[
                SkillReference(
                    skill_id="test-skill", name="Test Skill", order=1
                )
            ],
            created_by="user-456",
        )

        assert config.tenant_id == "tenant-123"
        assert config.name == "Test Agent"
        assert config.status == AgentStatus.DRAFT
        assert config.trigger == TriggerType.ON_DEMAND
        assert config.schedule is None
        assert len(config.skills) == 1
        assert config.sharing_level == SharingLevel.PRIVATE

    def test_scheduled_agent_requires_schedule(self) -> None:
        """Test scheduled trigger requires schedule field."""
        # Missing schedule - should fail
        with pytest.raises(ValidationError, match="schedule is required"):
            AgentConfig(
                tenant_id="tenant-123",
                name="Scheduled Agent",
                description="Test",
                trigger=TriggerType.SCHEDULED,
                skills=[SkillReference(skill_id="test", name="Test", order=1)],
                created_by="user-456",
            )

        # With valid schedule - should succeed
        config = AgentConfig(
            tenant_id="tenant-123",
            name="Scheduled Agent",
            description="Test",
            trigger=TriggerType.SCHEDULED,
            schedule="0 8 * * MON",  # Every Monday at 8am
            skills=[SkillReference(skill_id="test", name="Test", order=1)],
            created_by="user-456",
        )
        assert config.schedule == "0 8 * * MON"

    def test_non_scheduled_agent_cannot_have_schedule(self) -> None:
        """Test non-scheduled triggers cannot have schedule."""
        with pytest.raises(
            ValidationError, match="schedule should not be set"
        ):
            AgentConfig(
                tenant_id="tenant-123",
                name="On-Demand Agent",
                description="Test",
                trigger=TriggerType.ON_DEMAND,
                schedule="0 8 * * MON",  # Invalid for on-demand
                skills=[SkillReference(skill_id="test", name="Test", order=1)],
                created_by="user-456",
            )

    def test_cron_expression_validation(self) -> None:
        """Test cron expression validation."""
        # Valid cron expressions
        valid_crons = [
            "0 8 * * *",  # Daily at 8am
            "0 8 * * MON",  # Every Monday at 8am
            "*/15 * * * *",  # Every 15 minutes
            "0 0 1 * *",  # First of every month
            "0 8 * * MON-FRI",  # Weekdays at 8am
        ]

        for cron in valid_crons:
            config = AgentConfig(
                tenant_id="tenant-123",
                name="Test",
                description="Test",
                trigger=TriggerType.SCHEDULED,
                schedule=cron,
                skills=[SkillReference(skill_id="test", name="Test", order=1)],
                created_by="user-456",
            )
            assert config.schedule == cron

        # Invalid cron expressions
        invalid_crons = [
            "invalid",
            "0 8 * *",  # Missing field
            "0 99 * * *",  # Invalid hour
            "60 * * * *",  # Invalid minute
        ]

        for cron in invalid_crons:
            with pytest.raises(ValidationError, match="Invalid cron expression"):
                AgentConfig(
                    tenant_id="tenant-123",
                    name="Test",
                    description="Test",
                    trigger=TriggerType.SCHEDULED,
                    schedule=cron,
                    skills=[SkillReference(skill_id="test", name="Test", order=1)],
                    created_by="user-456",
                )

    def test_skill_order_uniqueness(self) -> None:
        """Test skill order numbers must be unique."""
        # Valid: unique orders
        AgentConfig(
            tenant_id="tenant-123",
            name="Multi-Skill Agent",
            description="Test",
            skills=[
                SkillReference(skill_id="skill-1", name="Skill 1", order=1),
                SkillReference(skill_id="skill-2", name="Skill 2", order=2),
                SkillReference(skill_id="skill-3", name="Skill 3", order=3),
            ],
            created_by="user-456",
        )

        # Invalid: duplicate orders
        with pytest.raises(ValidationError, match="order numbers must be unique"):
            AgentConfig(
                tenant_id="tenant-123",
                name="Multi-Skill Agent",
                description="Test",
                skills=[
                    SkillReference(skill_id="skill-1", name="Skill 1", order=1),
                    SkillReference(skill_id="skill-2", name="Skill 2", order=1),  # Duplicate!
                ],
                created_by="user-456",
            )

    def test_integration_id_validation(self) -> None:
        """Test integration IDs must be non-empty."""
        # Valid: non-empty integration IDs
        AgentConfig(
            tenant_id="tenant-123",
            name="Test Agent",
            description="Test",
            skills=[SkillReference(skill_id="test", name="Test", order=1)],
            integrations=["integration-123", "integration-456"],
            created_by="user-456",
        )

        # Invalid: empty integration ID
        with pytest.raises(ValidationError, match="must be non-empty"):
            AgentConfig(
                tenant_id="tenant-123",
                name="Test Agent",
                description="Test",
                skills=[SkillReference(skill_id="test", name="Test", order=1)],
                integrations=["integration-123", ""],  # Empty ID
                created_by="user-456",
            )

    def test_at_least_one_skill_required(self) -> None:
        """Test agent must have at least one skill."""
        with pytest.raises(ValidationError):
            AgentConfig(
                tenant_id="tenant-123",
                name="Test Agent",
                description="Test",
                skills=[],  # Empty skills list
                created_by="user-456",
            )

    def test_all_fields_populated(self) -> None:
        """Test agent config with all fields populated."""
        config = AgentConfig(
            id="agent-123",
            tenant_id="tenant-456",
            name="Weekly Reporter",
            description="Generates weekly reports from Notion",
            status=AgentStatus.ACTIVE,
            trigger=TriggerType.SCHEDULED,
            schedule="0 8 * * MON",
            skills=[
                SkillReference(
                    skill_id="notion-report",
                    name="Notion Weekly Report",
                    source="public",
                    order=1,
                    config={"databases": ["Projects"], "timeframe": "7d"},
                ),
                SkillReference(
                    skill_id="slack-post",
                    name="Slack Poster",
                    source="community",
                    order=2,
                    config={"channel": "#team-updates"},
                ),
            ],
            integrations=["integration-notion-123", "integration-slack-456"],
            sharing_level=SharingLevel.TEAM,
            created_by="user-789",
        )

        assert config.id == "agent-123"
        assert config.status == AgentStatus.ACTIVE
        assert config.trigger == TriggerType.SCHEDULED
        assert len(config.skills) == 2
        assert config.skills[0].order == 1
        assert config.skills[1].order == 2
        assert len(config.integrations) == 2
        assert config.sharing_level == SharingLevel.TEAM
