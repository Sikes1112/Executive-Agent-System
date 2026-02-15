#!/usr/bin/env python3
import argparse
import re
import sys
import json
from pathlib import Path

def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(2)

def read_text(p: Path) -> str:
    if not p.exists():
        fail(f"missing file: {p}")
    return p.read_text(encoding="utf-8", errors="strict")

def first_nonempty_line(s: str) -> str:
    for line in s.splitlines():
        if line.strip():
            return line.rstrip("\n")
    return ""

def last_nonempty_line(s: str) -> str:
    for line in reversed(s.splitlines()):
        if line.strip():
            return line.rstrip("\n")
    return ""

def assert_no_imports(s: str, label: str) -> None:
    if re.search(r'^\s*import\s+', s, flags=re.M):
        fail(f"{label}: imports are forbidden")

def assert_no_placeholders(s: str, label: str) -> None:
    if "..." in s:
        fail(f"{label}: contains placeholder '...'")

def assert_contains(s: str, needle: str, label: str) -> None:
    if needle not in s:
        fail(f"{label}: missing required text: {needle}")

def assert_regex(s: str, pattern: str, label: str, desc: str) -> None:
    if not re.search(pattern, s, flags=re.M):
        fail(f"{label}: missing required pattern ({desc}): {pattern}")

def validate_types(ts: str) -> None:
    label = "types.ts"
    assert_no_imports(ts, label)
    assert_no_placeholders(ts, label)

    # Common failure you already hit: whole file wrapped in { ... }
    first = first_nonempty_line(ts).lstrip()
    if first.startswith("{"):
        fail(f"{label}: looks wrapped in outer braces '{{ ... }}' (first nonempty line starts with '{{')")

    # Expect core exports exist (minimal guard)
    required = [
        "Sentiment",
        "ReplyTone",
        "ReplyDraftStatus",
        "ActionStatus",
        "ThreadStatusEnum",
        "Review",
        "ReplyDraft",
        "ActionItem",
        "IssueTag",
        "ThreadStatus",
    ]
    for r in required:
        assert_contains(ts, r, label)

def validate_validators(ts: str) -> None:
    label = "validators.ts"
    assert_no_imports(ts, label)
    assert_no_placeholders(ts, label)

    required_exports = [
        "Severity",
        "ValidationError",
        "export function isNonEmptyString",
        "export function minLength",
        "export function isOneOf",
        "export function isStringArray",
        "export function pushErr",
        "export function validateReplyDraft",
        "export function validateActionItem",
        "export function validateReview",
    ]
    for r in required_exports:
        assert_contains(ts, r, label)

    # Ensure deterministic allowed lists exist (prevents accidental drift)
    assert_regex(ts, r'^\s*const\s+VALID_SENTIMENT:\s+readonly\s+string\[\]\s*=\s*\[', label, "VALID_SENTIMENT const")
    assert_regex(ts, r'^\s*const\s+VALID_TONE:\s+readonly\s+string\[\]\s*=\s*\[', label, "VALID_TONE const")
    assert_regex(ts, r'^\s*const\s+VALID_DRAFT_STATUS:\s+readonly\s+string\[\]\s*=\s*\[', label, "VALID_DRAFT_STATUS const")
    assert_regex(ts, r'^\s*const\s+VALID_ACTION_STATUS:\s+readonly\s+string\[\]\s*=\s*\[', label, "VALID_ACTION_STATUS const")

def validate_fsm(ts: str, machine_names: list[str]) -> None:
    label = "fsm.ts"
    assert_no_imports(ts, label)
    assert_no_placeholders(ts, label)

    required = [
        "export function step",
        "export function run",
        "Transition",
        "MachineDef",
    ]
    for r in required:
        assert_contains(ts, r, label)

    # Ensure each machine is exported as const <Name>
    for name in machine_names:
        assert_regex(ts, rf'^\s*export\s+const\s+{re.escape(name)}\s*:', label, f"export const {name}: ...")

def load_machine_names(state_machines_path: Path) -> list[str]:
    if not state_machines_path.exists():
        return []
    try:
        obj = json.loads(state_machines_path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"state_machines.json invalid JSON: {e}")
    names = []
    for m in (obj.get("machines") or []):
        n = m.get("name")
        if isinstance(n, str) and n.strip():
            names.append(n.strip())
    return names

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, help="Workspace root (e.g. ~/.openclaw/workspace-exec)")
    ap.add_argument("--check", required=True, choices=["types", "validators", "fsm", "all"])
    args = ap.parse_args()

    ws = Path(args.workspace).expanduser().resolve()
    bundles = ws / "bundles"
    code = bundles / "code_skeleton"
    domain = bundles / "domain"

    if args.check in ("types", "all"):
        types_path = code / "types.ts"
        validate_types(read_text(types_path))

    if args.check in ("validators", "all"):
        validators_path = code / "validators.ts"
        validate_validators(read_text(validators_path))

    if args.check in ("fsm", "all"):
        fsm_path = code / "fsm.ts"
        machine_names = load_machine_names(domain / "state_machines.json")
        # If state_machines.json missing, still validate core runner shape
        validate_fsm(read_text(fsm_path), machine_names)

    print(f"PASS {args.check}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
