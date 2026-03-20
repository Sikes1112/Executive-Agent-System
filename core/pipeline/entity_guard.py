import json, os, sys
from pathlib import Path

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

def main():
    script_dir = Path(__file__).resolve().parent
    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", str(script_dir.parents[2]))).expanduser().resolve()

    if len(sys.argv) < 2:
        print("usage: entity_guard.py <normalized_json_file> [ticket_json_file]", file=sys.stderr)
        return 2

    norm_path = Path(sys.argv[1])
    ticket_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else None

    current_path = workspace_root / "workspace-example/bundles/ui_spec/screens.json"
    if not current_path.exists():
        print(f"GUARD_FAIL missing current file: {current_path}", file=sys.stderr)
        return 3

    allowed_ids = load_ids(json.loads(current_path.read_text()))

    # Optional per-ticket override: allow specific new IDs only.
    allow_new = set()
    if ticket_path and ticket_path.exists():
        try:
            ticket = json.loads(ticket_path.read_text())
            raw = ticket.get("allow_new_screen_ids") or []
            if isinstance(raw, list):
                allow_new = {x for x in raw if isinstance(x, str) and x.strip()}
        except Exception:
            # If ticket is unreadable, ignore override (fail-closed behavior stays).
            allow_new = set()

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
