# WORLDCOIN-AUTO-006 Objective Validation Repair

Date: 2026-07-24
Goal id: WORLDCOIN-G041
Task id: WORLDCOIN-AUTO-006
Work scope: `objective_validation_repair`
Status: unapproved preparation evidence produced; G039 execution remains
blocked on a canonical human-signed Gate 0B selection and an independently
reviewed, operator-controlled Gate-first launcher.

## Gap disposition

The source scan identified missing objective-validation evidence for
WORLDCOIN-G041. This record connects the generated work item to repository
evidence without selecting a backend, importing a tool, executing a circuit,
or manufacturing approval.

The exact G041 acceptance terms are covered by:

- `data/worldcoin_human_aid/bootstrap/zkp-toolchain-dependency-proposal.json` —
  qualified G002 inventory, human-owned architecture/backend/version and
  binary-or-image questions, supply-chain evidence fields, expiry, bounded
  smoke contract, and explicit non-approval.
- `scripts/verify_world_aid_zkp_toolchain.py` — repository-only checks,
  exact signed-byte approval parsing, immutable path/digest cross-binding for
  a future approval, host-architecture and resource checks, and delegation of
  signed Gate 0B verification before any approved mode.
- `tests/world_aid/fixtures/zkp_toolchain_smoke/SMOKE_SPEC.md`,
  `Nargo.toml`, `Nargo.lock`, and `src/main.nr` — locked, bounded,
  backend-neutral smoke inputs; `Nargo.lock` is an explicitly versioned
  repository contract rather than a tool-generated compatibility claim, and
  they contain no production aid policy or setup keys.
- `tests/world_aid/test_zkp_toolchain_bootstrap_static.py` — the guarded
  non-executing acceptance contract.
- `tests/world_aid/test_zkp_toolchain_bootstrap.py` — the future G039 runtime
  contract, which retains a non-environmental false launcher fence and records
  no approval from a fixture.
- `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G041` —
  objective, acceptance terms, and the canonical validation command.

## Evidence terms repaired

| Required term | Repository evidence |
|---|---|
| Backend selection remains human-owned | Proposal selection fields are null and Gate 0B is required |
| Architecture, version, binary/image digest | Proposal questions plus future approval cross-binding |
| License, provenance, SBOM, vulnerabilities, exceptions, expiry | Proposal evidence fields and canonical Gate 0B record |
| Deterministic flags and resource bounds | Proposal and locked smoke specification |
| Offline location and locked inputs | Read-only offline-root contract and committed smoke fixture |
| Repeat-build/proof/verify evidence | SMOKE_SPEC and G039 runtime contract |
| Network/registry deny and fail-closed drift checks | Verifier, proposal, and static tests |
| No static execution | No tool imports, subprocesses, writes, downloads, caches, secrets, builds, proofs, verification, or parameters |
| Production-trust boundary | Smoke artifacts and Groth16 parameters are explicitly not production trust; G039 owns approved execution |

## Validation

Canonical command:

```text
test -f tests/world_aid/test_zkp_toolchain_bootstrap.py && PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -s -p no:cacheprovider -c /dev/null --confcutdir=tests/world_aid tests/world_aid/test_zkp_toolchain_bootstrap_static.py
```

The canonical command reads repository files and JSON only. It does not
import or execute Nargo, Noir, ProveKit, `bb`, Cargo, Rust, a proof backend,
or a container; it does not download, contact a registry, inspect or mutate a
cache, look up a secret, build a circuit, generate a proof, verify a proof, or
generate setup parameters. Approved mode additionally requires the external
read-only allowed-signers store and delegates signature, expiry, artifact,
root-commit, and submodule checks to `scripts/verify_world_aid_gate_0b.py`.
