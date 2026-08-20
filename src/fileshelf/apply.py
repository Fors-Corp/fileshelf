"""Execute a plan: dry-run or real moves, with conflict handling."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from fileshelf.journal import new_session_id, write_session
from fileshelf.models import MoveAction, Plan
from fileshelf.safety import deny_reason, is_home


@dataclass
class ApplyResult:
    session_id: str
    dry_run: bool
    moved: list[MoveAction] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    journal_path: Path | None = None


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    n = 1
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _same_volume(a: Path, b: Path) -> bool:
    try:
        return os.stat(a).st_dev == os.stat(b if b.exists() else b.parent).st_dev
    except OSError:
        return False


def _move(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if _same_volume(src, dst.parent):
        src.rename(dst)
    else:
        shutil.move(str(src), str(dst))


def apply_plan(
    plan: Plan,
    *,
    dry_run: bool = True,
    conflict: str = "rename",
    extra_deny: tuple[Path, ...] = (),
    force_home: bool = False,
) -> ApplyResult:
    if conflict not in {"rename", "skip", "overwrite"}:
        raise ValueError("conflict must be rename, skip, or overwrite")

    result = ApplyResult(session_id=new_session_id(), dry_run=dry_run)

    if is_home(plan.root) and not force_home:
        result.errors.append(
            "refusing to organize $HOME without --force-home "
            "(that would reshuffle your whole home directory)"
        )
        return result
    if is_home(plan.destination_root) and not force_home:
        result.errors.append("refusing to use $HOME as a destination without --force-home")
        return result

    extra = extra_deny + (Path.home() / "Library",)
    root_reason = deny_reason(plan.root, extra)
    dest_reason = deny_reason(plan.destination_root, extra)
    if root_reason:
        result.errors.append(f"scan root is {root_reason}: {plan.root}")
        return result
    if dest_reason:
        result.errors.append(f"destination is {dest_reason}: {plan.destination_root}")
        return result

    for action in plan.actions:
        src_reason = deny_reason(action.source, extra)
        dst_reason = deny_reason(action.destination, extra)
        if src_reason:
            result.skipped.append((action.source, src_reason))
            continue
        if dst_reason:
            result.skipped.append((action.source, dst_reason))
            continue
        if not action.source.exists():
            result.skipped.append((action.source, "source disappeared"))
            continue

        dest = action.destination
        if dest.exists() or dest == action.source:
            if conflict == "skip":
                result.skipped.append((action.source, "destination exists"))
                continue
            if conflict == "rename":
                dest = unique_path(dest)
            # overwrite: proceed

        moved = MoveAction(
            source=action.source,
            destination=dest,
            category=action.category,
            subcategory=action.subcategory,
            reason=action.reason,
            size_bytes=action.size_bytes,
            conflict=action.conflict,
        )

        if dry_run:
            result.moved.append(moved)
            continue

        try:
            _move(action.source, dest)
            result.moved.append(moved)
        except OSError as exc:
            result.errors.append(f"{action.source} → {dest}: {exc}")

    if not dry_run and result.moved:
        result.journal_path = write_session(
            session_id=result.session_id,
            root=plan.root,
            dest=plan.destination_root,
            layout=plan.layout,
            moves=result.moved,
            errors=result.errors,
            skipped=[f"{p}: {why}" for p, why in result.skipped],
        )
    return result
