# Documentation Index

This directory contains canonical architecture references, runbooks, implementation plans, policy documents, and labeled working notes for the 211-AI monorepo.

## Start here

- **Repository overview:** `../README.md`
- **Repository structure contract:** `architecture/REPOSITORY_STRUCTURE.md`
- **Wallet service/API scope:** `../wallet_interface/README.md`
- **Abby UI runtime and tests:** `../wallet_interface/ui/README.md`
- **Deployment assets:** `../wallet_interface/deploy/README.md`
- **Ops sandbox notes:** `../ops/README.md`

## Subdirectory index

| Directory | Contents |
| --- | --- |
| `adr/` | Architecture Decision Records — stable, append-only design decisions |
| `runbooks/` | Operational runbooks for live environments |
| `specs/` | System specifications, contracts, threat models, and policies |
| `planning/` | Implementation plans, TODO backlogs, and historical working notes *(non-canonical)* |
| `architecture/` | Repository structure contract |

## Quick links

### Architecture decisions (`adr/`)
- `adr/WALLET_PRODUCTION_DECISIONS_ADR.md` — wallet production decision log
- `adr/WALLET_SECURITY_ARCHITECTURE_ADR.md` — wallet security architecture

### Runbooks (`runbooks/`)
- `runbooks/WALLET_OPERATIONS_RUNBOOK.md` — wallet operator reference
- `runbooks/211_SERVICE_NAVIGATION_PORTAL_RUNBOOK.md` — portal operations
- `runbooks/AI_AGENT_CHAT_RUNBOOK.md` — agent chat operations

### Specifications and contracts (`specs/`)
- `specs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md` — stable wallet API/CLI/MCP contract
- `specs/WALLET_PROOF_VERIFIER_CONTRACT.md` — verifier HTTP contract
- `specs/WALLET_RETENTION_POLICY.md` — storage and retention policy
- `specs/WALLET_UCAN_PROFILE.md` — UCAN profile and fixture validation contract
- `specs/PRIVACY_POLICY.md` / `specs/TERMS_AND_CONDITIONS.md`

### Active implementation backlogs (`planning/`)
- `planning/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md`
- `planning/UCAN_ZK_DATA_WALLET_TODO.md`
- `planning/211_SERVICE_NAVIGATION_PORTAL_PLAN.md`
- `planning/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md`
- `planning/HMIS_INTEGRATION_IMPLEMENTATION_PLAN.md`

## Working notes and generated artifacts

JSON manifests, transcript captures, batch-state files, and similarly named exploratory files in this directory root are generated reference material. They are not canonical contracts unless another document explicitly promotes them.
