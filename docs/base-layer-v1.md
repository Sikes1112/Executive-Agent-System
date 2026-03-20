# BASE_LAYER_V1.md — OpenClaw System Base Layer v1 (SEALED)

## Status
**SEALED (Immutable):** Base Layer v1 is frozen.
No base-layer edits are allowed without a **version bump** (v1 → v2) using the Change Protocol.

**Seal Date (local):** 2026-02-16

---

## Purpose
Provide a boring, deterministic, governed foundation so product-layer work can proceed without
fragile runtime behavior, silent corruption, or governance bypass.

Base Layer v1 ensures:
- deterministic specialist execution
- governed bundle mutation
- no silent corruption
- drift detection is meaningful
- execution remains stable after inactivity

---

## Machine Context (v1 Reference)
- Node: Mac mini (local-only)
- RAM: 32GB
- Provider: Ollama (local inference)
- OpenClaw: **2026.2.12**
- Ollama: **0.16.1**
- No external web exposure
- No daemons beyond OpenClaw gateway
- Specialists are deterministic-only

---

## Models Present (Ollama)
- qwen2.5-coder:14b-32k (ID: a0ea7c61c958)
- qwen2.5-coder:14b      (ID: 9ec8897f747e)
- llama3.1:8b            (ID: 46e0c10c039e)
- deepseek-r1:8b         (ID: 6995872bfe4c)

Model usage is routed by Exec; Iteration is expected to run under the configured local provider.

---

## Architecture (Base Layer Components)

### 1) Control Plane — Exec (Executive Router)
- Owns governance + policy + approvals
- Owns run receipts + memory logs
- Owns all mutations of `bundles/`
- Invokes Helper and Iteration through canonical entrypoints

Workspace:
`~/.openclaw/workspace-exec/`

Key directories:
- `bundles/`
- `memory/`
- `tools/`

---

### 2) Iteration Specialist (Deterministic PATCH_MODE Compiler)
Properties:
- Stateless, ticket-scoped
- No tools, no browsing
- JSON-only output
- Must pass: sanitize → gate → allowlist → screens guard → approval → apply

Canonical entrypoint:
`~/.openclaw/workspace-exec/entrypoints/run_once.sh`

**Structural invariants (v1):**
- **Single-writer lock** prevents concurrent bundle mutation
- **Atomic apply transaction** prevents partial-apply corruption:
  - stage → apply → recompute baseline → atomic swap

---

### 3) Helper Layer (Natural Language → Envelope JSON)
Purpose:
- Converts natural language into envelope JSON
- Computes `origin_input_hash`
- Supports ticket-level `allow_new_screen_ids`

Canonical entrypoint:
`~/.openclaw/workspace-exec/entrypoints/run_intake.sh`

Validation tool:
`~/.openclaw/workspace-exec/core/batch/validate.py`

---

### 4) Guardrails (v1)
- **Path allowlist:** only canonical bundle paths are writable
- **Screens no-new-IDs guard:** blocks new screen IDs unless envelope includes `allow_new_screen_ids`
- **Sanitizer fail-closed:** `{ "ok": false }` halts run, copies artifacts, exits nonzero
- **Drift detection:** `_baseline.sha256` represents current bundle state

---

## Bundle Contract (v1)
Root:
`~/.openclaw/workspace-exec/workspace-example/bundles/`

Structure:
- `contracts/`
- `domain/`
- `tests/`
- `ui_spec/`
  - `components.json`
  - `navigation.json`
  - `screens.json`
- `_baseline.sha256`

Current screen IDs:
- inbox
- review_detail
- draft_reply
- action_items
- settings
- profile

---

## Sealed Surface Fingerprints (Hashes)
These define the **immutable base layer surface** for v1.

- `entrypoints/run_once.sh`
  - sha256: **3e405c56a2a8e309c1209322f40c8afd86d852c8755c03bf34a968bd3de34e68**
- `entrypoints/run_intake.sh`
  - sha256: **862d15c65270eef2f5e6909ee841b90ab8ac30261a3539e70e2126b668ceebce**
- `entrypoints/run_batch.sh`
  - sha256: **5740a6a14063e947c782ecd97cb0723b3e80d542632da4225dcea46df2620103**
- `core/drift.sh`
  - sha256: **8149492f5b5d37466b744665ed2a19b515905b13c509b9ba63c127ac3f0e3ab3**

---

## Guarantees (v1)

### G1 — No Silent Corruption (Bundle Writes)
- Sanitizer failures halt (fail-closed)
- Only allowlisted paths can be written
- Atomic apply ensures either:
  - all patches land + baseline is updated, or
  - nothing changes

### G2 — Deterministic Specialist Boundary
- Iteration produces JSON-only PATCH_MODE
- No tools, no browsing, no side effects outside authorized bundle paths

### G3 — Governance Integrity
- New screen IDs require explicit envelope permission via `allow_new_screen_ids`
- Only Exec-run entrypoints mutate bundles

### G4 — Traceability
- Helper persists input/envelope/validation artifacts in exec memory
- Iteration run receipt includes ticket + session id + artifact paths

---

## Non-Goals (v1)
- No product feature work in base layer
- No new frameworks
- No “polish” edits
- No additional micro-guards unless a true structural weakness is proven

---

## Change Protocol (v1 → v2)
Base Layer changes are forbidden unless ALL steps are followed.

1) Create: `BASE_LAYER_V2_PROPOSAL.md` containing:
   - weakness description (silent corruption / drift / ambiguity / bypass)
   - concrete failure mode and impact
   - minimal change proposed
   - rollback plan

2) Implement changes in a controlled edit.
3) Recompute and record new sha256 fingerprints.
4) Run a verification pass (helper + iteration + drift check).
5) Only then declare v2 sealed.

---

## Seal Statement
Base Layer v1 is sealed and boring by design.
Product-layer development must not modify base-layer scripts, guards, or governance primitives without a v2 bump.
