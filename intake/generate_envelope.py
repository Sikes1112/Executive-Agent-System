#!/usr/bin/env python3
import hashlib
import json
import datetime
import pathlib
import sys

if len(sys.argv) != 3:
    print("usage: helper_generate_envelope.py <input_txt> <output_json>")
    sys.exit(2)

raw_path = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])

raw = raw_path.read_text()
h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")

lower = raw.lower()

tickets = []
tid = 1

def add_ticket(intent, scope, paths, risk, deps, extra=None):
    global tid
    t = {
        "ticket_id": f"t{tid}",
        "intent_summary": intent,
        "patch_scope": scope,
        "target_paths": paths,
        "risk_level": risk,
        "depends_on": deps,
    }
    if isinstance(extra, dict):
        for k,v in extra.items():
            t[k] = v
    tickets.append(t)
    tid += 1

if "settings" in lower:
    add_ticket(
        "Add new Settings screen.",
        "medium",
        ["bundles/ui_spec/screens.json"],
        "low",
        []
    )

if "settings" in lower:
    add_ticket(
        "Add navigation route to Settings screen.",
        "medium",
        ["bundles/ui_spec/navigation.json"],
        "low",
        ["t1"] if tickets else []
    )

if "toggle" in lower or "dark mode" in lower:
    add_ticket(
        "Add Dark Mode toggle component.",
        "medium",
        ["bundles/ui_spec/components.json"],
        "low",
        ["t1"] if tickets else []
    )


import re

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

# Generic "add/create new X screen" rule (non-settings)
# Fires only when input includes add/create + screen and is not the special-case "settings" handled below.
if ("screen" in lower) and (("add" in lower) or ("create" in lower) or ("new screen" in lower)) and ("settings" not in lower) and not any(k in lower for k in ["cleanup","remove","delete","merge","consolidate","dedupe","de-dup"]):
    m = None
    patterns = [
        r'(?:screen\s+id)\s*(?:should\s*be\s*)?["\']([a-z0-9_]+)["\']',
        r'add\s+(?:a\s+|a\s+new\s+)?([a-z0-9][a-z0-9 \-]{0,40})\s+screen',
        r'create\s+(?:a\s+|a\s+new\s+)?([a-z0-9][a-z0-9 \-]{0,40})\s+screen',
    ]
    for pat in patterns:
        mm = re.search(pat, lower)
        if mm:
            m = mm
            break

    if m:
        raw_name = m.group(1)
        screen_id = raw_name if re.fullmatch(r"[a-z0-9_]+", raw_name) else slugify(raw_name)
        if screen_id:
            add_ticket(
                f"Add new {screen_id} screen.",
                "medium",
                ["bundles/ui_spec/screens.json"],
                "low",
                [],
                extra={"allow_new_screen_ids": [screen_id]}
            )
if not tickets:
    add_ticket(
        "Interpret input into minimal ticket batch.",
        "narrow",
        [],
        "medium",
        []
    )

envelope = {
    "batch_id": f"batch-{h[:12]}",
    "origin_input_hash": h,
    "created_at": now,
    "tickets": tickets
}

out_path.write_text(json.dumps(envelope, indent=2) + "\n")
