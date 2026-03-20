#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
AUDIT_ROOT="${AUDIT_ROOT:-$WORKSPACE_ROOT/audit}"

if [ $# -lt 1 ]; then
  echo "usage: run_intake.sh <input_text_file>"
  exit 2
fi

INPUT_PATH="$1"

if [ ! -f "$INPUT_PATH" ]; then
  echo "input file not found: $INPUT_PATH"
  exit 2
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$AUDIT_ROOT/helper_runs"
mkdir -p "$OUT_DIR"

RAW_TXT="$OUT_DIR/${TS}_input.txt"
ENVELOPE_JSON="$OUT_DIR/${TS}_envelope.json"
VALIDATION_JSON="$OUT_DIR/${TS}_validation.json"

cp "$INPUT_PATH" "$RAW_TXT"

python3 "$WORKSPACE_ROOT/intake/generate_envelope.py" "$RAW_TXT" "$ENVELOPE_JSON"
python3 "$WORKSPACE_ROOT/intake/allow_new_screen_ids.py" "$RAW_TXT" "$ENVELOPE_JSON"

set +e
WORKSPACE_ROOT="$WORKSPACE_ROOT" AUDIT_ROOT="$AUDIT_ROOT" \
  "$WORKSPACE_ROOT/core/batch/validate.py" "$ENVELOPE_JSON" >"$VALIDATION_JSON"
CODE=$?
set -e

echo "RUN_DIR=$OUT_DIR"
echo "INPUT_SAVED=$RAW_TXT"
echo "ENVELOPE=$ENVELOPE_JSON"
echo "VALIDATION=$VALIDATION_JSON"
echo "EXIT_CODE=$CODE"

exit $CODE
