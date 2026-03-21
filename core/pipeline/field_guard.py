#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HARD_DISALLOWED_TOP_LEVEL_FIELDS = {"layout", "style"}


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


def enforce_field_guards(normalized: dict[str, Any], ticket: dict[str, Any]) -> dict[str, Any]:
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
    args = ap.parse_args()

    normalized_path = Path(args.normalized)
    ticket_path = Path(args.ticket)

    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))

    guarded = enforce_field_guards(normalized, ticket)
    normalized_path.write_text(json.dumps(guarded, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
