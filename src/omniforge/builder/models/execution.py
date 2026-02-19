"""Agent execution tracking models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentExecution(BaseModel):
    """Agent execution log entry.

    Tracks individual executions of an agent, including timing, status, and outputs.

    Attributes:
        id: Unique execution identifier
        agent_id: Agent that was executed
        tenant_id: Tenant context for this execution
        status: Current execution status
        trigger_type: What triggered this execution (scheduled, on-demand, event)
        started_at: Execution start time
        completed_at: Execution completion time (None if still running)
        duration_ms: Execution duration in milliseconds
        output: Structured output from execution (skill results)
        error: Error message if execution failed
        skill_executions: Per-skill execution details
        metadata: Additional execution metadata
    """

    id: Optional[str] = None
    agent_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    trigger_type: str = Field(..., pattern="^(on_demand|scheduled|event_driven)$")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = Field(default=None, ge=0)
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    skill_executions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "agent_id": "agent-123",
                "tenant_id": "tenant-456",
                "status": "success",
                "trigger_type": "scheduled",
                "started_at": "2026-01-25T08:30:00Z",
                "completed_at": "2026-01-25T08:30:45Z",
                "duration_ms": 45000,
                "output": {"report_generated": True, "file_path": "reports/weekly.md"},
                "skill_executions": [
                    {
                        "skill_id": "notion-weekly-report",
                        "status": "success",
                        "duration_ms": 45000,
                    }
                ],
            }
        }
