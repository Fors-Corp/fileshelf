"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from fileshelf import __version__
from fileshelf.apply import apply_plan
from fileshelf.classify import category_order
from fileshelf.config import Config, config_path, dump_config, load_config, write_default_config
from fileshelf.duplicates import find_duplicates
from fileshelf.format import human_mtime, human_size
from fileshelf.planner import LAYOUTS, plan_from_scan
from fileshelf.render import plan_summary, plan_table, plan_tree
from fileshelf.safety import deny_reason, is_home
from fileshelf.journal import data_dir, history_dir, list_sessions
from fileshelf.scanner import scan as scan_dir
from fileshelf.ui import banner, console
from fileshelf.undo import latest_undoable, undo_session

SUPPORT_LINE = "Support this project: https://marcfors.com/donate?from=fileshelf"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Smart file organizer with a polished terminal UI.",
    epilog=SUPPORT_LINE,
)
config_app = typer.Typer(no_args_is_help=True, help="View or create ~/.fileshelf/config.toml.")
app.add_typer(config_app, name="config")


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


def _cfg() -> Config:
    return load_config()


def _protect_extra(cfg: Config) -> tuple[Path, ...]:
    return (Path.home() / "Library", *cfg.protect_paths)


def _assert_allowed(
    root: Path,
    cfg: Config,
    *,
    dest: Path | None = None,
    force_home: bool = False,
    applying: bool = False,
) -> None:
    extra = _protect_extra(cfg)
    reason = deny_reason(root, extra)
    if reason:
        console.print(f"[shelf.err]Refusing to touch {root}: {reason}[/]")
        raise typer.Exit(code=1)
    if dest is not None:
        dest_reason = deny_reason(dest.expanduser(), extra)
        if dest_reason:
            console.print(f"[shelf.err]Refusing destination {dest}: {dest_reason}[/]")
            raise typer.Exit(code=1)
    if applying and is_home(root) and not force_home:
        console.print(
            "[shelf.err]Refusing to organize $HOME without --force-home "
            "(that would reshuffle your whole home directory)[/]"
        )
        raise typer.Exit(code=1)


def _scan_or_exit(root: Path, cfg: Config, recursive: bool, hidden: bool):
    with console.status("[shelf.muted]scanning…[/]"):
        result = scan_dir(
            root,
            recursive=recursive,
            include_hidden=hidden,
            extra_skip_dirs=set(cfg.skip_directories),
            rules=cfg.rules,
        )
    if result.errors and not result.files:
        for err in result.errors:
            console.print(f"[shelf.err]{err}[/]")
        raise typer.Exit(code=1)
    return result


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
    cfg = _cfg()
    root = path.expanduser()
    _assert_allowed(root, cfg)
    console.print(banner(path=str(root), subtitle="scan"))
    result = _scan_or_exit(root, cfg, recursive, hidden)

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


@app.command()
def plan(
    path: Path = typer.Argument(
        Path("."),
        help="Folder to organize.",
        show_default="current directory",
    ),
    dest: Path | None = typer.Option(
        None,
        "--dest",
        "-d",
        help="Shelf root (defaults to the scanned folder).",
    ),
    layout: str | None = typer.Option(
        None,
        "--layout",
        "-l",
        help="Shelf layout: smart, type, date, type-date.",
    ),
    recursive: bool = typer.Option(True, "--recursive/--one-level"),
    hidden: bool = typer.Option(False, "--hidden"),
    skip_duplicates: bool = typer.Option(False, "--skip-duplicates", help="Leave extra duplicates unmoved."),
    tree: bool = typer.Option(False, "--tree", help="Show destination tree instead of a file table."),
    limit: int = typer.Option(30, "--limit", min=0, help="Max rows in the file table (0 = all)."),
) -> None:
    """Preview where files would be shelved. Read-only."""
    cfg = _cfg()
    layout = layout or cfg.layout
    if layout not in LAYOUTS:
        console.print(f"[shelf.err]Unknown layout '{layout}'. Choose from: {', '.join(LAYOUTS)}[/]")
        raise typer.Exit(code=2)

    root = path.expanduser()
    _assert_allowed(root, cfg, dest=dest)
    console.print(banner(path=str(root), dry_run=True, subtitle=f"layout: {layout}"))
    result = _scan_or_exit(root, cfg, recursive, hidden)
    organized = plan_from_scan(
        result,
        dest=dest,
        layout=layout,
        skip_duplicates=skip_duplicates or cfg.skip_duplicates,
    )

    if tree:
        console.print(plan_tree(organized))
    else:
        console.print(plan_table(organized, limit=limit))
        if limit and organized.move_count > limit:
            console.print(f"[shelf.muted]showing {limit} of {organized.move_count} moves — pass --limit 0 for all[/]")
    console.print(plan_summary(organized))


@app.command()
def organize(
    path: Path = typer.Argument(
        Path("."),
        help="Folder to organize.",
        show_default="current directory",
    ),
    dest: Path | None = typer.Option(None, "--dest", "-d", help="Shelf root (defaults to the scanned folder)."),
    layout: str | None = typer.Option(None, "--layout", "-l", help="Shelf layout: smart, type, date, type-date."),
    apply_moves: bool = typer.Option(False, "--apply", help="Actually move files. Dry-run otherwise."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt (with --apply)."),
    conflict: str | None = typer.Option(
        None,
        "--conflict",
        help="When the destination exists: rename, skip, or overwrite.",
    ),
    recursive: bool = typer.Option(True, "--recursive/--one-level"),
    hidden: bool = typer.Option(False, "--hidden"),
    skip_duplicates: bool = typer.Option(False, "--skip-duplicates", help="Leave extra duplicates unmoved."),
    force_home: bool = typer.Option(False, "--force-home", help="Allow organizing $HOME (dangerous)."),
    limit: int = typer.Option(30, "--limit", min=0),
) -> None:
    """Move files onto shelves. Dry-run unless --apply is passed."""
    cfg = _cfg()
    layout = layout or cfg.layout
    conflict = conflict or cfg.conflict
    if layout not in LAYOUTS:
        console.print(f"[shelf.err]Unknown layout '{layout}'. Choose from: {', '.join(LAYOUTS)}[/]")
        raise typer.Exit(code=2)
    if conflict not in {"rename", "skip", "overwrite"}:
        console.print("[shelf.err]--conflict must be rename, skip, or overwrite[/]")
        raise typer.Exit(code=2)

    root = path.expanduser()
    _assert_allowed(root, cfg, dest=dest, force_home=force_home, applying=apply_moves)
    console.print(
        banner(
            path=str(root),
            dry_run=not apply_moves,
            subtitle=f"layout: {layout}",
        )
    )
    result = _scan_or_exit(root, cfg, recursive, hidden)
    organized = plan_from_scan(
        result,
        dest=dest,
        layout=layout,
        skip_duplicates=skip_duplicates or cfg.skip_duplicates,
    )
    console.print(plan_table(organized, limit=limit))
    console.print(plan_summary(organized))

    if not organized.actions:
        console.print("[shelf.muted]Nothing to move.[/]")
        raise typer.Exit()

    if not apply_moves:
        console.print("[shelf.muted]Dry-run only. Pass --apply to move files.[/]")
        raise typer.Exit()

    if not yes:
        from rich.prompt import Confirm

        if not Confirm.ask(
            f"[shelf.warn]Move {organized.move_count} files now?[/]",
            default=False,
        ):
            console.print("[shelf.muted]Cancelled.[/]")
            raise typer.Exit()

    applied = apply_plan(
        organized,
        dry_run=False,
        conflict=conflict,
        extra_deny=_protect_extra(cfg),
        force_home=force_home,
    )
    if applied.errors and not applied.moved:
        for err in applied.errors:
            console.print(f"[shelf.err]{err}[/]")
        raise typer.Exit(code=1)

    console.print(
        f"[shelf.ok]Moved {len(applied.moved)} files[/]  ·  session [bold]{applied.session_id}[/]"
    )
    if applied.journal_path:
        console.print(f"[shelf.muted]journal: {applied.journal_path}[/]")
    if applied.skipped:
        console.print(f"[shelf.warn]Skipped {len(applied.skipped)} files[/]")
    for err in applied.errors:
        console.print(f"[shelf.err]{err}[/]")


@app.command()
def tui(
    path: Path = typer.Argument(
        Path("."),
        help="Folder to organize.",
        show_default="current directory",
    ),
    dest: Path | None = typer.Option(None, "--dest", "-d", help="Shelf root (defaults to the scanned folder)."),
    layout: str | None = typer.Option(None, "--layout", "-l", help="Shelf layout: smart, type, date, type-date."),
    recursive: bool = typer.Option(True, "--recursive/--one-level", help="Walk subfolders, or only the top level."),
    force_home: bool = typer.Option(False, "--force-home", help="Allow organizing $HOME (dangerous)."),
) -> None:
    """Interactive terminal UI for reviewing and applying a plan."""
    from fileshelf.tui import run_tui

    cfg = _cfg()
    layout = layout or cfg.layout
    if layout not in LAYOUTS:
        console.print(f"[shelf.err]Unknown layout '{layout}'. Choose from: {', '.join(LAYOUTS)}[/]")
        raise typer.Exit(code=2)
    root = path.expanduser().resolve()
    _assert_allowed(root, cfg, dest=dest, force_home=force_home, applying=False)
    run_tui(root, dest=dest, layout=layout, force_home=force_home, recursive=recursive)


@app.command()
def duplicates(
    path: Path = typer.Argument(
        Path("."),
        help="Folder to inspect.",
        show_default="current directory",
    ),
    recursive: bool = typer.Option(True, "--recursive/--one-level"),
    hidden: bool = typer.Option(False, "--hidden"),
) -> None:
    """Find duplicate files by content hash. Read-only."""
    cfg = _cfg()
    root = path.expanduser()
    _assert_allowed(root, cfg)
    console.print(banner(path=str(root), subtitle="duplicates"))
    result = _scan_or_exit(root, cfg, recursive, hidden)
    with console.status("[shelf.muted]hashing…[/]"):
        groups = find_duplicates(result.files)

    if not groups:
        console.print("[shelf.ok]No duplicates found.[/]")
        raise typer.Exit()

    table = Table(
        title="Duplicate groups (newest kept first)",
        border_style="#3d4f63",
        header_style="shelf.accent",
    )
    table.add_column("Copies", justify="right")
    table.add_column("Size each", justify="right")
    table.add_column("Wasted", justify="right", style="shelf.warn")
    table.add_column("Hash", style="shelf.muted")
    table.add_column("Files")

    wasted = 0
    extra_count = 0
    for group in groups:
        extra = group.extras
        extra_count += len(extra)
        wasted += group.size_bytes * len(extra)
        names = "\n".join(str(f.path.relative_to(result.root)) if f.path.is_relative_to(result.root) else str(f.path) for f in group.files)
        table.add_row(
            str(len(group.files)),
            human_size(group.size_bytes),
            human_size(group.size_bytes * len(extra)),
            group.digest[:12],
            names,
        )
    console.print(table)
    extra_label = "extra copy" if extra_count == 1 else "extra copies"
    console.print(
        f"[shelf.warn]{extra_count} {extra_label}[/]  ·  [shelf.accent]{human_size(wasted)} wasted[/]  ·  "
        "[shelf.muted]pass --skip-duplicates on plan/organize to leave extras unmoved[/]"
    )


@config_app.command("show")
def config_show() -> None:
    """Print the loaded configuration."""
    path = config_path()
    cfg = load_config()
    console.print(banner(subtitle="config"))
    if path.exists():
        console.print(f"[shelf.muted]{path}[/]")
        console.print(Syntax(path.read_text(encoding="utf-8"), "toml", theme="ansi_dark", word_wrap=True))
    else:
        console.print(f"[shelf.muted]No file at {path} — showing built-in defaults. Run [bold]shelf config init[/bold].[/]")
        console.print(Syntax(dump_config(cfg), "toml", theme="ansi_dark", word_wrap=True))


@config_app.command("init")
def config_init(
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing config file."),
) -> None:
    """Write a default config to ~/.fileshelf/config.toml."""
    path = write_default_config(overwrite=overwrite)
    console.print(f"[shelf.ok]Wrote {path}[/]")


@app.command("history")
def history_cmd() -> None:
    """List applied organization sessions."""
    console.print(banner(subtitle="history"))
    sessions = list_sessions()
    if not sessions:
        console.print("[shelf.muted]No sessions yet. Apply a plan with [bold]shelf organize --apply[/bold].[/]")
        raise typer.Exit()

    table = Table(border_style="#3d4f63", header_style="shelf.accent")
    table.add_column("Session")
    table.add_column("When", style="shelf.muted")
    table.add_column("Moves", justify="right")
    table.add_column("Layout")
    table.add_column("Root", style="shelf.path")
    table.add_column("State")
    for session in sessions:
        state = Text("undone", style="shelf.warn") if session.get("undone_at") else Text("applied", style="shelf.ok")
        table.add_row(
            session.get("id", "?"),
            str(session.get("started_at", ""))[:19].replace("T", " "),
            str(len(session.get("moves") or [])),
            str(session.get("layout", "")),
            str(session.get("root", "")),
            state,
        )
    console.print(table)


@app.command()
def undo(
    session: str | None = typer.Option(None, "--session", "-s", help="Session id (defaults to the last applied)."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be restored without moving."),
) -> None:
    """Restore files from the last (or a given) applied session."""
    console.print(banner(dry_run=dry_run, subtitle="undo"))
    try:
        preview = undo_session(session, dry_run=True)
    except FileNotFoundError as exc:
        console.print(f"[shelf.err]{exc}[/]")
        raise typer.Exit(code=1)

    if preview.errors and not preview.restored:
        for err in preview.errors:
            console.print(f"[shelf.err]{err}[/]")
        raise typer.Exit(code=1)

    table = Table(title=f"Undo {preview.session_id}", border_style="#3d4f63", header_style="shelf.accent")
    table.add_column("From")
    table.add_column("Back to")
    for src, dst in preview.restored:
        table.add_row(str(src), str(dst))
    console.print(table)
    console.print(f"[shelf.brand]{len(preview.restored)} files[/] would be restored")
    if preview.skipped:
        console.print(f"[shelf.warn]{len(preview.skipped)} missing at destination[/]")

    if dry_run:
        console.print("[shelf.muted]Dry-run only. Drop --dry-run to restore.[/]")
        raise typer.Exit()

    if not yes:
        from rich.prompt import Confirm

        if not Confirm.ask(f"[shelf.warn]Restore {len(preview.restored)} files from session {preview.session_id}?[/]", default=False):
            console.print("[shelf.muted]Cancelled.[/]")
            raise typer.Exit()

    result = undo_session(preview.session_id, dry_run=False)
    if result.errors and not result.restored:
        for err in result.errors:
            console.print(f"[shelf.err]{err}[/]")
        raise typer.Exit(code=1)
    console.print(f"[shelf.ok]Restored {len(result.restored)} files[/] from session [bold]{result.session_id}[/]")
    for err in result.errors:
        console.print(f"[shelf.err]{err}[/]")


@app.command()
def doctor() -> None:
    """Check the local environment, config, and history. Read-only."""
    import os
    import sys
    from importlib.metadata import version as pkg_version

    console.print(banner(subtitle="doctor"))
    table = Table(border_style="#3d4f63", header_style="shelf.accent", show_header=False)
    table.add_column("Check", style="shelf.cat")
    table.add_column("Value")

    def row(name: str, value: str, ok: bool = True) -> None:
        mark = Text("ok", style="shelf.ok") if ok else Text("warn", style="shelf.warn")
        table.add_row(name, Text.assemble(mark, "  ", value))

    row("fileshelf", __version__)
    row("python", sys.version.split()[0], sys.version_info >= (3, 11))
    row("rich", pkg_version("rich"))
    row("textual", pkg_version("textual"))
    cfg_file = config_path()
    row("config", str(cfg_file), cfg_file.exists())
    ddir = data_dir()
    writable = os.access(ddir, os.W_OK) if ddir.exists() else os.access(ddir.parent, os.W_OK)
    row("data dir", str(ddir), writable)
    sessions = list_sessions()
    undoable = latest_undoable()
    row("history", f"{len(sessions)} sessions in {history_dir()}")
    row("undo", undoable["id"] if undoable else "nothing to undo", bool(undoable) or not sessions)
    row("home", str(Path.home()))
    console.print(table)
    if not cfg_file.exists():
        console.print("[shelf.muted]Tip: run [bold]shelf config init[/bold] to write a config file.[/]")
