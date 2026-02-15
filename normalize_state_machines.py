#!/usr/bin/env python3
import json
from pathlib import Path

PATH = Path("/Users/sikesadmin/.openclaw/workspace-exec/bundles/domain/state_machines.json")

def main():
    obj = json.loads(PATH.read_text(encoding="utf-8"))
    machines = obj.get("machines")
    if not isinstance(machines, list):
        raise SystemExit("FAIL: machines must be a list")

    changed = False
    for m in machines:
        if not isinstance(m, dict):
            raise SystemExit("FAIL: machine not object")
        events = m.get("events")
        trans = m.get("transitions")
        if not isinstance(events, list) or not isinstance(trans, list):
            raise SystemExit("FAIL: machine missing events/transitions arrays")
        event_set = set([e for e in events if isinstance(e, str)])

        # ensure transition schema + collect used events
        for t in trans:
            if not isinstance(t, dict):
                raise SystemExit("FAIL: transition not object")
            ev = t.get("event")
            if isinstance(ev, str) and ev not in event_set:
                events.append(ev)
                event_set.add(ev)
                changed = True
            if "guards" not in t:
                t["guards"] = []
                changed = True
            if "actions" not in t:
                t["actions"] = []
                changed = True
            # ensure they are arrays
            if not isinstance(t["guards"], list) or not isinstance(t["actions"], list):
                raise SystemExit("FAIL: guards/actions must be arrays")

    if changed:
        PATH.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("OK: normalized state_machines.json (added events + guards/actions)")
    else:
        print("OK: no changes needed")

if __name__ == "__main__":
    main()
