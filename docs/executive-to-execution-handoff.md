# Executive to Execution Handoff

## 1. Purpose

This document defines the boundary between the Executive Control Layer and the Execution Layer.

The Executive Control Layer decides:
- what the task actually is
- who should perform it
- what tools are allowed
- whether the result stayed in scope
- whether the work is approved

The Execution Layer (`workspace-exec`) does not make those decisions.

It only receives an approved execution package and applies validated workspace mutations safely.

---

## 2. Core Boundary

The system boundary is:

User → Exec → Specialist → Exec Review → workspace-exec

Exec is the approval authority.  
workspace-exec is the mutation authority.

Neither may absorb the other’s role.

---

## 3. Required Upstream Artifacts Before Execution

No work may be handed to `workspace-exec` unless all of the following exist:

1. **Task Contract**
   - validated task definition
   - objective, deliverable, constraints, non-goals, acceptance criteria, risk

2. **Delegation Brief**
   - bounded specialist assignment
   - approved tool scope
   - required output format

3. **Approval Record**
   - explicit Exec decision
   - drift review complete
   - tool compliance recorded
   - next action recorded

If any of these are missing, handoff is invalid.

---

## 4. Handoff Rule

`workspace-exec` may only receive work if Exec decision = `approve`.

If Exec decision is:
- `revise`
- `reroute`
- `split`
- `escalate`

then no execution handoff may occur.

This is a hard fail-closed rule.

---

## 5. Execution Package

When Exec approves work, it must emit a structured execution package for `workspace-exec`.

That package must be:

- concrete
- bounded
- mutation-ready
- contract-valid
- traceable to the approved task

It must not contain vague intent, open-ended reasoning, or unresolved ambiguity.

---

## 6. Minimum Traceability Requirements

Every execution package must be traceable back to:

- `task_id`
- `delegation_id`
- `approval_id`
- assigned specialist
- approved path scope
- approved mutation scope

This ensures every workspace mutation can be tied back to an explicit Exec decision.

---

## 7. Fail-Closed Conditions

Exec must block handoff if:

- intent was not fully validated
- delegation was incomplete
- tool scope was exceeded
- drift was detected and unresolved
- approval record is missing
- mutation scope is ambiguous

`workspace-exec` must reject execution if the upstream handoff package is incomplete or invalid.

---

## 8. Role Separation

### Exec
- defines the task
- approves the task
- approves the tool scope
- approves the specialist result
- emits the execution handoff

### Specialist
- performs bounded work only
- cannot self-approve
- cannot hand work directly to `workspace-exec`

### workspace-exec
- validates execution contracts
- stages and applies mutation atomically
- records audit artifacts
- never decides what the task should have been

---

## 9. Core Principle

The Executive Control Layer governs correctness before execution.

The Execution Layer governs safety during execution.

The system is reliable only if both layers remain separate.
