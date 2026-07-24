# WORLDCOIN-AUTO-001 Objective Validation Repair

Date: 2026-07-24  
Goal id: WORLDCOIN-G002  
Task id: WORLDCOIN-AUTO-001  
Todo vector key: `3acfa404134f3aa1`  
Merge key: `da65cca9cb744dfe`  
Merge family: `objective/WORLDCOIN-G002`  
Work scope: `objective_validation_repair`  
Status: evidence produced; validation is the task's pytest gate

## Gap disposition

The source scan identified “objective validation repair” as the missing
evidence for WORLDCOIN-G002. This record connects the supervisor-fed work item
to the completed repository evidence without changing TODO completion
metadata.

The exact G002 acceptance terms are covered by:

- `docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md` — cited findings,
  speculation labels, compatibility freeze, missing boundaries, and acceptance
  trace.
- `data/worldcoin_human_aid/audit/component-map.json` — stable component IDs,
  owners, interfaces, risks, goals, conflict surfaces, classifications, and
  evidence.
- `data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json` — static
  installed/missing npm, Python/PostgreSQL, and ZKP inventory plus a
  human-selection-only approval question set.
- `tests/world_aid/test_integration_audit_contract.py` — offline structural,
  source-citation, exact-finding, machine-map, bootstrap, and no-side-effect
  contract.
- `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G002` —
  supervisor/heap alignment and the canonical validation command.

## Evidence terms repaired

| Required term | Repository evidence |
|---|---|
| Every claim cites a path/symbol or official version; speculation labeled | Audit “Scope, method, and evidence rules” and “Speculation register” |
| Simulated profile receipt is not eligibility | Audit finding A-01; component `document-profile-receipt` |
| Provider signal context is unenforced | Audit finding A-02; component `provider-context` |
| Plaintext principal secrets/raw World bindings | Audit finding A-03; component `local-wallet-repository` |
| Unauthenticated status returns full bindings | Audit finding A-04; component `wallet-status-api` |
| Legacy defaults on | Audit finding A-05; component `world-id-config-verifier` |
| Accepted v3 can be mislabeled v4 | Audit finding A-06; component `world-id-wallet-binding` |
| Missing EIP-1271 SIWE | Audit “Missing trust boundaries” item 1; component `wallet-principal-auth` |
| Missing issuer lifecycle | Audit item 2; component `issuer-lifecycle` |
| Missing encrypted transactional storage | Audit item 3; component `local-wallet-repository` |
| Missing payout and reconciliation | Audit items 4–5; component `payout-reconciliation` |
| Stable machine ownership/conflicts | Component map `components` |
| Human-approved offline inputs only | Bootstrap proposal `human_approval_questions` and `approval_gate` |
| No prohibited audit integration actions | Bootstrap `audit_observation`; static pytest contract |

## Validation

Canonical command:

```text
python -m pytest -q tests/world_aid/test_integration_audit_contract.py
```

The contract reads repository text and JSON only. It imports no wallet,
World, database, package-core, or ZKP runtime module and invokes no network,
secret, package, container, database, npm, or proof tool.
