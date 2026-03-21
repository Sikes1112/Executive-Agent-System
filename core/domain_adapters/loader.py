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
