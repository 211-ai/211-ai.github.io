from __future__ import annotations

from scraper.build_retrieval_package import (
    CorpusDocument,
    build_bm25_rows,
    build_graph_analytics_rows,
    build_graph_rows,
    tokenize_text,
)


def test_tokenize_text_removes_basic_stopwords():
    tokens = tokenize_text("The food pantry is open on Monday and Tuesday.")
    assert "the" not in tokens
    assert "and" not in tokens
    assert "food" in tokens
    assert "pantry" in tokens


def test_build_bm25_rows_returns_documents_and_terms():
    documents = [
        CorpusDocument(
            doc_id="page:one",
            doc_type="page",
            title="Food Pantry",
            text="Food pantry open monday",
            source_url="https://www.211info.org/food",
            source_content_cid="cid-page-one",
            source_page_cid="cid-page-one",
        ),
        CorpusDocument(
            doc_id="service:two",
            doc_type="service",
            title="Housing Program",
            text="Housing shelter program intake phone",
            source_url="https://gethelp.211info.org/get-help/housing-shelter/example/",
            source_content_cid="cid-service-two",
            source_page_cid="cid-page-two",
        ),
    ]

    doc_rows, term_rows = build_bm25_rows(documents)

    assert len(doc_rows) == 2
    assert any(row["term"] == "food" and row["doc_id"] == "page:one" for row in term_rows)
    assert any(row["term"] == "housing" and row["doc_id"] == "service:two" for row in term_rows)


def test_build_graph_rows_creates_provider_category_and_link_edges():
    page = CorpusDocument(
        doc_id="page:one",
        doc_type="page",
        title="Example Page",
        text="Example page body",
        source_url="https://www.211info.org/example",
        source_content_cid="cid-page-one",
        source_page_cid="cid-page-one",
        host="www.211info.org",
    )
    service = CorpusDocument(
        doc_id="service:two",
        doc_type="service",
        title="Example Service",
        text="Example service description",
        source_url="https://www.211info.org/example",
        source_content_cid="cid-service-two",
        source_page_cid="cid-page-one",
        provider_name="Example Provider",
        program_name="Example Program",
        categories="Housing | Shelter",
        host="www.211info.org",
        city="Portland",
        state="OR",
    )

    _, bm25_rows = build_bm25_rows([page, service])

    nodes, edges = build_graph_rows(
        [page, service],
        page_links={"https://www.211info.org/example": ["https://www.211info.org/example"]},
        known_page_urls={"https://www.211info.org/example"},
        bm25_rows=bm25_rows,
        keyterms_per_document=4,
        max_cooccurrence_partners=4,
    )

    node_types = {row["node_type"] for row in nodes}
    relations = {row["relation"] for row in edges}

    assert "provider" in node_types
    assert "program" in node_types
    assert "category" in node_types
    assert "host" in node_types
    assert "keyterm" in node_types
    assert "DERIVED_FROM_PAGE" in relations
    assert "PROVIDES_SERVICE" in relations
    assert "HAS_PROGRAM" in relations
    assert "IN_CATEGORY" in relations
    assert "HAS_KEYTERM" in relations
    assert "CO_OCCURS_WITH" in relations


def test_build_graph_analytics_rows_creates_communities_and_document_membership():
    page = CorpusDocument(
        doc_id="page:one",
        doc_type="page",
        title="Food Help",
        text="food pantry groceries",
        source_url="https://www.211info.org/food",
        source_content_cid="cid-page-one",
        source_page_cid="cid-page-one",
        host="www.211info.org",
    )
    service = CorpusDocument(
        doc_id="service:two",
        doc_type="service",
        title="Food Pantry",
        text="food pantry groceries intake",
        source_url="https://www.211info.org/food",
        source_content_cid="cid-service-two",
        source_page_cid="cid-page-one",
        provider_name="Example Provider",
        categories="Food",
        host="www.211info.org",
    )
    _, bm25_rows = build_bm25_rows([page, service])
    nodes, edges = build_graph_rows(
        [page, service],
        page_links={},
        known_page_urls=set(),
        bm25_rows=bm25_rows,
        keyterms_per_document=4,
        max_cooccurrence_partners=4,
    )

    node_metrics, communities, document_communities = build_graph_analytics_rows(nodes, edges)

    assert len(node_metrics) == len(nodes)
    assert communities
    assert any(row["doc_id"] == "page:one" for row in document_communities)
    assert any(row["doc_id"] == "service:two" for row in document_communities)
    assert all(row["community_id"] for row in document_communities)
