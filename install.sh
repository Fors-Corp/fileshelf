#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

"$PYTHON" -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install -U pip
pip install -e "$ROOT[dev]"

echo
echo "fileshelf installed into $ROOT/.venv"
echo "Run:  $ROOT/shelf --help"
echo "Or add this directory to PATH:  export PATH=\"$ROOT:\$PATH\""
