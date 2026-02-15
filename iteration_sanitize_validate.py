#!/usr/bin/env python3
"""
Exec-side sanitizer + validator for Iteration PATCH_MODE outputs.

Goal:
- Accept common "model drift" wrappers (```json fences, leading/trailing prose)
- Extract exactly one JSON object
- Validate minimal schema invariants
- Output normalized JSON (raw, no fences) to stdout
- Non-zero exit on failure

Usage:
  python3 iteration_sanitize_validate.py --text-file /path/to/payload_text.txt
  python3 iteration_sanitize_validate.py --stdin < payload_text.txt
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, Tuple

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n|\n\s*```\s*$", re.IGNORECASE)

def strip_fences(s: str) -> str:
    # Remove a single pair of surrounding fences if present
    s2 = FENCE_RE.sub("", s)
    return s2.strip()

def extract_first_json_object(s: str) -> Tuple[str, str]:
    """
    Extract the first balanced {...} object from s.
    Returns (json_text, remainder_without_that_object_trimmed).
    """
    start = s.find("{")
    if start == -1:
        raise ValueError("No '{' found in output")

    depth = 0
    in_str = False
    esc = False
    end = None

    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

    if end is None:
        raise ValueError("Unbalanced JSON braces; could not find end of object")

    json_text = s[start:end].strip()
    remainder = (s[:start] + s[end:]).strip()
    return json_text, remainder

def validate_patch_mode(obj: Dict[str, Any]) -> None:
    # Required keys
    for k in ("ticket", "mode", "output", "bundles", "notes"):
        if k not in obj:
            raise ValueError(f"Missing required top-level key: {k}")

    if obj["output"] != "PATCH_MODE":
        raise ValueError(f'output must be "PATCH_MODE" (got {obj["output"]!r})')

    if not isinstance(obj["bundles"], list):
        raise ValueError("bundles must be an array/list")

    for i, b in enumerate(obj["bundles"]):
        if not isinstance(b, dict):
            raise ValueError(f"bundles[{i}] must be an object")
        if "path" not in b or "patch" not in b:
            raise ValueError(f"bundles[{i}] must include path and patch")
        if not isinstance(b["path"], str):
            raise ValueError(f"bundles[{i}].path must be a string")
        if not isinstance(b["patch"], dict):
            raise ValueError(f"bundles[{i}].patch must be an object ({{}} allowed)")

        # Hard ban placeholders like "..." inside patch objects (string value)
        def walk(x: Any) -> None:
            if isinstance(x, dict):
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
            elif isinstance(x, str):
                if "..." in x:
                    raise ValueError("Placeholder '...' found inside patch content")
        walk(b["patch"])

    if not isinstance(obj["notes"], list):
        raise ValueError("notes must be an array/list")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", help="File containing raw payload text")
    ap.add_argument("--stdin", action="store_true", help="Read raw payload text from stdin")
    args = ap.parse_args()

    if not args.text_file and not args.stdin:
        ap.error("Provide --text-file or --stdin")

    raw = sys.stdin.read() if args.stdin else open(args.text_file, "r", encoding="utf-8").read()

    # First pass: strip common code fences
    s = strip_fences(raw)

    # Second pass: extract first JSON object even if extra text exists
    json_text, remainder = extract_first_json_object(s)

    # If there is non-empty remainder, we still accept (sanitizer role),
    # but we record it in stderr so Exec can decide to reject if desired.
    if remainder:
        print("WARN: extra non-JSON text was present and was discarded by sanitizer", file=sys.stderr)

    # Parse + validate
    obj = json.loads(json_text)
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON must be an object")

    validate_patch_mode(obj)

    # Emit normalized JSON (no fences, stable formatting)
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"VALIDATION_FAIL: {e}", file=sys.stderr)
        raise SystemExit(2)
