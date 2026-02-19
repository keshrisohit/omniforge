"""Main CLI entry point for OmniForge.

Provides command-line interface for agent management and orchestration.
"""

import click

from omniforge.cli import agent


@click.group()
@click.version_option(version="0.1.0", prog_name="omniforge")
def cli() -> None:
    """OmniForge - Enterprise-grade AI agent platform."""
    pass


# Register command groups
cli.add_command(agent.agent)


def main() -> None:
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
