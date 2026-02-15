#!/usr/bin/env python3
"""
iter_pack_validate.py
Validate applied Spec Pack files for completeness beyond "JSON parses".

Start small: validate domain/app_overview.json against expected v1 shape.

Usage:
  iter_pack_validate.py --workspace ~/.openclaw/workspace-exec --check app_overview
Exit codes: 0 pass, 2 fail
"""
import argparse, json, sys
from pathlib import Path

def fail(msg):
    print("FAIL:", msg, file=sys.stderr)
    raise SystemExit(2)

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"cannot parse {p}: {e}")

def check_app_overview(ws: Path):
    p = ws / "bundles/domain/app_overview.json"
    obj = load_json(p)

    required = ["app_name","one_sentence","primary_user","problem_statement","non_goals","constraints","glossary","user_journeys","success_metrics","assumptions"]
    for k in required:
        if k not in obj: fail(f"app_overview missing key: {k}")

    if not isinstance(obj["non_goals"], list): fail("non_goals must be array")
    if not isinstance(obj["constraints"], list): fail("constraints must be array")

    # glossary must be array of {term, definition}
    g = obj["glossary"]
    if not isinstance(g, list): fail("glossary must be array of {term, definition}")
    for i, it in enumerate(g):
        if not (isinstance(it, dict) and isinstance(it.get("term"), str) and isinstance(it.get("definition"), str)):
            fail(f"glossary[{i}] must be object with term/definition strings")

    # journeys/metrics/assumptions must be arrays of strings (simple v1)
    for key in ("user_journeys","success_metrics","assumptions"):
        v = obj[key]
        if not isinstance(v, list): fail(f"{key} must be array")
        if len(v) < 5: fail(f"{key} must have >=5 items (got {len(v)})")
        if not all(isinstance(x, str) for x in v):
            fail(f"{key} items must be strings in v1")

    print("PASS app_overview", file=sys.stderr)


def check_state_machines(ws: Path):
    p = ws / "bundles/domain/state_machines.json"
    obj = load_json(p)
    machines = obj.get("machines")
    if not isinstance(machines, list) or len(machines) == 0:
        fail("state_machines.machines must be nonempty array")

    req = ["name","states","events","initial_state","terminal_states","transitions","invariants"]
    for mi, m in enumerate(machines):
        if not isinstance(m, dict):
            fail(f"machines[{mi}] must be object")
        for k in req:
            if k not in m:
                fail(f"machines[{mi}] missing key: {k}")
        if not isinstance(m["events"], list): fail(f"machines[{mi}].events must be array")
        evset = set([e for e in m["events"] if isinstance(e, str)])
        if not isinstance(m["transitions"], list): fail(f"machines[{mi}].transitions must be array")
        for ti, t in enumerate(m["transitions"]):
            if not isinstance(t, dict): fail(f"machines[{mi}].transitions[{ti}] must be object")
            for k in ("from","event","to","guards","actions"):
                if k not in t: fail(f"machines[{mi}].transitions[{ti}] missing key: {k}")
            if not isinstance(t["guards"], list) or not isinstance(t["actions"], list):
                fail(f"machines[{mi}].transitions[{ti}].guards/actions must be arrays")
            ev = t["event"]
            if isinstance(ev, str) and ev not in evset:
                fail(f"machines[{mi}] transition event not declared in events[]: {ev}")

    print("PASS state_machines", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--check", required=True, choices=["app_overview","state_machines"])
    args = ap.parse_args()
    ws = Path(args.workspace).expanduser()

    if args.check == "app_overview":
        check_app_overview(ws)
    elif args.check == "state_machines":
        check_state_machines(ws)

if __name__ == "__main__":
    main()
