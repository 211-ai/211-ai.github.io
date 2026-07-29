# ruff: noqa: E501
"""IndexTTS multi-space routing and top-level TTS entry-point helpers."""

from __future__ import annotations

import base64
import os
from collections.abc import Mapping, Sequence
from typing import Any

from .._vendor import ensure_ipfs_datasets_py_path
from ._tts_gradio import (  # noqa: F401
    _extract_hf_whisper_text,
    _gradio_file_key,
    _gradio_update_value,
)

ensure_ipfs_datasets_py_path()

from ._tts_client import (  # noqa: E402,F401
    _INDEXTTS_CACHE_LOCK,
    _INDEXTTS_CONFIG_CACHE,
    _INDEXTTS_FN_INDEX_CACHE,
    _INDEXTTS_REFERENCE_CACHE,
)
from ._tts_config import (  # noqa: E402,F401
    _INDEXTTS_ACTIVE_SPACE_URL,
    _INDEXTTS_ACTIVE_TIMEOUT_SECONDS,
    _INDEXTTS_FAST_FAIL_MODE,
    _INDEXTTS_FORCE_REQUIRE_BATCH,
    _clean_voice_reply_text,
    _hf_whisper_model_name,
    _hf_whisper_timeout_seconds,
    _indextts_api_name,
    _indextts_attempt_timeout_seconds,
    _indextts_batch_api_name,
    _indextts_batch_enabled,
    _indextts_cache_ttl_seconds,
    _indextts_degraded_error_payload,
    _indextts_endpoint_retry_count,
    _indextts_endpoint_timeout_seconds,
    _indextts_fallback_space_base_url,
    _indextts_fast_fail_mode,
    _indextts_force_require_batch,
    _indextts_model_name,
    _indextts_require_batch_mode,
    _indextts_single_batch_fallback_enabled,
    _indextts_space_base_url,
    _indextts_space_base_urls,
    _indextts_use_space_base_url,
    _indextts_use_timeout_seconds,
    _run_indextts_with_endpoint_retry,
    _run_indextts_with_endpoint_timeout,
    _silent_wav_bytes,
    _voice_llm_timeout_seconds,
)
from ._tts_http import (  # noqa: E402,F401
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
from ._tts_pipeline import (  # noqa: E402,F401
    _indextts_execute_with_queue_fallback,
    _run_indextts_gradio_batch_tts_for_space,
    _run_indextts_gradio_tts_for_space,
)


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


def _single_tts_response_from_batch(
    batch: Mapping[str, Any],
    *,
    text: str,
    result_path: str,
    prior_error: Exception | None = None,
) -> dict[str, Any]:
    """Convert a one-item ``gen_batch`` receipt to the wallet TTS envelope."""

    items = batch.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("IndexTTS batch returned no items")
    first_item = items[0] if isinstance(items[0], Mapping) else {}
    response: dict[str, Any] = {
        "audioBase64": str(first_item.get("audioBase64") or ""),
        "mimeType": str(first_item.get("mimeType") or "audio/wav"),
        "model": str(batch.get("model") or _indextts_model_name()),
        "spaceUrl": str(batch.get("spaceUrl") or _indextts_space_base_url()),
        "provider": str(batch.get("provider") or "huggingface-zero-gpu-gradio"),
        "billTo": str(
            batch.get("billTo")
            or os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
            or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
            or "publicus"
        ),
        "referenceAudio": "",
        "text": str(first_item.get("text") or text),
        "originalText": str(first_item.get("originalText") or ""),
        "latency": {
            "result_path": result_path,
            "batch_latency": dict(batch.get("latency") or {}),
        },
    }
    if prior_error is not None:
        response["latency"]["single_error"] = str(prior_error)
    if not response["audioBase64"]:
        raise ValueError("IndexTTS batch did not return audioBase64")
    return response


def _run_indextts_compatibility_tts_with_batch_fallback(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    if _indextts_batch_enabled():
        try:
            with _indextts_force_require_batch(True):
                batch = _run_indextts_gradio_batch_tts(
                    texts=[text],
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
            return _single_tts_response_from_batch(
                batch,
                text=text,
                result_path="publicus-batch-primary",
            )
        except Exception as batch_exc:
            if _indextts_require_batch_mode():
                raise
            try:
                return _run_indextts_gradio_tts(
                    text=text,
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_audio_name,
                    reference_audio_mime_type=reference_audio_mime_type,
                )
            except Exception as single_exc:
                raise ValueError(
                    f"IndexTTS batch primary failed and single fallback failed: "
                    f"batch={batch_exc}; single={single_exc}"
                ) from single_exc

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
        try:
            return _single_tts_response_from_batch(
                batch,
                text=text,
                result_path="single-batch-fallback",
                prior_error=single_exc,
            )
        except ValueError as response_exc:
            raise response_exc from single_exc


def _run_indextts_tts_with_batch_fallback(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> dict[str, Any]:
    """Use package-native Publicus synthesis, retaining the wallet fallback."""

    try:
        from ._voice_router_adapter import (  # noqa: WPS433
            _PackageFirstTTSProvider,
            _package_indextts_tts_provider,
        )

        package_provider = _package_indextts_tts_provider()
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        package_provider = None
    if package_provider is None:
        return _run_indextts_compatibility_tts_with_batch_fallback(
            text=text,
            voice_description=voice_description,
            reference_audio=reference_audio,
            reference_audio_name=reference_audio_name,
            reference_audio_mime_type=reference_audio_mime_type,
        )

    provider = _PackageFirstTTSProvider(package_provider)
    audio = provider.synthesize(
        text,
        voice=voice_description,
        reference_audio=reference_audio,
        reference_audio_name=reference_audio_name,
        reference_audio_mime_type=reference_audio_mime_type,
    )
    compatibility_result = provider.compatibility_provider.last_result
    if provider.last_backend == "wallet-gradio-compatibility" and compatibility_result:
        return dict(compatibility_result)

    receipt = provider.last_receipt
    receipt_to_dict = getattr(receipt, "to_dict", None)
    try:
        receipt_payload = receipt_to_dict() if callable(receipt_to_dict) else {}
    except Exception:
        receipt_payload = {}
    selected_endpoint = str(
        getattr(receipt, "selected_endpoint", "")
        or (
            package_provider.endpoints[0]
            if getattr(package_provider, "endpoints", ())
            else _indextts_space_base_url()
        )
    )
    spoken_text = provider.last_spoken_text or _normalize_indextts_spoken_text(text)
    return {
        "audioBase64": base64.b64encode(audio).decode("ascii"),
        "mimeType": "audio/wav",
        "model": str(
            getattr(package_provider, "default_model", "")
            or _indextts_model_name()
        ),
        "spaceUrl": selected_endpoint,
        "provider": "ipfs_accelerate_py-abby-indextts",
        "billTo": (
            os.getenv("IPFS_ACCELERATE_PY_ABBY_HF_BILL_TO")
            or os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
            or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
            or "publicus"
        ),
        "referenceAudio": "",
        "text": spoken_text,
        "originalText": text if text != spoken_text else "",
        "latency": {
            "result_path": provider.last_backend,
            "provider_receipt": receipt_payload,
        },
    }

