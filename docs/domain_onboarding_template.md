# Domain Onboarding Template

## Purpose
Define a repeatable, low-risk onboarding pattern for new execution domains so additions follow the same controls as existing domains (`iteration`, `outreach`, `reputationops`) instead of ad hoc edits.

This template is documentation-only and is intended to preserve current runtime behavior while standardizing future onboarding.

## Domain classes

### Mutation domains
- Intent: produce workspace mutations that continue through guardrails and apply.
- Current example: `iteration`.
- Required behavior:
  - `mode` is mutation-like in adapter metadata.
  - `result_handling.sanitize_apply_supported = true`.
  - `guard_behavior = iteration` unless a new guard behavior is explicitly implemented.

### Generation domains
- Intent: produce normalized non-mutation artifacts/results.
- Current example: `outreach`.
- Required behavior:
  - `result_handling.sanitize_apply_supported = false`.
  - Sanitization still required.
  - Downstream handling must be explicit (e.g., sanitize-only artifact persistence).

### Pipeline domains
- Intent: domain-specific pipeline outputs that are not direct mutation apply.
- Current example: `reputationops`.
- Required behavior:
  - `result_handling.sanitize_apply_supported = false`.
  - Must define explicit downstream behavior before rollout beyond sanitize.

## Required adapter metadata
Define domain entry in `core/domain_adapters/registry.json` with at least:
- `name`: stable domain identifier.
- `prompt_path`: specialist system prompt path.
- `mode`: one of `mutation`, `generation`, `pipeline`.
- `guard_behavior`: currently `iteration` or `passthrough`.
- `result_handling.result_mode`: must align with domain class.
- `result_handling.sanitize_apply_supported`: boolean controlling whether run proceeds past sanitize.

Optional but recommended:
- `result_handling.normalized_result_contract` for documented target schema details.

## Result contract requirements
Every domain must have one explicit normalized result contract enforced by sanitize logic.

For mutation domains:
- Contract shape must remain compatible with existing patch-mode normalization and downstream guards/apply.

For non-mutation domains:
- Contract must be fully specified with:
  - required top-level keys
  - allowed enums/status values
  - artifact/item schema
  - notes type rules

Onboarding rule:
- Never rely on prompt-only schema guidance.
- Sanitize must enforce the same required shape.

## Sanitization rules
- Domain-specific normalization selection is required (`--domain` routed to domain validator).
- Failure mode must remain fail-closed with structured errors.
- Sanitizer must reject:
  - wrong top-level type
  - missing required keys
  - invalid enum values
  - invalid nested structure types

For non-mutation domains, sanitize success does not imply apply eligibility.

## Downstream handling modes
After sanitize, each domain must declare one handling mode:
- `mutation_apply`: continue through field/entity guard, approval, and apply.
- `sanitize_only_non_mutation`: persist normalized output + metadata artifact, then exit success.
- `unsupported_non_mutation`: explicit fail with domain-specific unsupported message.

Current mappings:
- `iteration` -> `mutation_apply`
- `outreach` -> `sanitize_only_non_mutation`
- `reputationops` -> currently non-mutation and treated as unsupported for post-sanitize apply

## Artifact persistence rules
For non-mutation domains, persist domain outputs as audit artifacts in the run directory:
- normalized payload artifact
- metadata artifact with, at minimum:
  - `ticket_id`
  - `domain`
  - `handling_mode`
  - `status`
  - pointer to normalized artifact path
  - `run_stage_reached`

For mutation domains, standard run output and existing audit artifacts remain unchanged.

## Batch handling rules
- Envelope validation must accept the new domain name (`core/batch/validate.py` supported domains).
- Batch ordering, dependency checks, and stop-on-failure semantics remain unchanged.
- Domain-specific artifact naming should remain deterministic (`<ticket_id>_<domain>_output.txt`).
- Any non-mutation success exception handling in batch orchestration must be explicit and scoped to that domain behavior.

## File touch matrix
Common onboarding touch points and rationale:

| File | Always vs conditional | Why it is touched |
|---|---|---|
| `core/domain_adapters/registry.json` | Always | Register domain metadata and handling mode. |
| `core/prompts/<domain>_specialist.md` | Always | Define strict output contract instructions for specialist. |
| `core/pipeline/sanitize.py` | Always | Enforce domain normalized contract in code (fail-closed). |
| `core/batch/validate.py` | Usually | Add domain to supported batch-domain allowlist. |
| `entrypoints/run_once.sh` | Conditional (non-mutation domains) | Add/adjust post-sanitize domain handling and artifact persistence behavior. |
| `entrypoints/run_batch.sh` | Conditional (domain-specific success semantics) | Handle domain-specific success/exception paths and metadata copy behavior. |
| `core/pipeline/field_guard.py` | Conditional | Only if a new guard behavior beyond `iteration`/`passthrough` is needed. |
| `core/pipeline/entity_guard.py` | Conditional | Only if a new guard behavior beyond `iteration`/`passthrough` is needed. |
| `docs/` | Always | Record onboarding pattern, contracts, and rollout notes. |

Safety note:
- Prefer docs-first planning and contract specification before any runtime file edits.

## Minimum safe rollout order
1. Classify domain as `mutation`, `generation`, or `pipeline`.
2. Define normalized result contract (required keys/types/enums).
3. Add/update specialist prompt for that contract.
4. Add adapter registry metadata and result handling flags.
5. Implement/confirm sanitize enforcement for the contract.
6. Update batch domain allowlist validation (if needed).
7. Implement/confirm downstream handling mode (apply vs sanitize-only vs unsupported).
8. Run minimal domain-focused validation checks.
9. Update docs with final contract, handling mode, and artifacts.

## Done criteria
A domain is onboarded only when all are true:
- Registry entry exists with valid metadata.
- Specialist prompt is present and aligned to sanitizer contract.
- Sanitizer enforces domain contract fail-closed.
- Batch validator accepts domain where intended.
- Downstream handling mode is explicit and tested (or intentionally unsupported with clear failure).
- Audit artifact behavior is deterministic and documented.
- Existing domain behavior (`iteration`, `outreach`) is unchanged in regression checks.
- Documentation reflects the final behavior and rollout constraints.

## Outreach example
Outreach is the reference generation-domain onboarding pattern:
- Domain class: `generation`.
- Registry signals:
  - `mode: generation`
  - `guard_behavior: passthrough`
  - `result_handling.result_mode: generation`
  - `result_handling.sanitize_apply_supported: false`
  - `normalized_result_contract` documented in adapter metadata.
- Sanitizer enforces:
  - top-level keys: `mode`, `iteration`, `result`, `notes`
  - `mode == generation`
  - `result.status in {ok, needs_input, blocked}`
  - artifact item shape and types.
- Downstream behavior:
  - sanitize-only success path
  - writes normalized outreach artifact + metadata artifact
  - does not run mutation guards/apply
  - batch runner treats this domain’s sanitize-only completion as success and copies metadata artifact.

## ReputationOps onboarding notes placeholder
Use this section when onboarding/finishing `reputationops` with the same template:
- Domain classification confirmation:
- Normalized result contract id/version:
- Sanitizer enforcement status:
- Downstream handling mode decision:
- Artifact persistence plan:
- Batch behavior notes:
- Rollout validation evidence:
