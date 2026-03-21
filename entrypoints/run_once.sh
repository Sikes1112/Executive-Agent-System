#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
AUDIT_ROOT="${AUDIT_ROOT:-$WORKSPACE_ROOT/audit}"

TICKET_FILE="${1:?usage: run_once.sh /path/to/ticket.json}"

MAX_TICKET_CHARS=${MAX_TICKET_CHARS:-1400}
TICKET_CHARS=$(wc -c < "$TICKET_FILE" | tr -d " ")
if [ "$TICKET_CHARS" -gt "$MAX_TICKET_CHARS" ]; then
  echo "TICKET_SIZE_FAIL chars=$TICKET_CHARS max=$MAX_TICKET_CHARS file=$TICKET_FILE" >&2
  exit 42
fi

set +e
ADAPTER_META="$(python3 - "$WORKSPACE_ROOT" "$TICKET_FILE" <<'PY'
import importlib.util
import json
import re
import sys
from pathlib import Path

workspace_root = Path(sys.argv[1])
ticket_path = Path(sys.argv[2])
loader_path = workspace_root / "core" / "domain_adapters" / "loader.py"

try:
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"failed to read ticket json: {exc}", file=sys.stderr)
    sys.exit(1)

if not isinstance(ticket, dict):
    print("ticket json must be an object", file=sys.stderr)
    sys.exit(1)

domain = ticket.get("domain")
if domain is not None and not isinstance(domain, str):
    print("ticket domain must be a string when provided", file=sys.stderr)
    sys.exit(1)

try:
    spec = importlib.util.spec_from_file_location("domain_adapter_loader", str(loader_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load adapter loader: {loader_path}")
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    adapter = loader.get_adapter(domain)
except Exception as exc:
    print(f"adapter lookup failed for domain={domain!r}: {exc}", file=sys.stderr)
    sys.exit(1)

if not isinstance(adapter, dict):
    print("adapter payload must be an object", file=sys.stderr)
    sys.exit(1)

name = adapter.get("name")
prompt_path = adapter.get("prompt_path")
lock_suffix = adapter.get("lock_suffix") or name

if not isinstance(name, str) or not name.strip():
    print("adapter missing valid 'name'", file=sys.stderr)
    sys.exit(1)
if not isinstance(prompt_path, str) or not prompt_path.strip():
    print("adapter missing valid 'prompt_path'", file=sys.stderr)
    sys.exit(1)
if not isinstance(lock_suffix, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", lock_suffix):
    print("adapter missing valid 'lock_suffix' or fallback name", file=sys.stderr)
    sys.exit(1)

print(f"{name}\t{prompt_path}\t{lock_suffix}")
PY
)"
ADAPTER_EXIT=$?
set -e
if [ "$ADAPTER_EXIT" -ne 0 ]; then
  echo "ADAPTER_RESOLUTION_FAIL ticket=$TICKET_FILE" >&2
  exit 44
fi
IFS=$'\t' read -r ADAPTER_NAME ADAPTER_PROMPT_PATH ADAPTER_LOCK_SUFFIX <<< "$ADAPTER_META"

# ---------------------------
# SINGLE-WRITER LOCK (structural)
# ---------------------------
LOCK_ROOT="$WORKSPACE_ROOT/core/locks"
LOCK_DIR="$LOCK_ROOT/${ADAPTER_LOCK_SUFFIX}_apply.lock"
mkdir -p "$LOCK_ROOT"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "LOCK_HELD another ${ADAPTER_NAME} apply is running (or crashed). lock=$LOCK_DIR" >&2
  echo "If you are sure nothing is running, remove it: rm -rf $LOCK_DIR" >&2
  exit 43
fi

# ---------------------------
# TEMP FILES (safe / unique)
# ---------------------------
TXT="$(mktemp -t iter_payload_text).txt"
NORM="$(mktemp -t iter_normalized).json"
STAGE_DIR=""

cleanup() {
  rm -rf "$LOCK_DIR" 2>/dev/null || true
  rm -f "$TXT" "$NORM" 2>/dev/null || true
  if [ -n "${STAGE_DIR:-}" ]; then
    rm -rf "$STAGE_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

ADAPTER_ENV_PREFIX="$(printf '%s' "$ADAPTER_NAME" | tr '[:lower:]' '[:upper:]')"
ADAPTER_PROVIDER_VAR="${ADAPTER_ENV_PREFIX}_PROVIDER"
ADAPTER_MODEL_VAR="${ADAPTER_ENV_PREFIX}_MODEL"
ADAPTER_PROVIDER="${!ADAPTER_PROVIDER_VAR:-}"
ADAPTER_MODEL="${!ADAPTER_MODEL_VAR:-}"

ITERATION_PROVIDER="${ADAPTER_PROVIDER:-${ITERATION_PROVIDER:-ollama}}"
ITERATION_MODEL="${ADAPTER_MODEL:-${ITERATION_MODEL:-qwen2.5-coder:14b-32k}}"
SYSTEM_PROMPT_PATH="${SYSTEM_PROMPT_PATH:-$WORKSPACE_ROOT/$ADAPTER_PROMPT_PATH}"
INVOKE_PATH="$WORKSPACE_ROOT/intake/adapters/invoke.py"

python3 "$INVOKE_PATH" \
  --provider "$ITERATION_PROVIDER" \
  --model "$ITERATION_MODEL" \
  --system-prompt "$SYSTEM_PROMPT_PATH" \
  --message "$TICKET_FILE" > "$TXT"

if [ ! -s "$TXT" ]; then
  echo "INVOKE_EMPTY_RESPONSE provider=$ITERATION_PROVIDER model=$ITERATION_MODEL ticket=$TICKET_FILE" >&2
  exit 2
fi

echo "RUN_RECEIPT ticket=$TICKET_FILE provider=$ITERATION_PROVIDER model=$ITERATION_MODEL prompt=$SYSTEM_PROMPT_PATH txt=$TXT norm=$NORM"

set +e
python3 "$WORKSPACE_ROOT/core/pipeline/sanitize.py" --text-file "$TXT" > "$NORM"
SANITIZE_EXIT=$?
set -e
if [ "$SANITIZE_EXIT" -ne 0 ]; then
  RUN_DIR="$(dirname "$TICKET_FILE")"
  cp -f "$TXT" "$RUN_DIR/$(basename "$TXT")"
  cp -f "$NORM" "$RUN_DIR/$(basename "$NORM")"
  echo "SANITIZE_FAIL copied_payload=$RUN_DIR/$(basename "$TXT") copied_error=$RUN_DIR/$(basename "$NORM")" >&2
  exit "$SANITIZE_EXIT"
fi

echo "NORMALIZED_JSON_FILE=$NORM"

python3 "$WORKSPACE_ROOT/core/pipeline/field_guard.py" \
  --normalized "$NORM" \
  --ticket "$TICKET_FILE"

ALLOWLIST_PATH="$WORKSPACE_ROOT/contracts/allowlists/canonical_pack_paths.txt"
python3 "$WORKSPACE_ROOT/core/pipeline/allowlist.py" --allowlist "$ALLOWLIST_PATH" --normalized "$NORM"
WORKSPACE_ROOT="$WORKSPACE_ROOT" AUDIT_ROOT="$AUDIT_ROOT" \
  python3 "$WORKSPACE_ROOT/core/pipeline/entity_guard.py" "$NORM" "$TICKET_FILE"

APPROVAL_POLICY="${APPROVAL_POLICY:-P1}"
python3 "$WORKSPACE_ROOT/core/pipeline/approve.py" \
  --policy "$APPROVAL_POLICY" \
  --raw-text-file "$TXT" \
  --normalized-json-file "$NORM"

# ---------------------------
# ATOMIC APPLY TRANSACTION (structural)
#   - stage under workspace root so renames are same-filesystem
#   - write patches into staged bundle tree
#   - compute new baseline
#   - swap bundles atomically
# ---------------------------
LIVE_BUNDLES="$WORKSPACE_ROOT/workspace-example/bundles"

STAGE_DIR="$(mktemp -d "$WORKSPACE_ROOT/.stage.iter.XXXXXX")"
STAGE_WORKSPACE_EXAMPLE="$STAGE_DIR/workspace-example"
STAGE_BUNDLES="$STAGE_WORKSPACE_EXAMPLE/bundles"
BACKUP_DIR="$WORKSPACE_ROOT/.bundles.backup.$(date -u +%Y%m%dT%H%M%SZ)"

# Stage current bundles as baseline for patching (deterministic base)
mkdir -p "$STAGE_BUNDLES"
# macOS rsync exists; this keeps stage consistent with live
rsync -a --delete "$LIVE_BUNDLES/" "$STAGE_BUNDLES/"

python3 "$WORKSPACE_ROOT/core/pipeline/apply.py" \
  --allowlist "$ALLOWLIST_PATH" \
  --normalized "$NORM" \
  --workspace "$STAGE_WORKSPACE_EXAMPLE"

# Recompute baseline in stage (transactional)
WORKSPACE_ROOT="$STAGE_DIR" "$WORKSPACE_ROOT/core/baseline.sh" --write

# Swap bundles atomically (directory renames)
mv "$LIVE_BUNDLES" "$BACKUP_DIR"
mv "$STAGE_BUNDLES" "$LIVE_BUNDLES"
rm -rf "$BACKUP_DIR" 2>/dev/null || true

echo "ATOMIC_APPLY_OK bundles_swapped=1"
