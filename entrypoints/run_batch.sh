#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
AUDIT_ROOT="${AUDIT_ROOT:-$WORKSPACE_ROOT/audit}"

if [ $# -lt 1 ]; then
  echo "usage: run_batch.sh <envelope_json>"
  exit 2
fi

ENVELOPE_PATH="$1"

if [ ! -f "$ENVELOPE_PATH" ]; then
  echo "envelope not found: $ENVELOPE_PATH"
  exit 2
fi

VALIDATION_JSON="$(mktemp)"
RUN_DIR="$AUDIT_ROOT/exec_runs/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_DIR"

WORKSPACE_ROOT="$WORKSPACE_ROOT" AUDIT_ROOT="$AUDIT_ROOT" \
  "$WORKSPACE_ROOT/core/batch/validate.py" "$ENVELOPE_PATH" > "$VALIDATION_JSON"

OK=$(python3 -c "import json;print(json.load(open('$VALIDATION_JSON'))['ok'])")
if [ "$OK" != "True" ]; then
  cat "$VALIDATION_JSON"
  echo "validation failed"
  exit 2
fi

EXEC_ORDER=$(python3 -c "import json;print(' '.join(json.load(open('$VALIDATION_JSON'))['exec_order']))")

cp "$ENVELOPE_PATH" "$RUN_DIR/envelope.json"
cp "$VALIDATION_JSON" "$RUN_DIR/validation.json"

for TID in $EXEC_ORDER; do
  TICKET_JSON="$RUN_DIR/${TID}_ticket.json"

  python3 - <<PY > "$TICKET_JSON"
import json, pathlib

env = json.load(open("$ENVELOPE_PATH"))

ticket = None
for t in env["tickets"]:
    if t["ticket_id"] == "$TID":
        ticket = t
        break

if ticket is None:
    raise SystemExit("ticket not found")

current_objects = {}

for path in ticket.get("target_paths", []):
    full_path = pathlib.Path("$WORKSPACE_ROOT") / "workspace-example" / path
    if full_path.exists():
        txt = full_path.read_text()
        if len(txt) <= 4500:
            current_objects[path] = json.loads(txt)

ticket["current_objects"] = current_objects
if "domain" in ticket:
    ticket["domain"] = ticket["domain"]

print(json.dumps(ticket, indent=2))
PY

  WORKSPACE_ROOT="$WORKSPACE_ROOT" AUDIT_ROOT="$AUDIT_ROOT" \
    MAX_TICKET_CHARS=6000 "$WORKSPACE_ROOT/entrypoints/run_once.sh" "$TICKET_JSON" > "$RUN_DIR/${TID}_iteration_output.txt" 2>&1
done

echo "EXEC_RUN_DIR=$RUN_DIR"
