"""Configuration classes for prompt definitions in agent configurations.

This module provides the PromptConfig dataclass for defining prompts
within agent configurations.
"""

from dataclasses import dataclass, field
from typing import Any

from omniforge.prompts.enums import MergeBehavior


@dataclass
class PromptConfig:
    """Configuration for a prompt in an agent definition.

    This dataclass is used to define prompts when configuring agents,
    providing a clean interface for specifying prompt content, variables,
    and merge behavior.

    Attributes:
        agent_prompt: The prompt template content for the agent
        variables: Dictionary of variables to substitute in the prompt
        merge_behavior: Dictionary mapping merge point names to merge behaviors

    Example:
        >>> config = PromptConfig(
        ...     agent_prompt="You are a helpful assistant. {{ instructions }}",
        ...     variables={"instructions": "Be concise and clear."},
        ...     merge_behavior={"context": MergeBehavior.APPEND}
        ... )
        >>> config.agent_prompt
        'You are a helpful assistant. {{ instructions }}'
    """

    agent_prompt: str
    variables: dict[str, Any] = field(default_factory=dict)
    merge_behavior: dict[str, MergeBehavior] = field(default_factory=dict)
