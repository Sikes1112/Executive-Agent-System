# quickstart.md — Minimal Run

This guide runs `workspace-exec` end-to-end from raw intent → applied change.

The execution layer is provider-agnostic. This guide shows the default local path using Ollama. API-backed providers can be used by setting `ITERATION_PROVIDER` and related environment variables.

---

## 1. Prerequisites

- Python 3.9+ (stdlib only — no dependencies)
- Bash (macOS or Linux)

Choose a provider:

### Option A — Local (default)
- Ollama running locally: https://ollama.com

### Option B — API-backed
- Access to a supported provider
- Required API key configured via environment variables

---

## 2. Setup

```bash
git clone <repo-url>
cd workspace-exec
```
No installation step required.
Local setup (Ollama)
ollama serve
ollama pull qwen2.5-coder:14b-32k
API-backed setup
Example (Anthropic):
export ITERATION_PROVIDER=anthropic
export ITERATION_MODEL=<model-id>
export ANTHROPIC_API_KEY=<your-key>
Other providers can be added through the adapter layer.
3. Minimal Run
Step 1 — Create intent file
echo "add a settings screen" > input.txt
Step 2 — Run intake
bash entrypoints/run_intake.sh input.txt
Output includes:
ENVELOPE=/path/to/..._envelope.json
VALIDATION=/path/to/..._validation.json
EXIT_CODE=0
Step 3 — Run batch
bash entrypoints/run_batch.sh <envelope.json>
Use the ENVELOPE= path from step 2.
One-liner
eval $(bash entrypoints/run_intake.sh input.txt) && \
bash entrypoints/run_batch.sh "$ENVELOPE"
4. Expected Output
Intake artifacts
audit/helper_runs/
{TS}_input.txt
{TS}_envelope.json
{TS}_validation.json
Execution artifacts
audit/exec_runs/{TS}/
envelope.json
validation.json
t1_ticket.json
t1_iteration_output.txt
Workspace changes
workspace-example/bundles/
bundle files updated in place
_baseline.sha256 rewritten
Successful run
exits with code 0
prints EXEC_RUN_DIR=...
5. Common Issues
Ollama not running
Error: connection refused
Fix:
ollama serve
Model not pulled
Error: model not found
Fix:
ollama pull qwen2.5-coder:14b-32k
Lock file exists (exit 43)
core/locks/iteration_apply.lock
Fix:
rm -rf core/locks/iteration_apply.lock
Invalid PATCH_MODE output (exit 2)
Sanitize failed — model did not return valid JSON.
Check:
audit/exec_runs/{TS}/t1_iteration_output.txt
Ticket too large (exit 42)
Enriched ticket exceeded MAX_TICKET_CHARS.
Fix:
reduce scope per ticket
or increase limit:
export MAX_TICKET_CHARS=3000