#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  baseline.sh --write
  baseline.sh --print
  baseline.sh --check

Environment:
  WORKSPACE_ROOT  Optional workspace root. Defaults to repo root.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BUNDLES_DIR="$WORKSPACE_ROOT/workspace-example/bundles"
BASELINE_PATH="$BUNDLES_DIR/_baseline.sha256"

MODE="${1:-}"
if [[ -z "$MODE" ]]; then
  usage
  exit 2
fi

generate_manifest() {
  python3 - "$BUNDLES_DIR" <<'PY'
import hashlib
import sys
from pathlib import Path

bundles_dir = Path(sys.argv[1])

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

entries = []
for p in bundles_dir.rglob("*"):
    if not p.is_file():
        continue
    if p.name == "_baseline.sha256":
        continue
    rel = p.relative_to(bundles_dir).as_posix()
    entries.append((rel, sha256_file(p)))

entries.sort(key=lambda x: x[0])
for rel, digest in entries:
    print(f"{digest}  {rel}")
PY
}

case "$MODE" in
  --print)
    generate_manifest
    ;;
  --write)
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    generate_manifest > "$tmp"
    cp "$tmp" "$BASELINE_PATH"
    ;;
  --check)
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    generate_manifest > "$tmp"
    cmp -s "$tmp" "$BASELINE_PATH"
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage
    exit 2
    ;;
esac
