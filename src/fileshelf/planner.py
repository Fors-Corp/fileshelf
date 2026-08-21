"""Build a move plan from a scan result."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fileshelf.duplicates import DuplicateGroup, find_duplicates
from fileshelf.models import FileItem, MoveAction, Plan, ScanResult

LAYOUTS = ("smart", "type", "date", "type-date")
_MEDIA = {"Images", "Videos", "Audio"}


def _date_parts(mtime: float) -> tuple[str, str]:
    dt = datetime.fromtimestamp(mtime)
    return f"{dt.year:04d}", f"{dt.month:02d}"


def destination_for(
    item: FileItem,
    dest_root: Path,
    layout: str,
) -> Path:
    year, month = _date_parts(item.mtime)
    name = item.path.name

    if layout == "type":
        parts = [item.category]
    elif layout == "date":
        parts = [year, month]
    elif layout == "type-date":
        parts = [item.category, year, month]
    elif layout == "smart":
        parts = [item.category]
        if item.subcategory:
            parts.append(item.subcategory)
        if item.category in _MEDIA or item.subcategory in {"Screenshots", "Camera", "WhatsApp", "Screen Recordings"}:
            parts.extend([year, month])
    else:
        raise ValueError(f"unknown layout: {layout}")

    return dest_root.joinpath(*parts, name)


def _already_shelved(source: Path, dest: Path) -> bool:
    try:
        return source.resolve() == dest.resolve()
    except OSError:
        return source == dest


def plan_from_scan(
    scan: ScanResult,
    *,
    dest: Path | None = None,
    layout: str = "smart",
    skip_duplicates: bool = False,
    duplicate_groups: list[DuplicateGroup] | None = None,
) -> Plan:
    if layout not in LAYOUTS:
        raise ValueError(f"layout must be one of {', '.join(LAYOUTS)}")

    dest_root = (dest or scan.root).expanduser().resolve()
    plan = Plan(root=scan.root, destination_root=dest_root, layout=layout)

    skip_paths: set[Path] = set()
    if skip_duplicates:
        groups = duplicate_groups if duplicate_groups is not None else find_duplicates(scan.files)
        for group in groups:
            for extra in group.extras:
                skip_paths.add(extra.path)

    claimed: dict[Path, Path] = {}
    for item in scan.files:
        if item.path in skip_paths:
            plan.skipped.append((item.path, "duplicate (keeping newest)"))
            continue
        target = destination_for(item, dest_root, layout)
        if _already_shelved(item.path, target):
            plan.skipped.append((item.path, "already on the right shelf"))
            continue

        conflict: str | None = None
        if target in claimed:
            conflict = "collision"
        elif target.exists():
            conflict = "exists"

        claimed[target] = item.path
        plan.actions.append(
            MoveAction(
                source=item.path,
                destination=target,
                category=item.category,
                subcategory=item.subcategory,
                reason=item.reason,
                size_bytes=item.size_bytes,
                conflict=conflict,
            )
        )

    plan.actions.sort(key=lambda a: str(a.destination).lower())
    return plan
