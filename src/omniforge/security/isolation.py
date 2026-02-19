"""Tenant isolation enforcement utilities.

This module provides helper functions to enforce tenant isolation
across different resource types (agents, tasks).
"""

from typing import Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.errors import TenantIsolationError
from omniforge.security.tenant import get_tenant_id
from omniforge.tasks.models import Task


def enforce_agent_isolation(agent: BaseAgent) -> None:
    """Enforce tenant isolation for an agent resource.

    Verifies that the current tenant context matches the agent's tenant.
    Raises an error if there is a tenant mismatch.

    Args:
        agent: The agent to check

    Raises:
        TenantIsolationError: If agent belongs to a different tenant
    """
    current_tenant = get_tenant_id()

    # If no current tenant context, allow access (for backwards compatibility)
    if current_tenant is None:
        return

    # If agent has no tenant_id, it's a shared agent (allow access)
    if not hasattr(agent, "tenant_id") or agent.tenant_id is None:
        return

    # Check for tenant mismatch
    if agent.tenant_id != current_tenant:
        raise TenantIsolationError("agent", agent.identity.id)


def enforce_task_isolation(task: Task) -> None:
    """Enforce tenant isolation for a task resource.

    Verifies that the current tenant context matches the task's tenant.
    Raises an error if there is a tenant mismatch.

    Args:
        task: The task to check

    Raises:
        TenantIsolationError: If task belongs to a different tenant
    """
    current_tenant = get_tenant_id()

    # If no current tenant context, allow access (for backwards compatibility)
    if current_tenant is None:
        return

    # If task has no tenant_id, it's a shared task (allow access)
    if task.tenant_id is None:
        return

    # Check for tenant mismatch
    if task.tenant_id != current_tenant:
        raise TenantIsolationError("task", task.id)


def filter_by_tenant(resources: list, current_tenant: Optional[str] = None) -> list:
    """Filter a list of resources by current tenant.

    Returns only resources that belong to the current tenant or
    are shared (tenant_id is None).

    Args:
        resources: List of resources to filter (agents, tasks, etc.)
        current_tenant: Optional tenant ID to filter by (uses context if None)

    Returns:
        Filtered list of resources

    Examples:
        >>> from omniforge.security.tenant import TenantContext
        >>> TenantContext.set("tenant-1")
        >>> agents = [agent1, agent2, agent3]  # Mixed tenant agents
        >>> filtered = filter_by_tenant(agents)
        >>> # Returns only agents for tenant-1
    """
    tenant_id = current_tenant or get_tenant_id()

    # If no tenant context, return all resources
    if tenant_id is None:
        return resources

    # Filter to resources matching tenant or shared resources
    return [
        resource
        for resource in resources
        if (
            (hasattr(resource, "tenant_id") and resource.tenant_id == tenant_id)
            or (hasattr(resource, "tenant_id") and resource.tenant_id is None)
        )
    ]
