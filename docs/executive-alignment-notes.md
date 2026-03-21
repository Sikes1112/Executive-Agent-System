# Executive Alignment Notes

## 1. Purpose

This document records how the new Executive Control Layer files align with the existing system files.

It exists to prevent:
- duplicate governance logic
- contradictory authority rules
- unclear layer boundaries
- drift between the control layer and execution layer

---

## 2. Files Compared

### New Executive Layer Files
- `docs/executive-control-layer.md`
- `contracts/executive/task-contract.schema.json`
- `contracts/executive/tool-policy-matrix.json`
- `contracts/executive/delegation-brief.schema.json`
- `docs/drift-model.md`
- `contracts/executive/approval-record.schema.json`
- `docs/executive-to-execution-handoff.md`

### Existing Files
- `agent-config/AGENT_CAPABILITIES.md`
- `agent-config/CONTINUITY_MODE.md`
- `docs/execution-layer.md`

---

## 3. Confirmed Alignments

### 3.1 Exec Authority
- Exec owns routing
- Exec owns approval
- Exec owns escalation
- Exec must not do specialist work

### 3.2 Specialist Boundaries
- Specialists are bounded
- Specialists do not self-approve
- Specialists do not own system memory/logs

### 3.3 Execution Layer Boundary
- `workspace-exec` is execution only
- `workspace-exec` is not the supervisory layer
- `workspace-exec` should only receive approved concrete mutations

### 3.4 Continuity
- Continuity is exec-owned support logic
- Continuity is not an independent authority layer

---

## 4. Potential Overlaps

List any places where old and new files describe the same thing in different ways.

### Example categories
- tool governance
- escalation rules
- specialist authority
- continuity ownership
- fail-closed behavior

---

## 5. Potential Contradictions

List any places where old and new files conflict.

### Check specifically
- Does any older file imply Exec can do specialist work?
- Does any older file allow specialists too much autonomy?
- Does any older file blur Exec vs `workspace-exec`?
- Does continuity appear both stateless and exec-owned in conflicting ways?

---

## 6. Gaps Still Not Implemented

These are design elements now documented but not yet proven in runtime.

### Expected current gaps
- task contract generation at runtime
- delegation brief generation at runtime
- drift review enforcement at runtime
- approval record generation at runtime
- enforced handoff gate into `workspace-exec`

---

## 7. Decisions

Record any decisions made during alignment.

### Examples
- `AGENT_CAPABILITIES.md` remains authority baseline for agent roles
- new executive contract files become canonical for control-loop structure
- `docs/execution-layer.md` remains lower-layer definition
- continuity remains exec-owned procedure, not independent control authority

---

## 8. Next Implementation Target

State the next runtime implementation surface to build after alignment.