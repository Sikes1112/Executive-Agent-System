from __future__ import annotations


class IterationAdapter:
    name = "iteration"
    mode = "mutation"

    def get_prompt_path(self) -> str:
        return "core/prompts/iteration_specialist.md"

    def get_guard_behavior(self) -> str:
        return "iteration"
