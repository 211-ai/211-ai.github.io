"""Compatibility wrapper around :mod:`ipfs_datasets_py.llm_router`."""

from __future__ import annotations

from typing import Any

from ipfs_datasets_py import llm_router as _datasets_llm_router

from .llm_consensus import (
    ConsensusReceipt,
    LocalConsensusOperator,
    build_consensus_request,
    load_consensus_config,
    run_local_consensus,
)


def _normalize_provider(provider: str | None) -> str | None:
    raw = (provider or "").strip()
    if not raw:
        return None
    if raw.lower() in {"hf", "huggingface"}:
        return "hf_inference_api"
    return raw


def generate_text(prompt: str, *args: Any, provider: str | None = None, **kwargs: Any) -> str:
    return str(
        _datasets_llm_router.generate_text(
            prompt,
            *args,
            provider=_normalize_provider(provider),
            **kwargs,
        )
    )


def get_llm_provider(provider: str | None = None, *args: Any, **kwargs: Any) -> Any:
    return _datasets_llm_router.get_llm_provider(_normalize_provider(provider), *args, **kwargs)


def clear_llm_router_caches() -> None:
    _datasets_llm_router.clear_llm_router_caches()


def generate_text_consensus(
    prompt: str,
    *,
    model_name: str | None = None,
    provider: str | None = None,
    consensus: dict[str, Any] | None = None,
    proof_policy: dict[str, Any] | None = None,
    operators: list[Any] | tuple[Any, ...] | None = None,
    return_receipt: bool = True,
    **kwargs: Any,
) -> ConsensusReceipt | str:
    options = load_consensus_config(dict(consensus or {}))
    if not options["enabled"]:
        text = generate_text(prompt, provider=provider, model_name=model_name, **kwargs)
        return text if not return_receipt else run_local_consensus(
            request=build_consensus_request(
                prompt=prompt,
                provider=_normalize_provider(provider),
                model_name=model_name,
                generation_params=dict(kwargs),
                proof_policy=dict(proof_policy or {"mode": "receipt_only"}),
                comparison=options["comparison"],
                quorum=1,
                min_operators=1,
                metadata={"mode": "disabled"},
            ),
            operators=[LocalConsensusOperator("disabled-local-router", lambda _: text, provider=_normalize_provider(provider) or "auto")],
            fail_closed=False,
        )
    normalized_provider = _normalize_provider(provider)

    response_schema = kwargs.get("response_schema")
    if response_schema is None:
        response_schema = kwargs.get("response_format")

    request = build_consensus_request(
        prompt=prompt,
        request_id=str(options["request_id"] or "") or None,
        provider=normalized_provider,
        model_name=model_name,
        model_commitment=str(options["model_commitment"] or "") or None,
        tokenizer_commitment=str(options["tokenizer_commitment"] or "") or None,
        generation_params=dict(kwargs),
        response_schema=response_schema if isinstance(response_schema, dict) else {},
        proof_policy=dict(proof_policy or {"mode": "receipt_only"}),
        nonce=str(options["nonce"]) if options["nonce"] is not None else None,
        deadline_unix_ms=int(options["deadline_unix_ms"]),
        prompt_cid=str(options["prompt_cid"]) if options["prompt_cid"] is not None else None,
        context_cids=list(options["context_cids"]),
        prompt_redaction_policy=str(options["prompt_redaction_policy"]),
        comparison=str(options["comparison"]),
        quorum=int(options["quorum"]),
        min_operators=int(options["min_operators"]),
        metadata={"mode": str(options["mode"])},
    )

    resolved_operators: list[Any]
    if operators:
        resolved_operators = list(operators)
    else:
        operator_kwargs = dict(kwargs)

        def _generate(_: Any) -> str:
            return str(
                _datasets_llm_router.generate_text(
                    prompt,
                    model_name=model_name,
                    provider=normalized_provider,
                    **operator_kwargs,
                )
            )

        resolved_operators = [
            LocalConsensusOperator(
                operator_id=str(options["operator_id"] or "local-router"),
                handler=_generate,
                provider=normalized_provider or "auto",
                model_name=model_name,
            )
        ]

    receipt = run_local_consensus(
        request=request,
        operators=resolved_operators,
        timeout_s=float(options["timeout_s"]),
        operator_timeout_s=options["operator_timeout_s"],
        fail_closed=bool(options["fail_closed"]),
        receipt_path=options["receipt_path"],
        receipt_jsonl_path=options["receipt_jsonl_path"],
    )
    return receipt if return_receipt else receipt.text


def __getattr__(name: str) -> Any:
    return getattr(_datasets_llm_router, name)


__all__ = ["generate_text", "generate_text_consensus", "get_llm_provider", "clear_llm_router_caches"]
