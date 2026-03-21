# Current Limitations

This document lists current implementation constraints in this repository.

## Execution and Atomicity

- Atomicity is per ticket, not per batch.
- No cross-ticket rollback.
- Sequential ticket execution only.

## Domain Handling

- Only mutation domain outputs (`iteration`) can enter apply.
- Non-mutation domains (`outreach`, `reputationops`) stop after sanitize + artifact persistence.
- Unsupported domains are rejected by batch validation and/or domain routing.

## Control and Policy

- Approval policy is global per run (`APPROVAL_POLICY`), not per ticket.
- Entity guard coverage is currently iteration-oriented.

## Integration and Config

- Workspace structure assumptions are implementation-specific.
- Intake is heuristic/pattern-based convenience logic.
- No built-in batch resume.

## Reliability and Ops

- Stale lock directories may require manual cleanup.
- Audit artifacts are files on disk and are not append-only protected by default.

