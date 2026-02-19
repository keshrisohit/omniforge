"""Custom exceptions for agent module.

This module defines the exception hierarchy for agent-related errors,
providing structured error handling with status codes and error codes.
"""

from typing import Optional


class AgentError(Exception):
    """Base exception for all agent-related errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code for API responses
    """

    def __init__(self, message: str, code: str, status_code: int) -> None:
        """Initialize agent error.

        Args:
            message: Human-readable error description
            code: Machine-readable error code
            status_code: HTTP status code (400, 500, etc.)
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AgentNotFoundError(AgentError):
    """Raised when an agent cannot be found.

    This error indicates that the requested agent does not exist in the system.
    """

    def __init__(self, agent_id: str) -> None:
        """Initialize agent not found error.

        Args:
            agent_id: The ID of the agent that was not found
        """
        super().__init__(
            message=f"Agent '{agent_id}' not found",
            code="agent_not_found",
            status_code=404,
        )
        self.agent_id = agent_id


class TaskNotFoundError(AgentError):
    """Raised when a task cannot be found.

    This error indicates that the requested task does not exist in the system.
    """

    def __init__(self, task_id: str) -> None:
        """Initialize task not found error.

        Args:
            task_id: The ID of the task that was not found
        """
        super().__init__(
            message=f"Task '{task_id}' not found",
            code="task_not_found",
            status_code=404,
        )
        self.task_id = task_id


class TaskStateError(AgentError):
    """Raised when an operation is invalid for the current task state.

    This error indicates that the requested operation cannot be performed
    because the task is in an incompatible state.
    """

    def __init__(self, task_id: str, current_state: str, operation: str) -> None:
        """Initialize task state error.

        Args:
            task_id: The ID of the task
            current_state: The current state of the task
            operation: The operation that was attempted
        """
        super().__init__(
            message=f"Cannot perform '{operation}' on task '{task_id}' "
            f"in state '{current_state}'",
            code="task_state_error",
            status_code=409,
        )
        self.task_id = task_id
        self.current_state = current_state
        self.operation = operation


class SkillNotFoundError(AgentError):
    """Raised when a skill cannot be found.

    This error indicates that the requested skill does not exist in the agent.
    """

    def __init__(self, skill_name: str, agent_id: Optional[str] = None) -> None:
        """Initialize skill not found error.

        Args:
            skill_name: The name of the skill that was not found
            agent_id: Optional agent ID for additional context
        """
        if agent_id:
            message = f"Skill '{skill_name}' not found in agent '{agent_id}'"
        else:
            message = f"Skill '{skill_name}' not found"

        super().__init__(
            message=message,
            code="skill_not_found",
            status_code=404,
        )
        self.skill_name = skill_name
        self.agent_id = agent_id


class AgentProcessingError(AgentError):
    """Raised when an internal agent processing error occurs.

    This error indicates an unexpected failure during agent processing
    that is not the client's fault.
    """

    def __init__(self, message: str, agent_id: Optional[str] = None) -> None:
        """Initialize agent processing error.

        Args:
            message: Description of the processing failure
            agent_id: Optional agent ID for additional context
        """
        if agent_id:
            full_message = f"Agent '{agent_id}': {message}"
        else:
            full_message = message

        super().__init__(
            message=full_message,
            code="agent_processing_error",
            status_code=500,
        )
        self.agent_id = agent_id


class UnauthorizedError(AgentError):
    """Raised when authentication is required but not provided.

    This error indicates that the request requires authentication
    but no valid credentials were provided.
    """

    def __init__(self, message: str = "Authentication required") -> None:
        """Initialize unauthorized error.

        Args:
            message: Description of the authentication requirement
        """
        super().__init__(
            message=message,
            code="unauthorized",
            status_code=401,
        )


class ForbiddenError(AgentError):
    """Raised when user lacks permission for the requested operation.

    This error indicates that the user is authenticated but does not
    have the required permissions to perform the operation.
    """

    def __init__(self, message: str = "Insufficient permissions") -> None:
        """Initialize forbidden error.

        Args:
            message: Description of the permission denial
        """
        super().__init__(
            message=message,
            code="forbidden",
            status_code=403,
        )


class TenantIsolationError(AgentError):
    """Raised when a tenant isolation violation is detected.

    This error indicates that a user attempted to access resources
    belonging to a different tenant.
    """

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize tenant isolation error.

        Args:
            resource_type: Type of resource (e.g., "agent", "task")
            resource_id: ID of the resource that was accessed
        """
        super().__init__(
            message=f"Access denied: {resource_type} '{resource_id}' "
            f"belongs to a different tenant",
            code="tenant_isolation_violation",
            status_code=403,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id
