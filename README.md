# fileshelf

Smart file organizer with a polished terminal UI.

`shelf` looks at a messy folder, classifies what it finds, proposes a shelf
layout, and only moves files when you say so. Dry-run is the default. Every
applied session can be undone.

```
  ╭──────────────────────────────────────────────╮
  │  fileshelf  ·  smart file organizer          │
  │  dry-run · ~/Downloads · layout: smart       │
  ╰──────────────────────────────────────────────╯
```

## Status

**v0.3.0** — scan, classify, and preview a shelf plan. Feature work lands
version by version; see [ROADMAP.md](ROADMAP.md).

## Install

```bash
./install.sh
./shelf --help
```

`install.sh` (arriving in v1.0.0) creates a project-local virtualenv. Until
then, from a clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
shelf --help
```

## Quick start

```bash
shelf scan ~/Downloads
shelf plan ~/Downloads --tree
shelf plan ~/Downloads --layout type-date
```

Coming next: `organize`, `tui`, `undo`.

## License

MIT
