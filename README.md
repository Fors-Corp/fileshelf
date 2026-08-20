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

**v0.4.0** — scan, plan, and safely apply (dry-run by default). See
[ROADMAP.md](ROADMAP.md).

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
shelf organize ~/Downloads                 # dry-run
shelf organize ~/Downloads --apply         # asks before moving
shelf organize ~/Downloads --apply --yes   # no prompt
```

Coming next: config, duplicates, `tui`, `undo`.

## License

MIT
