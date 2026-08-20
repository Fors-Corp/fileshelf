"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table
from rich.text import Text

from fileshelf import __version__
from fileshelf.classify import category_order
from fileshelf.format import human_mtime, human_size
from fileshelf.scanner import scan as scan_dir
from fileshelf.ui import banner, console

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Smart file organizer with a polished terminal UI.",
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"fileshelf {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    return


@app.command()
def about() -> None:
    """Show what fileshelf is and the current version."""
    console.print(banner(subtitle=f"v{__version__}"))
    console.print(
        "Local-only organizer: classify, plan a shelf layout, then move "
        "files when you say so.\n"
        "Dry-run is the default. See [bold]ROADMAP.md[/bold] for the feature plan."
    )


@app.command()
def scan(
    path: Path = typer.Argument(
        Path("."),
        exists=False,
        help="Folder to inspect.",
        show_default="current directory",
    ),
    recursive: bool = typer.Option(True, "--recursive/--one-level", help="Walk subfolders."),
    hidden: bool = typer.Option(False, "--hidden", help="Include hidden files and folders."),
    limit: int = typer.Option(0, "--limit", min=0, help="Show at most N files (0 = summary only)."),
) -> None:
    """Classify files in a folder. Read-only."""
    root = path.expanduser()
    console.print(banner(path=str(root), subtitle="scan"))

    with console.status("[shelf.muted]scanning…[/]"):
        result = scan_dir(root, recursive=recursive, include_hidden=hidden)

    if result.errors and not result.files:
        for err in result.errors:
            console.print(f"[shelf.err]{err}[/]")
        raise typer.Exit(code=1)

    groups = result.by_category()
    table = Table(
        title="Classification",
        border_style="#3d4f63",
        header_style="shelf.accent",
        show_lines=False,
    )
    table.add_column("Category", style="shelf.cat")
    table.add_column("Files", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Oldest", style="shelf.muted")
    table.add_column("Newest", style="shelf.muted")

    order = list(category_order())
    for cat in order:
        items = groups.get(cat)
        if not items:
            continue
        table.add_row(
            cat,
            str(len(items)),
            human_size(sum(i.size_bytes for i in items)),
            human_mtime(min(i.mtime for i in items)),
            human_mtime(max(i.mtime for i in items)),
        )
    for cat, items in groups.items():
        if cat not in order:
            table.add_row(
                cat,
                str(len(items)),
                human_size(sum(i.size_bytes for i in items)),
                human_mtime(min(i.mtime for i in items)),
                human_mtime(max(i.mtime for i in items)),
            )

    console.print(table)
    summary = Text()
    summary.append(f"{len(result.files)} files", style="shelf.brand")
    summary.append("  ·  ", style="shelf.muted")
    summary.append(human_size(result.total_size), style="shelf.accent")
    if result.skipped_dirs:
        summary.append("  ·  ", style="shelf.muted")
        summary.append(f"{result.skipped_dirs} dirs skipped", style="shelf.muted")
    console.print(summary)

    if limit > 0:
        files_table = Table(
            title=f"Files (first {min(limit, len(result.files))})",
            border_style="#3d4f63",
            header_style="shelf.accent",
        )
        files_table.add_column("Category", style="shelf.cat")
        files_table.add_column("Size", justify="right")
        files_table.add_column("Name")
        files_table.add_column("Why", style="shelf.muted")
        for item in result.files[:limit]:
            rel = item.path.relative_to(result.root) if item.path.is_relative_to(result.root) else item.path
            files_table.add_row(
                item.subcategory or item.category,
                human_size(item.size_bytes),
                str(rel),
                item.reason,
            )
        console.print(files_table)

    if result.errors:
        console.print(f"[shelf.warn]{len(result.errors)} paths skipped due to errors[/]")
