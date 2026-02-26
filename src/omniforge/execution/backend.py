"""Abstract execution backend interface.

Provides a swappable execution layer so agents can run on different backends
(in-process asyncio, Temporal, etc.) without changing agent code.
"""

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable


class ExecutionBackend(ABC):
    """Abstract execution backend.

    Defines the contract for running activities (tool calls, LLM calls)
    and child agents. Swap implementations to change execution model.

    Available implementations:
    - InProcessBackend: default, runs in asyncio (zero extra deps)
    - TemporalBackend: durable, restartable (requires omniforge[temporal])
    """

    @abstractmethod
    async def run_activity(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args: Any,
        activity_name: str = "",
        timeout_ms: int = 30_000,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Any:
        """Run a single unit of work.

        Args:
            fn: Async callable to execute
            *args: Positional arguments for fn
            activity_name: Human-readable name (used by Temporal for visibility)
            timeout_ms: Timeout in milliseconds (used by Temporal)
            max_retries: Max retry attempts (used by Temporal; InProcess handles
                         retries internally inside fn)
            **kwargs: Keyword arguments for fn

        Returns:
            Result of fn(*args, **kwargs)

        Raises:
            Any exception raised by fn
        """
        ...
