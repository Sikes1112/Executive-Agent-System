import json
from pathlib import Path

ROOT = Path.home() / ".openclaw/workspace-exec" / "bundles"
SCREENS = ROOT / "ui_spec" / "screens.json"

def test_screens_json_shape():
    assert SCREENS.exists(), f"Missing {SCREENS}"
    data = json.loads(SCREENS.read_text(encoding="utf-8"))
    assert "screens" in data, "screens.json must contain top-level key 'screens'"
    assert isinstance(data["screens"], list), "screens.json 'screens' must be a list"
    for i, s in enumerate(data["screens"]):
        assert isinstance(s, dict), f"screens[{i}] must be an object"
        assert "id" in s and isinstance(s["id"], str) and s["id"].strip(), f"screens[{i}] missing valid 'id'"

def test_no_duplicate_screen_ids():
    data = json.loads(SCREENS.read_text(encoding="utf-8"))
    ids = [s["id"] for s in data["screens"] if isinstance(s, dict) and "id" in s]
    assert len(ids) == len(set(ids)), f"Duplicate screen ids found: {ids}"
