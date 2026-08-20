"""Shared Rich styling: theme, banner, console."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "shelf.brand": "bold #7eb8c9",
        "shelf.accent": "bold #e8b86d",
        "shelf.ok": "bold #8fbf8f",
        "shelf.warn": "bold #e8b86d",
        "shelf.err": "bold #d98989",
        "shelf.muted": "dim",
        "shelf.cat": "#c9a0dc",
        "shelf.path": "italic #a8b4c4",
    }
)

console = Console(theme=THEME)


def banner(
    subtitle: str | None = None,
    *,
    dry_run: bool | None = None,
    path: str | None = None,
) -> Panel:
    title = Text()
    title.append("fileshelf", style="shelf.brand")
    title.append("  ·  ", style="shelf.muted")
    title.append("smart file organizer", style="shelf.accent")

    body = Text()
    body.append(title)
    if subtitle or dry_run is not None or path:
        body.append("\n")
        bits: list[str] = []
        if dry_run is True:
            bits.append("dry-run")
        elif dry_run is False:
            bits.append("APPLY")
        if path:
            bits.append(path)
        if subtitle:
            bits.append(subtitle)
        body.append("  ·  ".join(bits), style="shelf.muted")

    return Panel(
        body,
        border_style="#3d4f63",
        padding=(0, 1),
    )
