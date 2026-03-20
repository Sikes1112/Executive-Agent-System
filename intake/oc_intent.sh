#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   oc_intent.sh "do X"
#   oc_intent.sh --edit
#   oc_intent.sh --file /path/to/intent.txt

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
AUDIT_ROOT="${AUDIT_ROOT:-$WORKSPACE_ROOT/audit}"

HELPER="$WORKSPACE_ROOT/entrypoints/run_intake.sh"
ITER="$WORKSPACE_ROOT/entrypoints/run_once.sh"

if [ ! -x "$HELPER" ]; then echo "MISSING/NOT_EXEC: $HELPER" >&2; exit 2; fi
if [ ! -x "$ITER" ]; then echo "MISSING/NOT_EXEC: $ITER" >&2; exit 2; fi

MODE="string"
INTENT_FILE=""

if [ "${1:-}" = "--edit" ]; then
  MODE="edit"
elif [ "${1:-}" = "--file" ]; then
  MODE="file"
  INTENT_FILE="${2:-}"
  if [ -z "$INTENT_FILE" ]; then echo "usage: --file /path/to/intent.txt" >&2; exit 2; fi
elif [ $# -ge 1 ]; then
  MODE="string"
else
  echo "usage: oc_intent.sh \"intent text\" | --edit | --file path" >&2
  exit 2
fi

TMP_INTENT="$(mktemp -t oc_intent).txt"
cleanup() { rm -f "$TMP_INTENT" 2>/dev/null || true; }
trap cleanup EXIT

if [ "$MODE" = "string" ]; then
  printf "%s\n" "$*" > "$TMP_INTENT"
  INTENT_FILE="$TMP_INTENT"
elif [ "$MODE" = "edit" ]; then
  : > "$TMP_INTENT"
  ${EDITOR:-nano} "$TMP_INTENT"
  INTENT_FILE="$TMP_INTENT"
elif [ "$MODE" = "file" ]; then
  if [ ! -f "$INTENT_FILE" ]; then echo "intent file not found: $INTENT_FILE" >&2; exit 2; fi
fi

echo "=== HELPER: generating envelope ==="
HELPER_OUT="$("$HELPER" "$INTENT_FILE")" || {
  echo "HELPER_FAILED" >&2
  exit 3
}
echo "$HELPER_OUT"

ENVELOPE_PATH="$(printf "%s\n" "$HELPER_OUT" | awk -F= '/^ENVELOPE=/{print $2}' | tail -n 1)"
VALIDATION_PATH="$(printf "%s\n" "$HELPER_OUT" | awk -F= '/^VALIDATION=/{print $2}' | tail -n 1)"
RUN_DIR="$(printf "%s\n" "$HELPER_OUT" | awk -F= '/^RUN_DIR=/{print $2}' | tail -n 1)"

if [ -z "$ENVELOPE_PATH" ] || [ ! -f "$ENVELOPE_PATH" ]; then
  echo "FAILED_TO_LOCATE_ENVELOPE from helper output" >&2
  exit 4
fi

echo
echo "=== EXEC ROUTER (v1): routing to iteration ==="
echo "ENVELOPE=$ENVELOPE_PATH"
echo "VALIDATION=$VALIDATION_PATH"
echo "RUN_DIR=$RUN_DIR"

# ---- Retry-on-empty payload preflight (wrapper-level) ----
echo
echo "=== ITERATION: preflight raw capture + retry-on-empty ==="

DBG_DIR="$AUDIT_ROOT/iteration_debug"
mkdir -p "$DBG_DIR"

run_raw_once () {
  local sid out
  sid="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
  out="$DBG_DIR/raw_${sid}.json"
  openclaw agent --agent iteration --local --json --session-id "$sid" -m "$(cat "$ENVELOPE_PATH")" > "$out"
  echo "$out"
}

payload_len () {
  python3 - "$1" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p,"r",encoding="utf-8"))
print(len(d.get("payloads") or []))
PY
}

MAX_TRIES=5
OK_RAW=""

for i in $(seq 1 "$MAX_TRIES"); do
  RAW="$(run_raw_once)"
  LEN="$(payload_len "$RAW")"
  echo "RAW_CAPTURE_${i}=$RAW payloads_len=$LEN"
  if [ "$LEN" -gt 0 ]; then
    OK_RAW="$RAW"
    break
  fi
  sleep 0.4
done

if [ -z "$OK_RAW" ]; then
  echo "ITERATION_EMPTY_PAYLOAD_FAIL"
  echo "Saved raw runs in: $DBG_DIR"
  exit 5
fi

echo
echo "=== ITERATION: applying via sealed entrypoint ==="
"$ITER" "$ENVELOPE_PATH"

echo
echo "DONE"
echo "Helper artifacts: $RUN_DIR"
echo "Bundles root: $WORKSPACE_ROOT/workspace-example/bundles"
