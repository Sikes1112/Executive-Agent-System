# Adopting workspace-exec

workspace-exec is an execution-governance layer.

It sits between your agents' output and real-world mutation.

If your system currently allows agents to:
- write files
- call tools
- mutate state directly

this repo replaces that layer with one that is **validated, constrained, audited, and fail-closed**.

It does not replace your agents.

It replaces the part of your system where things can silently break.

---

## Role in Your System

Your system already has:
- agents
- planning / reasoning
- orchestration

Keep all of that.

Insert workspace-exec at the point where intent becomes mutation.
Your Agents / Orchestrator
↓
workspace-exec
↓
Safe, deterministic state changes

Agents produce intent.

workspace-exec decides if that intent is allowed to become reality.

---

## What This System Handles

Once intent enters workspace-exec, it is no longer trusted.

The system enforces:

- **Validation**
  - envelope schema
  - DAG correctness
  - ticket limits

- **Constraint Enforcement**
  - path allowlisting
  - entity guards (e.g. new IDs require explicit permission)
  - approval policies

- **Execution**
  - invokes a stateless specialist model
  - extracts structured PATCH_MODE output
  - applies changes atomically

- **Audit Logging**
  - every run produces a full artifact trail
  - input → envelope → model output → applied changes

- **Drift Detection**
  - SHA256 baseline of workspace state
  - `core/drift.sh` detects unauthorized mutation

All gates are **fail-closed**.

Invalid output is rejected—not repaired.

---

## What Your System Must Provide

You have two integration paths:

### Option A — Natural Language Intent

Provide plain text input.

workspace-exec handles translation → execution.

```bash
echo "add a settings screen" > /tmp/intent.txt
WORKSPACE_ROOT="$(pwd)" entrypoints/run_intake.sh /tmp/intent.txt
```
Option B — Structured Envelope (Recommended)
Provide a pre-built envelope.
This is the direct integration path for existing systems.
{
  "batch_id": "b001",
  "origin_input_hash": "<sha256>",
  "created_at": "2026-03-18T00:00:00Z",
  "tickets": [
    {
      "ticket_id": "t1",
      "intent_summary": "Add Settings screen",
      "patch_scope": "medium",
      "target_paths": ["bundles/ui_spec/screens.json"],
      "risk_level": "low",
      "depends_on": []
    }
  ]
}
Your system already produces tasks.
Map them to this schema and hand them off.
Integration Flow
Your System
  → produces intent or tickets
  → calls workspace-exec

workspace-exec
  → validates (schema, DAG, limits)
  → invokes specialist
  → enforces gates (fail-closed)
  → applies changes atomically
  → logs audit artifacts

Your System
  → reads updated state
  → or reads audit artifacts

Drift detection is available via `core/drift.sh` and is not automatic.

Agents never mutate state directly.
They produce intent only.
What to Keep vs Replace
Keep	Replace
Your agents	Direct file writes
Your orchestrator	Tool-calling execution layers
Your planning logic	Unvalidated LLM output
Your task generation	Silent mutations
You are not changing how your system thinks.
You are changing how it executes.
Customization Surface
Provider
ITERATION_PROVIDER=ollama
ITERATION_MODEL=qwen2.5-coder:14b-32k
or
ITERATION_PROVIDER=anthropic
ITERATION_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=...
Specialist Behavior
Defined by:
core/prompts/iteration_specialist.md
Change this to redefine:
domain
output format
constraints
Allowlist
contracts/allowlists/canonical_pack_paths.txt
Controls what can be mutated.
Anything outside this list is rejected.
Approval Policy
APPROVAL_POLICY=P0  # always accept
APPROVAL_POLICY=P1  # default
APPROVAL_POLICY=P2  # always reject
APPROVAL_POLICY=P3  # dry-run
Intake Layer
Optional.
If you already produce envelopes:
skip run_intake.sh
call run_batch.sh directly
Assumptions
Workspace state is structured (JSON / TS bundles)
Single-writer execution (no parallel mutation)
Domain-specific validation lives in allowlist + entity guard
Base layer is sealed (v1)
Known Limitations
Entity guard is domain-specific (UI-oriented)
Intake layer is minimal (pattern-based)
No partial batch resume
Audit is not append-only enforced
Bottom Line
You do not need a new agent system.
You need a safer execution layer.
workspace-exec is that layer.