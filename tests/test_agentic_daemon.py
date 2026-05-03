from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import duckdb

from scraper.agentic_daemon import AgenticCrawlerDaemon, CrawlItem, CrawlState, FetchResult
from scraper.agentic_daemon import (
    choose_result_display_name,
    extract_address,
    extract_result_page_services,
    normalize_provider_name,
    split_provider_program_names,
)
from scraper.backfill_pattern_stats import backfill_pattern_stats
from scraper.config import Config
from scraper.duckdb_state import DuckDBCrawlStore, pattern_prefix_for_url, score_queue_item
from scraper.duckdb_etl import DuckDBETLWarehouse
from scraper.export_canonical_services import export_canonical_services
from scraper.reextract_warehouse import reextract_warehouse
from scraper.supervisor import SelfHealingSupervisor, SupervisorConfig


class StubFetcher:
    def fetch(self, url: str) -> FetchResult:
        html = """
        <html>
          <head><title>Example Food Program</title></head>
          <body>
            <main>
              <h1>Example Food Program</h1>
              <p>Service provides food resources. Hours: Monday 9-5.</p>
              <p>Address: 123 Main St, Portland, OR 97201. Call 503-555-1212.</p>
              <a href="/about-211info/find-services/">Find services</a>
            </main>
          </body>
        </html>
        """
        return FetchResult(
            url=url,
            title="Example Food Program",
            text=(
                "Example Food Program. Service provides food resources. "
                "Hours: Monday 9-5. 123 Main St, Portland, OR 97201. "
                "Call 503-555-1212."
            ),
            html=html,
            links=["https://www.211info.org/about-211info/find-services/"],
            success=True,
            quality_score=1.0,
        )

    def archive(self, result: FetchResult, metadata: dict) -> dict:
        return {"status": "success", "archive_id": "stub"}


class StubDatasetSink:
    def save_snapshot(self, records: list[dict], destination):
        destination.write_text(json.dumps({"data": records}), encoding="utf-8")
        return {"status": "success", "record_count": len(records)}


def test_crawl_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = CrawlState(
        queue=[CrawlItem(url="https://www.211info.org/")],
        seen_urls={"https://example.com"},
        processed_pages=2,
    )
    state.save(path)

    loaded = CrawlState.load(path)
    assert loaded.queue[0].url == "https://www.211info.org/"
    assert "https://example.com" in loaded.seen_urls
    assert loaded.processed_pages == 2


def test_agentic_daemon_processes_stub_fetch(tmp_path):
    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed", request_delay=0)
    daemon = AgenticCrawlerDaemon(
        cfg,
        state_path=tmp_path / "state" / "agentic_daemon_state.json",
        strategy_path=tmp_path / "state" / "daemon_strategy.json",
        fetcher=StubFetcher(),
        dataset_sink=StubDatasetSink(),
    )

    result = daemon.run_once(seed_urls=["https://www.211info.org/"], max_pages=1)

    assert result["processed_pages"] == 1
    assert result["extracted_services"] == 1
    assert (tmp_path / "raw" / "agentic_pages_raw.jsonl").exists()
    assert (tmp_path / "raw" / "services_raw_agentic.jsonl").exists()
    assert (tmp_path / "processed" / "services_agentic.csv").exists()
    state = CrawlState.load(tmp_path / "state" / "agentic_daemon_state.json")
    assert state.queue
    assert (tmp_path / "state" / "agentic_daemon_state.duckdb").exists()


def test_duckdb_store_migrates_json_state(tmp_path):
    state_path = tmp_path / "state" / "agentic_daemon_state.json"
    db_path = tmp_path / "state" / "agentic_daemon_state.duckdb"
    legacy = CrawlState(
        queue=[CrawlItem(url="https://www.211info.org/legacy", depth=1, kind="seed")],
        seen_urls={"https://www.211info.org/seen"},
        failed_urls={"https://www.211info.org/failed": 2},
    )
    legacy.save(state_path)

    store = DuckDBCrawlStore(db_path)
    store.migrate_from_state(CrawlState.load(state_path))

    assert store.queue_count() == 1
    assert store.seen_count() == 1
    assert store.failed_count() == 1


def test_duckdb_store_migrates_legacy_queue_without_priority_column(tmp_path):
    db_path = tmp_path / "legacy_state.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE queue (
            seq BIGINT PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            depth INTEGER NOT NULL,
            kind TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            claimed_at TIMESTAMP
        )
        """
    )
    con.execute(
        """
        INSERT INTO queue(seq, url, depth, kind, metadata_json, status)
        VALUES (1, 'https://gethelp.211info.org/get-help/food/community-meals', 1, 'discovered', '{}', 'queued')
        """
    )
    con.close()

    store = DuckDBCrawlStore(db_path)

    assert store.queue_count() == 1
    con = duckdb.connect(str(db_path), read_only=True)
    columns = {
        str(row[1])
        for row in con.execute("PRAGMA table_info('queue')").fetchall()
    }
    assert "priority" in columns
    assert con.execute("select count(*) from queue_summary").fetchone()[0] == 1


def test_duckdb_store_records_pattern_yield_stats(tmp_path):
    store = DuckDBCrawlStore(tmp_path / "state.duckdb")

    store.record_pattern_outcome(
        "https://gethelp.211info.org/get-help/food/community-meals-one",
        extracted=False,
        fetch_success=True,
    )
    store.record_pattern_outcome(
        "https://gethelp.211info.org/get-help/food/community-meals-two",
        extracted=True,
        fetch_success=True,
    )
    store.record_pattern_outcome(
        "https://gethelp.211info.org/get-help/food/community-meals-three",
        extracted=False,
        fetch_success=False,
    )

    stats = store.pattern_yield_stats()

    assert stats[0]["pattern"] == "/get-help/food/"
    assert stats[0]["attempts"] == 3
    assert stats[0]["successes"] == 1
    assert stats[0]["fetch_failures"] == 1


def test_queue_pattern_frontier_view_joins_queue_and_pattern_stats(tmp_path):
    store = DuckDBCrawlStore(tmp_path / "state.duckdb")
    store.enqueue_items(
        [
            CrawlItem(url="https://gethelp.211info.org/get-help/food/detail-one", depth=1, kind="discovered"),
            CrawlItem(url="https://gethelp.211info.org/get-help/food/detail-two", depth=1, kind="discovered"),
            CrawlItem(url="https://gethelp.211info.org/get-help/housing/detail-three", depth=1, kind="discovered"),
        ]
    )
    store.upsert_pattern_yield_stats(
        [
            {"pattern": "/get-help/food/", "attempts": 10, "successes": 8, "fetch_failures": 0},
            {"pattern": "/get-help/housing/", "attempts": 4, "successes": 4, "fetch_failures": 0},
        ]
    )

    con = duckdb.connect(str(tmp_path / "state.duckdb"), read_only=True)
    rows = con.execute(
        """
        select pattern, queued_urls, attempts, successes
        from queue_pattern_frontier
        order by queued_urls desc, pattern asc
        """
    ).fetchall()

    assert rows[0] == ("/get-help/food/", 2, 10, 8)
    assert rows[1] == ("/get-help/housing/", 1, 4, 4)


def test_backfill_pattern_stats_from_warehouse(tmp_path):
    warehouse = DuckDBETLWarehouse(tmp_path / "warehouse.duckdb")
    warehouse.append_crawl_pages(
        [
            {"url": "https://gethelp.211info.org/get-help/food/detail-one", "title": "", "body_text": "", "links": [], "depth": 1, "kind": "discovered", "quality_score": 1.0, "archive": {}, "fetched_at": "2026-05-02T00:00:00+00:00"},
            {"url": "https://gethelp.211info.org/get-help/food/detail-two", "title": "", "body_text": "", "links": [], "depth": 1, "kind": "discovered", "quality_score": 1.0, "archive": {}, "fetched_at": "2026-05-02T00:00:00+00:00"},
            {"url": "https://gethelp.211info.org/get-help/housing/detail-three", "title": "", "body_text": "", "links": [], "depth": 1, "kind": "discovered", "quality_score": 1.0, "archive": {}, "fetched_at": "2026-05-02T00:00:00+00:00"},
        ]
    )
    warehouse.append_raw_services(
        [
            {"detail_url": "https://gethelp.211info.org/get-help/food/detail-one", "name": "Food One"},
            {"detail_url": "https://gethelp.211info.org/get-help/housing/detail-three", "name": "Housing Three"},
        ],
        source="agentic_daemon",
    )

    result = backfill_pattern_stats(
        warehouse_path=tmp_path / "warehouse.duckdb",
        state_db_path=tmp_path / "state.duckdb",
    )

    assert result["pattern_count"] == 2
    store = DuckDBCrawlStore(tmp_path / "state.duckdb")
    stats = {row["pattern"]: row for row in store.pattern_yield_stats()}
    assert stats["/get-help/food/"]["attempts"] == 2
    assert stats["/get-help/food/"]["successes"] == 1
    assert stats["/get-help/housing/"]["attempts"] == 1
    assert stats["/get-help/housing/"]["successes"] == 1


def test_reextract_warehouse_writes_new_source_lineage(tmp_path):
    warehouse = DuckDBETLWarehouse(tmp_path / "warehouse.duckdb")
    warehouse.append_crawl_pages(
        [
            {
                "url": "https://gethelp.211info.org/get-help/transportation/air-fare/",
                "title": "Air Fare - 211info",
                "body_text": (
                    "Transportation > Air Fare 2 Matching Service Providers "
                    "ANGEL FLIGHT WEST Print & Share X Print & Share Print PDF "
                    "Arranges air travel through donated flights. "
                    "123 Sky Way Portland, OR 97204 Eligibility: Unrestricted Hours: Monday-Friday 8am-5pm "
                    "Email (503) 555-1212 Get Directions Visit Website More Details "
                    "SECOND PROVIDER PROGRAM Print & Share X Print & Share Print PDF "
                    "Provides transportation support for medical appointments. "
                    "456 Care Avenue Salem, OR 97301 Eligibility: Varies Hours: Daily 9am-5pm "
                    "Email (503) 555-3434 Get Directions Visit Website More Details"
                ),
                "links": [],
                "depth": 1,
                "kind": "discovered",
                "quality_score": 1.0,
                "archive": {},
                "fetched_at": "2026-05-02T00:00:00+00:00",
            }
        ],
        source_run="demo",
    )

    result = reextract_warehouse(warehouse_path=tmp_path / "warehouse.duckdb", source="agentic_reextract_v2")

    assert result["pages_scanned"] == 1
    assert result["pages_with_records"] == 1
    assert result["raw_records"] == 2
    con = duckdb.connect(str(tmp_path / "warehouse.duckdb"), read_only=True)
    assert con.execute(
        "select count(*) from raw_services where source = 'agentic_reextract_v2'"
    ).fetchone()[0] == 2
    assert con.execute(
        "select count(*) from processed_services where source = 'agentic_reextract_v2' and provider_name <> ''"
    ).fetchone()[0] == 2


def test_canonical_processed_services_prefers_reextract_source(tmp_path):
    warehouse = DuckDBETLWarehouse(tmp_path / "warehouse.duckdb")
    warehouse.append_processed_services(
        [
            {
                "id": "svc-1",
                "name": "Old Service",
                "provider_name": "Old Service",
                "program_name": "",
                "description": "old",
                "address": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
                "phone": "(503) 555-1111",
                "email": "",
                "website": "https://example.org/service",
                "hours": "",
                "eligibility": "",
                "languages": "",
                "categories": "food",
                "accessibility": "",
                "source_url": "https://gethelp.211info.org/get-help/food/example-service/",
                "search_category": "",
                "search_zip": "",
            }
        ],
        source="agentic_daemon",
        source_run="legacy",
    )
    warehouse.append_processed_services(
        [
            {
                "id": "svc-1-new",
                "name": "New Service",
                "provider_name": "Provider Org",
                "program_name": "New Service",
                "description": "new",
                "address": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
                "phone": "(503) 555-1111",
                "email": "",
                "website": "https://example.org/service",
                "hours": "Daily",
                "eligibility": "",
                "languages": "",
                "categories": "food",
                "accessibility": "",
                "source_url": "https://gethelp.211info.org/get-help/food/example-service/",
                "search_category": "",
                "search_zip": "",
            }
        ],
        source="agentic_reextract_v2",
        source_run="reextract",
    )

    con = duckdb.connect(str(tmp_path / "warehouse.duckdb"), read_only=True)
    row = con.execute(
        "select source, name, provider_name, program_name, hours from canonical_processed_services"
    ).fetchone()

    assert row == ("agentic_reextract_v2", "New Service", "Provider Org", "New Service", "Daily")


def test_export_canonical_services_writes_jsonl_and_csv(tmp_path):
    warehouse = DuckDBETLWarehouse(tmp_path / "warehouse.duckdb")
    warehouse.append_processed_services(
        [
            {
                "id": "svc-1",
                "name": "Display Name",
                "provider_name": "Provider Org",
                "program_name": "Display Name",
                "description": "desc",
                "address": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
                "phone": "(503) 555-1111",
                "email": "",
                "website": "https://example.org/service",
                "hours": "Daily",
                "eligibility": "",
                "languages": "",
                "categories": "food",
                "accessibility": "",
                "source_url": "https://gethelp.211info.org/get-help/food/example-service/",
                "search_category": "",
                "search_zip": "",
            }
        ],
        source="agentic_reextract_v2",
        source_run="reextract",
    )

    result = export_canonical_services(
        warehouse_path=tmp_path / "warehouse.duckdb",
        output_dir=tmp_path / "out",
    )

    assert result["record_count"] == 1
    assert (tmp_path / "out" / "services_canonical.jsonl").exists()
    assert (tmp_path / "out" / "services_canonical.csv").exists()
    payload = (tmp_path / "out" / "services_canonical.jsonl").read_text(encoding="utf-8")
    assert '"provider_name": "Provider Org"' in payload


def test_agentic_daemon_uses_duckdb_queue_across_passes(tmp_path):
    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed", request_delay=0)
    daemon = AgenticCrawlerDaemon(
        cfg,
        state_path=tmp_path / "state" / "agentic_daemon_state.json",
        strategy_path=tmp_path / "state" / "daemon_strategy.json",
        fetcher=StubFetcher(),
        dataset_sink=StubDatasetSink(),
    )

    first = daemon.run_once(seed_urls=["https://www.211info.org/"], max_pages=1)
    second = daemon.run_once(seed_urls=["https://www.211info.org/"], max_pages=1)

    assert first["processed_pages"] == 1
    assert second["processed_pages"] == 1
    assert second["queue_remaining"] >= 0
    store = DuckDBCrawlStore(tmp_path / "state" / "agentic_daemon_state.duckdb")
    assert store.seen_count() >= 2


def test_agentic_daemon_populates_etl_warehouse(tmp_path):
    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed", request_delay=0)
    daemon = AgenticCrawlerDaemon(
        cfg,
        state_path=tmp_path / "state" / "agentic_daemon_state.json",
        strategy_path=tmp_path / "state" / "daemon_strategy.json",
        fetcher=StubFetcher(),
        dataset_sink=StubDatasetSink(),
    )

    daemon.run_once(seed_urls=["https://www.211info.org/"], max_pages=1)

    con = duckdb.connect(str(tmp_path / "state" / "etl_warehouse.duckdb"), read_only=True)
    assert con.execute("select count(*) from crawl_pages").fetchone()[0] == 1
    assert con.execute("select count(*) from raw_services").fetchone()[0] == 1
    assert con.execute("select count(*) from processed_services").fetchone()[0] == 1


def test_extract_result_page_services_parses_multiple_provider_blocks():
    text = """
    Transportation > Air Fare 2 Matching Service Providers
    ANGEL FLIGHT WEST Print & Share X Print & Share Print PDF
    Arranges air travel through donated flights for non-emergency medical transport.
    123 Sky Way Portland, OR 97204 Eligibility: Unrestricted Hours: Monday-Friday 8am-5pm
    Email (503) 555-1212 Get Directions Visit Website More Details
    SECOND PROVIDER PROGRAM Print & Share X Print & Share Print PDF
    Provides transportation support for medical appointments.
    456 Care Avenue Salem, OR 97301 Eligibility: Varies Hours: Daily 9am-5pm
    Email (503) 555-3434 Get Directions Visit Website More Details
    """

    records = extract_result_page_services(text, "https://gethelp.211info.org/get-help/transportation/air-fare/")

    assert len(records) == 2
    assert records[0]["name"] == "ANGEL FLIGHT WEST"
    assert records[0]["address"] == "123 Sky Way Portland, OR 97204"
    assert records[0]["phone"] == "(503) 555-1212"
    assert "donated flights" in records[0]["description"]


def test_extract_result_page_services_accepts_descriptive_chunk_with_contact_info():
    text = """
    Diverse Populations > General Recreational Activities/Sports * Native American Community
    1 Matching Service Providers Print & Share All Results X Print & Share Print PDF
    NATIVE AMERICAN YOUTH AND FAMILY CENTER RECREATION Print & Share X Print & Share Print PDF
    Recreational activities offered include after-school sport clinics and seasonal teams.
    5135 NE Columbia Boulevard Portland, OR 97218 Eligibility: Native American students attending public schools
    Hours: Varies by service Email (503) 288-8177 Get Directions Visit Website More Details
    """

    records = extract_result_page_services(
        text,
        "https://gethelp.211info.org/get-help/diverse-populations/general-recreational-activities-sports-native-american-community/",
    )

    assert len(records) == 1
    assert records[0]["name"] == "NATIVE AMERICAN YOUTH AND FAMILY CENTER RECREATION"
    assert records[0]["address"] == "5135 NE Columbia Boulevard Portland, OR 97218"


def test_extract_result_page_services_skips_zero_match_pages():
    text = "Parenting & Childcare > Teen Expectant/New Parent Assistance 0 Matching Service Providers No Mapping Information Available"

    records = extract_result_page_services(
        text,
        "https://gethelp.211info.org/get-help/child-care-parenting/teen-expectant-new-parent-assistance/",
    )

    assert records == []


def test_extract_address_supports_flattened_site_format():
    text = (
        "Provides meals and referrals. 817 S 10th Street Coos Bay, OR 97420 "
        "Eligibility: Ages 0-24 Hours: Monday-Friday 9am-5pm"
    )

    assert extract_address(text) == "817 S 10th Street Coos Bay, OR 97420"


def test_normalize_provider_name_strips_pdf_and_duplicate_prefix():
    assert normalize_provider_name("PDF NATIONAL DOMESTIC VIOLENCE HOTLINE") == "NATIONAL DOMESTIC VIOLENCE HOTLINE"
    assert (
        normalize_provider_name(
            "QUEST CENTER FOR INTEGRATIVE HEALTH QUEST CENTER FOR INTEGRATIVE HEALTH MULTNOMAH HEALTH SERVICES"
        )
        == "QUEST CENTER FOR INTEGRATIVE HEALTH MULTNOMAH HEALTH SERVICES"
    )
    assert normalize_provider_name("Air Fare - 211info") == "Air Fare"


def test_choose_result_display_name_prefers_short_program_tail():
    assert (
        choose_result_display_name(
            "UNITED STATES DEPARTMENT OF HEALTH AND HUMAN SERVICES SUBSTANCE ABUSE AND MENTAL HEALTH SERVICES ADMINISTRATION DISASTER DISTRESS HELPLINE",
            description="Provides disaster crisis counseling to people experiencing emotional distress after disasters.",
            detail_url="https://gethelp.211info.org/get-help/disaster-services/disaster-service-centers-hotlines/",
        )
        == "DISASTER DISTRESS HELPLINE"
    )
    assert (
        choose_result_display_name(
            "UNITED STATES DEPARTMENT OF HEALTH AND HUMAN SERVICES ADMINISTRATION FOR CHILDREN AND FAMILIES OFFICE OF HEAD START HEAD START LOCATOR",
            description="Provides an online tool to find Head Start and Early Head Start programs.",
            detail_url="https://gethelp.211info.org/get-help/education/head-start/",
        )
        == "HEAD START LOCATOR"
    )


def test_split_provider_program_names_separates_provider_and_program():
    provider_name, program_name = split_provider_program_names(
        "UNITED STATES DEPARTMENT OF HEALTH AND HUMAN SERVICES SUBSTANCE ABUSE AND MENTAL HEALTH SERVICES ADMINISTRATION DISASTER DISTRESS HELPLINE",
        "DISASTER DISTRESS HELPLINE",
    )

    assert provider_name == "UNITED STATES DEPARTMENT OF HEALTH AND HUMAN SERVICES SUBSTANCE ABUSE AND MENTAL HEALTH SERVICES ADMINISTRATION"
    assert program_name == "DISASTER DISTRESS HELPLINE"


def test_single_record_extractor_skips_result_page_title_without_contact(tmp_path):
    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed", request_delay=0)
    daemon = AgenticCrawlerDaemon(
        cfg,
        state_path=tmp_path / "state" / "agentic_daemon_state.json",
        strategy_path=tmp_path / "state" / "daemon_strategy.json",
        fetcher=StubFetcher(),
        dataset_sink=StubDatasetSink(),
    )
    result = FetchResult(
        url="https://gethelp.211info.org/get-help/diverse-populations/example/",
        title="General Recreational Activities/Sports * Native American Community - 211info",
        text=(
            "- Radius - 5 Miles Search by Provider Name > New Search > Diverse Populations > "
            "General Recreational Activities/Sports * Native American Community "
            "1 Matching Service Providers No Mapping Information Available"
        ),
        html="",
    )

    records = daemon._extract_service_records(result, CrawlItem(url=result.url))

    assert records == []


def test_queue_priority_prefers_service_detail_urls():
    root_score = score_queue_item("https://www.211info.org/", depth=0, kind="seed")
    category_score = score_queue_item("https://gethelp.211info.org/get-help/food/", depth=1, kind="discovered")
    detail_score = score_queue_item(
        "https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/",
        depth=1,
        kind="discovered",
    )

    assert detail_score > category_score > root_score


def test_duckdb_store_claims_high_priority_urls_first(tmp_path):
    store = DuckDBCrawlStore(tmp_path / "state.duckdb")
    store.enqueue_items(
        [
            CrawlItem(url="https://www.211info.org/", depth=0, kind="seed"),
            CrawlItem(url="https://gethelp.211info.org/get-help/food/", depth=1, kind="discovered"),
            CrawlItem(
                url="https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/",
                depth=1,
                kind="discovered",
            ),
        ]
    )

    batch = store.claim_batch(limit=2, blocked_urls=set())

    assert "community-meals-at-risk-youth" in batch[0].url
    assert "/get-help/food/" in batch[1].url


def test_queue_priority_deprioritizes_pattern_matches():
    detail_score = score_queue_item(
        "https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/",
        depth=1,
        kind="discovered",
    )
    deprioritized_score = score_queue_item(
        "https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/",
        depth=1,
        kind="discovered",
        strategy={"deprioritized_url_patterns": ["/get-help/food/"]},
    )

    assert deprioritized_score < detail_score


def test_queue_priority_boosts_high_yield_patterns():
    base_score = score_queue_item(
        "https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/",
        depth=1,
        kind="discovered",
    )
    boosted_score = score_queue_item(
        "https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/",
        depth=1,
        kind="discovered",
        pattern_stats={"attempts": 40, "successes": 39, "success_rate": 0.975},
    )

    assert boosted_score > base_score


def test_queue_priority_penalizes_low_yield_patterns():
    base_score = score_queue_item(
        "https://gethelp.211info.org/get-help/crisis-hotlines/runaway-homeless-youth-helplines",
        depth=1,
        kind="discovered",
    )
    penalized_score = score_queue_item(
        "https://gethelp.211info.org/get-help/crisis-hotlines/runaway-homeless-youth-helplines",
        depth=1,
        kind="discovered",
        pattern_stats={"attempts": 59, "successes": 30, "success_rate": 0.508},
    )

    assert penalized_score < base_score


def test_pattern_prefix_for_url_extracts_get_help_family():
    assert pattern_prefix_for_url("https://gethelp.211info.org/get-help/food/community-meals") == "/get-help/food/"
    assert pattern_prefix_for_url("https://www.211info.org/search/?search_term=food") == ""


def test_supervisor_rewrites_strategy_for_stale_active_url(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    stale_at = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    state = CrawlState(
        queue=[CrawlItem(url="https://www.211info.org/next")],
        active_url="https://www.211info.org/stuck",
        heartbeat_at=stale_at,
        last_progress_at=stale_at,
        processed_pages=1,
    )
    state.save(state_path)
    strategy_path.write_text(
        json.dumps({"generation": 0, "request_delay": 2.0, "max_depth": 3}),
        encoding="utf-8",
    )
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    stuck, reason = supervisor.is_stuck(CrawlState.load(state_path))
    updated = supervisor.rewrite_strategy(CrawlState.load(state_path), reason)

    assert stuck is True
    assert updated["generation"] == 1
    assert updated["request_delay"] == 3.0
    assert updated["max_depth"] == 2
    assert "https://www.211info.org/stuck" in updated["blocked_urls"]
    assert events_path.exists()


def test_supervisor_does_not_mark_queued_state_stuck_without_progress_timestamp(tmp_path):
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=tmp_path / "state.json",
            strategy_path=tmp_path / "strategy.json",
            events_path=tmp_path / "events.jsonl",
            stale_seconds=60,
        )
    )
    state = CrawlState(
        queue=[CrawlItem(url="https://www.211info.org/pending")],
        processed_pages=10,
        last_progress_at="",
        heartbeat_at="",
    )

    stuck, reason = supervisor.is_stuck(state)

    assert stuck is False
    assert reason == ""


def test_agentic_daemon_blocks_pattern_matches(tmp_path):
    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed", request_delay=0)
    daemon = AgenticCrawlerDaemon(
        cfg,
        state_path=tmp_path / "state" / "agentic_daemon_state.json",
        strategy_path=tmp_path / "state" / "daemon_strategy.json",
        fetcher=StubFetcher(),
        dataset_sink=StubDatasetSink(),
    )

    assert daemon._is_blocked(
        "https://www.211info.org/search/?search_term=test",
        {"blocked_urls": [], "blocked_url_patterns": ["/search/?"]},
    )


def test_supervisor_rewrite_adds_blocked_patterns_from_failures(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    state = CrawlState(
        queue=[CrawlItem(url="https://www.211info.org/next")],
        active_url="https://www.211info.org/stuck",
        failed_urls={
            "https://www.211info.org/search/?search_term=abc": 1,
            "https://www.211info.org/give-help/provider-tools/resources@wa211.org": 1,
            "https://gethelp.211info.org/get-help/food/detail-one": 2,
            "https://gethelp.211info.org/get-help/food/detail-two": 2,
            "https://gethelp.211info.org/get-help/food/detail-three": 2,
        },
    )
    state.save(state_path)
    strategy_path.write_text(json.dumps({}), encoding="utf-8")
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    updated = supervisor.rewrite_strategy(state, "test")

    assert "/search/?" in updated["blocked_url_patterns"]
    assert "resources@" in updated["blocked_url_patterns"]
    assert "/get-help/food/" in updated["deprioritized_url_patterns"]


def test_supervisor_reconcile_failure_patterns_updates_strategy_without_generation_bump(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    state = CrawlState(
        failed_urls={
            "https://www.211info.org/search/?search_term=abc": 1,
            "https://www.211info.org/give-help/provider-tools/resources@wa211.org": 1,
        },
    )
    state.save(state_path)
    strategy_path.write_text(json.dumps({"generation": 7, "blocked_url_patterns": []}), encoding="utf-8")
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    updated = supervisor.reconcile_failure_patterns(state)

    assert updated is not None
    assert updated["generation"] == 7
    assert "/search/?" in updated["blocked_url_patterns"]
    assert "resources@" in updated["blocked_url_patterns"]
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert any("failure_pattern_refresh" in line for line in lines)


def test_supervisor_reconcile_failure_patterns_deprioritizes_before_blocking(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    state = CrawlState(
        failed_urls={
            "https://gethelp.211info.org/get-help/food/detail-one": 2,
            "https://gethelp.211info.org/get-help/food/detail-two": 2,
            "https://gethelp.211info.org/get-help/food/detail-three": 2,
        },
    )
    state.save(state_path)
    strategy_path.write_text(json.dumps({"generation": 7}), encoding="utf-8")
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    updated = supervisor.reconcile_failure_patterns(state)

    assert updated is not None
    assert "/get-help/food/" in updated["deprioritized_url_patterns"]
    assert "/get-help/food/" not in updated.get("blocked_url_patterns", [])


def test_supervisor_reconcile_failure_patterns_skips_when_coverage_mode_enabled(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    state = CrawlState(
        failed_urls={
            "https://gethelp.211info.org/get-help/food/detail-one": 2,
            "https://gethelp.211info.org/get-help/food/detail-two": 2,
            "https://gethelp.211info.org/get-help/food/detail-three": 2,
        },
    )
    state.save(state_path)
    strategy_path.write_text(json.dumps({"generation": 7, "coverage_mode": True}), encoding="utf-8")
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    updated = supervisor.reconcile_failure_patterns(state)

    assert updated is None


def test_apply_strategy_priorities_uses_pattern_yield_stats(tmp_path):
    store = DuckDBCrawlStore(tmp_path / "state.duckdb")
    store.enqueue_items(
        [
            CrawlItem(url="https://gethelp.211info.org/get-help/food/detail-one", depth=1, kind="discovered"),
            CrawlItem(url="https://gethelp.211info.org/get-help/crisis-hotlines/detail-two", depth=1, kind="discovered"),
        ]
    )
    store.upsert_pattern_yield_stats(
        [
            {"pattern": "/get-help/food/", "attempts": 40, "successes": 39, "fetch_failures": 0},
            {"pattern": "/get-help/crisis-hotlines/", "attempts": 59, "successes": 30, "fetch_failures": 0},
        ]
    )

    store.apply_strategy_priorities({})

    con = duckdb.connect(str(tmp_path / "state.duckdb"), read_only=True)
    rows = con.execute(
        "select url, priority from queue_priority_frontier order by priority desc, url asc"
    ).fetchall()

    assert "get-help/food" in rows[0][0]


def test_supervisor_uses_pattern_yield_stats_for_deprioritization(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    state = CrawlState()
    state.save(state_path)
    strategy_path.write_text(json.dumps({"generation": 7}), encoding="utf-8")
    store = DuckDBCrawlStore(state_path.with_suffix(".duckdb"))
    for suffix in ("one", "two", "three", "four"):
        store.record_pattern_outcome(
            f"https://gethelp.211info.org/get-help/food/detail-{suffix}",
            extracted=False,
            fetch_success=True,
        )
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    updated = supervisor.reconcile_failure_patterns(state)

    assert updated is not None
    assert "/get-help/food/" in updated["deprioritized_url_patterns"]


def test_supervisor_uses_pattern_yield_stats_for_blocking(tmp_path):
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    events_path = tmp_path / "events.jsonl"
    state = CrawlState()
    state.save(state_path)
    strategy_path.write_text(json.dumps({"generation": 7}), encoding="utf-8")
    store = DuckDBCrawlStore(state_path.with_suffix(".duckdb"))
    for suffix in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"):
        store.record_pattern_outcome(
            f"https://gethelp.211info.org/get-help/food/detail-{suffix}",
            extracted=False,
            fetch_success=True,
        )
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            stale_seconds=60,
        )
    )

    updated = supervisor.reconcile_failure_patterns(state)

    assert updated is not None
    assert "/get-help/food/" in updated["blocked_url_patterns"]


def test_supervisor_startup_grace_skips_stale_progress_check(tmp_path):
    supervisor = SelfHealingSupervisor(
        SupervisorConfig(
            state_path=tmp_path / "state.json",
            strategy_path=tmp_path / "strategy.json",
            events_path=tmp_path / "events.jsonl",
            stale_seconds=60,
        )
    )
    stale_at = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    state = CrawlState(
        queue=[CrawlItem(url="https://www.211info.org/pending")],
        processed_pages=10,
        last_progress_at=stale_at,
    )

    stuck, reason = supervisor.is_stuck(
        state,
        now_ts=datetime.now(timezone.utc).timestamp(),
        ignore_progress_until_ts=datetime.now(timezone.utc).timestamp() + 30,
    )

    assert stuck is False
    assert reason == ""
