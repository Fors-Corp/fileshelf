# fileshelf roadmap

Smart file organization for messy folders (Downloads, Desktop, camera dumps)
without surprise deletes. Moves are planned first, applied only on demand,
and reversible.

## Product principles

1. **Dry-run by default.** Nothing moves unless you pass `--apply` or confirm in the TUI.
2. **Local only.** No network, no telemetry, no cloud classifiers.
3. **Reversible.** Every applied session is journaled so you can undo it.
4. **System paths are off-limits.** A hardcoded deny-list cannot be weakened from config.
5. **Already-organized files stay put.** If a file is already on its shelf, skip it.

## Semver plan

| Version | Status | What lands |
| --- | --- | --- |
| **0.1.0** | shipped | Package scaffold, branded CLI, `--version` / `--help` |
| **0.2.0** | current | Scan a folder and classify files (type + size + age) with a Rich table |
| **0.3.0** | planned | Organization *plan*: type, date, type+date, and smart layouts |
| **0.4.0** | planned | Safe apply: dry-run, conflict handling, deny-list, move journal |
| **0.5.0** | planned | Config file, custom rules, duplicate detection |
| **0.6.0** | planned | Interactive Textual TUI (browse, toggle, confirm) |
| **0.7.0** | planned | Undo last session, history browser, `doctor` |
| **1.0.0** | planned | Tests, installer, stable CLI surface |

Each version is a tagged git commit (`v0.1.0`, `v0.2.0`, …).

## Feature map

### Scan & classify

- Walk a directory (recursive by default) with progress output
- Classify by extension into Images, Videos, Audio, Documents, Spreadsheets,
  Presentations, Ebooks, Archives, Code, Installers, Fonts, Design, Other
- Smart filename heuristics: screenshots, camera roll (`IMG_`, `DSC_`),
  receipts/invoices, WhatsApp media, screen recordings
- Skip junk directories (`.git`, `node_modules`, `.venv`, trash, …)
- Skip hidden files unless `--hidden`
- Human-readable sizes, counts, and oldest/newest per category

### Organization layouts

| Layout | Destination pattern |
| --- | --- |
| `type` | `{dest}/{Category}/{filename}` |
| `date` | `{dest}/{year}/{month}/{filename}` |
| `type-date` | `{dest}/{Category}/{year}/{month}/{filename}` |
| `smart` | type + subcategory + date for media (default) |

Examples of `smart`:

- `Screenshot 2026-08-01.png` → `Images/Screenshots/2026/08/`
- `IMG_4021.HEIC` → `Images/Camera/2026/08/`
- `invoice-acme.pdf` → `Documents/Receipts/`
- `Setup.pkg` → `Installers/`
- `notes.txt` → `Documents/`

Destination defaults to the scanned folder (organize in place). `--dest` shelves
into another directory.

### Apply (never silent)

- Dry-run is the default for `organize`
- `--apply` actually moves; same-volume uses rename, cross-volume copies then removes
- Conflicts: `rename` (default, `file-1.ext`), `skip`, or `overwrite`
- Create missing destination folders
- Refuse to touch the deny-list (`/System`, `/usr`, `/Applications`, …)
- Warn (and require `--force-home`) if the scan root is `$HOME`
- Skip files already at their planned destination

### Config & rules (`~/.fileshelf/config.toml`)

- Default layout, destination, conflict policy, skip-hidden
- Extra skip-directory names
- Extra protected paths (can only *add* protection)
- Custom filename-pattern → destination rules

### Duplicates

- Fast fingerprint (size + prefix hash), then SHA-256 confirmation
- Keep newest by default, report the rest
- Optional: omit duplicates from the move plan

### TUI

- Category sidebar with counts and sizes
- File table with proposed destination
- Toggle files in/out of the plan
- Confirm dialog before apply
- Keyboard-first: scan, toggle, apply, undo, quit

### Undo & history

- JSON session journals under `~/.fileshelf/history/`
- `shelf undo` reverses the last applied session (or a given id)
- `shelf history` lists sessions
- `shelf doctor` checks Python, config, history, and write access

## Possible later features (post-1.0)

These are intentionally *not* in 1.0 so the core loop stays small and trustworthy:

- Watch mode for Downloads
- EXIF/GPS-based photo shelves
- Content-based document classification (PDF text)
- Export plan as JSON/CSV
- macOS Finder tags
- Merge empty leftover folders after a move
- Parallel hashing
- iCloud / Dropbox placeholder awareness

## Non-goals

- Deleting files (this is an organizer, not a cleaner)
- Sending file contents anywhere
- Auto-apply on a schedule without an explicit user action
- Reorganizing the whole home directory without an extra confirmation
