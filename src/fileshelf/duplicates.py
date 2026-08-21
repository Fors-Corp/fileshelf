"""Find duplicate files: size → prefix hash → SHA-256."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from fileshelf.models import FileItem

PREFIX_BYTES = 65536


@dataclass
class DuplicateGroup:
    digest: str
    size_bytes: int
    files: list[FileItem]  # newest first

    @property
    def keep(self) -> FileItem:
        return self.files[0]

    @property
    def extras(self) -> list[FileItem]:
        return self.files[1:]


def _hash_file(path: Path, *, prefix_only: bool = False) -> str:
    digest = hashlib.sha256()
    remaining = PREFIX_BYTES if prefix_only else None
    with path.open("rb") as fh:
        while True:
            chunk_size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
                if remaining <= 0:
                    break
    return digest.hexdigest()


def find_duplicates(items: list[FileItem]) -> list[DuplicateGroup]:
    by_size: dict[int, list[FileItem]] = defaultdict(list)
    for item in items:
        if item.size_bytes <= 0:
            continue
        by_size[item.size_bytes].append(item)

    groups: list[DuplicateGroup] = []
    for size, same_size in by_size.items():
        if len(same_size) < 2:
            continue
        by_prefix: dict[str, list[FileItem]] = defaultdict(list)
        for item in same_size:
            try:
                by_prefix[_hash_file(item.path, prefix_only=True)].append(item)
            except OSError:
                continue
        for prefixed in by_prefix.values():
            if len(prefixed) < 2:
                continue
            by_full: dict[str, list[FileItem]] = defaultdict(list)
            for item in prefixed:
                try:
                    by_full[_hash_file(item.path, prefix_only=False)].append(item)
                except OSError:
                    continue
            for digest, files in by_full.items():
                if len(files) < 2:
                    continue
                files.sort(key=lambda f: f.mtime, reverse=True)
                groups.append(DuplicateGroup(digest=digest, size_bytes=size, files=files))

    groups.sort(key=lambda g: g.size_bytes * len(g.files), reverse=True)
    return groups
