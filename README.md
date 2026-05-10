# 211-AI

211-AI is a combined data pipeline, retrieval stack, wallet service, and frontend
for privacy-preserving 211 service navigation.

The repository now covers four connected lanes:

1. **211 corpus generation** from 211info.org through bounded and agentic
   scraping flows.
2. **Retrieval and portal packaging** for browser GraphRAG, portal search, and
   downstream datasets.
3. **UCAN/ZK-style wallet application workflows** exposed through
   `wallet_interface/` on top of `ipfs_datasets_py.wallet`.
4. **Abby**, the React/Vite UI for safety check-ins, sharing, uploads, proofs,
   exports, analytics, recipient access, and social-service navigation.

## Repository map

| Path | Purpose |
| --- | --- |
| `scraper/` | Batch scraper, agentic daemon, ETL, enrichment, retrieval-package builders, portal package builders, and export utilities. |
| `scripts/` | Thin CLIs for corpus builds, address enrichment, Hugging Face uploads, release checks, and implementation control-plane services (`portal`, `agent`, `graphrag`, `wallet`). |
| `wallet_interface/` | Python application layer, FastAPI surface, deployment assets, and the Abby UI workspace. |
| `wallet_interface/ui/` | Vite/React frontend, Playwright coverage, GitHub Pages build, and browser GraphRAG/runtime workers. |
| `docs/` | Product, architecture, security, runbook, threat-model, and implementation tracking documents. |
| `tests/` | Python test suite covering scraper, packaging, wallet, deployment, and documentation contracts. |
| `artifacts/` | Generated review packets and migration artifacts checked into the repo. |
| `state/` | Checked-in service state helpers and other repository state files. |
| `tmp_assets/` | Working asset packs and sliced UI assets used during Abby design iteration. |
| `ipfs_datasets_py/` | Vendored dependency used for wallet, optimizer, and optional web-archiving integrations during local development. |

## What is implemented here

### Data collection and packaging

- Bounded scraper entry point: `python -m scraper.main --mode all`
- Agentic crawl/ETL daemon: `python -m scraper.agentic_daemon`
- Self-healing crawl supervisor: `python -m scraper.supervisor`
- Retrieval package builder: `python -m scraper.build_retrieval_package`
- Browser GraphRAG corpus builder: `python scripts/build_browser_graphrag_corpus.py`
- Service portal package builder: `python scripts/build_service_portal_package.py`
- Address-enrichment, WARC/archive ingest, warehouse backfill, and export tools
  under `scraper/` and `scripts/`

### Wallet application layer

`wallet_interface/` is the repository-owned app layer around
`ipfs_datasets_py.wallet`. It includes:

- `WalletInterfaceService`
- FastAPI routes for wallet creation, grants, delegated access, proofs,
  analytics, exports, uploads, audit, storage verification/repair, and dead-drop
  workflows
- ops-health and release-readiness checks via `python -m wallet_interface.ops`
- reference Docker, Compose, Kubernetes, and Cloudflare deployment assets

See `wallet_interface/README.md` and the wallet docs listed in `docs/README.md`.

### Abby UI

The Abby frontend lives in `wallet_interface/ui/` and includes:

- Mobile-first React/Vite application flows for registration, check-ins,
  contacts, uploads, sharing rules, social services, shelter workflows,
  recipient access, exports, analytics, security, and audit review
- Browser GraphRAG runtime and local-model worker infrastructure
- Playwright smoke, fullstack, visual-capture, refinement, and service-action
  coverage
- GitHub Pages deployment via `.github/workflows/abby-ui-pages.yml`
- Visual review artifact generation via
  `.github/workflows/abby-ui-visual-review.yml`

See `wallet_interface/ui/README.md` for UI-specific environment variables,
verification commands, and GitHub Pages notes.

## Quick start

### Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest
```

### Abby UI environment

```bash
cd wallet_interface/ui
npm ci
```

## Common development workflows

### Run the bounded scraper

```bash
python -m scraper.main --mode all
```

### Run the agentic crawl lane

```bash
python -m scraper.agentic_daemon --once --max-pages 25
python -m scraper.supervisor --stale-seconds 600 --check-interval 30 --daemon-workers 4
```

### Run the wallet API locally

```bash
uvicorn wallet_interface.asgi:app --reload
```

### Run Abby locally

```bash
cd wallet_interface/ui
npm run dev
```

### Check implementation-service status

```bash
python scripts/manage_implementation_services.py status all
```

## Validation commands

### Python

```bash
python -m pytest tests/ -q
```

### Abby UI

```bash
cd wallet_interface/ui
npm run build
npm run test:smoke
npm run test:visual
```

For wallet release readiness, use:

```bash
python -m wallet_interface.ops --validate-production-readiness
python -m wallet_interface.ops --validate-proof-contract
python -m wallet_interface.ops --validate-distance-proof-contract
python -m wallet_interface.ops --validate-target-signoff-packet /path/to/packet.json
```

## Documentation

Start with `docs/README.md` for the current documentation index.

Key documents:

- `docs/AGENTIC_SCRAPER_DESIGN.md`
- `docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md`
- `docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md`
- `docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md`
- `docs/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md`
- `docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md`

## Deployment references

- Wallet deployment assets: `wallet_interface/deploy/README.md`
- Cloudflare edge reference: `wallet_interface/deploy/cloudflare/README.md`
- Kubernetes reference manifests: `wallet_interface/deploy/kubernetes/README.md`
- Abby GitHub Pages workflow: `.github/workflows/abby-ui-pages.yml`

## Notes

- The vendored `ipfs_datasets_py/` checkout is used as a local-development
  fallback when the package is not otherwise installed.
- Many runtime data directories such as `data/` are generated during scraper,
  packaging, wallet, and implementation-service runs and may not exist in a
  fresh clone.
