from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scraper.browser_graphrag_corpus import build_browser_graphrag_corpus


def _write_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _make_package(root: Path) -> Path:
    package_dir = root / "retrieval_package"
    _write_parquet(
        package_dir / "content" / "documents.parquet",
        [
            {
                "doc_id": "page:cid-page",
                "doc_type": "page",
                "title": "Food help",
                "text": "Food pantry and groceries.",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-page",
                "source_page_cid": "cid-page",
                "provider_name": "",
                "program_name": "",
                "categories": "Food",
                "host": "example.org",
                "city": "Portland",
                "state": "OR",
                "metadata_json": "{}",
            },
            {
                "doc_id": "service:cid-service",
                "doc_type": "service",
                "title": "Community pantry",
                "text": "Community pantry has intake phone.",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-service",
                "source_page_cid": "cid-page",
                "provider_name": "Community Provider",
                "program_name": "Pantry",
                "categories": "Food",
                "host": "example.org",
                "city": "Portland",
                "state": "OR",
                "metadata_json": "{}",
            },
        ],
    )
    _write_parquet(
        package_dir / "retrieval" / "bm25_documents.parquet",
        [
            {
                "doc_id": "page:cid-page",
                "doc_type": "page",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-page",
                "source_page_cid": "cid-page",
                "doc_length": 4,
            },
            {
                "doc_id": "service:cid-service",
                "doc_type": "service",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-service",
                "source_page_cid": "cid-page",
                "doc_length": 5,
            },
        ],
    )
    _write_parquet(
        package_dir / "retrieval" / "bm25_terms.parquet",
        [
            {
                "doc_id": "page:cid-page",
                "doc_type": "page",
                "source_content_cid": "cid-page",
                "source_page_cid": "cid-page",
                "term": "food",
                "tf": 2.0,
                "df": 2,
                "idf": 0.2,
                "doc_length": 4.0,
                "avg_doc_length": 4.5,
                "document_count": 2,
            },
            {
                "doc_id": "service:cid-service",
                "doc_type": "service",
                "source_content_cid": "cid-service",
                "source_page_cid": "cid-page",
                "term": "pantry",
                "tf": 3.0,
                "df": 2,
                "idf": 0.5,
                "doc_length": 5.0,
                "avg_doc_length": 4.5,
                "document_count": 2,
            },
        ],
    )
    _write_parquet(
        package_dir / "retrieval" / "vector_embeddings.parquet",
        [
            {
                "doc_id": "page:cid-page",
                "doc_type": "page",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-page",
                "source_page_cid": "cid-page",
                "embedding_model": "test-embedding",
                "embedding_dim": 3,
                "embedding": [0.1, 0.2, 0.3],
            },
            {
                "doc_id": "service:cid-service",
                "doc_type": "service",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-service",
                "source_page_cid": "cid-page",
                "embedding_model": "test-embedding",
                "embedding_dim": 3,
                "embedding": [0.4, 0.5, 0.6],
            },
        ],
    )
    _write_parquet(
        package_dir / "graph" / "knowledge_graph_nodes.parquet",
        [
            {
                "node_id": "page:cid-page",
                "node_type": "page",
                "label": "Food help",
                "host": "example.org",
                "node_cid": "node-page",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-page",
                "source_page_cid": "cid-page",
            },
            {
                "node_id": "service:cid-service",
                "node_type": "service",
                "label": "Community pantry",
                "node_cid": "node-service",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-service",
                "source_page_cid": "cid-page",
            },
            {
                "node_id": "term:food",
                "node_type": "keyterm",
                "label": "food",
                "node_cid": "node-term-food",
                "term": "food",
            },
        ],
    )
    _write_parquet(
        package_dir / "graph" / "knowledge_graph_edges.parquet",
        [
            {
                "source": "page:cid-page",
                "target": "term:food",
                "relation": "HAS_KEYTERM",
                "edge_cid": "edge-page-term",
                "bm25_score": 0.4,
                "tf": 2.0,
                "idf": 0.2,
            },
            {
                "source": "service:cid-service",
                "target": "page:cid-page",
                "relation": "DERIVED_FROM_PAGE",
                "edge_cid": "edge-service-page",
            },
        ],
    )
    _write_parquet(
        package_dir / "graph" / "graph_communities.parquet",
        [
            {
                "community_id": "community:food",
                "community_cid": "cid-community",
                "label": "food",
                "node_count": 3,
                "document_count": 2,
                "page_count": 1,
                "service_count": 1,
                "keyterm_count": 1,
                "provider_count": 0,
                "category_count": 0,
                "top_terms_json": '[["food",2]]',
                "top_categories_json": "[]",
                "top_hosts_json": '[["example.org",1]]',
            }
        ],
    )
    _write_parquet(
        package_dir / "graph" / "document_communities.parquet",
        [
            {
                "doc_id": "page:cid-page",
                "doc_type": "page",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-page",
                "source_page_cid": "cid-page",
                "community_id": "community:food",
                "community_label": "food",
            },
            {
                "doc_id": "service:cid-service",
                "doc_type": "service",
                "source_url": "https://example.org/food",
                "source_content_cid": "cid-service",
                "source_page_cid": "cid-page",
                "community_id": "community:food",
                "community_label": "food",
            },
        ],
    )
    (package_dir / "manifest").mkdir(parents=True, exist_ok=True)
    (package_dir / "manifest" / "build_manifest.json").write_text(
        json.dumps(
            {
                "build_manifest_cid": "cid-manifest",
                "document_count": 2,
                "graph_node_count": 3,
                "graph_edge_count": 2,
            }
        ),
        encoding="utf-8",
    )
    return package_dir


def _make_portal_parquet(root: Path) -> Path:
    portal_path = root / "documents.portal.parquet"
    _write_parquet(
        portal_path,
        [
            {
                "service_doc_id": "service:cid-service",
                "phones": json.dumps(
                    [
                        {
                            "contact_id": "service:cid-service:phone:0",
                            "label": "main",
                            "tel_url": "tel:+15035550100",
                            "sms_url": "sms:+15035550100",
                            "value": "(503) 555-0100",
                            "confidence": 0.99,
                        }
                    ]
                ),
                "emails": json.dumps([]),
                "websites": json.dumps(
                    [
                        {
                            "contact_id": "service:cid-service:website:0",
                            "label": "apply",
                            "url": "https://example.org/apply",
                            "value": "https://example.org/apply",
                            "confidence": 0.99,
                        }
                    ]
                ),
                "addresses": json.dumps(
                    [
                        {
                            "location_id": "service:cid-service:location:0",
                            "address": "123 Main St, Portland, OR 97204",
                            "street": "123 Main St",
                            "city": "Portland",
                            "state": "OR",
                            "postal_code": "97204",
                            "maps_query": "123 Main St Portland OR 97204",
                            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=123+Main+St+Portland+OR+97204",
                            "apple_maps_url": "https://maps.apple.com/?q=123+Main+St+Portland+OR+97204",
                            "geo_url": "geo:0,0?q=123+Main+St+Portland+OR+97204",
                            "geo": {"lat": None, "lon": None, "precision": "address_query"},
                            "confidence": 0.99,
                        }
                    ]
                ),
                "hours": json.dumps([{"label": "hours", "value": "Mon-Fri 9am-5pm", "confidence": 0.97}]),
                "eligibility": json.dumps([{"label": "eligibility", "value": "Low income households", "confidence": 0.97}]),
                "intake_steps": json.dumps([{"label": "intake", "value": "Apply online or call first", "confidence": 0.97}]),
                "required_documents": json.dumps([{"label": "documents", "value": "Photo ID", "confidence": 0.97}]),
                "fees": json.dumps([]),
                "languages": json.dumps([]),
                "accessibility": json.dumps([]),
                "travel_info": json.dumps([{"label": "travel", "value": "Bus stop nearby", "confidence": 0.97}]),
                "area_served": json.dumps([{"label": "area served", "value": "Multnomah County", "confidence": 0.97}]),
                "geo": json.dumps({"lat": None, "lon": None, "precision": "address_query"}),
            }
        ],
    )
    return portal_path


def test_build_browser_graphrag_corpus_writes_static_assets(tmp_path: Path):
    package_dir = _make_package(tmp_path)
    portal_parquet_path = _make_portal_parquet(tmp_path)
    output_dir = tmp_path / "browser_corpus"

    result = build_browser_graphrag_corpus(
        package_dir=package_dir,
        output_dir=output_dir,
        portal_parquet_path=portal_parquet_path,
        max_terms_per_document=8,
        max_edges_per_document=4,
    )

    assert result["document_count"] == 2
    assert result["service_document_count"] == 1
    assert result["service_phone_count"] == 1
    assert result["service_address_count"] == 1
    assert result["service_intake_step_count"] == 1
    assert result["service_required_document_count"] == 1
    assert result["embedding_count"] == 2
    assert result["embedding_dimension"] == 3
    assert result["graph_neighborhood_count"] == 2

    documents = pd.read_parquet(output_dir / "generated" / "documents.parquet").to_dict(orient="records")
    document_index = json.loads((output_dir / "generated" / "document-index.json").read_text())
    bm25 = json.loads((output_dir / "generated" / "bm25-documents.json").read_text())
    embedding_index = json.loads((output_dir / "generated" / "embedding-index.json").read_text())
    graph_index = json.loads((output_dir / "generated" / "graph-neighborhood-index.json").read_text())
    graph_shard = json.loads((output_dir / graph_index["docIdToShard"]["service:cid-service"]).read_text())
    communities = json.loads((output_dir / "generated" / "graph-communities.json").read_text())
    service_geo_index = json.loads((output_dir / "generated" / "service-geo-index.json").read_text())
    artifacts = json.loads((output_dir / "artifacts.manifest.json").read_text())

    assert documents[0]["source_content_cid"] == "cid-page"
    assert document_index["contentCidToIndex"]["cid-service"] == 1
    assert documents[1]["phones"][0]["tel_url"] == "tel:+15035550100"
    assert documents[1]["addresses"][0]["maps_query"] == "123 Main St Portland OR 97204"
    assert documents[1]["intake_steps"][0]["value"] == "Apply online or call first"
    assert not (output_dir / "generated" / "documents.json").exists()
    assert bm25["documents"][1]["terms"]["pantry"] == 3.0
    assert embedding_index["binary"] == "embeddings.f32"
    assert (output_dir / "generated" / "embeddings.f32").stat().st_size == 2 * 3 * 4
    assert not (output_dir / "generated" / "graph-neighborhoods.json").exists()
    assert graph_index["neighborhoodCount"] == 2
    assert graph_index["shardCount"] == 1
    assert graph_index["shards"][0]["cid"]
    assert "service:cid-service" in graph_shard["neighborhoods"]
    assert graph_shard["neighborhoods"]["service:cid-service"]["edge_ids"] == ["edge-service-page"]
    assert graph_shard["edges"]["edge-service-page"]["relation"] == "DERIVED_FROM_PAGE"
    assert graph_shard["nodes"]["term:food"]["label"] == "food"
    assert communities["communities"][0]["top_terms"] == [["food", 2]]
    assert service_geo_index["serviceCount"] == 1
    assert service_geo_index["docsWithAddress"] == 1
    assert service_geo_index["docsByCity"]["portland"] == ["service:cid-service"]
    assert "multnomah" in service_geo_index["docsByPlaceTerm"]
    assert artifacts["sourcePackage"]["build_manifest_cid"] == "cid-manifest"
    generated_manifest = json.loads((output_dir / "generated" / "generated-manifest.json").read_text())
    assert generated_manifest["serviceDocumentCount"] == 1
    assert generated_manifest["servicePhoneCount"] == 1
    assert generated_manifest["serviceAddressCount"] == 1
    assert generated_manifest["serviceIntakeStepCount"] == 1
    assert generated_manifest["serviceRequiredDocumentCount"] == 1
