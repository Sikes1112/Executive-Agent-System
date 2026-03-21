# Domain Behavior Summary

This document is the runtime behavior summary for supported domains in this repository.

## Supported Domains

| Domain | Class | Sanitizer contract | Post-sanitize behavior |
|---|---|---|---|
| `iteration` | mutation | PATCH_MODE mutation object | full bounded mutation pipeline + atomic apply |
| `outreach` | generation | normalized generation result | sanitize-only artifact persistence + controlled stop |
| `reputationops` | pipeline | normalized pipeline result | sanitize-only artifact persistence + controlled stop |

## Domain Routing

- Ticket domain is optional.
- If omitted, domain defaults to `iteration`.
- Batch validation allows `iteration`, `outreach`, and `reputationops`.

## Mutation Domain (`iteration`)

Expected output shape:
- PATCH_MODE JSON object with `ticket`, `mode`, `output`, `bundles`, `notes`

Execution path:
1. sanitize
2. field_guard
3. allowlist
4. entity_guard
5. approve
6. apply (staged + atomic swap)

Outcome:
- Mutations may be applied if all gates pass.

## Generation Domain (`outreach`)

Expected output shape:
- normalized generation result object
- top-level keys: `mode`, `iteration`, `result`, `notes`

Execution path:
1. sanitize
2. persist normalized outreach artifact
3. persist outreach metadata artifact
4. controlled success stop (no apply)

Outcome:
- No workspace mutation apply path is entered.

## Pipeline Domain (`reputationops`)

Expected output shape:
- normalized pipeline result object
- top-level keys: `mode`, `iteration`, `result`, `notes`

Execution path:
1. sanitize
2. persist normalized reputationops artifact
3. persist reputationops metadata artifact
4. controlled success stop (no apply)

Outcome:
- No workspace mutation apply path is entered.

## Non-Mutation Domain Persistence

For `outreach` and `reputationops`, metadata artifacts include:
- `ticket_id`
- `domain`
- `handling_mode` = `sanitize_only_non_mutation`
- `status` = `ok`
- `normalized_artifact`
- `run_stage_reached` = `sanitize_complete`

## Batch Semantics Across Domains

- Batch executes in dependency order.
- Domain-specific output logs are named `<ticket_id>_<domain>_output.txt`.
- Non-mutation sanitize-only completion is treated as successful ticket completion for supported non-mutation domains.
- Batch remains fail-closed for all other failures.

