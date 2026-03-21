# Operator Quickstart

This quickstart is for running the current repository implementation.

## 1. Prerequisites

- Python 3.9+
- Bash (macOS/Linux)
- One supported provider configured for the target domain runs

Provider defaults:
- `ITERATION_PROVIDER=ollama`
- `ITERATION_MODEL=qwen2.5-coder:14b-32k`

## 2. Clone and Enter Repo

```bash
git clone <repo-url>
cd workspace-exec
```

## 3. First Run: Intake -> Batch

```bash
echo "add a settings screen" > input.txt
bash entrypoints/run_intake.sh input.txt
# copy ENVELOPE=... from output
bash entrypoints/run_batch.sh <ENVELOPE_PATH>
```

Expected:
- validation passes
- an `audit/exec_runs/<timestamp>/` directory is created
- for mutation tickets, apply may occur if all gates pass

## 4. First Run: Direct Envelope

If you already have a valid envelope:

```bash
bash entrypoints/run_batch.sh /path/to/envelope.json
```

Use explicit `ticket.domain` when domain routing must be deterministic.

## 5. Domain Notes During Runs

- `iteration`: full bounded mutation pipeline
- `outreach`: sanitize + artifact persistence + stop
- `reputationops`: sanitize + artifact persistence + stop

Non-mutation domain success does not imply workspace apply.

## 6. Where To Inspect Outputs

- Intake artifacts: `audit/helper_runs/`
- Execution artifacts: `audit/exec_runs/<timestamp>/`
- Domain output logs: `<ticket_id>_<domain>_output.txt`

For non-mutation domains, look for:
- `.normalized.<domain>.json`
- `.metadata.<domain>.json`

## 7. Common Operational Issues

- Exit `42`: enriched ticket exceeded size limit
- Exit `43`: lock already held
- Exit `44`: domain adapter resolution failure
- Exit `45`: unsupported non-mutation post-sanitize handling
- Exit `2`/`3`/`10`: stage or policy failures (see error model)

See [error-model.md](error-model.md) for full table.

