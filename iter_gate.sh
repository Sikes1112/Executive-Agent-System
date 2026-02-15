#!/usr/bin/env bash
set -euo pipefail
IN="${1:-/dev/stdin}"
python3 ~/.openclaw/workspace-exec/iteration_sanitize_validate.py --text-file "$IN"
echo "ITERATION_GATE=PASS" 1>&2
