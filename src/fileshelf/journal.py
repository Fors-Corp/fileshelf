"""Local JSON journals of applied organization sessions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fileshelf.models import MoveAction


def data_dir() -> Path:
    return Path.home() / ".fileshelf"


def history_dir() -> Path:
    return data_dir() / "history"


def new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


def write_session(
    *,
    session_id: str,
    root: Path,
    dest: Path,
    layout: str,
    moves: list[MoveAction],
    errors: list[str],
    skipped: list[str],
) -> Path:
    history_dir().mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "dest": str(dest),
        "layout": layout,
        "moves": [
            {
                "src": str(m.source),
                "dst": str(m.destination),
                "size": m.size_bytes,
                "category": m.category,
            }
            for m in moves
        ],
        "errors": errors,
        "skipped": skipped,
    }
    path = history_dir() / f"{session_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_session(session_id: str) -> dict[str, Any]:
    path = history_dir() / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(session_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions() -> list[dict[str, Any]]:
    folder = history_dir()
    if not folder.exists():
        return []
    sessions = []
    for path in sorted(folder.glob("*.json"), reverse=True):
        try:
            sessions.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return sessions
