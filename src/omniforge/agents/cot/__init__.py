"""Chain of Thought (CoT) agent implementation.

This module provides data structures and functionality for chain of thought reasoning,
enabling transparent, debuggable agent decision-making processes.
"""

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.autonomous import AutonomousCoTAgent, MaxIterationsError
from omniforge.agents.cot.chain import (
    ChainMetrics,
    ChainStatus,
    ReasoningChain,
    ReasoningStep,
    StepType,
    SynthesisInfo,
    ThinkingInfo,
    ToolCallInfo,
    ToolResultInfo,
    ToolType,
    VisibilityConfig,
    VisibilityLevel,
)
from omniforge.agents.cot.engine import ReasoningEngine, ToolCallResult
from omniforge.agents.cot.events import (
    ChainCompletedEvent,
    ChainFailedEvent,
    ChainStartedEvent,
    ReasoningStepEvent,
)
from omniforge.agents.cot.parser import ParsedResponse, ReActParser
from omniforge.agents.cot.prompts import (
    build_react_system_prompt,
    format_single_tool,
    format_tool_descriptions,
)

__all__ = [
    "CoTAgent",
    "AutonomousCoTAgent",
    "MaxIterationsError",
    "ChainMetrics",
    "ChainStatus",
    "ReasoningChain",
    "ReasoningStep",
    "StepType",
    "SynthesisInfo",
    "ThinkingInfo",
    "ToolCallInfo",
    "ToolResultInfo",
    "ToolType",
    "VisibilityConfig",
    "VisibilityLevel",
    "ReasoningEngine",
    "ToolCallResult",
    "ChainCompletedEvent",
    "ChainFailedEvent",
    "ChainStartedEvent",
    "ReasoningStepEvent",
    "ParsedResponse",
    "ReActParser",
    "build_react_system_prompt",
    "format_single_tool",
    "format_tool_descriptions",
]
