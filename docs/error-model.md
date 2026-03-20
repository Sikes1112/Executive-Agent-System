# Error Model

## 1. Overview

The system is **fail-closed**. Any non-zero exit from a pipeline stage halts execution immediately. No stage is skipped on failure and no retry is attempted within a stage.

All mutations are **atomic at the ticket level**. If a failure occurs before the final apply stage completes, no changes are written to the live workspace.

`run_batch.sh` runs under `set -euo pipefail`. A failure in `run_once.sh` for any ticket causes the entire batch to stop — no subsequent tickets are processed.

---

## 2. Exit Code Table

Exit code 2 is used as a general failure code across multiple components. The specific failure source must be determined from the emitting component and audit artifacts.

| Exit Code | Component | Meaning | Retryable | Notes |
|-----------|-----------|---------|-----------|-------|
| 0 | All | Success | — | |
| 2 | `run_batch.sh` | Invalid usage, missing envelope, or batch validation failure | No | Generic failure code used by most scripts |
| 2 | `run_once.sh` | Empty response from LLM invoke | Yes | Model may be unavailable or timed out |
| 2 | `run_once.sh` (via `sanitize.py`) | JSON extraction/normalization failed | Yes | Malformed model output; payload artifacts copied to run dir |
| 2 | `run_once.sh` (via `allowlist.py`) | Patch targets disallowed paths | No | Path not in `contracts/allowlists/canonical_pack_paths.txt` |
| 2 | `run_once.sh` (via `approve.py`) | Approval policy P2 — explicit reject | No | Policy decision; requires envelope rebuild |
| 2 | `run_once.sh` (via `apply.py`) | Patch application failed | No | Invalid path, format, or sentinel |
| 2 | `run_intake.sh` | Invalid usage or input file not found | No | |
| 2 | `core/batch/validate.py` | Batch envelope fails validation | No | Returns structured JSON with error |
| 2 | `core/pipeline/sanitize.py` | No JSON found or parse failure | Yes | LLM output unusable |
| 2 | `core/pipeline/allowlist.py` | Path validation failed | No | |
| 2 | `core/pipeline/approve.py` | Policy P2 reject | No | |
| 2 | `core/pipeline/apply.py` | Patch format or path error | No | |
| 2 | `intake/adapters/invoke.py` | HTTP, network, or response error | Yes | |
| 3 | `core/pipeline/entity_guard.py` | Required file missing (`screens.json`) | No | Environment misconfiguration |
| 3 | `core/pipeline/approve.py` | Policy P3 reject | No | |
| 3 | `intake/oc_intent.sh` | Intake helper failure | Depends | Inspect underlying cause |
| 4 | `intake/oc_intent.sh` | Envelope not produced | No | Intake failure |
| 5 | `intake/oc_intent.sh` | Repeated empty model responses | No | Retry budget exhausted (5 attempts). Check provider before retrying. |
| 10 | `core/pipeline/entity_guard.py` | Unauthorized new screen IDs | No | Must update `allow_new_screen_ids` |
| 42 | `run_once.sh` | Ticket exceeds size limit | No | Reduce ticket size |
| 43 | `run_once.sh` | Lock held | Yes (manual) | Remove stale lock if safe |

---

## 3. Failure Categories

### Intake failures  
Failures before any ticket execution. Includes invalid input, envelope generation failure, or intake pipeline issues. Exit codes: 2, 3, 4, 5.

### Validation failures  
Failures in `core/batch/validate.py`. The envelope is structurally or semantically invalid. Exit code: 2.

### Pipeline failures  
Failures during ticket processing (`sanitize`, `allowlist`, `entity_guard`, `approve`). Exit codes: 2, 3, 10.

### Apply failures  
Patch accepted but could not be written. Live workspace remains unchanged. Exit code: 2.

### System failures  
Lock or environment issues preventing execution:
- Lock held (43)
- Ticket too large (42)
- Missing required files (3)

---

## 4. Propagation Rules

### Within `run_once.sh`
- Stages execute sequentially:
  invoke → sanitize → allowlist → entity_guard → approve → apply → baseline → swap
- Any non-zero exit stops execution immediately
- No retry is performed
- If failure occurs before apply completes, no changes are written

### Within `run_batch.sh`
- Envelope is validated once before execution
- Tickets run in dependency order
- First failing ticket stops the entire batch
- No retry and no rollback of previously applied tickets

### Intake behavior
- Empty model responses may be retried a limited number of times
- All other failures propagate immediately

---

## 5. Caller Handling Guidelines

Audit artifacts are the authoritative source for debugging and must be used to determine failure cause.

| Condition | Action |
|----------|--------|
| Exit 0 | Proceed. Outputs are valid. |
| Exit 2 — validation | Fix envelope. Do not retry unchanged. |
| Exit 2 — sanitize | Retry possible. Inspect model output if persistent. |
| Exit 2 — allowlist/apply | Fix patch or target paths. Do not retry. |
| Exit 2 — invoke | Retry after checking model availability. |
| Exit 3 — policy reject | Requires human decision. |
| Exit 3 — missing file | Fix environment. |
| Exit 4 | Intake failed. Inspect helper artifacts. |
| Exit 5 | Model failure. Check provider configuration. |
| Exit 10 | Unauthorized mutation. Update ticket. |
| Exit 42 | Reduce ticket size or adjust config. |
| Exit 43 | Check lock. Remove only if stale. |

---

## 6. Example Failure Flow

**Scenario:** Ticket targets a path not in the allowlist.

1. Envelope validates successfully  
2. `run_once.sh` begins ticket execution  
3. `sanitize.py` passes  
4. `allowlist.py` fails (exit 2)  
5. `run_once.sh` exits immediately  
6. No changes are written  
7. `run_batch.sh` exits and stops remaining tickets  
8. Audit artifacts contain full failure trace  

**Caller action:**  
Inspect audit output, correct `target_paths`, rebuild envelope, and re-run.