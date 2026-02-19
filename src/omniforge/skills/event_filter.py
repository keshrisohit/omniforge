"""Event filtering utilities for visibility control.

This module provides filtering functionality for task events based on visibility
levels and user roles, enabling progressive disclosure in the UI.
"""

import re
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from omniforge.agents.events import TaskEvent, TaskMessageEvent
from omniforge.agents.models import TextPart
from omniforge.tools.types import VisibilityLevel

# Patterns for sensitive data that should be redacted
SENSITIVE_PATTERNS = ["password", "api_key", "token", "secret", "credential"]

# Default visibility levels by role
DEFAULT_VISIBILITY_BY_ROLE = {
    "END_USER": VisibilityLevel.SUMMARY,
    "DEVELOPER": VisibilityLevel.FULL,
    "ADMIN": VisibilityLevel.FULL,
}


@dataclass
class VisibilityConfig:
    """Configuration for event visibility filtering.

    Attributes:
        level: Visibility level for the user (FULL/SUMMARY/HIDDEN)
    """

    level: VisibilityLevel = VisibilityLevel.SUMMARY


class EventFilter:
    """Filters task events based on visibility rules.

    This class implements role-based event filtering and sensitive data redaction
    for task events in autonomous skill execution.

    Example:
        >>> filter = EventFilter(user_role="END_USER")
        >>> async for event in filter.filter_events(event_stream):
        ...     # END_USER only sees SUMMARY events, sensitive data redacted
        ...     print(event)
    """

    def __init__(self, user_role: Optional[str] = None):
        """Initialize event filter.

        Args:
            user_role: User's role (END_USER, DEVELOPER, ADMIN)
        """
        self.user_role = user_role
        self.config = self._get_visibility_config(user_role)

    def _get_visibility_config(self, user_role: Optional[str]) -> VisibilityConfig:
        """Get visibility configuration for user role.

        Args:
            user_role: User's role identifier

        Returns:
            VisibilityConfig with appropriate visibility level
        """
        level = (
            DEFAULT_VISIBILITY_BY_ROLE.get(user_role, VisibilityLevel.SUMMARY)
            if user_role
            else VisibilityLevel.SUMMARY
        )
        return VisibilityConfig(level=level)

    def should_emit_event(self, event: TaskEvent) -> bool:
        """Check if event should be emitted based on visibility rules.

        Resolution logic:
        - Events without visibility attribute: always emit
        - HIDDEN events: never emit
        - SUMMARY events: emit for SUMMARY and FULL levels
        - FULL events: emit only for FULL level

        Args:
            event: Task event to check

        Returns:
            True if event should be emitted, False otherwise
        """
        if not hasattr(event, "visibility"):
            return True

        event_visibility = event.visibility
        user_level = self.config.level

        if event_visibility == VisibilityLevel.HIDDEN:
            return False
        elif event_visibility == VisibilityLevel.SUMMARY:
            return user_level in [VisibilityLevel.FULL, VisibilityLevel.SUMMARY]
        elif event_visibility == VisibilityLevel.FULL:
            return user_level == VisibilityLevel.FULL
        else:
            return True

    def filter_sensitive_data(self, event: TaskEvent) -> TaskEvent:
        """Redact sensitive data from event content.

        Scans event content for sensitive patterns (passwords, API keys, etc.)
        and replaces values with [REDACTED].

        Args:
            event: Task event to filter

        Returns:
            New event with sensitive data redacted
        """
        if isinstance(event, TaskMessageEvent):
            filtered_parts: list = []
            for part in event.message_parts:
                if isinstance(part, TextPart):
                    filtered_text = self._redact_sensitive(part.text)
                    filtered_parts.append(TextPart(text=filtered_text))
                else:
                    filtered_parts.append(part)

            # Create new event with filtered parts
            return event.model_copy(update={"message_parts": filtered_parts})

        return event

    def _redact_sensitive(self, text: str) -> str:
        """Redact sensitive values from text.

        Matches patterns like:
        - "api_key": "value"
        - api_key=value
        - password: secret123

        Args:
            text: Text to redact

        Returns:
            Text with sensitive values replaced with [REDACTED]
        """
        for pattern in SENSITIVE_PATTERNS:
            # Match pattern: "key": "value" or key=value or key: value
            text = re.sub(
                rf"({pattern}\s*[=:]\s*)[\"']?[^\"'\s,}}]+[\"']?",
                r"\1[REDACTED]",
                text,
                flags=re.IGNORECASE,
            )
        return text


async def filter_event_stream(
    event_stream: AsyncIterator[TaskEvent],
    user_role: Optional[str] = None,
) -> AsyncIterator[TaskEvent]:
    """Filter an async event stream based on user role.

    Convenience function that combines event filtering and sensitive data redaction.

    Args:
        event_stream: Async iterator of TaskEvent instances
        user_role: User's role (END_USER, DEVELOPER, ADMIN)

    Yields:
        Filtered TaskEvent instances with sensitive data redacted

    Example:
        >>> async for event in filter_event_stream(executor.execute(...), "END_USER"):
        ...     print(event)  # Only SUMMARY events, no sensitive data
    """
    event_filter = EventFilter(user_role=user_role)

    async for event in event_stream:
        if event_filter.should_emit_event(event):
            yield event_filter.filter_sensitive_data(event)
