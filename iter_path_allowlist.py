#!/usr/bin/env python3
"""
iter_path_allowlist.py
Fail closed if Iteration tries to touch any file path not in canonical_pack_paths.txt.

Usage:
  iter_path_allowlist.py --allowlist canonical_pack_paths.txt --normalized normalized.json

Exit codes:
  0 = PASS
  2 = FAIL (paths not allowed or cannot determine paths)
"""
import argparse, json, sys, pathlib

def load_allowlist(p: str) -> set[str]:
    lines = []
    for raw in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return set(lines)

def extract_paths(obj) -> list[str]:
    """
    Extract patch target paths from the normalized JSON.

    Your current normalized schema uses:
      - obj["bundles"][].{"path": "...", "patch": {...}}

    Also supports common alternates as fallbacks.
    """
    candidates = []

    # Primary: OpenClaw normalized hybrid schema
    b = obj.get("bundles")
    if isinstance(b, list):
        for item in b:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                candidates.append(item["path"])

    # Fallbacks: other patch shapes
    for key in ("patches","files","edits","ops"):
        v = obj.get(key)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and isinstance(item.get("path"), str):
                    candidates.append(item["path"])

    # De-dupe while preserving order
    seen=set(); out=[]
    for p in candidates:
        if p not in seen:
            seen.add(p); out.append(p)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowlist", required=True)
    ap.add_argument("--normalized", required=True)
    args = ap.parse_args()

    allow = load_allowlist(args.allowlist)
    try:
        obj = json.loads(pathlib.Path(args.normalized).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: cannot read/parse normalized JSON: {e}", file=sys.stderr)
        return 2

    paths = extract_paths(obj)
    if not paths:
        print("FAIL: could not extract any patch paths from normalized JSON", file=sys.stderr)
        return 2

    # Normalize: disallow absolute paths and parent traversal early.
    bad = []
    for p in paths:
        if p.startswith("/") or ".." in pathlib.PurePosixPath(p).parts or "\\" in p:
            bad.append(p)
            continue
        if p not in allow:
            bad.append(p)

    if bad:
        print("FAIL: disallowed paths detected:", file=sys.stderr)
        for p in bad:
            print(f"- {p}", file=sys.stderr)
        return 2

    print("PASS", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
