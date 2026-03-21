from __future__ import annotations


class ReputationOpsAdapter:
    name = "reputationops"
    mode = "pipeline"

    def get_prompt_path(self) -> str:
        return "core/prompts/reputationops_specialist.md"

    def get_guard_behavior(self) -> str:
        return "passthrough"
