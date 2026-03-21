from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"


def _load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def get_adapter(domain: str | None) -> dict[str, Any]:
    registry = _load_registry()
    default_domain = str(registry.get("default", "iteration"))
    adapters = registry.get("adapters", {})

    key = (domain or "").strip() or default_domain
    if key not in adapters:
        key = default_domain

    adapter = adapters.get(key)
    if not isinstance(adapter, dict):
        raise ValueError(f"Adapter definition not found for domain: {key}")

    return adapter


def get_result_handling(domain: str | None) -> dict[str, Any]:
    adapter = get_adapter(domain)
    mode = str(adapter.get("mode", "mutation"))
    raw = adapter.get("result_handling")
    if isinstance(raw, dict):
        return {
            "result_mode": str(raw.get("result_mode", mode)),
            "sanitize_apply_supported": bool(raw.get("sanitize_apply_supported", False)),
        }

    return {
        "result_mode": mode,
        "sanitize_apply_supported": mode == "mutation",
    }


def get_result_contract_metadata(domain: str | None) -> dict[str, Any] | None:
    adapter = get_adapter(domain)
    raw = adapter.get("result_handling")
    if not isinstance(raw, dict):
        return None

    contract = raw.get("normalized_result_contract")
    if not isinstance(contract, dict):
        return None

    return contract
