# The Execution Layer

## 1. The Problem

Agents produce intent. They reason about what should change, generate text, and call tools. What they do not do — reliably — is produce safe, consistent workspace mutations.

Direct tool execution has no enforcement: no path restrictions, no structural validation, no atomic guarantees. An agent that writes files directly can clobber unrelated state, introduce partial updates, skip validation, and leave no recoverable record. Run it twice and get different results. Run it at scale and get drift.

The problem is not the agent. The problem is the absence of structure between the agent and the workspace.

---

## 2. The Execution Layer Concept

An execution layer sits between intent and mutation. It receives what an agent decided should happen and controls how that decision is carried out.

It is not responsible for the decision. It is responsible for execution: validating the proposed change, enforcing contracts, applying it safely, and recording what happened.

Intent in. Controlled mutation out.

---

## 3. What workspace-exec Does

- **Enforces contracts.** Patches must target allowlisted paths. Entity guard blocks unauthorized structural additions. Approval policy gates changes before apply.
- **Runs fail-closed.** Any stage failure halts execution. No partial mutation is applied.
- **Guarantees atomic apply.** Changes are staged, validated, and applied as a single atomic operation. Either the full patch lands or nothing does.
- **Produces an audit trail.** Every run writes artifacts: input, envelope, validation result, and per-ticket pipeline output.

---

## 4. What It Is Not

- Not an agent — it has no reasoning, planning, or memory  
- Not a scheduler — it does not decide when or what to run  
- Not a framework — it does not provide abstractions for building agents  
- Not a memory system — it holds no state beyond the workspace it mutates  

---

## 5. Why This Matters

Agent systems fail at the execution boundary. The reasoning layer can be sophisticated; if mutations are uncontrolled, the system is unreliable.

A dedicated execution layer makes the contract explicit: agents think, workspace-exec executes. This separation allows the agent layer to change without affecting how mutations are applied.

It enables safe automation, deterministic behavior, and auditability.

Reliability in agent systems is not a property of the agent. It is a property of the execution layer.