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

# ---------------------------
# SINGLE-WRITER LOCK (structural)
# ---------------------------
LOCK_ROOT="$WORKSPACE_ROOT/core/locks"
LOCK_DIR="$LOCK_ROOT/iteration_apply.lock"
mkdir -p "$LOCK_ROOT"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "LOCK_HELD another iteration apply is running (or crashed). lock=$LOCK_DIR" >&2
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

ITERATION_PROVIDER="${ITERATION_PROVIDER:-ollama}"
ITERATION_MODEL="${ITERATION_MODEL:-qwen2.5-coder:14b-32k}"
SYSTEM_PROMPT_PATH="${SYSTEM_PROMPT_PATH:-$WORKSPACE_ROOT/core/prompts/iteration_specialist.md}"
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
