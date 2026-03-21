# Architecture Overview

This document describes the architecture pattern and how this repository currently implements it.

## 1. Pattern: Executive Control Layer

An executive control layer separates:
- **intent generation** (agents/orchestrator)
- **execution governance** (validation, constraints, handling, audit)

The control layer does not decide product intent. It governs whether and how intent is allowed to execute.

Core pattern:
1. accept intent/envelope
2. validate envelope and dependencies
3. resolve ticket domain
4. invoke specialist
5. sanitize against domain contract
6. branch by handling mode
7. persist audit artifacts
8. fail closed on violations

## 2. Reference Implementation In This Repo

Primary entrypoints:
- `entrypoints/run_intake.sh`
- `entrypoints/run_batch.sh`
- `entrypoints/run_once.sh`

Core modules:
- `core/batch/validate.py`
- `core/domain_adapters/registry.json`
- `core/pipeline/sanitize.py`
- `core/pipeline/field_guard.py`
- `core/pipeline/allowlist.py`
- `core/pipeline/entity_guard.py`
- `core/pipeline/approve.py`
- `core/pipeline/apply.py`

## 3. Domain Model

Supported domains:
- `iteration` (mutation domain)
- `outreach` (generation domain)
- `reputationops` (pipeline domain)

Domain metadata drives:
- specialist prompt path
- guard behavior
- whether sanitize can continue to apply path

## 4. Execution Paths

### 4.1 Mutation path (`iteration`)

1. sanitize
2. field guard
3. allowlist
4. entity guard
5. approval
6. staged apply + atomic swap

### 4.2 Non-mutation path (`outreach`, `reputationops`)

1. sanitize
2. persist normalized artifact
3. persist metadata artifact
4. controlled success stop

No mutation apply is attempted on this path.

## 5. Batch Behavior

- envelope validation occurs before execution
- tickets execute in dependency order
- domain is resolved per ticket
- stop on first failing ticket
- no cross-ticket rollback

## 6. Audit Model

Artifacts are written to:
- `audit/helper_runs/`
- `audit/exec_runs/<timestamp>/`

Artifacts include envelope/validation inputs plus per-ticket outputs and domain-specific metadata for non-mutation domains.

## 7. Fail-Closed Guarantees

- invalid contracts stop execution
- stage failures halt ticket execution
- mutation apply is bounded and atomic for mutation domain
- audit artifacts preserve execution evidence

## 8. Adaptation Guidance

To adapt this architecture to another agent system:
- keep your planner/orchestrator upstream
- preserve sanitize-first, domain-aware contract enforcement
- keep mutation apply separate from non-mutation handling
- keep deterministic audit outputs

