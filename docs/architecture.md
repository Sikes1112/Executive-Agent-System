# architecture.md — System Architecture

This document describes how `workspace-exec` operates as a control-plane execution layer for safe, deterministic, auditable mutation.

It sits between:

- upstream intent producers
- downstream workspace state

Its role is to turn proposed change into controlled mutation. It does not decide what should change. It validates structure, constrains writable surface area, applies policy, and commits approved changes atomically.

## Contents

1. [System overview](#1-system-overview)
2. [Core components](#2-core-components)
3. [Execution flow](#3-execution-flow)
4. [Pipeline breakdown](#4-pipeline-breakdown)
5. [Data flow](#5-data-flow)
6. [ASCII diagram](#6-ascii-diagram)
7. [Design decisions](#7-design-decisions)
8. [What this system is not](#8-what-this-system-is-not)

---

## 1. System overview

`workspace-exec` is a control-plane layer for file mutation.

It receives either:

- raw intent that can be converted into a batch envelope
- or a pre-built structured envelope

It then:

1. validates the batch
2. executes tickets in dependency order
3. routes each ticket through a fixed mutation pipeline
4. applies accepted changes to the workspace
5. records execution artifacts in audit storage

The system treats specialist output as untrusted until it passes the pipeline. No model output is written directly to the live workspace.

---

## 2. Core components

### Intake layer (`intake/`)

Optional entry path that converts natural-language intent into an execution envelope.

**Role**
- translate raw intent into structured tickets
- infer limited ticket metadata such as `allow_new_screen_ids`
- validate the generated envelope before execution

**Inputs**
- plain-text intent file

**Outputs**
- envelope JSON
- validation output
- intake audit artifacts

**Relevant scripts**
- `intake/generate_envelope.py`
- `intake/allow_new_screen_ids.py`
- `entrypoints/run_intake.sh`

If intake is skipped, the caller provides the envelope directly.

---

### Batch validator (`core/batch/validate.py`)

Validates the envelope before any ticket runs.

**Role**
- enforce envelope and ticket shape
- verify dependency references
- detect cycles
- compute deterministic execution order

**Input**
- envelope JSON

**Output**
- validation result JSON, including `exec_order`

If validation fails, batch execution does not begin.

---

### Execution orchestrator (`entrypoints/run_batch.sh`)

Controls batch-level execution.

**Role**
- validate the batch
- iterate tickets in topological order
- enrich each ticket with current workspace state
- invoke single-ticket execution
- persist batch audit artifacts

**Input**
- envelope JSON

**Output**
- per-run audit directory
- per-ticket execution artifacts

Execution is sequential. Parallel ticket execution is not supported.

---

### Ticket executor (`entrypoints/run_once.sh`)

Runs one ticket through the mutation pipeline.

**Role**
- enforce pre-pipeline gates such as ticket size and single-writer lock
- invoke the specialist
- pass specialist output through the pipeline
- coordinate staged apply and final atomic swap

**Input**
- enriched ticket JSON

**Output**
- success or failure exit status
- raw specialist output for audit
- applied mutation if all gates pass

This is the unit that owns per-ticket atomicity.

---

### Pipeline stages (`core/pipeline/`)

The mutation pipeline is a fixed sequence of gates:

1. `sanitize.py`
2. `allowlist.py`
3. `entity_guard.py`
4. `approve.py`
5. `apply.py`

Each stage receives the output of the previous stage. A failure at any stage stops the ticket.

---

### Provider adapter (`intake/adapters/invoke.py`)

Wraps model invocation behind a uniform interface.

**Role**
- send the enriched ticket to the configured provider
- return raw model text without transforming it

**Inputs**
- provider
- model
- system prompt file
- message file

**Output**
- raw specialist response text

The adapter does not validate the response. That starts in `sanitize.py`.

---

### Workspace (`workspace-example/bundles/`)

The mutable state managed by the system.

**Role**
- hold bundle files that represent the current working state
- serve as the only valid mutation target set
- provide source material for `current_objects` enrichment

**Contents**
- JSON bundles
- TypeScript files
- `_baseline.sha256` manifest for drift tracking

The governance layer is domain-agnostic. The workspace contents are not.

---

### Audit system (`audit/`)

Stores execution artifacts for traceability.

**Role**
- retain intake artifacts
- retain batch execution artifacts
- retain enriched tickets and raw specialist output

**Primary locations**
- `audit/helper_runs/`
- `audit/exec_runs/{TIMESTAMP}/`

Audit files are written as execution proceeds. They provide the record of what was requested, validated, generated, and applied.

---

## 3. Execution flow

The system executes in a fixed progression:

1. Accept raw intent or a pre-built envelope
2. If using intake, convert raw intent into an envelope
3. Validate the envelope
4. Compute ticket execution order from `depends_on`
5. For each ticket:
   - enrich with current workspace objects
   - invoke the specialist
   - run the pipeline
   - apply approved output through staged atomic write
   - record audit artifacts
6. Stop on first ticket failure

At the batch level, execution is deterministic and sequential.

At the ticket level, execution is fail-closed.

---

## 4. Pipeline breakdown

### sanitize

**What it checks**
- raw model output can be reduced to a single valid PATCH_MODE JSON object

**Why it exists**
- model output may include prose, fences, tags, or malformed JSON

**What it prevents**
- downstream stages operating on ambiguous or structurally invalid output

---

### allowlist

**What it checks**
- every target path is explicitly allowlisted
- path format is safe

**Why it exists**
- writable surface area must be explicit and bounded

**What it prevents**
- unauthorized paths
- path traversal
- writes outside the intended workspace

---

### entity_guard

**What it checks**
- selected structural changes require explicit ticket-level authorization

**Why it exists**
- some mutations have broader downstream impact than simple edits

**What it prevents**
- accidental introduction of guarded entities, such as unapproved new screen IDs

---

### approve

**What it checks**
- output against the active approval policy

**Why it exists**
- structural validity alone is not always sufficient for acceptance

**What it prevents**
- applying output that is technically valid but operationally suspect under the current policy

---

### apply

**What it checks**
- final patch shape is valid for the target file type
- resolved paths remain inside workspace boundaries

**Why it exists**
- the final write path must be safe and atomic

**What it prevents**
- partial writes
- invalid file replacement
- workspace corruption on failed mutation

---

## 5. Data flow

### Envelope

The envelope is the unit of batch execution.

It contains batch metadata and a list of tickets. It is validated once before execution begins and remains fixed for the life of the batch.

---

### Ticket

A ticket is the unit of mutation intent within a batch.

It describes:

- what change is being requested
- expected scope
- expected target paths
- risk level
- dependency edges
- any explicit structural permissions needed for execution

Before execution, each ticket is enriched with `current_objects` so the specialist can produce full-file replacement output.

---

### PATCH_MODE output

PATCH_MODE is the mutation format returned by the specialist.

It identifies:

- the ticket being processed
- the output mode
- the target bundle paths
- the replacement patch content
- any notes emitted by the specialist

For JSON targets, the patch is a full object replacement signaled by `_full_object: true`.

For TypeScript targets, the patch contains full file text.

---

### Bundle state

Bundle files are the mutable state the system manages.

They serve two roles:

- source state for ticket enrichment
- destination state for approved mutations

After successful apply, baseline information is recomputed so later drift checks can detect out-of-band change.

---

## 6. ASCII diagram

```text
[Intent]
   |
   v
[Intake] (optional)
   |
   v
[Envelope]
   |
   v
[Batch Validator]
   |
   v
[run_batch]
   |
   v
[Ticket Enrichment]
   |
   v
[run_once]
   |
   v
[invoke.py]
   |
   v
[sanitize]
   |
   v
[allowlist]
   |
   v
[entity_guard]
   |
   v
[approve]
   |
   v
[apply]
   |
   v
[Workspace]
   |
   v
[Audit]
```
More explicitly:
intake converts raw intent into an envelope
batch validation computes execution order
run_batch executes tickets one at a time
run_once owns single-ticket execution and staged apply
pipeline stages gate mutation before the workspace is touched
7. Design decisions
No direct tool execution
The specialist does not write files directly. It produces a structured mutation proposal that must pass the pipeline first.
This separates model generation from filesystem mutation and makes every applied change traceable.
Full-object patching
JSON mutation is full replacement, not merge.
This avoids partial-object corruption and forces the specialist to reason against current state before proposing a replacement.
Explicit allowlist
Writable paths are declared outside the model.
This keeps the write surface small, reviewable, and change-controlled.
Per-ticket atomicity
Each ticket is committed independently through staging and atomic swap.
This keeps each unit of mutation deterministic without requiring batch-wide rollback logic.
8. What this system is not
workspace-exec is not:
an agent framework
a scheduler
a memory system
a multi-agent orchestrator
a chatbot
a provider-specific runtime
It does not decide which agent should run, when work should run, or what the work should be. It only governs how approved mutations move from intent into workspace state.