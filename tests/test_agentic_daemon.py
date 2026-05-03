from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import duckdb

from scraper.agentic_daemon import AgenticCrawlerDaemon, CrawlItem, CrawlState, FetchResult
from scraper.config import Config
from scraper.duckdb_state import DuckDBCrawlStore, score_queue_item
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
