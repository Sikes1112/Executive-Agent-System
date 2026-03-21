# workspace-exec

`workspace-exec` is a domain-aware executive control layer for agent systems.

It is designed to sit between agent output and state mutation so execution is bounded, auditable, and fail-closed.

## How to use this repository

This repository serves two purposes:

1. **Reference architecture**
   → see how to build a domain-aware executive control layer for agent systems  
   → start with: docs/framework-vs-implementation.md, docs/architecture.md

2. **Runnable implementation**
   → run the current system locally  
   → start with: docs/quickstart.md

If you want to adapt this system to your own agents:
→ read docs/domain_onboarding_template.md

## Architecture Pattern (Reusable)

At a high level, the control-layer pattern is:
1. Accept untrusted intent (raw text or structured work items)
2. Validate and order work (schema + dependency checks)
3. Route work by domain
4. Enforce domain contracts through sanitize-first validation
5. Branch execution by handling mode
6. Persist audit artifacts for every run
7. Fail closed on contract or policy violations

This pattern is independent of any single model provider, orchestrator, or product domain.

## This Repository (Current Implementation)

This implementation is domain-aware and currently supports three domains:

- `iteration` (mutation domain)
  - result contract: PATCH_MODE mutation payload
  - handling: full bounded mutation pipeline
- `outreach` (generation domain)
  - result contract: normalized generation result
  - handling: sanitize + artifact persistence + controlled stop (no apply)
- `reputationops` (pipeline domain)
  - result contract: normalized pipeline result
  - handling: sanitize + artifact persistence + controlled stop (no apply)

### Current Ticket/Bulk Behavior

- Batch envelopes are validated and executed in dependency order
- Execution is sequential and fail-closed
- Tickets are domain-aware through optional `ticket.domain`
- Domain-specific output artifacts are written under `audit/exec_runs/<timestamp>/`

## Supported vs Intentionally Unsupported

### Supported now

- Intake path (`run_intake.sh`) and direct envelope path (`run_batch.sh`)
- Domain-aware routing (`iteration`, `outreach`, `reputationops`)
- Sanitization and contract enforcement per domain
- Bounded mutation apply for `iteration`
- Non-mutation sanitize-only success paths for `outreach` and `reputationops`
- Audit artifact generation for helper and execution runs

### Intentionally unsupported now

- Applying non-mutation domain outputs to workspace bundles
- Cross-ticket rollback after partial batch success
- Parallel ticket execution
- Automatic retries across pipeline stages
- Runtime code/schema evolution through docs-only configuration

## Using This As A Reference Architecture

If you are integrating into your own agent system, keep your existing orchestrator and specialists. Reuse the control-layer boundary:

- Keep upstream planning, routing, and reasoning where it already exists
- Normalize work into bounded tickets with explicit domain and scope
- Enforce sanitize-first contracts before any mutation path
- Separate handling modes:
  - `mutation_apply`
  - `sanitize_only_non_mutation`
  - explicit unsupported/fail paths
- Keep all executions auditable and fail-closed

Start here:
- [Framework vs Implementation](docs/framework-vs-implementation.md)
- [Architecture](docs/architecture.md)
- [Domain Behavior](docs/domain-behavior.md)
- [Domain Onboarding Template](docs/domain_onboarding_template.md)

## Running This Repo Today

Start here:
- [Operator Quickstart](docs/quickstart.md)
- [Configuration](docs/configuration.md)
- [Contracts](docs/contracts.md)
- [Error Model](docs/error-model.md)
- [Limitations](docs/limitations.md)

### First-run example (raw intent)

```bash
echo "add a settings screen" > /tmp/intent.txt
WORKSPACE_ROOT="$(pwd)" bash entrypoints/run_intake.sh /tmp/intent.txt
# copy ENVELOPE=... from output
WORKSPACE_ROOT="$(pwd)" bash entrypoints/run_batch.sh <ENVELOPE_PATH>
```

### First-run example (domain-specific direct envelope)

Use a direct envelope with explicit `domain` per ticket when you want deterministic domain routing, then run:

```bash
WORKSPACE_ROOT="$(pwd)" bash entrypoints/run_batch.sh /path/to/envelope.json
```

## Repository Layout

```text
workspace-exec/
├── contracts/
├── core/
├── docs/
├── entrypoints/
├── intake/
├── audit/
└── workspace-example/
```

## Safety Model

- Fail-closed execution
- Allowlisted mutation paths for mutation domain outputs
- Domain-specific contracts enforced in sanitize step
- Per-ticket atomic mutation apply for mutation domain
- Audit artifacts for traceability and debugging

