"""AgentForge CLI — server management and admin utilities."""
import typer
import uvicorn
from typing import Optional

app = typer.Typer(
    name="agentforge",
    help="AgentForge — Mega AI Agent Platform CLI",
    add_completion=False,
)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    workers: int = typer.Option(1, help="Number of worker processes"),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev only)"),
    env: Optional[str] = typer.Option(None, help="Override APP_ENV"),
) -> None:
    """Start the AgentForge API server."""
    if env:
        import os
        os.environ["APP_ENV"] = env
    typer.echo(f"Starting AgentForge on {host}:{port} (workers={workers}, reload={reload})")
    uvicorn.run(
        "agentforge.api.main:app",
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        log_level="info",
    )


@app.command()
def skills(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search skills by keyword"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """List available skills in the catalog."""
    from agentforge.skills.registry import SkillRegistry
    registry = SkillRegistry()
    registry.auto_discover("agentforge.skills.catalog")

    if search:
        results = registry.search(search)
    elif category:
        results = registry.list_category(category)
    else:
        results = registry.list_all()

    if not results:
        typer.echo("No skills found.")
        raise typer.Exit()

    typer.echo(f"\n{'NAME':<30} {'CATEGORY':<20} {'LEVEL':<15} DESCRIPTION")
    typer.echo("-" * 90)
    for s in results:
        typer.echo(f"{s.name:<30} {s.category:<20} {s.level:<15} {s.description[:60]}")
    typer.echo(f"\nTotal: {len(results)} skill(s)")


@app.command()
def version() -> None:
    """Show AgentForge version."""
    typer.echo("AgentForge v0.1.0")


if __name__ == "__main__":
    app()
