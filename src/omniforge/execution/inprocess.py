"""In-process execution backend.

Default backend that runs everything in asyncio — identical behaviour to
before the backend abstraction was introduced. Zero new dependencies.
"""

from typing import Any, Awaitable, Callable

from omniforge.execution.backend import ExecutionBackend


class InProcessBackend(ExecutionBackend):
    """Runs activities directly in the current asyncio event loop.

    This is the default backend. It is a transparent passthrough — it calls
    fn(*args, **kwargs) and returns the result. Retry logic, timeouts, and
    skill restrictions are all handled inside fn itself (by ToolExecutor).
    """

    async def run_activity(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args: Any,
        activity_name: str = "",
        timeout_ms: int = 30_000,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Any:
        return await fn(*args, **kwargs)
