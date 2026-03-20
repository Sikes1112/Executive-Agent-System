# workspace-exec

Execution-governance layer for multi-agent systems.

This repository provides the missing layer between agent output and real-world mutation: a deterministic, auditable, fail-closed execution pipeline.

workspace-exec is a control-plane execution layer. It does not generate output—it governs how output is validated, constrained, and applied.

Agents produce intent. This system ensures that intent becomes safe, deterministic state change.

The reasoning layer can be local, API-backed, or hybrid. workspace-exec governs execution, not inference.

## Why Governance

Unconstrained LLM output applied directly to a codebase or data model is unsafe. Even well-aligned models:

- produce structurally valid but semantically incorrect patches
- hallucinate file paths or entity IDs that do not exist
- apply wide-scope changes when narrow changes were intended
- produce non-deterministic behavior across retries

A governance layer interposes between the model output and the workspace to enforce:

- Fail-closed gates — every stage either passes explicitly or halts
- Path allowlisting — only declared bundle paths are writable
- Entity guards — structural entities (e.g., screen IDs) cannot be created without explicit operator permission
- Atomic apply — partial writes never reach the live workspace
- Auditability — every input, decision, and output is logged

Without governance, system reliability depends on model quality.

With governance, correctness becomes a structural property of the system itself.

## What This Is

A deterministic pipeline that:

- Accepts natural language intent via the Helper layer
- Converts it to a validated ticket batch envelope
- Routes tickets (respecting dependency order) to an Iteration Specialist
- Passes each specialist response through a sequential pipeline (`sanitize → allowlist → entity_guard → approve → apply`)
- Writes mutations atomically to the bundle workspace
- Maintains a SHA256 baseline for drift detection
- Logs all artifacts to an audit trail

The bundle workspace (`workspace-example/bundles/`) is a domain-specific structured data layer — JSON definitions of domain model, API contracts, UI spec, test vectors, and generated code skeleton.

The governance layer is domain-agnostic; the bundles are the product layer.

## Where This Fits

This system is not an agent framework. It sits beneath your existing agents and orchestrator.

Your upstream system may use local models, cloud/API-backed models, or a mix of both.

Your system:
- generates intent (natural language or structured tickets)

workspace-exec:
- validates
- constrains
- executes
- audits

Flow:

```text
Your Orchestrator / Agents
↓
workspace-exec (this repository)
↓
Validated, auditable mutations to your workspace
You keep your agents. This replaces unsafe execution.
```
Quickstart
Default examples use Ollama for local setup simplicity. The execution model is provider-agnostic; API-backed providers can be used through configuration.
Run a full end-to-end execution in three steps:
echo "add a settings screen" >/tmp/intent.txt
WORKSPACE_ROOT="$(pwd)" entrypoints/run_intake.sh /tmp/intent.txt
WORKSPACE_ROOT="$(pwd)" ITERATION_PROVIDER=ollama entrypoints/run_batch.sh <ENVELOPE_PATH>
core/drift.sh
See docs/quickstart.md for full instructions.
Repository Layout
workspace-exec/
├── agent-config/
├── audit/
├── contracts/
├── core/
├── entrypoints/
├── intake/
├── workspace-example/
└── AGENTS.md

Entry Points
entrypoints/run_intake.sh <input.txt> — Convert natural language intent to ticket batch envelope
entrypoints/run_batch.sh <envelope.json> — Execute all tickets in a validated envelope
entrypoints/run_once.sh <ticket.json> — Execute a single ticket
core/drift.sh — Check for unauthorized bundle mutations
Configuration (at a glance)
WORKSPACE_ROOT
AUDIT_ROOT
ITERATION_PROVIDER
ITERATION_MODEL
SYSTEM_PROMPT_PATH
APPROVAL_POLICY

Documentation
docs/architecture.md
docs/quickstart.md
docs/adoption.md
docs/contracts.md
docs/configuration.md
docs/roadmap.md
docs/error-model.md  
docs/integration-example.md  
docs/exec-layer.md 

What This Is Not
This repository is not:
a multi-agent framework
a scheduler
a memory system
a chatbot
tied to any specific model runtime or deployment style
It is a governed execution layer.

Terminology
Bundle — versioned JSON file
Envelope — batch of tickets
Ticket — unit of work
PATCH_MODE — mutation format
Exec — control plane
Iteration Specialist — model or execution backend that produces patch output
Helper — NL → envelope
Baseline — drift reference