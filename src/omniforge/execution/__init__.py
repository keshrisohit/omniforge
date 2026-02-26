"""Execution layer for agent and skill orchestration.

This module provides execution services for running agents and orchestrating
multi-skill workflows with error handling and data flow management.
"""

from omniforge.execution.backend import ExecutionBackend
from omniforge.execution.inprocess import InProcessBackend
from omniforge.execution.scheduler import AgentScheduler, ScheduleConfig

__all__ = [
    "AgentScheduler",
    "ExecutionBackend",
    "InProcessBackend",
    "ScheduleConfig",
]
