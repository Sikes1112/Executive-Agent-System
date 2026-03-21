from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
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

TASK_CONTRACT_REQUIRED_FIELDS = {
    "task_id",
    "source_request",
    "objective",
    "deliverable",
    "constraints",
    "non_goals",
    "acceptance_criteria",
    "risk_level",
    "assigned_specialist",
    "tool_policy",
}

DELEGATION_BRIEF_REQUIRED_FIELDS = {
    "delegation_id",
    "task_id",
    "assigned_specialist",
    "objective",
    "deliverable",
    "constraints",
    "non_goals",
    "acceptance_criteria",
    "tool_policy",
    "output_requirements",
    "escalation_conditions",
}

APPROVAL_RECORD_REQUIRED_FIELDS = {
    "approval_id",
    "task_id",
    "delegation_id",
    "assigned_specialist",
    "decision",
    "decision_reason",
    "drift_review",
    "tool_compliance",
    "next_action",
    "created_at",
}

APPROVAL_DECISIONS = {"approve", "revise", "reroute", "split", "escalate"}
TOOL_COMPLIANCE_VALUES = {"compliant", "non_compliant", "not_applicable"}
DRIFT_KEYS = (
    "goal_drift",
    "scope_drift",
    "tool_drift",
    "format_drift",
    "loop_drift",
    "role_drift",
)


def normalize_specialist(name: str) -> str:
    lowered = name.strip().lower()

    if lowered in {"ui/ux designer", "ui designer", "ux designer", "designer"}:
        return "iteration"
    if lowered in {"web developer", "frontend developer", "front-end developer"}:
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


def _build_blocked_intake_result(source_request: str, reason: str) -> dict[str, Any]:
    return {
        "classification": "blocked",
        "decision": "escalate",
        "reason": reason,
        "source_request": source_request,
        "risk_level": "high",
    }


def canonicalize_intake_result(
    raw_request: str,
    intake_result: dict[str, Any],
) -> dict[str, Any]:
    classification = str(intake_result.get("classification", "")).strip().lower()

    if classification in {"blocked", "escalate", "chat"}:
        reason = str(intake_result.get("reason", "")).strip()
        if not reason:
            reason = "Intake did not produce a canonical task contract."
        return _build_blocked_intake_result(raw_request, reason)

    candidate = intake_result
    for key in ("task_contract", "contract", "normalized_task_contract", "payload"):
        nested = intake_result.get(key)
        if isinstance(nested, dict):
            candidate = nested
            break

    if not isinstance(candidate, dict):
        return _build_blocked_intake_result(
            raw_request,
            "Intake payload was not a JSON object task contract.",
        )

    normalized_candidate = dict(candidate)
    if "source_request" not in normalized_candidate or not str(
        normalized_candidate.get("source_request", "")
    ).strip():
        normalized_candidate["source_request"] = raw_request

    missing = _missing_or_empty_fields(normalized_candidate, TASK_CONTRACT_REQUIRED_FIELDS)
    if missing:
        return _build_blocked_intake_result(
            raw_request,
            "Intake task contract missing required fields: " + ", ".join(missing),
        )

    return normalized_candidate


def is_high_risk_broad_scope_request(task_contract: dict[str, Any]) -> bool:
    source_text = " ".join([
        str(task_contract.get("source_request", "")),
        str(task_contract.get("objective", "")),
        str(task_contract.get("deliverable", "")),
    ]).lower()
    scope_text = " ".join([
        " ".join(task_contract.get("constraints", []) or []),
        " ".join(task_contract.get("non_goals", []) or []),
    ]).lower()
    combined = f"{source_text} {scope_text}"

    broad_markers = (
        "redesign entire website",
        "redesign the entire website",
        "redesign whole website",
        "redesign whole site",
        "restructure all pages",
        "restructure every page",
        "all pages",
        "animations everywhere",
        "across the entire site",
        "site-wide redesign",
        "full website redesign",
        "completely redesign",
    )
    return any(marker in combined for marker in broad_markers)


def supports_explicit_broad_scope(task_contract: dict[str, Any]) -> bool:
    tool_policy = task_contract.get("tool_policy", {}) or {}
    allowed_tools = {str(t).strip().lower() for t in tool_policy.get("allowed_tools", [])}
    explicit_tools = {
        "architecture_redesign",
        "sitewide_redesign",
        "site_wide_redesign",
        "full_redesign",
    }
    return bool(allowed_tools.intersection(explicit_tools))


def detect_scope_conflicts(task_contract: dict[str, Any]) -> list[str]:
    source_text = " ".join([
        str(task_contract.get("source_request", "")),
        str(task_contract.get("objective", "")),
        str(task_contract.get("deliverable", "")),
    ]).lower()
    policy_text = " ".join([
        " ".join(task_contract.get("constraints", []) or []),
        " ".join(task_contract.get("non_goals", []) or []),
        " ".join(task_contract.get("acceptance_criteria", []) or []),
    ]).lower()

    requested_structural = any(marker in source_text for marker in (
        "video background",
        "carousel",
        "slider",
        "interactive carousel",
        "interactive hero",
    ))
    forbidden_structural = any(marker in policy_text for marker in (
        "no new interactive component",
        "maintain existing layout",
        "maintain existing structure",
        "no major redesign",
        "hero section only",
        "do not introduce video backgrounds",
        "do not introduce",
    ))

    conflicts = []
    if requested_structural and forbidden_structural:
        conflicts.append(
            "Task requests structural/interactive additions while bounded scope forbids them."
        )
    return conflicts


def detect_request_level_block_reason(raw_request: str) -> str | None:
    lowered = raw_request.lower()

    broad_markers = (
        "redesign entire website",
        "redesign the entire website",
        "redesign whole website",
        "redesign whole site",
        "restructure all pages",
        "restructure every page",
        "animations everywhere",
        "site-wide redesign",
        "full website redesign",
        "completely redesign",
    )
    if any(marker in lowered for marker in broad_markers):
        return (
            "High-risk broad scope request requires explicit redesign support; "
            "escalating instead of bounded iteration execution."
        )

    hero_markers = ("hero", "hero section")
    forbidden_additions = ("video background", "carousel", "slider", "interactive carousel")
    if (
        any(marker in lowered for marker in hero_markers)
        and any(marker in lowered for marker in forbidden_additions)
    ):
        return (
            "Scope contradiction detected: bounded hero improvements cannot include "
            "video backgrounds or interactive carousel/slider additions."
        )

    return None


def is_hero_scoped_source_request(source_request: str) -> bool:
    lowered = source_request.lower()

    hero_markers = ("hero", "hero section", "above the fold")
    broad_markers = (
        "whole site",
        "entire site",
        "site-wide",
        "whole website",
        "entire website",
        "full redesign",
        "redesign the site",
        "redesign the website",
    )

    has_hero_marker = any(marker in lowered for marker in hero_markers)
    has_broad_marker = any(marker in lowered for marker in broad_markers)
    return has_hero_marker and not has_broad_marker


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

    source_request = str(normalized.get("source_request", ""))
    if (
        normalized["assigned_specialist"] == "iteration"
        and is_hero_scoped_source_request(source_request)
    ):
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


def _missing_or_empty_fields(payload: dict[str, Any], required: set[str]) -> list[str]:
    missing = []
    for field in sorted(required):
        if field not in payload:
            missing.append(field)
            continue

        value = payload[field]
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
            continue
        if isinstance(value, (list, dict)) and not value:
            missing.append(field)
            continue
    return missing


def validate_task_contract_grounding(task_contract: dict[str, Any]) -> None:
    missing = _missing_or_empty_fields(task_contract, TASK_CONTRACT_REQUIRED_FIELDS)
    if missing:
        raise ValueError(
            "Task contract missing required bounded fields: "
            + ", ".join(missing)
        )

    specialist = task_contract.get("assigned_specialist")
    if specialist not in CANONICAL_SPECIALISTS:
        raise ValueError(
            f"Task contract assigned_specialist is not canonical: {specialist}"
        )

    tool_policy = task_contract.get("tool_policy", {})
    paths = tool_policy.get("allowed_paths", [])
    if has_placeholder_path(paths):
        raise ValueError(f"Task contract contains placeholder allowed_paths: {paths}")


def validate_delegation_brief(delegation_brief: dict[str, Any]) -> None:
    missing = _missing_or_empty_fields(
        delegation_brief, DELEGATION_BRIEF_REQUIRED_FIELDS
    )
    if missing:
        raise ValueError(
            "Delegation brief missing required fields: " + ", ".join(missing)
        )


def _map_review_decision(parsed_review: dict[str, Any]) -> str:
    decision = str(parsed_review.get("decision", "")).strip().lower()
    if decision in APPROVAL_DECISIONS:
        return decision

    status = str(parsed_review.get("status", "")).strip().lower()
    if status in {"approved", "approve"}:
        return "approve"
    if status in {"review_blocked", "blocked", "escalate"}:
        return "escalate"
    if status in {"revise", "revision_required"}:
        return "revise"
    if status in {"reroute"}:
        return "reroute"
    if status in {"split"}:
        return "split"

    return "revise"


def _canonicalize_drift_review(raw_drift: Any) -> dict[str, bool]:
    source = raw_drift if isinstance(raw_drift, dict) else {}
    return {
        key: bool(source.get(key, False))
        for key in DRIFT_KEYS
    }


def normalize_approval_record(
    task_contract: dict[str, Any],
    delegation_brief: dict[str, Any],
    parsed_review: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task_contract.get("task_id", "")).strip()
    delegation_id = str(delegation_brief.get("delegation_id", "")).strip()
    assigned_specialist = str(
        delegation_brief.get("assigned_specialist")
        or task_contract.get("assigned_specialist")
        or "unknown"
    ).strip()

    decision = _map_review_decision(parsed_review)
    reason = (
        str(parsed_review.get("decision_reason", "")).strip()
        or str(parsed_review.get("reason", "")).strip()
        or "No explicit decision reason provided by review model."
    )

    tool_compliance = str(
        parsed_review.get("tool_compliance", "not_applicable")
    ).strip().lower()
    if tool_compliance not in TOOL_COMPLIANCE_VALUES:
        tool_compliance = "not_applicable"

    approval_record = {
        "approval_id": (
            str(parsed_review.get("approval_id", "")).strip()
            or f"approval-{task_id or 'unknown'}-{delegation_id or 'unknown'}"
        ),
        "task_id": task_id,
        "delegation_id": delegation_id,
        "assigned_specialist": assigned_specialist,
        "decision": decision,
        "decision_reason": reason,
        "drift_review": _canonicalize_drift_review(parsed_review.get("drift_review")),
        "tool_compliance": tool_compliance,
        "next_action": (
            str(parsed_review.get("next_action", "")).strip()
            or (
                "Emit execution package for workspace-exec with approved bounded changes."
                if decision == "approve"
                else "Hold handoff until Exec resolves review outcome."
            )
        ),
        "approved_execution_package_ref": str(
            parsed_review.get("approved_execution_package_ref", "")
        ).strip(),
        "revision_instructions": [
            str(item) for item in parsed_review.get("revision_instructions", [])
            if str(item).strip()
        ] if isinstance(parsed_review.get("revision_instructions"), list) else [],
        "reroute_target": str(parsed_review.get("reroute_target", "")).strip(),
        "split_tasks": [
            str(item) for item in parsed_review.get("split_tasks", [])
            if str(item).strip()
        ] if isinstance(parsed_review.get("split_tasks"), list) else [],
        "escalation_question": str(
            parsed_review.get("escalation_question", "")
        ).strip(),
        "created_at": (
            str(parsed_review.get("created_at", "")).strip()
            or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        ),
    }

    if approval_record["decision"] != "approve":
        approval_record["approved_execution_package_ref"] = ""

    missing = _missing_or_empty_fields(approval_record, APPROVAL_RECORD_REQUIRED_FIELDS)
    if missing:
        raise ValueError(
            "Approval record missing required fields after normalization: "
            + ", ".join(missing)
        )

    return approval_record


def build_delegation_brief_fallback(task_contract: dict[str, Any]) -> dict[str, Any]:
    objective = task_contract["objective"]
    constraints = task_contract["constraints"]
    non_goals = task_contract["non_goals"]
    acceptance_criteria = task_contract["acceptance_criteria"]

    structural_task = any(
        phrase in " ".join(constraints + non_goals).lower()
        for phrase in [
            "layout",
            "structure",
            "do not redesign",
            "unchanged",
            "no major redesign",
            "hero section only",
        ]
    )

    output_requirements = [
        "Return a concise work-product summary.",
        "Return specific, concrete proposed hero-section changes.",
        "Explain how each change satisfies the acceptance criteria.",
        "Include a scope check stating why the proposal remains within bounds.",
    ]

    escalation_conditions = [
        "The task cannot be completed without changing layout or structure.",
        "The required improvement would introduce a new component type or new interaction pattern.",
        "The requested result cannot be achieved within the approved tool or mutation scope.",
    ]

    if structural_task:
        output_requirements.extend([
            "Do not introduce video backgrounds, sliders, overlays, popups, new sections, or new component types.",
            "Limit changes to copy refinement, visual polish, spacing, typography emphasis, CTA refinement, and non-structural trust/clarity improvements.",
        ])
        escalation_conditions.append(
            "A meaningful improvement would require structural redesign beyond the approved scope."
        )

    return {
        "delegation_id": f"delegation-{task_contract['task_id']}",
        "task_id": task_contract["task_id"],
        "assigned_specialist": task_contract["assigned_specialist"],
        "objective": task_contract["objective"],
        "deliverable": task_contract["deliverable"],
        "constraints": task_contract["constraints"],
        "non_goals": task_contract["non_goals"],
        "acceptance_criteria": task_contract["acceptance_criteria"],
        "tool_policy": task_contract["tool_policy"],
        "output_requirements": output_requirements,
        "escalation_conditions": escalation_conditions,
        "created_at": task_contract["created_at"],
    }


def run_delegation(task_contract: dict[str, Any]) -> tuple[dict[str, Any], str]:
    parsed = build_delegation_brief_fallback(task_contract)
    output = json.dumps(parsed, indent=2)
    print("\n=== RAW DELEGATION OUTPUT ===")
    print(output)

    validate_delegation_brief(parsed)
    return parsed, output

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
    return normalize_approval_record(task_contract, delegation_brief, parsed)


def _create_run_audit_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = REPO_ROOT / "audit" / "exec_runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_execution_package(
    task_contract: dict[str, Any],
    delegation_brief: dict[str, Any],
    approval_record: dict[str, Any],
    specialist_output: str,
    matched_grounding_candidates: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    grounding = {
        "matched_candidates": matched_grounding_candidates or [],
    }
    return {
        "task_id": task_contract.get("task_id", ""),
        "delegation_id": delegation_brief.get("delegation_id", ""),
        "approval_id": approval_record.get("approval_id", ""),
        "approved_scope": {
            "objective": (
                delegation_brief.get("objective")
                or task_contract.get("objective", "")
            ),
            "constraints": (
                delegation_brief.get("constraints")
                or task_contract.get("constraints", [])
            ),
            "non_goals": (
                delegation_brief.get("non_goals")
                or task_contract.get("non_goals", [])
            ),
            "tool_policy": (
                delegation_brief.get("tool_policy")
                or task_contract.get("tool_policy", {})
            ),
        },
        "approved_output": specialist_output,
        "next_action": approval_record.get("next_action", ""),
        "grounding": grounding,
    }


def _existing_repo_path(path_str: str) -> str | None:
    if not isinstance(path_str, str):
        return None
    normalized = path_str.strip().replace("\\", "/").lstrip("/")
    if not normalized:
        return None
    if normalized.startswith("workspace-example/"):
        normalized = normalized[len("workspace-example/") :]
    bundles_prefix = "bundles/"
    idx = normalized.find(bundles_prefix)
    if idx >= 0:
        normalized = normalized[idx:]

    candidates = [REPO_ROOT / normalized]
    if normalized.startswith("bundles/"):
        candidates.insert(0, REPO_ROOT / "workspace-example" / normalized)

    for candidate in candidates:
        if candidate.exists():
            return normalized
    return None


def resolve_allowed_paths(task_contract: dict[str, Any]) -> list[str]:
    tool_policy = task_contract.get("tool_policy", {}) or {}
    provided_paths = tool_policy.get("allowed_paths", []) or []
    grounded = []

    for path_str in provided_paths:
        if not isinstance(path_str, str):
            continue
        existing = _existing_repo_path(path_str)
        if existing:
            grounded.append(existing)

    if grounded:
        return list(dict.fromkeys(grounded))
    return []


GROUNDING_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "make",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "up",
    "with",
    "without",
    "improve",
    "improving",
    "update",
    "enhance",
    "refine",
    "change",
    "changes",
    "section",
    "screen",
    "component",
    "page",
    "ui",
    "ux",
    "layout",
    "visual",
    "easier",
    "better",
}


def _extract_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 3 and token not in GROUNDING_STOPWORDS
    }


def _collect_request_grounding_terms(
    task_contract: dict[str, Any],
    delegation_brief: dict[str, Any],
) -> set[str]:
    request_text = " ".join([
        str(task_contract.get("source_request", "")),
        str(task_contract.get("objective", "")),
        str(task_contract.get("deliverable", "")),
        " ".join(str(x) for x in (task_contract.get("constraints") or [])),
        str(delegation_brief.get("objective", "")),
    ])
    return _extract_terms(request_text)


def _collect_object_grounding_terms(node: Any, terms: set[str]) -> None:
    if isinstance(node, dict):
        for key in ("screen_id", "component_id", "id", "purpose", "title"):
            value = node.get(key)
            if isinstance(value, str):
                terms.update(_extract_terms(value))
        for value in node.values():
            _collect_object_grounding_terms(value, terms)
        return

    if isinstance(node, list):
        for item in node:
            _collect_object_grounding_terms(item, terms)


def _load_allowed_path_objects(allowed_paths: list[str]) -> list[Any]:
    objects: list[Any] = []
    for path_str in allowed_paths:
        normalized = _existing_repo_path(path_str)
        if not normalized:
            continue
        candidate = REPO_ROOT / normalized
        if not candidate.exists() and normalized.startswith("bundles/"):
            candidate = REPO_ROOT / "workspace-example" / normalized
        if not candidate.exists() or candidate.suffix.lower() != ".json":
            continue
        try:
            objects.append(json.loads(read_text(candidate)))
        except (json.JSONDecodeError, OSError):
            continue
    return objects


def _build_current_objects_from_allowed_paths(allowed_paths: list[str]) -> dict[str, Any]:
    current_objects: dict[str, Any] = {}
    for path_str in allowed_paths:
        normalized = _existing_repo_path(path_str)
        if not normalized:
            continue
        candidate = REPO_ROOT / normalized
        if not candidate.exists() and normalized.startswith("bundles/"):
            candidate = REPO_ROOT / "workspace-example" / normalized
        if not candidate.exists() or candidate.suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(read_text(candidate))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict):
            current_objects[normalized] = payload
    return current_objects


def load_current_objects() -> dict[str, Any]:
    base = REPO_ROOT / "workspace-example" / "bundles"
    files = {
        "bundles/ui_spec/screens.json": base / "ui_spec" / "screens.json",
        "bundles/ui_spec/components.json": base / "ui_spec" / "components.json",
    }

    current_objects: dict[str, Any] = {}

    for key, path in files.items():
        try:
            with path.open("r", encoding="utf-8") as f:
                current_objects[key] = json.load(f)
        except Exception as e:  # noqa: BLE001
            print(f"Failed to load {path}: {e}")

    return current_objects


def _collect_object_grounding_paths(
    node: Any,
    request_terms: set[str],
    matched_paths: set[str],
    current_path: str | None = None,
) -> None:
    if isinstance(node, dict):
        path_context = current_path
        for key in ("path", "file_path", "bundle_path", "source_path", "target_path"):
            value = node.get(key)
            if isinstance(value, str):
                existing = _existing_repo_path(value)
                if existing:
                    path_context = existing
                    break

        terms: set[str] = set()
        _collect_object_grounding_terms(node, terms)
        if path_context and request_terms.intersection(terms):
            matched_paths.add(path_context)

        for key, value in node.items():
            if isinstance(key, str):
                key_path = _existing_repo_path(key)
                if key_path:
                    _collect_object_grounding_paths(value, request_terms, matched_paths, key_path)
                    continue
            _collect_object_grounding_paths(value, request_terms, matched_paths, path_context)
        return

    if isinstance(node, list):
        for item in node:
            _collect_object_grounding_paths(item, request_terms, matched_paths, current_path)


def _normalize_grounding_text(value: str) -> str:
    lowered = value.lower().replace("_", " ")
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_grounding_keywords(
    task_contract: dict[str, Any],
    delegation_brief: dict[str, Any],
) -> list[str]:
    request_text = " ".join([
        str(task_contract.get("source_request", "")),
        str(task_contract.get("objective", "")),
        str(task_contract.get("deliverable", "")),
        " ".join(str(x) for x in (task_contract.get("constraints") or [])),
        str(delegation_brief.get("objective", "")),
    ])
    normalized = _normalize_grounding_text(request_text)
    keywords: list[str] = []
    seen: set[str] = set()
    for token in normalized.split():
        if len(token) < 3 or token in GROUNDING_STOPWORDS or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _collect_grounding_candidates_from_payload(payload: Any) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if not isinstance(payload, dict):
        return candidates

    for file_path, file_data in payload.items():
        if not isinstance(file_path, str) or not isinstance(file_data, dict):
            continue

        if "screens" in file_data and isinstance(file_data["screens"], list):
            for screen in file_data["screens"]:
                if not isinstance(screen, dict):
                    continue
                screen_id = screen.get("id")
                if isinstance(screen_id, str):
                    normalized = _normalize_grounding_text(screen_id)
                    if normalized:
                        candidates.append((file_path, normalized))

        if "components" in file_data and isinstance(file_data["components"], list):
            for comp in file_data["components"]:
                if not isinstance(comp, dict):
                    continue
                component_id = comp.get("id")
                if isinstance(component_id, str):
                    normalized = _normalize_grounding_text(component_id)
                    if normalized:
                        candidates.append((file_path, normalized))
                component_purpose = comp.get("purpose")
                if isinstance(component_purpose, str):
                    normalized = _normalize_grounding_text(component_purpose)
                    if normalized:
                        candidates.append((file_path, normalized))

    return candidates


def _collect_grounding_candidates_from_object(obj: Any, source_path: str | None) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if not isinstance(obj, dict):
        return candidates

    screens = obj.get("screens")
    if isinstance(screens, list):
        for screen in screens:
            if not isinstance(screen, dict):
                continue
            screen_id = screen.get("id")
            if isinstance(screen_id, str):
                normalized = _normalize_grounding_text(screen_id)
                if normalized:
                    candidates.append((source_path or "", normalized))

    components = obj.get("components")
    if isinstance(components, list):
        for component in components:
            if not isinstance(component, dict):
                continue
            component_id = component.get("id")
            if isinstance(component_id, str):
                normalized = _normalize_grounding_text(component_id)
                if normalized:
                    candidates.append((source_path or "", normalized))
            component_purpose = component.get("purpose")
            if isinstance(component_purpose, str):
                normalized = _normalize_grounding_text(component_purpose)
                if normalized:
                    candidates.append((source_path or "", normalized))

    return candidates


def evaluate_object_grounding(
    task_contract: dict[str, Any],
    delegation_brief: dict[str, Any],
    allowed_paths: list[str],
    current_objects: Any | None = None,
) -> tuple[bool, list[str], list[dict[str, Any]]]:
    keywords = _extract_grounding_keywords(task_contract, delegation_brief)
    if not keywords:
        print("grounding keywords: []")
        print("grounding candidates: []")
        print("grounding matched candidates: []")
        return False, [], []

    if current_objects is None:
        current_objects = task_contract.get("current_objects")
    if current_objects is None:
        current_objects = delegation_brief.get("current_objects")

    candidates: list[tuple[str, str]] = []
    candidates.extend(_collect_grounding_candidates_from_payload(current_objects))

    for path_str in allowed_paths:
        normalized = _existing_repo_path(path_str)
        if not normalized:
            continue
        for obj in _load_allowed_path_objects([normalized]):
            candidates.extend(_collect_grounding_candidates_from_object(obj, normalized))

    deduped_candidates: list[tuple[str, str]] = list(dict.fromkeys(candidates))
    print("grounding candidates:", [candidate for _, candidate in deduped_candidates])

    scored_candidates: list[tuple[str, str, int]] = []

    for source_path, candidate in deduped_candidates:
        score = sum(1 for k in keywords if k in candidate)
        scored_candidates.append((source_path, candidate, score))

    print("grounding keywords:", keywords)
    print(
        "candidate scores:",
        [(candidate, score) for _, candidate, score in scored_candidates],
    )
    matched = [
        (source_path, candidate, score)
        for source_path, candidate, score in scored_candidates
        if score >= 2
    ]
    print("grounding matched candidates:", [candidate for _, candidate, _ in matched])

    request_text = _normalize_grounding_text(
        " ".join(
            [
                str(task_contract.get("source_request", "")),
                str(task_contract.get("objective", "")),
                str(delegation_brief.get("objective", "")),
            ]
        )
    )
    eligible_main = [
        (candidate, score)
        for _, candidate, score in matched
        if len(candidate.split()) >= 2
    ]
    in_request = [
        (candidate, score)
        for candidate, score in eligible_main
        if candidate in request_text
    ]
    main_pool = in_request or eligible_main
    if not main_pool:
        main_pool = [(candidate, score) for _, candidate, score in matched]
    main_entity = ""
    if main_pool:
        main_entity = sorted(
            main_pool,
            key=lambda item: (len(item[0].split()), -item[1], len(item[0])),
        )[0][0]
    main_entity_tokens = set(main_entity.split())

    matched_paths = [path for path, _, _ in matched if path]
    matched_candidates = [
        {
            "file": path,
            "candidate": candidate,
            "score": score,
            "tier": (
                "primary"
                if main_entity_tokens
                and main_entity_tokens.issubset(set(candidate.split()))
                else "secondary"
            ),
        }
        for path, candidate, score in matched
        if path
    ]
    deduped_map: dict[tuple[str, str], dict[str, Any]] = {}
    for item in matched_candidates:
        key = (str(item.get("file", "")), str(item.get("candidate", "")))
        if key in deduped_map:
            continue
        deduped_map[key] = item
    deduped_matched_candidates = list(deduped_map.values())
    return bool(matched), list(dict.fromkeys(matched_paths)), deduped_matched_candidates


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python core/exec_runner.py "your request here"')
        sys.exit(1)

    raw_request = sys.argv[1]
    run_audit_dir = _create_run_audit_dir()

    early_block_reason = detect_request_level_block_reason(raw_request)
    if early_block_reason:
        blocked_result = _build_blocked_intake_result(raw_request, early_block_reason)
        _write_json(run_audit_dir / "intake.json", blocked_result)
        print("\n=== INTAKE RESULT ===")
        print(json.dumps(blocked_result, indent=2))
        print("\nStopped at intake blocked/escalate classification.")
        return

    intake_result = canonicalize_intake_result(raw_request, run_intake(raw_request))
    _write_json(run_audit_dir / "intake.json", intake_result)

    print("\n=== INTAKE RESULT ===")
    print(json.dumps(intake_result, indent=2))

    if intake_result.get("classification") in {"blocked", "escalate"}:
        print("\nStopped at intake blocked/escalate classification.")
        return

    task_contract = normalize_task_contract(intake_result)
    _write_json(run_audit_dir / "normalized_task_contract.json", task_contract)

    print("\n=== NORMALIZED TASK CONTRACT ===")
    print(json.dumps(task_contract, indent=2))

    if is_high_risk_broad_scope_request(task_contract) and not supports_explicit_broad_scope(task_contract):
        blocked_result = _build_blocked_intake_result(
            task_contract.get("source_request", raw_request),
            (
                "High-risk broad scope request requires explicit redesign support; "
                "escalating instead of bounded iteration execution."
            ),
        )
        _write_json(run_audit_dir / "approval_record.json", blocked_result)
        print("\n=== APPROVAL RECORD ===")
        print(json.dumps(blocked_result, indent=2))
        return

    validate_task_contract_grounding(task_contract)

    scope_conflicts = detect_scope_conflicts(task_contract)
    if scope_conflicts:
        blocked_result = _build_blocked_intake_result(
            task_contract.get("source_request", raw_request),
            "Scope contradiction detected: " + " ".join(scope_conflicts),
        )
        _write_json(run_audit_dir / "approval_record.json", blocked_result)
        print("\n=== APPROVAL RECORD ===")
        print(json.dumps(blocked_result, indent=2))
        return

    delegation_brief, raw_delegation_output = run_delegation(task_contract)
    (run_audit_dir / "raw_delegation_output.txt").write_text(
        raw_delegation_output,
        encoding="utf-8",
    )
    _write_json(run_audit_dir / "delegation_brief.json", delegation_brief)
    print("\n=== DELEGATION BRIEF ===")
    print(json.dumps(delegation_brief, indent=2))

    specialist_output = run_specialist(delegation_brief)
    (run_audit_dir / "specialist_output.txt").write_text(
        specialist_output,
        encoding="utf-8",
    )
    print("\n=== SPECIALIST OUTPUT ===")
    print(specialist_output)

    grounded_paths = resolve_allowed_paths(task_contract)
    current_objects = load_current_objects()
    task_contract["current_objects"] = current_objects
    delegation_brief["current_objects"] = current_objects
    print("DEBUG current_objects keys:", json.dumps(list(current_objects.keys())))
    print("DEBUG current_objects sample:", current_objects)
    has_grounding_match, matched_object_paths, matched_grounding_candidates = evaluate_object_grounding(
        task_contract,
        delegation_brief,
        grounded_paths,
        current_objects,
    )

    if not has_grounding_match:
        approval_record = normalize_approval_record(
            task_contract,
            delegation_brief,
            {
                "decision": "escalate",
                "decision_reason": (
                    "No grounded object match found in allowed_paths/current_objects for "
                    "requested change."
                ),
                "next_action": "Hold handoff until Exec resolves review outcome.",
            },
        )
    else:
        approval_record = run_review(task_contract, delegation_brief, specialist_output)
        pre_approval_conflicts = detect_scope_conflicts(task_contract)
        if approval_record.get("decision") == "approve" and pre_approval_conflicts:
            approval_record["decision"] = "escalate"
            approval_record["decision_reason"] = (
                "Pre-approval contradiction check failed: "
                + " ".join(pre_approval_conflicts)
            )
            approval_record["next_action"] = "Hold handoff until Exec resolves review outcome."
            approval_record["approved_execution_package_ref"] = ""
        if approval_record.get("decision") == "approve":
            final_allowed_paths = grounded_paths
            if not final_allowed_paths:
                final_allowed_paths = list(dict.fromkeys(matched_object_paths))
                if final_allowed_paths:
                    print("allowed_paths inferred from object grounding")
            if not final_allowed_paths:
                approval_record["decision"] = "escalate"
                approval_record["decision_reason"] = (
                    "Grounded object match found, but no concrete matched file paths were "
                    "available for bounded execution."
                )
                approval_record["next_action"] = "Hold handoff until Exec resolves review outcome."
                approval_record["approved_execution_package_ref"] = ""
            else:
                task_contract.setdefault("tool_policy", {})["allowed_paths"] = final_allowed_paths
                delegation_brief.setdefault("tool_policy", {})["allowed_paths"] = final_allowed_paths

    _write_json(run_audit_dir / "approval_record.json", approval_record)
    print("\n=== APPROVAL RECORD ===")
    print(json.dumps(approval_record, indent=2))

    if approval_record.get("decision") == "approve":
        execution_package = build_execution_package(
            task_contract,
            delegation_brief,
            approval_record,
            specialist_output,
            matched_grounding_candidates=matched_grounding_candidates,
        )
        _write_json(run_audit_dir / "execution_package.json", execution_package)
        print("\n=== EXECUTION PACKAGE ===")
        print(json.dumps(execution_package, indent=2))


if __name__ == "__main__":
    main()
