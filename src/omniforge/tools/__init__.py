"""Tool management and execution for OmniForge.

This module provides the core tool infrastructure including error handling,
registration, validation, and execution.

Built-in Tools:
    - LLMTool: Access to 100+ LLM providers via LiteLLM
      (Available through get_default_tool_registry() or import from omniforge.tools.builtin)

Quick Start:
    >>> from omniforge.tools import get_default_tool_registry
    >>> registry = get_default_tool_registry()
    >>> tools = registry.list_tools()
    >>> llm_tool = registry.get("llm")
"""

from typing import TYPE_CHECKING

from omniforge.tools.base import (
    AuditLevel,
    BaseTool,
    ParameterType,
    StreamingTool,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolPermissions,
    ToolResult,
    ToolRetryConfig,
    ToolVisibilityConfig,
)
from omniforge.tools.errors import (
    CostBudgetExceededError,
    ModelNotApprovedError,
    RateLimitExceededError,
    ToolAlreadyRegisteredError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    ToolValidationError,
)
from omniforge.tools.registry import ToolRegistry, get_default_registry, register_tool
from omniforge.tools.setup import get_default_tool_registry, setup_default_tools
from omniforge.tools.types import ToolType, VisibilityLevel

# Lazy import ToolExecutor to avoid circular imports with agents.cot.chain
if TYPE_CHECKING:
    from omniforge.tools.executor import ToolExecutor

__all__ = [
    # Base classes and interfaces
    "BaseTool",
    "StreamingTool",
    # Models
    "ToolDefinition",
    "ToolParameter",
    "ToolRetryConfig",
    "ToolVisibilityConfig",
    "ToolPermissions",
    "ToolCallContext",
    "ToolResult",
    # Enums
    "AuditLevel",
    "ParameterType",
    "ToolType",
    "VisibilityLevel",
    # Registry
    "ToolRegistry",
    "get_default_registry",
    "register_tool",
    # Executor
    "ToolExecutor",
    # Setup
    "setup_default_tools",
    "get_default_tool_registry",
    # Errors
    "ToolError",
    "ToolNotFoundError",
    "ToolAlreadyRegisteredError",
    "ToolValidationError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "RateLimitExceededError",
    "CostBudgetExceededError",
    "ModelNotApprovedError",
]


def __getattr__(name: str):
    """Lazy import for ToolExecutor to avoid circular imports."""
    if name == "ToolExecutor":
        from omniforge.tools.executor import ToolExecutor

        return ToolExecutor
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
