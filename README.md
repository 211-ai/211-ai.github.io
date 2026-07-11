# 211-AI Monorepo

211-AI is a monorepo for the 211 service-data platform, wallet-backed privacy workflows, Abby's frontend experience, and the operational tooling that supports them.

## Repository scope

This repository currently contains four primary product surfaces plus supporting operational assets:

| Area | Path | Purpose |
| --- | --- | --- |
| Scraper + ETL | `scraper/` | Collect, normalize, enrich, and export 211 service data |
| Wallet API + application layer | `wallet_interface/` | Python wallet workflows, service matching, proofs, exports, and deployment assets |
| Abby UI | `wallet_interface/ui/` | React/Vite client for Abby, service navigation, and wallet interactions |
| Documentation + operations | `docs/`, `ops/`, `artifacts/` | Architecture references, runbooks, sandbox ops assets, and archived deliverables |

The repository structure contract lives in `docs/architecture/REPOSITORY_STRUCTURE.md`.

## Monorepo map

```text
211-ai.github.io/
├── scraper/                  # scraper, ETL, export, and data packaging code
├── wallet_interface/         # wallet API, app service, deploy assets, UI package
│   └── ui/                   # Abby React/Vite frontend
├── tests/                    # Python repo-level tests
├── docs/                     # canonical docs, plans, ADRs, runbooks, working notes
├── ops/                      # sandbox and operational helper assets
├── scripts/                  # repository automation that is not yet package-owned
├── artifacts/                # archived deliverables and review packets
├── data/                     # generated and runtime data products
├── state/                    # local runtime state snapshots
├── ipfs_datasets_py/         # git submodule dependency
└── ipfs_kit_py/              # git submodule dependency
```

## Dependency and packaging model

The Python surfaces are now defined by the top-level `pyproject.toml` so the scraper and wallet packages can be installed without relying on ad hoc path bootstrapping.

### Install the Python project

```bash
git submodule update --init --recursive
python3 -m pip install -e ".[wallet,test]"
```

### Wallet dependency bootstrap

For environments that need the wallet runtime plus the vendored `ipfs_datasets_py` checkout for zero-knowledge proof flows and IPFS/Filecoin storage integrations, use:

```bash
./scripts/install_wallet_python_dependencies.sh
```

## Validation matrix

| Area | Command |
| --- | --- |
| Scraper tests | `python -m pytest tests/test_scraper.py -q` |
| Packaging/docs sanity | `python -m pytest tests/test_wallet_python_dependencies.py -q` |
| Abby UI build | `cd wallet_interface/ui && npm ci && npm run build` |
| Abby UI smoke tests | `cd wallet_interface/ui && npm run test:smoke` |
| Pages deployment workflow | `/.github/workflows/abby-ui-pages.yml` |

## Documentation entry points

- Repository structure: `docs/architecture/REPOSITORY_STRUCTURE.md`
- Docs index: `docs/README.md`
- Wallet scope: `wallet_interface/README.md`
- Abby UI runtime and tests: `wallet_interface/ui/README.md`
- Wallet deploy assets: `wallet_interface/deploy/README.md`
- Ops sandbox notes: `ops/README.md`

## Current refactor direction

The repository remains a monorepo. The immediate refactor goals are:

1. keep production code separate from generated state, review artifacts, and sandbox assets;
2. make Python packaging explicit and installable;
3. consolidate GitHub Actions around distinct scraper, wallet, and UI concerns; and
4. make the root documentation accurately describe the full system instead of only the original scraper slice.
