# Contracts Reference

This document summarizes current runtime contracts for this repository.

## 1. Envelope Contract

Used by:
- `entrypoints/run_batch.sh`
- `core/batch/validate.py`

Top-level required fields:
- `batch_id` (string)
- `origin_input_hash` (string)
- `created_at` (string)
- `tickets` (array, 1..20)

Batch validation enforces:
- unique `ticket_id`
- valid `depends_on` references
- DAG only (no cycles)
- supported `domain` values when provided

Supported `domain` values:
- `iteration`
- `outreach`
- `reputationops`

If `domain` is omitted, runtime defaults to `iteration` during adapter resolution.

## 2. Ticket Contract

Required fields:
- `ticket_id`
- `intent_summary`
- `patch_scope` (`narrow|medium|wide`)
- `target_paths` (array)
- `risk_level` (`low|medium|high`)
- `depends_on` (array)

Optional fields:
- `domain`
- `allow_new_screen_ids`
- `mutation_targets`

## 3. Domain Output Contracts

### 3.1 `iteration` (mutation)

Expected sanitized shape:
- PATCH_MODE object with:
  - `ticket`
  - `mode`
  - `output` = `PATCH_MODE`
  - `bundles`
  - `notes`

### 3.2 `outreach` (generation)

Expected sanitized shape:
- object with top-level keys:
  - `mode` = `generation`
  - `iteration`
  - `result`
  - `notes`

`result` requires:
- `status` in `{ok, needs_input, blocked}`
- `summary` (string)
- `artifacts` (array of `{name,type,content}`)

### 3.3 `reputationops` (pipeline)

Expected sanitized shape:
- object with top-level keys:
  - `mode` = `pipeline`
  - `iteration`
  - `result`
  - `notes`

`result` requires:
- `status` in `{ok, needs_input, blocked}`
- `summary` (string)
- `artifacts` (array of `{name,type,content}`)

## 4. Runtime Handling Modes

### Mutation apply path
For `iteration`:
- sanitize -> field_guard -> allowlist -> entity_guard -> approve -> apply

### Sanitize-only non-mutation path
For `outreach` and `reputationops`:
- sanitize -> persist normalized artifact + metadata -> success stop

No apply path is entered for these non-mutation domains.

## 5. Audit Artifacts

Batch run directory:
- `audit/exec_runs/<timestamp>/`

Common files:
- `envelope.json`
- `validation.json`
- `<ticket_id>_ticket.json`
- `<ticket_id>_<domain>_output.txt`

Non-mutation domains may also produce:
- `<ticket_stem>.normalized.<domain>.json`
- `<ticket_stem>.metadata.<domain>.json`

## 6. Locking and Atomicity

- Lock path is domain adapter lock suffix based: `core/locks/<suffix>_apply.lock`
- Mutation atomicity is per ticket
- No cross-ticket rollback

## 7. Integration Notes

- `target_paths` is advisory; allowlist and downstream guards are authoritative.
- Domain-aware routing depends on `ticket.domain` (or default).
- Unknown/invalid domains fail validation or route to adapter default behavior.

