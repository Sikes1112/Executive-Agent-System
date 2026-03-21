from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def require_fields(obj: dict[str, Any], fields: list[str], label: str) -> None:
    missing = [f for f in fields if f not in obj]
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def stable_json_hash(data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalize_target_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/").lstrip("/")
    workspace_prefix = "workspace-example/"
    if normalized.startswith(workspace_prefix):
        normalized = normalized[len(workspace_prefix) :]
    bundles_prefix = "bundles/"
    idx = normalized.find(bundles_prefix)
    if idx >= 0:
        normalized = normalized[idx:]
    elif normalized and not normalized.startswith(bundles_prefix):
        normalized = f"{bundles_prefix}{normalized}"
    return normalized


def derive_mutation_notes(
    objective: str,
    target_paths: list[str],
    approved_output: Any,
) -> list[str]:
    notes: list[str] = [
        "Apply concrete edits only to: " + ", ".join(target_paths),
        "Use current_objects as baseline and return full-object JSON patches for changed targets.",
    ]

    text = approved_output if isinstance(approved_output, str) else json.dumps(approved_output)
    for raw in text.splitlines():
        line = raw.strip().lstrip("- ").strip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if (
            "revised:" in lower
            or lower.startswith(("replace ", "update ", "change ", "set ", "add ", "increase ", "enhance ", "bold "))
        ):
            if line not in notes:
                notes.append(line)
        if len(notes) >= 8:
            break

    if len(notes) <= 2:
        notes.append(f"Mutation objective: {objective}")
    return notes


def _normalize_grounding_candidate(candidate: str) -> str:
    lowered = candidate.lower().replace("_", " ")
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in lowered)
    return " ".join(cleaned.split())


def _candidate_matches_text(candidate: str, text: str) -> bool:
    normalized_candidate = _normalize_grounding_candidate(candidate)
    normalized_text = _normalize_grounding_candidate(text)
    if not normalized_candidate or not normalized_text:
        return False
    if normalized_candidate in normalized_text or normalized_text in normalized_candidate:
        return True
    candidate_tokens = set(normalized_candidate.split())
    text_tokens = set(normalized_text.split())
    if not candidate_tokens or not text_tokens:
        return False
    overlap = candidate_tokens.intersection(text_tokens)
    return len(overlap) >= min(2, len(candidate_tokens), len(text_tokens))


def derive_mutation_targets(
    execution_package: dict[str, Any],
    target_paths: list[str],
) -> list[dict[str, Any]]:
    grounding = execution_package.get("grounding") if isinstance(execution_package, dict) else {}
    matched_raw = grounding.get("matched_candidates") if isinstance(grounding, dict) else []
    matched_candidates = matched_raw if isinstance(matched_raw, list) else []
    matched_pairs: list[tuple[str, str, int, str]] = []

    for item in matched_candidates:
        if not isinstance(item, dict):
            continue
        file_path = item.get("file")
        candidate = item.get("candidate")
        score = item.get("score", 0)
        tier = item.get("tier", "")
        if not isinstance(file_path, str) or not isinstance(candidate, str):
            continue
        if not isinstance(score, (int, float)):
            score = 0
        if not isinstance(tier, str):
            tier = ""
        normalized_path = normalize_target_path(file_path)
        normalized_candidate = _normalize_grounding_candidate(candidate)
        if normalized_path and normalized_candidate:
            matched_pairs.append((normalized_path, normalized_candidate, int(score), tier.lower().strip()))

    if not matched_pairs:
        return []

    path_set = set(target_paths)
    script_dir = Path(__file__).resolve().parent
    workspace_root = Path(
        os.environ.get("WORKSPACE_ROOT", str(script_dir.parent))
    ).expanduser().resolve()

    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    primary_candidates = [
        (file_path, candidate)
        for file_path, candidate, score, tier in matched_pairs
        if score >= 2 and tier == "primary"
    ]
    print("PRIMARY targets:", [candidate for _, candidate in primary_candidates])

    for file_path, candidate in primary_candidates:
        if file_path not in path_set:
            continue

        bundle_path = workspace_root / "workspace-example" / file_path
        if not bundle_path.exists() or bundle_path.suffix.lower() != ".json":
            continue

        try:
            payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if file_path.endswith("ui_spec/screens.json"):
            fields = ["title"]
            for screen in payload.get("screens", []) if isinstance(payload, dict) else []:
                if not isinstance(screen, dict):
                    continue
                object_id = screen.get("id")
                if not isinstance(object_id, str):
                    continue
                if not _candidate_matches_text(candidate, object_id):
                    continue
                key = (file_path, object_id)
                if key in seen:
                    continue
                seen.add(key)
                targets.append(
                    {
                        "file": file_path,
                        "object_id": object_id,
                        "fields": fields,
                    }
                )

        if file_path.endswith("ui_spec/components.json"):
            fields = ["purpose", "props"]
            for component in payload.get("components", []) if isinstance(payload, dict) else []:
                if not isinstance(component, dict):
                    continue
                object_id = component.get("id")
                purpose = component.get("purpose")
                if not isinstance(object_id, str):
                    continue
                matches = _candidate_matches_text(candidate, object_id)
                if isinstance(purpose, str):
                    matches = matches or _candidate_matches_text(candidate, purpose)
                if not matches:
                    continue
                key = (file_path, object_id)
                if key in seen:
                    continue
                seen.add(key)
                targets.append(
                    {
                        "file": file_path,
                        "object_id": object_id,
                        "fields": fields,
                    }
                )

    filtered_targets = targets[:2]
    print("FILTERED targets:", [target.get("object_id") for target in filtered_targets])
    return filtered_targets


def build_workspace_exec_envelope(
    execution_package: dict[str, Any],
    approval_record: dict[str, Any],
) -> dict[str, Any]:
    require_fields(
        execution_package,
        [
            "task_id",
            "delegation_id",
            "approval_id",
            "approved_scope",
            "approved_output",
            "next_action",
        ],
        "execution_package",
    )
    require_fields(
        approval_record,
        [
            "approval_id",
            "task_id",
            "delegation_id",
            "decision",
            "decision_reason",
            "created_at",
        ],
        "approval_record",
    )

    if approval_record["decision"] != "approve":
        raise ValueError("Cannot create workspace-exec envelope from non-approved run.")

    if approval_record["approval_id"] != execution_package["approval_id"]:
        raise ValueError("approval_id mismatch between approval_record and execution_package.")

    approved_scope = execution_package["approved_scope"]
    require_fields(
        approved_scope,
        ["objective", "constraints", "non_goals", "tool_policy"],
        "approved_scope",
    )

    tool_policy = approved_scope["tool_policy"]
    require_fields(
        tool_policy,
        [
            "allowed_tools",
            "disallowed_tools",
            "internet",
            "file_mutation",
            "allowed_paths",
            "background_execution",
        ],
        "approved_tool_policy",
    )

    target_paths = tool_policy.get("allowed_paths", [])
    if not isinstance(target_paths, list):
        raise ValueError("approved_scope.tool_policy.allowed_paths must be an array.")

    normalized_target_paths: list[str] = []
    for p in target_paths:
        if not isinstance(p, str) or not p.strip():
            raise ValueError("approved_scope.tool_policy.allowed_paths entries must be non-empty strings.")
        normalized_target_paths.append(normalize_target_path(p))

    if len(target_paths) == 0:
        raise ValueError(
            "Cannot create workspace-exec envelope: allowed_paths is empty. "
            "Exec must approve concrete target paths before handoff."
        )

    task_id = execution_package["task_id"]
    ticket_id = f"{task_id}-t1"
    mutation_notes = derive_mutation_notes(
        objective=approved_scope["objective"],
        target_paths=normalized_target_paths,
        approved_output=execution_package["approved_output"],
    )
    mutation_targets = derive_mutation_targets(
        execution_package=execution_package,
        target_paths=normalized_target_paths,
    )

    ticket = {
        "ticket_id": ticket_id,
        "domain": "iteration",
        "intent_summary": approved_scope["objective"],
        "patch_scope": "wide",
        "target_paths": normalized_target_paths,
        "risk_level": "medium",
        "depends_on": [],
        "notes": mutation_notes,
        "mutation_targets": mutation_targets,
    }

    envelope = {
        "batch_id": f"batch-{task_id}",
        "origin_input_hash": stable_json_hash(execution_package),
        "created_at": approval_record["created_at"],
        "tickets": [ticket],
    }

    return envelope


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "usage: python3 core/exec_to_workspace_exec.py /path/to/execution_package.json",
            file=sys.stderr,
        )
        sys.exit(1)

    execution_package_path = Path(sys.argv[1]).resolve()
    run_dir = execution_package_path.parent

    approval_record_path = run_dir / "approval_record.json"
    output_envelope_path = run_dir / "workspace_exec_envelope.json"

    execution_package = read_json(execution_package_path)
    approval_record = read_json(approval_record_path)

    envelope = build_workspace_exec_envelope(execution_package, approval_record)
    write_json(output_envelope_path, envelope)

    print(f"WORKSPACE_EXEC_ENVELOPE={output_envelope_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
