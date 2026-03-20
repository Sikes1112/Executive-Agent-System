# DELEGATION_ENVELOPES.md — Exec Hard Contracts + Validation

This file defines runtime-enforced delegation envelopes.
If a specialist does not comply, Exec must validate, sanitize, retry once, then fail-closed.

---

## Envelope: continuity (v1)

### Purpose
Continuity produces structured project-state summaries and next-action proposals.
Continuity never takes action.

### Forbidden (must refuse)
- File writes (create/modify/delete)
- Ticket creation or updates
- Routing/config changes
- Delegation/spawning
- CLI execution
- Tool/internet use unless explicitly approved read-only by Exec per-ticket

### Required Input Contract
If any REQUIRED header field is missing, continuity must output:
- `0) Input Completeness` → `Status: INPUT INCOMPLETE`
- list missing fields
- set Next Smallest Action to a verification step

REQUIRED Header fields:
- Project
- Snapshot Timestamp
- Snapshot Scope
- Current Goal
- Constraints
- Active Threads List
- Deadlines
- Ticket Summary
- Branch/Variant Summary

---

## Continuity Output Schema (Canonical, MUST MATCH)

Continuity must output EXACTLY these headings, in this order, with bullet content underneath.
No extra headings, no preamble, no “example”, no tables.

0) Input Completeness
- Status: COMPLETE | INPUT INCOMPLETE
- Missing fields (if any)
- Assumptions (max 5)

1) Current State Snapshot
- (5–10 bullets, concrete facts only)

2) Delta Since Last Snapshot
- (max 7 bullets) OR “No prior snapshot available”

3) Open Threads / Unknowns
- (max 7 bullets)
- Unknowns must include a proposed verification step

4) Risk Flags
- (max 5 bullets)
- Each bullet format: [Drift Type] — why it matters — impact

Allowed Drift Types (exactly one):
- Structural Drift
- Execution Stall
- Branch Fragmentation
- Deadline Compression
- Context Overload
- Ambiguity Fog

5) Next Smallest Action
- ONE step only, executable, <= 20 minutes
- If INPUT INCOMPLETE: action becomes verification

6) Decision Points for Exec
- 0–3 bullets

7) Proposed Exec Instructions
- 3–8 bullets, imperative, safe, minimal
- No tool requests unless justified and read-only

8) Confidence
- Score: 0–100
- (1–3 bullets) what would raise confidence

---

## Exec Validation Rules (Fail Closed)

Exec must validate every continuity response.

Hard-fail if any of the following is true:
- Missing any heading 0–8
- Headings out of order
- Any extra headings/sections
- Any preamble text before “0) Input Completeness”
- Any drift type outside the allowed list
- More than one Next Smallest Action

If hard-fail:
1) Count as failed attempt
2) Retry ONCE with the Noncompliance Retry Message (below)
3) Re-validate
4) If still fail → stop and return to user with:
   - what failed
   - what was expected
   - options: (a) proceed with Exec-only deterministic summary, (b) change model, (c) pause

---

## Noncompliance Retry Message (Exec → continuity)

NONCOMPLIANT OUTPUT.
Re-issue the response in the exact canonical schema.
Rules:
- Output ONLY headings 0–8 and bullets.
- No preamble, no explanations, no examples, no tables.
- Headings must match exactly and be in order.
- Include exactly ONE Next Smallest Action.

---

## Exec Sanitizer (If you must salvage content)

If continuity output contains useful bullets but breaks schema:
- Exec may extract ONLY bullets that map cleanly into the canonical headings.
- Exec must discard hallucinated references (files/paths/tickets not in snapshot).
- Exec must never invent missing facts to fill sections.

---

## Two-Pass Fill Protocol (Exec → continuity) — REQUIRED for compliance

Use this when continuity tends to “talk about the format” instead of emitting it.

### Pass 1 — Skeleton Only
Exec message MUST be:

PASS 1 (SKELETON ONLY).
Return ONLY the canonical headings 0) through 8) in order.
Under each heading, include placeholder bullets only (use "-" bullets), no prose.
Do not add any extra headings, examples, tables, or notes.
Do not fill content yet.

Then include the full Continuity Snapshot.

Validation after Pass 1:
- Headings 0–8 exist, in order
- No extra text outside headings + placeholder bullets

If noncompliant:
- Send the Noncompliance Retry Message once.
- If still noncompliant → fail-closed.

### Pass 2 — Fill Bullets Only
Exec message MUST be:

PASS 2 (FILL BULLETS ONLY).
Using the exact skeleton you returned in Pass 1, replace placeholders with real bullets.
Rules:
- Keep headings identical and in the same order.
- Bullet lists only. No paragraphs.
- Risk Flags must be: [Drift Type] — why it matters — impact.
- Next Smallest Action must be ONE step <= 20 minutes.

Then paste the Pass 1 skeleton back to continuity, followed by the same Continuity Snapshot.

Validation after Pass 2:
- Full canonical schema satisfied (per Exec Validation Rules)
- No hallucinated paths/tickets/tools beyond snapshot
- Exactly one Next Smallest Action
