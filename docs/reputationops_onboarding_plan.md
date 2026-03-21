# ReputationOps Domain Notes (Implemented State)

This document records the current implemented state for `reputationops` in this repository.

## Status

`reputationops` is implemented as a **pipeline domain** with sanitize-only non-mutation handling.

## Current Runtime Behavior

- Adapter exists in `core/domain_adapters/registry.json`
- Batch validator supports `reputationops`
- Sanitizer enforces `reputationops` normalized contract
- `run_once.sh` persists:
  - normalized reputationops artifact
  - reputationops metadata artifact
- `run_batch.sh` treats sanitize-only reputationops completion as successful ticket completion

## Handling Mode

`reputationops` currently uses:
- `sanitize_only_non_mutation`

Meaning:
- sanitize is required
- mutation guards/apply path is not entered
- artifacts are persisted for audit and downstream consumption

## Contract Shape Summary

Top-level required keys:
- `mode`
- `iteration`
- `result`
- `notes`

Key constraints:
- `mode` must be `pipeline`
- `result.status` in `{ok, needs_input, blocked}`
- `result.artifacts[]` requires `name`, `type`, `content`

## Why This Exists

This note prevents drift where older docs treated `reputationops` as not yet wired.

For new domain additions, use [domain_onboarding_template.md](domain_onboarding_template.md).

