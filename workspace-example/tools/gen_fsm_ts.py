#!/usr/bin/env python3
import json
from pathlib import Path

WS = Path.home() / ".openclaw" / "workspace-exec"
src_path = WS / "bundles" / "domain" / "state_machines.json"
out_path = WS / "bundles" / "code_skeleton" / "fsm.ts"

obj = json.loads(src_path.read_text(encoding="utf-8"))
machines = obj.get("machines", [])

def lit_union(values):
    return " | ".join([f"'{v}'" for v in values])

lines = []
lines.append("// fsm.ts (deterministic, no imports)")
lines.append("")
lines.append("export type GuardFn<C> = (ctx: C) => boolean;")
lines.append("export type ActionFn<C> = (ctx: C) => C;")
lines.append("")
lines.append("export type Transition<C> = {")
lines.append("  from: string;")
lines.append("  event: string;")
lines.append("  to: string;")
lines.append("  guards: GuardFn<C>[];")
lines.append("  actions: ActionFn<C>[];")
lines.append("};")
lines.append("")
lines.append("export type MachineDef<C> = {")
lines.append("  name: string;")
lines.append("  initialState: string;")
lines.append("  terminalStates: string[];")
lines.append("  transitions: Transition<C>[];")
lines.append("};")
lines.append("")
lines.append("export function step<C>(m: MachineDef<C>, state: string, event: string, ctx: C): { state: string; ctx: C } {")
lines.append("  const candidates = m.transitions.filter(t => t.from === state && t.event === event);")
lines.append("  if (candidates.length === 0) throw new Error(`No transition for ${m.name}: ${state} --(${event})-> ?`);")
lines.append("  for (let i = 0; i < candidates.length; i++) {")
lines.append("    const t = candidates[i];")
lines.append("    let ok = true;")
lines.append("    for (let g = 0; g < t.guards.length; g++) {")
lines.append("      if (!t.guards[g](ctx)) { ok = false; break; }")
lines.append("    }")
lines.append("    if (!ok) continue;")
lines.append("    let nextCtx = ctx;")
lines.append("    for (let a = 0; a < t.actions.length; a++) nextCtx = t.actions[a](nextCtx);")
lines.append("    return { state: t.to, ctx: nextCtx };")
lines.append("  }")
lines.append("  throw new Error(`All guards failed for ${m.name}: ${state} --(${event})-> ?`);")
lines.append("}")
lines.append("")
lines.append("export function run<C>(m: MachineDef<C>, events: string[], ctx: C): { state: string; ctx: C } {")
lines.append("  let s = m.initialState;")
lines.append("  let c = ctx;")
lines.append("  for (let i = 0; i < events.length; i++) {")
lines.append("    const r = step(m, s, events[i], c);")
lines.append("    s = r.state;")
lines.append("    c = r.ctx;")
lines.append("  }")
lines.append("  return { state: s, ctx: c };")
lines.append("}")
lines.append("")

# Emit machine defs (typed loosely; transitions + strings are deterministic)
for m in machines:
    name = m.get("name")
    if not name:
        continue
    init = m.get("initial_state", "")
    terminals = m.get("terminal_states", [])
    transitions = m.get("transitions", [])

    # Normalize transitions: ensure guards/actions exist
    norm = []
    for t in transitions:
        norm.append({
            "from": t.get("from"),
            "event": t.get("event"),
            "to": t.get("to"),
            "guards": t.get("guards", []),
            "actions": t.get("actions", []),
        })

    lines.append(f"export const {name}: MachineDef<any> = {{")
    lines.append(f"  name: {json.dumps(name)},")
    lines.append(f"  initialState: {json.dumps(init)},")
    lines.append(f"  terminalStates: {json.dumps(terminals)},")
    lines.append(f"  transitions: {json.dumps(norm, ensure_ascii=False)},")
    lines.append("};")
    lines.append("")

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
print(f"WROTE {out_path}")
