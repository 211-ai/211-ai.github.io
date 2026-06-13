"""Tests for the Chainlink CRE bridge client skeleton."""

from __future__ import annotations

import pytest

from ipfs_accelerate_py.chainlink_cre import (
    CREInferenceResult,
    CRESubmission,
    ChainlinkCREBridgeClient,
    ChainlinkCREBridgeError,
)
from ipfs_accelerate_py.llm_consensus import (
    ConsensusReceipt,
    build_consensus_request,
    normalized_output_hash,
    sha256_digest,
)


def _request():
    return build_consensus_request(
        prompt="Return JSON with answer=yes",
        provider="mock",
        model_name="mock-model",
        proof_policy={"mode": "chainlink_cre"},
        comparison="canonical_json",
        quorum=1,
        min_operators=1,
        nonce="nonce-cre-1",
    )


def _client(**kwargs):
    values = {"workflow_id": "wf-llm-router-v1", "don_id": "don-42"}
    values.update(kwargs)
    return ChainlinkCREBridgeClient(**values)


def test_simulated_submit_wait_verify_and_receipt() -> None:
    request = _request()
    output_text = "{\"answer\":\"yes\"}"
    client = _client(simulated_response={"output_text": output_text, "cre_round": 7})

    submission = client.submit(request, prompt="raw prompt stays outside receipt")
    result = client.wait(submission)
    verification = client.verify(result, request)
    receipt = client.build_receipt(
        request,
        result,
        verification=verification,
        fail_closed=True,
        created_at="2026-06-13T12:00:00Z",
    )

    assert isinstance(submission, CRESubmission)
    assert submission.workflow_id == "wf-llm-router-v1"
    assert result.request_hash == request.request_hash
    assert result.output_hash == sha256_digest(output_text)
    assert result.normalized_output_hash == normalized_output_hash(
        output_text,
        comparison="canonical_json",
    )
    assert verification.verified is True
    assert receipt.consensus.accepted is True
    assert receipt.responses[0].transport == "chainlink_cre"
    assert receipt.proof.verified is True
    assert receipt.proof.cre_workflow_id == "wf-llm-router-v1"
    assert receipt.text == output_text

    restored = ConsensusReceipt.from_json(receipt.to_json())
    assert restored.proof.metadata["cre_round"] == 7


def test_run_fails_closed_for_workflow_mismatch() -> None:
    request = _request()
    client = _client(
        simulated_response={
            "workflow_id": "wf-wrong",
            "output_text": "{\"answer\":\"yes\"}",
        }
    )

    with pytest.raises(ChainlinkCREBridgeError, match="cre_workflow_id_mismatch"):
        client.run(request)


def test_verify_fails_for_request_hash_mismatch() -> None:
    request = _request()
    client = _client()
    output_text = "{\"answer\":\"yes\"}"
    result = CREInferenceResult(
        submission_id="sub-1",
        workflow_id="wf-llm-router-v1",
        don_id="don-42",
        request_hash="sha256:wrong-request",
        output_hash=sha256_digest(output_text),
        output_text=output_text,
        cre_round=1,
        cre_report_hash="sha256:report",
        nonce="nonce-cre-1",
    )

    verification = client.verify(result, request)

    assert verification.verified is False
    assert verification.reason == "request_hash_mismatch"


def test_verify_fails_for_output_hash_mismatch() -> None:
    request = _request()
    client = _client()
    result = CREInferenceResult(
        submission_id="sub-1",
        workflow_id="wf-llm-router-v1",
        don_id="don-42",
        request_hash=request.request_hash or "",
        output_hash="sha256:wrong-output",
        output_text="{\"answer\":\"yes\"}",
        cre_round=1,
        cre_report_hash="sha256:report",
        nonce="nonce-cre-1",
    )

    verification = client.verify(result, request)

    assert verification.verified is False
    assert verification.reason == "output_hash_mismatch"


def test_verify_fails_closed_for_missing_cre_metadata() -> None:
    request = _request()
    client = _client()
    result = {
        "submission_id": "sub-1",
        "workflow_id": "wf-llm-router-v1",
        "don_id": "don-42",
        "request_hash": request.request_hash,
        "output_hash": sha256_digest("{\"answer\":\"yes\"}"),
        "output_text": "{\"answer\":\"yes\"}",
        "cre_round": 1,
    }

    verification = client.verify(result, request)

    assert verification.verified is False
    assert verification.reason == "cre_report_hash_missing"


def test_verify_fails_closed_when_output_hash_cannot_be_bound() -> None:
    request = _request()
    client = _client()
    result = {
        "submission_id": "sub-1",
        "workflow_id": "wf-llm-router-v1",
        "don_id": "don-42",
        "request_hash": request.request_hash,
        "output_hash": "sha256:result-only",
        "cre_round": 1,
        "cre_report_hash": "sha256:report",
    }

    verification = client.verify(result, request)

    assert verification.verified is False
    assert verification.reason == "expected_output_hash_missing"


def test_hash_only_result_can_be_verified_with_expected_output_hash() -> None:
    request = _request()
    client = _client()
    result = {
        "submission_id": "sub-1",
        "workflow_id": "wf-llm-router-v1",
        "don_id": "don-42",
        "request_hash": request.request_hash,
        "output_hash": "sha256:result-only",
        "cre_round": 1,
        "cre_report_hash": "sha256:report",
        "nonce": "nonce-cre-1",
    }

    verification = client.verify(
        result,
        request,
        expected_output_hash="sha256:result-only",
    )

    assert verification.verified is True


def test_wait_requires_handler_or_simulation() -> None:
    request = _request()
    client = _client()
    submission = client.submit(request)

    with pytest.raises(ChainlinkCREBridgeError, match="cre_wait_handler_required"):
        client.wait(submission)
