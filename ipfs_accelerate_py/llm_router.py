"""Compatibility wrapper around :mod:`ipfs_datasets_py.llm_router`."""

from __future__ import annotations

from typing import Any

from ipfs_datasets_py import llm_router as _datasets_llm_router


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


def __getattr__(name: str) -> Any:
    return getattr(_datasets_llm_router, name)


__all__ = ["generate_text", "get_llm_provider", "clear_llm_router_caches"]
