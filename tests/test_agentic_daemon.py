from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from scraper.agentic_daemon import AgenticCrawlerDaemon, CrawlItem, CrawlState, FetchResult
from scraper.config import Config
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
