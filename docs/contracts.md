# contracts.md — Integration Reference

This document defines the integration contracts exposed by `workspace-exec`.

It covers the interfaces between:

- intake and batch execution
- batch execution and tickets
- `workspace-exec` and the mutation specialist
- pipeline stages and the live workspace

This is an implementation reference. It documents current behavior only.

## Contents

1. [Intake input contract](#1-intake-input-contract)
2. [Envelope schema](#2-envelope-schema)
3. [Ticket contract](#3-ticket-contract)
4. [PATCH_MODE contract](#4-patch_mode-contract)
5. [Provider adapter contract](#5-provider-adapter-contract)
6. [Pipeline stage contracts](#6-pipeline-stage-contracts)
7. [Workspace layout contract](#7-workspace-layout-contract)
8. [Execution contract](#8-execution-contract)
9. [Common integration mistakes](#9-common-integration-mistakes)
10. [Current implementation limits](#10-current-implementation-limits)

---

## 1. Intake input contract

**Entrypoint:** `entrypoints/run_intake.sh`

### Invocation

```bash
bash entrypoints/run_intake.sh <input_file>
Required input
Item	Requirement
<input_file>	Path to a plain-text UTF-8 file
File contents	Free-form natural-language intent
File existence	Required. Missing file exits with code 2
Output
run_intake.sh writes shell-assignable lines to stdout:
ENVELOPE=/path/to/envelope.json
VALIDATION=/path/to/validation.json
EXIT_CODE=0
It also writes both artifacts under:
audit/helper_runs/
using a timestamp-prefixed filename convention.
Processing sequence
Copy raw input to audit/helper_runs/{TIMESTAMP}_input.txt
Run intake/generate_envelope.py to produce an envelope
Run intake/allow_new_screen_ids.py to infer allow_new_screen_ids from recognized intent patterns
Run core/batch/validate.py against the resulting envelope
If validation fails, intake exits with code 2.
Notes
Input is expected to be UTF-8.
Intake is pattern-based. It does not call an LLM.
If input is not recognized, intake falls back to a generic single-ticket envelope.
Intake is optional. Integrations may bypass it and submit an envelope directly to entrypoints/run_batch.sh.
2. Envelope schema
Used by: entrypoints/run_batch.sh, core/batch/validate.py
Top-level shape
{
  "batch_id": "<string>",
  "origin_input_hash": "<string>",
  "created_at": "<string>",
  "tickets": [<ticket>, ...]
}
Field definitions
Field	Type	Required	Constraints
batch_id	string	yes	Non-empty. Convention: batch-<12-char-hex>
origin_input_hash	string	yes	Minimum 32 characters. Typically SHA-256 of raw input
created_at	string	yes	Non-empty ISO 8601 timestamp
tickets	array	yes	1 to 20 items
Batch-level constraints
MAX_TICKETS_PER_BATCH = 20
ticket_id values must be unique within the batch
depends_on must form a DAG
every depends_on reference must resolve to a ticket in the same batch
forward references are allowed
validation failure rejects the entire batch before execution
Example
{
  "batch_id": "batch-a3f9c2e81b4d",
  "origin_input_hash": "e3b0c44298fc1c149afb...",
  "created_at": "2026-03-18T00:00:00Z",
  "tickets": []
}
3. Ticket contract
Shape
{
  "ticket_id": "<string>",
  "intent_summary": "<string>",
  "patch_scope": "narrow | medium | wide",
  "target_paths": ["<bundle-relative-path>", "..."],
  "risk_level": "low | medium | high",
  "depends_on": ["<ticket_id>", "..."],
  "allow_new_screen_ids": ["<screen_id>", "..."]
}
Required fields
Field	Required
ticket_id	yes
intent_summary	yes
patch_scope	yes
target_paths	yes
risk_level	yes
depends_on	yes
allow_new_screen_ids	no
depends_on must be present even when empty:
"depends_on": []
Field semantics
ticket_id
Unique identifier within the batch. Must be non-empty.
intent_summary
Short description of the requested mutation.
patch_scope
Declares expected mutation breadth for the specialist.
Value	Meaning
narrow	One or two fields in one bundle
medium	Multiple fields or one full bundle object
wide	Multiple bundles or coordinated change
This field is advisory. It does not directly gate execution.
target_paths
Relative bundle paths the ticket is expected to affect.
Example:
["bundles/ui_spec/screens.json", "bundles/ui_spec/navigation.json"]
Constraints:
relative path only
no leading /
no ..
target_paths is advisory. Enforcement happens later through the allowlist gate, not during ticket validation.
risk_level
Informational only. Used for validation output and audit surfacing.
Allowed values:
low
medium
high
This field does not block execution.
depends_on
List of ticket IDs that must complete before this ticket runs.
Rules:
all referenced IDs must exist in the same batch
cycles fail batch validation
execution order is computed topologically from this graph
allow_new_screen_ids
Optional permission list for new screen IDs introduced through bundles/ui_spec/screens.json.
Example:
"allow_new_screen_ids": ["settings_screen", "profile_screen"]
If a ticket introduces new screen IDs and those IDs are not listed here, entity_guard.py rejects the mutation.
Invalid ticket conditions
Condition	Enforced by	Effect
Missing required field	core/batch/validate.py	Batch fails
Empty ticket_id	core/batch/validate.py	Batch fails
Duplicate ticket_id	core/batch/validate.py	Batch fails
Invalid patch_scope	core/batch/validate.py	Batch fails
Invalid risk_level	core/batch/validate.py	Batch fails
Unknown depends_on target	core/batch/validate.py	Batch fails
Dependency cycle	core/batch/validate.py	Batch fails
Enriched ticket exceeds MAX_TICKET_CHARS	run_once.sh	Ticket exits 42; batch stops
4. PATCH_MODE contract
This is the contract between workspace-exec and the mutation specialist.
The specialist must emit exactly one JSON object and nothing else.
no prose
no markdown fences
no wrapper commentary
Required output shape
{
  "ticket": "<ticket_id>",
  "mode": "iteration",
  "output": "PATCH_MODE",
  "bundles": [
    {
      "path": "<canonical-bundle-path>",
      "patch": {}
    }
  ],
  "notes": ["<string>", "..."]
}
Top-level rules
Field	Type	Required	Constraints
ticket	string	yes	Must match the current ticket_id
mode	string	yes	Must equal "iteration"
output	string	yes	Must equal "PATCH_MODE"
bundles	array	yes	One or more bundle patch entries
notes	array[string]	yes	May be empty
Bundle entry shape
{
  "path": "bundles/domain/domain_model.json",
  "patch": {}
}
Field	Required	Constraints
path	yes	Exact match against contracts/allowlists/canonical_pack_paths.txt
patch	yes	Object. Interpretation depends on target file type
JSON target contract
For .json targets, the patch must be a complete replacement object and must include:
"_full_object": true
Example:
{
  "path": "bundles/domain/domain_model.json",
  "patch": {
    "_full_object": true,
    "entities": [],
    "relationships": []
  }
}
Rules:
_full_object: true is required
the patch object replaces the entire file
_full_object is written into the output file
writes are atomic
There is no partial-object merge behavior.
TypeScript target contract
For .ts targets:
{
  "path": "bundles/code_skeleton/types.ts",
  "patch": {
    "content": "// full TypeScript source\nexport type Foo = {...}"
  }
}
Rules:
patch.content must be a string
the file is fully replaced
writes are atomic
Path rules
Paths must:
be relative
not start with /
not contain ..
not contain backslashes
resolve inside WORKSPACE_ROOT
exist in the canonical allowlist
Rejection conditions
Stage	Condition	Exit
sanitize.py	No valid JSON object found	2
sanitize.py	Missing required key	2
sanitize.py	mode != "iteration"	2
sanitize.py	output != "PATCH_MODE"	2
sanitize.py	Invalid bundle entry	2
allowlist.py	Path not in allowlist	2
allowlist.py	Absolute path	2
allowlist.py	Traversal path	2
allowlist.py	Backslash in path	2
entity_guard.py	Unauthorized new screen ID	10
entity_guard.py	screens.json missing when needed	3
approve.py	Policy rejects	2 or 3
apply.py	Missing _full_object: true for .json	2
apply.py	Missing content string for .ts	2
apply.py	Path escapes workspace	2
apply.py	Unsupported file extension	2
5. Provider adapter contract
Script: intake/adapters/invoke.py
Invocation
python3 intake/adapters/invoke.py \
  --provider <ollama|anthropic> \
  --model <model-name> \
  --system-prompt <path-to-system-prompt.md> \
  --message <path-to-ticket.json>
Inputs
Argument	Required	Notes
--provider	yes	ollama or anthropic
--model	yes	Provider-specific model name
--system-prompt	yes	Path to system prompt text
--message	yes	Path to ticket JSON
Environment variables
Variable	Required for	Default
OLLAMA_BASE_URL	ollama	http://127.0.0.1:11434
ANTHROPIC_API_KEY	anthropic	none
Ollama request shape
{
  "model": "<model>",
  "stream": false,
  "messages": [
    {"role": "system", "content": "<system-prompt-text>"},
    {"role": "user", "content": "<ticket-json-text>"}
  ]
}
Sent to:
POST {OLLAMA_BASE_URL}/api/chat
Anthropic request shape
{
  "model": "<model>",
  "max_tokens": 4096,
  "system": "<system-prompt-text>",
  "messages": [
    {"role": "user", "content": "<ticket-json-text>"}
  ]
}
Sent to:
POST https://api.anthropic.com/v1/messages
Response handling
The adapter writes raw model text to stdout.
It does not normalize, validate, or repair model output. That is the job of core/pipeline/sanitize.py.
Extraction paths:
Provider	Response extraction path
Ollama	response_body["message"]["content"]
Anthropic	response_body["content"][0]["text"]
If request or extraction fails, the adapter exits non-zero and run_once.sh treats that as a pipeline failure.
6. Pipeline stage contracts
The per-ticket pipeline is executed sequentially by entrypoints/run_once.sh.
Any stage failure stops the current ticket. The batch then stops.
Stage 1: Sanitize
Script: core/pipeline/sanitize.py
Input
raw model text from stdin or file argument
Behavior
strip markdown fences
strip wrapper tags such as <final> and </finally>
extract the first JSON object using brace-depth matching
attempt double-brace repair if parse fails
validate the result against the PATCH_MODE shape
Success output
Normalized JSON written to stdout.
Failure output
Structured error JSON written to stdout, with exit code 2.
Failure classes
Condition	Error code
No JSON object found	no_json
JSON parse failure after repair	json_parse
Missing required top-level key	missing_key
Invalid mode	invalid_mode
Invalid output	invalid_output
bundles is not an array	invalid_bundles
Bundle entry missing path or patch	invalid_bundle_entry
JSON patch missing _full_object: true	missing_full_object
Exit codes:
0 = valid
2 = invalid
Stage 2: Allowlist
Script: core/pipeline/allowlist.py
Input
normalized PATCH_MODE JSON
contracts/allowlists/canonical_pack_paths.txt
Behavior
For each bundle path, verify:
no leading /
no ..
no backslash
exact match in allowlist
Output
Pass or fail message to stderr.
Exit codes
0 = pass
2 = fail
Stage 3: Entity guard
Script: core/pipeline/entity_guard.py
Input
normalized PATCH_MODE JSON
current ticket JSON
Behavior
If the mutation does not target bundles/ui_spec/screens.json, the guard passes as not applicable.
If it does:
load current IDs from live screens.json
extract IDs from the patch
compute newly introduced IDs
compare new IDs to ticket.allow_new_screen_ids
reject any unapproved new ID
Exit codes
Condition	Exit
Pass	0
Unauthorized new screen IDs	10
Live screens.json missing	3
Stage 4: Approve
Script: core/pipeline/approve.py
Inputs
APPROVAL_POLICY
raw model text
normalized PATCH_MODE JSON
Supported policies
Policy	Behavior	Exit
P0	Always accept	0
P1	Accept, optionally flag	0
P2	Always reject	2
P3	Always reject	3
P1 flags
Flag	Condition
format_drift	Raw output included fences or leading non-JSON text
notes_nonempty	notes array is non-empty
hard_notes_present	A note begins with LIMIT_EXCEEDED, REWRITE_REQUIRES_APPROVAL, MISSING_, or UNMET:
Under P1, any flag changes the decision from ACCEPT to ACCEPT_FLAG. Exit code remains 0.
Example output
{
  "policy": "P1",
  "decision": "ACCEPT_FLAG",
  "flags": {
    "format_drift": false,
    "notes_nonempty": true,
    "hard_notes_present": false
  },
  "notes": ["some note from specialist"]
}
Stage 5: Apply
Script: core/pipeline/apply.py
Input
normalized PATCH_MODE JSON
WORKSPACE_ROOT
allowlist path
Behavior
For each bundle entry:
validate path safety
for .json, require _full_object: true and write the full object
for .ts, require patch.content and write the full file
reject all other extensions
apply.py writes into a staging copy, not directly into the live workspace.
Exit codes
0 = success
2 = failure
Failure cases
Condition
Path escapes workspace
Missing _full_object: true for JSON
Missing content string for TypeScript
Unsupported extension
Write failure
7. Workspace layout contract
The current implementation expects the following repository layout.
<WORKSPACE_ROOT>/
├── contracts/
│   ├── allowlists/
│   │   └── canonical_pack_paths.txt
│   ├── schemas/
│   │   └── ui_spec_screens.schema.json
│   └── delegation/
│       └── DELEGATION_ENVELOPES.md
│
├── core/
│   ├── pipeline/
│   │   ├── sanitize.py
│   │   ├── allowlist.py
│   │   ├── entity_guard.py
│   │   ├── approve.py
│   │   └── apply.py
│   ├── batch/
│   │   └── validate.py
│   ├── prompts/
│   │   └── iteration_specialist.md
│   ├── baseline.sh
│   ├── drift.sh
│   └── locks/
│
├── entrypoints/
│   ├── run_batch.sh
│   ├── run_once.sh
│   └── run_intake.sh
│
├── intake/
│   ├── generate_envelope.py
│   ├── allow_new_screen_ids.py
│   ├── oc_intent.sh
│   └── adapters/
│       └── invoke.py
│
├── workspace-example/
│   └── bundles/
│       ├── _baseline.sha256
│       ├── domain/
│       ├── contracts/
│       ├── ui_spec/
│       ├── tests/
│       └── code_skeleton/
│
└── audit/
    ├── helper_runs/
    └── exec_runs/
Required vs optional
Path	Required	Notes
contracts/allowlists/canonical_pack_paths.txt	yes	Required allowlist
core/pipeline/*.py	yes	All five stages required
core/batch/validate.py	yes	Required
core/prompts/iteration_specialist.md	yes	Unless overridden
intake/adapters/invoke.py	yes	Required
entrypoints/run_batch.sh	yes	Required
entrypoints/run_once.sh	yes	Required
workspace-example/bundles/ui_spec/screens.json	yes	Required by entity_guard.py
Other target bundle files	yes	Missing file may cause apply failure
workspace-example/bundles/_baseline.sha256	no	Created by baseline.sh --write
audit/helper_runs/	no	Created at runtime
audit/exec_runs/	no	Created at runtime
core/locks/	no	Created at runtime
Workspace path note
The live bundle path is currently hardcoded to workspace-example/bundles/.
To target a different live bundle root, the current implementation requires code changes in at least:
entrypoints/run_once.sh
core/pipeline/entity_guard.py
There is no environment variable for this today.
8. Execution contract
Entrypoint: entrypoints/run_batch.sh
Invocation
bash entrypoints/run_batch.sh <envelope.json>
Required input
Item	Requirement
<envelope.json>	Must exist
Envelope shape	Must pass core/batch/validate.py
Lock state	core/locks/iteration_apply.lock/ must not already exist
If the envelope is missing or invalid, execution stops before any ticket runs.
Ordering guarantees
tickets run in topological order derived from depends_on
execution is strictly sequential
no parallel ticket execution
a ticket is not started until all dependencies complete successfully
Per-ticket atomicity
Each ticket commits independently.
Flow:
copy live bundles into a staging directory
apply writes into staging only
recompute baseline in staging
atomically swap staging into live position
discard staging on pre-swap failure
If any step before the final swap fails, the live workspace remains unchanged for that ticket.
Batch-level behavior
There is no cross-ticket rollback.
If ticket t3 fails after t1 and t2 have committed, those earlier changes remain live.
Failure behavior
Condition	Behavior
Envelope validation fails	Entire batch aborts before execution
Lock already held	Batch aborts immediately
Any ticket exits non-zero	Batch stops immediately
Enriched ticket exceeds MAX_TICKET_CHARS	Ticket exits 42; batch stops
Specialist returns invalid output	Pipeline rejects; batch stops
There is no built-in retry.
Audit artifacts
For each batch run:
audit/exec_runs/{TIMESTAMP}/
├── envelope.json
├── validation.json
├── {ticket_id}_ticket.json
└── {ticket_id}_iteration_output.txt
{ticket_id}_ticket.json is the enriched ticket passed to the specialist, including injected current_objects.
Single-writer lock
run_once.sh acquires:
core/locks/iteration_apply.lock/
using mkdir, relying on POSIX directory creation atomicity.
If the lock already exists, execution exits with 43.
If the process is killed and the lock remains, it must be removed manually:
rmdir core/locks/iteration_apply.lock
Environment variables
Variable	Default	Effect
WORKSPACE_ROOT	repo root	Base path for file operations
AUDIT_ROOT	$WORKSPACE_ROOT/audit	Audit artifact root
ITERATION_PROVIDER	ollama	Provider passed to adapter
ITERATION_MODEL	qwen2.5-coder:14b-32k	Model passed to adapter
APPROVAL_POLICY	P1	Approval behavior
SYSTEM_PROMPT_PATH	core/prompts/iteration_specialist.md	Specialist system prompt
MAX_TICKET_CHARS	1400	Character limit for enriched ticket JSON
ANTHROPIC_API_KEY	unset	Required for Anthropic
OLLAMA_BASE_URL	http://127.0.0.1:11434	Ollama base URL
9. Common integration mistakes
Omitting _full_object: true for JSON patches
JSON targets are full replacements. Without _full_object: true, apply fails.
Producing partial JSON objects
There is no merge behavior. The supplied object becomes the entire file.
Using paths not present in the allowlist
Allowlist checks are exact string matches.
Treating target_paths as enforcement
target_paths is advisory. The actual gate is the canonical path allowlist.
Creating dependency cycles
Any cycle fails the entire batch before execution starts.
Patching screens.json without allow_new_screen_ids
New screen IDs must be declared explicitly or entity_guard.py rejects the change.
Assuming batch-wide atomicity
Atomicity is per ticket, not per batch.
Relying on intake for structured integrations
Intake is pattern-based convenience logic. Programmatic integrations should usually generate envelopes directly.
Running with APPROVAL_POLICY=P2 or P3 unintentionally
Both policies reject all mutations.
Ignoring injected current_objects
The specialist is expected to preserve existing state when full-file replacements are required.
10. Current implementation limits
These are current implementation constraints, not general design principles.
Item	Detail
Hardcoded live bundle root	The implementation assumes workspace-example/bundles/
Intake is regex-based	Intake uses pattern matching, not an LLM
No cross-ticket rollback	Earlier committed tickets remain applied if a later ticket fails
Stale lock requires manual cleanup	Crashes or forced termination can leave the lock behind
_full_object is persisted	The key is written into JSON bundle files
MAX_TICKET_CHARS applies to the enriched ticket	Injected current_objects can push an otherwise small ticket over the limit
Entity guard is limited to screen IDs	Other entity types do not have equivalent explicit-allow guards
No runtime schema enforcement for bundles	Schemas are not enforced after apply
Anthropic max_tokens is fixed	Not currently configurable through environment
Audit files are mutable	Audit outputs are plain files without integrity protection
Intake helper only adds one new screen ID per ticket	Multi-screen creation usually requires hand-authored envelopes
Summary
To integrate with workspace-exec, a host system must be able to:
submit either raw intent to intake or a valid batch envelope directly
produce tickets that satisfy the ticket contract
supply or accept a mutation specialist that returns valid PATCH_MODE output
operate within the canonical path allowlist and current workspace layout
tolerate per-ticket commits without batch-wide rollback
Anything outside those contracts is not guaranteed by the current implementation.