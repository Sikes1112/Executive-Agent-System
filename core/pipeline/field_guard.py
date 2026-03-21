#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HARD_DISALLOWED_TOP_LEVEL_FIELDS = {"layout", "style"}
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "domain_adapters" / "registry.json"


def _index_targets(ticket: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = {}
    raw_targets = ticket.get("mutation_targets")
    if not isinstance(raw_targets, list):
        return out

    for target in raw_targets:
        if not isinstance(target, dict):
            continue
        file_path = target.get("file")
        object_id = target.get("object_id")
        fields = target.get("fields")
        if not isinstance(file_path, str) or not isinstance(object_id, str):
            continue
        allowed = set()
        if isinstance(fields, list):
            allowed = {f for f in fields if isinstance(f, str)}
        out.setdefault(file_path, {})[object_id] = allowed
    return out


def _find_object_by_id(payload: dict[str, Any], object_id: str) -> dict[str, Any] | None:
    for value in payload.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict) and item.get("id") == object_id:
                return item
    return None


def _enforce_on_object(
    obj: dict[str, Any],
    baseline_obj: dict[str, Any] | None,
    allowed_fields: set[str],
) -> None:
    keys = list(obj.keys())
    for field_name in keys:
        if field_name == "id":
            continue
        if field_name in HARD_DISALLOWED_TOP_LEVEL_FIELDS:
            print("REMOVED FIELD:", field_name)
            obj.pop(field_name, None)
            continue
        if field_name in allowed_fields:
            continue
        print("REMOVED FIELD:", field_name)
        obj.pop(field_name, None)


def _resolve_guard_behavior(ticket: dict[str, Any], domain_override: str | None) -> str:
    if not isinstance(ticket, dict):
        raise ValueError("invalid_ticket_type")

    if domain_override is not None:
        domain_raw: Any = domain_override
    else:
        domain_raw = ticket.get("domain")

    if domain_raw is None:
        domain = "iteration"
    elif not isinstance(domain_raw, str):
        raise ValueError("invalid_domain_type")
    else:
        domain = domain_raw.strip() or "iteration"

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    adapters = registry.get("adapters")
    if not isinstance(adapters, dict):
        raise ValueError("invalid_adapter_registry")
    if domain not in adapters:
        raise ValueError(f"unknown_domain:{domain}")

    adapter = adapters.get(domain)
    if not isinstance(adapter, dict):
        raise ValueError(f"invalid_adapter:{domain}")
    guard_behavior = adapter.get("guard_behavior")
    if not isinstance(guard_behavior, str) or not guard_behavior.strip():
        raise ValueError(f"invalid_guard_behavior:{domain}")
    return guard_behavior.strip()


def enforce_field_guards(
    normalized: dict[str, Any],
    ticket: dict[str, Any],
    domain_override: str | None = None,
) -> dict[str, Any]:
    guard_behavior = _resolve_guard_behavior(ticket, domain_override)
    if guard_behavior == "passthrough":
        return normalized
    if guard_behavior != "iteration":
        raise ValueError(f"unsupported_guard_behavior:{guard_behavior}")

    targets_by_file = _index_targets(ticket)
    if not targets_by_file:
        return normalized

    current_objects = ticket.get("current_objects")
    if not isinstance(current_objects, dict):
        current_objects = {}

    bundles = normalized.get("bundles")
    if not isinstance(bundles, list):
        return normalized

    for bundle in bundles:
        if not isinstance(bundle, dict):
            continue
        file_path = bundle.get("path")
        patch = bundle.get("patch")
        if not isinstance(file_path, str) or not isinstance(patch, dict):
            continue
        file_targets = targets_by_file.get(file_path)
        if not file_targets:
            continue

        baseline_root = current_objects.get(file_path)
        baseline_root = baseline_root if isinstance(baseline_root, dict) else {}

        for value in patch.values():
            if not isinstance(value, list):
                continue
            for item in value:
                if not isinstance(item, dict):
                    continue
                object_id = item.get("id")
                if not isinstance(object_id, str):
                    continue
                allowed_fields = file_targets.get(object_id)
                if allowed_fields is None:
                    continue
                baseline_obj = _find_object_by_id(baseline_root, object_id)
                _enforce_on_object(item, baseline_obj, allowed_fields)

    return normalized


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalized", required=True)
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--domain", required=False)
    args = ap.parse_args()

    normalized_path = Path(args.normalized)
    ticket_path = Path(args.ticket)

    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))

    try:
        guarded = enforce_field_guards(normalized, ticket, domain_override=args.domain)
    except ValueError as e:
        print(f"FIELD_GUARD_FAIL {e}", file=sys.stderr)
        raise SystemExit(2)
    normalized_path.write_text(json.dumps(guarded, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
