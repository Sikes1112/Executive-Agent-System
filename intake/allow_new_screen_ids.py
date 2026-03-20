import json, re, sys
from pathlib import Path

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def infer_ids(text: str) -> list[str]:
    t = text.lower()

    # Skip negative/cleanup intents.
    if any(k in t for k in ["remove screen", "delete screen", "cleanup", "merge screens", "consolidate screens"]):
        return []

    # Must look like an add/new screen request.
    if "screen" not in t or not any(k in t for k in ["add", "create", "new screen"]):
        return []

    candidates: list[str] = []

    patterns = [
        r"(?:screen\s+id)\s*(?:should\s+be)?\s*[:=]\s*['\"]([a-z0-9_]+)['\"]",
        r"(?:screen\s+id)\s+(?:should\s+be)\s+['\"]([a-z0-9_]+)['\"]",
        r"(?:id)\s*[:=]\s*['\"]([a-z0-9_]+)['\"]",
        r"only\s+allow\s+new\s+screen\s+id[s]?\s*[:=]?\s*\[?\s*['\"]([a-z0-9_]+)['\"]",
        r"add\s+(?:a\s+|a\s+new\s+)?screen\s+['\"]?([a-z0-9_]+)['\"]?",
        r"add\s+(?:a\s+|a\s+new\s+)?([a-z0-9][a-z0-9 \-]{0,40})\s+screen",
        r"create\s+(?:a\s+|a\s+new\s+)?([a-z0-9][a-z0-9 \-]{0,40})\s+screen",
    ]

    for pat in patterns:
        for m in re.finditer(pat, t):
            raw = m.group(1)
            if not raw:
                continue
            cand = raw if re.fullmatch(r"[a-z0-9_]+", raw) else slugify(raw)
            if cand and cand not in candidates:
                candidates.append(cand)

    return candidates[:5]

def main() -> int:
    if len(sys.argv) != 3:
        print("usage: helper_allow_new_screen_ids.py <input_text_file> <envelope_json_file>", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    env_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"missing input file: {input_path}", file=sys.stderr)
        return 2
    if not env_path.exists():
        print(f"missing envelope file: {env_path}", file=sys.stderr)
        return 2

    input_text = input_path.read_text(errors="ignore")
    inferred = infer_ids(input_text)
    if not inferred:
        return 0

    env = json.loads(env_path.read_text(encoding="utf-8"))
    tickets = env.get("tickets") or []
    if not isinstance(tickets, list) or not tickets:
        # If envelope has no tickets, nothing to do (keep fail-closed elsewhere).
        return 0

    changed = 0
    for t in tickets:
        if not isinstance(t, dict):
            continue
        # Do not overwrite if already present.
        if t.get("allow_new_screen_ids"):
            continue
        # Strict default: allow exactly ONE inferred id.
        t["allow_new_screen_ids"] = inferred[:1]
        changed += 1

    if changed:
        env_path.write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
