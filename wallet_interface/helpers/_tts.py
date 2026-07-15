# ruff: noqa: E501
"""IndexTTS / Gradio / Whisper / voice-reply / speech-normalisation helpers."""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import re
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .._vendor import ensure_ipfs_datasets_py_path
from ._tts_gradio import (  # noqa: E402
    _dedupe_gradio_references,
    _extract_audio_files_from_zip,
    _extract_hf_whisper_text,
    _find_gradio_audio_reference,
    _find_gradio_audio_references,
    _find_gradio_file_reference,
    _first_upload_path,
    _gradio_file_key,
    _gradio_output_values,
    _gradio_update_value,
    _indextts_batch_request_data,
    _indextts_request_data,
    _default_indextts_reference_wav,
    _normalize_indextts_queue_failure,
)

ensure_ipfs_datasets_py_path()


from ipfs_accelerate_py import HFSpaceClient  # noqa: E402

from ._tts_config import (  # noqa: E402
    _INDEXTTS_ACTIVE_SPACE_URL,
    _INDEXTTS_ACTIVE_TIMEOUT_SECONDS,
    _INDEXTTS_FAST_FAIL_MODE,
    _INDEXTTS_FORCE_REQUIRE_BATCH,
    _clean_voice_reply_text,
    _hf_whisper_model_name,
    _hf_whisper_timeout_seconds,
    _indextts_allow_direct_predict_fallback,
    _indextts_api_name,
    _indextts_attempt_timeout_seconds,
    _indextts_batch_api_name,
    _indextts_cache_ttl_seconds,
    _indextts_degraded_fast_fail_enabled,
    _indextts_endpoint_retry_count,
    _indextts_endpoint_timeout_seconds,
    _indextts_fallback_space_base_url,
    _indextts_fast_fail_mode,
    _indextts_force_require_batch,
    _indextts_is_fast_fail_mode,
    _indextts_model_name,
    _indextts_require_batch_mode,
    _indextts_single_batch_fallback_enabled,
    _indextts_space_base_url,
    _indextts_space_base_urls,
    _indextts_timeout_seconds,
    _indextts_use_space_base_url,
    _indextts_use_timeout_seconds,
    _is_opaque_indextts_queue_failure,
    _silent_wav_bytes,
    _indextts_degraded_error_payload,
    _run_indextts_with_endpoint_retry,
    _run_indextts_with_endpoint_timeout,
    _voice_llm_timeout_seconds,
)

from ._tts_http import (  # noqa: E402
    _configured_hf_token,
    _generate_indextts_voice_reply_text,
    _gradio_upload_file,
    _http_bytes,
    _http_json,
    _indextts_headers,
    _publicus_indextts_credential_warning,
    _run_hf_whisper_stt,
    _voice_proxy_runtime_warnings,
)

# Text-normalization constants and pure functions live in the stdlib-only submodule
from ._tts_normalization import (  # noqa: E402,F401
    _ADDRESS_DIRECTION_WORDS,
    _OMITTED_VOICE_FIELDS,
    _STATE_WORDS,
    _STREET_SUFFIX_WORDS,
    _UNIT_WORDS,
    _digits_to_words,
    _domain_to_spoken_site,
    _normalize_address_directions_and_highways,
    _normalize_address_prosody,
    _normalize_direction_token,
    _normalize_hours_and_separators,
    _normalize_indextts_spoken_text,
    _normalize_percentages_and_currency,
    _normalize_phone_extensions,
    _normalize_phone_list_prosody,
    _normalize_phone_numbers,
    _normalize_record_list_sentence,
    _normalize_sentence_prosody,
    _normalize_suffix_token,
    _normalize_urls_for_speech,
    _normalize_zip_codes,
    _number_to_words,
    _ordinal_to_words,
    _prefer_primary_voice_contact,
    _shorten_long_eligibility_for_voice,
    _strip_coordinates,
    _strip_scraped_page_chrome,
    _strip_unspoken_fields,
    _title_case_program_name,
)


from ._tts_client import (  # noqa: E402
    _INDEXTTS_CACHE_LOCK,
    _INDEXTTS_CONFIG_CACHE,
    _INDEXTTS_FN_INDEX_CACHE,
    _INDEXTTS_REFERENCE_CACHE,
    _INDEXTTS_SPACE_CLIENT,
    _INDEXTTS_SPACE_CLIENT_KEY,
    _indextts_batch_fn_index,
    _indextts_config,
    _indextts_fn_index,
    _indextts_queue_join,
    _indextts_space_client,
)
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



def _run_indextts_gradio_tts(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None
    errors_by_space: dict[str, str] = {}
    space_urls = _indextts_space_base_urls()
    for index, space_url in enumerate(space_urls):
        with _indextts_use_space_base_url(space_url), _indextts_use_timeout_seconds(
            _indextts_attempt_timeout_seconds(index, len(space_urls))
        ), _indextts_fast_fail_mode(index < (len(space_urls) - 1)):
            try:
                return _run_indextts_gradio_tts_for_space(
                    text=text,
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
            except Exception as exc:
                last_error = exc
                errors_by_space[space_url] = str(exc)
                continue
    detail = "; ".join(f"{url}: {message}" for url, message in errors_by_space.items())
    if last_error is not None:
        raise ValueError(f"IndexTTS failed across configured spaces ({detail})") from last_error
    raise ValueError("IndexTTS failed: no configured spaces available")


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


def _run_indextts_gradio_batch_tts(
    *,
    texts: Sequence[str],
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None
    errors_by_space: dict[str, str] = {}
    space_urls = _indextts_space_base_urls()
    for index, space_url in enumerate(space_urls):
        with _indextts_use_space_base_url(space_url), _indextts_use_timeout_seconds(
            _indextts_attempt_timeout_seconds(index, len(space_urls))
        ), _indextts_fast_fail_mode(index < (len(space_urls) - 1)):
            try:
                return _run_indextts_gradio_batch_tts_for_space(
                    texts=texts,
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
            except Exception as exc:
                last_error = exc
                errors_by_space[space_url] = str(exc)
                continue
    detail = "; ".join(f"{url}: {message}" for url, message in errors_by_space.items())
    if last_error is not None:
        raise ValueError(f"IndexTTS batch failed across configured spaces ({detail})") from last_error
    raise ValueError("IndexTTS batch failed: no configured spaces available")


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



def _run_indextts_tts_with_batch_fallback(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    try:
        return _run_indextts_gradio_tts(
            text=text,
            voice_description=voice_description,
            reference_audio=reference_audio,
            reference_audio_name=reference_audio_name,
            reference_audio_mime_type=reference_audio_mime_type,
        )
    except Exception as single_exc:
        if not _indextts_single_batch_fallback_enabled():
            raise
        try:
            with _indextts_force_require_batch(True):
                batch = _run_indextts_gradio_batch_tts(
                    texts=[text],
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
        except Exception as batch_exc:
            raise ValueError(
                f"IndexTTS single failed and batch fallback failed: single={single_exc}; batch={batch_exc}"
            ) from batch_exc
        items = batch.get("items") if isinstance(batch, Mapping) else None
        if not isinstance(items, list) or not items:
            raise ValueError("IndexTTS batch fallback returned no items") from single_exc
        first_item = items[0] if isinstance(items[0], Mapping) else {}
        response: dict[str, Any] = {
            "audioBase64": str(first_item.get("audioBase64") or ""),
            "mimeType": str(first_item.get("mimeType") or "audio/wav"),
            "model": str(batch.get("model") or _indextts_model_name()) if isinstance(batch, Mapping) else _indextts_model_name(),
            "spaceUrl": str(batch.get("spaceUrl") or _indextts_space_base_url()) if isinstance(batch, Mapping) else _indextts_space_base_url(),
            "provider": str(batch.get("provider") or "huggingface-zero-gpu-gradio") if isinstance(batch, Mapping) else "huggingface-zero-gpu-gradio",
            "billTo": str(batch.get("billTo") or os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus")
            if isinstance(batch, Mapping)
            else (os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus"),
            "referenceAudio": "",
            "text": str(first_item.get("text") or text),
            "originalText": str(first_item.get("originalText") or ""),
            "latency": {
                "result_path": "single-batch-fallback",
                "single_error": str(single_exc),
                "batch_latency": dict(batch.get("latency") or {}) if isinstance(batch, Mapping) else {},
            },
        }
        if not response["audioBase64"]:
            raise ValueError("IndexTTS batch fallback did not return audioBase64") from single_exc
        return response


def _indextts_upload_reference_audio(
    audio: bytes | None,
    file_name: str | None,
    mime_type: str | None = None,
) -> dict[str, Any] | None:
    if audio:
        guessed_type = mime_type or mimetypes.guess_type(file_name or "")[0] or "audio/wav"
        parsed = _indextts_space_client().upload_file(file_name or "reference.wav", audio, guessed_type)
        upload_path = _first_upload_path(parsed)
        if not upload_path:
            raise RuntimeError("IndexTTS upload did not return a reference path")
        return {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(file_name or "reference.wav")}
    path = os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_PATH", "").strip()
    if path and os.path.exists(path):
        stat = os.stat(path)
        cache_key = (os.path.abspath(path), f"{stat.st_mtime_ns}:{stat.st_size}")
        with _INDEXTTS_CACHE_LOCK:
            cached = _INDEXTTS_REFERENCE_CACHE.get(cache_key)
            if cached:
                return dict(cached)
        with open(path, "rb") as handle:
            data = handle.read()
        mime_type = mimetypes.guess_type(path)[0] or "audio/wav"
        parsed = _indextts_space_client().upload_file(os.path.basename(path), data, mime_type)
        upload_path = _first_upload_path(parsed)
        if not upload_path:
            raise RuntimeError("IndexTTS upload did not return a reference path")
        uploaded = {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(path)}
        with _INDEXTTS_CACHE_LOCK:
            _INDEXTTS_REFERENCE_CACHE[cache_key] = dict(uploaded)
        return uploaded
    remote_path = os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH", "").strip()
    if remote_path:
        return {"path": remote_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(remote_path) or "reference.wav"}
    cache_key = ("default-abby-reference", "v1")
    with _INDEXTTS_CACHE_LOCK:
        cached = _INDEXTTS_REFERENCE_CACHE.get(cache_key)
        if cached:
            return dict(cached)
    parsed = _indextts_space_client().upload_file("abby-reference.wav", _default_indextts_reference_wav(), "audio/wav")
    upload_path = _first_upload_path(parsed)
    if not upload_path:
        raise RuntimeError("IndexTTS upload did not return a reference path")
    uploaded = {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": "abby-reference.wav"}
    with _INDEXTTS_CACHE_LOCK:
        _INDEXTTS_REFERENCE_CACHE[cache_key] = dict(uploaded)
    return uploaded




def _indextts_wait_for_result(session_hash: str) -> dict[str, Any]:
    try:
        return _indextts_space_client().wait_for_queue_result(
            session_hash,
            timeout_seconds=_indextts_timeout_seconds(),
            poll_interval_seconds=0.5,
        )
    except Exception as exc:
        detail = _normalize_indextts_queue_failure(exc)
        raise ValueError(f"IndexTTS Gradio queue failed: {detail}") from exc


def _indextts_batch_audio_references(result: Mapping[str, Any]) -> list[Any]:
    outputs = _gradio_output_values(result)
    if len(outputs) >= 2:
        generated_files = _find_gradio_audio_references(outputs[1])
        if generated_files:
            return _dedupe_gradio_references(generated_files)
    if len(outputs) >= 3:
        zip_ref = _find_gradio_file_reference(outputs[2], suffixes=(".zip",))
        if zip_ref:
            try:
                archive, _mime_type = _fetch_gradio_file(zip_ref)
                extracted = _extract_audio_files_from_zip(archive)
                if extracted:
                    return extracted
            except Exception:
                pass
    return _dedupe_gradio_references(_find_gradio_audio_references(result))


def _fetch_gradio_file(reference: Any) -> tuple[bytes, str]:
    if isinstance(reference, Mapping) and isinstance(reference.get("_inline_bytes"), (bytes, bytearray)):
        name = str(reference.get("name") or reference.get("path") or "")
        return bytes(reference["_inline_bytes"]), mimetypes.guess_type(name)[0] or "audio/wav"
    data, detected_type = _indextts_space_client().fetch_file(reference)
    path = str(reference.get("path") or reference.get("name") or "") if isinstance(reference, Mapping) else str(reference or "")
    mime_type = str(reference.get("mime_type") or reference.get("mimeType") or "") if isinstance(reference, Mapping) else ""
    return data, mime_type or detected_type or mimetypes.guess_type(path)[0] or "audio/wav"


