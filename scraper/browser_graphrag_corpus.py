from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


DEFAULT_PACKAGE_DIR = Path("data/retrieval_package")
DEFAULT_OUTPUT_DIR = Path("wallet_interface/ui/public/corpus/211-info/current")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORTAL_PARQUET = REPO_ROOT / "data" / "portal" / "documents.portal.parquet"
DEFAULT_BROWSER_EMBEDDING_MODEL_BY_PYTHON_MODEL = {
    "BAAI/bge-small-en-v1.5": "Xenova/bge-small-en-v1.5",
}
GEO_STOP_WORDS = {
    "and",
    "ave",
    "avenue",
    "blvd",
    "boulevard",
    "box",
    "center",
    "county",
    "court",
    "ct",
    "drive",
    "dr",
    "hwy",
    "highway",
    "lane",
    "ln",
    "loop",
    "main",
    "north",
    "northeast",
    "northwest",
    "or",
    "parkway",
    "pkwy",
    "place",
    "pl",
    "po",
    "rd",
    "road",
    "south",
    "southeast",
    "southwest",
    "st",
    "state",
    "street",
    "suite",
    "the",
    "unit",
    "west",
}


def _bootstrap_local_ipfs_datasets() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    local_ipfs = repo_root / "ipfs_datasets_py"
    if local_ipfs.exists() and str(local_ipfs) not in sys.path:
        sys.path.insert(0, str(local_ipfs))


def cid_for_file(path: Path) -> str:
    data = path.read_bytes()
    try:
        _bootstrap_local_ipfs_datasets()
        from ipfs_datasets_py.utils.cid_utils import cid_for_bytes

        return str(cid_for_bytes(data))
    except Exception:
        return f"sha256:{hashlib.sha256(data).hexdigest()}"


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return file_record(path)


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "bytes": int(path.stat().st_size),
        "cid": cid_for_file(path),
    }


def compact_text(value: Any, max_chars: int) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip(), True
    return text, False


def read_manifest(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "manifest" / "build_manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def json_value(value: Any, default: Any) -> Any:
    if value in ("", None):
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(str(value))
    except Exception:
        return default
    return parsed if parsed is not None else default


def load_portal_service_details(portal_parquet_path: Path) -> dict[str, dict[str, Any]]:
    if not portal_parquet_path.exists():
        return {}

    frame = pd.read_parquet(
        portal_parquet_path,
        columns=[
            "service_doc_id",
            "phones",
            "emails",
            "websites",
            "addresses",
            "hours",
            "eligibility",
            "intake_steps",
            "required_documents",
            "fees",
            "languages",
            "accessibility",
            "travel_info",
            "area_served",
            "geo",
        ],
    ).fillna("")

    details: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        doc_id = str(row.get("service_doc_id", ""))
        if not doc_id:
            continue
        details[doc_id] = {
            "phones": json_value(row.get("phones"), []),
            "emails": json_value(row.get("emails"), []),
            "websites": json_value(row.get("websites"), []),
            "addresses": json_value(row.get("addresses"), []),
            "hours": json_value(row.get("hours"), []),
            "eligibility": json_value(row.get("eligibility"), []),
            "intake_steps": json_value(row.get("intake_steps"), []),
            "required_documents": json_value(row.get("required_documents"), []),
            "fees": json_value(row.get("fees"), []),
            "languages": json_value(row.get("languages"), []),
            "accessibility": json_value(row.get("accessibility"), []),
            "travel_info": json_value(row.get("travel_info"), []),
            "area_served": json_value(row.get("area_served"), []),
            "geo": json_value(row.get("geo"), {"lat": None, "lon": None, "precision": "none"}),
        }
    return details


def load_documents(
    package_dir: Path,
    *,
    portal_service_details: dict[str, dict[str, Any]],
    max_documents: int,
    text_max_chars: int,
) -> list[dict[str, Any]]:
    frame = pd.read_parquet(package_dir / "content" / "documents.parquet")
    if max_documents > 0:
        frame = frame.head(max_documents)

    documents: list[dict[str, Any]] = []
    for row in frame.fillna("").to_dict(orient="records"):
        text, text_truncated = compact_text(row.get("text", ""), text_max_chars)
        doc_id = str(row.get("doc_id", ""))
        document = {
            "doc_id": doc_id,
            "doc_type": str(row.get("doc_type", "")),
            "title": str(row.get("title", "")),
            "text": text,
            "text_truncated": text_truncated,
            "source_url": str(row.get("source_url", "")),
            "source_content_cid": str(row.get("source_content_cid", "")),
            "source_page_cid": str(row.get("source_page_cid", "")),
            "provider_name": str(row.get("provider_name", "")),
            "program_name": str(row.get("program_name", "")),
            "categories": str(row.get("categories", "")),
            "host": str(row.get("host", "")),
            "city": str(row.get("city", "")),
            "state": str(row.get("state", "")),
        }
        if document["doc_type"] == "service":
            document.update(portal_service_details.get(doc_id, {}))
        documents.append(document)
    return documents


def normalize_geo_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def tokenize_geo_text(value: str) -> set[str]:
    tokens = set()
    for token in normalize_geo_key(value).split():
        if len(token) < 2:
            continue
        if token in GEO_STOP_WORDS:
            continue
        if token.isdigit() and len(token) < 5:
            continue
        tokens.add(token)
    return tokens


def add_geo_term(index: dict[str, set[str]], key: Any, doc_id: str) -> None:
    normalized = normalize_geo_key(key)
    if not normalized:
        return
    index.setdefault(normalized, set()).add(doc_id)


def build_service_geo_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    docs_by_city: dict[str, set[str]] = {}
    docs_by_state: dict[str, set[str]] = {}
    docs_by_place_term: dict[str, set[str]] = {}
    geo_precision_counts: dict[str, int] = defaultdict(int)
    docs_with_address = 0
    docs_with_map_query = 0
    docs_with_coordinates = 0
    docs_with_area_served = 0
    service_count = 0

    for document in documents:
        if document.get("doc_type") != "service":
            continue
        service_count += 1
        doc_id = str(document.get("doc_id", ""))
        geo = document.get("geo") if isinstance(document.get("geo"), dict) else {}
        precision = str((geo or {}).get("precision") or "none")
        geo_precision_counts[precision] += 1
        if (geo or {}).get("lat") is not None and (geo or {}).get("lon") is not None:
            docs_with_coordinates += 1

        place_text_parts = [
            str(document.get("city", "")),
            str(document.get("state", "")),
            str(document.get("categories", "")),
        ]
        add_geo_term(docs_by_city, document.get("city"), doc_id)
        add_geo_term(docs_by_state, document.get("state"), doc_id)

        addresses = document.get("addresses") if isinstance(document.get("addresses"), list) else []
        if addresses:
            docs_with_address += 1
        seen_map_query = False
        for address in addresses:
            if not isinstance(address, dict):
                continue
            add_geo_term(docs_by_city, address.get("city"), doc_id)
            add_geo_term(docs_by_state, address.get("state"), doc_id)
            place_text_parts.extend(
                [
                    str(address.get("address", "")),
                    str(address.get("street", "")),
                    str(address.get("city", "")),
                    str(address.get("state", "")),
                    str(address.get("postal_code", "")),
                    str(address.get("maps_query", "")),
                ]
            )
            if address.get("maps_query"):
                seen_map_query = True
        if seen_map_query:
            docs_with_map_query += 1

        area_served = document.get("area_served") if isinstance(document.get("area_served"), list) else []
        if area_served:
            docs_with_area_served += 1
        for item in area_served:
            if isinstance(item, dict):
                place_text_parts.append(str(item.get("value", "")))

        travel_info = document.get("travel_info") if isinstance(document.get("travel_info"), list) else []
        for item in travel_info:
            if isinstance(item, dict):
                place_text_parts.append(str(item.get("value", "")))

        for term in tokenize_geo_text(" ".join(part for part in place_text_parts if part)):
            docs_by_place_term.setdefault(term, set()).add(doc_id)

    return {
        "schemaVersion": 1,
        "serviceCount": service_count,
        "docsWithAddress": docs_with_address,
        "docsWithMapQuery": docs_with_map_query,
        "docsWithCoordinates": docs_with_coordinates,
        "docsWithAreaServed": docs_with_area_served,
        "geoPrecisionCounts": dict(sorted(geo_precision_counts.items())),
        "docsByCity": {key: sorted(value) for key, value in sorted(docs_by_city.items())},
        "docsByState": {key: sorted(value) for key, value in sorted(docs_by_state.items())},
        "docsByPlaceTerm": {key: sorted(value) for key, value in sorted(docs_by_place_term.items())},
    }


def build_document_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "count": len(documents),
        "docIdToIndex": {document["doc_id"]: index for index, document in enumerate(documents)},
        "contentCidToIndex": {
            document["source_content_cid"]: index
            for index, document in enumerate(documents)
            if document.get("source_content_cid")
        },
    }


def build_bm25_payload(
    package_dir: Path,
    *,
    selected_doc_ids: set[str],
    max_terms_per_document: int,
) -> dict[str, Any]:
    doc_frame = pd.read_parquet(package_dir / "retrieval" / "bm25_documents.parquet").fillna("")
    if selected_doc_ids:
        doc_frame = doc_frame[doc_frame["doc_id"].isin(selected_doc_ids)]

    term_frame = pd.read_parquet(package_dir / "retrieval" / "bm25_terms.parquet").fillna("")
    if selected_doc_ids:
        term_frame = term_frame[term_frame["doc_id"].isin(selected_doc_ids)]

    if term_frame.empty:
        document_frequency: dict[str, int] = {}
        documents = [
            {
                "doc_id": str(row["doc_id"]),
                "doc_type": str(row.get("doc_type", "")),
                "source_content_cid": str(row.get("source_content_cid", "")),
                "source_page_cid": str(row.get("source_page_cid", "")),
                "document_length": int(row.get("doc_length") or 0),
                "terms": {},
            }
            for row in doc_frame.to_dict(orient="records")
        ]
        avgdl = 0.0
        document_count = len(documents)
    else:
        term_frame = term_frame.assign(score=term_frame["tf"].astype(float) * term_frame["idf"].astype(float))
        term_frame = term_frame.sort_values(["doc_id", "score", "idf", "tf", "term"], ascending=[True, False, False, False, True])
        if max_terms_per_document > 0:
            term_frame = term_frame.groupby("doc_id", sort=False).head(max_terms_per_document)

        term_rows_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        document_frequency: dict[str, int] = {}
        for row in term_frame.to_dict(orient="records"):
            term = str(row.get("term", ""))
            if not term:
                continue
            document_frequency[term] = max(document_frequency.get(term, 0), int(row.get("df") or 0))
            term_rows_by_doc[str(row.get("doc_id", ""))].append(
                {
                    "term": term,
                    "tf": float(row.get("tf") or 0.0),
                    "idf": float(row.get("idf") or 0.0),
                }
            )

        documents = []
        for row in doc_frame.to_dict(orient="records"):
            doc_id = str(row.get("doc_id", ""))
            documents.append(
                {
                    "doc_id": doc_id,
                    "doc_type": str(row.get("doc_type", "")),
                    "source_url": str(row.get("source_url", "")),
                    "source_content_cid": str(row.get("source_content_cid", "")),
                    "source_page_cid": str(row.get("source_page_cid", "")),
                    "document_length": int(row.get("doc_length") or 0),
                    "terms": {
                        term_row["term"]: term_row["tf"]
                        for term_row in term_rows_by_doc.get(doc_id, [])
                    },
                    "term_idf": {
                        term_row["term"]: term_row["idf"]
                        for term_row in term_rows_by_doc.get(doc_id, [])
                    },
                }
            )
        avgdl = float(term_frame["avg_doc_length"].iloc[0]) if "avg_doc_length" in term_frame and len(term_frame) else 0.0
        document_count = int(term_frame["document_count"].iloc[0]) if "document_count" in term_frame and len(term_frame) else len(documents)

    return {
        "schemaVersion": 1,
        "documents": documents,
        "documentFrequency": document_frequency,
        "k1": 1.5,
        "b": 0.75,
        "avgdl": avgdl,
        "documentCount": document_count,
        "maxTermsPerDocument": max_terms_per_document,
    }


def write_embeddings(
    package_dir: Path,
    output_path: Path,
    *,
    selected_doc_ids: set[str],
) -> dict[str, Any]:
    frame = pd.read_parquet(package_dir / "retrieval" / "vector_embeddings.parquet").fillna("")
    if selected_doc_ids:
        frame = frame[frame["doc_id"].isin(selected_doc_ids)]

    vectors: list[list[float]] = []
    doc_ids: list[str] = []
    content_cids: list[str] = []
    page_cids: list[str] = []
    source_urls: list[str] = []
    model_name = ""
    dimension = 0

    for row in frame.to_dict(orient="records"):
        embedding = row.get("embedding")
        if embedding is None:
            values = []
        else:
            values = [float(value) for value in embedding]
        if not values:
            continue
        if dimension and len(values) != dimension:
            raise ValueError(f"embedding dimension mismatch for {row.get('doc_id')}")
        dimension = len(values)
        vectors.append(values)
        doc_ids.append(str(row.get("doc_id", "")))
        content_cids.append(str(row.get("source_content_cid", "")))
        page_cids.append(str(row.get("source_page_cid", "")))
        source_urls.append(str(row.get("source_url", "")))
        model_name = model_name or str(row.get("embedding_model", ""))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        for vector in vectors:
            handle.write(struct.pack(f"<{dimension}f", *vector))

    index = {
        "schemaVersion": 1,
        "count": len(vectors),
        "dimension": dimension,
        "embeddingModel": model_name,
        "browserEmbeddingModel": DEFAULT_BROWSER_EMBEDDING_MODEL_BY_PYTHON_MODEL.get(model_name, ""),
        "binary": output_path.name,
        "doc_ids": doc_ids,
        "source_content_cids": content_cids,
        "source_page_cids": page_cids,
        "source_urls": source_urls,
    }
    return index


def compact_node(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key, "")
        for key in [
            "node_id",
            "node_type",
            "label",
            "node_cid",
            "source_url",
            "source_content_cid",
            "source_page_cid",
            "provider_name",
            "program_name",
            "categories",
            "city",
            "state",
            "category",
            "term",
        ]
        if row.get(key, "") not in ("", None) or key in {"node_id", "node_type", "label"}
    }


def compact_edge(row: dict[str, Any]) -> dict[str, Any]:
    edge = {
        "source": str(row.get("source", "")),
        "target": str(row.get("target", "")),
        "relation": str(row.get("relation", "")),
        "edge_cid": str(row.get("edge_cid", "")),
    }
    for key in ["bm25_score", "tf", "idf", "shared_document_count", "cooccurrence_score"]:
        value = row.get(key)
        if value not in ("", None) and not (isinstance(value, float) and math.isnan(value)):
            edge[key] = float(value)
    if row.get("source_content_cid"):
        edge["source_content_cid"] = str(row["source_content_cid"])
    return edge


def edge_priority(edge: dict[str, Any]) -> tuple[int, float]:
    relation = str(edge.get("relation", ""))
    priority = {
        "HAS_KEYTERM": 100,
        "IN_CATEGORY": 90,
        "LOCATED_IN": 85,
        "PROVIDES_SERVICE": 80,
        "HAS_PROGRAM": 75,
        "DERIVED_FROM_PAGE": 70,
        "HAS_DOCUMENT": 60,
        "LINKS_TO": 40,
        "CO_OCCURS_WITH": 30,
    }.get(relation, 10)
    score = max(
        float(edge.get("bm25_score") or 0.0),
        float(edge.get("cooccurrence_score") or 0.0),
        float(edge.get("shared_document_count") or 0.0),
    )
    return priority, score


def build_graph_neighborhoods(
    package_dir: Path,
    *,
    selected_doc_ids: set[str],
    max_edges_per_document: int,
) -> dict[str, Any]:
    nodes = pd.read_parquet(package_dir / "graph" / "knowledge_graph_nodes.parquet").fillna("")
    edges = pd.read_parquet(package_dir / "graph" / "knowledge_graph_edges.parquet").fillna("")

    node_by_id = {
        str(row.get("node_id", "")): compact_node(row)
        for row in nodes.to_dict(orient="records")
        if row.get("node_id")
    }

    selected = selected_doc_ids or {
        node_id
        for node_id, node in node_by_id.items()
        if node.get("node_type") in {"page", "service"}
    }

    incident: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edges.to_dict(orient="records"):
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        if source in selected:
            incident[source].append(compact_edge(row))
        if target in selected and target != source:
            incident[target].append(compact_edge(row))

    neighborhoods: dict[str, dict[str, Any]] = {}
    exported_nodes: dict[str, dict[str, Any]] = {}
    exported_edges: dict[str, dict[str, Any]] = {}
    for doc_id in sorted(selected):
        ranked_edges = sorted(
            incident.get(doc_id, []),
            key=lambda edge: edge_priority(edge),
            reverse=True,
        )
        if max_edges_per_document > 0:
            ranked_edges = ranked_edges[:max_edges_per_document]
        node_ids = [doc_id]
        exported_nodes[doc_id] = node_by_id.get(doc_id, {"node_id": doc_id})
        edge_ids: list[str] = []
        for edge in ranked_edges:
            edge_id = str(edge.get("edge_cid") or f"{edge.get('source')}->{edge.get('relation')}->{edge.get('target')}")
            exported_edges[edge_id] = edge
            edge_ids.append(edge_id)
            for node_id in [edge.get("source", ""), edge.get("target", "")]:
                if node_id and node_id in node_by_id:
                    exported_nodes[node_id] = node_by_id[node_id]
                    if node_id not in node_ids:
                        node_ids.append(node_id)
        neighborhoods[doc_id] = {
            "node_ids": node_ids,
            "edge_ids": edge_ids,
        }

    return {
        "schemaVersion": 1,
        "maxEdgesPerDocument": max_edges_per_document,
        "nodes": exported_nodes,
        "edges": exported_edges,
        "neighborhoods": neighborhoods,
    }


def write_graph_neighborhood_artifacts(
    *,
    output_dir: Path,
    generated_dir: Path,
    graph_payload: dict[str, Any],
    shard_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    legacy_graph_path = generated_dir / "graph-neighborhoods.json"
    if legacy_graph_path.exists():
        legacy_graph_path.unlink()

    shard_dir = generated_dir / "graph-neighborhoods"
    shard_dir.mkdir(parents=True, exist_ok=True)
    for stale_path in shard_dir.glob("*.json"):
        stale_path.unlink()

    neighborhoods: dict[str, dict[str, Any]] = graph_payload["neighborhoods"]
    nodes: dict[str, dict[str, Any]] = graph_payload["nodes"]
    edges: dict[str, dict[str, Any]] = graph_payload["edges"]
    doc_ids = sorted(neighborhoods)
    shard_size = max(1, shard_size)

    shard_records: list[dict[str, Any]] = []
    doc_id_to_shard: dict[str, str] = {}
    artifact_records: list[dict[str, Any]] = []

    for shard_number, start_index in enumerate(range(0, len(doc_ids), shard_size)):
        shard_doc_ids = doc_ids[start_index : start_index + shard_size]
        shard_neighborhoods = {
            doc_id: neighborhoods[doc_id]
            for doc_id in shard_doc_ids
        }
        shard_node_ids = sorted(
            {
                node_id
                for neighborhood in shard_neighborhoods.values()
                for node_id in neighborhood.get("node_ids", [])
            }
        )
        shard_edge_ids = sorted(
            {
                edge_id
                for neighborhood in shard_neighborhoods.values()
                for edge_id in neighborhood.get("edge_ids", [])
            }
        )
        shard_payload = {
            "schemaVersion": 1,
            "shardId": f"shard-{shard_number:04d}",
            "maxEdgesPerDocument": graph_payload["maxEdgesPerDocument"],
            "doc_ids": shard_doc_ids,
            "nodes": {
                node_id: nodes[node_id]
                for node_id in shard_node_ids
                if node_id in nodes
            },
            "edges": {
                edge_id: edges[edge_id]
                for edge_id in shard_edge_ids
                if edge_id in edges
            },
            "neighborhoods": shard_neighborhoods,
        }
        shard_path = shard_dir / f"shard-{shard_number:04d}.json"
        shard_record = write_json(shard_path, shard_payload)
        relative_path = Path(shard_record["path"]).relative_to(output_dir).as_posix()
        for doc_id in shard_doc_ids:
            doc_id_to_shard[doc_id] = relative_path
        shard_records.append(
            {
                "id": f"shard-{shard_number:04d}",
                "path": relative_path,
                "bytes": shard_record["bytes"],
                "cid": shard_record["cid"],
                "documentCount": len(shard_doc_ids),
                "nodeCount": len(shard_payload["nodes"]),
                "edgeCount": len(shard_payload["edges"]),
                "firstDocId": shard_doc_ids[0] if shard_doc_ids else "",
                "lastDocId": shard_doc_ids[-1] if shard_doc_ids else "",
            }
        )
        artifact_records.append(relative_manifest_record(output_dir, shard_record, "graph"))

    graph_index = {
        "schemaVersion": 1,
        "maxEdgesPerDocument": graph_payload["maxEdgesPerDocument"],
        "neighborhoodCount": len(neighborhoods),
        "shardSize": shard_size,
        "shardCount": len(shard_records),
        "shards": shard_records,
        "docIdToShard": doc_id_to_shard,
    }
    graph_index_record = write_json(generated_dir / "graph-neighborhood-index.json", graph_index)
    artifact_records.insert(0, relative_manifest_record(output_dir, graph_index_record, "graph"))
    return graph_index, artifact_records


def build_community_payloads(package_dir: Path, *, selected_doc_ids: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    communities_frame = pd.read_parquet(package_dir / "graph" / "graph_communities.parquet").fillna("")
    document_frame = pd.read_parquet(package_dir / "graph" / "document_communities.parquet").fillna("")
    if selected_doc_ids:
        document_frame = document_frame[document_frame["doc_id"].isin(selected_doc_ids)]

    used_community_ids = set(str(value) for value in document_frame["community_id"].tolist()) if len(document_frame) else set()
    community_rows = [
        {
            "community_id": str(row.get("community_id", "")),
            "community_cid": str(row.get("community_cid", "")),
            "label": str(row.get("label", "")),
            "node_count": int(row.get("node_count") or 0),
            "document_count": int(row.get("document_count") or 0),
            "page_count": int(row.get("page_count") or 0),
            "service_count": int(row.get("service_count") or 0),
            "keyterm_count": int(row.get("keyterm_count") or 0),
            "provider_count": int(row.get("provider_count") or 0),
            "category_count": int(row.get("category_count") or 0),
            "top_terms": json.loads(row.get("top_terms_json") or "[]"),
            "top_categories": json.loads(row.get("top_categories_json") or "[]"),
            "top_hosts": json.loads(row.get("top_hosts_json") or "[]"),
        }
        for row in communities_frame.to_dict(orient="records")
        if not used_community_ids or str(row.get("community_id", "")) in used_community_ids
    ]
    document_rows = [
        {
            "doc_id": str(row.get("doc_id", "")),
            "doc_type": str(row.get("doc_type", "")),
            "source_url": str(row.get("source_url", "")),
            "source_content_cid": str(row.get("source_content_cid", "")),
            "source_page_cid": str(row.get("source_page_cid", "")),
            "community_id": str(row.get("community_id", "")),
            "community_label": str(row.get("community_label", "")),
        }
        for row in document_frame.to_dict(orient="records")
    ]
    return (
        {"schemaVersion": 1, "communities": community_rows},
        {"schemaVersion": 1, "documents": document_rows},
    )


def relative_manifest_record(root: Path, record: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "path": Path(record["path"]).relative_to(root).as_posix(),
        "bytes": record["bytes"],
        "cid": record["cid"],
        "role": role,
    }


def build_browser_graphrag_corpus(
    *,
    package_dir: Path = DEFAULT_PACKAGE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    portal_parquet_path: Path = DEFAULT_PORTAL_PARQUET,
    max_documents: int = 0,
    text_max_chars: int = 6000,
    max_terms_per_document: int = 48,
    max_edges_per_document: int = 8,
    graph_shard_size: int = 500,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    output_dir = output_dir.resolve()
    generated_dir = output_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = read_manifest(package_dir)
    portal_service_details = load_portal_service_details(portal_parquet_path.resolve())
    documents = load_documents(
        package_dir,
        portal_service_details=portal_service_details,
        max_documents=max_documents,
        text_max_chars=text_max_chars,
    )
    selected_doc_ids = {document["doc_id"] for document in documents}
    service_documents = [document for document in documents if document.get("doc_type") == "service"]
    service_count = len(service_documents)
    service_phone_count = sum(1 for document in service_documents if document.get("phones"))
    service_address_count = sum(1 for document in service_documents if document.get("addresses"))
    service_intake_step_count = sum(1 for document in service_documents if document.get("intake_steps"))
    service_required_document_count = sum(1 for document in service_documents if document.get("required_documents"))

    artifact_records: list[dict[str, Any]] = []
    documents_record = write_json(generated_dir / "documents.json", documents)
    artifact_records.append(relative_manifest_record(output_dir, documents_record, "documents"))

    document_index_record = write_json(generated_dir / "document-index.json", build_document_index(documents))
    artifact_records.append(relative_manifest_record(output_dir, document_index_record, "index"))

    bm25_payload = build_bm25_payload(
        package_dir,
        selected_doc_ids=selected_doc_ids,
        max_terms_per_document=max_terms_per_document,
    )
    bm25_record = write_json(generated_dir / "bm25-documents.json", bm25_payload)
    artifact_records.append(relative_manifest_record(output_dir, bm25_record, "retrieval"))

    embedding_index = write_embeddings(
        package_dir,
        generated_dir / "embeddings.f32",
        selected_doc_ids=selected_doc_ids,
    )
    embedding_binary_record = file_record(generated_dir / "embeddings.f32")
    artifact_records.append(relative_manifest_record(output_dir, embedding_binary_record, "retrieval"))
    embedding_index_record = write_json(generated_dir / "embedding-index.json", embedding_index)
    artifact_records.append(relative_manifest_record(output_dir, embedding_index_record, "retrieval"))

    graph_payload = build_graph_neighborhoods(
        package_dir,
        selected_doc_ids=selected_doc_ids,
        max_edges_per_document=max_edges_per_document,
    )
    graph_index, graph_records = write_graph_neighborhood_artifacts(
        output_dir=output_dir,
        generated_dir=generated_dir,
        graph_payload=graph_payload,
        shard_size=graph_shard_size,
    )
    artifact_records.extend(graph_records)

    graph_communities, document_communities = build_community_payloads(
        package_dir,
        selected_doc_ids=selected_doc_ids,
    )
    communities_record = write_json(generated_dir / "graph-communities.json", graph_communities)
    artifact_records.append(relative_manifest_record(output_dir, communities_record, "graph"))
    document_communities_record = write_json(generated_dir / "document-communities.json", document_communities)
    artifact_records.append(relative_manifest_record(output_dir, document_communities_record, "graph"))

    service_geo_index = build_service_geo_index(documents)
    service_geo_record = write_json(generated_dir / "service-geo-index.json", service_geo_index)
    artifact_records.append(relative_manifest_record(output_dir, service_geo_record, "geo"))

    generated_manifest = {
        "schemaVersion": 1,
        "documentCount": len(documents),
        "serviceDocumentCount": service_count,
        "servicePhoneCount": service_phone_count,
        "serviceAddressCount": service_address_count,
        "serviceIntakeStepCount": service_intake_step_count,
        "serviceRequiredDocumentCount": service_required_document_count,
        "embeddingCount": int(embedding_index["count"]),
        "embeddingDimension": int(embedding_index["dimension"]),
        "embeddingModel": embedding_index["embeddingModel"],
        "bm25DocumentCount": len(bm25_payload["documents"]),
        "graphNeighborhoodCount": len(graph_payload["neighborhoods"]),
        "graphNeighborhoodShardCount": int(graph_index["shardCount"]),
        "graphCommunityCount": len(graph_communities["communities"]),
        "documentCommunityCount": len(document_communities["documents"]),
        "geoSearchIndexedServiceCount": int(service_geo_index["serviceCount"]),
        "geoSearchPlaceTermCount": len(service_geo_index["docsByPlaceTerm"]),
        "sourcePackage": {
            "path": str(package_dir),
            "build_manifest_cid": source_manifest.get("build_manifest_cid", ""),
            "document_count": source_manifest.get("document_count", 0),
            "graph_node_count": source_manifest.get("graph_node_count", 0),
            "graph_edge_count": source_manifest.get("graph_edge_count", 0),
        },
        "files": artifact_records,
    }
    generated_manifest_record = write_json(generated_dir / "generated-manifest.json", generated_manifest)
    artifact_records.append(relative_manifest_record(output_dir, generated_manifest_record, "metadata"))

    artifacts_manifest = {
        "schemaVersion": 1,
        "datasetId": "endomorphosis/211-info",
        "datasetPath": "browser/211-info/current",
        "corpus": {
            "name": "211info retrieval package",
            "source": "https://huggingface.co/datasets/endomorphosis/211-info",
            "documentCount": len(documents),
            "embeddingModel": embedding_index["embeddingModel"],
            "embeddingDimension": int(embedding_index["dimension"]),
        },
        "sourcePackage": generated_manifest["sourcePackage"],
        "artifacts": artifact_records,
    }
    artifacts_manifest_record = write_json(output_dir / "artifacts.manifest.json", artifacts_manifest)

    return {
        "output_dir": str(output_dir),
        "document_count": len(documents),
        "service_document_count": service_count,
        "service_phone_count": service_phone_count,
        "service_address_count": service_address_count,
        "service_intake_step_count": service_intake_step_count,
        "service_required_document_count": service_required_document_count,
        "embedding_count": int(embedding_index["count"]),
        "embedding_dimension": int(embedding_index["dimension"]),
        "bm25_document_count": len(bm25_payload["documents"]),
        "graph_neighborhood_count": len(graph_payload["neighborhoods"]),
        "graph_neighborhood_shard_count": int(graph_index["shardCount"]),
        "graph_community_count": len(graph_communities["communities"]),
        "document_community_count": len(document_communities["documents"]),
        "geo_indexed_service_count": int(service_geo_index["serviceCount"]),
        "geo_place_term_count": len(service_geo_index["docsByPlaceTerm"]),
        "artifact_count": len(artifact_records) + 1,
        "artifacts_manifest_cid": artifacts_manifest_record["cid"],
        "generated_manifest_cid": generated_manifest_record["cid"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build browser-ready static GraphRAG assets from the 211 retrieval package")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--portal-parquet-path", type=Path, default=DEFAULT_PORTAL_PARQUET)
    parser.add_argument("--max-documents", type=int, default=0, help="Optional cap for smoke builds")
    parser.add_argument("--text-max-chars", type=int, default=6000, help="Per-document text cap; 0 keeps full text")
    parser.add_argument("--max-terms-per-document", type=int, default=48)
    parser.add_argument("--max-edges-per-document", type=int, default=8)
    parser.add_argument("--graph-shard-size", type=int, default=500)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = build_browser_graphrag_corpus(
        package_dir=args.package_dir,
        output_dir=args.output_dir,
        portal_parquet_path=args.portal_parquet_path,
        max_documents=args.max_documents,
        text_max_chars=args.text_max_chars,
        max_terms_per_document=args.max_terms_per_document,
        max_edges_per_document=args.max_edges_per_document,
        graph_shard_size=args.graph_shard_size,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
