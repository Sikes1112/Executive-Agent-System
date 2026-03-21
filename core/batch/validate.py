#!/usr/bin/env python3
"""
helper_batch_validate.py
Validates Helper Ticket Batch Envelope and enforces guardrails:
- schema presence (batch + tickets)
- MAX_TICKETS_PER_BATCH
- unique ticket_id
- depends_on references valid IDs
- DAG only (no cycles)
- emits topological order
- writes audit log record
Exit codes:
  0 = PASS
  2 = FAIL (validation)
"""
from __future__ import annotations

import json
import os
import sys
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


MAX_TICKETS_PER_BATCH = 20
SUPPORTED_DOMAINS = {"iteration", "outreach", "reputationops"}


def _fail(msg: str, details: Dict[str, Any] | None = None) -> None:
    payload = {"ok": False, "error": msg}
    if details:
        payload["details"] = details
    print(json.dumps(payload, indent=2))
    raise SystemExit(2)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception as e:
        _fail("invalid_json", {"path": str(path), "exception": str(e)})


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _toposort(nodes: List[str], edges: Dict[str, List[str]]) -> Tuple[List[str], List[str]]:
    """
    edges: node -> list of deps (incoming edges)
    returns (order, cycle_nodes_if_any)
    """
    temp = set()
    perm = set()
    order: List[str] = []
    cycle: List[str] = []

    def visit(n: str) -> None:
        nonlocal cycle
        if n in perm:
            return
        if n in temp:
            cycle = [n]
            return
        temp.add(n)
        for d in edges.get(n, []):
            visit(d)
            if cycle:
                return
        temp.remove(n)
        perm.add(n)
        order.append(n)

    for n in nodes:
        if n not in perm:
            visit(n)
            if cycle:
                break

    return (order, cycle)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: validate.py <helper_batch.json>", file=sys.stderr)
        raise SystemExit(2)

    in_path = Path(sys.argv[1]).expanduser().resolve()
    data = _load_json(in_path)
    script_dir = Path(__file__).resolve().parent
    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", str(script_dir.parents[2]))).expanduser().resolve()
    audit_root = Path(os.environ.get("AUDIT_ROOT", str(workspace_root / "audit"))).expanduser().resolve()

    # --- batch schema ---
    if not isinstance(data, dict):
        _fail("batch_not_object", {"type": type(data).__name__})

    required_batch = ["batch_id", "origin_input_hash", "created_at", "tickets"]
    missing_batch = [k for k in required_batch if k not in data]
    if missing_batch:
        _fail("missing_batch_fields", {"missing": missing_batch})

    batch_id = data["batch_id"]
    origin_input_hash = data["origin_input_hash"]
    created_at = data["created_at"]
    tickets = data["tickets"]

    if not isinstance(batch_id, str) or not batch_id.strip():
        _fail("invalid_batch_id")
    if not isinstance(origin_input_hash, str) or len(origin_input_hash) < 32:
        _fail("invalid_origin_input_hash")
    if not isinstance(created_at, str) or not created_at.strip():
        _fail("invalid_created_at")
    if not isinstance(tickets, list):
        _fail("tickets_not_array", {"type": type(tickets).__name__})

    # --- batch guardrails ---
    if len(tickets) == 0:
        _fail("empty_tickets")
    if len(tickets) > MAX_TICKETS_PER_BATCH:
        _fail("too_many_tickets", {"count": len(tickets), "max": MAX_TICKETS_PER_BATCH})

    required_ticket = [
        "ticket_id", "intent_summary", "patch_scope", "target_paths",
        "risk_level", "depends_on"
    ]

    seen_ids: set[str] = set()
    id_list: List[str] = []
    deps_map: Dict[str, List[str]] = {}
    high_risk: List[str] = []

    for i, t in enumerate(tickets):
        if not isinstance(t, dict):
            _fail("ticket_not_object", {"index": i, "type": type(t).__name__})
        missing_t = [k for k in required_ticket if k not in t]
        if missing_t:
            _fail("missing_ticket_fields", {"index": i, "missing": missing_t})

        tid = t["ticket_id"]
        if not isinstance(tid, str) or not tid.strip():
            _fail("invalid_ticket_id", {"index": i})
        if tid in seen_ids:
            _fail("duplicate_ticket_id", {"ticket_id": tid})
        seen_ids.add(tid)
        id_list.append(tid)

        # minimal field checks
        if not isinstance(t["intent_summary"], str) or not t["intent_summary"].strip():
            _fail("invalid_intent_summary", {"ticket_id": tid})
        if t["patch_scope"] not in ("narrow", "medium", "wide"):
            _fail("invalid_patch_scope", {"ticket_id": tid, "patch_scope": t["patch_scope"]})
        if t["risk_level"] not in ("low", "medium", "high"):
            _fail("invalid_risk_level", {"ticket_id": tid, "risk_level": t["risk_level"]})
        if t["risk_level"] == "high":
            high_risk.append(tid)

        target_paths = t["target_paths"]
        if not isinstance(target_paths, list) or not all(isinstance(p, str) and p for p in target_paths):
            _fail("invalid_target_paths", {"ticket_id": tid})

        depends_on = t["depends_on"]
        if not isinstance(depends_on, list) or not all(isinstance(d, str) and d for d in depends_on):
            _fail("invalid_depends_on", {"ticket_id": tid})
        deps_map[tid] = depends_on

        if "domain" in t:
            domain = t["domain"]
            if not isinstance(domain, str) or domain not in SUPPORTED_DOMAINS:
                _fail("invalid_domain", {"ticket_id": tid, "domain": domain, "supported": sorted(SUPPORTED_DOMAINS)})

    # --- dependency reference validation ---
    unknown_deps: Dict[str, List[str]] = {}
    all_ids = set(id_list)
    for tid, deps in deps_map.items():
        bad = [d for d in deps if d not in all_ids]
        if bad:
            unknown_deps[tid] = bad
    if unknown_deps:
        _fail("unknown_depends_on_ids", {"unknown": unknown_deps})

    # --- DAG validation + toposort ---
    order, cycle = _toposort(id_list, deps_map)
    if cycle:
        _fail("dependency_cycle_detected", {"cycle_hint": cycle})

    # order currently lists deps before dependents due to DFS append; reverse to get exec order
    exec_order = order

    # --- audit log ---
    now = datetime.now(timezone.utc).isoformat()
    audit_dir = audit_root / "helper_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    raw = in_path.read_text()
    audit_id = _sha256_text(raw)[:16]
    audit_path = audit_dir / f"{now.replace(':','').replace('.','')}_{audit_id}.json"

    audit = {
        "ok": True,
        "validated_at": now,
        "input_path": str(in_path),
        "batch_id": batch_id,
        "origin_input_hash": origin_input_hash,
        "created_at": created_at,
        "ticket_count": len(tickets),
        "high_risk_tickets": high_risk,
        "exec_order": exec_order,
        "notes": {
            "max_tickets_per_batch": MAX_TICKETS_PER_BATCH,
            "requires_operator_approval_if_high_risk": bool(high_risk),
        },
    }
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")

    # --- output ---
    out = {
        "ok": True,
        "batch_id": batch_id,
        "ticket_count": len(tickets),
        "high_risk_tickets": high_risk,
        "exec_order": exec_order,
        "audit_log": str(audit_path),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
