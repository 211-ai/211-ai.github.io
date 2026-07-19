# ruff: noqa: E501
"""IndexTTS queue-fallback execution and per-space TTS pipeline helpers."""

from __future__ import annotations

import base64
import os
import time
from collections.abc import Mapping, Sequence
from typing import Any

from ._tts_client import (
    _fetch_gradio_file,
    _indextts_batch_audio_references,
    _indextts_batch_fn_index,
    _indextts_config,
    _indextts_fn_index,
    _indextts_queue_join,
    _indextts_space_client,
    _indextts_upload_reference_audio,
    _indextts_wait_for_result,
)
from ._tts_config import (
    _indextts_allow_direct_predict_fallback,
    _indextts_api_name,
    _indextts_batch_api_name,
    _indextts_degraded_fast_fail_enabled,
    _indextts_is_fast_fail_mode,
    _indextts_model_name,
    _indextts_require_batch_mode,
    _indextts_space_base_url,
    _indextts_timeout_seconds,
    _is_opaque_indextts_queue_failure,
)
from ._tts_gradio import (
    _find_gradio_audio_reference,
    _indextts_batch_request_data,
    _indextts_request_data,
)
from ._tts_normalization import _normalize_indextts_spoken_text


def _indextts_execute_with_queue_fallback(
    *,
    fn_index: int,
    data: Sequence[Any],
    timings: dict[str, Any],
    api_name: str,
) -> Mapping[str, Any]:
    stage_start = time.perf_counter()
    session_hash = _indextts_queue_join(fn_index, data)
    timings["queue_join_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))

    stage_start = time.perf_counter()
    queue_error: Exception | None = None
    should_retry_queue = True
    try:
        result = _indextts_wait_for_result(session_hash)
        timings["queue_wait_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
        timings["result_path"] = "queue"
        return result
    except Exception as exc:
        timings["queue_wait_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
        timings["queue_error"] = str(exc)
        if _indextts_is_fast_fail_mode():
            raise
        if not _indextts_allow_direct_predict_fallback():
            raise
        if not _is_opaque_indextts_queue_failure(str(exc)):
            should_retry_queue = False
        queue_error = exc

    if _indextts_is_fast_fail_mode():
        if queue_error is not None:
            raise queue_error
        raise ValueError("IndexTTS fast-fail mode reached fallback guard without queue error")

    if _indextts_degraded_fast_fail_enabled():
        if queue_error is not None:
            raise queue_error
        raise ValueError("IndexTTS degraded fast-fail mode reached fallback guard without queue error")

    if should_retry_queue:
        # Opaque queue failures are commonly transient. Retry one fresh queue session
        # before using direct predict as a compatibility fallback.
        retry_start = time.perf_counter()
        retry_session_hash = _indextts_queue_join(fn_index, data)
        timings["queue_retry_join_ms"] = max(0, int((time.perf_counter() - retry_start) * 1000))
        retry_start = time.perf_counter()
        try:
            result = _indextts_wait_for_result(retry_session_hash)
            timings["queue_retry_wait_ms"] = max(0, int((time.perf_counter() - retry_start) * 1000))
            timings["result_path"] = "queue-retry"
            return result
        except Exception as retry_exc:
            timings["queue_retry_wait_ms"] = max(0, int((time.perf_counter() - retry_start) * 1000))
            timings["queue_retry_error"] = str(retry_exc)
            if not _is_opaque_indextts_queue_failure(str(retry_exc)):
                raise
            queue_error = retry_exc

    api_name_fallback_start = time.perf_counter()
    try:
        api_name_result = _indextts_space_client().call_api_name(
            api_name,
            data,
            timeout_seconds=_indextts_timeout_seconds(),
            poll_interval_seconds=0.5,
        )
        timings["api_name_fallback_ms"] = max(0, int((time.perf_counter() - api_name_fallback_start) * 1000))
        timings["result_path"] = "api-name-fallback"
        return api_name_result if isinstance(api_name_result, Mapping) else {"data": api_name_result}
    except Exception as api_name_exc:
        timings["api_name_fallback_ms"] = max(0, int((time.perf_counter() - api_name_fallback_start) * 1000))
        timings["api_name_fallback_error"] = str(api_name_exc)

    direct_start = time.perf_counter()
    try:
        direct_result = _indextts_space_client().call_endpoint(fn_index, data)
        timings["direct_predict_ms"] = max(0, int((time.perf_counter() - direct_start) * 1000))
        timings["result_path"] = "direct-predict-fallback"
        return {"data": direct_result if isinstance(direct_result, list) else [direct_result]}
    except Exception as direct_predict_exc:
        timings["direct_predict_ms"] = max(0, int((time.perf_counter() - direct_start) * 1000))
        timings["direct_predict_error"] = str(direct_predict_exc)
        if queue_error is not None:
            raise queue_error
        raise


def _run_indextts_gradio_tts_for_space(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    total_start = time.perf_counter()
    timings: dict[str, Any] = {}
    raw_prompt = str(text or "").strip()
    if not raw_prompt:
        raise ValueError("text is required")
    prompt = _normalize_indextts_spoken_text(raw_prompt)
    stage_start = time.perf_counter()
    config = _indextts_config()
    timings["config_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    uploaded_reference = _indextts_upload_reference_audio(reference_audio, reference_audio_name, reference_audio_mime_type)
    timings["reference_upload_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    fn_index = _indextts_fn_index(config)
    timings["fn_index_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    data = _indextts_request_data(
        text=prompt,
        voice_description=voice_description,
        reference_audio=uploaded_reference,
    )
    result = _indextts_execute_with_queue_fallback(
        fn_index=fn_index,
        data=data,
        timings=timings,
        api_name=_indextts_api_name(),
    )
    audio_ref = _find_gradio_audio_reference(result)
    if not audio_ref:
        # Some Space revisions return batch-shaped outputs (including zip bundles)
        # even for single-item invocations. Reuse batch extraction and keep the
        # first generated audio to preserve the single-route contract.
        batch_refs = _indextts_batch_audio_references(result)
        if batch_refs:
            audio_ref = batch_refs[0]
    if not audio_ref:
        raise ValueError("IndexTTS completed without an audio file in the Gradio output")
    stage_start = time.perf_counter()
    audio_bytes, mime_type = _fetch_gradio_file(audio_ref)
    timings["file_fetch_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
    if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
        mime_type = "audio/wav"
    timings["total_ms"] = max(0, int((time.perf_counter() - total_start) * 1000))
    return {
        "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
        "mimeType": mime_type or "audio/wav",
        "model": _indextts_model_name(),
        "spaceUrl": _indextts_space_base_url(),
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus",
        "referenceAudio": str(uploaded_reference.get("orig_name") or uploaded_reference.get("path") or "")
        if isinstance(uploaded_reference, Mapping)
        else "",
        "text": prompt,
        "originalText": raw_prompt if raw_prompt != prompt else "",
        "latency": timings,
    }


def _run_indextts_gradio_batch_tts_for_space(
    *,
    texts: Sequence[str],
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    total_start = time.perf_counter()
    raw_prompts = [str(text or "").strip() for text in texts if str(text or "").strip()]
    if not raw_prompts:
        raise ValueError("texts is required")
    prompts = [_normalize_indextts_spoken_text(text) for text in raw_prompts]
    config = _indextts_config()
    uploaded_reference = _indextts_upload_reference_audio(reference_audio, reference_audio_name, reference_audio_mime_type)
    timings: dict[str, Any] = {}
    try:
        stage_start = time.perf_counter()
        fn_index = _indextts_batch_fn_index(config)
        timings["batch_fn_index_ms"] = max(0, int((time.perf_counter() - stage_start) * 1000))
        data = _indextts_batch_request_data(
            texts=prompts,
            voice_description=voice_description,
            reference_audio=uploaded_reference,
        )
        result = _indextts_execute_with_queue_fallback(
            fn_index=fn_index,
            data=data,
            timings=timings,
            api_name=_indextts_batch_api_name(),
        )
        audio_refs = _indextts_batch_audio_references(result)
        if len(audio_refs) < len(prompts):
            raise ValueError(f"IndexTTS batch returned {len(audio_refs)} audio files for {len(prompts)} texts")
        items: list[dict[str, Any]] = []
        fetch_start = time.perf_counter()
        for index, audio_ref in enumerate(audio_refs[: len(prompts)]):
            audio_bytes, mime_type = _fetch_gradio_file(audio_ref)
            if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
                mime_type = "audio/wav"
            items.append(
                {
                    "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
                    "mimeType": mime_type or "audio/wav",
                    "text": prompts[index],
                    "originalText": raw_prompts[index] if raw_prompts[index] != prompts[index] else "",
                }
            )
        timings["file_fetch_ms"] = max(0, int((time.perf_counter() - fetch_start) * 1000))
        mode = "batch"
    except Exception as exc:
        if _indextts_require_batch_mode():
            raise
        fallback_start = time.perf_counter()
        items = [
            _run_indextts_gradio_tts_for_space(
                text=raw_prompt,
                voice_description=voice_description,
                reference_audio=reference_audio,
                reference_audio_name=reference_audio_name,
                reference_audio_mime_type=reference_audio_mime_type,
            )
            for raw_prompt in raw_prompts
        ]
        timings["sequential_fallback_ms"] = max(0, int((time.perf_counter() - fallback_start) * 1000))
        mode = "sequential-fallback"
        timings["batch_error"] = str(exc)
    timings["total_ms"] = max(0, int((time.perf_counter() - total_start) * 1000))
    return {
        "items": items,
        "batchSize": len(items),
        "mode": mode,
        "model": _indextts_model_name(),
        "spaceUrl": _indextts_space_base_url(),
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus",
        "latency": timings,
    }
