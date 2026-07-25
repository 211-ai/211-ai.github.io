# WORLDCOIN-AUTO-007 Objective Validation Repair

Date: 2026-07-24
Goal id: WORLDCOIN-G042
Task id: WORLDCOIN-AUTO-007
Work scope: `objective_validation_repair`
Status: unapproved preparation evidence produced; G040 execution remains blocked
on a canonical human-signed Gate 0B-selection

## Gap disposition

The source scan identified missing objective-validation evidence for
WORLDCOIN-G042. This record connects the generated work item to repository
evidence without claiming TODO completion, selecting a DuckDB build, importing
DuckDB, or manufacturing approval.

The exact G042 acceptance terms are covered by:

- `data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json` —
  qualified G002 declaration and observed-metadata carry-forward, unresolved
  version conflict, human-only wheel/ABI/platform and supply-chain questions,
  policies, tests, exceptions, and expiry.
- `scripts/verify_world_aid_duckdb_bootstrap.py` — repository-only preparation
  checks plus delegation of any approved mode to the canonical signed Gate 0B
  verifier before DuckDB-specific wheel and path cross-binding.
- `requirements-world-aid.lock` — deliberately non-installable, hash-required,
  no-index human-selection contract.
- `docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md`,
  `wallet_interface/deploy/world-aid-duckdb-runtime.yml`, and
  `docs/specs/WORLD_AID_DUCKDB_BACKUP.md` — reviewed single-writer,
  local-path, extension/network-deny, raw opaque G040 backup, and separate G033
  application-encryption boundaries.
- `tests/world_aid/test_duckdb_bootstrap_static.py` — the non-executing G042
  acceptance contract.
- `tests/world_aid/test_duckdb_bootstrap.py` — the future G040 real-execution
  contract, which fails closed if execution or any required smoke check is
  absent or skipped.
- `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G042` —
  objective/acceptance alignment and the canonical validation command.

## Evidence terms repaired

| Required term | Repository evidence |
|---|---|
| Declarations and metadata remain unapproved | Proposal `inventory`, including root `>=1.4.0` and observed 1.4.3/1.5.2 conflict |
| Exact wheel remains human-owned | Proposal `dependency`; all selection fields are null |
| Wheel filename/hash, CPython ABI, and platform agree | Canonical approval delegation plus G042 wheel-name cross-check |
| License, provenance, SBOM, vulnerabilities, exceptions, expiry | Proposal `dependency` and `approval`; canonical Gate 0B record |
| Read-only inputs and bound artifacts | Canonical digest/Git/signature verification plus G042 canonical lock/policy-path checks |
| Extension/network deny and exactly one local writer | Runtime policy and verifier |
| Skipped execution fails closed | Future G040 runtime contract requires explicit execution markers, performs the exact smoke set, and emits `real_execution=true` only after cleanup |
| G040/G033 separation | Backup contract: raw opaque backup in G040; envelope/plaintext-marker/key lifecycle in G033 |
| No G042 runtime action | Proposal non-execution receipt and guarded static contract |

## Validation

Canonical command:

```text
test -f tests/world_aid/test_duckdb_bootstrap.py && PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -s -p no:cacheprovider -c /dev/null --confcutdir=tests/world_aid tests/world_aid/test_duckdb_bootstrap_static.py
```

The canonical command reads repository text and JSON only. It does not import
or execute DuckDB, create or open a database, install a wheel, execute pip,
contact an index or extension registry, inspect a package cache, look up a
secret, or run the G040 smoke. A later approved-mode invocation additionally
requires the external read-only allowed-signers store and delegates the full
record, signature, expiry, evidence, artifact, root-commit, and submodule
checks to `scripts/verify_world_aid_gate_0b.py`; even that verification does
not import or execute DuckDB.
