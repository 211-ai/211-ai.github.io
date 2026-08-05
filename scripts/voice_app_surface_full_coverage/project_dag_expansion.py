#!/usr/bin/env python3
"""Project v2 variant lattices into DAG expansion packs + edge sidecar (VAS2-018).

Reads ``data/voice_app_surface_full_coverage/variants/{p0,p1}/*.jsonl`` and
writes:
  - per-surface exemplar packs under ``.../dag_expansion/``
  - ``docs/phone_dialog_generation/surface_expansion_edges_v2.jsonl``
  - projection manifest under reports/

Usage:
  python scripts/voice_app_surface_full_coverage/project_dag_expansion.py --write
  python scripts/voice_app_surface_full_coverage/project_dag_expansion.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANTS_ROOT = (
    REPO_ROOT / "data" / "voice_app_surface_full_coverage" / "variants"
)
EXPANSION_DIR = (
    REPO_ROOT / "data" / "voice_app_surface_full_coverage" / "dag_expansion"
)
OUT_EDGES = (
    REPO_ROOT
    / "docs"
    / "phone_dialog_generation"
    / "surface_expansion_edges_v2.jsonl"
)
OUT_MANIFEST = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_full_coverage"
    / "reports"
    / "dag-expansion-projection-manifest.json"
)
PROGRAM_ID = "voice-app-surface-full-coverage-v2"
SCHEMA_EDGE = "voice-app-surface-full-coverage/projected-dag-edge@1"
SCHEMA_MANIFEST = "voice-app-surface-full-coverage/dag-expansion-projection@1"
P0_SURFACES = (
    "home",
    "check-in",
    "calendar",
    "messages",
    "contacts",
    "social-services",
    "interactions",
    "uploads",
    "settings",
)
MIN_EDGES_PER_P0_SURFACE = 500

ASSISTANT_TEMPLATES: dict[str, str] = {
    "open_app_surface": "I can open the {surface} screen after you confirm.",
    "read_calendar": "I can read your calendar after you confirm.",
    "create_calendar_reminder": "I can create a calendar reminder after you confirm.",
    "read_provider_messages": "I can read your provider messages after you confirm.",
    "leave_provider_message": "I can leave a message for the provider after you confirm.",
    "open_wallet_documents": "I can open your wallet documents after you confirm.",
    "open_service_detail": "I can open service details after you confirm.",
    "schedule_service_callback": "I can schedule a service callback after you confirm.",
    "no_action": "I can share that information without changing any app screens.",
}

ROUTE_FOR_ACTION: dict[str, str] = {
    "open_app_surface": "app_surface_navigation",
    "read_calendar": "calendar_event_support",
    "create_calendar_reminder": "calendar_event_support",
    "read_provider_messages": "provider_contact_support",
    "leave_provider_message": "provider_contact_support",
    "open_wallet_documents": "wallet_document_support",
    "open_service_detail": "grounded_211_answer",
    "schedule_service_callback": "service_interaction_support",
    "no_action": "template_guided_fallback",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _edge_id(route: str, user: str, surface_id: str) -> str:
    digest = hashlib.sha256(
        f"v2|{route}|{surface_id}|{user}".encode("utf-8")
    ).hexdigest()[:20]
    return f"edge-vas2-{digest}"


def _ex_id(surface_id: str, user: str) -> str:
    digest = hashlib.sha256(f"{surface_id}|{user}".encode()).hexdigest()[:16]
    return f"var2-{digest}"


def _assistant(logical_action: str, surface_id: str) -> str:
    tmpl = ASSISTANT_TEMPLATES.get(
        logical_action, "I can help with that after you confirm."
    )
    return tmpl.format(surface=surface_id.replace("-", " "))


def load_variants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tier in ("p0", "p1"):
        d = VARIANTS_ROOT / tier
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                row["_tier"] = tier.upper()
                rows.append(row)
    return rows


def to_exemplars(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exemplars: list[dict[str, Any]] = []
    for v in variants:
        if v.get("negative"):
            continue
        user = str(v.get("user_text") or "").strip()
        if not user:
            continue
        surface_id = str(v.get("surface_id") or "").strip()
        logical = str(v.get("logical_action") or "open_app_surface").strip()
        route = str(v.get("expected_route") or ROUTE_FOR_ACTION.get(logical) or "").strip()
        if not route:
            continue
        exemplars.append(
            {
                "id": v.get("variant_id") or _ex_id(surface_id, user),
                "user": user,
                "assistant": _assistant(logical, surface_id),
                "route": route,
                "surface_id": surface_id,
                "logical_action": logical,
                "priority": v.get("priority") or v.get("_tier"),
                "axes": v.get("axes") or [],
                "program_id": PROGRAM_ID,
            }
        )
    return exemplars


def write_expansion_packs(exemplars: list[dict[str, Any]]) -> dict[str, int]:
    EXPANSION_DIR.mkdir(parents=True, exist_ok=True)
    by_surface: dict[str, list[dict[str, Any]]] = {}
    for ex in exemplars:
        sid = str(ex.get("surface_id") or "unknown")
        by_surface.setdefault(sid, []).append(ex)
    counts: dict[str, int] = {}
    for sid, rows in sorted(by_surface.items()):
        path = EXPANSION_DIR / f"{sid}.exemplars.jsonl"
        path.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8",
        )
        counts[sid] = len(rows)
    return counts


def project_edges(exemplars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ex in exemplars:
        user = str(ex.get("user") or "").strip()
        assistant = str(ex.get("assistant") or "").strip()
        route = str(ex.get("route") or "").strip()
        surface_id = str(ex.get("surface_id") or "").strip()
        if not user or not route:
            continue
        key = f"{route}|{surface_id}|{user.lower()}"
        if key in seen:
            continue
        seen.add(key)
        edge_id = _edge_id(route, user, surface_id)
        edges.append(
            {
                "schema": SCHEMA_EDGE,
                "id": edge_id,
                "type": "intent_to_response_frame",
                "route": route,
                "surface_id": surface_id or None,
                "logical_action": ex.get("logical_action"),
                "program_id": PROGRAM_ID,
                "source": "vas2_dag_expansion_projection",
                "examples": [
                    {
                        "recordId": ex.get("id") or edge_id,
                        "user": user,
                        "assistant": assistant
                        or "I can help with that after you confirm.",
                    }
                ],
                "reuseCount": 1,
                "reusable": False,
                "projection_note": (
                    "VAS2 sidecar edge for fold into slotted_response_dag.json."
                ),
            }
        )
    edges.sort(key=lambda e: (e.get("route") or "", e.get("surface_id") or "", e["id"]))
    return edges


def build_manifest(edges: list[dict[str, Any]], *, pack_counts: dict[str, int]) -> dict[str, Any]:
    by_surface: dict[str, int] = {}
    by_route: dict[str, int] = {}
    for edge in edges:
        sid = str(edge.get("surface_id") or "unknown")
        route = str(edge.get("route") or "unknown")
        by_surface[sid] = by_surface.get(sid, 0) + 1
        by_route[route] = by_route.get(route, 0) + 1
    p0_ok = {
        sid: by_surface.get(sid, 0) >= MIN_EDGES_PER_P0_SURFACE for sid in P0_SURFACES
    }
    return {
        "schema": SCHEMA_MANIFEST,
        "program_id": PROGRAM_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "expansion_dir": str(EXPANSION_DIR.relative_to(REPO_ROOT)),
        "edges_path": str(OUT_EDGES.relative_to(REPO_ROOT)),
        "edge_count": len(edges),
        "pack_counts": dict(sorted(pack_counts.items())),
        "by_surface": dict(sorted(by_surface.items())),
        "by_route": dict(sorted(by_route.items())),
        "p0_surface_floors": {
            "minimum": MIN_EDGES_PER_P0_SURFACE,
            "met": p0_ok,
            "all_met": all(p0_ok.values()),
        },
        "edges_digest": _sha256_file(OUT_EDGES) if OUT_EDGES.is_file() else None,
        "full_dag_merge": {
            "status": "not_applied",
            "target": "docs/phone_dialog_generation/slotted_response_dag.json",
            "operator_command": (
                "python scripts/voice_app_surface_full_coverage/fold_surface_expansion_into_dag.py --write"
            ),
        },
    }


def write_projection() -> dict[str, Any]:
    variants = load_variants()
    exemplars = to_exemplars(variants)
    pack_counts = write_expansion_packs(exemplars)
    edges = project_edges(exemplars)
    OUT_EDGES.parent.mkdir(parents=True, exist_ok=True)
    OUT_EDGES.write_text(
        "".join(json.dumps(edge, sort_keys=True) + "\n" for edge in edges),
        encoding="utf-8",
    )
    manifest = build_manifest(edges, pack_counts=pack_counts)
    manifest["edges_digest"] = _sha256_file(OUT_EDGES)
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def check_projection() -> list[str]:
    errors: list[str] = []
    if not OUT_EDGES.is_file():
        return [f"missing projected edges {OUT_EDGES}"]
    if not OUT_MANIFEST.is_file():
        return [f"missing manifest {OUT_MANIFEST}"]
    manifest = json.loads(OUT_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA_MANIFEST:
        errors.append("manifest schema mismatch")
    if not manifest.get("p0_surface_floors", {}).get("all_met"):
        errors.append(
            f"P0 floors not met: {manifest.get('p0_surface_floors', {}).get('met')}"
        )
    n = sum(
        1
        for line in OUT_EDGES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if n != manifest.get("edge_count"):
        errors.append(
            f"edge_count mismatch file={n} manifest={manifest.get('edge_count')}"
        )
    if n < MIN_EDGES_PER_P0_SURFACE * 5:
        errors.append(f"too few projected edges: {n}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write or not args.check:
        manifest = write_projection()
        print(
            json.dumps(
                {
                    "wrote_edges": str(OUT_EDGES.relative_to(REPO_ROOT)),
                    "edge_count": manifest["edge_count"],
                    "p0_all_met": manifest["p0_surface_floors"]["all_met"],
                    "by_surface": manifest["by_surface"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    if args.check:
        errors = check_projection()
        if errors:
            print("dag expansion projection FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("dag expansion projection OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
