"""Core abstractions and protocols for OmniForge.

This package contains core protocols and interfaces that enable cross-layer
communication without creating circular dependencies.
"""

from omniforge.core.protocols import ChainRecorder

__all__ = [
    "ChainRecorder",
]
