# Chainlink ZKML LLM Router Consensus Runbook

Last updated: 2026-06-13

Plan: `docs/CHAINLINK_ZKML_LLM_ROUTER_CONSENSUS_PLAN.md`
Proof policy reference: `docs/CHAINLINK_ZKML_LLM_ROUTER_PROOF_POLICY.md`
Backlog: `docs/CHAINLINK_ZKML_LLM_ROUTER_CONSENSUS_TODO.md`

---

## Overview

The `ipfs_accelerate_py.llm_router` module supports a verified inference mode
that requires independent operators to agree on the same answer before returning
a result. This runbook provides configuration examples, operating guidance, and
warnings for each supported consensus mode.

Consensus is not a replacement for the standard one-shot `generate_text` path.
Enable it only when auditability, quorum enforcement, or proof verification is
required.

---

## Quick Reference

| Mode | When to use | Quorum | Fail closed |
| --- | --- | --- | --- |
| `receipt_only` (local) | Dev, low-risk generation, smoke tests | ≥1 | Optional |
| `receipt_only` (libp2p) | Production multi-operator quorum | ≥2-of-3 | Required |
| `receipt_only` + CRE | Chainlink-verified structured output | ≥DON threshold | Required |
| `tee_or_zkml` | High-assurance attestation | ≥2-of-3 | Required |
| `zkml_required` | Bounded classifier or checker circuit | ≥2-of-3 | Required |
| `unsupported` | Free-form advice for high-impact decisions | — | Raise on entry |

---

## Example 1: Receipt-Only Local Consensus

Use this for development, unit tests, and low-risk generation where
multi-operator infrastructure is not yet in place.

```python
from ipfs_accelerate_py.llm_router import generate_text_consensus

receipt = generate_text_consensus(
    "Summarize the service options for a caller needing food assistance.",
    provider="hf_inference_api",
    model_name="mistralai/Mistral-7B-Instruct-v0.2",
    consensus={
        "enabled": True,
        "mode": "local_quorum",
        "quorum": 1,
        "min_operators": 1,
        "comparison": "normalized_text",
        "fail_closed": False,
    },
    proof_policy={"mode": "receipt_only"},
    return_receipt=True,
)

print(receipt.text)
print(receipt.quorum_result)   # "quorum_met"
print(receipt.proof_policy)    # {"mode": "receipt_only"}
print(receipt.receipt_hash)    # sha256 binding of the receipt JSON
```

> **Warning — non-deterministic generation parameters**: Generation parameters
> such as `temperature`, `top_p`, and `top_k` produce non-deterministic outputs.
> When using `exact` or `canonical_json` comparison across multiple operators,
> set these parameters to deterministic values (e.g., `temperature=0`,
> `do_sample=False`) or use `normalized_text` comparison with a suitable quorum
> threshold. Failure to do so will result in systematic quorum failures as
> operators produce different outputs from the same prompt.

---

## Example 2: Receipt-Only libp2p Quorum (Multi-Operator)

Use this for production quorum enforcement across independent libp2p peer
operators. Requires the libp2p task client integration (CLZKML-180).

```python
from ipfs_accelerate_py.llm_router import generate_text_consensus
from ipfs_accelerate_py.llm_consensus import LocalConsensusOperator

# Operators connect to independent libp2p peers running the inference worker.
# In production, replace LocalConsensusOperator with RemoteConsensusOperator
# once CLZKML-180 libp2p fan-out is enabled.
operator_a = LocalConsensusOperator(
    operator_id="op-peer-a",
    handler=lambda req: call_remote_peer("peer-a.example.com", req),
    provider="hf_inference_api",
)
operator_b = LocalConsensusOperator(
    operator_id="op-peer-b",
    handler=lambda req: call_remote_peer("peer-b.example.com", req),
    provider="hf_inference_api",
)
operator_c = LocalConsensusOperator(
    operator_id="op-peer-c",
    handler=lambda req: call_remote_peer("peer-c.example.com", req),
    provider="hf_inference_api",
)

receipt = generate_text_consensus(
    "Extract the service category from the following text as JSON: ...",
    consensus={
        "enabled": True,
        "mode": "local_quorum",
        "quorum": 2,
        "min_operators": 3,
        "comparison": "canonical_json",
        "fail_closed": True,
        "timeout_s": 30,
    },
    proof_policy={"mode": "receipt_only"},
    operators=[operator_a, operator_b, operator_c],
    return_receipt=True,
)
```

> **Warning — fail_closed is required for production quorum**: When `fail_closed`
> is `False`, the router returns a result even if quorum is not met, providing no
> consensus guarantee. Always set `fail_closed: True` for any production
> multi-operator deployment. A `LLMConsensusError` will be raised if quorum
> cannot be reached, which must be caught and handled by the caller.

> **Warning — deterministic decoding for canonical_json comparison**: Structured
> JSON output requires deterministic decoding. Instruct the model with an
> explicit schema and a zero-temperature setting. Malformed JSON from any
> operator fails quorum for that operator under `canonical_json` comparison.

---

## Example 3: CRE-Verified Consensus

Use this when Chainlink Runtime Environment (CRE) workflow verification is
required. CRE confirms that the inference capability was executed across DON
nodes according to an approved workflow. Requires the CRE bridge
(CLZKML-200 and CLZKML-220).

```python
from ipfs_accelerate_py.llm_router import generate_text_consensus

receipt = generate_text_consensus(
    "Is this caller eligible for emergency rental assistance? Output JSON: ...",
    consensus={
        "enabled": True,
        "mode": "local_quorum",
        "quorum": 3,
        "min_operators": 5,
        "comparison": "canonical_json",
        "fail_closed": True,
        "timeout_s": 60,
        "metadata": {
            "cre_workflow_id": "wf-eligibility-v1",
            "cre_registry": "mainnet-cre-registry.example.com",
            "model_policy_id": "policy-mistral-eligibility-v1",
        },
    },
    proof_policy={
        "mode": "receipt_only",
        "cre_verified": True,
        "cre_workflow_id": "wf-eligibility-v1",
        "cre_registry": "mainnet-cre-registry.example.com",
    },
    return_receipt=True,
)

# The ChainlinkCREVerifier (CLZKML-140) will check:
#   - workflow ID and registry match the expected values
#   - request hash and output hash are bound in the CRE report
#   - model_policy_id is present and matches the approved policy
assert receipt.quorum_result == "quorum_met"
assert receipt.proof_policy.get("cre_verified") is True
```

> **Warning — CRE consensus is not a ZKML proof**: Chainlink CRE verifies that
> the HTTP inference capability was executed by DON nodes according to the
> workflow. This is consensus evidence, not a zero-knowledge proof of model
> execution. Do not label a CRE receipt as ZKML-verified. Use `tee_or_zkml`
> or `zkml_required` proof policy when a cryptographic execution proof is
> required.

> **Warning — high-impact decisions require fail-closed**: Any workflow that
> affects service eligibility, emergency routing, or institutional audit must set
> `fail_closed: True`. A partial result returned without quorum is not verified
> output. The caller must catch `LLMConsensusError` and handle it as a
> routing failure, not as a non-verified fallback.

---

## Example 4: Proof-Policy Configuration

### Receipt-Only (Low Risk)

```python
proof_policy = {"mode": "receipt_only"}
consensus = {
    "enabled": True,
    "quorum": 1,
    "comparison": "normalized_text",
    "fail_closed": False,
}
```

### Receipt-Only with Signatures (Structured Automation)

```python
proof_policy = {
    "mode": "receipt_only",
    "require_signatures": True,
    "signing_key_id": "prod-key-v1",
}
consensus = {
    "enabled": True,
    "quorum": 2,
    "min_operators": 3,
    "comparison": "canonical_json",
    "fail_closed": True,
}
```

### TEE or ZKML (High-Assurance Attestation)

```python
proof_policy = {
    "mode": "tee_or_zkml",
    "tee_measurement_allowlist": ["enclave-measurement-sha256:abcdef..."],
    "require_nonce": True,
}
consensus = {
    "enabled": True,
    "quorum": 2,
    "min_operators": 3,
    "comparison": "canonical_json",
    "fail_closed": True,
    "timeout_s": 60,
}
```

### ZKML Required (Bounded Classifier)

```python
proof_policy = {
    "mode": "zkml_required",
    "verifier_key_hash": "sha256:verifier-key-hash-here",
    "circuit_id": "service-category-classifier-v1",
    "circuit_version": "1.0.0",
}
consensus = {
    "enabled": True,
    "quorum": 2,
    "min_operators": 3,
    "comparison": "canonical_json",
    "fail_closed": True,
}
```

> **Warning — zkml_required applies only to bounded models**: Do not apply
> `zkml_required` policy to full large language model generation. A ZKML proof
> proves only the circuit that was verified. Claiming full LLM generation is
> ZKML-proven without a circuit that encompasses the entire generation is
> incorrect. Use `zkml_required` only for pinned bounded classifiers or checker
> circuits where a real verifier key and circuit commitment exist.

---

## Fail-Closed Behavior Reference

| Condition | `fail_closed=True` | `fail_closed=False` |
| --- | --- | --- |
| Quorum not met | Raise `LLMConsensusError` | Return partial result with `quorum_result="quorum_not_met"` |
| No successful operator responses | Raise `LLMConsensusError` | Return empty receipt |
| Tied normalized outputs | Raise `LLMConsensusError` | Return tie receipt |
| Invalid quorum configuration | Raise `LLMConsensusError` | Return error receipt |
| Proof verification failure | Raise `LLMConsensusError` | Return unverified receipt |

**Always use `fail_closed=True` for:**
- Service eligibility or entitlement decisions
- Emergency call routing
- Onchain or institutional audit workflows
- Any output that will be stored or acted upon without human review

---

## Receipt Fields Reference

A `ConsensusReceipt` includes:

| Field | Description |
| --- | --- |
| `schema_version` | Always `llm-router-consensus-receipt-v1` |
| `request_hash` | SHA-256 of the canonical request payload |
| `output_hash` | SHA-256 of the raw output |
| `normalized_output_hash` | SHA-256 after comparison-mode normalization |
| `quorum_result` | `quorum_met`, `quorum_not_met`, or `quorum_error` |
| `quorum` | Required quorum threshold |
| `comparison` | Comparison mode used (`exact`, `canonical_json`, `normalized_text`, `semantic`) |
| `proof_policy` | Proof policy dict bound at request time |
| `operator_responses` | Per-operator results including output hash and optional signature |
| `receipt_hash` | SHA-256 of the full receipt JSON |
| `created_at` | UTC ISO timestamp of receipt creation |

---

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_CONSENSUS_ENABLED` | `false` | Enable consensus mode |
| `LLM_CONSENSUS_MODE` | `local_quorum` | Consensus mode |
| `LLM_CONSENSUS_QUORUM` | `1` | Required agreement count |
| `LLM_CONSENSUS_MIN_OPERATORS` | `1` | Minimum operator count |
| `LLM_CONSENSUS_COMPARISON` | `exact` | Output comparison mode |
| `LLM_CONSENSUS_FAIL_CLOSED` | `true` | Raise on quorum failure |
| `LLM_CONSENSUS_TIMEOUT_S` | `30` | Total fan-out timeout (seconds) |
| `LLM_CONSENSUS_RECEIPT_PATH` | — | Write receipt JSON to this path |
| `LLM_CONSENSUS_RECEIPT_JSONL_PATH` | — | Append receipt to this JSONL file |

---

## Troubleshooting

**Systematic quorum failures with `canonical_json` comparison**: Operators are
producing different JSON structure or key ordering. Ensure the model is prompted
with an explicit JSON schema, `temperature=0`, `do_sample=False`, and that all
operators use the same model version.

**`LLMConsensusError: Consensus quorum not met`**: Fewer operators agreed than
`quorum` requires. Check operator availability, model consistency, and that
`comparison` mode matches the output format. Lower `quorum` only in development.

**Receipt hash mismatch**: The receipt was mutated after creation, or a
downstream verifier is computing the hash on a different serialization. Use
`receipt.to_json()` as the canonical serialization source.

**CRE verification failure**: The CRE workflow ID, registry, or model policy ID
in the receipt does not match the expected values. Verify the workflow was
deployed to the correct registry and that the `proof_policy` dict matches the
deployment configuration exactly.

---

## Security Notes

- Never log or persist raw prompts that contain PII, credentials, or sensitive
  caller data. Use `prompt_redaction_policy: "hash_only"` and store only the
  `prompt_hash` in receipts.
- Do not place private inputs (API keys, signing keys, enclave secrets) in the
  `generation_params` dict. These fields are hashed and included in receipt
  payloads.
- Production operator signing keys must be rotated independently of model
  versions. A compromised signing key invalidates signature evidence but does
  not automatically invalidate ZKML or TEE proofs.
- Semantic comparison (`comparison: "semantic"`) is advisory only and must not
  be used as the sole quorum criterion for high-impact decisions. It does not
  provide byte-level binding between the output and the receipt.
