# Configuration

All runtime configuration is environment-variable based.

## Core Paths

### `WORKSPACE_ROOT`
- Default: repo root resolved by entrypoint
- Purpose: base path for runtime operations

### `AUDIT_ROOT`
- Default: `$WORKSPACE_ROOT/audit`
- Purpose: helper and execution artifact root

## Provider and Model Selection

Provider/model can be set globally or per domain.

Global fallbacks:
- `ITERATION_PROVIDER` (default: `ollama`)
- `ITERATION_MODEL` (default: `qwen2.5-coder:14b-32k`)

Per-domain overrides (checked first for that domain):
- `OUTREACH_PROVIDER`, `OUTREACH_MODEL`
- `REPUTATIONOPS_PROVIDER`, `REPUTATIONOPS_MODEL`
- `ITERATION_PROVIDER`, `ITERATION_MODEL` (also domain-specific for iteration)

Resolution behavior in `run_once.sh`:
1. `<DOMAIN>_PROVIDER` / `<DOMAIN>_MODEL`
2. `ITERATION_PROVIDER` / `ITERATION_MODEL`
3. built-in defaults

## Prompt Path

### `SYSTEM_PROMPT_PATH`
- Default: domain adapter prompt path from `core/domain_adapters/registry.json`
- Override behavior: if set, it overrides adapter prompt path for all domains for that run

## Approval and Safety

### `APPROVAL_POLICY`
- Default: `P1`
- Supported: `P0`, `P1`, `P2`, `P3`

### `MAX_TICKET_CHARS`
- Default in `run_once.sh`: `1400`
- `run_batch.sh` currently invokes `run_once.sh` with `MAX_TICKET_CHARS=6000`

## Provider-Specific Variables

### Ollama
- `OLLAMA_BASE_URL` (default: `http://127.0.0.1:11434`)

### Anthropic
- `ANTHROPIC_API_KEY` (required when provider is `anthropic`)

## Minimal Examples

Local defaults:
```bash
export ITERATION_PROVIDER=ollama
export ITERATION_MODEL=qwen2.5-coder:14b-32k
```

Outreach using Anthropic while iteration uses Ollama:
```bash
export ITERATION_PROVIDER=ollama
export ITERATION_MODEL=qwen2.5-coder:14b-32k
export OUTREACH_PROVIDER=anthropic
export OUTREACH_MODEL=claude-3-5-sonnet-latest
export ANTHROPIC_API_KEY=<key>
```

