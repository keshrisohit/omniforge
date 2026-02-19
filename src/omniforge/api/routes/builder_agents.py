"""Builder agent API route handlers.

This module provides FastAPI route handlers for agent CRUD operations,
including listing, retrieving, updating, deleting, and executing agents
created through the conversational builder.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from omniforge.api.dependencies import get_current_tenant
from omniforge.api.schemas.builder import (
    AgentDetailResponse,
    AgentExecutionResponse,
    AgentExecutionsListResponse,
    AgentListResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentSummary,
)

# Create router with prefix and tags
router = APIRouter(prefix="/api/v1/builder/agents", tags=["builder-agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> AgentListResponse:
    """List all agents for the current tenant.

    Returns a summary view of all agents created by users in the current tenant.
    Includes basic information like name, status, trigger type, and last run time.

    Args:
        tenant_id: Current tenant ID from middleware

    Returns:
        AgentListResponse containing list of agent summaries

    Raises:
        HTTPException: If tenant_id is not available

    Examples:
        >>> GET /api/v1/builder/agents
        >>>
        >>> {
        >>>   "agents": [
        >>>     {
        >>>       "id": "agent-123",
        >>>       "name": "Weekly Reporter",
        >>>       "description": "Generates weekly reports",
        >>>       "status": "active",
        >>>       "trigger_type": "scheduled",
        >>>       "skills": [...],
        >>>       "last_run": "2026-01-25T10:00:00Z"
        >>>     }
        >>>   ]
        >>> }
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # TODO: Fetch agents from repository
    # For now, return empty list as placeholder
    agents: list[AgentSummary] = []

    return AgentListResponse(agents=agents)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: str,
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> AgentDetailResponse:
    """Get detailed information about a specific agent.

    Returns complete agent configuration including all skills, integrations,
    trigger settings, and usage statistics.

    Args:
        agent_id: Unique agent identifier
        tenant_id: Current tenant ID from middleware

    Returns:
        AgentDetailResponse with full agent configuration

    Raises:
        HTTPException: If tenant_id missing or agent not found

    Examples:
        >>> GET /api/v1/builder/agents/agent-123
        >>>
        >>> {
        >>>   "id": "agent-123",
        >>>   "name": "Weekly Reporter",
        >>>   "description": "Generates weekly reports from Notion",
        >>>   "status": "active",
        >>>   "trigger_type": "scheduled",
        >>>   "schedule": "0 8 * * MON",
        >>>   "skills": [...],
        >>>   "integrations": ["integration-notion-456"],
        >>>   "usage_stats": {...}
        >>> }
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # TODO: Fetch agent from repository
    # For now, return 404 as placeholder
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_id: str,
    body: AgentRunRequest,
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> AgentRunResponse:
    """Execute an agent on-demand.

    Triggers immediate execution of the specified agent, even if it's configured
    for scheduled or event-driven execution. Returns an execution ID that can be
    used to track progress and retrieve results.

    Args:
        agent_id: Unique agent identifier
        body: AgentRunRequest with optional input parameters
        tenant_id: Current tenant ID from middleware

    Returns:
        AgentRunResponse with execution_id and status

    Raises:
        HTTPException: If tenant_id missing, agent not found, or execution fails

    Examples:
        >>> POST /api/v1/builder/agents/agent-123/run
        >>> {
        >>>   "input_data": {"timeframe": "7 days"}
        >>> }
        >>>
        >>> {
        >>>   "execution_id": "exec-789",
        >>>   "status": "pending"
        >>> }
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # TODO: Fetch agent and trigger execution via executor
    # For now, return placeholder response
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"

    return AgentRunResponse(
        execution_id=execution_id,
        status="pending",
    )


@router.get("/{agent_id}/executions", response_model=AgentExecutionsListResponse)
async def list_agent_executions(
    agent_id: str,
    tenant_id: Optional[str] = Depends(get_current_tenant),
    limit: int = 20,
    offset: int = 0,
) -> AgentExecutionsListResponse:
    """List execution history for a specific agent.

    Returns paginated list of past executions with status, timing, outputs,
    and any errors. Useful for monitoring agent performance and debugging.

    Args:
        agent_id: Unique agent identifier
        tenant_id: Current tenant ID from middleware
        limit: Maximum number of executions to return (default: 20)
        offset: Number of executions to skip for pagination (default: 0)

    Returns:
        AgentExecutionsListResponse with list of execution results

    Raises:
        HTTPException: If tenant_id missing or agent not found

    Examples:
        >>> GET /api/v1/builder/agents/agent-123/executions?limit=10&offset=0
        >>>
        >>> {
        >>>   "executions": [
        >>>     {
        >>>       "id": "exec-789",
        >>>       "agent_id": "agent-123",
        >>>       "status": "completed",
        >>>       "started_at": "2026-01-25T10:00:00Z",
        >>>       "completed_at": "2026-01-25T10:01:30Z",
        >>>       "duration_ms": 90000,
        >>>       "output": {...},
        >>>       "skill_executions": [...]
        >>>     }
        >>>   ]
        >>> }
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # TODO: Fetch executions from repository with pagination
    # For now, return empty list
    executions: list[AgentExecutionResponse] = []

    return AgentExecutionsListResponse(executions=executions)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> None:
    """Delete an agent and all its associated data.

    Permanently removes the agent configuration, skill files, and execution
    history. This action cannot be undone.

    Args:
        agent_id: Unique agent identifier
        tenant_id: Current tenant ID from middleware

    Raises:
        HTTPException: If tenant_id missing or agent not found

    Examples:
        >>> DELETE /api/v1/builder/agents/agent-123
        >>>
        >>> # Returns 204 No Content on success
    """
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")

    # TODO: Delete agent from repository
    # For now, return 404
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
