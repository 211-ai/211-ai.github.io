# Wallet Proof Verifier HTTP Contract

This contract defines the external verifier service expected by
`wallet_interface.proof_backends.HttpLocationRegionProofBackend` when
`WALLET_PROOF_BACKEND=http-location-region`.

The HTTP backend replaces simulated proof receipts in production mode and must
never return private witness values in public inputs, receipts, logs, or errors.
The first production readiness gate validates `location_region`. The same
backend also defines the next proof-family contract, `location_distance`,
through `POST /prove/location-distance`; distance proof verifiers should pass
`python -m wallet_interface.ops --validate-distance-proof-contract` before UI
exposure. For WALLET-140 handoff, real verifier credentials are handled only
through the selected secret manager. Committed configuration, readiness
reports, and signoff packets may name the secret-manager reference, but must
not contain bearer tokens, custom header values, proving keys, verifier keys,
or circuit secret material.

## Configuration

Required wallet API/worker environment:

```bash
WALLET_PROOF_MODE=production
WALLET_PROOF_BACKEND=http-location-region
WALLET_PROOF_SERVICE_URL=https://verifier.example.com
WALLET_PROOF_VERIFIER_ID=verifier-http-v1
WALLET_PROOF_SYSTEM=groth16
WALLET_PROOF_CIRCUIT_ID=location-region-v1
WALLET_PROOF_CREDENTIAL_SECRET_REF=secret-manager://wallet/prod/proof-verifier
```

Optional:

```bash
WALLET_PROOF_PROVE_PATH=/prove/location-region
WALLET_PROOF_DISTANCE_PROVE_PATH=/prove/location-distance
WALLET_PROOF_VERIFY_PATH=/verify
WALLET_PROOF_HTTP_HEADER_NAME=x-wallet-proof-key
WALLET_PROOF_TIMEOUT_SECONDS=30
```

If the target uses bearer or custom-header authentication, the deployment
platform injects runtime-only `WALLET_PROOF_BEARER_TOKEN` or
`WALLET_PROOF_HTTP_HEADER_VALUE` from `WALLET_PROOF_CREDENTIAL_SECRET_REF`.
Those values are intentionally not shown as env assignments here. Do not commit
them to env examples, signoff packets, readiness reports, logs, or ticket
comments.

## Authentication

The wallet backend sends JSON `POST` requests. If configured, it also sends:

- `Authorization: Bearer {WALLET_PROOF_BEARER_TOKEN}`
- `{WALLET_PROOF_HTTP_HEADER_NAME}: {WALLET_PROOF_HTTP_HEADER_VALUE}`

Production verifier deployments should require at least one authenticated
channel and should be reachable only from the wallet API/ops worker network.

## Credential Handoff

The target owner provisions the verifier credential in the selected secret
manager before staging validation. The wallet deployment receives only:

- `WALLET_PROOF_CREDENTIAL_SECRET_REF`, the secret-manager path or provider
  identifier for the verifier credential.
- Runtime-injected `WALLET_PROOF_BEARER_TOKEN` or
  `WALLET_PROOF_HTTP_HEADER_VALUE`, available only inside the wallet API and
  ops worker process environment.
- Non-secret verifier metadata: `WALLET_PROOF_SERVICE_URL`,
  `WALLET_PROOF_VERIFIER_ID`, `WALLET_PROOF_SYSTEM`, circuit IDs, and endpoint
  paths.

The completed target signoff packet should archive the credential reference
and validation artifact IDs only. It should not archive a rendered process
environment, request headers, Kubernetes Secret contents, ExternalSecret
resolved values, CI masked-secret screenshots, or verifier private key
material.

## Non-Simulated Cutover Evidence

Before any user-facing non-simulated proof path is exposed, the target
environment needs a completed cutover packet for the selected HTTP verifier
backend. The packet is an evidence bundle, not a secret bundle. It records
artifact IDs, reviewer decisions, service metadata, and rollback owners while
leaving bearer tokens, header values, proving keys, verifier keys, witnesses,
precise coordinates, and secret payloads in their approved systems.

The packet applies to both proof families handled by this backend:
`location_region` and `location_distance`. A passing local self-check is useful
for repository automation, but it is not launch evidence. Launch evidence must
come from the target staging environment with the real verifier service,
runtime-injected credentials, production proof mode, and simulated receipts
disabled.

Record this verifier selection in the packet:

- Verifier service URL or private service name.
- `WALLET_PROOF_VERIFIER_ID`, `WALLET_PROOF_SYSTEM`, and region/distance
  circuit IDs.
- Region, distance, health, and verify endpoint paths.
- `WALLET_PROOF_CREDENTIAL_SECRET_REF` and the credential rotation owner.
- Verifier deployment artifact or image digest.
- Rollback owner, rollback command or deployment reference, and last known good
  verifier release.

Required evidence:

| Proof family | Evidence | Pass condition |
| --- | --- | --- |
| `location_region` | Staging health report | `python -m wallet_interface.ops --validate-proof-contract --fail-on-error` archives `checks.health.status=ok` for the selected verifier ID and proof system. |
| `location_region` | Staging prove report | The same artifact archives `checks.prove.status=ok`, `receipt.proof_type=location_region`, `receipt.is_simulated=false`, and expected verifier metadata. |
| `location_region` | Staging verify report | The same artifact archives `checks.verify.status=ok` and a verified returned receipt. |
| `location_region` | No-leak report | The same artifact archives `checks.public_input_safety.status=ok`, and any linked verifier/API log review shows no witness keys, precise coordinates, addresses, nonce values, bearer tokens, header values, or secret payloads. |
| `location_region` | Credential-reference report | The readiness report and signoff packet show `WALLET_PROOF_CREDENTIAL_SECRET_REF` or provider equivalent, with no rendered secret values. |
| `location_region` | Failure-mode report | A target-staging drill with an invalid credential, unhealthy verifier, rejected prove response, or `verify=false` response makes the contract/readiness command return nonzero and leaves no stored proof receipt. The archived failure output must not include witness or secret values. |
| `location_region` | Rollback report | A target-staging rollback drill reverts to the approved previous API/UI/ops/verifier configuration or otherwise disables proof creation while keeping `WALLET_PROOF_MODE=production` so simulated receipts remain rejected. |
| `location_distance` | Staging health report | `python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error` archives `checks.health.status=ok` for the selected verifier ID and proof system. |
| `location_distance` | Staging prove report | The same artifact archives `checks.prove.status=ok`, `receipt.proof_type=location_distance`, `receipt.is_simulated=false`, and expected verifier metadata. |
| `location_distance` | Staging verify report | The same artifact archives `checks.verify.status=ok` and a verified returned receipt. |
| `location_distance` | No-leak report | The same artifact archives `checks.public_input_safety.status=ok`, and any linked verifier/API log review shows no wallet coordinates, target coordinates, addresses, nonce values, bearer tokens, header values, or secret payloads. |
| `location_distance` | Credential-reference report | The readiness report and signoff packet show the verifier credential reference used by the distance endpoint, with no rendered secret values. |
| `location_distance` | Failure-mode report | A target-staging drill with an invalid credential, unhealthy verifier, rejected prove response, out-of-policy distance response, or `verify=false` response makes the contract/readiness command return nonzero and leaves no stored proof receipt. The archived failure output must not include witness or secret values. |
| `location_distance` | Rollback report | A target-staging rollback drill proves the live Proof Center can keep distance proof creation and display hidden while the API/ops worker continue to reject simulated receipts. |

The cutover packet is incomplete if any evidence artifact is missing, reports
`mode=local_self_check`, has `status=error`, records a simulated receipt, or
contains secret or witness material. Treat an incomplete packet as a launch
blocker for all non-simulated user proof creation.

## Health Endpoint

Default path: `POST /health`

Request:

```json
{
  "verifier_id": "verifier-http-v1",
  "proof_system": "groth16"
}
```

Successful response:

```json
{
  "ok": true,
  "status": "ready",
  "verifier_id": "verifier-http-v1",
  "proof_system": "groth16",
  "circuit_id": "location-region-v1",
  "version": "2026.05.05"
}
```

Failure response:

```json
{
  "ok": false,
  "status": "down",
  "reason": "verifier unavailable"
}
```

`GET /ops/health` reports `proof_registry=error` when this endpoint returns
`ok=false`, a non-ready status, invalid JSON, or an HTTP error.

## Location-Region Prove Endpoint

Default path: `POST /prove/location-region`

Request:

```json
{
  "wallet_id": "wallet-123",
  "proof_type": "location_region",
  "statement": {
    "claim": "location_in_region",
    "region_id": "multnomah_county",
    "witness_commitment": "..."
  },
  "public_inputs": {
    "claim": "location_in_region",
    "region_id": "multnomah_county",
    "region_policy_hash": "..."
  },
  "witness": {
    "lat": 45.5152,
    "lon": -122.6784,
    "nonce": "wallet-local-nonce"
  },
  "witness_record_ids": ["record-1"],
  "verifier_id": "verifier-http-v1",
  "proof_system": "groth16",
  "circuit_id": "location-region-v1"
}
```

The verifier must treat `witness` as private input. It may log request IDs,
verifier metadata, public inputs, receipt IDs, and proof hashes; it must not log
precise coordinates, nonces, addresses, or decrypted record values.

Response can be either a receipt object or `{ "receipt": { ... } }`.

Successful response:

```json
{
  "receipt": {
    "proof_id": "proof-http-1",
    "wallet_id": "wallet-123",
    "proof_type": "location_region",
    "statement": {
      "claim": "location_in_region",
      "region_id": "multnomah_county",
      "witness_commitment": "..."
    },
    "verifier_id": "verifier-http-v1",
    "public_inputs": {
      "claim": "location_in_region",
      "region_id": "multnomah_county",
      "region_policy_hash": "..."
    },
    "proof_hash": "hex-or-content-hash",
    "witness_record_ids": ["record-1"],
    "is_simulated": false,
    "proof_system": "groth16",
    "circuit_id": "location-region-v1",
    "verifier_digest": "sha256(proof_system:verifier_id)",
    "proof_artifact_ref": "ipfs://bafy... or https://verifier.example.com/proofs/proof-http-1",
    "verification_status": "verified",
    "expires_at": null
  }
}
```

Required receipt fields:

- `proof_id`
- `wallet_id`
- `proof_type`
- `statement`
- `verifier_id`
- `public_inputs`
- `proof_hash`
- `witness_record_ids`
- `is_simulated=false`
- `proof_system`
- `verification_status=verified`

The wallet fills missing `wallet_id`, `proof_type`, `verifier_id`,
`proof_system`, `circuit_id`, `is_simulated=false`, and `verifier_digest`
defaults, but production verifiers should return them explicitly.

## Location-Distance Prove Endpoint

Default path: `POST /prove/location-distance`

Request:

```json
{
  "wallet_id": "wallet-123",
  "proof_type": "location_distance",
  "statement": {
    "claim": "location_within_distance",
    "target_id": "shelter-west",
    "max_distance_km": 1.0,
    "target_policy_hash": "...",
    "witness_commitment": "..."
  },
  "public_inputs": {
    "claim": "location_within_distance",
    "target_id": "shelter-west",
    "max_distance_km": 1.0,
    "target_policy_hash": "..."
  },
  "witness": {
    "lat": 45.5152,
    "lon": -122.6784,
    "target_lat": 45.516,
    "target_lon": -122.679,
    "max_distance_km": 1.0
  },
  "witness_record_ids": ["record-1"],
  "verifier_id": "verifier-http-v1",
  "proof_system": "groth16",
  "circuit_id": "location-distance-v1"
}
```

The verifier must prove the private wallet point is within `max_distance_km` of
the target point. The wallet service pre-checks the distance before calling the
verifier, but the verifier must not rely on that pre-check.

Successful response:

```json
{
  "receipt": {
    "proof_id": "proof-http-distance-1",
    "wallet_id": "wallet-123",
    "proof_type": "location_distance",
    "statement": {
      "claim": "location_within_distance",
      "target_id": "shelter-west",
      "max_distance_km": 1.0,
      "target_policy_hash": "...",
      "witness_commitment": "..."
    },
    "verifier_id": "verifier-http-v1",
    "public_inputs": {
      "claim": "location_within_distance",
      "target_id": "shelter-west",
      "max_distance_km": 1.0,
      "target_policy_hash": "..."
    },
    "proof_hash": "hex-or-content-hash",
    "witness_record_ids": ["record-1"],
    "is_simulated": false,
    "proof_system": "groth16",
    "circuit_id": "location-distance-v1",
    "verifier_digest": "sha256(proof_system:verifier_id)",
    "proof_artifact_ref": "ipfs://bafy... or https://verifier.example.com/proofs/proof-http-distance-1",
    "verification_status": "verified",
    "expires_at": null
  }
}
```

Do not include precise wallet coordinates, target coordinates, exact addresses,
nonces, or witness objects in the returned receipt.

## Verify Endpoint

Default path: `POST /verify`

Request:

```json
{
  "receipt": {
    "proof_id": "proof-http-1",
    "wallet_id": "wallet-123",
    "proof_type": "location_region",
    "statement": {},
    "verifier_id": "verifier-http-v1",
    "public_inputs": {},
    "proof_hash": "hex-or-content-hash",
    "witness_record_ids": ["record-1"],
    "is_simulated": false,
    "proof_system": "groth16",
    "circuit_id": "location-region-v1",
    "verifier_digest": "sha256(proof_system:verifier_id)",
    "proof_artifact_ref": "ipfs://bafy...",
    "verification_status": "verified",
    "created_at": "2026-05-05T00:00:00+00:00",
    "expires_at": null
  }
}
```

Successful response:

```json
{
  "verified": true
}
```

Failure response:

```json
{
  "verified": false,
  "reason": "invalid proof hash"
}
```

The wallet stores a proof receipt only after `verify` returns `true`.

## Ops Validation

Run:

```bash
curl -fsS \
  -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
  "https://wallet-api.example.com/ops/health?verify_storage=false"
```

Then run the verifier contract check from the same environment as the API or
ops worker:

```bash
python -m wallet_interface.ops --validate-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-production-readiness
```

When these commands are run without target `WALLET_*` verifier environment
variables, the CLI performs a local synthetic self-check so repository release
automation can exercise the contract scanner. Any configured target
environment runs the strict external verifier check and fails closed when the
HTTP backend, verifier credentials, secret-manager references, health endpoint,
prove endpoint, verify endpoint, or no-leak scan is not valid.

The first command performs a non-user location-region staging contract check:

- `POST /health`
- `POST /prove/location-region` with a synthetic witness
- `POST /verify` with the returned receipt
- receipt/public-input scanning for leaked synthetic witness fields or values

The distance command performs the same health/prove/verify/no-leak checks
against `POST /prove/location-distance`. The production-readiness gate runs
both verifier checks unless explicitly skipped, and also validates
secret-manager references for proof, storage, ops-health, and alert
credentials without printing secret values.

Archive the target staging JSON output for all three commands. The archived
region and distance contract reports must show `status=ok`, the expected
verifier ID and proof system, successful `health`, `prove`,
`public_input_safety`, and `verify` checks, and no secret values in the report.

Expected proof check:

```json
{
  "name": "proof_registry",
  "status": "ok",
  "details": {
    "backend": "HttpLocationRegionProofBackend",
    "verifier_id": "verifier-http-v1",
    "proof_system": "groth16",
    "backend_health": {
      "ok": true,
      "status": "ready"
    }
  }
}
```

Run a full location-region proof workflow in staging before production use:

1. Start the API with `WALLET_PROOF_MODE=production` and
   `WALLET_PROOF_BACKEND=http-location-region`.
2. Add a wallet location record.
3. Create a `location/prove_region` grant or owner proof request.
4. Confirm the proof receipt has `is_simulated=false`,
   `proof_system=groth16`, the expected `verifier_id`, and no precise
   coordinates in `public_inputs`.
5. Confirm `/ops/health` stays `ok` after proof creation.

Before enabling location-distance proof UI in production, run the same workflow
with a `location/prove_distance` grant and confirm the receipt has
`proof_type=location_distance`, `is_simulated=false`, expected verifier
metadata, and no precise wallet or target coordinates in `statement`,
`public_inputs`, verifier responses, wallet logs, verifier logs, or archived
evidence. Until that target staging validation is archived and approved in
`docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md`, `location_distance` remains hidden
from live Proof Center creation and display surfaces.

## Security Requirements

- Do not return `witness`, `lat`, `lon`, exact address, or nonce values in
  receipt `public_inputs`, verifier errors, or logs.
- Use TLS between wallet services and verifier.
- Authenticate every endpoint.
- Keep proving keys, verifier keys, and circuit artifacts in the verifier
  environment or a dedicated artifact store, not in wallet snapshots.
- Rotate verifier credentials through the target secret manager and redeploy
  the API and ops worker together.
- Treat `verification_status` values other than `verified` as failure.
