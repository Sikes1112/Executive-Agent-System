# ReputationOps Pipeline Domain Onboarding Plan

## Scope
This document is a docs-first onboarding plan for `reputationops` as a pipeline domain.

Current intent:
- Preserve all current runtime behavior in this iteration.
- Define the minimum safe implementation sequence for a later runtime rollout.

## Current State Snapshot (Ground Truth)
- Adapter is already registered as `reputationops` with:
  - `mode: "pipeline"`
  - `guard_behavior: "passthrough"`
  - `result_handling.result_mode: "pipeline"`
  - `result_handling.sanitize_apply_supported: false`
  - Source: `core/domain_adapters/registry.json`
- Domain is accepted by batch validation allowlist:
  - `SUPPORTED_DOMAINS = {"iteration", "outreach", "reputationops"}`
  - Source: `core/batch/validate.py`
- Sanitizer currently supports only `iteration` and `outreach` domain contracts.
  - `reputationops` currently fails sanitize with `unsupported_result_mode_or_domain`.
  - Source: `core/pipeline/sanitize.py`
- `run_once.sh` has explicit sanitize-only handling for `outreach` only.
  - Non-mutation domains other than `outreach` currently exit with unsupported downstream handling.
  - Source: `entrypoints/run_once.sh`
- `run_batch.sh` has explicit sanitize-only success exception handling for `outreach` only.
  - Source: `entrypoints/run_batch.sh`

## Domain Classification
- Domain: `reputationops`
- Classification: `pipeline` (non-mutation)
- Mutation/apply behavior: not eligible for field/entity guard + apply path.

## Proposed Adapter Metadata
Target metadata for future completion (keeping current keys and adding explicit contract metadata):

```json
{
  "name": "reputationops",
  "prompt_path": "core/prompts/reputationops_specialist.md",
  "mode": "pipeline",
  "guard_behavior": "passthrough",
  "result_handling": {
    "result_mode": "pipeline",
    "sanitize_apply_supported": false,
    "normalized_result_contract": {
      "contract_id": "normalized_reputationops_result.v1",
      "status": "target_only_not_enforced",
      "required_top_level_keys": ["mode", "iteration", "result", "notes"],
      "field_requirements": {
        "mode": "must be the literal string 'pipeline'",
        "iteration": "must preserve input iteration metadata as provided",
        "result": {
          "required_keys": ["status", "summary", "artifacts"],
          "status_values": ["ok", "needs_input", "blocked"],
          "artifacts_item_shape": ["name", "type", "content"]
        },
        "notes": "array of strings"
      }
    }
  }
}
```

## Proposed Result Contract Shape
Normalized ReputationOps output contract for sanitizer enforcement:

```json
{
  "mode": "pipeline",
  "iteration": {},
  "result": {
    "status": "ok | needs_input | blocked",
    "summary": "string",
    "artifacts": [
      {
        "name": "string",
        "type": "string",
        "content": {}
      }
    ]
  },
  "notes": ["string"]
}
```

Contract rules:
- Top-level object required.
- Required top-level keys: `mode`, `iteration`, `result`, `notes`.
- `mode` must equal `pipeline`.
- `result.status` must be one of `ok`, `needs_input`, `blocked`.
- `result.summary` must be a string.
- `result.artifacts` must be an array; each item requires `name`, `type`, `content`.
- `content` may be object or string to support structured and rendered artifacts.
- `notes` must be an array of strings.

## Sanitization Expectations
- Add domain-aware ReputationOps normalization branch in `core/pipeline/sanitize.py`.
- Enforce contract fail-closed (same strictness level as existing `outreach` validation):
  - reject non-object payloads
  - reject missing required keys
  - reject invalid enum values
  - reject invalid nested types
- Keep no-repair behavior unchanged (no silent schema fixes).

## Downstream Handling Recommendation
Recommended mode after sanitize for `reputationops`:
- `sanitize_only_non_mutation`

Rationale:
- Aligns with non-mutation domain behavior.
- Avoids entering mutation guard/apply path.
- Preserves safety-critical mutation pipeline boundaries.

## Artifact Persistence Plan
On sanitize success for `reputationops`, persist two artifacts under the run directory (matching current outreach pattern):
- Normalized payload artifact:
  - `<ticket_stem>.normalized.reputationops.json`
- Metadata artifact:
  - `<ticket_stem>.metadata.reputationops.json`

Metadata minimum fields:
- `ticket_id`
- `domain` (value: `reputationops`)
- `handling_mode` (value: `sanitize_only_non_mutation`)
- `status` (value: `ok`)
- `normalized_artifact` (path string)
- `run_stage_reached` (value: `sanitize_complete`)

## Batch Handling Expectations
- Keep existing batch envelope validation behavior and ordering semantics unchanged.
- Continue accepting `reputationops` domain in batch validation.
- Add explicit sanitize-only success handling for `reputationops` in batch orchestration, analogous to outreach handling, including metadata artifact copy into run directory.
- Preserve deterministic output file naming:
  - `<ticket_id>_<domain>_output.txt`

## Exact Files Likely To Be Touched Later
Docs/spec first, then minimal runtime changes when rollout starts:

- `docs/reputationops_onboarding_plan.md` (this plan; update with rollout evidence)
- `core/prompts/reputationops_specialist.md` (tighten output contract instructions)
- `core/domain_adapters/registry.json` (add `normalized_result_contract` metadata block)
- `core/pipeline/sanitize.py` (implement ReputationOps normalized contract enforcement)
- `entrypoints/run_once.sh` (add ReputationOps sanitize-only artifact persistence path)
- `entrypoints/run_batch.sh` (treat ReputationOps sanitize-only completion as success and copy metadata artifact)

Files expected to remain untouched for this onboarding:
- `core/pipeline/field_guard.py`
- `core/pipeline/entity_guard.py`
- `core/exec_runner.py`
- `core/batch/validate.py` (already includes `reputationops`)

## Recommended Safe Rollout Order
1. Finalize and approve this plan.
2. Define final `normalized_reputationops_result.v1` contract details.
3. Update `core/prompts/reputationops_specialist.md` to match the contract exactly.
4. Add contract metadata block to `core/domain_adapters/registry.json`.
5. Implement strict `reputationops` validator in `core/pipeline/sanitize.py`.
6. Add sanitize-only artifact persistence branch in `entrypoints/run_once.sh`.
7. Add sanitize-only success handling + metadata copy branch in `entrypoints/run_batch.sh`.
8. Run minimal targeted checks:
   - single `reputationops` ticket via `run_once.sh` validates sanitize-only success path
   - mixed-domain batch verifies stop-on-failure and sanitize-only success behavior remain correct
   - regression checks for `iteration` and `outreach` unchanged
9. Document final behavior and evidence in `docs/`.

## Explicit Not Doing Yet
- Not modifying `run_once.sh` in this change.
- Not modifying `run_batch.sh` in this change.
- Not modifying `core/pipeline/sanitize.py` in this change.
- Not modifying `core/domain_adapters/registry.json` in this change.
- Not changing any guard, approval, or apply behavior.
- Not introducing new dependencies.
- Not performing refactors or formatting-only edits.
