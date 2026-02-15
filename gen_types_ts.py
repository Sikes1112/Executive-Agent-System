#!/usr/bin/env python3
import json
from pathlib import Path

WS = Path.home() / ".openclaw" / "workspace-exec"
domain_path = WS / "bundles" / "domain" / "domain_model.json"
rules_path = WS / "bundles" / "domain" / "validation_rules.json"
out_path = WS / "bundles" / "code_skeleton" / "types.ts"

domain = json.loads(domain_path.read_text(encoding="utf-8"))
rules = json.loads(rules_path.read_text(encoding="utf-8"))
enums = rules.get("enums", {})

def ts_union(values):
    # 'a' | 'b' | 'c'
    return " | ".join([f"'{v}'" for v in values])

# Map of enum name -> literal union
enum_unions = {}
for k, vals in enums.items():
    if isinstance(vals, list) and all(isinstance(x, str) for x in vals):
        enum_unions[k] = ts_union(vals)

# Field type mapping
def map_type(t: str) -> str:
    # Examples from your domain_model:
    # "string", "enum:Sentiment", "array:string", "array:ActionItem", "ReplyDraft"
    if t == "string":
        return "string"
    if t.startswith("enum:"):
        name = t.split(":", 1)[1]
        return name
    if t.startswith("array:"):
        inner = t.split(":", 1)[1]
        if inner == "string":
            return "string[]"
        return f"{inner}[]"
    # passthrough for entity names like ReplyDraft, ActionItem
    return t

entities = domain.get("entities", [])
# Preserve stable ordering by file order
lines = []
lines.append("// types.ts (deterministic, no imports)\n")

# Emit enums first (stable: sorted by name to avoid drift)
for name in sorted(enum_unions.keys()):
    lines.append(f"export type {name} = {enum_unions[name]};\n")

# If ActionStatus / ThreadStatusEnum exist as enums in rules, great.
# If not, but they appear in domain, they’ll be declared as interface field types; dev can add later.

for ent in entities:
    ename = ent.get("name")
    fields = ent.get("fields", [])
    if not ename or not isinstance(fields, list):
        continue
    lines.append(f"export interface {ename} {{")
    for f in fields:
        fname = f.get("name")
        ftype = f.get("type")
        req = bool(f.get("required", False))
        if not fname or not ftype:
            continue
        ts_t = map_type(str(ftype))
        opt = "" if req else "?"
        lines.append(f"  {fname}{opt}: {ts_t};")
    lines.append("}\n")

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
print(f"WROTE {out_path}")
