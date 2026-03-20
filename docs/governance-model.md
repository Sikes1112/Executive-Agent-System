# OPERATIONS_NAVIGATOR_RULES.md — Full-Scope Ops Contract (Exec Authoritative)

This file is the **enforcement contract** for full-scope operations across OpenClaw.
It exists to prevent the most common collapse mode of agent systems: **entropy from mixed modes, silent architectural drift, and untrusted ticket generation**.

---

## 1) Mode Locking (No Cross-Mode Operations)

All work must declare one of the following modes at the top of the session:

- **STABILIZATION** — runtime validation only (status, drift, security audit, perms, health checks).
- **DEBUG** — targeted failure resolution with minimal change surface area.
- **EVOLUTION** — controlled system expansion (new agents, new contracts, new pipeline stages).
- **RESEARCH** — external knowledge import (docs/framework comparisons) with *no runtime changes*.

**Rule:** No cross-mode operations.
- If in STABILIZATION/DEBUG, do not change architecture or pipeline order.
- If in RESEARCH, do not change runtime, configs, or workspaces.
- EVOLUTION is the only mode where architecture changes are permitted.

---

## 2) Architecture Freeze Policy (Prevents Silent Drift)

In **STABILIZATION** or **DEBUG**:

- **DO NOT modify**:
  - apply layer scripts (e.g., `core/pipeline/apply.py`, validators, gates)
  - core governance docs (`SOUL.md`, `IDENTITY.md`, delegation envelopes)
  - pipeline ordering (gate → normalize → allowlist → approve → apply)
  - baseline manifests / drift mechanism (except explicitly re-baselining in EVOLUTION)

Architecture changes require an explicit mode switch to **EVOLUTION**.

---

## 3) Helper Is Untrusted (Probabilistic Front-End)

Helper is a **translator**, not an architect.

Helper output is treated as **untrusted input** until validated by Exec and the existing gates.

---

## 4) Mandatory Ticket Envelope (Helper MUST NOT Emit Raw PATCH_MODE)

Helper MUST output a **Ticket Batch Envelope**.
Helper MUST NOT emit raw PATCH_MODE JSON directly to Iteration.

### 4.1 Batch Envelope Schema (Minimum)

Helper output MUST be JSON with:

- `batch_id` (string; unique)
- `origin_input_hash` (string; sha256 of the raw user input text)
- `created_at` (ISO string)
- `tickets` (array)

### 4.2 Ticket Envelope Schema (Minimum)

Each ticket MUST include:

- `ticket_id` (string; unique within batch)
- `intent_summary` (string; 1–3 sentences)
- `patch_scope` ("narrow" | "medium" | "wide")
- `target_paths` (array of strings; must be allowlist-eligible)
- `risk_level` ("low" | "medium" | "high")
- `depends_on` (array of ticket_id strings; may be empty)
- `patch_payload` (object) — **this is the only place PATCH_MODE appears**

### 4.3 patch_payload Requirements

`patch_payload` MUST be valid PATCH_MODE JSON and MUST include:
- `_full_object: true` for any JSON file write
- file operations limited to allowlist paths
- no tools, no web, no external fetch

**Exec Responsibility:** validate envelopes, extract `patch_payload`, and only then route to Iteration.

---

## 5) Batch Guardrails (Prevents Explosion)

- `MAX_TICKETS_PER_BATCH = 20`
- If Helper produces > 20 tickets: Exec must require explicit operator approval (or split into multiple batches).
- If any ticket has `risk_level = high`: Exec must require explicit operator approval.

---

## 6) Dependency Guardrails (DAG Only)

`depends_on` must form a **DAG**:
- No cycles
- All dependencies must reference valid `ticket_id`s in the same batch

Exec must reject a batch that fails DAG validation.

---

## 7) Auditability

For every batch:
- store the raw Helper output (envelope) with a timestamp
- store Exec’s validation result (PASS/FAIL + reasons)
- store the final list of routed tickets + order (topological order if deps exist)

Location: `~/.openclaw/workspace-exec/memory/` or an equivalent audit directory.
