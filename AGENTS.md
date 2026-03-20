# AGENTS.md

Repository-level guidance for coding agents:

- Keep changes focused and minimal.
- Do not change core execution/governance logic unless explicitly requested.
- Prefer reversible refactors and preserve the runnable golden path.
- Use `WORKSPACE_ROOT`-relative paths; avoid hardcoded local machine paths.
- Keep docs and examples aligned with code changes.
- Avoid adding new dependencies unless necessary.
