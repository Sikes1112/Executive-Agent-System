import argparse
import json, os, sys
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "domain_adapters" / "registry.json"

def load_ids(obj):
    if isinstance(obj, dict) and "screens" in obj and isinstance(obj["screens"], list):
        lst = obj["screens"]
    elif isinstance(obj, list):
        lst = obj
    else:
        return set()
    ids = set()
    for s in lst:
        if isinstance(s, dict) and "id" in s:
            ids.add(s["id"])
    return ids

def resolve_guard_behavior(ticket: dict | None, domain_override: str | None) -> str:
    if domain_override is not None:
        domain_raw = domain_override
    else:
        domain_raw = ticket.get("domain") if isinstance(ticket, dict) else None

    if domain_raw is None:
        domain = "iteration"
    elif not isinstance(domain_raw, str):
        raise ValueError("invalid_domain_type")
    else:
        domain = domain_raw.strip() or "iteration"

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    adapters = registry.get("adapters")
    if not isinstance(adapters, dict):
        raise ValueError("invalid_adapter_registry")
    if domain not in adapters:
        raise ValueError(f"unknown_domain:{domain}")

    adapter = adapters.get(domain)
    if not isinstance(adapter, dict):
        raise ValueError(f"invalid_adapter:{domain}")
    guard_behavior = adapter.get("guard_behavior")
    if not isinstance(guard_behavior, str) or not guard_behavior.strip():
        raise ValueError(f"invalid_guard_behavior:{domain}")
    return guard_behavior.strip()

def main():
    script_dir = Path(__file__).resolve().parent
    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", str(script_dir.parents[2]))).expanduser().resolve()

    ap = argparse.ArgumentParser()
    ap.add_argument("normalized_json_file")
    ap.add_argument("ticket_json_file", nargs="?")
    ap.add_argument("--domain", required=False)
    args = ap.parse_args()

    norm_path = Path(args.normalized_json_file)
    ticket_path = Path(args.ticket_json_file) if args.ticket_json_file else None

    current_path = workspace_root / "workspace-example/bundles/ui_spec/screens.json"
    if not current_path.exists():
        print(f"GUARD_FAIL missing current file: {current_path}", file=sys.stderr)
        return 3

    allowed_ids = load_ids(json.loads(current_path.read_text()))

    # Optional per-ticket override: allow specific new IDs only.
    allow_new = set()
    ticket = None
    if ticket_path and ticket_path.exists():
        try:
            ticket = json.loads(ticket_path.read_text())
            raw = ticket.get("allow_new_screen_ids") or []
            if isinstance(raw, list):
                allow_new = {x for x in raw if isinstance(x, str) and x.strip()}
        except Exception:
            # If ticket is unreadable, ignore override (fail-closed behavior stays).
            allow_new = set()

    try:
        guard_behavior = resolve_guard_behavior(ticket, args.domain)
    except ValueError as e:
        print(f"SCREENS_GUARD_FAIL {e}", file=sys.stderr)
        return 2

    if guard_behavior == "passthrough":
        print("SCREENS_GUARD_PASS (passthrough)")
        return 0
    if guard_behavior != "iteration":
        print(f"SCREENS_GUARD_FAIL unsupported_guard_behavior:{guard_behavior}", file=sys.stderr)
        return 2

    norm = json.loads(norm_path.read_text())
    bundles = norm.get("bundles") or []

    for b in bundles:
        if b.get("path") != "bundles/ui_spec/screens.json":
            continue
        patch = b.get("patch")
        if patch is None:
            continue

        patched_ids = load_ids(patch)
        new_ids = sorted(patched_ids - allowed_ids)
        if not new_ids:
            print("SCREENS_GUARD_PASS")
            return 0

        # If any new IDs exist, allow only those explicitly approved on the ticket.
        not_allowed = sorted([x for x in new_ids if x not in allow_new])
        if not_allowed:
            print("SCREENS_GUARD_FAIL new_screen_ids=" + ",".join(not_allowed), file=sys.stderr)
            if allow_new:
                print("SCREENS_GUARD_NOTE allowed_by_ticket=" + ",".join(sorted(allow_new)), file=sys.stderr)
            return 10

        print("SCREENS_GUARD_PASS (ticket_override)")
        return 0

    # If no screens.json bundle touched, pass.
    print("SCREENS_GUARD_PASS (not_applicable)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
