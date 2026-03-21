# Task Contract Generation

## 1. Purpose

This document defines how Exec converts an incoming request into a valid Task Contract.

A Task Contract is the first structured artifact in the Executive Control Layer.
No delegation may occur until a valid Task Contract exists.

---

## 2. Input

Exec receives:
- raw user request
- recent context if relevant
- current project/task state if relevant

---

## 3. Output

Exec must produce a Task Contract matching:

`contracts/executive/task-contract.schema.json`

---

## 4. Generation Procedure

### Step 1 — Classify the request
Determine:
- chat vs task
- specialist needed vs not needed
- clear vs unclear

If chat-only, stop here.

### Step 2 — Extract core task intent
Derive:
- objective
- deliverable
- constraints
- likely risk level

### Step 3 — Define non-goals
State what is explicitly out of scope.

### Step 4 — Define acceptance criteria
List concrete checks that would make the task complete.

### Step 5 — Assign specialist
Select exactly one specialist.

### Step 6 — Apply tool policy
Attach a task-level tool policy consistent with:
`contracts/executive/tool-policy-matrix.json`

### Step 7 — Validate completeness
If objective, deliverable, constraints, non-goals, or acceptance criteria are unclear:
- narrow the task, or
- ask one targeted clarification

### Step 8 — Emit contract
Produce a valid Task Contract artifact.

---

## 5. Clarification Rule

Exec may ask at most one targeted clarification before contract generation if a critical field cannot be safely inferred.

If the task can be safely narrowed without clarification, Exec should narrow it and proceed.

---

## 6. Hard Stop Conditions

Exec must not emit a Task Contract if:
- no objective can be identified
- no deliverable can be identified
- specialist assignment is ambiguous
- tool scope cannot be bounded
- the request is too unclear to constrain safely

---

## 7. Core Principle

The goal is not to perfectly understand the request in the abstract.

The goal is to reduce it into bounded, reviewable, executable structure.