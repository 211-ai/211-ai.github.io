# Repository Structure Contract

This document is the source of truth for the 211-AI monorepo layout.

## Repository classification

| Class | Meaning | Current homes |
| --- | --- | --- |
| Production code | Maintained application or library code that ships or is executed directly | `scraper/`, `wallet_interface/`, `wallet_interface/ui/src/` |
| Repository automation | Scripts or workflows used to build, validate, or operate the repo | `scripts/`, `.github/workflows/` |
| Canonical docs | Architecture, ADRs, runbooks, contracts, and implementation backlogs that describe the live system | `docs/` |
| Generated/runtime data | Data outputs, local state, caches, and machine-generated artifacts | `data/`, `state/` |
| Archived deliverables | Review packets, signoff artifacts, and historical work products retained for reference | `artifacts/` |
| Sandbox ops assets | Local nginx/bootstrap files, local logs, temporary gateway configs, and other operational scratch material | `ops/sandbox/` |
| Vendored dependencies | Git submodules or local package checkouts required by some workflows | `ipfs_datasets_py/`, `ipfs_kit_py/` |

## Monorepo domains

### `scraper/`
Owns service discovery, crawling, extraction, ETL, enrichment, and export workflows for 211 data.

### `wallet_interface/`
Owns the Python wallet application surface, proof integrations, deployment assets, and the embedded Abby UI package.

### `wallet_interface/ui/`
Owns the React/Vite frontend, client-side agent flows, browser storage adapters, and Playwright-driven UI validation.

### `docs/`
Owns canonical architecture records, runbooks, plans, and policy references. Historical working notes are allowed, but they must be called out as non-canonical.

### `ops/`
Owns sandbox or operator-adjacent local files that should not live at repository root.

### `artifacts/`
Owns historical deliverables, screenshots, review packets, and signoff bundles that are intentionally preserved outside the active code paths.

## Packaging policy

- Python packages are installed from the repository root via `pyproject.toml`.
- `scraper` and `wallet_interface` are first-class installable packages.
- `ipfs_datasets_py` and `ipfs_kit_py` remain git submodules for now.
- Code that needs the vendored `ipfs_datasets_py` checkout should use the shared vendor helper instead of introducing new direct `sys.path` mutations.

## Documentation policy

- The root `README.md` must describe the whole repository, not only one subsystem.
- `docs/README.md` is the navigation index for canonical documentation.
- Exploratory notes remain in `docs/`, but they must be clearly labeled as working notes.

## Operational hygiene policy

- Local logs, test nginx configs, and similar sandbox files belong under `ops/sandbox/`.
- Generated data and runtime state belong under `data/` and `state/`.
- New root-level temporary files should not be introduced.

## Validation policy

Use the narrowest existing validation that covers the changed surface:

- scraper changes: `python -m pytest tests/test_scraper.py -q`
- packaging/docs changes: `python -m pytest tests/test_wallet_python_dependencies.py -q`
- UI changes: `cd wallet_interface/ui && npm ci && npm run build`
- UI browser smoke: `cd wallet_interface/ui && npm run test:smoke`
