# ruff: noqa: E501
"""Pure Gradio response-parsing and audio-utility helpers for IndexTTS.

All functions in this module are stdlib-only (json, io, zipfile) — they carry
no optional-dependency imports and can be unit-tested without installing
ipfs_datasets_py, ipfs_accelerate_py, or Playwright.
"""

from __future__ import annotations

import io
import json
import math
import os
import struct
import wave
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any

# ---------------------------------------------------------------------------
# Request-payload builders
# ---------------------------------------------------------------------------

def _indextts_request_data(
    *,
    text: str,
    voice_description: str | None,
    reference_audio: Mapping[str, Any] | None,
) -> list[Any]:
    raw_template = os.getenv("WALLET_INDEXTTS_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{text}", text)
            .replace("{voice_description}", voice_description or "")
            .replace("{reference_audio}", json.dumps(reference_audio) if reference_audio else "null")
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise ValueError("WALLET_INDEXTTS_DATA_TEMPLATE must render to a JSON array")
        return parsed
    # IndexTeam/IndexTTS-2-Demo /gen_single Gradio input order.
    return [
        "Same as the voice reference",
        reference_audio,
        text,
        None,
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        voice_description or "",
        False,
        120,
        True,
        0.8,
        30,
        0.8,
        0.0,
        3,
        10.0,
        1500,
    ]


def _indextts_batch_request_data(
    *,
    texts: Sequence[str],
    voice_description: str | None,
    reference_audio: Mapping[str, Any] | None,
) -> list[Any]:
    text_list = [str(text) for text in texts]
    raw_template = os.getenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{texts}", json.dumps(text_list))
            .replace("{text}", json.dumps(json.dumps(text_list)))
            .replace("{voice_description}", json.dumps(voice_description or ""))
            .replace("{reference_audio}", json.dumps(reference_audio) if reference_audio else "null")
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise ValueError("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE must render to a JSON array")
        return parsed
    # Publicus/IndexTTS-2-Demo /gen_batch uses a Gradio Textbox, but the
    # backend batch parser expects a JSON-encoded list string in that textbox.
    return [
        "Same as the voice reference",
        reference_audio,
        json.dumps(text_list),
        None,
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        voice_description or "",
        False,
        120,
        len(text_list) if len(text_list) > 1 else 0,
        True,
        0.8,
        30,
        0.8,
        0.0,
        3,
        10.0,
        1500,
    ]


# ---------------------------------------------------------------------------
# Gradio upload response parsing
# ---------------------------------------------------------------------------

def _first_upload_path(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            found = _first_upload_path(item)
            if found:
                return found
    if isinstance(value, Mapping):
        for key in ("path", "name"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        for item in value.values():
            found = _first_upload_path(item)
            if found:
                return found
    return ""


# ---------------------------------------------------------------------------
# Queue / error normalization
# ---------------------------------------------------------------------------

def _normalize_indextts_queue_failure(error: Exception) -> str:
    detail = str(error or "").strip() or type(error).__name__
    normalized = detail.replace('"', "'").lower()
    if "space queue failed" in normalized and "{'error': none}" in normalized:
        return (
            "Space queue failed without diagnostic details (error=null). "
            "The Hugging Face Space may be overloaded or dropped the job; retry shortly."
        )
    return detail


# ---------------------------------------------------------------------------
# Gradio audio-reference finders
# ---------------------------------------------------------------------------

def _find_gradio_audio_reference(value: Any) -> Any:
    if isinstance(value, Mapping):
        if str(value.get("mime_type") or value.get("mimeType") or "").startswith("audio/"):
            return value
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "")
            if pathish and (pathish.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in pathish or "/gradio_api/file=" in pathish):
                return value
        for item in value.values():
            found = _find_gradio_audio_reference(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_gradio_audio_reference(item)
            if found:
                return found
    if isinstance(value, str) and (value.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in value or "/gradio_api/file=" in value):
        return value
    return None


def _find_gradio_audio_references(value: Any) -> list[Any]:
    found: list[Any] = []
    seen: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            direct = _find_gradio_audio_reference(item)
            if direct is item:
                key = json.dumps(item, sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    found.append(item)
                return
            for child in item.values():
                visit(child)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if isinstance(item, str):
            direct = _find_gradio_audio_reference(item)
            if direct:
                key = str(direct)
                if key not in seen:
                    seen.add(key)
                    found.append(direct)

    visit(value)
    return found


# ---------------------------------------------------------------------------
# Gradio output-value helpers
# ---------------------------------------------------------------------------

def _gradio_update_value(value: Any) -> Any:
    if isinstance(value, Mapping) and value.get("__type__") == "update":
        return value.get("value")
    return value


def _gradio_output_values(result: Mapping[str, Any]) -> list[Any]:
    data = result.get("data")
    if isinstance(data, list):
        return [_gradio_update_value(item) for item in data]
    return []


def _gradio_file_key(reference: Any) -> str:
    if isinstance(reference, Mapping):
        return str(reference.get("url") or reference.get("path") or reference.get("name") or json.dumps(reference, sort_keys=True, default=str))
    return str(reference)


def _dedupe_gradio_references(references: Sequence[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for reference in references:
        key = _gradio_file_key(reference)
        if key and key not in seen:
            seen.add(key)
            deduped.append(reference)
    return deduped


def _find_gradio_file_reference(value: Any, *, suffixes: Sequence[str]) -> Any:
    suffix_tuple = tuple(suffix.lower() for suffix in suffixes)
    if isinstance(value, Mapping):
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "").lower()
            if pathish.endswith(suffix_tuple) or any("/file=" in pathish and suffix in pathish for suffix in suffix_tuple):
                return value
        for item in value.values():
            found = _find_gradio_file_reference(item, suffixes=suffix_tuple)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_gradio_file_reference(item, suffixes=suffix_tuple)
            if found:
                return found
    if isinstance(value, str) and value.lower().endswith(suffix_tuple):
        return value
    return None


# ---------------------------------------------------------------------------
# ZIP audio extraction
# ---------------------------------------------------------------------------

def _extract_audio_files_from_zip(data: bytes) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in sorted(archive.namelist()):
            if name.endswith("/") or not name.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
                continue
            extracted.append({"name": name, "_inline_bytes": archive.read(name)})
    return extracted


# ---------------------------------------------------------------------------
# Whisper STT response parsing (pure function, stdlib only)
# ---------------------------------------------------------------------------

def _extract_hf_whisper_text(payload: Any) -> str:
    if isinstance(payload, Mapping):
        for key in ("text", "transcription", "transcript", "generated_text", "output_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("items", "results", "segments", "chunks", "output", "data"):
            nested = payload.get(key)
            extracted = _extract_hf_whisper_text(nested)
            if extracted:
                return extracted
        return ""
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        pieces: list[str] = []
        for item in payload:
            extracted = _extract_hf_whisper_text(item)
            if extracted:
                pieces.append(extracted)
        if pieces:
            return " ".join(pieces).strip()
        return ""
    if isinstance(payload, str):
        return payload.strip()
    return ""


# ---------------------------------------------------------------------------
# Reference audio generation
# ---------------------------------------------------------------------------


def _default_indextts_reference_wav() -> bytes:
    """Generate a 1.5-second 220 Hz sine wave WAV at 24 kHz as default reference audio."""
    sample_rate = 24_000
    duration_seconds = 1.5
    frames = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            envelope = min(1.0, index / 2_400, (frames - index) / 2_400)
            value = int(10_000 * envelope * math.sin(2.0 * math.pi * 220.0 * index / sample_rate))
            wav.writeframesraw(struct.pack("<h", value))
    return buffer.getvalue()
