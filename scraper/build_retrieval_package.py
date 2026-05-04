from __future__ import annotations

import argparse
import asyncio
import importlib.machinery
import json
import logging
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable
from urllib.parse import urlparse

import duckdb
import pandas as pd

from .utils import clean_text, setup_logging

logger = logging.getLogger("scraper.retrieval_package")

TOKEN_RE = re.compile(r"[A-Za-z0-9']+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


@dataclass
class CorpusDocument:
    doc_id: str
    doc_type: str
    title: str
    text: str
    source_url: str
    source_content_cid: str
    source_page_cid: str
    provider_name: str = ""
    program_name: str = ""
    categories: str = ""
    host: str = ""
    city: str = ""
    state: str = ""
    metadata_json: str = ""


def _bootstrap_local_ipfs_datasets() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    local_ipfs = repo_root / "ipfs_datasets_py"
    if local_ipfs.exists() and str(local_ipfs) not in sys.path:
        sys.path.insert(0, str(local_ipfs))


def _ensure_torchvision_stub() -> None:
    if "torchvision" in sys.modules:
        return
    try:
        import torchvision  # type: ignore  # noqa: F401
        return
    except Exception:
        pass

    def stub(name: str):
        module = type(sys)(name)
        module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None)
        return module

    vision = stub("torchvision")
    submodules: dict[str, Any] = {}
    for submodule_name in ["transforms", "io", "datasets", "models", "ops", "utils", "_meta_registrations"]:
        full_name = f"torchvision.{submodule_name}"
        submodule = stub(full_name)
        submodules[submodule_name] = submodule
        setattr(vision, submodule_name, submodule)
        sys.modules[full_name] = submodule

    class _InterpolationMode:
        NEAREST = "nearest"
        NEAREST_EXACT = "nearest-exact"
        BILINEAR = "bilinear"
        BICUBIC = "bicubic"
        BOX = "box"
        HAMMING = "hamming"
        LANCZOS = "lanczos"

    submodules["transforms"].InterpolationMode = _InterpolationMode
    sys.modules["torchvision"] = vision


def _cid_for_obj(payload: dict[str, Any]) -> str:
    _bootstrap_local_ipfs_datasets()
    from ipfs_datasets_py.utils.cid_utils import cid_for_obj

    return str(cid_for_obj(payload))


def _cid_for_file(path: Path) -> str:
    _bootstrap_local_ipfs_datasets()
    from ipfs_datasets_py.utils.cid_utils import cid_for_bytes

    return str(cid_for_bytes(path.read_bytes()))


def tokenize_text(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(clean_text(text))]
    return [token for token in tokens if len(token) >= 2 and token not in STOPWORDS]


def build_bm25_rows(documents: list[CorpusDocument]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not documents:
        return [], []

    document_count = len(documents)
    doc_tokens: dict[str, list[str]] = {}
    doc_lengths: dict[str, int] = {}
    document_frequency: Counter[str] = Counter()

    document_rows: list[dict[str, Any]] = []
    for document in documents:
        tokens = tokenize_text(document.text)
        doc_tokens[document.doc_id] = tokens
        doc_lengths[document.doc_id] = len(tokens)
        document_frequency.update(set(tokens))
        document_rows.append(
            {
                "doc_id": document.doc_id,
                "doc_type": document.doc_type,
                "source_url": document.source_url,
                "source_content_cid": document.source_content_cid,
                "source_page_cid": document.source_page_cid,
                "doc_length": len(tokens),
            }
        )

    avg_doc_length = (
        sum(float(length) for length in doc_lengths.values()) / document_count if document_count else 0.0
    )

    bm25_rows: list[dict[str, Any]] = []
    for document in documents:
        tf_counter = Counter(doc_tokens[document.doc_id])
        for term, tf in sorted(tf_counter.items()):
            df = int(document_frequency.get(term) or 0)
            idf = math.log(((document_count - df + 0.5) / (df + 0.5)) + 1.0) if df else 0.0
            bm25_rows.append(
                {
                    "doc_id": document.doc_id,
                    "doc_type": document.doc_type,
                    "source_content_cid": document.source_content_cid,
                    "source_page_cid": document.source_page_cid,
                    "term": term,
                    "tf": float(tf),
                    "df": df,
                    "idf": idf,
                    "doc_length": float(doc_lengths[document.doc_id]),
                    "avg_doc_length": avg_doc_length,
                    "document_count": document_count,
                }
            )
    return document_rows, bm25_rows


def build_graph_rows(
    documents: list[CorpusDocument],
    page_links: dict[str, list[str]],
    known_page_urls: set[str],
    *,
    bm25_rows: list[dict[str, Any]] | None = None,
    keyterms_per_document: int = 12,
    max_cooccurrence_partners: int = 8,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()

    def add_node(node_id: str, node_type: str, label: str, **attrs: Any) -> None:
        if not node_id or node_id in seen_nodes:
            return
        payload = {
            "node_id": node_id,
            "node_type": node_type,
            "label": label,
            **attrs,
        }
        payload["node_cid"] = _cid_for_obj(payload)
        nodes.append(payload)
        seen_nodes.add(node_id)

    def add_edge(source: str, target: str, relation: str, **attrs: Any) -> None:
        if not source or not target:
            return
        payload = {
            "source": source,
            "target": target,
            "relation": relation,
            **attrs,
        }
        edge_key = _cid_for_obj(payload)
        if edge_key in seen_edges:
            return
        payload["edge_cid"] = edge_key
        edges.append(payload)
        seen_edges.add(edge_key)

    page_id_by_url = {
        document.source_url: document.doc_id
        for document in documents
        if document.doc_type == "page" and document.source_url
    }

    for document in documents:
        host = document.host or urlparse(document.source_url).netloc.lower()
        host_node = f"host:{host}" if host else ""
        if host:
            add_node(host_node, "host", host, host=host)

        add_node(
            document.doc_id,
            document.doc_type,
            document.title or document.source_url,
            source_url=document.source_url,
            source_content_cid=document.source_content_cid,
            source_page_cid=document.source_page_cid,
            host=host,
            provider_name=document.provider_name,
            program_name=document.program_name,
            categories=document.categories,
            city=document.city,
            state=document.state,
        )
        if host_node:
            add_edge(host_node, document.doc_id, "HAS_DOCUMENT")

        if document.doc_type == "service" and document.source_page_cid:
            add_edge(document.doc_id, document.source_page_cid, "DERIVED_FROM_PAGE")

        if document.provider_name:
            provider_id = f"provider:{_cid_for_obj({'provider_name': document.provider_name})}"
            add_node(provider_id, "provider", document.provider_name, provider_name=document.provider_name)
            add_edge(provider_id, document.doc_id, "PROVIDES_SERVICE")

        if document.program_name:
            program_id = f"program:{_cid_for_obj({'program_name': document.program_name})}"
            add_node(program_id, "program", document.program_name, program_name=document.program_name)
            add_edge(document.doc_id, program_id, "HAS_PROGRAM")

        for raw_category in re.split(r"[|,;/]+", document.categories or ""):
            category = clean_text(raw_category)
            if not category:
                continue
            category_id = f"category:{_cid_for_obj({'category': category.lower()})}"
            add_node(category_id, "category", category, category=category)
            add_edge(document.doc_id, category_id, "IN_CATEGORY")

        if document.city or document.state:
            location_label = clean_text(" ".join(part for part in [document.city, document.state] if part))
            if location_label:
                location_id = f"location:{_cid_for_obj({'location': location_label})}"
                add_node(location_id, "location", location_label, city=document.city, state=document.state)
                add_edge(document.doc_id, location_id, "LOCATED_IN")

    for source_url, links in page_links.items():
        source_id = page_id_by_url.get(source_url)
        if not source_id:
            continue
        for link in links:
            if link not in known_page_urls:
                continue
            target_id = page_id_by_url.get(link)
            if target_id:
                add_edge(source_id, target_id, "LINKS_TO")

    if bm25_rows:
        keyterms = _select_keyterms_from_bm25(
            bm25_rows,
            keyterms_per_document=keyterms_per_document,
            max_cooccurrence_partners=max_cooccurrence_partners,
        )
        document_index = {document.doc_id: document for document in documents}
        for term_payload in keyterms["term_nodes"]:
            add_node(
                term_payload["node_id"],
                "keyterm",
                term_payload["label"],
                term=term_payload["term"],
                term_corpus_df=term_payload["term_corpus_df"],
                term_global_score=term_payload["term_global_score"],
            )
        for edge in keyterms["doc_term_edges"]:
            document = document_index.get(edge["doc_id"])
            source_content_cid = document.source_content_cid if document else ""
            add_edge(
                edge["doc_id"],
                edge["term_node_id"],
                "HAS_KEYTERM",
                bm25_score=edge["bm25_score"],
                tf=edge["tf"],
                idf=edge["idf"],
                source_content_cid=source_content_cid,
            )
        for edge in keyterms["term_cooccurrence_edges"]:
            add_edge(
                edge["source_term_node_id"],
                edge["target_term_node_id"],
                "CO_OCCURS_WITH",
                shared_document_count=edge["shared_document_count"],
                cooccurrence_score=edge["cooccurrence_score"],
            )

    return nodes, edges


def _select_keyterms_from_bm25(
    bm25_rows: list[dict[str, Any]],
    *,
    keyterms_per_document: int,
    max_cooccurrence_partners: int,
) -> dict[str, list[dict[str, Any]]]:
    if not bm25_rows:
        return {"term_nodes": [], "doc_term_edges": [], "term_cooccurrence_edges": []}

    rows_by_doc: dict[str, list[dict[str, Any]]] = {}
    global_term_scores: Counter[str] = Counter()
    global_term_df: dict[str, int] = {}

    for row in bm25_rows:
        doc_id = str(row.get("doc_id") or "")
        term = str(row.get("term") or "")
        if not doc_id or not term:
            continue
        score = float(row.get("tf") or 0.0) * float(row.get("idf") or 0.0)
        enriched = {
            **row,
            "bm25_score": score,
        }
        rows_by_doc.setdefault(doc_id, []).append(enriched)
        global_term_scores[term] += score
        global_term_df[term] = max(global_term_df.get(term, 0), int(row.get("df") or 0))

    top_terms_by_doc: dict[str, list[dict[str, Any]]] = {}
    for doc_id, rows in rows_by_doc.items():
        ranked = sorted(
            rows,
            key=lambda row: (
                float(row.get("bm25_score") or 0.0),
                float(row.get("idf") or 0.0),
                float(row.get("tf") or 0.0),
                str(row.get("term") or ""),
            ),
            reverse=True,
        )
        top_terms_by_doc[doc_id] = ranked[: max(1, int(keyterms_per_document))]

    term_node_rows: list[dict[str, Any]] = []
    seen_term_nodes: set[str] = set()
    doc_term_edges: list[dict[str, Any]] = []
    term_pair_counts: Counter[tuple[str, str]] = Counter()
    term_pair_scores: Counter[tuple[str, str]] = Counter()

    for doc_id, top_rows in top_terms_by_doc.items():
        doc_term_node_ids: list[str] = []
        doc_term_scores: dict[str, float] = {}
        for row in top_rows:
            term = str(row["term"])
            term_node_id = f"term:{_cid_for_obj({'term': term})}"
            doc_term_node_ids.append(term_node_id)
            doc_term_scores[term_node_id] = float(row["bm25_score"])
            if term_node_id not in seen_term_nodes:
                term_node_rows.append(
                    {
                        "node_id": term_node_id,
                        "label": term,
                        "term": term,
                        "term_corpus_df": int(global_term_df.get(term, 0)),
                        "term_global_score": float(global_term_scores.get(term, 0.0)),
                    }
                )
                seen_term_nodes.add(term_node_id)
            doc_term_edges.append(
                {
                    "doc_id": doc_id,
                    "term_node_id": term_node_id,
                    "bm25_score": float(row["bm25_score"]),
                    "tf": float(row.get("tf") or 0.0),
                    "idf": float(row.get("idf") or 0.0),
                }
            )

        unique_terms = list(dict.fromkeys(doc_term_node_ids))
        for index, source_term in enumerate(unique_terms):
            for target_term in unique_terms[index + 1 :]:
                pair = tuple(sorted((source_term, target_term)))
                source_score = float(doc_term_scores.get(source_term, 0.0))
                target_score = float(doc_term_scores.get(target_term, 0.0))
                term_pair_counts[pair] += 1
                term_pair_scores[pair] += min(source_score, target_score)

    neighbors_by_term: dict[str, list[dict[str, Any]]] = {}
    for (source_term, target_term), shared_count in term_pair_counts.items():
        score = float(term_pair_scores[(source_term, target_term)])
        neighbors_by_term.setdefault(source_term, []).append(
            {
                "source_term_node_id": source_term,
                "target_term_node_id": target_term,
                "shared_document_count": int(shared_count),
                "cooccurrence_score": score,
            }
        )
        neighbors_by_term.setdefault(target_term, []).append(
            {
                "source_term_node_id": target_term,
                "target_term_node_id": source_term,
                "shared_document_count": int(shared_count),
                "cooccurrence_score": score,
            }
        )

    term_cooccurrence_edges: list[dict[str, Any]] = []
    emitted_pairs: set[tuple[str, str]] = set()
    for source_term, neighbor_rows in neighbors_by_term.items():
        ranked_neighbors = sorted(
            neighbor_rows,
            key=lambda row: (
                int(row["shared_document_count"]),
                float(row["cooccurrence_score"]),
                row["target_term_node_id"],
            ),
            reverse=True,
        )[: max(1, int(max_cooccurrence_partners))]
        for row in ranked_neighbors:
            pair = tuple(sorted((row["source_term_node_id"], row["target_term_node_id"])))
            if pair in emitted_pairs:
                continue
            emitted_pairs.add(pair)
            term_cooccurrence_edges.append(row)

    return {
        "term_nodes": term_node_rows,
        "doc_term_edges": doc_term_edges,
        "term_cooccurrence_edges": term_cooccurrence_edges,
    }


def _edge_weight(edge: dict[str, Any]) -> float:
    relation = str(edge.get("relation") or "")
    if relation == "HAS_KEYTERM":
        return max(0.05, min(10.0, float(edge.get("bm25_score") or 0.0)))
    if relation == "CO_OCCURS_WITH":
        return max(0.05, math.log1p(float(edge.get("shared_document_count") or 0.0)))
    if relation in {"PROVIDES_SERVICE", "HAS_PROGRAM", "IN_CATEGORY", "LOCATED_IN"}:
        return 2.0
    if relation == "DERIVED_FROM_PAGE":
        return 1.5
    return 1.0


def build_graph_analytics_rows(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not nodes:
        return [], [], []

    import networkx as nx

    node_by_id = {str(row.get("node_id") or ""): row for row in nodes if row.get("node_id")}
    graph = nx.Graph()
    for node_id in node_by_id:
        graph.add_node(node_id)
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if not source or not target or source == target:
            continue
        weight = _edge_weight(edge)
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
            graph[source][target]["edge_count"] += 1
        else:
            graph.add_edge(source, target, weight=weight, edge_count=1)

    communities: list[set[str]]
    if graph.number_of_edges() == 0:
        communities = [{node_id} for node_id in graph.nodes]
    else:
        try:
            communities = [
                set(community)
                for community in nx.community.louvain_communities(
                    graph,
                    weight="weight",
                    seed=17,
                    resolution=1.0,
                )
            ]
        except Exception:
            communities = [set(component) for component in nx.connected_components(graph)]

    communities = sorted(
        communities,
        key=lambda community: (-len(community), sorted(community)[0] if community else ""),
    )
    community_by_node: dict[str, str] = {}
    for index, community in enumerate(communities):
        community_payload = {
            "kind": "graph_community",
            "index": index,
            "node_ids": sorted(community),
        }
        community_id = f"community:{_cid_for_obj(community_payload)}"
        for node_id in community:
            community_by_node[node_id] = community_id

    degree_by_node = dict(graph.degree())
    weighted_degree_by_node = dict(graph.degree(weight="weight"))

    node_metric_rows: list[dict[str, Any]] = []
    for node_id, node in node_by_id.items():
        node_metric_rows.append(
            {
                "node_id": node_id,
                "node_type": node.get("node_type", ""),
                "label": node.get("label", ""),
                "source_content_cid": node.get("source_content_cid", ""),
                "community_id": community_by_node.get(node_id, ""),
                "degree": int(degree_by_node.get(node_id, 0)),
                "weighted_degree": float(weighted_degree_by_node.get(node_id, 0.0)),
            }
        )

    community_rows: list[dict[str, Any]] = []
    document_community_rows: list[dict[str, Any]] = []
    for community in communities:
        node_rows = [node_by_id[node_id] for node_id in community if node_id in node_by_id]
        if not node_rows:
            continue
        community_id = community_by_node.get(str(node_rows[0].get("node_id") or ""), "")
        node_types = Counter(str(row.get("node_type") or "") for row in node_rows)
        top_terms = Counter(
            str(row.get("term") or row.get("label") or "")
            for row in node_rows
            if row.get("node_type") == "keyterm"
        )
        top_categories = Counter(
            str(row.get("category") or row.get("label") or "")
            for row in node_rows
            if row.get("node_type") == "category"
        )
        top_hosts = Counter(
            str(row.get("host") or row.get("label") or "")
            for row in node_rows
            if row.get("node_type") == "host"
        )
        top_labels = [
            term
            for term, _count in top_terms.most_common(5)
            if term
        ] or [
            category
            for category, _count in top_categories.most_common(5)
            if category
        ] or [
            str(row.get("label") or "")
            for row in node_rows[:5]
            if row.get("label")
        ]
        label = clean_text(" / ".join(top_labels[:3])) or community_id
        payload = {
            "community_id": community_id,
            "label": label,
            "node_count": len(node_rows),
            "node_type_counts": dict(node_types),
            "top_terms": top_terms.most_common(20),
            "top_categories": top_categories.most_common(20),
            "top_hosts": top_hosts.most_common(20),
        }
        community_rows.append(
            {
                "community_id": community_id,
                "community_cid": _cid_for_obj(payload),
                "label": label,
                "node_count": int(len(node_rows)),
                "document_count": int(node_types.get("page", 0) + node_types.get("service", 0)),
                "page_count": int(node_types.get("page", 0)),
                "service_count": int(node_types.get("service", 0)),
                "keyterm_count": int(node_types.get("keyterm", 0)),
                "provider_count": int(node_types.get("provider", 0)),
                "category_count": int(node_types.get("category", 0)),
                "top_terms_json": json.dumps(top_terms.most_common(20), ensure_ascii=False),
                "top_categories_json": json.dumps(top_categories.most_common(20), ensure_ascii=False),
                "top_hosts_json": json.dumps(top_hosts.most_common(20), ensure_ascii=False),
            }
        )
        for row in node_rows:
            node_type = str(row.get("node_type") or "")
            if node_type not in {"page", "service"}:
                continue
            document_community_rows.append(
                {
                    "doc_id": row.get("node_id", ""),
                    "doc_type": node_type,
                    "source_url": row.get("source_url", ""),
                    "source_content_cid": row.get("source_content_cid", ""),
                    "source_page_cid": row.get("source_page_cid", ""),
                    "community_id": community_id,
                    "community_label": label,
                }
            )

    return node_metric_rows, community_rows, document_community_rows


def _page_content_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "page",
        "url": row["url"],
        "title": row["title"],
        "body_text": row["body_text"],
        "links_json": row["links_json"],
        "depth": row["depth"],
        "page_kind": row["kind"],
    }


def _service_content_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "service",
        "id": row["id"],
        "name": row["name"],
        "provider_name": row["provider_name"],
        "program_name": row["program_name"],
        "description": row["description"],
        "address": row["address"],
        "city": row["city"],
        "state": row["state"],
        "zip": row["zip"],
        "phone": row["phone"],
        "email": row["email"],
        "website": row["website"],
        "hours": row["hours"],
        "eligibility": row["eligibility"],
        "languages": row["languages"],
        "categories": row["categories"],
        "accessibility": row["accessibility"],
        "source_url": row["source_url"],
        "search_category": row["search_category"],
        "search_zip": row["search_zip"],
    }


def load_corpus_documents(
    *,
    warehouse_path: Path,
    max_pages: int = 0,
    max_services: int = 0,
) -> tuple[list[CorpusDocument], dict[str, list[str]], dict[str, str]]:
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        pages_limit_sql = f"LIMIT {int(max_pages)}" if max_pages and max_pages > 0 else ""
        pages = con.execute(
            f"""
            WITH ranked AS (
                SELECT
                    url,
                    title,
                    body_text,
                    links_json,
                    depth,
                    kind,
                    quality_score,
                    fetched_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY url
                        ORDER BY fetched_at DESC
                    ) AS rn
                FROM crawl_pages
                WHERE COALESCE(body_text, '') <> ''
            )
            SELECT url, title, body_text, links_json, depth, kind, quality_score, fetched_at
            FROM ranked
            WHERE rn = 1
            ORDER BY fetched_at DESC, url ASC
            {pages_limit_sql}
            """
        ).fetchall()
        page_columns = [str(item[0]) for item in con.description]
        page_rows = [dict(zip(page_columns, row, strict=False)) for row in pages]

        page_links: dict[str, list[str]] = {}
        page_cid_by_url: dict[str, str] = {}
        documents: list[CorpusDocument] = []

        for row in page_rows:
            payload = _page_content_payload(row)
            source_content_cid = _cid_for_obj(payload)
            page_cid_by_url[str(row["url"])] = source_content_cid
            links = json.loads(str(row.get("links_json") or "[]"))
            page_links[str(row["url"])] = [str(link) for link in links]
            title = clean_text(str(row.get("title") or ""))
            text = clean_text(" ".join(part for part in [title, str(row.get("body_text") or "")] if part))
            host = urlparse(str(row["url"])).netloc.lower()
            documents.append(
                CorpusDocument(
                    doc_id=f"page:{source_content_cid}",
                    doc_type="page",
                    title=title or str(row["url"]),
                    text=text,
                    source_url=str(row["url"]),
                    source_content_cid=source_content_cid,
                    source_page_cid=source_content_cid,
                    host=host,
                    metadata_json=json.dumps(payload, ensure_ascii=False),
                )
            )

        services_limit_sql = f"LIMIT {int(max_services)}" if max_services and max_services > 0 else ""
        services = con.execute(
            f"""
            SELECT
                id, name, provider_name, program_name, description, address, city, state, zip,
                phone, email, website, hours, eligibility, languages, categories,
                accessibility, source_url, search_category, search_zip, source
            FROM canonical_processed_services
            ORDER BY source_url ASC, name ASC
            {services_limit_sql}
            """
        ).fetchall()
        service_columns = [str(item[0]) for item in con.description]
        for row in [dict(zip(service_columns, item, strict=False)) for item in services]:
            payload = _service_content_payload(row)
            source_content_cid = _cid_for_obj(payload)
            title = clean_text(str(row.get("name") or ""))
            text_parts = [
                title,
                str(row.get("provider_name") or ""),
                str(row.get("program_name") or ""),
                str(row.get("description") or ""),
                str(row.get("address") or ""),
                str(row.get("city") or ""),
                str(row.get("state") or ""),
                str(row.get("zip") or ""),
                str(row.get("phone") or ""),
                str(row.get("email") or ""),
                str(row.get("website") or ""),
                str(row.get("hours") or ""),
                str(row.get("eligibility") or ""),
                str(row.get("languages") or ""),
                str(row.get("categories") or ""),
                str(row.get("accessibility") or ""),
            ]
            text = clean_text(" ".join(part for part in text_parts if part))
            source_url = str(row.get("source_url") or "")
            source_page_cid = page_cid_by_url.get(source_url, "")
            host = urlparse(source_url).netloc.lower()
            doc_primary = str(row.get("id") or source_content_cid)
            documents.append(
                CorpusDocument(
                    doc_id=f"service:{doc_primary}",
                    doc_type="service",
                    title=title,
                    text=text,
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                    provider_name=clean_text(str(row.get("provider_name") or "")),
                    program_name=clean_text(str(row.get("program_name") or "")),
                    categories=clean_text(
                        " | ".join(
                            part
                            for part in [str(row.get("categories") or ""), str(row.get("search_category") or "")]
                            if clean_text(part)
                        )
                    ),
                    host=host,
                    city=clean_text(str(row.get("city") or "")),
                    state=clean_text(str(row.get("state") or "")),
                    metadata_json=json.dumps(payload, ensure_ascii=False),
                )
            )
    finally:
        con.close()

    return documents, page_links, page_cid_by_url


def build_embeddings(
    documents: list[CorpusDocument],
    *,
    model_name: str,
    batch_size: int = 64,
) -> list[dict[str, Any]]:
    if not documents:
        return []
    _ensure_torchvision_stub()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    vectors = model.encode(
        [document.text for document in documents],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(documents) >= 128,
    )
    rows: list[dict[str, Any]] = []
    for document, vector in zip(documents, vectors, strict=False):
        rows.append(
            {
                "doc_id": document.doc_id,
                "doc_type": document.doc_type,
                "source_url": document.source_url,
                "source_content_cid": document.source_content_cid,
                "source_page_cid": document.source_page_cid,
                "embedding_model": model_name,
                "embedding_dim": int(len(vector)),
                "embedding": [float(value) for value in vector.tolist()],
            }
        )
    return rows


def _write_parquet(records: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(records)
    frame.to_parquet(path, index=False)
    file_cid = _cid_for_file(path)
    return {
        "path": str(path),
        "row_count": int(len(frame)),
        "file_cid": file_cid,
        "size_bytes": int(path.stat().st_size),
    }


def _write_text(path: Path, content: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "path": str(path),
        "row_count": 1,
        "file_cid": _cid_for_file(path),
        "size_bytes": int(path.stat().st_size),
    }


def build_retrieval_package(
    *,
    warehouse_path: Path,
    output_dir: Path,
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    embedding_batch_size: int = 64,
    max_pages: int = 0,
    max_services: int = 0,
) -> dict[str, Any]:
    documents, page_links, page_cid_by_url = load_corpus_documents(
        warehouse_path=warehouse_path,
        max_pages=max_pages,
        max_services=max_services,
    )
    known_page_urls = set(page_cid_by_url.keys())

    document_rows = [
        {
            "doc_id": document.doc_id,
            "doc_type": document.doc_type,
            "title": document.title,
            "text": document.text,
            "source_url": document.source_url,
            "source_content_cid": document.source_content_cid,
            "source_page_cid": document.source_page_cid,
            "provider_name": document.provider_name,
            "program_name": document.program_name,
            "categories": document.categories,
            "host": document.host,
            "city": document.city,
            "state": document.state,
            "metadata_json": document.metadata_json,
        }
        for document in documents
    ]
    bm25_document_rows, bm25_term_rows = build_bm25_rows(documents)
    embedding_rows = build_embeddings(
        documents,
        model_name=embedding_model,
        batch_size=embedding_batch_size,
    )
    graph_nodes, graph_edges = build_graph_rows(
        documents,
        page_links=page_links,
        known_page_urls=known_page_urls,
        bm25_rows=bm25_term_rows,
    )
    graph_node_metrics, graph_communities, document_communities = build_graph_analytics_rows(
        graph_nodes,
        graph_edges,
    )

    artifact_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []

    def record_artifact(name: str, relative_path: str, records: list[dict[str, Any]]) -> None:
        info = _write_parquet(records, output_dir / relative_path)
        artifact_rows.append(
            {
                "artifact_name": name,
                "artifact_kind": "parquet",
                **info,
            }
        )
        manifest_rows.append(
            {
                "artifact_name": name,
                "artifact_kind": "parquet",
                "artifact_path": relative_path,
                "artifact_cid": info["file_cid"],
                "row_count": info["row_count"],
                "size_bytes": info["size_bytes"],
            }
        )

    record_artifact("documents", "content/documents.parquet", document_rows)
    record_artifact("bm25_documents", "retrieval/bm25_documents.parquet", bm25_document_rows)
    record_artifact("bm25_terms", "retrieval/bm25_terms.parquet", bm25_term_rows)
    record_artifact("vector_embeddings", "retrieval/vector_embeddings.parquet", embedding_rows)
    record_artifact("knowledge_graph_nodes", "graph/knowledge_graph_nodes.parquet", graph_nodes)
    record_artifact("knowledge_graph_edges", "graph/knowledge_graph_edges.parquet", graph_edges)
    record_artifact("graph_node_metrics", "graph/graph_node_metrics.parquet", graph_node_metrics)
    record_artifact("graph_communities", "graph/graph_communities.parquet", graph_communities)
    record_artifact("document_communities", "graph/document_communities.parquet", document_communities)

    build_manifest = {
        "warehouse_path": str(warehouse_path),
        "document_count": len(document_rows),
        "page_document_count": sum(1 for row in document_rows if row["doc_type"] == "page"),
        "service_document_count": sum(1 for row in document_rows if row["doc_type"] == "service"),
        "bm25_term_count": len(bm25_term_rows),
        "embedding_count": len(embedding_rows),
        "embedding_model": embedding_model,
        "graph_node_count": len(graph_nodes),
        "graph_edge_count": len(graph_edges),
        "graph_community_count": len(graph_communities),
        "document_community_count": len(document_communities),
        "artifacts": manifest_rows,
    }
    build_manifest["build_manifest_cid"] = _cid_for_obj(build_manifest)
    artifact_rows.append(
        {
            "artifact_name": "artifact_manifest",
            "artifact_kind": "json",
            **_write_text(output_dir / "manifest" / "build_manifest.json", json.dumps(build_manifest, indent=2)),
        }
    )
    record_artifact("artifact_inventory", "manifest/artifact_inventory.parquet", artifact_rows)

    readme = "\n".join(
        [
            "# 211 Retrieval Package",
            "",
            f"- Documents: {build_manifest['document_count']}",
            f"- Page documents: {build_manifest['page_document_count']}",
            f"- Service documents: {build_manifest['service_document_count']}",
            f"- Embedding model: `{embedding_model}`",
            f"- Graph nodes: {build_manifest['graph_node_count']}",
            f"- Graph edges: {build_manifest['graph_edge_count']}",
            f"- Graph communities: {build_manifest['graph_community_count']}",
            "",
            "Every artifact row is keyed by `source_content_cid` or derived `node_cid`/`edge_cid` so downstream systems can trace back to the original 211 scraped content.",
        ]
    )
    _write_text(output_dir / "README.md", readme)

    return build_manifest


def upload_package_to_huggingface(
    *,
    package_dir: Path,
    repo_id: str,
    private: bool = False,
    force_reupload: bool = False,
) -> dict[str, Any]:
    _bootstrap_local_ipfs_datasets()
    from huggingface_hub import HfApi
    from ipfs_datasets_py.processors.legal_scrapers.huggingface_pipeline_engine import (
        UploadToHuggingFaceInParallel,
    )

    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    configs = SimpleNamespace(
        REPO_ID=repo_id,
        REQUEST_LIMIT_PER_HOUR=300,
        HUGGING_FACE_USER_ACCESS_TOKEN=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN"),
        paths=SimpleNamespace(INPUT_FROM_SQL=str(package_dir)),
    )
    uploader = UploadToHuggingFaceInParallel(configs=configs)
    return asyncio.run(
        uploader.upload_to_hugging_face_in_parallel(
            output_dir=package_dir,
            target_dir_name="data",
            max_concurrency=4,
            retry_limit=3,
            force_reupload=force_reupload,
        )
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build vector, BM25, graph, and Parquet package for 211 crawl data")
    parser.add_argument(
        "--warehouse-path",
        type=Path,
        default=Path("data/live/state/etl_warehouse.duckdb"),
        help="DuckDB warehouse path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/retrieval_package"),
        help="Package output directory",
    )
    parser.add_argument(
        "--embedding-model",
        default="BAAI/bge-small-en-v1.5",
        help="SentenceTransformers embedding model",
    )
    parser.add_argument("--embedding-batch-size", type=int, default=64)
    parser.add_argument("--max-pages", type=int, default=0, help="Optional page cap for bounded builds")
    parser.add_argument("--max-services", type=int, default=0, help="Optional service cap for bounded builds")
    parser.add_argument("--hf-repo-id", default="", help="Optional Hugging Face dataset repo id to upload into")
    parser.add_argument("--hf-private", action="store_true", help="Create the HF repo as private when uploading")
    parser.add_argument(
        "--force-upload",
        action="store_true",
        help="Reupload package folders even if the repo already has files with matching names",
    )
    parser.add_argument("--skip-upload", action="store_true", help="Build local artifacts only")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    manifest = build_retrieval_package(
        warehouse_path=args.warehouse_path,
        output_dir=args.output_dir,
        embedding_model=args.embedding_model,
        embedding_batch_size=args.embedding_batch_size,
        max_pages=args.max_pages,
        max_services=args.max_services,
    )
    result: dict[str, Any] = {"build": manifest}
    if args.hf_repo_id and not args.skip_upload:
        result["upload"] = upload_package_to_huggingface(
            package_dir=args.output_dir,
            repo_id=args.hf_repo_id,
            private=bool(args.hf_private),
            force_reupload=bool(args.force_upload),
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
