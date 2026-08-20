"""Hardcoded path protection. Config can only add more deny paths, never fewer."""

from __future__ import annotations

from pathlib import Path

ABSOLUTE_DENY: tuple[str, ...] = (
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/etc",
    "/dev",
    "/private/etc",
    "/private/var/db",
    "/private/var/root",
    "/Applications",
    "/Library/Apple",
    "/Library/CoreServices",
    "/Library/Extensions",
    "/Library/Frameworks",
    "/Library",
)

RELATIVE_DENY: tuple[str, ...] = (
    "System",
    "usr",
    "bin",
    "sbin",
    "Library/Apple",
    "Library/CoreServices",
)


def _volume_roots() -> list[Path]:
    roots = [Path("/")]
    volumes = Path("/Volumes")
    if volumes.is_dir():
        try:
            for entry in volumes.iterdir():
                if entry.is_dir() or entry.is_symlink():
                    roots.append(entry)
        except OSError:
            pass
    return roots


def _protected_prefixes() -> list[Path]:
    prefixes = [Path(p) for p in ABSOLUTE_DENY]
    for root in _volume_roots():
        for rel in RELATIVE_DENY:
            prefixes.append(root / rel)
    return prefixes


def is_home(path: Path) -> bool:
    try:
        return path.expanduser().resolve() == Path.home().resolve()
    except OSError:
        return False


def is_denied(path: Path, extra: tuple[Path, ...] = ()) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        resolved = path.expanduser()

    if resolved == Path("/"):
        return True

    for prefix in list(_protected_prefixes()) + list(extra):
        try:
            pref = prefix.expanduser().resolve()
        except OSError:
            pref = prefix
        if resolved == pref or pref in resolved.parents:
            return True
        # Also block moving the prefix itself
        if resolved in pref.parents:
            # dest/source is an ancestor of a protected path — too broad, skip
            continue
    return False


def deny_reason(path: Path, extra: tuple[Path, ...] = ()) -> str | None:
    if is_denied(path, extra):
        return "protected system path"
    return None
