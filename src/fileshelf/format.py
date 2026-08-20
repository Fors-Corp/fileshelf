"""Human-readable sizes and dates."""

from __future__ import annotations

from datetime import datetime

_UNITS = ("B", "KB", "MB", "GB", "TB")


def human_size(n: int) -> str:
    if n < 0:
        return "0 B"
    size = float(n)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def human_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
