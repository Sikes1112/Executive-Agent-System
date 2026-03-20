# Integration Example

## 1. Overview

workspace-exec sits between intent generation and workspace mutation. It does not produce intent — it receives it, validates it, and executes it through a controlled, fail-closed pipeline.

The host system is responsible for everything upstream: agent orchestration, decision-making, business logic, and producing valid intent or envelopes.

The upstream system may use local models, API-backed models, or a hybrid approach. workspace-exec governs execution only.
[ Your Agent / System ]
|
v
workspace-exec ← validates, enforces, applies
|
v
[ Workspace Files / Bundles ]

---

## 2. Integration Model

Two supported entry paths:

### A) Raw intent path

Use when your system produces natural-language or loosely-structured intent text.
agent output (text) → input file → run_intake.sh → envelope.json → run_batch.sh

`run_intake.sh` handles:
- envelope generation  
- screen ID inference  
- batch validation  

It emits `KEY=VALUE` lines including `ENVELOPE=<path>`.

---

### B) Direct envelope path

Use when your system constructs structured envelopes directly (preferred for production integrations).
your system → envelope.json → run_batch.sh

Envelope must conform to the batch schema validated by `core/batch/validate.py`.

---

## 3. Minimal Flow
Agent produces intent text
→ write to input.txt
→ run_intake.sh input.txt
→ generates envelope.json
→ validates batch
→ emits ENVELOPE=<path>
→ run_batch.sh $ENVELOPE
→ validates envelope
→ for each ticket (topological order):
→ invoke model
→ sanitize response
→ check allowlist
→ check entity guard
→ check approval policy
→ apply patches atomically
→ update baseline
→ workspace files mutated
→ audit artifacts written
→ exit 0

Each stage is fail-closed. Any stage failure stops the pipeline.

No mutation is applied unless all pipeline stages succeed for a ticket.

Live files are not modified until the final atomic apply completes.

---

## 4. Inputs and Outputs

### Inputs

| Input | Format | Used by |
|------|--------|--------|
| Raw intent | Plain text file | `run_intake.sh` |
| Envelope | JSON file (batch schema) | `run_batch.sh` |

---

### Outputs

| Output | Location | Notes |
|-------|----------|------|
| Mutated workspace files | `workspace-example/bundles/` | Only written on success |
| Intake audit artifacts | `audit/helper_runs/` | Input copy, envelope, validation |
| Execution audit artifacts | `audit/exec_runs/<timestamp>/` | Per-ticket output, envelope, validation |
| Exit code | Shell exit code | 0 = success; see error model for non-zero codes |

---

## 5. Example Commands

### Raw intent path

```bash
echo "add a settings screen" > input.txt

eval "$(bash entrypoints/run_intake.sh input.txt)"
# → sets ENVELOPE, VALIDATION, RUN_DIR, EXIT_CODE

bash entrypoints/run_batch.sh "$ENVELOPE"
Direct envelope path
bash entrypoints/run_batch.sh /path/to/envelope.json
With explicit workspace root
WORKSPACE_ROOT=/path/to/workspace-exec \
AUDIT_ROOT=/path/to/audit \
bash entrypoints/run_batch.sh envelope.json
6. Host Responsibilities
The integrating system is responsible for:
Producing valid intent or envelopes
Malformed envelopes are rejected before execution.
Handling exit codes
Non-zero exit means the current ticket failed and the batch stopped. Previously completed tickets may have already been applied.
Inspecting audit artifacts on failure
audit/exec_runs/ contains per-ticket outputs. <ticket_id>_iteration_output.txt is the primary debugging artifact.
Not bypassing the pipeline
Do not write directly to workspace bundles. All mutations must go through the execution pipeline.
7. What This System Does NOT Do
Does not manage or schedule agents
Does not store memory or session state
Does not interpret business logic or decide what to build
Does not retry on failure (except limited retries during intake for empty model responses)
Does not roll back previously applied tickets if a later ticket fails
Does not push changes to version control