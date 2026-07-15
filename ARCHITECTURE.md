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
| `helpers/` | Internal helpers package with 11 domain submodules (see table below) |
| `app_service.py` | `WalletInterfaceService` orchestrator |
| `proof_backends.py` | Proof backend implementations |
| `service_matching.py` | Service match logic |
| `world_id.py` | World ID integration |
| `ops.py` | Production readiness validation |
| `cli.py` | CLI entry point |
| `deploy/` | Kubernetes, Docker, and storage configuration |
| `ui/` | Abby React/Vite frontend package |

### Helpers submodule layout

| Submodule | Optional deps required | Responsibility |
| --- | --- | --- |
| `helpers/_tts_normalization.py` | None (stdlib only) | Pure text-normalization for TTS: number-to-words, zip/phone/address/URL normalization |
| `helpers/_tts_gradio.py` | None (stdlib only) | Pure Gradio response/file parsing, request-payload builders, ZIP audio extraction, Whisper text extraction, `_default_indextts_reference_wav` |
| `helpers/_tts_config.py` | None (stdlib only) | IndexTTS/Whisper env config readers, feature flags, threading.local overrides, `_clean_voice_reply_text`, `_silent_wav_bytes`, `_indextts_degraded_error_payload`, endpoint timeout/retry wrappers |
| `helpers/_auth.py` | None for pure helpers; optional deps for UCAN/SMTP | Auth helpers: bearer extraction, phone/email normalization, magic-login, UCAN |
| `helpers/_app.py` | None for pure helpers; optional `ipfs_datasets_py` for `_prepare_hf_router_environment`/`_wallet_interface_service_from_env` | IPFS CID utilities, service factory, shared constants |
| `helpers/_ai_routing.py` | None for pure helpers; optional `ipfs_datasets_py` for `_require_wallet_router_actor` | LLM router helpers, rate limiting, wallet actor resolution |
| `helpers/_records.py` | None for pure helpers; optional `ipfs_datasets_py` for `_generate_wallet_organizer_profile` | Document profile classification, privacy vector helpers |
| `helpers/_storage_filecoin.py` | None (stdlib only) | Filecoin pin sidecar: `_filecoin_pin_request`, `_mock_filecoin_pin_request`, `_submit_ipfs_cid_to_filecoin_pin`, `_fetch_filecoin_pin_status`, request headers, status URLs |
| `helpers/_storage.py` | None for pure helpers; optional `ipfs_datasets_py` for `_publish_bytes_to_ipfs` | IPFS publish, encryption-key helpers, dead-drop email, encrypted record graph; re-exports from `_storage_filecoin` |
| `helpers/_tts_http.py` | `ipfs_datasets_py` (resolve_secret) | HTTP credential helpers, `_indextts_headers`, `_http_json`/`_http_bytes`, multipart upload, Whisper STT, voice-reply LLM |
| `helpers/_tts_client.py` | `ipfs_accelerate_py` (`HFSpaceClient`) | HF Space client singleton with config/fn-index cache: `_indextts_space_client`, `_indextts_config`, `_indextts_fn_index`, `_indextts_queue_join`; file upload/wait/download: `_indextts_upload_reference_audio`, `_indextts_wait_for_result`, `_indextts_batch_audio_references`, `_fetch_gradio_file` |
| `helpers/_tts_pipeline.py` | `ipfs_accelerate_py` (via `_tts_client`) | Per-space TTS pipeline: `_indextts_execute_with_queue_fallback` (queue→retry→api_name→direct predict), `_run_indextts_gradio_tts_for_space`, `_run_indextts_gradio_batch_tts_for_space` |
| `helpers/_tts.py` | `ipfs_datasets_py`, `ipfs_accelerate_py` | Multi-space routing layer and top-level entry point: `_run_indextts_gradio_tts` (single), `_run_indextts_gradio_batch_tts` (batch), `_run_indextts_tts_with_batch_fallback` |

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
| Wallet | `features/wallet/` | Wallet screens (Proof, Export, Uploads, Analytics, Contacts, Login, Registration, Settings, BenefitsProtection), wallet API client, capabilities, mock service data |
| Service navigation | `features/service-navigation/` | Home, Shelter, SocialServices, CheckIn, ServiceDetail, ServicePlan; graphrag + service-action services |
| Agent/chat | `features/agent/` | Agent chat controller, LLM workers, agent services |
| Interactions | `features/interactions/` | Interaction history, client messages |
| Calendar | `features/calendar/` | Calendar screen |
| Shared UI | `shared/components/` | UI primitives with no domain coupling |
| Shared utilities | `shared/lib/` | Storage adapters, locale helpers, utilities |

Old locations in `app/screens/` and `services/` are backward-compat re-export stubs that delegate to the canonical feature paths. All major migrations are complete:

| Former source path | Canonical target | Migration status |
| --- | --- | --- |
| `agent/` (14 files + `tools/`) | `features/agent/lib/` | ✅ Migrated — stubs left at `agent/` |
| `lib/graphrag/` (10 files) | `features/service-navigation/lib/graphrag/` | ✅ Migrated — re-export barrel left at `lib/graphrag/` |
| `workers/` (5 files) | `features/agent/workers/` | ✅ Migrated — `new URL(...)` service references updated |

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
| Python lint | `ruff check scraper/ wallet_interface/ tests/` |
| Unit tests | `python -m pytest tests/unit/ -q` |
| Contract tests | `python -m pytest tests/contract/ -q` |
| Scraper tests | `python -m pytest tests/test_scraper.py -q` |
| Packaging/docs checks | `python -m pytest tests/test_wallet_python_dependencies.py -q` |
| Abby UI type check | `cd wallet_interface/ui && npx tsc --noEmit` |
| Abby UI build | `cd wallet_interface/ui && npm ci && npm run build` |
| Abby UI smoke tests | `cd wallet_interface/ui && npm run test:smoke` |
