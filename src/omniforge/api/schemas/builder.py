"""Pydantic schemas for builder agent API requests and responses.

This module defines data models for agent CRUD operations and execution.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillReferenceSchema(BaseModel):
    """Schema for skill reference in agent configuration.

    Attributes:
        skill_id: Unique skill identifier
        name: Human-readable skill name
        source: Skill source (custom/public/community)
        order: Execution order (1-indexed)
        config: Skill-specific configuration
    """

    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    source: str = Field(default="custom", description="Skill source location")
    order: int = Field(..., ge=1, description="Execution order")
    config: dict[str, Any] = Field(default_factory=dict, description="Skill-specific configuration")


class AgentUsageStats(BaseModel):
    """Agent usage statistics.

    Attributes:
        total_runs: Total number of executions
        successful_runs: Number of successful executions
        last_run: Timestamp of last execution
    """

    total_runs: int = Field(default=0, description="Total execution count")
    successful_runs: int = Field(default=0, description="Successful execution count")
    last_run: Optional[datetime] = Field(None, description="Last execution timestamp")


class AgentSummary(BaseModel):
    """Summary view of an agent for list endpoints.

    Attributes:
        id: Unique agent identifier
        name: Agent name
        description: What the agent does
        status: Current lifecycle status
        trigger_type: How agent is triggered
        skills: List of skills
        last_run: Last execution timestamp
    """

    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    status: str = Field(..., description="Agent status (draft/active/paused/archived)")
    trigger_type: str = Field(..., description="Trigger type (on_demand/scheduled/event_driven)")
    skills: list[SkillReferenceSchema] = Field(
        default_factory=list, description="Skills used by agent"
    )
    last_run: Optional[datetime] = Field(None, description="Last execution timestamp")


class AgentListResponse(BaseModel):
    """Response for listing user's agents.

    Attributes:
        agents: List of agent summaries
    """

    agents: list[AgentSummary] = Field(default_factory=list, description="List of agents")


class AgentDetailResponse(BaseModel):
    """Detailed view of a single agent.

    Attributes:
        id: Unique agent identifier
        name: Agent name
        description: What the agent does
        status: Current lifecycle status
        trigger_type: How agent is triggered
        schedule: Cron expression (if scheduled)
        skills: List of skills with configuration
        integrations: Integration IDs required
        usage_stats: Execution statistics
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    status: str = Field(..., description="Agent status")
    trigger_type: str = Field(..., description="Trigger type")
    schedule: Optional[str] = Field(None, description="Cron schedule expression")
    skills: list[SkillReferenceSchema] = Field(
        default_factory=list, description="Skills configuration"
    )
    integrations: list[str] = Field(default_factory=list, description="Required integration IDs")
    usage_stats: AgentUsageStats = Field(..., description="Execution statistics")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AgentRunRequest(BaseModel):
    """Request to execute an agent.

    Attributes:
        input_data: Optional input parameters for execution
    """

    input_data: dict[str, Any] = Field(
        default_factory=dict, description="Input parameters for agent execution"
    )


class AgentRunResponse(BaseModel):
    """Response after triggering agent execution.

    Attributes:
        execution_id: Unique execution identifier
        status: Execution status (always "pending" initially)
    """

    execution_id: str = Field(..., description="Unique execution identifier")
    status: str = Field(default="pending", description="Execution status")


class SkillExecutionResult(BaseModel):
    """Result of a single skill execution.

    Attributes:
        skill_id: Skill identifier
        status: Execution status
        output: Skill output data
        error: Error message if failed
        duration_ms: Execution duration in milliseconds
    """

    skill_id: str = Field(..., description="Skill identifier")
    status: str = Field(..., description="Execution status")
    output: Optional[dict[str, Any]] = Field(None, description="Skill output")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Execution duration")


class AgentExecutionResponse(BaseModel):
    """Detailed execution result.

    Attributes:
        id: Execution identifier
        agent_id: Agent identifier
        status: Overall execution status
        trigger_type: How execution was triggered
        started_at: Start timestamp
        completed_at: Completion timestamp
        duration_ms: Total duration in milliseconds
        output: Overall execution output
        error: Error message if failed
        skill_executions: Results of individual skill executions
    """

    id: str = Field(..., description="Execution identifier")
    agent_id: str = Field(..., description="Agent identifier")
    status: str = Field(..., description="Execution status")
    trigger_type: str = Field(..., description="Trigger type")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_ms: Optional[int] = Field(None, description="Total duration")
    output: Optional[dict[str, Any]] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message")
    skill_executions: list[SkillExecutionResult] = Field(
        default_factory=list, description="Individual skill results"
    )


class AgentExecutionsListResponse(BaseModel):
    """Response for listing agent executions.

    Attributes:
        executions: List of execution results
    """

    executions: list[AgentExecutionResponse] = Field(
        default_factory=list, description="List of executions"
    )
