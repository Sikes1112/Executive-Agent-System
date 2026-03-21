# Integration Example

This document shows how to use `workspace-exec` as an execution control layer in a larger agent system.

## 1. Placement In Your Stack

Your upstream system remains responsible for:
- planning/reasoning
- deciding work items
- constructing intent or envelopes

`workspace-exec` is responsible for:
- validation
- domain routing
- sanitize-first contract enforcement
- bounded handling execution
- audit artifact persistence

## 2. Two Integration Paths

### Path A: raw intent

```text
upstream intent text -> run_intake.sh -> envelope -> run_batch.sh
```

### Path B: direct envelope

```text
upstream envelope -> run_batch.sh
```

Path B is preferred when your orchestrator already emits structured work.

## 3. Domain-Aware Integration

Each ticket may provide:
- `domain: iteration|outreach|reputationops`

Behavior by domain:
- `iteration`: mutation pipeline and possible apply
- `outreach`: sanitize-only artifact persistence and stop
- `reputationops`: sanitize-only artifact persistence and stop

## 4. Example Calls

Raw intent:

```bash
echo "add a settings screen" > input.txt
eval "$(bash entrypoints/run_intake.sh input.txt)"
bash entrypoints/run_batch.sh "$ENVELOPE"
```

Direct envelope:

```bash
bash entrypoints/run_batch.sh /path/to/envelope.json
```

## 5. Host Responsibilities

- Provide valid envelope/ticket shape
- Set provider/model env vars appropriate for targeted domains
- Handle non-zero exits as fail-closed outcomes
- Read audit artifacts for diagnostics

## 6. What This Layer Deliberately Does Not Do

- It does not replace your planner/orchestrator
- It does not invent business goals
- It does not provide cross-ticket rollback
- It does not apply non-mutation domain outputs to workspace state

