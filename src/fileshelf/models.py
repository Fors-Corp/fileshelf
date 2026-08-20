"""Core data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileItem:
    path: Path
    size_bytes: int
    mtime: float
    category: str
    subcategory: str | None
    extension: str
    reason: str


@dataclass
class ScanResult:
    root: Path
    files: list[FileItem] = field(default_factory=list)
    skipped_dirs: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        return sum(f.size_bytes for f in self.files)

    def by_category(self) -> dict[str, list[FileItem]]:
        groups: dict[str, list[FileItem]] = {}
        for item in self.files:
            groups.setdefault(item.category, []).append(item)
        return groups


@dataclass(frozen=True)
class MoveAction:
    source: Path
    destination: Path
    category: str
    subcategory: str | None
    reason: str
    size_bytes: int
    conflict: str | None = None  # exists | collision


@dataclass
class Plan:
    root: Path
    destination_root: Path
    layout: str
    actions: list[MoveAction] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def move_count(self) -> int:
        return len(self.actions)

    @property
    def conflict_count(self) -> int:
        return sum(1 for a in self.actions if a.conflict)

    @property
    def total_size(self) -> int:
        return sum(a.size_bytes for a in self.actions)
