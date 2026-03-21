# Exec Manual Runtime

## 1. Purpose

This document defines the manual runtime procedure for Exec before full automation exists.

It is used to test whether the Executive Control Layer works in practice using a human operator plus an LLM.

The goal is not speed.
The goal is to prove that the control loop is coherent, repeatable, and enforceable.

---

## 2. Inputs

The runtime begins with:

- raw user request
- relevant recent context if needed
- current project/task state if needed

---

## 3. Manual Runtime Loop

### Step 1 — Intake Classification
Determine:

- Is this chat or structured work?
- Does it require a specialist?
- Is the request clear enough to bound?

If chat-only:
- answer directly
- do not create a task contract

If structured work:
- continue

---

### Step 2 — Task Contract Generation
Create a task contract matching:

`contracts/executive/task-contract.schema.json`

The task contract must include:
- objective
- deliverable
- constraints
- non-goals
- acceptance criteria
- risk level
- assigned specialist
- task-level tool policy

If critical fields cannot be bounded:
- narrow the task, or
- ask one targeted clarification

---

### Step 3 — Delegation Brief Generation
Create a delegation brief matching:

`contracts/executive/delegation-brief.schema.json`

The brief must be:
- bounded
- explicit
- assigned to exactly one specialist
- tool-scoped
- output-scoped

---

### Step 4 — Specialist Output Review
Receive specialist output and evaluate it against:

- task contract
- delegation brief
- tool policy
- drift model

Use:

`docs/drift-model.md`

Check:
- goal drift
- scope drift
- tool drift
- format drift
- loop drift
- role drift

---

### Step 5 — Approval Decision
Create an approval record matching:

`contracts/executive/approval-record.schema.json`

Decision must be one of:
- approve
- revise
- reroute
- split
- escalate

No implicit approval is allowed.

---

### Step 6 — Handoff Decision
If decision = `approve`:
- emit an execution-ready package for `workspace-exec`

If decision is anything else:
- do not hand off to execution

This is fail-closed.

---

## 4. Required Artifacts Per Run

A valid manual Exec run should produce:

1. Task Contract
2. Delegation Brief
3. Specialist Output
4. Approval Record
5. Execution Handoff Decision

---

## 5. Hard Rules

- Exec must not do specialist work
- Specialists must not self-approve
- No work reaches `workspace-exec` without explicit approval
- No vague delegation
- No silent scope expansion
- No tool expansion without approval

---

## 6. Success Condition

The manual runtime is considered successful if a raw request can be converted into a bounded, reviewable, approval-gated flow without ambiguity about:

- ownership
- scope
- tool use
- approval status
- execution eligibility

---

## 7. Purpose of This Stage

This manual runtime exists to validate the Executive Control Layer before building full automation.

It should expose:
- missing fields
- weak contracts
- unclear delegation
- drift-detection gaps
- approval ambiguities