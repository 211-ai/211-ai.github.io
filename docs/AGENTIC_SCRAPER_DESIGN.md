# Agentic 211info Scraper Design

## Goals

- Maintain a durable crawl queue across runs.
- Use local `requests` + BeautifulSoup by default so daemon startup stays lightweight.
- Optionally use `ipfs_datasets_py.processors.web_archiving.UnifiedWebArchivingAPI` when `SCRAPER_ENABLE_IPFS_TOOLS=true`.
- ETL service-like pages into the existing canonical `services_agentic.jsonl` and `services_agentic.csv` outputs.
- Publish a dataset snapshot through the `save_dataset` tool when available, otherwise write JSON locally.
- Let a supervisor recover stuck crawls by rewriting strategy/state, not by silently mutating source code.

## Runtime Pieces

- `scraper.agentic_daemon.AgenticCrawlerDaemon` owns the crawl queue, heartbeat, URL discovery, raw page archive metadata, service extraction, and ETL export.
- `scraper.agentic_daemon.WebArchivingAdapter` uses direct HTTP fetching by default and can opt into the unified web-archiving API and WebArchive classes from the local `ipfs_datasets_py` tree.
- `scraper.agentic_daemon.DatasetSink` writes `data/processed/services_agentic_dataset.json` by default and can opt into `dataset_tools.save_dataset`.
- `scraper.supervisor.SelfHealingSupervisor` monitors `data/state/agentic_daemon_state.json`, restarts stale daemon processes, and rewrites `data/state/daemon_strategy.json`.

## Commands

Run one bounded ETL pass:

```bash
python -m scraper.agentic_daemon --once --max-pages 25
```

Run the daemon continuously:

```bash
python -m scraper.agentic_daemon --interval 300 --max-pages 25 --workers 4
```

Run the supervisor:

```bash
python -m scraper.supervisor --stale-seconds 600 --check-interval 30 --daemon-workers 4
```

`--workers` controls bounded parallel page fetches inside each daemon pass.
Keep this modest for live-site crawling. Larger parallelism is better suited to
archive/index backends such as Common Crawl or Cloudflare Browser Rendering.

## Supervisor Rewrite Policy

When the daemon appears stuck, the supervisor:

- Adds the active URL to `blocked_urls`.
- Increments `generation`.
- Increases `request_delay` up to 30 seconds.
- Reduces `max_depth` by one down to a floor of one.
- Writes an event to `data/state/supervisor_events.jsonl`.

This implements self-healing behavior without runtime source rewriting. If source-level rewriting is later required, it should be added as an explicit reviewable patch-generation step with tests and human approval.
