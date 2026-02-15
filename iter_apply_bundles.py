#!/usr/bin/env python3
"""
Apply normalized Iteration PATCH_MODE bundles into the Exec workspace bundles/ tree.

Rules:
- Fail closed if any path is not in canonical_pack_paths.txt
- Write JSON patches as pretty JSON
- For .ts paths, expect patch to be {"content": "<string>"} (future tickets)

Usage:
  iter_apply_bundles.py --allowlist canonical_pack_paths.txt --normalized /tmp/iter_normalized_123.json --workspace ~/.openclaw/workspace-exec
"""
import argparse, json, sys
from pathlib import Path, PurePosixPath

def load_allowlist(p: Path) -> set[str]:
    out=set()
    for line in p.read_text(encoding="utf-8").splitlines():
        s=line.strip()
        if not s or s.startswith("#"): continue
        out.add(s)
    return out

def fail(msg: str, code: int=2):
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--allowlist", required=True)
    ap.add_argument("--normalized", required=True)
    ap.add_argument("--workspace", required=True)
    args=ap.parse_args()

    allow=load_allowlist(Path(args.allowlist))
    norm_path=Path(args.normalized)
    ws=Path(args.workspace).expanduser()

    obj=json.loads(norm_path.read_text(encoding="utf-8"))
    bundles=obj.get("bundles")
    if not isinstance(bundles, list) or not bundles:
        fail("FAIL: normalized JSON has no bundles[]")

    for item in bundles:
        if not isinstance(item, dict): fail("FAIL: bundle item not an object")
        rel=item.get("path")
        patch=item.get("patch")
        if not isinstance(rel, str): fail("FAIL: bundle path missing/invalid")
        if rel.startswith("/") or ".." in PurePosixPath(rel).parts or "\\" in rel:
            fail(f"FAIL: illegal path: {rel}")
        if rel not in allow:
            fail(f"FAIL: path not allowlisted: {rel}")
        if not isinstance(patch, dict):
            fail(f"FAIL: patch for {rel} must be object")

        out_path = ws / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if rel.endswith(".json"):
            out_path.write_text(json.dumps(patch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"WROTE_JSON {out_path}")
        elif rel.endswith(".ts"):
            content = patch.get("content")
            if not isinstance(content, str):
                fail(f"FAIL: .ts patch must include string patch.content for {rel}")
            out_path.write_text(content.rstrip("\n") + "\n", encoding="utf-8")
            print(f"WROTE_TS {out_path}")
        else:
            fail(f"FAIL: unsupported extension for {rel}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
