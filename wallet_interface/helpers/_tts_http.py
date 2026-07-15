# ruff: noqa: E501
"""IndexTTS / Whisper HTTP credential and transport helpers.

Dependency tier: optional (needs ipfs_datasets_py for resolve_secret; _app for
LLM routing; falls back gracefully so pure-HTTP helpers are always importable).
"""

from __future__ import annotations

import json
import mimetypes
import os
import time
import uuid
from collections.abc import Mapping
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request

try:
    from .._vendor import ensure_ipfs_datasets_py_path

    ensure_ipfs_datasets_py_path()

    from ipfs_datasets_py.utils.secrets import resolve_secret  # noqa: E402

    _SECRETS_AVAILABLE = True
except ImportError:  # pragma: no cover
    resolve_secret = None  # type: ignore[assignment]
    _SECRETS_AVAILABLE = False

try:
    from ._app import _prepare_hf_router_environment  # noqa: E402

    _APP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _prepare_hf_router_environment = None  # type: ignore[assignment]
    _APP_AVAILABLE = False

from ._tts_config import (
    _clean_voice_reply_text,
    _hf_whisper_model_name,
    _hf_whisper_timeout_seconds,
    _indextts_space_base_url,
    _indextts_timeout_seconds,
    _voice_llm_timeout_seconds,
)
from ._tts_gradio import (
    _extract_hf_whisper_text,
    _first_upload_path,
)


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _configured_hf_token() -> str:
    if resolve_secret is None:  # pragma: no cover
        return os.getenv("HF_TOKEN", "").strip()
    return (
        resolve_secret(
            "WALLET_INDEXTTS_HF_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACEHUB_API_TOKEN",
            "IPFS_DATASETS_PY_HF_API_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
        )
        or ""
    ).strip()


def _indextts_headers(*, accept: str = "application/json") -> dict[str, str]:
    headers = {"Accept": accept}
    token = _configured_hf_token()
    if token:
        headers["Authorization"] = "Bearer " + token
    bill_to = (
        os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to
    return headers


def _publicus_indextts_credential_warning() -> dict[str, Any] | None:
    space_url = _indextts_space_base_url().lower()
    if "publicus-indextts" not in space_url and "publicus/indextts" not in (os.getenv("WALLET_INDEXTTS_MODEL_NAME", "").lower()):
        return None
    token_present = bool(_configured_hf_token())
    if token_present:
        return None
    bill_to = (
        os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip() or "publicus"
    return {
        "code": "publicus_indextts_missing_hf_token",
        "message": (
            "Publicus IndexTTS is configured without a Hugging Face token. "
            "Set WALLET_INDEXTTS_HF_TOKEN or HF_TOKEN and keep X-HF-Bill-To set to the Publicus account."
        ),
        "spaceUrl": _indextts_space_base_url(),
        "modelName": os.getenv("WALLET_INDEXTTS_MODEL_NAME", "Publicus/IndexTTS-2-Demo"),
        "billTo": bill_to,
        "envVars": ["WALLET_INDEXTTS_HF_TOKEN", "HF_TOKEN", "WALLET_INDEXTTS_HF_BILL_TO"],
    }


def _voice_proxy_runtime_warnings() -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    publicus_warning = _publicus_indextts_credential_warning()
    if publicus_warning:
        warnings.append(publicus_warning)
    return warnings


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------


def _http_json(method: str, url: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = _indextts_headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url, data=data, headers=headers, method=method)
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        raw = response.read()
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{url} did not return a JSON object")
    return parsed


def _http_bytes(url: str) -> tuple[bytes, str]:
    request = urllib_request.Request(url, headers=_indextts_headers(accept="audio/*, application/octet-stream"))
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        return response.read(), response.headers.get("Content-Type") or "audio/wav"


def _gradio_upload_file(data: bytes, file_name: str, mime_type: str) -> dict[str, Any]:
    boundary = f"----211AiIndexTts{uuid.uuid4().hex}"
    safe_name = os.path.basename(file_name or "reference.wav")
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="files"; filename="{safe_name}"\r\n'.encode(),
            f"Content-Type: {mime_type or 'application/octet-stream'}\r\n\r\n".encode(),
            data,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    headers = _indextts_headers()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request = urllib_request.Request(
        f"{_indextts_space_base_url()}/gradio_api/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    upload_path = _first_upload_path(parsed)
    if not upload_path:
        raise ValueError("IndexTTS upload did not return a Gradio file path")
    return {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": safe_name}


# ---------------------------------------------------------------------------
# Whisper STT (HTTP-direct, no HFSpaceClient)
# ---------------------------------------------------------------------------


def _run_hf_whisper_stt(
    audio: bytes,
    *,
    audio_name: str | None = None,
    audio_type: str | None = None,
    language: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    if not audio:
        raise ValueError("audio is required")
    if resolve_secret is None:  # pragma: no cover
        token = os.getenv("HF_TOKEN", "").strip()
    else:
        token = (
            resolve_secret(
                "WALLET_HF_WHISPER_TOKEN",
                "IPFS_DATASETS_PY_HF_API_TOKEN",
                "HF_TOKEN",
                "HUGGINGFACEHUB_API_TOKEN",
                "HUGGINGFACE_API_TOKEN",
                "HUGGINGFACE_HUB_TOKEN",
            )
            or ""
        ).strip()
    if not token:
        raise ValueError("Hugging Face token is required for Whisper STT")
    selected_model = _hf_whisper_model_name(model_name)
    base_url = (
        os.getenv("WALLET_HF_WHISPER_BASE_URL", "https://router.huggingface.co/hf-inference/models")
        .strip()
        .rstrip("/")
    )
    content_type = (audio_type or mimetypes.guess_type(audio_name or "")[0] or "audio/wav").strip()
    if content_type in {"application/octet-stream", "binary/octet-stream"}:
        content_type = mimetypes.guess_type(audio_name or "")[0] or "audio/wav"
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
        "Content-Type": content_type,
    }
    bill_to = (
        os.getenv("WALLET_HF_WHISPER_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to
    if language:
        headers["X-Wallet-STT-Language"] = language
    url = f"{base_url}/{urllib_parse.quote(selected_model, safe='/')}"
    request = urllib_request.Request(url, data=audio, headers=headers, method="POST")
    with urllib_request.urlopen(request, timeout=_hf_whisper_timeout_seconds()) as response:
        raw = response.read()
    result = json.loads(raw.decode("utf-8"))
    text = _extract_hf_whisper_text(result)
    return {
        "model": selected_model,
        "modelName": selected_model,
        "provider": "huggingface-whisper",
        "text": text,
    }


# ---------------------------------------------------------------------------
# LLM-based voice-reply text generation (no HFSpaceClient)
# ---------------------------------------------------------------------------


def _generate_indextts_voice_reply_text(
    *,
    mode: str,
    text: str,
    system_prompt: str | None,
    user_prompt: str | None,
    fallback_text: str | None,
) -> tuple[str, dict[str, Any]]:
    timings: dict[str, Any] = {}
    fallback = str(fallback_text or "").strip()
    prompt = str(text or "").strip()
    if str(mode or "").strip().lower() != "voice-reply":
        reply_text = prompt or fallback
        if not reply_text:
            raise ValueError("text is required")
        return reply_text, timings

    user_text = str(user_prompt or "").strip()
    system_text = str(system_prompt or "").strip()
    if not prompt:
        prompt = "\n\n".join(part for part in (system_text, f"Caller request: {user_text}" if user_text else "") if part)
    if not prompt:
        raise ValueError("text or user_prompt is required")

    llm_start = time.perf_counter()
    try:
        if _prepare_hf_router_environment is None:  # pragma: no cover
            raise ImportError("_app not available")
        kwargs = _prepare_hf_router_environment(
            {
                "max_new_tokens": int(os.getenv("WALLET_VOICE_LLM_MAX_NEW_TOKENS", "120")),
                "temperature": float(os.getenv("WALLET_VOICE_LLM_TEMPERATURE", "0.2")),
                "timeout": _voice_llm_timeout_seconds(),
            }
        )
        from ipfs_datasets_py import llm_router  # noqa: WPS433

        provider = os.getenv("WALLET_VOICE_LLM_PROVIDER", "hf_inference_api").strip() or "hf_inference_api"
        model_name = (
            os.getenv("WALLET_VOICE_LLM_MODEL")
            or os.getenv("WALLET_AI_ROUTER_LLM_MODEL")
            or "Qwen/Qwen3.5-2B"
        ).strip()
        generated = llm_router.generate_text(
            prompt,
            model_name=model_name,
            provider=provider,
            **kwargs,
        )
        timings["llm_request_ms"] = max(0, int((time.perf_counter() - llm_start) * 1000))
        timings["llm_provider"] = provider
        timings["llm_model"] = model_name
        return _clean_voice_reply_text(generated, prompt=prompt, fallback_text=fallback), timings
    except Exception as exc:
        timings["llm_request_ms"] = max(0, int((time.perf_counter() - llm_start) * 1000))
        timings["llm_error"] = str(exc)[:240]
        if fallback:
            return fallback, timings
        raise
