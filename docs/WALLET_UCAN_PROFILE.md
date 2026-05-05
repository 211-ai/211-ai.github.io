# Wallet UCAN Profile

Status: accepted for first production deployment.

Date: 2026-05-05

## Decision

The wallet uses signed `wallet-ucan-v1` invocation tokens as its first
production authorization profile. Direct byte-level `ucanto`/w3up token
compatibility is not a launch blocker. External UCAN adapters must preserve the
same issuer, audience, capability, caveat, expiry, revocation, and proof-chain
semantics before they are accepted as equivalent.

The profile is implemented in `ipfs_datasets_py.wallet.ucan`.

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

This envelope is for verifier, audit, and adapter tests. It deliberately does
not expose raw record payloads, document text, precise location, decrypted keys,
or private metadata.

## Conformance Fixtures

`wallet_ucan_conformance_fixture(invocation, grant=...)` packages the token,
expected decoded UCAN fields, profile payload, and signature-payload hash into a
stable adapter-test fixture. `validate_ucan_profile_payload(payload)` validates
and normalizes an inspection envelope. `validate_wallet_ucan_conformance_fixture`
validates the complete fixture, including token prefix, decoded token fields,
expected UCAN fields, proof-chain grant ID, and signature-payload hash. External
`ucanto`/w3up adapters can use these functions without depending on product API
internals.

Conforming adapters must preserve:

- issuer DID and audience DID
- the `with` resource and `can` ability
- caveats in the capability `nb` field
- nonce, issued-at, optional expiry, proof-chain grant ID, and signature
- absence of raw wallet payloads, precise coordinates, decrypted keys, and
  private metadata
