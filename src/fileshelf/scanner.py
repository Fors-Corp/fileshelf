"""Walk a directory and classify files."""

from __future__ import annotations

import os
from pathlib import Path

from fileshelf.classify import classify, extension_of
from fileshelf.models import FileItem, ScanResult

SKIP_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".Trash",
    ".Trashes",
    "$RECYCLE.BIN",
    "System Volume Information",
    ".fileshelf",
}


def scan(
    root: Path,
    *,
    recursive: bool = True,
    include_hidden: bool = False,
    extra_skip_dirs: frozenset[str] | set[str] | None = None,
    follow_symlinks: bool = False,
    max_depth: int | None = None,
) -> ScanResult:
    root = root.expanduser().resolve()
    result = ScanResult(root=root)
    skip = set(SKIP_DIR_NAMES)
    if extra_skip_dirs:
        skip.update(extra_skip_dirs)

    if not root.exists():
        result.errors.append(f"path does not exist: {root}")
        return result
    if not root.is_dir():
        result.errors.append(f"not a directory: {root}")
        return result

    def _walk(current: Path, depth: int) -> None:
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            result.errors.append(f"{current}: {exc}")
            return

        for entry in entries:
            name = entry.name
            hidden = name.startswith(".")
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
                is_link = entry.is_symlink()
            except OSError as exc:
                result.errors.append(f"{entry.path}: {exc}")
                continue

            if is_link and not follow_symlinks:
                continue

            if is_dir:
                if (
                    name in skip
                    or name.endswith(".egg-info")
                    or (hidden and not include_hidden)
                ):
                    result.skipped_dirs += 1
                    continue
                if recursive and (max_depth is None or depth < max_depth):
                    _walk(Path(entry.path), depth + 1)
                continue

            if not is_file:
                continue
            if hidden and not include_hidden:
                continue

            path = Path(entry.path)
            try:
                stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                result.errors.append(f"{path}: {exc}")
                continue

            category, subcategory, reason = classify(path)
            result.files.append(
                FileItem(
                    path=path,
                    size_bytes=int(stat.st_size),
                    mtime=float(stat.st_mtime),
                    category=category,
                    subcategory=subcategory,
                    extension=extension_of(path),
                    reason=reason,
                )
            )

    _walk(root, 0)
    result.files.sort(key=lambda f: (f.category, f.path.name.lower()))
    return result
