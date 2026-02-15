# PREFLIGHT_CHECKLIST.md — Exec Router Pre-Flight

Exec must complete this checklist BEFORE creating a Ticket ID.

## A) Workspace Sanity (must pass)
- [ ] Confirm working workspace: `~/.openclaw/workspace-exec`
- [ ] Required dirs exist: `tickets/`, `memory/`
- [ ] Required files exist:
  - [ ] `SOUL.md`
  - [ ] `tickets/TICKET_TEMPLATE.md`
  - [ ] `memory/index.md`
  - [ ] `memory/YYYY-MM-DD.md` (today)

## B) Runtime Health (must pass)
- [ ] Gateway health is OK (`openclaw gateway status` shows RPC probe ok)

## C) Scope & Safety (must pass)
- [ ] Deliverable is 1 sentence and unambiguous
- [ ] Constraints include an explicit do-not-touch list
- [ ] Tools are OFF by default unless explicitly approved for this step
- [ ] No destructive action required for this ticket (if required → create a separate DESTRUCTIVE step)

## D) Routing Readiness (must pass)
- [ ] `AGENT_CAPABILITIES.md` exists and was consulted
- [ ] Selected agent exists (or agent creation is proposed as a separate step)

## If any check fails
Request exactly ONE missing artifact or clarifying detail, then stop.
