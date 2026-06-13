"""Unit tests for ipfs_accelerate_py.proof_verifiers.

Covers all four verifier classes with scenarios for:
- valid proof metadata (happy path)
- missing required fields
- mismatched binding fields (request hash, output hash, model commitment)
- replayed proof metadata (nonce / CRE round replay)
"""

from __future__ import annotations

import pytest

from ipfs_accelerate_py.proof_verifiers import (
    ChainlinkCREVerifier,
    ProofContext,
    ReceiptOnlyVerifier,
    TEEVerifier,
    VerificationResult,
    ZKMLVerifier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(
    request_hash: str = "sha256:req-abc",
    output_hash: str = "sha256:out-xyz",
    model_commitment: str = "sha256:model-v1",
    nonce: str = "nonce-unique-1",
) -> ProofContext:
    return ProofContext(
        request_hash=request_hash,
        output_hash=output_hash,
        model_commitment=model_commitment,
        nonce=nonce,
    )


def _receipt_meta(
    request_hash: str = "sha256:req-abc",
    output_hash: str = "sha256:out-xyz",
    nonce: str = "nonce-unique-1",
) -> dict:
    return {
        "request_hash": request_hash,
        "output_hash": output_hash,
        "nonce": nonce,
    }


def _tee_meta(
    request_hash: str = "sha256:req-abc",
    output_hash: str = "sha256:out-xyz",
    model_commitment: str = "sha256:model-v1",
    tee_measurement: str = "pcr0:aabbcc",
    tee_signer: str = "cert:tee-signer-pub",
    tee_nonce: str = "tee-nonce-1",
    tee_expiry_unix_ms: int = 9_999_999_999_000,
) -> dict:
    return {
        "request_hash": request_hash,
        "output_hash": output_hash,
        "model_commitment": model_commitment,
        "tee_measurement": tee_measurement,
        "tee_signer": tee_signer,
        "tee_nonce": tee_nonce,
        "tee_expiry_unix_ms": tee_expiry_unix_ms,
    }


def _zkml_verifier() -> ZKMLVerifier:
    return ZKMLVerifier(
        expected_verifier_key_hash="vk:sha256:pinned-key",
        expected_circuit_id="circuit-llm-checker-v1",
        expected_circuit_version="1.0.0",
    )


def _zkml_meta(
    request_hash: str = "sha256:req-abc",
    output_hash: str = "sha256:out-xyz",
    model_commitment: str = "sha256:model-v1",
    verifier_key_hash: str = "vk:sha256:pinned-key",
    circuit_id: str = "circuit-llm-checker-v1",
    circuit_version: str = "1.0.0",
    public_inputs_hash: str = "sha256:pub-inputs",
    proof_bytes: str = "0xdeadbeef",
    nonce: str = "nonce-unique-1",
) -> dict:
    return {
        "request_hash": request_hash,
        "output_hash": output_hash,
        "model_commitment": model_commitment,
        "verifier_key_hash": verifier_key_hash,
        "circuit_id": circuit_id,
        "circuit_version": circuit_version,
        "public_inputs_hash": public_inputs_hash,
        "proof_bytes": proof_bytes,
        "nonce": nonce,
    }


def _cre_verifier() -> ChainlinkCREVerifier:
    return ChainlinkCREVerifier(
        expected_workflow_id="wf-llm-router-v1",
        expected_don_id="don-42",
    )


def _cre_meta(
    request_hash: str = "sha256:req-abc",
    output_hash: str = "sha256:out-xyz",
    cre_workflow_id: str = "wf-llm-router-v1",
    cre_don_id: str = "don-42",
    cre_round: int = 1,
    cre_report_hash: str = "sha256:cre-report",
    nonce: str = "nonce-unique-1",
) -> dict:
    return {
        "request_hash": request_hash,
        "output_hash": output_hash,
        "cre_workflow_id": cre_workflow_id,
        "cre_don_id": cre_don_id,
        "cre_round": cre_round,
        "cre_report_hash": cre_report_hash,
        "nonce": nonce,
    }


# ===========================================================================
# ReceiptOnlyVerifier
# ===========================================================================

class TestReceiptOnlyVerifier:
    def test_valid_metadata_returns_verified(self) -> None:
        verifier = ReceiptOnlyVerifier()
        result = verifier.verify(_receipt_meta(), _ctx())
        assert result.verified is True
        assert result.verifier == "receipt-only-v1"
        assert result.reason == "receipt_binding_verified"

    def test_missing_proof_request_hash_fails(self) -> None:
        verifier = ReceiptOnlyVerifier()
        meta = _receipt_meta()
        del meta["request_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "request_hash" in result.reason

    def test_missing_proof_output_hash_fails(self) -> None:
        verifier = ReceiptOnlyVerifier()
        meta = _receipt_meta()
        del meta["output_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "output_hash" in result.reason

    def test_mismatched_request_hash_fails(self) -> None:
        verifier = ReceiptOnlyVerifier()
        meta = _receipt_meta(request_hash="sha256:wrong-req")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "request_hash_mismatch"

    def test_mismatched_output_hash_fails(self) -> None:
        verifier = ReceiptOnlyVerifier()
        meta = _receipt_meta(output_hash="sha256:wrong-out")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "output_hash_mismatch"

    def test_replayed_nonce_fails(self) -> None:
        verifier = ReceiptOnlyVerifier()
        meta = _receipt_meta(nonce="reused-nonce")
        ctx = _ctx(nonce="reused-nonce")
        first = verifier.verify(meta, ctx)
        assert first.verified is True
        # Second attempt with same nonce must fail
        second = verifier.verify(_receipt_meta(nonce="reused-nonce"), _ctx(nonce="reused-nonce"))
        assert second.verified is False
        assert second.reason == "replayed_nonce"

    def test_different_nonces_each_accepted(self) -> None:
        verifier = ReceiptOnlyVerifier()
        for i in range(3):
            nonce = f"unique-nonce-{i}"
            result = verifier.verify(_receipt_meta(nonce=nonce), _ctx(nonce=nonce))
            assert result.verified is True, f"Expected verified for nonce {nonce}"

    def test_empty_proof_meta_fails(self) -> None:
        verifier = ReceiptOnlyVerifier()
        result = verifier.verify({}, _ctx())
        assert result.verified is False

    def test_result_is_verification_result_instance(self) -> None:
        verifier = ReceiptOnlyVerifier()
        result = verifier.verify(_receipt_meta(), _ctx())
        assert isinstance(result, VerificationResult)


# ===========================================================================
# TEEVerifier
# ===========================================================================

class TestTEEVerifier:
    def test_valid_metadata_returns_verified(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        result = verifier.verify(_tee_meta(), _ctx())
        assert result.verified is True
        assert result.verifier == "tee-verifier-v1"
        assert result.reason == "tee_attestation_verified"

    def test_missing_proof_request_hash_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta()
        del meta["request_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "request_hash" in result.reason

    def test_missing_proof_output_hash_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta()
        del meta["output_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "output_hash" in result.reason

    def test_missing_model_commitment_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta()
        del meta["model_commitment"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "model_commitment" in result.reason

    def test_mismatched_request_hash_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta(request_hash="sha256:wrong")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "request_hash_mismatch"

    def test_mismatched_output_hash_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta(output_hash="sha256:wrong")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "output_hash_mismatch"

    def test_mismatched_model_commitment_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta(model_commitment="sha256:wrong-model")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "model_commitment_mismatch"

    def test_missing_tee_measurement_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta()
        meta["tee_measurement"] = ""
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "tee_measurement" in result.reason

    def test_missing_tee_signer_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta()
        del meta["tee_signer"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "tee_signer" in result.reason

    def test_missing_tee_nonce_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta = _tee_meta()
        del meta["tee_nonce"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "tee_nonce" in result.reason

    def test_expired_attestation_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=10_000_000_000_000)
        meta = _tee_meta(tee_expiry_unix_ms=1_000)
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "tee_attestation_expired"

    def test_replayed_tee_nonce_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        meta1 = _tee_meta(tee_nonce="tee-nonce-1")
        meta2 = _tee_meta(tee_nonce="tee-nonce-1")
        ctx1 = _ctx(nonce="unique-ctx-1")
        ctx2 = _ctx(nonce="unique-ctx-2")
        first = verifier.verify(meta1, ctx1)
        assert first.verified is True
        second = verifier.verify(meta2, ctx2)
        assert second.verified is False
        assert second.reason == "replayed_nonce"

    def test_empty_proof_meta_fails(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        result = verifier.verify({}, _ctx())
        assert result.verified is False

    def test_result_metadata_includes_measurement_and_signer(self) -> None:
        verifier = TEEVerifier(now_unix_ms=1_000_000)
        result = verifier.verify(_tee_meta(), _ctx())
        assert result.metadata["tee_measurement"] == "pcr0:aabbcc"
        assert result.metadata["tee_signer"] == "cert:tee-signer-pub"


# ===========================================================================
# ZKMLVerifier
# ===========================================================================

class TestZKMLVerifier:
    def test_valid_metadata_returns_verified(self) -> None:
        verifier = _zkml_verifier()
        result = verifier.verify(_zkml_meta(), _ctx())
        assert result.verified is True
        assert result.verifier == "zkml-verifier-v1"
        assert result.reason == "zkml_proof_verified"

    def test_missing_proof_request_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["request_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "request_hash" in result.reason

    def test_missing_proof_output_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["output_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "output_hash" in result.reason

    def test_missing_model_commitment_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["model_commitment"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "model_commitment" in result.reason

    def test_mismatched_request_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta(request_hash="sha256:wrong")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "request_hash_mismatch"

    def test_mismatched_output_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta(output_hash="sha256:wrong")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "output_hash_mismatch"

    def test_mismatched_model_commitment_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta(model_commitment="sha256:wrong-model")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "model_commitment_mismatch"

    def test_missing_verifier_key_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["verifier_key_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "verifier_key_hash_missing"

    def test_mismatched_verifier_key_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta(verifier_key_hash="vk:sha256:unknown-key")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "verifier_key_hash_mismatch"

    def test_missing_circuit_id_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["circuit_id"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "circuit_id_missing"

    def test_mismatched_circuit_id_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta(circuit_id="circuit-unknown")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "circuit_id_mismatch"

    def test_missing_circuit_version_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["circuit_version"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "circuit_version_missing"

    def test_mismatched_circuit_version_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta(circuit_version="9.9.9")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "circuit_version_mismatch"

    def test_missing_public_inputs_hash_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        meta["public_inputs_hash"] = ""
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "public_inputs_hash_missing"

    def test_missing_proof_data_fails(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        meta.pop("proof_bytes", None)
        meta.pop("proof_cid", None)
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "proof_data_missing"

    def test_proof_cid_accepted_instead_of_proof_bytes(self) -> None:
        verifier = _zkml_verifier()
        meta = _zkml_meta()
        del meta["proof_bytes"]
        meta["proof_cid"] = "bafy-proof-cid"
        result = verifier.verify(meta, _ctx())
        assert result.verified is True

    def test_replayed_nonce_fails(self) -> None:
        verifier = _zkml_verifier()
        meta1 = _zkml_meta(nonce="nonce-zkml-1")
        meta2 = _zkml_meta(nonce="nonce-zkml-1")
        ctx1 = _ctx(nonce="nonce-zkml-1")
        ctx2 = _ctx(nonce="nonce-zkml-1")
        first = verifier.verify(meta1, ctx1)
        assert first.verified is True
        second = verifier.verify(meta2, ctx2)
        assert second.verified is False
        assert second.reason == "replayed_nonce"

    def test_empty_proof_meta_fails(self) -> None:
        verifier = _zkml_verifier()
        result = verifier.verify({}, _ctx())
        assert result.verified is False

    def test_result_metadata_includes_circuit_and_inputs(self) -> None:
        verifier = _zkml_verifier()
        result = verifier.verify(_zkml_meta(), _ctx())
        assert result.metadata["circuit_id"] == "circuit-llm-checker-v1"
        assert result.metadata["circuit_version"] == "1.0.0"
        assert result.metadata["public_inputs_hash"] == "sha256:pub-inputs"


# ===========================================================================
# ChainlinkCREVerifier
# ===========================================================================

class TestChainlinkCREVerifier:
    def test_valid_metadata_returns_verified(self) -> None:
        verifier = _cre_verifier()
        result = verifier.verify(_cre_meta(), _ctx())
        assert result.verified is True
        assert result.verifier == "chainlink-cre-verifier-v1"
        assert result.reason == "chainlink_cre_report_verified"

    def test_missing_proof_request_hash_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta()
        del meta["request_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "request_hash" in result.reason

    def test_missing_proof_output_hash_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta()
        del meta["output_hash"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert "output_hash" in result.reason

    def test_mismatched_request_hash_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta(request_hash="sha256:wrong")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "request_hash_mismatch"

    def test_mismatched_output_hash_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta(output_hash="sha256:wrong")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "output_hash_mismatch"

    def test_missing_workflow_id_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta()
        del meta["cre_workflow_id"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "cre_workflow_id_missing"

    def test_mismatched_workflow_id_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta(cre_workflow_id="wf-unknown")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "cre_workflow_id_mismatch"

    def test_missing_don_id_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta()
        del meta["cre_don_id"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "cre_don_id_missing"

    def test_mismatched_don_id_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta(cre_don_id="don-99")
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "cre_don_id_mismatch"

    def test_missing_cre_round_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta()
        del meta["cre_round"]
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "cre_round_missing"

    def test_replayed_cre_round_fails(self) -> None:
        verifier = _cre_verifier()
        meta1 = _cre_meta(cre_round=5, nonce="n-1")
        meta2 = _cre_meta(cre_round=5, nonce="n-2")
        ctx1 = _ctx(nonce="n-1")
        ctx2 = _ctx(nonce="n-2")
        first = verifier.verify(meta1, ctx1)
        assert first.verified is True
        second = verifier.verify(meta2, ctx2)
        assert second.verified is False
        assert second.reason == "replayed_cre_round"

    def test_monotonically_increasing_rounds_accepted(self) -> None:
        verifier = _cre_verifier()
        for i, (r, n) in enumerate([(1, "n-a"), (2, "n-b"), (3, "n-c")]):
            result = verifier.verify(
                _cre_meta(cre_round=r, nonce=n),
                _ctx(nonce=n),
            )
            assert result.verified is True, f"Expected verified for round {r}"
            assert result.metadata["cre_round"] == r

    def test_missing_report_hash_fails(self) -> None:
        verifier = _cre_verifier()
        meta = _cre_meta()
        meta["cre_report_hash"] = ""
        result = verifier.verify(meta, _ctx())
        assert result.verified is False
        assert result.reason == "cre_report_hash_missing"

    def test_replayed_nonce_fails(self) -> None:
        verifier = _cre_verifier()
        meta1 = _cre_meta(cre_round=1, nonce="shared-nonce")
        meta2 = _cre_meta(cre_round=2, nonce="shared-nonce")
        ctx1 = _ctx(nonce="shared-nonce")
        ctx2 = _ctx(nonce="shared-nonce")
        first = verifier.verify(meta1, ctx1)
        assert first.verified is True
        second = verifier.verify(meta2, ctx2)
        assert second.verified is False
        assert second.reason == "replayed_nonce"

    def test_empty_proof_meta_fails(self) -> None:
        verifier = _cre_verifier()
        result = verifier.verify({}, _ctx())
        assert result.verified is False

    def test_result_metadata_includes_workflow_don_round(self) -> None:
        verifier = _cre_verifier()
        result = verifier.verify(_cre_meta(cre_round=7, nonce="n-7"), _ctx(nonce="n-7"))
        assert result.metadata["cre_workflow_id"] == "wf-llm-router-v1"
        assert result.metadata["cre_don_id"] == "don-42"
        assert result.metadata["cre_round"] == 7
