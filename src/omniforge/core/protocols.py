"""Core protocols for cross-layer abstractions.

This module defines protocol interfaces that allow different layers to interact
without creating circular dependencies. These protocols follow the dependency
inversion principle.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omniforge.agents.cot.chain import ReasoningStep


class ChainRecorder(Protocol):
    """Protocol for recording reasoning steps in a chain.

    This protocol allows the tools layer to record steps without depending
    on the concrete ReasoningChain implementation in the agents layer.

    The protocol defines the minimal interface needed for step recording,
    following the dependency inversion principle.

    The actual implementation is omniforge.agents.cot.chain.ReasoningChain,
    which automatically satisfies this protocol through structural typing.
    """

    def add_step(self, step: "ReasoningStep") -> None:
        """Add a step to the reasoning chain.

        Args:
            step: The reasoning step to add
        """
        ...
