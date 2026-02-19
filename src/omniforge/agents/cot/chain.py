"""Core data models for chain of thought reasoning."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Import tool-related enums from tools.types to avoid circular imports
from omniforge.tools.types import ToolType, VisibilityLevel


class StepType(str, Enum):
    """Type of reasoning step in the chain."""

    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYNTHESIS = "synthesis"


class ChainStatus(str, Enum):
    """Status of the reasoning chain."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class VisibilityConfig(BaseModel):
    """Configuration for step visibility control."""

    level: VisibilityLevel = Field(
        default=VisibilityLevel.FULL, description="Visibility level for the step"
    )
    reason: Optional[str] = Field(
        default=None, description="Reason for visibility setting (e.g., 'contains PII')"
    )


class ThinkingInfo(BaseModel):
    """Information for a thinking step."""

    content: str = Field(description="The thinking/reasoning content")
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Confidence level (0.0-1.0)"
    )


class ToolCallInfo(BaseModel):
    """Information for a tool call step."""

    tool_name: str = Field(description="Name of the tool being called")
    tool_type: ToolType = Field(description="Type of tool")
    parameters: dict = Field(default_factory=dict, description="Parameters passed to the tool")
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="ID to correlate with tool result"
    )


class ToolResultInfo(BaseModel):
    """Information for a tool result step."""

    correlation_id: str = Field(description="ID correlating to the tool call")
    success: bool = Field(description="Whether the tool call succeeded")
    result: Optional[dict] = Field(default=None, description="Result data from the tool")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SynthesisInfo(BaseModel):
    """Information for a synthesis step."""

    content: str = Field(description="The synthesized conclusion or answer")
    sources: list[UUID] = Field(
        default_factory=list, description="Step IDs used as sources for synthesis"
    )


class ChainMetrics(BaseModel):
    """Aggregated metrics for a reasoning chain."""

    total_steps: int = Field(default=0, description="Total number of steps")
    llm_calls: int = Field(default=0, description="Number of LLM inference calls")
    tool_calls: int = Field(default=0, description="Number of tool invocations")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    total_cost: float = Field(default=0.0, description="Total cost in USD")


class ReasoningStep(BaseModel):
    """A single step in the reasoning chain."""

    id: UUID = Field(default_factory=uuid4, description="Unique step identifier")
    step_number: int = Field(ge=0, description="Sequential step number")
    type: StepType = Field(description="Type of reasoning step")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Step creation time")
    parent_step_id: Optional[UUID] = Field(
        default=None, description="Parent step ID for nested operations"
    )
    visibility: VisibilityConfig = Field(
        default_factory=VisibilityConfig, description="Visibility configuration"
    )

    # Type-specific info fields
    thinking: Optional[ThinkingInfo] = Field(default=None, description="Thinking step info")
    tool_call: Optional[ToolCallInfo] = Field(default=None, description="Tool call step info")
    tool_result: Optional[ToolResultInfo] = Field(default=None, description="Tool result step info")
    synthesis: Optional[SynthesisInfo] = Field(default=None, description="Synthesis step info")

    # Token and cost tracking
    tokens_used: int = Field(default=0, description="Tokens used in this step")
    cost: float = Field(default=0.0, description="Cost of this step in USD")


class ReasoningChain(BaseModel):
    """A complete chain of reasoning for a task."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this chain")
    task_id: str = Field(description="ID of the task this chain is solving")
    agent_id: str = Field(description="ID of the agent executing this chain")
    status: ChainStatus = Field(default=ChainStatus.RUNNING, description="Chain execution status")
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Chain start timestamp"
    )
    completed_at: Optional[datetime] = Field(default=None, description="Chain completion time")
    steps: list[ReasoningStep] = Field(
        default_factory=list, description="Sequential list of reasoning steps"
    )
    metrics: ChainMetrics = Field(
        default_factory=ChainMetrics, description="Aggregated chain metrics"
    )
    child_chain_ids: list[str] = Field(
        default_factory=list, description="IDs of child chains for sub-agent delegation"
    )
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for multi-tenancy")

    def add_step(self, step: ReasoningStep) -> None:
        """Add a step to the chain and update metrics.

        Args:
            step: The reasoning step to add
        """
        # Auto-assign step number
        step.step_number = len(self.steps)

        # Add step to chain
        self.steps.append(step)

        # Update metrics
        self._update_metrics(step)

    def _update_metrics(self, step: ReasoningStep) -> None:
        """Update chain metrics based on the added step.

        Args:
            step: The step to incorporate into metrics
        """
        self.metrics.total_steps += 1
        self.metrics.total_tokens += step.tokens_used
        self.metrics.total_cost += step.cost

        # Update type-specific metrics
        if step.type == StepType.THINKING or step.type == StepType.SYNTHESIS:
            self.metrics.llm_calls += 1
        elif step.type == StepType.TOOL_CALL:
            self.metrics.tool_calls += 1

    def get_step_by_correlation_id(self, correlation_id: str) -> Optional[ReasoningStep]:
        """Find a tool_call step by its correlation ID.

        Args:
            correlation_id: The correlation ID to search for

        Returns:
            The matching tool_call step, or None if not found
        """
        for step in self.steps:
            if (
                step.type == StepType.TOOL_CALL
                and step.tool_call
                and step.tool_call.correlation_id == correlation_id
            ):
                return step
        return None
