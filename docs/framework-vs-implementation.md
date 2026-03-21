# Framework vs Implementation

This repository can be read in two layers:

- **Control-layer framework pattern**: reusable architecture principles for governing agent execution.
- **Reference implementation**: the concrete scripts, contracts, and behaviors implemented in this codebase.

## 1) Reusable Control-Layer Pattern

The reusable pattern is:

1. Treat agent output as untrusted
2. Convert work into bounded units
3. Validate structure before execution
4. Route by explicit domain
5. Enforce a domain contract via sanitize-first validation
6. Branch execution by handling mode
7. Keep writes bounded, atomic, and auditable
8. Fail closed on contract/policy violations

This pattern can be adapted to different:
- model providers
- orchestrators
- business domains
- workspace/data layouts

## 2) Current Reference Implementation

In this repository, the above pattern is implemented with:

- `entrypoints/run_intake.sh`
- `entrypoints/run_batch.sh`
- `entrypoints/run_once.sh`
- `core/batch/validate.py`
- `core/pipeline/*.py`
- `core/domain_adapters/registry.json`

Current domains:
- `iteration` (mutation)
- `outreach` (generation)
- `reputationops` (pipeline)

Current handling modes:
- `iteration`: sanitize -> field_guard -> allowlist -> entity_guard -> approve -> apply
- `outreach`: sanitize -> persist normalized artifact + metadata -> success stop
- `reputationops`: sanitize -> persist normalized artifact + metadata -> success stop

## 3) How To Adapt The Pattern

If you adopt this architecture in another system, preserve these boundaries:

- Keep **decisioning** upstream (planner/orchestrator)
- Keep **execution governance** in a separate control layer
- Encode **domain contracts** in code-level validators
- Separate **mutation** and **non-mutation** handling paths
- Preserve **audit artifacts** as first-class outputs

Typical adaptation steps:
1. Define your ticket/envelope schema
2. Define domain classes and contracts
3. Implement sanitize-first validators per domain
4. Implement handling-mode branching
5. Add bounded apply path only for mutation domains
6. Add deterministic audit outputs

## 4) What Is Specific To This Repo

Implementation details here that you may replace in your own stack:

- File layout rooted at `workspace-example/bundles/`
- Current allowlist/entity guard semantics
- Current provider adapter (`ollama`, `anthropic`)
- Current approval policies (`P0`-`P3`)
- Current domain set and contracts

