# 211-AI

211-AI is a multi-component repository for:

- **211 service data ingestion** (scraping, archival ETL, normalization)
- **privacy-preserving wallet + API** workflows for service navigation and controlled disclosure
- **Abby UI** (React/TypeScript) for client, shelter, provider, wallet, proof, and audit flows

## Current repository scope

The codebase currently includes three active application layers:

1. **`scraper/`** — bounded crawler + persistent agentic daemon, warehouse ETL, retrieval/package builders
2. **`wallet_interface/`** — Python wallet service and FastAPI endpoints (controllers, grants, analytics, proofs, exports, storage, dead-drop flows, ops health)
3. **`wallet_interface/ui/`** — Abby frontend with mobile-first and desktop workflows, wallet API integration, and Playwright suites

There is also a vendored submodule checkout at **`ipfs_datasets_py/`** used by wallet and optional scraping/archive paths.

## Repository layout

```text
.
├── scraper/                  # 211 scraping, crawl state, ETL, packaging
├── wallet_interface/         # wallet service, API, deploy assets, ops worker
│   └── ui/                   # Abby React/Vite frontend
├── scripts/                  # operations + implementation daemons + release checks
├── docs/                     # architecture/runbooks/plans/ADRs
├── tests/                    # Python and TypeScript tests for scraper/wallet/integration
└── ipfs_datasets_py/         # git submodule dependency for wallet/runtime helpers
```

## Quick start

### 1) Clone and initialize submodule

```bash
git clone https://github.com/211-ai/211-ai.github.io.git
cd 211-ai.github.io
git submodule update --init --recursive
```

### 2) Python environment (scraper + wallet backend)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) UI environment (Abby)
For the wallet API, zero-knowledge proof flows, and IPFS/Filecoin-backed
encrypted storage integrations, also install the wallet Python dependencies:

```bash
./scripts/install_wallet_python_dependencies.sh
```

That helper installs the FastAPI wallet runtime from `requirements.txt`,
initializes the `ipfs_datasets_py` git submodule if needed, and installs the
wallet core package editable so the proof backends and storage adapters are
available locally.

---

## Usage

### Quick start — scrape everything

```bash
npm --prefix wallet_interface/ui ci
```

## Run the main applications

### 211 scraper pipeline

```bash
# bounded static + browser scrape
python -m scraper.main --mode all

# persistent agentic loop
python -m scraper.agentic_daemon --interval 300 --max-pages 25 --workers 4

# watchdog/supervisor loop
python -m scraper.supervisor --stale-seconds 600 --check-interval 30 --daemon-workers 4
```

### WARC/archive ETL and portal packaging

```bash
# unpack archived WARC files and normalize service records
python -m scraper.warc_etl --warc-path /path/to/archive.warc.gz --output-dir data/live

# build portal package artifacts from retrieval/warehouse sources
python -m scraper.build_service_portal_package --output-dir data/portal
```

### Wallet API

```bash
python -m uvicorn wallet_interface.asgi:app --host 0.0.0.0 --port 8000 --reload
```

### Abby UI

```bash
npm --prefix wallet_interface/ui run dev
```

## Validation and release checks

### UI

```bash
npm --prefix wallet_interface/ui run build
npm --prefix wallet_interface/ui run test:smoke
npm --prefix wallet_interface/ui run test:fullstack
```

### Wallet release gate orchestrator

```bash
python scripts/run_wallet_release_checks.py --dry-run
python scripts/run_wallet_release_checks.py
```

## Documentation map

Start with:

- `docs/README.md` (current-state docs index)
- `wallet_interface/README.md` (wallet service/API scope)
- `wallet_interface/ui/README.md` (Abby UI runtime, testing, Pages deploy)
- `wallet_interface/deploy/README.md` (compose/k8s/cloudflare deployment assets)

## Notes

- Some backend tests require optional dependencies beyond `requirements.txt` (for example FastAPI and wallet submodule packages).
- Playwright suites require browser binaries (`npx playwright install`) in fresh environments.
