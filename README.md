# fileshelf

[![Support · 1,99 €](https://img.shields.io/badge/Support-1%2C99_%E2%82%AC-2f855a)](https://marcfors.com/donate?from=fileshelf)

Smart file organizer with a polished terminal UI.

`shelf` looks at a messy folder, classifies what it finds, proposes a shelf
layout, and only moves files when you say so. Dry-run is the default. Every
applied session is journaled and can be undone.

```
  ╭──────────────────────────────────────────────╮
  │  fileshelf  ·  smart file organizer          │
  │  dry-run · ~/Downloads · layout: smart       │
  ╰──────────────────────────────────────────────╯
```

Local only: no network, no telemetry, no cloud classifiers.

## Install

```bash
git clone https://github.com/marcfs31/fileshelf.git
cd fileshelf
./install.sh
./shelf --help
```

`install.sh` creates a project-local virtualenv. Optionally put the clone on
your `PATH`:

```bash
export PATH="$(pwd):$PATH"
```

## Quick start

```bash
shelf scan ~/Downloads
shelf plan ~/Downloads --tree
shelf organize ~/Downloads                 # dry-run
shelf organize ~/Downloads --apply         # asks before moving
shelf tui ~/Downloads                      # interactive review
shelf undo --dry-run
shelf doctor
```

## Commands

| Command | What it does |
| --- | --- |
| `scan` | Classify files (read-only) |
| `plan` | Preview destinations (read-only) |
| `organize` | Same as plan; `--apply` moves |
| `tui` | Interactive browser / apply / undo |
| `duplicates` | Content-hash duplicate groups |
| `config show` / `config init` | `~/.fileshelf/config.toml` |
| `history` | Applied sessions |
| `undo` | Restore a session |
| `doctor` | Environment and health check |

## Layouts

| Layout | Destination |
| --- | --- |
| `smart` (default) | type + subcategory + year/month for media |
| `type` | `{Category}/{filename}` |
| `date` | `{year}/{month}/{filename}` |
| `type-date` | `{Category}/{year}/{month}/{filename}` |

Examples of `smart`:

- `Screenshot 2026-08-01.png` → `Images/Screenshots/2026/08/`
- `IMG_4021.HEIC` → `Images/Camera/2026/08/`
- `invoice-acme.pdf` → `Documents/Receipts/`
- `Setup.pkg` → `Installers/`

Use `--dest` to shelf into another folder instead of organizing in place.

## Safety

1. **Dry-run by default.** `organize` only reports unless you pass `--apply`.
2. **Confirmation.** `--apply` asks unless you also pass `--yes`.
3. **Journals.** Each apply writes `~/.fileshelf/history/<session>.json`. `shelf undo` puts files back.
4. **Deny-list.** `/System`, `/usr`, `/Applications`, `~/Library`, and other system paths cannot be touched. Config can only *add* protected paths.
5. **`$HOME` guard.** Organizing your home directory requires `--force-home`.
6. **Conflicts.** Default is `rename` (`file-1.ext`). Also `skip` or `overwrite`.

## TUI

```bash
shelf tui ~/Downloads
```

| Key | Action |
| --- | --- |
| `space` | Toggle the current file in/out of the plan |
| `a` | Apply selected moves (confirm dialog) |
| `u` | Undo the last applied session |
| `l` | Cycle layout |
| `d` | Toggle skip-duplicates |
| `r` | Rescan |
| `q` | Quit |

## Config

```bash
shelf config init
```

Writes `~/.fileshelf/config.toml` — default layout, extra skip directories,
extra protect paths, and custom filename rules that run before built-in
heuristics. See [ROADMAP.md](ROADMAP.md) for the full feature map.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Versioning follows [semver](https://semver.org/). See [CHANGELOG.md](CHANGELOG.md).

## Support

If this project is useful to you, you can [support it with 1,99 €](https://marcfors.com/donate?from=fileshelf).

## License

MIT
