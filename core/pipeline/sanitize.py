#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n|\n\s*```\s*$", re.IGNORECASE)


TAG_RE = re.compile(r"</?(?:final|finally)>\s*", re.IGNORECASE)

def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s).strip()


def strip_fences(s: str) -> str:
    return FENCE_RE.sub("", s).strip()

def extract_first_json_object(s: str) -> Tuple[str, str]:
    start = s.find("{")
    if start < 0:
        raise ValueError("no_json_object_start")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    json_text = s[start:end].strip()
                    remainder = (s[:start] + s[end:]).strip()
                    return json_text, remainder
    raise ValueError("no_json_object_end")

def fail(code: str, details: Dict[str, Any] | None = None, exit_code: int = 2) -> None:
    payload: Dict[str, Any] = {"ok": False, "error": code}
    if details is not None:
        payload["details"] = details
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    raise SystemExit(exit_code)

def validate_patch_mode(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        fail("not_object", {"type": type(obj).__name__})

    required_top = ["ticket", "mode", "output", "bundles", "notes"]
    missing = [k for k in required_top if k not in obj]
    if missing:
        fail("missing_required_top_level_keys", {"missing": missing})

    if obj["output"] != "PATCH_MODE":
        fail("output_not_patch_mode", {"output": obj["output"]})

    if not isinstance(obj["ticket"], str) or not obj["ticket"].strip():
        fail("invalid_ticket")

    if not isinstance(obj["mode"], str) or not obj["mode"].strip():
        fail("invalid_mode")

    bundles = obj["bundles"]
    if not isinstance(bundles, list) or len(bundles) == 0:
        fail("invalid_bundles", {"type": type(bundles).__name__, "len": len(bundles) if isinstance(bundles, list) else None})

    for i, b in enumerate(bundles):
        if not isinstance(b, dict):
            fail("bundle_not_object", {"index": i, "type": type(b).__name__})
        if "path" not in b or "patch" not in b:
            fail("bundle_missing_fields", {"index": i})
        path = b["path"]
        patch = b["patch"]
        if not isinstance(path, str) or not path.strip():
            fail("invalid_bundle_path", {"index": i})
        if not isinstance(patch, dict):
            fail("invalid_bundle_patch_type", {"index": i, "type": type(patch).__name__})

    notes = obj["notes"]
    if not isinstance(notes, list) or not all(isinstance(x, str) for x in notes):
        fail("invalid_notes")

    return obj

def validate_outreach_generation_mode(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        fail("outreach_not_object", {"type": type(obj).__name__})

    required_top = ["mode", "iteration", "result", "notes"]
    missing = [k for k in required_top if k not in obj]
    if missing:
        fail("outreach_missing_required_top_level_keys", {"missing": missing})

    if obj["mode"] != "generation":
        fail("outreach_invalid_mode", {"mode": obj["mode"]})

    iteration = obj["iteration"]
    if not isinstance(iteration, dict):
        fail("outreach_invalid_iteration", {"type": type(iteration).__name__})

    result = obj["result"]
    if not isinstance(result, dict):
        fail("outreach_invalid_result", {"type": type(result).__name__})

    required_result = ["status", "summary", "artifacts"]
    missing_result = [k for k in required_result if k not in result]
    if missing_result:
        fail("outreach_missing_result_keys", {"missing": missing_result})

    if result["status"] not in {"ok", "needs_input", "blocked"}:
        fail("outreach_invalid_status", {"status": result["status"]})

    if not isinstance(result["summary"], str):
        fail("outreach_invalid_summary", {"type": type(result["summary"]).__name__})

    artifacts = result["artifacts"]
    if not isinstance(artifacts, list):
        fail("outreach_invalid_artifacts", {"type": type(artifacts).__name__})

    for i, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            fail("outreach_artifact_not_object", {"index": i, "type": type(artifact).__name__})
        required_artifact = ["name", "type", "content"]
        missing_artifact = [k for k in required_artifact if k not in artifact]
        if missing_artifact:
            fail("outreach_artifact_missing_fields", {"index": i, "missing": missing_artifact})
        if not isinstance(artifact["name"], str) or not artifact["name"].strip():
            fail("outreach_invalid_artifact_name", {"index": i})
        if not isinstance(artifact["type"], str) or not artifact["type"].strip():
            fail("outreach_invalid_artifact_type", {"index": i})
        if not isinstance(artifact["content"], (dict, str)):
            fail("outreach_invalid_artifact_content", {"index": i, "type": type(artifact["content"]).__name__})

    notes = obj["notes"]
    if not isinstance(notes, list) or not all(isinstance(x, str) for x in notes):
        fail("outreach_invalid_notes")

    return obj

def normalize_for_domain(obj: Any, domain: str) -> Dict[str, Any]:
    normalized_domain = domain.strip().lower() if isinstance(domain, str) else ""
    if not normalized_domain:
        normalized_domain = "iteration"

    if normalized_domain == "iteration":
        return validate_patch_mode(obj)
    if normalized_domain == "outreach":
        return validate_outreach_generation_mode(obj)

    fail("unsupported_result_mode_or_domain", {"domain": normalized_domain})

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", help="File containing raw model payload text")
    ap.add_argument("--stdin", action="store_true", help="Read raw payload text from stdin")
    ap.add_argument("--domain", help="Expected domain for result normalization")
    args = ap.parse_args()

    if bool(args.text_file) == bool(args.stdin):
        fail("usage", {"hint": "use exactly one of --text-file or --stdin"}, exit_code=2)

    if args.text_file:
        raw = Path(args.text_file).read_text(encoding="utf-8", errors="replace")
    else:
        raw = sys.stdin.read()

    has_backticks = "```" in raw
    s = strip_fences(raw)

    try:
        json_text, remainder = extract_first_json_object(s)
    except Exception as e:
        fail("no_json_object_found", {"exception": str(e), "has_backticks": has_backticks})

    if remainder:
        sys.stderr.write("WARN extra_non_json_text_discarded\n")

    try:
        obj = json.loads(json_text)
    except Exception as e:
        jt = json_text.strip()
        if jt.startswith("{{") and jt.endswith("}}"):
            try:
                obj = json.loads(jt[1:-1])
                json_text = jt[1:-1]
            except Exception:
                fail("invalid_json", {"exception": str(e), "has_backticks": has_backticks, "repair": "double_brace_failed"})
        else:
            fail("invalid_json", {"exception": str(e), "has_backticks": has_backticks})

    normalized = normalize_for_domain(obj, args.domain or "iteration")

    sys.stdout.write(json.dumps(normalized, indent=2) + "\n")

if __name__ == "__main__":
    main()
