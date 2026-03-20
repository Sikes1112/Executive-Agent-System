# configuration.md — Configuration

All configuration is provided via environment variables.

There are no config files. Defaults are applied at runtime by the entrypoint scripts.

---

## Variables

### WORKSPACE_ROOT

**Default:** auto-resolved (repo root)

Root directory for all file operations.

Override only if:
- running scripts from outside the repo
- embedding `workspace-exec` in another system

---

### AUDIT_ROOT

**Default:** `$WORKSPACE_ROOT/audit`

Directory where all audit artifacts are written:

- `helper_runs/`
- `exec_runs/`
- `helper_audit/`

Override to redirect audit output to another location or volume.

---

### ITERATION_PROVIDER

**Default:** `ollama`  
**Options:** `ollama`, `anthropic`

Selects the model provider used by the adapter.

- `ollama` → local model via Ollama
- `anthropic` → Anthropic API (requires `ANTHROPIC_API_KEY`)

---

### ITERATION_MODEL

**Default:** `qwen2.5-coder:14b-32k`

Model identifier passed to the provider.

Examples:
- Ollama: `qwen2.5-coder:14b-32k`
- Anthropic: `claude-3-5-sonnet-latest`

The model must reliably produce strict JSON output.

---

### SYSTEM_PROMPT_PATH

**Default:**  
`$WORKSPACE_ROOT/core/prompts/iteration_specialist.md`

Path to the system prompt passed to the model.

Override to:
- experiment with prompt variants
- inject domain-specific instructions

---

### APPROVAL_POLICY

**Default:** `P1`  
**Options:** `P0`, `P1`, `P2`, `P3`

Controls the approval stage of the pipeline.

| Policy | Behavior |
|---|---|
| P0 | Always accept (testing only) |
| P1 | Accept unless flagged (default) |
| P2 | Always reject |
| P3 | Always reject |

> Note: True dry-run output is not yet implemented; see roadmap.

Additional behavior:

- **format_drift**: model output contains non-JSON text
- **hard notes**: notes prefixed with `LIMIT_EXCEEDED`, `REWRITE_REQUIRES_APPROVAL`, `MISSING_`, or `UNMET:`

Use:
- `P1` for normal operation
- `P3` for safe dry-run validation

---

### MAX_TICKET_CHARS

**Default:** `1400`  
**Exit on breach:** `42`

Maximum size of the enriched ticket JSON passed to the model.

Purpose:
- prevent oversized context payloads
- enforce predictable model input size

Increase if:
- tickets include large `current_objects`

> Note: When invoked via `run_batch.sh`, the effective limit is 6000.

---

### OLLAMA_BASE_URL

**Default:** `http://127.0.0.1:11434`  
**Applies when:** `ITERATION_PROVIDER=ollama`

Base URL for the Ollama API.

Override if:
- running Ollama on a different port
- using a remote Ollama instance

---

### ANTHROPIC_API_KEY

**Default:** none  
**Required when:** `ITERATION_PROVIDER=anthropic`

API key for Anthropic.

Not used when provider is `ollama`.

---

## Example `.env`

Load with:

```bash
export $(cat .env | xargs)
```
Local (Ollama default)
ITERATION_PROVIDER=ollama
ITERATION_MODEL=qwen2.5-coder:14b-32k
OLLAMA_BASE_URL=http://127.0.0.1:11434
APPROVAL_POLICY=P1
MAX_TICKET_CHARS=1400
Anthropic
ITERATION_PROVIDER=anthropic
ITERATION_MODEL=claude-3-5-sonnet-latest
ANTHROPIC_API_KEY=sk-ant-...
APPROVAL_POLICY=P1
MAX_TICKET_CHARS=1400
Dry-run (no writes)
ITERATION_PROVIDER=ollama
ITERATION_MODEL=qwen2.5-coder:14b-32k
APPROVAL_POLICY=P3
Minimal recommended configs
Local development
No configuration required. Defaults apply.
CI / controlled runs
export ITERATION_PROVIDER=ollama
export ITERATION_MODEL=qwen2.5-coder:14b-32k
export APPROVAL_POLICY=P1
export AUDIT_ROOT=/var/log/workspace-exec
Anthropic backend
export ITERATION_PROVIDER=anthropic
export ITERATION_MODEL=claude-3-5-sonnet-latest
export ANTHROPIC_API_KEY=sk-ant-...
Testing / prompt development
export APPROVAL_POLICY=P3