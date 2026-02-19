"""Execution tracing for debugging and performance analysis.

This module provides detailed execution traces with timing information
for skills and agent executions.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

# Context variable to store current trace
current_trace_var: ContextVar[Optional["ExecutionTrace"]] = ContextVar(
    "current_trace", default=None
)


@dataclass
class SkillTrace:
    """Trace information for a single skill execution.

    Attributes:
        skill_id: Unique skill identifier
        skill_name: Human-readable skill name
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp (None if still running)
        duration_ms: Execution duration in milliseconds
        status: Execution status (success, failed, timeout)
        error: Error message if execution failed
        input_data: Input data provided to skill
        output_data: Output data produced by skill
    """

    skill_id: str
    skill_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status: str = "running"
    error: Optional[str] = None
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary for serialization.

        Returns:
            Dictionary representation of skill trace
        """
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "input_size_bytes": len(str(self.input_data).encode("utf-8")),
            "output_size_bytes": (
                len(str(self.output_data).encode("utf-8")) if self.output_data else 0
            ),
        }


@dataclass
class ExecutionTrace:
    """Complete execution trace for an agent run.

    Tracks all skill executions with timing and status information
    for debugging and performance analysis.

    Attributes:
        trace_id: Unique trace identifier
        agent_id: Agent identifier
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        total_duration_ms: Total execution duration in milliseconds
        skills: List of skill traces in execution order
        status: Overall execution status
    """

    trace_id: str
    agent_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    skills: list[SkillTrace] = field(default_factory=list)
    status: str = "running"

    def start_skill(
        self,
        skill_id: str,
        skill_name: str,
        input_data: dict[str, Any],
    ) -> SkillTrace:
        """Start tracing a new skill execution.

        Args:
            skill_id: Unique skill identifier
            skill_name: Human-readable skill name
            input_data: Input data for skill

        Returns:
            New SkillTrace instance

        Example:
            >>> trace = ExecutionTrace(
            ...     trace_id="trace-1", agent_id="agent-1", started_at=datetime.utcnow()
            ... )
            >>> skill_trace = trace.start_skill("skill-1", "processor", {"key": "value"})
        """
        skill_trace = SkillTrace(
            skill_id=skill_id,
            skill_name=skill_name,
            started_at=datetime.utcnow(),
            input_data=input_data,
        )
        self.skills.append(skill_trace)
        return skill_trace

    def complete_skill(
        self,
        skill_trace: SkillTrace,
        status: str,
        output_data: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Complete a skill trace with results.

        Args:
            skill_trace: SkillTrace to complete
            status: Final execution status (success, failed, timeout)
            output_data: Output data produced by skill
            error: Error message if execution failed

        Example:
            >>> trace.complete_skill(skill_trace, "success", {"result": "done"})
        """
        skill_trace.completed_at = datetime.utcnow()
        skill_trace.duration_ms = int(
            (skill_trace.completed_at - skill_trace.started_at).total_seconds() * 1000
        )
        skill_trace.status = status
        skill_trace.output_data = output_data
        skill_trace.error = error

    def complete(self, status: str) -> None:
        """Complete the execution trace.

        Args:
            status: Final execution status (success, failed, partial)

        Example:
            >>> trace.complete("success")
        """
        self.completed_at = datetime.utcnow()
        self.total_duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary for serialization.

        Returns:
            Dictionary representation of execution trace

        Example:
            >>> trace_dict = trace.to_dict()
            >>> print(trace_dict["total_duration_ms"])
        """
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status,
            "skills": [skill.to_dict() for skill in self.skills],
            "skill_count": len(self.skills),
            "successful_skills": sum(1 for s in self.skills if s.status == "success"),
            "failed_skills": sum(1 for s in self.skills if s.status == "failed"),
        }


class ExecutionTracer:
    """Manages execution traces for agent runs.

    Provides methods to start, update, and retrieve execution traces
    with automatic context management.
    """

    def start_trace(self, trace_id: str, agent_id: Optional[str] = None) -> ExecutionTrace:
        """Start a new execution trace.

        Args:
            trace_id: Unique trace identifier
            agent_id: Optional agent identifier

        Returns:
            New ExecutionTrace instance

        Example:
            >>> tracer = get_execution_tracer()
            >>> trace = tracer.start_trace("trace-1", "agent-1")
        """
        trace = ExecutionTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            started_at=datetime.utcnow(),
        )
        current_trace_var.set(trace)
        return trace

    def get_current_trace(self) -> Optional[ExecutionTrace]:
        """Get the current execution trace from context.

        Returns:
            Current ExecutionTrace if available, None otherwise

        Example:
            >>> trace = tracer.get_current_trace()
            >>> if trace:
            ...     print(trace.trace_id)
        """
        return current_trace_var.get()

    def clear_trace(self) -> None:
        """Clear the current trace from context.

        Example:
            >>> tracer.clear_trace()
        """
        current_trace_var.set(None)


# Singleton instance
_execution_tracer: Optional[ExecutionTracer] = None


def get_execution_tracer() -> ExecutionTracer:
    """Get the global ExecutionTracer instance.

    Returns:
        Singleton ExecutionTracer instance

    Example:
        >>> tracer = get_execution_tracer()
        >>> trace = tracer.start_trace("trace-1")
    """
    global _execution_tracer
    if _execution_tracer is None:
        _execution_tracer = ExecutionTracer()
    return _execution_tracer
