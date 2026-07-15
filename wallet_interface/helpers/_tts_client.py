# ruff: noqa: E501
"""IndexTTS HF Space client and fn-index cache helpers.

All functions in this module require ``ipfs_accelerate_py`` (``HFSpaceClient``).
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

from ipfs_accelerate_py import HFSpaceClient  # noqa: E402

from ._tts_config import (
    _indextts_api_name,
    _indextts_batch_api_name,
    _indextts_cache_ttl_seconds,
    _indextts_space_base_url,
    _indextts_timeout_seconds,
)
from ._tts_http import _indextts_headers


_INDEXTTS_CACHE_LOCK = threading.Lock()
_INDEXTTS_CONFIG_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_INDEXTTS_FN_INDEX_CACHE: dict[tuple[str, str], int] = {}
_INDEXTTS_REFERENCE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}




_INDEXTTS_SPACE_CLIENT: HFSpaceClient | None = None
_INDEXTTS_SPACE_CLIENT_KEY = ""


def _indextts_space_client() -> HFSpaceClient:
    global _INDEXTTS_SPACE_CLIENT
    global _INDEXTTS_SPACE_CLIENT_KEY
    cache_key = "|".join(
        [
            _indextts_space_base_url(),
            str(_indextts_timeout_seconds()),
            os.getenv("WALLET_INDEXTTS_API_NAME", ""),
            os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", ""),
            os.getenv("WALLET_INDEXTTS_HF_BILL_TO", ""),
            os.getenv("IPFS_DATASETS_PY_HF_BILL_TO", ""),
            os.getenv("HF_TOKEN", ""),
            os.getenv("HUGGINGFACEHUB_API_TOKEN", ""),
            os.getenv("IPFS_DATASETS_PY_HF_API_TOKEN", ""),
        ]
    )
    if _INDEXTTS_SPACE_CLIENT is not None and cache_key == _INDEXTTS_SPACE_CLIENT_KEY:
        return _INDEXTTS_SPACE_CLIENT
    _INDEXTTS_SPACE_CLIENT = HFSpaceClient(
        _indextts_space_base_url(),
        timeout_seconds=_indextts_timeout_seconds(),
        headers_factory=lambda: _indextts_headers(),
    )
    _INDEXTTS_SPACE_CLIENT_KEY = cache_key
    return _INDEXTTS_SPACE_CLIENT


def _indextts_config() -> dict[str, Any]:
    cache_key = (_indextts_space_base_url(), _indextts_api_name())
    now = time.time()
    with _INDEXTTS_CACHE_LOCK:
        cached = _INDEXTTS_CONFIG_CACHE.get(cache_key)
        if cached and now - float(cached.get("created_at", 0)) < _indextts_cache_ttl_seconds():
            return dict(cached["config"])
    config = _indextts_space_client().get_config()
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_CONFIG_CACHE[cache_key] = {"created_at": now, "config": dict(config)}
    return config


def _indextts_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    cache_key = (_indextts_space_base_url(), _indextts_api_name())
    with _INDEXTTS_CACHE_LOCK:
        if cache_key in _INDEXTTS_FN_INDEX_CACHE:
            return _INDEXTTS_FN_INDEX_CACHE[cache_key]
    api_name = _indextts_api_name()
    try:
        fn_index = int(
            _indextts_space_client().resolve_fn_index(
                api_name,
                config,
                fallback_markers=("tts", "synth", "generate", "infer", "predict"),
            )
        )
    except Exception as exc:
        raise ValueError(f"IndexTTS api_name {api_name!r} was not found in Gradio config") from exc
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_FN_INDEX_CACHE[cache_key] = fn_index
    return fn_index


def _indextts_batch_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_BATCH_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    api_name = _indextts_batch_api_name()
    if not api_name:
        raise ValueError("WALLET_INDEXTTS_BATCH_API_NAME is empty")
    cache_key = (_indextts_space_base_url(), f"batch:{api_name}")
    with _INDEXTTS_CACHE_LOCK:
        if cache_key in _INDEXTTS_FN_INDEX_CACHE:
            return _INDEXTTS_FN_INDEX_CACHE[cache_key]
    try:
        fn_index = int(_indextts_space_client().resolve_fn_index(api_name, config))
    except Exception as exc:
        raise ValueError(f"IndexTTS batch api_name {api_name!r} was not found in Gradio config") from exc
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_FN_INDEX_CACHE[cache_key] = fn_index
    return fn_index


def _indextts_queue_join(fn_index: int, data: Sequence[Any]) -> str:
    return _indextts_space_client().queue_join(int(fn_index), list(data))


