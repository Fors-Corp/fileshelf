"""Reverse an applied organization session."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fileshelf.apply import move_file, unique_path
from fileshelf.journal import list_sessions, load_session


@dataclass
class UndoResult:
    session_id: str
    dry_run: bool
    restored: list[tuple[Path, Path]] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def latest_undoable() -> dict | None:
    for session in list_sessions():
        if not session.get("undone_at"):
            return session
    return None


def mark_undone(session_id: str) -> None:
    import json

    from fileshelf.journal import history_dir

    payload = load_session(session_id)
    payload["undone_at"] = datetime.now(timezone.utc).isoformat()
    path = history_dir() / f"{session_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def undo_session(session_id: str | None = None, *, dry_run: bool = False) -> UndoResult:
    if session_id:
        payload = load_session(session_id)
    else:
        payload = latest_undoable()
        if payload is None:
            raise FileNotFoundError("no undoable sessions")
        session_id = str(payload["id"])

    result = UndoResult(session_id=session_id, dry_run=dry_run)
    if payload.get("undone_at"):
        result.errors.append(f"session {session_id} was already undone at {payload['undone_at']}")
        return result

    moves = list(reversed(payload.get("moves") or []))
    for entry in moves:
        src = Path(entry["dst"])
        dst = Path(entry["src"])
        if not src.exists():
            result.skipped.append((src, "file no longer at destination"))
            continue
        dest = dst
        if dest.exists():
            dest = unique_path(dest)
        if dry_run:
            result.restored.append((src, dest))
            continue
        try:
            move_file(src, dest)
            result.restored.append((src, dest))
        except OSError as exc:
            result.errors.append(f"{src} → {dest}: {exc}")

    if not dry_run and result.restored:
        mark_undone(session_id)
    return result
