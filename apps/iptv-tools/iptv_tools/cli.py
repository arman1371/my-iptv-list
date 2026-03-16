import click
import uvicorn


@click.group()
def cli():
    """IPTV Tools — a CLI toolbox for IPTV utilities."""
    pass


@cli.command()
@click.option(
    "--host", default="0.0.0.0", show_default=True, help="Host to bind the server to."
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Port to bind the server to.",
)
def serve(host: str, port: int):
    """Start the IPTV Tools API server."""
    click.echo(f"Starting IPTV Tools API on http://{host}:{port}")
    uvicorn.run(
        "iptv_tools.api.app:app",
        host=host,
        port=port,
        reload=False,
    )
