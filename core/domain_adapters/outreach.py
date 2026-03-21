from __future__ import annotations


class OutreachAdapter:
    name = "outreach"
    mode = "generation"

    def get_prompt_path(self) -> str:
        return "core/prompts/outreach_specialist.md"

    def get_guard_behavior(self) -> str:
        return "passthrough"
