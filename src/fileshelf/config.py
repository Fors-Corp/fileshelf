"""User config at ~/.fileshelf/config.toml."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

from fileshelf.journal import data_dir

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore


DEFAULT_CONFIG = """# fileshelf configuration
# Paths in [protect] can only add protection — the built-in deny-list
# cannot be weakened from this file.

[defaults]
layout = "smart"
conflict = "rename"
include_hidden = false
recursive = true
skip_duplicates = false

[skip]
directories = []

[protect]
paths = []

# Custom filename rules run before built-in heuristics.
# [[rules]]
# name = "tax-docs"
# match = '(?i)1099|w-2|tax[-_ ]return'
# category = "Documents"
# subcategory = "Taxes"
"""


@dataclass
class Rule:
    match: str
    category: str
    subcategory: str | None = None
    name: str | None = None


@dataclass
class Config:
    layout: str = "smart"
    conflict: str = "rename"
    include_hidden: bool = False
    recursive: bool = True
    skip_duplicates: bool = False
    skip_directories: list[str] = field(default_factory=list)
    protect_paths: list[Path] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)


def config_path() -> Path:
    return data_dir() / "config.toml"


def load_config(path: Path | None = None) -> Config:
    target = path or config_path()
    if not target.exists():
        return Config()
    data = tomllib.loads(target.read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    skip = data.get("skip", {})
    protect = data.get("protect", {})
    rules = [
        Rule(
            match=r["match"],
            category=r["category"],
            subcategory=r.get("subcategory"),
            name=r.get("name"),
        )
        for r in data.get("rules", [])
        if "match" in r and "category" in r
    ]
    return Config(
        layout=str(defaults.get("layout", "smart")),
        conflict=str(defaults.get("conflict", "rename")),
        include_hidden=bool(defaults.get("include_hidden", False)),
        recursive=bool(defaults.get("recursive", True)),
        skip_duplicates=bool(defaults.get("skip_duplicates", False)),
        skip_directories=[str(x) for x in skip.get("directories", [])],
        protect_paths=[Path(p).expanduser() for p in protect.get("paths", [])],
        rules=rules,
    )


def write_default_config(path: Path | None = None, *, overwrite: bool = False) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        return target
    target.write_text(DEFAULT_CONFIG, encoding="utf-8")
    return target


def dump_config(cfg: Config) -> str:
    payload = {
        "defaults": {
            "layout": cfg.layout,
            "conflict": cfg.conflict,
            "include_hidden": cfg.include_hidden,
            "recursive": cfg.recursive,
            "skip_duplicates": cfg.skip_duplicates,
        },
        "skip": {"directories": cfg.skip_directories},
        "protect": {"paths": [str(p) for p in cfg.protect_paths]},
        "rules": [
            {
                k: v
                for k, v in {
                    "name": r.name,
                    "match": r.match,
                    "category": r.category,
                    "subcategory": r.subcategory,
                }.items()
                if v is not None
            }
            for r in cfg.rules
        ],
    }
    return tomli_w.dumps(payload)
