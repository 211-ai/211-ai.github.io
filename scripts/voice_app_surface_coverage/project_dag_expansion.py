#!/usr/bin/env python3
"""Project surface expansion packs into DAG-compatible edge records (residual).

Does **not** rewrite the multi-MB ``slotted_response_dag.json`` by default.
Produces a sidecar edge JSONL + manifest that a future offline DAG rebuild
can absorb with a single deterministic merge step.

Usage:
  python scripts/voice_app_surface_coverage/project_dag_expansion.py --write
  python scripts/voice_app_surface_coverage/project_dag_expansion.py --check
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
EXPANSION_DIR = (
    REPO_ROOT / "data" / "voice_app_surface_coverage" / "dag_expansion"
)
OUT_EDGES = (
    REPO_ROOT
    / "docs"
    / "phone_dialog_generation"
    / "surface_expansion_edges.jsonl"
)
OUT_MANIFEST = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "reports"
    / "dag-expansion-projection-manifest.json"
)
PROGRAM_ID = "voice-app-surface-coverage-v1"
SCHEMA_EDGE = "voice-app-surface-coverage/projected-dag-edge@1"
SCHEMA_MANIFEST = "voice-app-surface-coverage/dag-expansion-projection@1"
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
MIN_EDGES_PER_P0_SURFACE = 200


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _edge_id(route: str, user: str, surface_id: str) -> str:
    digest = hashlib.sha256(
        f"{route}|{surface_id}|{user}".encode("utf-8")
    ).hexdigest()[:20]
    return f"edge-vas-{digest}"


def _load_exemplars() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not EXPANSION_DIR.is_dir():
        return rows
    for path in sorted(EXPANSION_DIR.glob("*.exemplars.jsonl")):
        # Prefer surface files; route-* packs are aggregates.
        if path.name.startswith("route-"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


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
                "source": "vas_dag_expansion_projection",
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
                    "Sidecar edge for offline rebuild; not yet folded into "
                    "slotted_response_dag.json."
                ),
            }
        )
    edges.sort(key=lambda e: (e.get("route") or "", e.get("surface_id") or "", e["id"]))
    return edges


def build_manifest(
    edges: list[dict[str, Any]],
    *,
    edges_path: Path,
) -> dict[str, Any]:
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
        "edges_path": str(edges_path.relative_to(REPO_ROOT)),
        "edge_count": len(edges),
        "by_surface": dict(sorted(by_surface.items())),
        "by_route": dict(sorted(by_route.items())),
        "p0_surface_floors": {
            "minimum": MIN_EDGES_PER_P0_SURFACE,
            "met": p0_ok,
            "all_met": all(p0_ok.values()),
        },
        "edges_digest": _sha256_file(edges_path) if edges_path.is_file() else None,
        "full_dag_merge": {
            "status": "not_applied",
            "target": "docs/phone_dialog_generation/slotted_response_dag.json",
            "operator_command": (
                "python scripts/voice_app_surface_coverage/project_dag_expansion.py "
                "--write && # then offline rebuild tooling absorbs surface_expansion_edges.jsonl"
            ),
            "note": (
                "Full DAG rewrite remains operator-gated due to 67MB artifact size "
                "and GraphRAG rebuild cost."
            ),
        },
    }


def write_projection() -> dict[str, Any]:
    exemplars = _load_exemplars()
    edges = project_edges(exemplars)
    OUT_EDGES.parent.mkdir(parents=True, exist_ok=True)
    OUT_EDGES.write_text(
        "".join(json.dumps(edge, sort_keys=True) + "\n" for edge in edges),
        encoding="utf-8",
    )
    manifest = build_manifest(edges, edges_path=OUT_EDGES)
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
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
    # count edges quickly
    n = sum(1 for line in OUT_EDGES.read_text(encoding="utf-8").splitlines() if line.strip())
    if n != manifest.get("edge_count"):
        errors.append(f"edge_count mismatch file={n} manifest={manifest.get('edge_count')}")
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
