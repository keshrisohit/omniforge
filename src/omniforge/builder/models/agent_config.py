"""Agent configuration Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from croniter import croniter
from pydantic import BaseModel, Field, field_validator, model_validator


class TriggerType(str, Enum):
    """Agent execution trigger types."""

    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"


class AgentStatus(str, Enum):
    """Agent lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class SharingLevel(str, Enum):
    """Agent sharing levels."""

    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"
    B2B2C = "b2b2c"


class SkillReference(BaseModel):
    """Reference to a skill within an agent.

    Attributes:
        skill_id: Unique skill identifier (matches SKILL.md filename without extension)
        name: Human-readable skill name
        source: Where skill comes from (custom/public/community)
        version: Optional version pin (semantic version, None = use latest)
        order: Execution order for multi-skill agents (1-indexed)
        config: Skill-specific configuration parameters
        error_strategy: How to handle errors during execution (default: stop_on_error)
        max_retries: Maximum retry attempts if error_strategy is RETRY_ON_ERROR
    """

    skill_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    source: str = Field(default="custom", pattern="^(custom|public|community)$")
    version: Optional[str] = Field(default=None, max_length=20)
    order: int = Field(..., ge=1)
    config: dict[str, Any] = Field(default_factory=dict)
    error_strategy: str = Field(
        default="stop_on_error",
        pattern="^(stop_on_error|skip_on_error|retry_on_error)$",
    )
    max_retries: int = Field(default=3, ge=0, le=10)

    @field_validator("skill_id")
    @classmethod
    def validate_skill_id(cls, v: str) -> str:
        """Validate skill_id follows kebab-case naming."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"skill_id must be kebab-case alphanumeric with hyphens: {v}")
        return v

    @model_validator(mode="after")
    def validate_max_retries(self) -> "SkillReference":
        """Validate max_retries is only set when error_strategy is RETRY_ON_ERROR."""
        if self.error_strategy != "retry_on_error" and self.max_retries != 3:
            raise ValueError(
                "max_retries should only be set when error_strategy is 'retry_on_error'"
            )
        return self


class AgentConfig(BaseModel):
    """Agent configuration.

    Represents a conversational-built agent with metadata, trigger configuration,
    and skill composition.

    Attributes:
        id: Unique agent identifier (auto-generated)
        tenant_id: Tenant this agent belongs to
        name: Human-readable agent name
        description: What the agent does
        status: Current lifecycle status
        trigger: How the agent is triggered
        schedule: Cron expression (required if trigger=SCHEDULED)
        skills: List of skills this agent uses
        integrations: Integration IDs this agent requires
        sharing_level: Who can access this agent
        created_by: User ID who created the agent
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: Optional[str] = None
    tenant_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    status: AgentStatus = Field(default=AgentStatus.DRAFT)
    trigger: TriggerType = Field(default=TriggerType.ON_DEMAND)
    schedule: Optional[str] = None
    skills: list[SkillReference] = Field(default_factory=list, min_length=1)
    integrations: list[str] = Field(default_factory=list)
    sharing_level: SharingLevel = Field(default=SharingLevel.PRIVATE)
    created_by: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate cron expression if provided."""
        if v is None:
            return v

        try:
            # Validate cron expression using croniter
            croniter(v)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression '{v}': {e}") from e

        return v

    @model_validator(mode="after")
    def validate_trigger_schedule(self) -> "AgentConfig":
        """Validate schedule is provided when trigger is SCHEDULED."""
        if self.trigger == TriggerType.SCHEDULED and not self.schedule:
            raise ValueError("schedule is required when trigger is SCHEDULED")
        if self.trigger != TriggerType.SCHEDULED and self.schedule:
            raise ValueError(f"schedule should not be set when trigger is {self.trigger.value}")
        return self

    @model_validator(mode="after")
    def validate_skill_order_unique(self) -> "AgentConfig":
        """Validate skill execution order numbers are unique."""
        orders = [skill.order for skill in self.skills]
        if len(orders) != len(set(orders)):
            raise ValueError(f"Skill order numbers must be unique, got duplicates: {orders}")
        return self

    @model_validator(mode="after")
    def validate_integration_ids(self) -> "AgentConfig":
        """Validate integration IDs are valid UUIDs or identifiers."""
        for integration_id in self.integrations:
            if not integration_id or len(integration_id) < 1:
                raise ValueError(f"Invalid integration_id: '{integration_id}' must be non-empty")
        return self

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "tenant_id": "tenant-123",
                "name": "Weekly Reporter",
                "description": "Generates weekly reports from Notion and posts to Slack",
                "status": "active",
                "trigger": "scheduled",
                "schedule": "0 8 * * MON",
                "skills": [
                    {
                        "skill_id": "notion-weekly-report",
                        "name": "Notion Weekly Summary",
                        "source": "public",
                        "order": 1,
                        "config": {"databases": ["Client Projects"], "timeframe": "7d"},
                    }
                ],
                "integrations": ["integration-notion-123"],
                "sharing_level": "private",
                "created_by": "user-456",
            }
        }
