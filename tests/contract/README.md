# Contract Tests

API contract tests that validate the wallet interface API surface against its published contracts.

These tests run against the wallet API (either live or via `TestClient`) and validate response shapes, error codes, and contract invariants documented in `docs/specs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md` and `docs/specs/WALLET_PROOF_VERIFIER_CONTRACT.md`.

## Target content

- Wallet CRUD contract
- Portal saved-services create/list
- Portal service-plan create/list
- Portal interactions create/list
- Wallet snapshot get
- Record grant/revoke lifecycle
- Export bundle create/verify/import round-trip
- Proof grant/invocation contract
- HMIS referral draft lifecycle

## Run contract tests

```bash
python -m pytest tests/contract/ -q
```
