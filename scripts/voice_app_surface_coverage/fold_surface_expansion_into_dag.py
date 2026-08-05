#!/usr/bin/env python3
"""Fold surface_expansion_edges.jsonl into slotted_response_dag.json.

Deterministic offline merge: creates intent + response-frame nodes and
intent_to_response_frame edges for each projected VAS edge that is not already
present. Uses the same sparse hashed-token embeddings as the existing DAG.

Usage:
  python scripts/voice_app_surface_coverage/fold_surface_expansion_into_dag.py --write
  python scripts/voice_app_surface_coverage/fold_surface_expansion_into_dag.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.simulate_211_conversations import generate_memory_embeddings  # noqa: E402

DAG_PATH = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_dag.json"
)
EDGES_PATH = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "surface_expansion_edges.jsonl"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "reports"
    / "dag-expansion-projection-manifest.json"
)
FOLD_RECEIPT = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "reports"
    / "dag-fold-receipt.json"
)
PROGRAM_ID = "voice-app-surface-coverage-v1"
SCHEMA_RECEIPT = "voice-app-surface-coverage/dag-fold@1"
BACKUP_SUFFIX = ".pre-vas-fold.bak"


def stable_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def load_sidecar_edges(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def fold(dag: dict[str, Any], sidecar: list[dict[str, Any]]) -> dict[str, Any]:
    intents: list[dict[str, Any]] = list(dag["nodes"]["intents"])
    frames: list[dict[str, Any]] = list(dag["nodes"]["responseFrames"])
    unique: list[dict[str, Any]] = list(dag["nodes"].get("uniqueExemplars") or [])
    edges: list[dict[str, Any]] = list(dag["edges"])

    intent_by_id = {n["id"]: n for n in intents}
    intent_by_text = {
        str(n.get("canonicalQueryTemplate") or ""): n for n in intents
    }
    frame_by_id = {n["id"]: n for n in frames}
    frame_by_sig = {str(n.get("responseSignature") or ""): n for n in frames}
    edge_ids = {e["id"] for e in edges}
    # Also key existing edges by (source, target, route) to avoid dups with different ids
    edge_keys = {
        (e.get("source"), e.get("target"), e.get("route")) for e in edges
    }

    new_intents: list[dict[str, Any]] = []
    new_frames: list[dict[str, Any]] = []
    new_edges: list[dict[str, Any]] = []
    new_unique: list[dict[str, Any]] = []
    skipped_existing = 0
    skipped_empty = 0

    for se in sidecar:
        examples = se.get("examples") or []
        if not examples:
            skipped_empty += 1
            continue
        ex0 = examples[0]
        user = str(ex0.get("user") or "").strip()
        assistant = str(ex0.get("assistant") or "").strip()
        record_id = str(ex0.get("recordId") or se.get("id") or "").strip()
        route = str(se.get("route") or "").strip()
        if not user or not assistant or not route:
            skipped_empty += 1
            continue

        intent_text = user  # surface variants are already short queries
        response_sig = assistant  # keep literal assistant text as signature for VAS

        intent_id = f"intent-{stable_id(intent_text)}"
        frame_id = f"response-frame-{stable_id(response_sig)}"
        pair_key = f"{intent_id}::{frame_id}::{route}"
        edge_id = str(se.get("id") or f"edge-{stable_id(pair_key)}")

        if edge_id in edge_ids or (intent_id, frame_id, route) in edge_keys:
            skipped_existing += 1
            continue

        # Intent node
        if intent_id not in intent_by_id and intent_text not in intent_by_text:
            intent_node = {
                "id": intent_id,
                "type": "intent",
                "canonicalQueryTemplate": intent_text,
                "recordIds": [record_id],
                "examples": [{"recordId": record_id, "user": user}],
                "reuseCount": 1,
                "routes": {route: 1},
                "querySlotKinds": {},
                "topQuerySlotValues": {},
                "evidenceDocIds": [],
                "surface_id": se.get("surface_id"),
                "logical_action": se.get("logical_action"),
                "program_id": PROGRAM_ID,
                "source": "vas_dag_fold",
            }
            new_intents.append(intent_node)
            intent_by_id[intent_id] = intent_node
            intent_by_text[intent_text] = intent_node
        else:
            existing = intent_by_id.get(intent_id) or intent_by_text[intent_text]
            intent_id = existing["id"]
            if record_id and record_id not in (existing.get("recordIds") or []):
                existing.setdefault("recordIds", []).append(record_id)
                existing["reuseCount"] = len(existing["recordIds"])
            routes = existing.get("routes") or {}
            if isinstance(routes, dict):
                routes[route] = int(routes.get(route) or 0) + 1
                existing["routes"] = routes

        # Response frame
        if frame_id not in frame_by_id and response_sig not in frame_by_sig:
            frame_node = {
                "id": frame_id,
                "type": "response_frame",
                "responseSignature": response_sig,
                "recordIds": [record_id],
                "examples": [{"recordId": record_id, "assistant": assistant}],
                "reuseCount": 1,
                "routes": {route: 1},
                "responseSlotKinds": {},
                "evidenceDocIds": [],
                "surface_id": se.get("surface_id"),
                "logical_action": se.get("logical_action"),
                "program_id": PROGRAM_ID,
                "source": "vas_dag_fold",
            }
            new_frames.append(frame_node)
            frame_by_id[frame_id] = frame_node
            frame_by_sig[response_sig] = frame_node
        else:
            existing_f = frame_by_id.get(frame_id) or frame_by_sig[response_sig]
            frame_id = existing_f["id"]
            if record_id and record_id not in (existing_f.get("recordIds") or []):
                existing_f.setdefault("recordIds", []).append(record_id)
                existing_f["reuseCount"] = len(existing_f["recordIds"])

        edge = {
            "id": edge_id,
            "type": "intent_to_response_frame",
            "source": intent_id,
            "target": frame_id,
            "route": route,
            "recordIds": [record_id],
            "examples": [
                {
                    "recordId": record_id,
                    "user": user,
                    "assistant": assistant,
                }
            ],
            "reuseCount": int(se.get("reuseCount") or 1),
            "reusable": bool(se.get("reusable") or False),
            "evidenceDocIds": [],
            "surface_id": se.get("surface_id"),
            "logical_action": se.get("logical_action"),
            "program_id": PROGRAM_ID,
            "source": "vas_dag_fold",
        }
        new_edges.append(edge)
        edge_ids.add(edge_id)
        edge_keys.add((intent_id, frame_id, route))

        # Unique exemplar for non-reusable single-use edges (matches builder policy)
        if not edge["reusable"]:
            uniq_id = f"unique-exemplar-{stable_id(record_id)}"
            new_unique.append(
                {
                    "id": uniq_id,
                    "type": "unique_exemplar",
                    "recordId": record_id,
                    "scenarioId": record_id,
                    "route": route,
                    "queryMaskedText": user,
                    "canonicalQueryTemplate": intent_text,
                    "responseMaskedText": assistant,
                    "responseSignature": response_sig,
                    "evidenceDocIds": [],
                    "user": user,
                    "assistant": assistant,
                    "surface_id": se.get("surface_id"),
                    "logical_action": se.get("logical_action"),
                    "program_id": PROGRAM_ID,
                    "source": "vas_dag_fold",
                }
            )

    # Embed new intents with the same sparse provider as the DAG
    if new_intents:
        texts = [n["canonicalQueryTemplate"] for n in new_intents]
        embeddings, emb_info = generate_memory_embeddings(
            texts, provider="deterministic_sparse_fallback"
        )
        for node, vector in zip(new_intents, embeddings):
            node["embedding"] = vector
        # keep embedding metadata consistent
        dag.setdefault("embedding", {}).update(
            {
                "provider": emb_info.get("provider"),
                "model": emb_info.get("model"),
                "kind": emb_info.get("kind"),
                "dimensions": emb_info.get("dimensions"),
            }
        )

    intents.extend(new_intents)
    frames.extend(new_frames)
    unique.extend(new_unique)
    edges.extend(new_edges)

    dag["nodes"]["intents"] = intents
    dag["nodes"]["responseFrames"] = frames
    dag["nodes"]["uniqueExemplars"] = unique
    dag["edges"] = edges
    dag["generatedAt"] = datetime.now(UTC).isoformat()
    dag.setdefault("inputs", {})["surfaceExpansionEdges"] = str(
        EDGES_PATH.relative_to(REPO_ROOT)
    )

    route_counts: Counter[str] = Counter()
    for e in edges:
        r = e.get("route")
        if r:
            route_counts[str(r)] += 1

    summary = dag.setdefault("summary", {})
    summary.update(
        {
            "intentNodeCount": len(intents),
            "responseFrameNodeCount": len(frames),
            "edgeCount": len(edges),
            "reusableEdgeCount": sum(1 for e in edges if e.get("reusable")),
            "uniqueExemplarCount": len(unique),
            "routeCounts": dict(sorted(route_counts.items())),
            "vasFold": {
                "added_intents": len(new_intents),
                "added_response_frames": len(new_frames),
                "added_edges": len(new_edges),
                "added_unique_exemplars": len(new_unique),
                "skipped_existing": skipped_existing,
                "skipped_empty": skipped_empty,
                "sidecar_edge_count": len(sidecar),
            },
        }
    )
    return {
        "added_intents": len(new_intents),
        "added_response_frames": len(new_frames),
        "added_edges": len(new_edges),
        "added_unique_exemplars": len(new_unique),
        "skipped_existing": skipped_existing,
        "skipped_empty": skipped_empty,
        "sidecar_edge_count": len(sidecar),
        "final_edge_count": len(edges),
        "final_intent_count": len(intents),
    }


def write_fold() -> dict[str, Any]:
    if not DAG_PATH.is_file():
        raise FileNotFoundError(DAG_PATH)
    if not EDGES_PATH.is_file():
        raise FileNotFoundError(EDGES_PATH)

    bak = DAG_PATH.with_suffix(DAG_PATH.suffix + BACKUP_SUFFIX)
    if not bak.is_file():
        shutil.copy2(DAG_PATH, bak)

    pre_digest = _sha256_file(DAG_PATH)
    dag = json.loads(DAG_PATH.read_text(encoding="utf-8"))
    sidecar = load_sidecar_edges(EDGES_PATH)
    stats = fold(dag, sidecar)

    # Stream write to avoid holding pretty print of 70MB+ in memory twice if possible
    DAG_PATH.write_text(
        json.dumps(dag, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    post_digest = _sha256_file(DAG_PATH)

    # Update projection manifest
    if MANIFEST_PATH.is_file():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest["full_dag_merge"] = {
            "status": "applied",
            "target": str(DAG_PATH.relative_to(REPO_ROOT)),
            "applied_at": datetime.now(UTC).isoformat(),
            "stats": stats,
            "pre_digest": pre_digest,
            "post_digest": post_digest,
            "backup": str(bak.relative_to(REPO_ROOT)) if bak.is_file() else None,
        }
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    receipt = {
        "schema": SCHEMA_RECEIPT,
        "program_id": PROGRAM_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "dag_path": str(DAG_PATH.relative_to(REPO_ROOT)),
        "sidecar_path": str(EDGES_PATH.relative_to(REPO_ROOT)),
        "backup_path": str(bak.relative_to(REPO_ROOT)) if bak.is_file() else None,
        "pre_digest": pre_digest,
        "post_digest": post_digest,
        "stats": stats,
        "status": "applied",
    }
    FOLD_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    FOLD_RECEIPT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def check_fold() -> list[str]:
    errors: list[str] = []
    if not FOLD_RECEIPT.is_file():
        return ["missing fold receipt"]
    receipt = json.loads(FOLD_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "applied":
        errors.append(f"fold status={receipt.get('status')}")
    stats = receipt.get("stats") or {}
    if int(stats.get("added_edges") or 0) < 1 and int(stats.get("skipped_existing") or 0) < 1:
        errors.append("fold added no edges")
    # Verify some edge-vas ids exist in DAG (stream scan)
    if not DAG_PATH.is_file():
        errors.append("missing DAG")
        return errors
    # cheap check: receipt stats vs sidecar count
    if not EDGES_PATH.is_file():
        errors.append("missing sidecar edges")
    else:
        n = sum(1 for line in EDGES_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
        covered = int(stats.get("added_edges") or 0) + int(stats.get("skipped_existing") or 0)
        if covered < n * 0.9:
            errors.append(
                f"fold coverage low: covered={covered} sidecar={n}"
            )
    if MANIFEST_PATH.is_file():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if (manifest.get("full_dag_merge") or {}).get("status") != "applied":
            errors.append("manifest full_dag_merge not applied")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write or not args.check:
        receipt = write_fold()
        print(json.dumps(receipt, indent=2, sort_keys=True))
    if args.check:
        errors = check_fold()
        if errors:
            print("dag fold FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("dag fold OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
