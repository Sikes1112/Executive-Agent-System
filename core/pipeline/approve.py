#!/usr/bin/env python3
import json, sys, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--policy", choices=["P0","P1","P2","P3"], required=True)
ap.add_argument("--raw-text-file", required=True)
ap.add_argument("--normalized-json-file", required=True)
args = ap.parse_args()

raw = open(args.raw_text_file, "r", encoding="utf-8").read()
obj = json.load(open(args.normalized_json_file, "r", encoding="utf-8"))

notes = obj.get("notes") or []
drift = ("```" in raw) or (raw.strip() and not raw.strip().startswith("{"))  # fences or leading non-JSON
hard = any(str(n).startswith(("LIMIT_EXCEEDED","REWRITE_REQUIRES_APPROVAL","MISSING_","UNMET:")) for n in notes)

if args.policy == "P0":
    decision = "ACCEPT"
    exit_code = 0
elif args.policy == "P1":
    decision = "ACCEPT_FLAG" if (drift or hard or notes) else "ACCEPT"
    exit_code = 0
elif args.policy == "P2":
    decision = "REJECT"
    exit_code = 2
else:  # P3
    decision = "REJECT"
    exit_code = 3

print(json.dumps({
  "policy": args.policy,
  "decision": decision,
  "flags": {
    "format_drift": bool(drift),
    "notes_nonempty": bool(notes),
    "hard_notes_present": bool(hard),
  },
  "notes": notes
}, separators=(",",":")))
raise SystemExit(exit_code)
