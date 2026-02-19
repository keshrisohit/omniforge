"""Agent management CLI commands.

Provides commands for listing, running, testing, and monitoring agents.
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from omniforge.builder.executor import AgentExecutionService, AgentExecutor
from omniforge.builder.models import ExecutionStatus
from omniforge.builder.repository import (
    AgentConfigRepository,
    AgentExecutionRepository,
)
from omniforge.builder.skill_generator import SkillMdGenerator

console = Console()


def get_tenant_id(tenant: Optional[str]) -> str:
    """Get tenant ID from flag or environment variable.

    Args:
        tenant: Tenant ID from CLI flag

    Returns:
        Tenant ID to use

    Raises:
        click.ClickException: If no tenant ID provided
    """
    tenant_id = tenant or os.getenv("OMNIFORGE_TENANT_ID", "default")

    if not tenant_id or tenant_id == "":
        raise click.ClickException(
            "No tenant ID provided. Use --tenant flag or set "
            "OMNIFORGE_TENANT_ID environment variable."
        )

    return tenant_id


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Get async database session.

    Yields:
        AsyncSession for database operations
    """
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///omniforge.db")
    engine = create_async_engine(db_url, echo=False)

    session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:  # type: ignore
        try:
            yield session  # type: ignore
        finally:
            await engine.dispose()


@click.group(name="agent")
def agent() -> None:
    """Manage agents."""
    pass


@agent.command(name="list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (table or json)",
)
@click.option(
    "--tenant",
    type=str,
    help="Tenant ID (defaults to OMNIFORGE_TENANT_ID environment variable or 'default')",
)
@click.option(
    "--status",
    type=click.Choice(["draft", "active", "paused", "archived"], case_sensitive=False),
    help="Filter by agent status",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of agents to display",
)
def list_agents(
    output_format: str,
    tenant: Optional[str],
    status: Optional[str],
    limit: int,
) -> None:
    """List all agents.

    Examples:
        omniforge agent list
        omniforge agent list --format json
        omniforge agent list --tenant tenant-123 --status active
    """
    tenant_id = get_tenant_id(tenant)

    async def _list() -> None:
        async with get_session() as session:
            repo = AgentConfigRepository(session)
            agents = await repo.list_by_tenant(
                tenant_id=tenant_id,
                status=status,
                limit=limit,
            )

            if output_format == "json":
                # JSON output
                output = [
                    {
                        "id": agent.id,
                        "name": agent.name,
                        "description": agent.description,
                        "status": agent.status.value,
                        "trigger": agent.trigger.value,
                        "schedule": agent.schedule,
                        "skills_count": len(agent.skills),
                        "created_at": agent.created_at.isoformat() if agent.created_at else None,
                        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
                    }
                    for agent in agents
                ]
                click.echo(json.dumps(output, indent=2))
            else:
                # Table output
                table = Table(title=f"Agents for Tenant: {tenant_id}")
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Name", style="green")
                table.add_column("Status", style="yellow")
                table.add_column("Trigger", style="blue")
                table.add_column("Skills", justify="right")
                table.add_column("Created", style="dim")

                for agent in agents:
                    table.add_row(
                        agent.id or "N/A",
                        agent.name,
                        agent.status.value,
                        agent.trigger.value,
                        str(len(agent.skills)),
                        agent.created_at.strftime("%Y-%m-%d %H:%M") if agent.created_at else "N/A",
                    )

                console.print(table)

                if not agents:
                    console.print("[yellow]No agents found.[/yellow]")

    asyncio.run(_list())


@agent.command(name="run")
@click.argument("agent_id", type=str)
@click.option(
    "--tenant",
    type=str,
    help="Tenant ID (defaults to OMNIFORGE_TENANT_ID environment variable or 'default')",
)
def run_agent(agent_id: str, tenant: Optional[str]) -> None:
    """Execute an agent manually.

    Examples:
        omniforge agent run agent-123
        omniforge agent run agent-123 --tenant tenant-456
    """
    tenant_id = get_tenant_id(tenant)

    async def _run() -> None:
        async with get_session() as session:
            agent_repo = AgentConfigRepository(session)
            execution_repo = AgentExecutionRepository(session)

            # Get skills directory
            skills_dir = Path(os.getenv("OMNIFORGE_SKILLS_DIR", "./skills"))
            skills_dir.mkdir(parents=True, exist_ok=True)

            # Create executor
            skill_generator = SkillMdGenerator()
            executor = AgentExecutor(skill_generator, skills_dir)
            service = AgentExecutionService(executor, agent_repo, execution_repo)

            console.print(f"[blue]Executing agent {agent_id}...[/blue]")

            try:
                execution = await service.execute_agent_by_id(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    trigger_type="on_demand",
                )

                await session.commit()

                if execution.status == ExecutionStatus.SUCCESS:
                    console.print("[green]✓ Execution successful[/green]")
                    console.print(f"Execution ID: {execution.id}")
                    console.print(f"Duration: {execution.duration_ms}ms")

                    if execution.output:
                        console.print("\nOutput:")
                        console.print(json.dumps(execution.output, indent=2))
                else:
                    console.print("[red]✗ Execution failed[/red]")
                    console.print(f"Status: {execution.status.value}")
                    if execution.error:
                        console.print(f"Error: {execution.error}")
                    sys.exit(1)

            except ValueError as e:
                raise click.ClickException(str(e))
            except Exception as e:
                raise click.ClickException(f"Execution failed: {e}")

    asyncio.run(_run())


@agent.command(name="test")
@click.argument("agent_id", type=str)
@click.option(
    "--dry-run",
    is_flag=True,
    required=True,
    help="Run in test mode without real API calls",
)
@click.option(
    "--tenant",
    type=str,
    help="Tenant ID (defaults to OMNIFORGE_TENANT_ID environment variable or 'default')",
)
def test_agent(agent_id: str, dry_run: bool, tenant: Optional[str]) -> None:
    """Test an agent without real API calls.

    Examples:
        omniforge agent test agent-123 --dry-run
        omniforge agent test agent-123 --dry-run --tenant tenant-456
    """
    tenant_id = get_tenant_id(tenant)

    async def _test() -> None:
        async with get_session() as session:
            agent_repo = AgentConfigRepository(session)

            # Load agent config
            agent_config = await agent_repo.get_by_id(agent_id, tenant_id)
            if not agent_config:
                raise click.ClickException(f"Agent {agent_id} not found for tenant {tenant_id}")

            console.print(f"[blue]Testing agent: {agent_config.name}[/blue]")
            console.print(f"Description: {agent_config.description}")
            console.print(f"Status: {agent_config.status.value}")
            console.print(f"Trigger: {agent_config.trigger.value}")
            console.print(f"Skills: {len(agent_config.skills)}")

            # Display skills
            table = Table(title="Skills to Execute")
            table.add_column("Order", justify="right")
            table.add_column("Skill ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Source", style="yellow")

            for skill in sorted(agent_config.skills, key=lambda s: s.order):
                table.add_row(
                    str(skill.order),
                    skill.skill_id,
                    skill.name,
                    skill.source,
                )

            console.print(table)
            console.print("[yellow]Note: Dry-run mode - no actual API calls will be made[/yellow]")

    asyncio.run(_test())


@agent.command(name="status")
@click.argument("agent_id", type=str)
@click.option(
    "--tenant",
    type=str,
    help="Tenant ID (defaults to OMNIFORGE_TENANT_ID environment variable or 'default')",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of recent executions to show (default: 10)",
)
def agent_status(agent_id: str, tenant: Optional[str], limit: int) -> None:
    """Show execution history for an agent.

    Examples:
        omniforge agent status agent-123
        omniforge agent status agent-123 --tenant tenant-456 --limit 20
    """
    tenant_id = get_tenant_id(tenant)

    async def _status() -> None:
        async with get_session() as session:
            agent_repo = AgentConfigRepository(session)
            execution_repo = AgentExecutionRepository(session)

            # Verify agent exists
            agent_config = await agent_repo.get_by_id(agent_id, tenant_id)
            if not agent_config:
                raise click.ClickException(f"Agent {agent_id} not found for tenant {tenant_id}")

            console.print(f"[blue]Agent: {agent_config.name}[/blue]")
            console.print(f"Status: {agent_config.status.value}")
            console.print()

            # Get executions
            executions = await execution_repo.list_by_agent(
                agent_id=agent_id,
                tenant_id=tenant_id,
                limit=limit,
            )

            if not executions:
                console.print("[yellow]No execution history found.[/yellow]")
                return

            # Display executions table
            table = Table(title=f"Last {len(executions)} Executions")
            table.add_column("Execution ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="yellow")
            table.add_column("Trigger", style="blue")
            table.add_column("Started", style="dim")
            table.add_column("Duration", justify="right")
            table.add_column("Error", style="red")

            for execution in executions:
                status_color = (
                    "green"
                    if execution.status == ExecutionStatus.SUCCESS
                    else "red" if execution.status == ExecutionStatus.FAILED else "yellow"
                )

                table.add_row(
                    execution.id or "N/A",
                    f"[{status_color}]{execution.status.value}[/{status_color}]",
                    execution.trigger_type,
                    (
                        execution.started_at.strftime("%Y-%m-%d %H:%M:%S")
                        if execution.started_at
                        else "N/A"
                    ),
                    f"{execution.duration_ms}ms" if execution.duration_ms is not None else "N/A",
                    (execution.error[:50] + "...") if execution.error else "",
                )

            console.print(table)

    asyncio.run(_status())
