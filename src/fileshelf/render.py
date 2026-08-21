"""Rich rendering for plans and sessions."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from fileshelf.format import human_size
from fileshelf.models import Plan


def plan_table(plan: Plan, *, limit: int = 0) -> Table:
    rows = plan.actions if limit <= 0 else plan.actions[:limit]
    table = Table(
        title=f"Plan ({plan.layout})",
        border_style="#3d4f63",
        header_style="shelf.accent",
    )
    table.add_column("Status", width=8)
    table.add_column("Size", justify="right")
    table.add_column("From")
    table.add_column("To")

    for action in rows:
        if action.conflict:
            status = Text(action.conflict, style="shelf.warn")
        else:
            status = Text("move", style="shelf.ok")
        try:
            src = action.source.relative_to(plan.root)
        except ValueError:
            src = action.source
        try:
            dst = action.destination.relative_to(plan.destination_root)
        except ValueError:
            dst = action.destination
        table.add_row(status, human_size(action.size_bytes), str(src), str(dst))
    return table


def plan_tree(plan: Plan) -> Tree:
    tree = Tree(f"[shelf.brand]{plan.destination_root}[/]")
    nodes: dict[Path, Tree] = {plan.destination_root: tree}

    dests = sorted({a.destination.parent for a in plan.actions}, key=lambda p: str(p).lower())
    for folder in dests:
        parent = folder
        chain: list[Path] = []
        while parent not in nodes and parent != parent.parent:
            chain.append(parent)
            parent = parent.parent
        chain.reverse()
        current_parent = nodes.get(parent, tree)
        for part in chain:
            label = part.name or str(part)
            child = current_parent.add(f"[shelf.cat]{label}/[/]")
            nodes[part] = child
            current_parent = child

    counts: dict[Path, int] = {}
    sizes: dict[Path, int] = {}
    for action in plan.actions:
        parent = action.destination.parent
        counts[parent] = counts.get(parent, 0) + 1
        sizes[parent] = sizes.get(parent, 0) + action.size_bytes

    for folder, node in nodes.items():
        if folder == plan.destination_root:
            continue
        n = counts.get(folder, 0)
        if n:
            unit = "file" if n == 1 else "files"
            node.label = Text.from_markup(
                f"[shelf.cat]{folder.name}/[/] [shelf.muted]{n} {unit} · {human_size(sizes.get(folder, 0))}[/]"
            )
    return tree


def plan_summary(plan: Plan) -> Text:
    text = Text()
    text.append(f"{plan.move_count} moves", style="shelf.brand")
    text.append("  ·  ", style="shelf.muted")
    text.append(human_size(plan.total_size), style="shelf.accent")
    text.append("  ·  ", style="shelf.muted")
    if plan.conflict_count:
        text.append(f"{plan.conflict_count} conflicts", style="shelf.warn")
    else:
        text.append("no conflicts", style="shelf.ok")
    if plan.skipped:
        text.append("  ·  ", style="shelf.muted")
        text.append(f"{len(plan.skipped)} skipped", style="shelf.muted")
    return text
