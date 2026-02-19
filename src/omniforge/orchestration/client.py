"""HTTP client for agent-to-agent communication.

This module provides the A2AClient class for making outbound HTTP requests
to other agents following the A2A protocol. It handles task creation,
SSE response parsing, and event streaming.
"""

import json
from typing import AsyncIterator

import httpx

from omniforge.agents.events import TaskEvent
from omniforge.agents.models import AgentCard
from omniforge.tasks.models import TaskCreateRequest


class A2AClient:
    """HTTP client for agent-to-agent communication.

    This client provides methods for communicating with other agents over HTTP
    following the A2A protocol. It handles SSE (Server-Sent Events) streaming
    and parses task events from remote agents.

    The client supports authentication, timeout configuration, and connection
    pooling for efficient communication.

    Attributes:
        _http_client: The underlying HTTP client for making requests

    Example:
        >>> client = A2AClient()
        >>> try:
        ...     # Create task on remote agent
        ...     async for event in client.send_task(agent_card, task_request):
        ...         if event.type == "message":
        ...             print(f"Message: {event.message_parts}")
        ...         elif event.type == "done":
        ...             print(f"Task completed: {event.final_state}")
        ... finally:
        ...     await client.close()
    """

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize the A2A client.

        Args:
            timeout: Default timeout in seconds for HTTP requests
        """
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client and release resources.

        Should be called when the client is no longer needed to properly
        clean up connections.

        Example:
            >>> client = A2AClient()
            >>> try:
            ...     # Use client
            ...     pass
            ... finally:
            ...     await client.close()
        """
        await self._http_client.aclose()

    async def __aenter__(self) -> "A2AClient":
        """Enter async context manager.

        Returns:
            This client instance
        """
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Exit async context manager and close client.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        await self.close()

    async def send_task(
        self, agent_card: AgentCard, request: TaskCreateRequest
    ) -> AsyncIterator[TaskEvent]:
        """Send a task to a remote agent and stream response events.

        Creates a new task on the remote agent specified by the agent_card's
        service endpoint. The remote agent must support the A2A protocol and
        return Server-Sent Events (SSE) for streaming task updates.

        Args:
            agent_card: The agent card containing service endpoint and identity
            request: The task creation request with message parts and metadata

        Yields:
            TaskEvent objects parsed from the SSE stream

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If SSE parsing fails or event format is invalid

        Example:
            >>> card = await discovery.get_agent_card("remote-agent")
            >>> request = TaskCreateRequest(
            ...     message_parts=[TextPart(text="Analyze this data")],
            ...     tenant_id="tenant-1",
            ...     user_id="user-1"
            ... )
            >>> async for event in client.send_task(card, request):
            ...     print(f"Event: {event.type}")
        """
        # Build URL for task creation
        endpoint = agent_card.service_endpoint.rstrip("/")
        agent_id = agent_card.identity.id
        url = f"{endpoint}/api/v1/agents/{agent_id}/tasks"

        # Prepare request body
        body = request.model_dump(mode="json")

        # Make POST request with SSE streaming
        async with self._http_client.stream(
            "POST",
            url,
            json=body,
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
            },
        ) as response:
            # Check response status
            response.raise_for_status()

            # Parse SSE events
            async for event in self._parse_sse_stream(response):
                yield event

    async def _parse_sse_stream(self, response: httpx.Response) -> AsyncIterator[TaskEvent]:
        """Parse Server-Sent Events stream into TaskEvent objects.

        Reads the SSE stream line by line, extracting event type and data
        fields, then parsing the JSON data into appropriate TaskEvent subclasses.

        Args:
            response: The HTTP response with SSE stream

        Yields:
            TaskEvent objects parsed from the stream

        Raises:
            ValueError: If event format is invalid or JSON parsing fails

        SSE Format:
            event: message
            data: {"type": "message", "task_id": "123", ...}

            event: done
            data: {"type": "done", "task_id": "123", ...}
        """
        import omniforge.agents.events as events_module

        event_type = None
        event_data = None

        async for line in response.aiter_lines():
            line = line.strip()

            # Skip empty lines (event separator)
            if not line:
                # Process complete event
                if event_type and event_data:
                    yield self._parse_event(event_type, event_data, events_module)
                    event_type = None
                    event_data = None
                continue

            # Parse SSE field
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                event_data = line[5:].strip()

    def _parse_event(self, event_type: str, event_data: str, events_module: object) -> TaskEvent:
        """Parse a single SSE event into a TaskEvent object.

        Maps the event type to the appropriate TaskEvent subclass and
        deserializes the JSON data.

        Args:
            event_type: The SSE event type (e.g., "status", "message", "done")
            event_data: The JSON data string
            events_module: The events module containing event classes

        Returns:
            Parsed TaskEvent object

        Raises:
            ValueError: If event type is unknown or JSON parsing fails
        """
        # Parse JSON data
        try:
            data = json.loads(event_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in SSE event: {event_data}") from e

        # Map event type to event class name - using getattr for dynamic access
        event_class_name_map = {
            "status": "TaskStatusEvent",
            "message": "TaskMessageEvent",
            "artifact": "TaskArtifactEvent",
            "done": "TaskDoneEvent",
            "error": "TaskErrorEvent",
        }

        event_class_name = event_class_name_map.get(event_type)
        if not event_class_name:
            raise ValueError(f"Unknown event type: {event_type}")

        event_class = getattr(events_module, event_class_name)

        # Deserialize event
        try:
            return event_class(**data)  # type: ignore[no-any-return]
        except Exception as e:
            raise ValueError(f"Failed to parse {event_type} event: {e}") from e
