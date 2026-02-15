# CONTINUITY_MODE.md — Exec Internal Continuity Procedure (Deterministic)

This is NOT a specialist agent.
This is an exec-owned procedure for generating continuity outputs deterministically.

## When to use
Use Continuity Mode when:
- a project feels messy or stalled
- the next action is unclear
- multiple threads exist
- deadlines are present or unknown
- you are about to delegate work and need a clean brief

## Input: Continuity Snapshot (required)
If any REQUIRED field is missing, output INPUT INCOMPLETE and make the Next Smallest Action a verification step.

REQUIRED:
- Project
- Snapshot Timestamp
- Snapshot Scope
- Current Goal
- Constraints
- Active Threads List
- Deadlines
- Ticket Summary
- Branch/Variant Summary

Optional high-value:
- Recent changes since last snapshot
- Known blockers
- Do-not-touch areas
- Acceptance criteria

## Output: Canonical Continuity Schema (0–8)
Output EXACTLY these headings in order. Bullets only. No preamble.

0) Input Completeness
- Status: COMPLETE | INPUT INCOMPLETE
- Missing fields (if any)
- Assumptions (max 5)

1) Current State Snapshot (5–10 bullets)
- Concrete facts only (paths, IDs, exact names)

2) Delta Since Last Snapshot
- Max 7 bullets OR “No prior snapshot available”

3) Open Threads / Unknowns (max 7)
- Threads or Unknowns only
- Unknowns include a verification step

4) Risk Flags (max 5)
- Each: [Drift Type] — why it matters — impact
Allowed Drift Types:
- Structural Drift
- Execution Stall
- Branch Fragmentation
- Deadline Compression
- Context Overload
- Ambiguity Fog

5) Next Smallest Action (ONE step)
- Concrete, <= 20 minutes
- If INPUT INCOMPLETE: make this a verification action

6) Decision Points for Exec (0–3)
- Only decisions that block progress

7) Proposed Exec Instructions (3–8)
- Imperative, safe, minimal
- No tools unless explicitly approved

8) Confidence
- Score: 0–100
- 1–3 bullets: what would raise it

## Filling Rules (Exec)
- No invention: if not in snapshot, label Unknown.
- Prefer unblocking actions over polish.
- If multiple threads: surface Top 3 by urgency/impact.
- Deadlines > blockers > missing source of truth > unfinished branches > everything else.

## Validation (Exec)
Hard-fail if:
- headings missing/out of order
- any extra headings
- any text before 0)
- more than one Next Smallest Action
- drift types outside allowed list
