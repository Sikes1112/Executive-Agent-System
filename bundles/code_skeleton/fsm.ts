// fsm.ts (deterministic, no imports)

export type GuardFn<C> = (ctx: C) => boolean;
export type ActionFn<C> = (ctx: C) => C;

export type Transition<C> = {
  from: string;
  event: string;
  to: string;
  guards: GuardFn<C>[];
  actions: ActionFn<C>[];
};

export type MachineDef<C> = {
  name: string;
  initialState: string;
  terminalStates: string[];
  transitions: Transition<C>[];
};

export function step<C>(m: MachineDef<C>, state: string, event: string, ctx: C): { state: string; ctx: C } {
  const candidates = m.transitions.filter(t => t.from === state && t.event === event);
  if (candidates.length === 0) throw new Error(`No transition for ${m.name}: ${state} --(${event})-> ?`);
  for (let i = 0; i < candidates.length; i++) {
    const t = candidates[i];
    let ok = true;
    for (let g = 0; g < t.guards.length; g++) {
      if (!t.guards[g](ctx)) { ok = false; break; }
    }
    if (!ok) continue;
    let nextCtx = ctx;
    for (let a = 0; a < t.actions.length; a++) nextCtx = t.actions[a](nextCtx);
    return { state: t.to, ctx: nextCtx };
  }
  throw new Error(`All guards failed for ${m.name}: ${state} --(${event})-> ?`);
}

export function run<C>(m: MachineDef<C>, events: string[], ctx: C): { state: string; ctx: C } {
  let s = m.initialState;
  let c = ctx;
  for (let i = 0; i < events.length; i++) {
    const r = step(m, s, events[i], c);
    s = r.state;
    c = r.ctx;
  }
  return { state: s, ctx: c };
}

export const ReviewLifecycle: MachineDef<any> = {
  name: "ReviewLifecycle",
  initialState: "NEW",
  terminalStates: ["RESOLVED", "ARCHIVED"],
  transitions: [{"from": "NEW", "event": "paste_review", "to": "ANALYZED", "guards": [], "actions": []}, {"from": "ANALYZED", "event": "extract_issues", "to": "DRAFTED", "guards": [], "actions": []}, {"from": "DRAFTED", "event": "draft_reply", "to": "EDITED", "guards": [], "actions": []}, {"from": "EDITED", "event": "user_edit", "to": "DRAFTED", "guards": [], "actions": []}, {"from": "DRAFTED", "event": "user_edit", "to": "EDITED", "guards": [], "actions": []}, {"from": "EDITED", "event": "mark_sent", "to": "SENT", "guards": [], "actions": []}, {"from": "SENT", "event": "resolve_follow_up", "to": "RESOLVED", "guards": [], "actions": []}, {"from": "RESOLVED", "event": "archive_review", "to": "ARCHIVED", "guards": [], "actions": []}],
};

export const ActionItemLifecycle: MachineDef<any> = {
  name: "ActionItemLifecycle",
  initialState: "OPEN",
  terminalStates: ["DONE", "CANCELED"],
  transitions: [{"from": "OPEN", "event": "start_work", "to": "IN_PROGRESS", "guards": [], "actions": []}, {"from": "IN_PROGRESS", "event": "pause_work", "to": "BLOCKED", "guards": [], "actions": []}, {"from": "BLOCKED", "event": "unblock", "to": "IN_PROGRESS", "guards": [], "actions": []}, {"from": "IN_PROGRESS", "event": "complete", "to": "DONE", "guards": [], "actions": []}, {"from": "OPEN", "event": "cancel", "to": "CANCELED", "guards": [], "actions": []}, {"from": "IN_PROGRESS", "event": "cancel", "to": "CANCELED", "guards": [], "actions": []}, {"from": "BLOCKED", "event": "cancel", "to": "CANCELED", "guards": [], "actions": []}],
};
