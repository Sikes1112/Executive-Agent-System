import json
import sys
from pathlib import Path

ROOT = Path.home() / ".openclaw/workspace-exec" / "bundles"
SCREENS = ROOT / "ui_spec" / "screens.json"

# Invariants (product-layer contract)
REQUIRED_EXISTING_IDS = ["inbox", "review_detail", "draft_reply", "action_items", "settings", "profile"]

def fail(msg):
    print("TEST_FAIL:", msg)
    sys.exit(1)

def load_json(p: Path):
    if not p.exists():
        fail(f"Missing {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"{p.name} invalid JSON: {e}")

def get_screen_ids(data):
    screens = data.get("screens")
    if "screens" not in data:
        fail("screens.json must contain top-level key 'screens'")
    if not isinstance(screens, list):
        fail("screens.json 'screens' must be a list")
    ids = []
    for i, s in enumerate(screens):
        if not isinstance(s, dict):
            fail(f"screens[{i}] must be an object")
        sid = s.get("id")
        if not isinstance(sid, str) or not sid.strip():
            fail(f"screens[{i}] missing valid 'id'")
        ids.append(sid)
    return ids

def test_screens_json_shape_and_ids():
    data = load_json(SCREENS)
    ids = get_screen_ids(data)

    if len(ids) == 0:
        fail("screens.json must not be empty")

    # Existing IDs must remain present (prevents accidental wipe)
    missing = [x for x in REQUIRED_EXISTING_IDS if x not in ids]
    if missing:
        fail(f"Missing required existing screen ids: {missing}")

def test_no_duplicate_screen_ids():
    data = load_json(SCREENS)
    ids = get_screen_ids(data)
    if len(ids) != len(set(ids)):
        fail(f"Duplicate screen ids found: {ids}")

if __name__ == "__main__":
    test_screens_json_shape_and_ids()
    test_no_duplicate_screen_ids()
    print("ALL_TESTS_PASS")
