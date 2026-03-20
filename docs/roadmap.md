# roadmap.md — Direction

This document outlines current capabilities and likely areas of expansion.

It reflects current implementation and observed limitations. It is not a commitment or release plan.

---

## Current capabilities

- End-to-end execution: intent → envelope → validation → pipeline → atomic apply
- Fixed five-stage pipeline:
  - sanitize
  - allowlist
  - entity_guard
  - approve
  - apply
- Provider abstraction:
  - Ollama (local)
  - Anthropic (API)
- Batch execution with dependency-ordered DAG
- Sequential execution with single-writer lock
- Per-ticket atomicity (staging + swap)
- Approval policies (P0–P3)
- Entity guard (screen ID authorization)
- SHA256 baseline + drift detection
- Full audit trail:
  - input
  - envelope
  - validation
  - enriched ticket
  - raw model output
  - applied result

---

## Near-term

### Governance

- **Configurable entity guard**  
  Current implementation is hardcoded to screen IDs.  
  Should move to a declarative rule system so additional entity types do not require code changes.

- **Policy sensitivity by ticket**  
  Allow stricter approval policies for higher-risk tickets within the same batch.

- **Formalized note taxonomy**  
  Centralize and standardize recognized note prefixes used by the approval stage.

---

### Provider abstraction

- **Centralized provider configuration**  
  Current configuration is environment-based.  
  A thin configuration layer would allow per-run or per-batch overrides.

- **Pre-pipeline response validation**  
  Detect provider-level failures (auth, empty response) before entering sanitize.  
  Improves error clarity and reduces ambiguous pipeline failures.

---

### Integration ergonomics

- **Exit code reference**  
  Provide a machine-readable mapping of exit codes (e.g., 2, 10, 42, 43) for external systems.

- **Envelope builder utility**  
  Provide a CLI or script for constructing envelopes directly, bypassing intake heuristics.

- **Dry-run output visibility**  
  When `APPROVAL_POLICY=P3`, emit the computed patch for inspection without applying it.

---

## Longer-term

### Performance and batching

- **Parallel execution for independent tickets**  
  Enable concurrent execution for tickets without dependency edges.  
  Requires moving from global lock to scoped locking (e.g., per-bundle).

- **Incremental context loading**  
  Avoid reloading unchanged bundles into `current_objects`.  
  Reduces token usage and improves throughput.

---

### Governance

- **Multi-entity guard system**  
  Extend guard logic beyond screen IDs to other structural entities (routes, components, domain objects).

- **Policy-as-code**  
  Replace fixed policy tiers with rule-based approval definitions.

- **Rollback entrypoint**  
  Provide a script to restore the workspace to the last known-good baseline.

---

### Provider abstraction

- **Capability-aware configuration**  
  Allow provider definitions to declare constraints (e.g., context limits) and adjust enrichment behavior accordingly.

- **Response caching for replay**  
  Cache model responses keyed by ticket input to allow deterministic replays of pipeline stages.

---

### Integration ergonomics

- **Structured pipeline output**  
  Emit machine-readable summaries of stage results for programmatic consumers.

- **Bundle schema validation**  
  Introduce schema enforcement at apply time to validate bundle structure before writing.

---

## Summary

The system is currently focused on:

- deterministic execution
- strict mutation control
- auditability

Future work focuses on:

- expanding governance coverage
- improving provider flexibility
- enabling better integration with external systems
- scaling execution safely