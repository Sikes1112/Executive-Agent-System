from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts" / "exec"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def extract_json_block(text: str) -> Any:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model output:\n{text}")

    return json.loads(text[start:end + 1])


def call_model(system_prompt: str, user_payload: str) -> str:
    body = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        "options": {
            "temperature": 0.2
        },
        "keep_alive": "10m",
    }

    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama HTTP error {e.code} calling {OLLAMA_URL}:\n{detail}"
        ) from e
    except error.URLError as e:
        raise RuntimeError(
            f"Could not reach Ollama at {OLLAMA_URL}. "
            "Make sure `ollama serve` is running."
        ) from e

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama returned non-JSON response:\n{raw}") from e

    message = parsed.get("message", {})
    content = message.get("content", "")

    if not content:
        raise RuntimeError(f"Ollama response missing message.content:\n{raw}")

    return content


def run_intake(raw_request: str) -> dict[str, Any]:
    prompt = read_text(PROMPTS_DIR / "manual-intake-prompt.md")
    output = call_model(prompt, raw_request)
    parsed = extract_json_block(output)
    return parsed


CANONICAL_SPECIALISTS = {
    "exec",
    "main",
    "continuity",
    "iteration",
    "outreach",
    "reputationops",
    "helper",
    "agent-builder",
}

PLACEHOLDER_PATH_MARKERS = {
    "/path/to/",
    "path/to/",
    "<path>",
    "TBD",
}


def normalize_specialist(name: str) -> str:
    lowered = name.strip().lower()

    if lowered in {"ui/ux designer", "ui designer", "ux designer", "designer"}:
        return "iteration"

    if lowered in {"writer", "copywriter", "messaging"}:
        return "outreach"

    if lowered in {"project continuity", "continuity agent"}:
        return "continuity"

    return name


def has_placeholder_path(paths: list[str]) -> bool:
    for p in paths:
        for marker in PLACEHOLDER_PATH_MARKERS:
            if marker in p:
                return True
    return False


def normalize_task_contract(task_contract: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(task_contract)

    specialist = normalized.get("assigned_specialist", "")
    normalized["assigned_specialist"] = normalize_specialist(specialist)

    tool_policy = dict(normalized.get("tool_policy", {}))

    # Ground this control loop in your agent/tool model instead of design tools.
    allowed_tools = tool_policy.get("allowed_tools", [])
    if normalized["assigned_specialist"] == "iteration":
        tool_policy["allowed_tools"] = [
            t for t in allowed_tools
            if t in {"patch_proposal", "refactor_proposal", "ui_improvement_proposal"}
        ] or ["ui_improvement_proposal", "patch_proposal"]

        tool_policy["disallowed_tools"] = list(set(
            tool_policy.get("disallowed_tools", []) + [
                "architecture_redesign",
                "unapproved_scope_expansion",
            ]
        ))

        # This task should not need internet by default.
        tool_policy["internet"] = "off"

        # Paths must stay empty unless grounded in a real repo path.
        if has_placeholder_path(tool_policy.get("allowed_paths", [])):
            tool_policy["allowed_paths"] = []

    normalized["tool_policy"] = tool_policy

    # Replace outcome-heavy criteria with reviewable artifact criteria.
    criteria = normalized.get("acceptance_criteria", [])
    rewritten = []
    for c in criteria:
        if "engagement metrics" in c.lower() or "significant improvement" in c.lower():
            continue
        rewritten.append(c)

    if normalized["assigned_specialist"] == "iteration":
        rewritten.extend([
            "Proposed changes remain within the hero section only.",
            "No new interactive component is introduced that changes page structure.",
            "The revised copy and UI suggestions are concrete and reviewable.",
        ])

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for item in rewritten:
        if item not in seen:
            seen.add(item)
            deduped.append(item)

    normalized["acceptance_criteria"] = deduped

    return normalized


def validate_task_contract_grounding(task_contract: dict[str, Any]) -> None:
    specialist = task_contract.get("assigned_specialist")
    if specialist not in CANONICAL_SPECIALISTS:
        raise ValueError(
            f"Task contract assigned_specialist is not canonical: {specialist}"
        )

    tool_policy = task_contract.get("tool_policy", {})
    paths = tool_policy.get("allowed_paths", [])
    if has_placeholder_path(paths):
        raise ValueError(f"Task contract contains placeholder allowed_paths: {paths}")


def run_delegation(task_contract: dict[str, Any]) -> dict[str, Any]:
    prompt = read_text(PROMPTS_DIR / "manual-delegation-prompt.md")
    output = call_model(prompt, json.dumps(task_contract, indent=2))
    parsed = extract_json_block(output)
    return parsed


def run_specialist(delegation_brief: dict[str, Any]) -> str:
    specialist = delegation_brief.get("assigned_specialist", "unknown")

    system_prompt = f"""
        You are the {specialist} specialist.

        You are executing a bounded delegation brief.
        Your job is to produce the actual work product and nothing outside the approved scope.

        Hard rules:
        - Do not restate the brief.
        - Do not add timelines, resources, approval processes, or project-management sections.
        - Do not invent new media types, new components, or new structure unless explicitly allowed.
        - Do not introduce video backgrounds, sliders, overlays, popups, or new structural elements unless explicitly requested.
        - Do not claim compliance if your proposal changes page structure.
        - Treat "maintain existing layout/structure" as meaning:
        - keep the same section structure
        - keep the same content pattern
        - only improve copy, styling, spacing, hierarchy, emphasis, and existing CTA presentation
        - If a proposed change would alter structure, do not include it.
        - Stay within the hero section only.
        - Return concrete, reviewable output.

        Required output shape:
        1. Work-Product Summary
        2. Proposed Changes
        3. Rationale by acceptance criterion
        4. Scope Check

        In Scope examples:
        - stronger headline
        - clearer subheadline
        - CTA copy improvement
        - spacing improvement
        - typography emphasis
        - trust cue text
        - non-structural visual polish

        Out of Scope examples unless explicitly approved:
        - video backgrounds
        - sliders
        - new overlays
        - new sections
        - new component types
        - major layout changes
        - feature additions

        If the task cannot be improved without violating scope, say that directly and explain the boundary.
        """
    return call_model(system_prompt, json.dumps(delegation_brief, indent=2))


def run_review(
    task_contract: dict[str, Any],
    delegation_brief: dict[str, Any],
    specialist_output: str,
) -> dict[str, Any]:
    prompt = read_text(PROMPTS_DIR / "manual-review-prompt.md")
    payload = {
        "task_contract": task_contract,
        "delegation_brief": delegation_brief,
        "specialist_output": specialist_output,
    }
    output = call_model(prompt, json.dumps(payload, indent=2))
    parsed = extract_json_block(output)
    return parsed


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python core/exec_runner.py "your request here"')
        sys.exit(1)

    raw_request = sys.argv[1]

    intake_result = run_intake(raw_request)

    print("\n=== INTAKE RESULT ===")
    print(json.dumps(intake_result, indent=2))

    if intake_result.get("classification") == "chat":
        print("\nStopped at chat classification.")
        return

    task_contract = normalize_task_contract(intake_result)
    validate_task_contract_grounding(task_contract)

    print("\n=== NORMALIZED TASK CONTRACT ===")
    print(json.dumps(task_contract, indent=2))

    delegation_brief = run_delegation(task_contract)
    print("\n=== DELEGATION BRIEF ===")
    print(json.dumps(delegation_brief, indent=2))

    specialist_output = run_specialist(delegation_brief)
    print("\n=== SPECIALIST OUTPUT ===")
    print(specialist_output)

    approval_record = run_review(task_contract, delegation_brief, specialist_output)
    print("\n=== APPROVAL RECORD ===")
    print(json.dumps(approval_record, indent=2))


if __name__ == "__main__":
    main()