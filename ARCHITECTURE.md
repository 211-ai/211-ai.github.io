# Architecture Overview

This file is the top-level architectural guide for the 211-AI monorepo. The authoritative structure contract lives at [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md).

## Repository purpose

This monorepo hosts a 211 service-data platform with four primary product surfaces:

| Surface | Path | Role |
| --- | --- | --- |
| **Scraper + ETL** | `scraper/` | Acquire, parse, enrich, and export 211 service data |
| **Wallet API** | `wallet_interface/` | Python wallet application, proof backends, service matching, deployment |
| **Abby UI** | `wallet_interface/ui/` | React/Vite frontend, agent/chat flows, browser storage adapters |
| **Docs + Operations** | `docs/`, `ops/`, `artifacts/` | Architecture, runbooks, sandbox ops, archived deliverables |

## Code classification

| Class | Current paths | Description |
| --- | --- | --- |
| Production code | `scraper/`, `wallet_interface/`, `wallet_interface/ui/src/` | Ships or is executed directly |
| Repository automation | `scripts/`, `.github/workflows/` | Build, validate, and operate the repo |
| Canonical docs | `docs/adr/`, `docs/runbooks/`, `docs/specs/` | ADRs, runbooks, contracts that describe the live system |
| Planning / working notes | `docs/planning/` | Implementation plans, TODO backlogs, historical notes *(non-canonical)* |
| Generated/runtime data | `data/`, `state/` | Data outputs, local state, caches |
| Archived deliverables | `artifacts/` | Historical review packets retained for reference |
| Sandbox ops | `ops/sandbox/` | Local nginx/bootstrap files, logs, gateway configs |
| Vendored dependencies | `ipfs_datasets_py/`, `ipfs_kit_py/` | Git submodule checkouts |

## Python packaging

All Python packages are installed from the repository root via `pyproject.toml`:

```bash
python -m pip install -e ".[wallet,test]"
```

`scraper` and `wallet_interface` are first-class installable packages. Vendored submodules (`ipfs_datasets_py`, `ipfs_kit_py`) are accessed via the shared `_vendor.py` helper rather than ad-hoc `sys.path` mutations.

## Backend module layout (`wallet_interface/`)

The wallet backend is organized by bounded context:

| Module | Responsibility |
| --- | --- |
| `api.py` | Thin FastAPI app factory; registers all route modules |
| `routes/` | Feature-grouped route modules (wallets, records, proofs, exports, etc.) |
| `services/` | Domain service classes extracted from the application service |
| `schemas/` | Pydantic request/response models grouped by domain |
| `app_service.py` | `WalletInterfaceService` orchestrator |
| `proof_backends.py` | Proof backend implementations |
| `service_matching.py` | Service match logic |
| `world_id.py` | World ID integration |
| `ops.py` | Production readiness validation |
| `cli.py` | CLI entry point |
| `deploy/` | Kubernetes, Docker, and storage configuration |
| `ui/` | Abby React/Vite frontend package |

## Scraper module layout (`scraper/`)

The scraper is organized in processing layers:

| Layer | Path | Responsibility |
| --- | --- | --- |
| Acquisition | `scraper/acquisition/` | Fetch from browsers, static pages, WARC archives |
| Parsing | `scraper/parsing/` | Extract text from PDFs, office documents, HTML |
| Enrichment | `scraper/enrichment/` | Geocode, normalize, DuckDB ETL, backfill |
| Export | `scraper/export/` | Package canonical services, build retrieval and portal packages |
| Orchestration | `scraper/orchestration/` | Supervisors, daemon, main entry point |

## Frontend layout (`wallet_interface/ui/src/`)

The frontend is organized by feature slice:

| Slice | Path | Responsibility |
| --- | --- | --- |
| App shell | `app/` | `App.tsx`, `AppRouter.tsx`, global hooks, app-level state |
| Wallet | `features/wallet/` | Wallet screens, wallet API client, proof review |
| Service navigation | `features/service-navigation/` | Service search, detail, service plan |
| Agent/chat | `features/agent/` | Agent chat, LLM workers, agent services |
| Interactions | `features/interactions/` | Interaction history |
| Calendar | `features/calendar/` | Calendar screen |
| Shared UI | `shared/components/` | UI primitives with no domain coupling |
| Shared utilities | `shared/lib/` | Storage adapters, locale helpers, utilities |

## Documentation layout (`docs/`)

| Directory | Contents |
| --- | --- |
| `adr/` | Architecture Decision Records — stable, append-only |
| `runbooks/` | Operational runbooks for live environments |
| `specs/` | System specs, contracts, threat models, policies |
| `planning/` | Implementation plans, TODOs, historical notes *(non-canonical)* |
| `architecture/` | Repository structure contract |

## Validation commands

| Area | Command |
| --- | --- |
| Scraper tests | `python -m pytest tests/test_scraper.py -q` |
| Packaging/docs checks | `python -m pytest tests/test_wallet_python_dependencies.py -q` |
| Abby UI build | `cd wallet_interface/ui && npm ci && npm run build` |
| Abby UI smoke tests | `cd wallet_interface/ui && npm run test:smoke` |
