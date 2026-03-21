# Domain Onboarding Template

Use this template when adding a new execution domain to this control layer.

This document distinguishes reusable onboarding steps from current implementation specifics.

## 1. Classify The Domain

Choose one domain class:

- **mutation**: domain output may continue to bounded apply path
- **generation**: domain output is non-mutation and should persist artifacts only
- **pipeline**: domain output is non-mutation pipeline artifact/result output

Current examples in this repository:
- `iteration` -> mutation
- `outreach` -> generation
- `reputationops` -> pipeline

## 2. Define Domain Metadata

Add/update adapter entry in `core/domain_adapters/registry.json`:
- `name`
- `prompt_path`
- `mode`
- `guard_behavior`
- `result_handling.result_mode`
- `result_handling.sanitize_apply_supported`

Optional but recommended:
- `result_handling.normalized_result_contract`

## 3. Define Sanitizer Contract

Every domain must have explicit sanitize-time contract enforcement in `core/pipeline/sanitize.py`.

At minimum enforce:
- top-level type
- required keys
- enum constraints
- nested artifact/object types

Do not rely on prompt instructions alone.

## 4. Define Post-Sanitize Handling Mode

Select one handling mode:
- `mutation_apply`
- `sanitize_only_non_mutation`
- explicit unsupported fail-closed path

Current mapping in this repo:
- `iteration` -> `mutation_apply`
- `outreach` -> `sanitize_only_non_mutation`
- `reputationops` -> `sanitize_only_non_mutation`

## 5. Define Batch Semantics

Ensure:
- `core/batch/validate.py` domain allowlist includes the domain
- output naming remains deterministic (`<ticket_id>_<domain>_output.txt`)
- non-mutation sanitize-only success behavior is explicit in `run_batch.sh`

## 6. Define Artifact Persistence (Non-Mutation)

For sanitize-only non-mutation domains, persist:
- normalized domain result artifact
- metadata artifact containing:
  - `ticket_id`
  - `domain`
  - `handling_mode`
  - `status`
  - `normalized_artifact`
  - `run_stage_reached`

## 7. Validation Checklist

Before declaring a domain onboarded:
1. domain metadata resolves correctly
2. sanitizer enforces domain contract fail-closed
3. run_once handling mode branch is implemented and tested
4. run_batch semantics are explicit and tested
5. docs are updated for contracts, behavior, and limitations

## 8. Reusable vs Repo-Specific Guidance

Reusable:
- domain classification
- sanitize-first enforcement
- explicit handling-mode branching
- fail-closed policy

Repo-specific:
- exact file paths and script names
- current domain names and contracts
- current artifact naming conventions

