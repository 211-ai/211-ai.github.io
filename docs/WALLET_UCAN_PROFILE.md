# Wallet UCAN Profile

Status: accepted for first production deployment.

Date: 2026-05-05

## Decision

The wallet uses signed `wallet-ucan-v1` invocation tokens as its first
production authorization profile. Direct byte-level `ucanto`/w3up token
compatibility is handled by a target-specific adapter track and is not the
production wallet token. External UCAN adapters must preserve the same issuer,
audience, capability, caveat, expiry, revocation, and proof-chain semantics
before they are accepted as equivalent.

The profile is implemented in `ipfs_datasets_py.wallet.ucan`.

The selected external stack for the current adapter track is `ucanto/w3up`.
The adapter identifier is `wallet-ucan-v1-ucanto-w3up-dag-cbor-v1`.

## Token Format

Invocation tokens are ASCII strings:

```text
wallet-ucan-v1.<base64url(canonical-json(WalletInvocation))>
```

`WalletInvocation` fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `invocation_id` | yes | Unique invocation identifier. |
| `grant_id` | yes | Grant that authorizes this invocation. |
| `issuer_did` | new tokens yes, legacy optional | DID that issued the grant. Verifiers reject mismatches when present. |
| `audience_did` | yes | DID invoking the delegated capability. |
| `resource` | yes | Wallet resource URI, usually `wallet://...`. |
| `ability` | yes | Wallet ability such as `record/analyze` or `export/create`. |
| `caveats` | yes | Invocation caveats, encoded as canonical JSON. |
| `issued_at` | yes | Invocation issue time. |
| `expires_at` | optional | Invocation expiry. |
| `nonce` | yes | Invocation nonce. |
| `signature` | yes | HMAC-SHA256 signature over the canonical invocation payload with `signature` removed. |

Legacy tokens that do not contain `issuer_did` remain accepted when their
signature validates. New tokens include `issuer_did`, and verification rejects a
present issuer that does not match the referenced grant.

## Capabilities

Resource helpers in `ipfs_datasets_py.wallet.ucan` define the stable wallet
resource vocabulary:

| Helper | Resource shape |
| --- | --- |
| `resource_for_wallet(wallet_id)` | `wallet://{wallet_id}` |
| `resource_for_record(wallet_id, record_id)` | `wallet://{wallet_id}/records/{record_id}` |
| `resource_for_location(wallet_id, record_id)` | `wallet://{wallet_id}/location/{record_id}` |
| `resource_for_export(wallet_id)` | `wallet://{wallet_id}/exports` |

Abilities are wallet-local strings. Current production-covered examples include
`record/analyze`, `record/decrypt`, `record/vector_profile`,
`record/analyze_redacted`, `location/read_coarse`, `location/read_precise`,
`location/prove_region`, `analytics/contribute`, `export/create`, and
`wallet/admin`.

## Caveats

The verifier enforces these caveats when present:

| Caveat | Purpose |
| --- | --- |
| `not_before` / `nbf` | Prevent use before a timestamp. |
| `record_ids` / `allowed_record_ids` | Restrict use to specific records. |
| `data_types` / `allowed_data_types` | Restrict use to specific wallet data types. |
| `purpose` | Require invocation purpose to match the grant purpose. |
| `output_types` / `allowed_output_types` | Restrict derived outputs such as summary, redacted analysis, vector profile, or encrypted export. |
| `user_presence_required` / `require_user_presence` | Require invocation caveats to include `user_present` or `user_presence`. |
| `max_delegation_depth` | Bound child delegation depth. |

Grant revocation, grant-chain status, expiry, audience matching, resource
matching, ability matching, threshold approval references, and key wrapping are
enforced by `ipfs_datasets_py.wallet` around these caveats.

## Interop Envelope

`invocation_to_ucan_profile_payload(invocation, grant=...)` exports a
deterministic UCAN-compatible inspection envelope:

```json
{
  "profile": "wallet-ucan-v1",
  "ucan": {
    "iss": "did:key:owner",
    "aud": "did:key:delegate",
    "att": [{"with": "wallet://wallet/records/record", "can": "record/analyze", "nb": {}}],
    "nnc": "nonce",
    "fct": "issued-at",
    "exp": "optional-expiry",
    "sig": "signature",
    "prf": ["grant-id"]
  },
  "wallet_invocation": {},
  "wallet_grant": {}
}
```

When a wallet grant is supplied, the capability `nb` field contains the
effective adapter-visible caveats: grant caveats plus any invocation caveats
that attenuate them. This keeps the external adapter byte block no broader than
the wallet grant even when the internal invocation token omits caveats that are
already enforced by the wallet grant.

This envelope is for verifier, audit, and adapter tests. It deliberately does
not expose raw record payloads, document text, precise location, decrypted keys,
or private metadata.

## External Adapter Track

`wallet-ucan-v1` remains the first-production encoding. The `ucanto/w3up`
adapter proves byte-level compatibility for an external verifier by encoding the
UCAN inspection fields as a canonical DAG-CBOR block:

```json
{
  "iss": "did:key:owner",
  "aud": "did:key:delegate",
  "att": [{"with": "wallet://wallet/records/record", "can": "record/analyze", "nb": {}}],
  "nnc": "nonce",
  "fct": "issued-at",
  "exp": "optional-expiry",
  "sig": "signature",
  "prf": ["grant-id"]
}
```

The adapter fixture records the `dag-cbor` block bytes as base64url, the
SHA-256 of those bytes, and the CIDv1 base32 `dag-cbor`/`sha2-256` CID. Fixture
validation decodes the exact bytes, recomputes the hash and CID, and verifies
that the decoded block exactly matches the wallet profile payload. Added,
removed, or changed capabilities and caveats fail validation. When
`wallet_grant` is present, validation also rejects adapter payloads whose
resource, ability, or caveats exceed the grant. The adapter does not introduce
new wallet abilities, resources, caveats, proof semantics, or authorization
bypasses.

## Conformance Fixtures

`wallet_ucan_conformance_fixture(invocation, grant=...)` packages the token,
expected decoded UCAN fields, profile payload, external adapter block, and
signature-payload hash into a stable adapter-test fixture.
`validate_ucan_profile_payload(payload)` validates and normalizes an inspection
envelope. `validate_wallet_ucan_external_adapter_fixture(adapter, profile_payload=...)`
validates the byte-level `ucanto/w3up` DAG-CBOR adapter block.
`validate_wallet_ucan_conformance_fixture` validates the complete fixture,
including token prefix, decoded token fields, expected UCAN fields, proof-chain
grant ID, signature-payload hash, grant-bounded caveats, and external adapter
hash/CID. External `ucanto`/w3up adapters can use these functions without
depending on product API internals.

The same contract is available from the wallet CLI for adapter pipelines:

```bash
python -m ipfs_datasets_py.wallet.cli --json ucan-profile
python -m ipfs_datasets_py.wallet.cli --json ucan-conformance-fixture \
  --invocation-token "$WALLET_UCAN_TOKEN" \
  --grant-path grant.json \
  --out wallet-ucan-fixture.json
python -m ipfs_datasets_py.wallet.cli --json ucan-validate-profile \
  --path wallet-ucan-profile-payload.json
python -m ipfs_datasets_py.wallet.cli --json ucan-validate-fixture \
  --path wallet-ucan-fixture.json
python -m ipfs_datasets_py.wallet.cli ucan-validate-fixture
```

When `ucan-validate-fixture` is run without `--path`, it validates the built-in
deterministic reference fixture for CI and adapter smoke tests.

Conforming adapters must preserve:

- issuer DID and audience DID
- the `with` resource and `can` ability
- caveats in the capability `nb` field
- nonce, issued-at, optional expiry, proof-chain grant ID, and signature
- absence of raw wallet payloads, precise coordinates, decrypted keys, and
  private metadata
