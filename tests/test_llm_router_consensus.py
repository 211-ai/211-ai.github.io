"""Tests for ipfs_accelerate_py.llm_router consensus wrapper."""

from __future__ import annotations

from typing import Any

from ipfs_accelerate_py import llm_router
from ipfs_accelerate_py.llm_consensus import (
    ConsensusRequest,
    ConsensusReceipt,
    LocalConsensusOperator,
    load_consensus_config,
)


def test_generate_text_consensus_returns_receipt_with_explicit_operators() -> None:
    operators = [
        LocalConsensusOperator("op-a", lambda _: "{\"answer\":\"yes\"}", provider="mock"),
        LocalConsensusOperator("op-b", lambda _: "{\n  \"answer\": \"yes\"\n}", provider="mock"),
    ]

    receipt = llm_router.generate_text_consensus(
        "return json",
        model_name="mock-model",
        provider="mock",
        consensus={
            "comparison": "canonical_json",
            "quorum": 2,
            "min_operators": 2,
            "nonce": "nonce-1",
        },
        operators=operators,
    )

    assert isinstance(receipt, ConsensusReceipt)
    assert receipt.consensus.accepted is True
    assert receipt.request.provider == "mock"
    assert receipt.request.model_name == "mock-model"
    assert receipt.text.replace(" ", "").replace("\n", "") in {
        "{\"answer\":\"yes\"}",
        "{\"answer\":\"yes\"}",
    }


def test_generate_text_consensus_can_return_text_only() -> None:
    text = llm_router.generate_text_consensus(
        "return json",
        consensus={"comparison": "canonical_json", "quorum": 1, "nonce": "nonce-1"},
        operators=[LocalConsensusOperator("op-a", lambda _: "{\"answer\":\"yes\"}")],
        return_receipt=False,
    )

    assert text == "{\"answer\":\"yes\"}"


def test_generate_text_consensus_normalizes_provider_alias_for_request() -> None:
    seen: dict[str, Any] = {}

    def _operator(request: ConsensusRequest) -> str:
        seen["provider"] = request.provider
        return "{\"answer\":\"yes\"}"

    receipt = llm_router.generate_text_consensus(
        "return json",
        provider="hf",
        consensus={"comparison": "canonical_json", "quorum": 1, "nonce": "nonce-1"},
        operators=[LocalConsensusOperator("op-a", _operator)],
    )

    assert isinstance(receipt, ConsensusReceipt)
    assert seen["provider"] == "hf_inference_api"
    assert receipt.request.provider == "hf_inference_api"


def test_generate_text_consensus_default_operator_uses_datasets_router(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_generate_text(prompt: str, **kwargs: Any) -> str:
        calls.append({"prompt": prompt, **kwargs})
        return "{\"answer\":\"yes\"}"

    monkeypatch.setattr(llm_router._datasets_llm_router, "generate_text", _fake_generate_text)

    receipt = llm_router.generate_text_consensus(
        "return json",
        provider="huggingface",
        model_name="mock-model",
        consensus={"comparison": "canonical_json", "quorum": 1, "nonce": "nonce-1"},
        temperature=0,
    )

    assert isinstance(receipt, ConsensusReceipt)
    assert receipt.consensus.accepted is True
    assert calls == [
        {
            "prompt": "return json",
            "model_name": "mock-model",
            "provider": "hf_inference_api",
            "temperature": 0,
        }
    ]


def test_generate_text_existing_behavior_still_delegates(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_generate_text(prompt: str, **kwargs: Any) -> str:
        calls.append({"prompt": prompt, **kwargs})
        return "plain text"

    monkeypatch.setattr(llm_router._datasets_llm_router, "generate_text", _fake_generate_text)

    text = llm_router.generate_text("hello", provider="hf", temperature=0)

    assert text == "plain text"
    assert calls == [
        {
            "prompt": "hello",
            "provider": "hf_inference_api",
            "temperature": 0,
        }
    ]


def test_load_consensus_config_reads_env_with_type_coercion() -> None:
    config = load_consensus_config(
        env={
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_MODE": "libp2p_quorum",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_COMPARISON": "canonical_json",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_QUORUM": "2",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_MIN_OPERATORS": "3",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_TIMEOUT_S": "12.5",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_OPERATOR_TIMEOUT_S": "4.5",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_FAIL_CLOSED": "false",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_CONTEXT_CIDS": "bafy-a,bafy-b",
        }
    )

    assert config["mode"] == "libp2p_quorum"
    assert config["comparison"] == "canonical_json"
    assert config["quorum"] == 2
    assert config["min_operators"] == 3
    assert config["timeout_s"] == 12.5
    assert config["operator_timeout_s"] == 4.5
    assert config["fail_closed"] is False
    assert config["context_cids"] == ["bafy-a", "bafy-b"]


def test_load_consensus_config_explicit_values_override_env() -> None:
    config = load_consensus_config(
        {
            "comparison": "exact",
            "quorum": 1,
            "minOperators": 1,
            "failClosed": True,
        },
        env={
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_COMPARISON": "canonical_json",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_QUORUM": "3",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_MIN_OPERATORS": "5",
            "IPFS_ACCELERATE_PY_LLM_CONSENSUS_FAIL_CLOSED": "false",
        },
    )

    assert config["comparison"] == "exact"
    assert config["quorum"] == 1
    assert config["min_operators"] == 1
    assert config["fail_closed"] is True


def test_load_consensus_config_rejects_impossible_quorum() -> None:
    try:
        load_consensus_config({"quorum": 3, "min_operators": 2}, env={})
    except Exception as exc:
        assert "quorum cannot exceed min_operators" in str(exc)
    else:
        raise AssertionError("expected impossible quorum to fail")


def test_generate_text_consensus_uses_env_config_when_explicit_config_missing(monkeypatch) -> None:
    monkeypatch.setenv("IPFS_ACCELERATE_PY_LLM_CONSENSUS_COMPARISON", "canonical_json")
    monkeypatch.setenv("IPFS_ACCELERATE_PY_LLM_CONSENSUS_QUORUM", "1")
    monkeypatch.setenv("IPFS_ACCELERATE_PY_LLM_CONSENSUS_MIN_OPERATORS", "1")
    monkeypatch.setenv("IPFS_ACCELERATE_PY_LLM_CONSENSUS_NONCE", "env-nonce")

    receipt = llm_router.generate_text_consensus(
        "return json",
        operators=[LocalConsensusOperator("op-a", lambda _: "{\"answer\":\"yes\"}")],
    )

    assert isinstance(receipt, ConsensusReceipt)
    assert receipt.request.comparison == "canonical_json"
    assert receipt.request.request_id == "env-nonce"
