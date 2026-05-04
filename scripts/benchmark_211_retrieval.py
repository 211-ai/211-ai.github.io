#!/usr/bin/env python3
"""Benchmark high-value 211 browser-corpus retrieval queries.

The benchmark mirrors the browser BM25/vector/hybrid score fusion closely
enough to catch obvious relevance regressions without requiring a browser.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_BROWSER_CORPUS_DIR = Path("wallet_interface/ui/public/corpus/211-info/current")
DEFAULT_QUERIES = [
    {
        "query": "food pantry",
        "expected_terms": ["food", "pantry"],
    },
    {
        "query": "emergency shelter",
        "expected_terms": ["shelter", "housing", "homeless"],
    },
    {
        "query": "utility assistance",
        "expected_terms": ["utility", "utilities", "electric", "gas", "energy", "liheap"],
    },
    {
        "query": "rental assistance",
        "expected_terms": ["rent", "rental", "housing"],
    },
    {
        "query": "mental health crisis support",
        "expected_terms": ["mental", "crisis", "behavioral", "counseling"],
    },
    {
        "query": "transportation",
        "expected_terms": ["transportation", "ride", "transit", "bus"],
    },
]
STOP_WORDS = {
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
    "how",
    "i",
    "in",
    "is",
    "it",
    "near",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class RankedResult:
    doc_id: str
    score: float
    keyword: float = 0.0
    vector: float = 0.0
    metadata: float = 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-corpus-dir", type=Path, default=DEFAULT_BROWSER_CORPUS_DIR)
    parser.add_argument("--queries-json", type=Path, help="Optional JSON query spec list.")
    parser.add_argument("--output", type=Path, help="Optional path for benchmark JSON output.")
    parser.add_argument("--candidate-limit", type=int, default=200)
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--skip-vector", action="store_true", help="Only run keyword checks.")
    args = parser.parse_args()

    benchmark = run_benchmark(
        browser_corpus_dir=args.browser_corpus_dir,
        query_specs=load_query_specs(args.queries_json),
        candidate_limit=args.candidate_limit,
        limit=args.limit,
        top_k=args.top_k,
        include_vector=not args.skip_vector,
    )
    rendered = json.dumps(benchmark, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if benchmark["passed"] else 1


def run_benchmark(
    *,
    browser_corpus_dir: Path,
    query_specs: list[dict[str, Any]],
    candidate_limit: int,
    limit: int,
    top_k: int,
    include_vector: bool,
) -> dict[str, Any]:
    generated_dir = browser_corpus_dir / "generated"
    documents = load_json(generated_dir / "documents.json")
    bm25_payload = load_json(generated_dir / "bm25-documents.json")
    embedding_index = load_json(generated_dir / "embedding-index.json")
    documents_by_id = {document["doc_id"]: document for document in documents}

    vector_context: dict[str, Any] | None = None
    if include_vector:
        vector_context = load_vector_context(generated_dir, embedding_index)

    records = []
    failed = False
    for spec in query_specs:
        query = str(spec["query"])
        expected_terms = [str(term).lower() for term in spec.get("expected_terms", [])]
        keyword_results = search_keyword(
            query,
            bm25_payload=bm25_payload,
            documents_by_id=documents_by_id,
            candidate_limit=candidate_limit,
            limit=limit,
        )
        keyword_record = summarize_mode(
            "keyword",
            query,
            expected_terms,
            keyword_results,
            documents_by_id,
            top_k,
        )
        mode_records = [keyword_record]

        if vector_context is not None:
            vector_scores = search_vector_scores(query, vector_context, candidate_limit)
            vector_results = rank_from_scores(
                mode="vector",
                query=query,
                documents_by_id=documents_by_id,
                keyword_scores={},
                vector_scores=vector_scores,
                limit=limit,
            )
            hybrid_results = rank_from_scores(
                mode="hybrid",
                query=query,
                documents_by_id=documents_by_id,
                keyword_scores={result.doc_id: result.score for result in keyword_results[:candidate_limit]},
                vector_scores=vector_scores,
                limit=limit,
            )
            mode_records.append(
                summarize_mode("vector", query, expected_terms, vector_results, documents_by_id, top_k)
            )
            mode_records.append(
                summarize_mode("hybrid", query, expected_terms, hybrid_results, documents_by_id, top_k)
            )

        required_records = [record for record in mode_records if record["mode"] in {"keyword", "hybrid"}]
        query_passed = all(record["passed"] for record in required_records)
        failed = failed or not query_passed
        records.append(
            {
                "query": query,
                "expected_terms": expected_terms,
                "passed": query_passed,
                "modes": mode_records,
            }
        )

    return {
        "schema_version": 1,
        "browser_corpus_dir": str(browser_corpus_dir),
        "document_count": len(documents),
        "embedding_model": embedding_index.get("embeddingModel"),
        "browser_embedding_model": embedding_index.get("browserEmbeddingModel"),
        "vector_enabled": vector_context is not None,
        "required_modes": ["keyword", "hybrid"] if vector_context is not None else ["keyword"],
        "top_k": top_k,
        "passed": not failed,
        "queries": records,
    }


def load_query_specs(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return DEFAULT_QUERIES
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError("Query spec must be a JSON list")
    return payload


def load_vector_context(generated_dir: Path, embedding_index: dict[str, Any]) -> dict[str, Any]:
    try:
        from scraper.build_retrieval_package import _ensure_torchvision_stub

        _ensure_torchvision_stub()
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - depends on local ML environment
        raise RuntimeError("Vector benchmark requires sentence-transformers and torch") from exc

    model_name = str(embedding_index.get("embeddingModel") or "BAAI/bge-small-en-v1.5")
    model = SentenceTransformer(model_name)
    vectors = np.fromfile(generated_dir / str(embedding_index["binary"]), dtype="<f4")
    expected_size = int(embedding_index["count"]) * int(embedding_index["dimension"])
    if vectors.size != expected_size:
        raise ValueError(f"Embedding vector length {vectors.size} did not match {expected_size}")
    vectors = vectors.reshape((int(embedding_index["count"]), int(embedding_index["dimension"])))
    vector_norms = np.linalg.norm(vectors, axis=1)
    return {
        "model": model,
        "vectors": vectors,
        "vector_norms": vector_norms,
        "doc_ids": embedding_index["doc_ids"],
    }


def search_keyword(
    query: str,
    *,
    bm25_payload: dict[str, Any],
    documents_by_id: dict[str, dict[str, Any]],
    candidate_limit: int,
    limit: int,
) -> list[RankedResult]:
    terms = tokenize(query)
    if not terms:
        return []
    ranked = []
    for document in bm25_payload["documents"]:
        score = score_bm25_document(
            document,
            terms,
            k1=float(bm25_payload["k1"]),
            b=float(bm25_payload["b"]),
            avgdl=float(bm25_payload["avgdl"]),
        )
        if score > 0:
            ranked.append(RankedResult(doc_id=document["doc_id"], score=score))
    ranked.sort(key=lambda result: result.score, reverse=True)
    keyword_scores = {result.doc_id: result.score for result in ranked[:candidate_limit]}
    return rank_from_scores(
        mode="keyword",
        query=query,
        documents_by_id=documents_by_id,
        keyword_scores=keyword_scores,
        vector_scores={},
        limit=limit,
    )


def search_vector_scores(query: str, vector_context: dict[str, Any], candidate_limit: int) -> dict[str, float]:
    query_vector = vector_context["model"].encode([query], normalize_embeddings=True)[0].astype(np.float32)
    query_norm = float(np.linalg.norm(query_vector))
    if query_norm == 0:
        return {}
    vectors = vector_context["vectors"]
    vector_norms = vector_context["vector_norms"]
    denominator = np.maximum(vector_norms * query_norm, 1e-12)
    scores = (vectors @ query_vector) / denominator
    top_indexes = np.argsort(scores)[-candidate_limit:][::-1]
    doc_ids = vector_context["doc_ids"]
    return {doc_ids[int(index)]: float(scores[int(index)]) for index in top_indexes}


def rank_from_scores(
    *,
    mode: str,
    query: str,
    documents_by_id: dict[str, dict[str, Any]],
    keyword_scores: dict[str, float],
    vector_scores: dict[str, float],
    limit: int,
) -> list[RankedResult]:
    normalized_keyword = normalize_scores(keyword_scores)
    normalized_vector = normalize_scores(vector_scores)
    candidates = set(keyword_scores) | set(vector_scores)
    results = []
    for doc_id in candidates:
        document = documents_by_id.get(doc_id)
        if not document:
            continue
        keyword = normalized_keyword.get(doc_id, 0.0)
        vector = normalized_vector.get(doc_id, 0.0)
        metadata = metadata_score(document, query)
        if mode == "keyword":
            score = keyword * 2 + metadata
        elif mode == "vector":
            score = vector * 2 + metadata * 0.5
        else:
            score = keyword * 1.4 + vector * 2 + metadata
        results.append(RankedResult(doc_id=doc_id, score=score, keyword=keyword, vector=vector, metadata=metadata))
    results.sort(key=lambda result: result.score, reverse=True)
    return results[:limit]


def summarize_mode(
    mode: str,
    query: str,
    expected_terms: list[str],
    results: list[RankedResult],
    documents_by_id: dict[str, dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    top_results = []
    matched = False
    for rank, result in enumerate(results, start=1):
        document = documents_by_id[result.doc_id]
        haystack = searchable_text(document)
        is_match = any(term in haystack for term in expected_terms)
        matched = matched or (rank <= top_k and is_match)
        top_results.append(
            {
                "rank": rank,
                "doc_id": result.doc_id,
                "doc_type": document.get("doc_type"),
                "title": document.get("title"),
                "provider_name": document.get("provider_name"),
                "program_name": document.get("program_name"),
                "categories": document.get("categories"),
                "source_url": document.get("source_url"),
                "score": round(result.score, 6),
                "score_parts": {
                    "keyword": round(result.keyword, 6),
                    "vector": round(result.vector, 6),
                    "metadata": round(result.metadata, 6),
                },
                "matched_expected_terms": is_match,
            }
        )
    return {
        "mode": mode,
        "query": query,
        "passed": matched,
        "top_k": top_k,
        "top_results": top_results,
    }


def score_bm25_document(document: dict[str, Any], query_terms: list[str], k1: float, b: float, avgdl: float) -> float:
    score = 0.0
    doc_length = max(float(document.get("document_length") or 0), 1.0)
    length_norm = 1 - b + (b * doc_length) / max(avgdl, 1.0)
    terms = document.get("terms") or {}
    term_idf = document.get("term_idf") or {}
    for term in query_terms:
        tf = float(terms.get(term) or 0)
        if tf <= 0:
            continue
        idf = float(term_idf.get(term) or 1)
        score += idf * ((tf * (k1 + 1)) / (tf + k1 * length_norm))
    return score


def metadata_score(document: dict[str, Any], query: str) -> float:
    lowered_query = query.lower()
    score = 0.0
    if lowered_query in str(document.get("title") or "").lower():
        score += 1.5
    for key in ["provider_name", "program_name", "categories", "city"]:
        value = str(document.get(key) or "").lower()
        if value and lowered_query in value:
            score += 0.5
    return score


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    values = list(scores.values())
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return {key: 1.0 for key in scores}
    return {key: (value - minimum) / (maximum - minimum) for key, value in scores.items()}


def searchable_text(document: dict[str, Any]) -> str:
    return " ".join(
        str(document.get(key) or "")
        for key in ["title", "provider_name", "program_name", "categories", "city", "state", "text", "source_url"]
    ).lower()


def tokenize(text: str) -> list[str]:
    clean = "".join(character.lower() if character.isalnum() or character in {" ", "-"} else " " for character in text)
    return [term for term in (part.strip() for part in clean.split()) if len(term) > 1 and term not in STOP_WORDS]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    sys.exit(main())
