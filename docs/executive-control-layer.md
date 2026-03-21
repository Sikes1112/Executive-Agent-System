# Executive Control Layer

## 1. Purpose

The Executive Control Layer (Exec) is the supervisory control plane of the system.

It sits above all specialists and above the execution layer.

Its responsibility is to ensure that:
- work is clearly defined before execution
- the correct agent performs the work
- tool usage is constrained and approved
- outputs remain aligned with the original intent
- only validated, approved changes reach the execution layer

Exec does not perform the work.  
Exec ensures the work is correct, safe, and on-track.

---

## 2. Scope

Exec is responsible for:

- Intent intake and classification
- Task validation and structuring
- Specialist routing and delegation
- Tool and capability governance
- Drift detection and correction
- Approval or rejection of outputs
- Controlled handoff to the execution layer
- Continuity and task-state awareness

---

## 3. Non-Scope

Exec MUST NOT:

- Perform specialist work
- Modify the workspace directly
- Bypass contracts or validation layers
- Allow specialists to self-authorize tools or scope
- Act as a general-purpose worker

If Exec begins performing specialist tasks, it is a system failure.

---

## 4. System Position

The system operates as a controlled pipeline:

User → Exec → Specialist → Exec Review → workspace-exec

- Exec governs all decisions
- Specialists perform bounded work
- workspace-exec performs validated mutations

No component may bypass Exec.

---

## 5. Control Loop

Every request MUST pass through the following loop:

### 5.1 Intake

Exec receives a request and determines:

- Is this simple chat or structured work?
- Does this require a specialist?
- Is the request sufficiently clear?

If unclear, Exec must:
- narrow the request, or
- ask a single targeted clarification

---

### 5.2 Intent Validation

Exec converts the request into a structured task definition:

- Objective
- Deliverable
- Constraints
- Non-goals
- Acceptance criteria
- Risk level

If any critical element is missing:
- Exec must not proceed to delegation

---

### 5.3 Tool Governance

Exec defines the allowed execution environment:

- Allowed tools
- Disallowed tools
- Internet permissions
- File mutation permissions
- Workspace path scope
- Background execution permissions

Specialists may NOT define or expand their own tool access.

---

### 5.4 Delegation

Exec assigns the task to exactly one specialist.

Delegation must include:
- Objective
- Deliverable
- Constraints
- Tool permissions
- Output requirements

Delegation MUST be bounded and explicit.

---

### 5.5 Drift Detection

Upon receiving specialist output, Exec evaluates:

- Alignment with original objective
- Scope expansion beyond task definition
- Changes to the problem definition
- Tool usage outside approved scope
- Output format correctness
- Evidence of looping or stalled progress

Drift types include:
- Goal Drift
- Scope Drift
- Tool Drift
- Format Drift
- Loop Drift
- Role Drift

---

### 5.6 Approval / Correction

Exec must choose one of the following:

- Approve — output meets all requirements
- Revise — requires correction within scope
- Reroute — incorrect specialist or domain
- Split — decompose into smaller tasks
- Escalate — request user input

Exec MUST NOT pass unvalidated work forward.

---

### 5.7 Handoff to Execution Layer

Only approved, concrete mutations are passed to `workspace-exec`.

Exec produces a structured, validated execution package.

workspace-exec:
- validates contracts
- applies changes atomically
- records audit artifacts

Exec does not execute changes directly.

---

## 6. Ownership Boundaries

### Exec

- Owns task definition
- Owns routing decisions
- Owns tool approval
- Owns drift detection
- Owns final approval
- Owns continuity and task state

### Specialists

- Stateless
- Operate only within assigned briefs
- Cannot modify system state directly
- Cannot approve their own work
- Cannot expand scope without approval

### workspace-exec

- Executes approved mutations only
- Enforces contracts and validation
- Applies changes atomically
- Produces audit logs

---

## 7. Fail-Closed Policy

The system MUST fail closed.

Exec must block execution if:

- Intent is unclear
- Task definition is incomplete
- Tool permissions are undefined
- Drift is detected
- Output does not meet acceptance criteria

No partial or uncertain work may reach the execution layer.

---

## 8. Enforcement Principles

- No implicit behavior — all actions must be defined
- No silent scope expansion
- No self-escalation by specialists
- No direct mutation outside execution layer
- All work must pass through Exec validation

---

## 9. Future Implementation Surfaces

The following components operationalize this layer:

- Task Contract Schema
- Tool Policy Matrix
- Delegation Brief Format
- Drift Model Definition
- Approval Record Schema

These must align with this control loop.

---

## 10. Core Principle

Reliability is not achieved by smarter agents.

Reliability is achieved by enforcing structure between intent and execution.

Exec is that structure.