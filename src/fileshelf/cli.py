"""Typer CLI entrypoint."""

from __future__ import annotations

import typer

from fileshelf import __version__
from fileshelf.ui import banner, console

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Smart file organizer with a polished terminal UI.",
)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
    ),
) -> None:
    if version:
        console.print(f"fileshelf {__version__}")
        raise typer.Exit()


@app.command()
def about() -> None:
    """Show what fileshelf is and the current version."""
    console.print(banner(subtitle=f"v{__version__}"))
    console.print(
        "Local-only organizer: classify, plan a shelf layout, then move "
        "files when you say so.\n"
        "Dry-run is the default. See [bold]ROADMAP.md[/bold] for the feature plan."
    )
