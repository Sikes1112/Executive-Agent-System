# Error Model

The runtime is fail-closed.

- Any non-zero stage/entrypoint failure stops the current execution path.
- `run_batch.sh` stops on first ticket failure (except supported sanitize-only non-mutation success handling).
- Mutation atomicity is per ticket.

## Exit Code Table

| Exit | Source | Meaning |
|---|---|---|
| 0 | all | success |
| 2 | entrypoints/pipeline/invoke/validate | generic validation/execution failure |
| 3 | pipeline | policy reject or required runtime file missing (context-specific) |
| 10 | `entity_guard.py` | unauthorized new screen IDs |
| 42 | `run_once.sh` | ticket exceeds `MAX_TICKET_CHARS` |
| 43 | `run_once.sh` | lock held |
| 44 | `run_once.sh` | adapter resolution failure |
| 45 | `run_once.sh` | unsupported non-mutation post-sanitize handling for resolved adapter |

## Domain-Aware Runtime Notes

### Mutation domain (`iteration`)
Failure at any stage in:
- sanitize
- field_guard
- allowlist
- entity_guard
- approve
- apply

causes ticket failure and batch stop.

### Non-mutation domains (`outreach`, `reputationops`)
On sanitize success, runtime persists normalized + metadata artifacts and exits ticket successfully without entering apply.

If sanitize fails, ticket fails and batch stops.

## Failure Propagation

- Batch envelope invalid -> batch exits before ticket execution
- Ticket failure -> batch stops immediately
- No cross-ticket rollback

## Debugging Artifacts

Check:
- `audit/helper_runs/`
- `audit/exec_runs/<timestamp>/`

Per-ticket logs:
- `<ticket_id>_<domain>_output.txt`

For sanitize-only non-mutation success:
- `<ticket_stem>.normalized.<domain>.json`
- `<ticket_stem>.metadata.<domain>.json`

