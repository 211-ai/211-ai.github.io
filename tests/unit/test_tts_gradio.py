"""Unit tests for wallet_interface/helpers/_tts_gradio.py.

All functions tested here are stdlib-only — no skips, no optional deps.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from wallet_interface.helpers._tts_gradio import (
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
    _normalize_indextts_queue_failure,
)

# ---------------------------------------------------------------------------
# _first_upload_path
# ---------------------------------------------------------------------------

class TestFirstUploadPath:
    def test_string_returned_as_is(self):
        assert _first_upload_path("/gradio_api/file=/tmp/foo.wav") == "/gradio_api/file=/tmp/foo.wav"

    def test_list_first_match(self):
        assert _first_upload_path(["/tmp/a.wav", "/tmp/b.wav"]) == "/tmp/a.wav"

    def test_dict_path_key(self):
        assert _first_upload_path({"path": "/tmp/foo.wav"}) == "/tmp/foo.wav"

    def test_dict_name_key_fallback(self):
        assert _first_upload_path({"name": "/tmp/bar.wav"}) == "/tmp/bar.wav"

    def test_nested_list_in_dict(self):
        assert _first_upload_path({"files": ["/tmp/deep.wav"]}) == "/tmp/deep.wav"

    def test_empty_input(self):
        assert _first_upload_path("") == ""

    def test_none_like(self):
        assert _first_upload_path(None) == ""  # type: ignore[arg-type]

    def test_list_skips_empty_items(self):
        assert _first_upload_path(["", {}, "/tmp/ok.wav"]) == "/tmp/ok.wav"


# ---------------------------------------------------------------------------
# _indextts_request_data
# ---------------------------------------------------------------------------

class TestIndexttsRequestData:
    def test_returns_list(self):
        result = _indextts_request_data(text="hello", voice_description=None, reference_audio=None)
        assert isinstance(result, list)

    def test_length_is_24(self):
        result = _indextts_request_data(text="hello", voice_description=None, reference_audio=None)
        assert len(result) == 24

    def test_text_at_index_2(self):
        result = _indextts_request_data(text="hello world", voice_description=None, reference_audio=None)
        assert result[2] == "hello world"

    def test_reference_audio_at_index_1(self):
        ref = {"path": "/tmp/ref.wav"}
        result = _indextts_request_data(text="hi", voice_description="female", reference_audio=ref)
        assert result[1] == ref

    def test_voice_description_in_result(self):
        result = _indextts_request_data(text="hi", voice_description="deep male", reference_audio=None)
        assert "deep male" in result

    def test_empty_voice_description(self):
        result = _indextts_request_data(text="hi", voice_description=None, reference_audio=None)
        # voice_description or "" → empty string should appear in list
        assert "" in result


# ---------------------------------------------------------------------------
# _indextts_batch_request_data
# ---------------------------------------------------------------------------

class TestIndeXttsBatchRequestData:
    def test_returns_list(self):
        result = _indextts_batch_request_data(texts=["a", "b"], voice_description=None, reference_audio=None)
        assert isinstance(result, list)

    def test_length_is_25(self):
        # Batch has one extra slot (len(text_list)) compared to single (24 elements)
        result = _indextts_batch_request_data(texts=["a", "b", "c"], voice_description=None, reference_audio=None)
        assert len(result) == 25

    def test_single_text_batch_count_zero(self):
        result = _indextts_batch_request_data(texts=["only"], voice_description=None, reference_audio=None)
        # len(text_list) if len > 1 else 0 → 0 for single item
        import json
        assert result[16] == 0

    def test_multi_text_batch_count(self):
        result = _indextts_batch_request_data(texts=["a", "b", "c"], voice_description=None, reference_audio=None)
        assert result[16] == 3

    def test_texts_json_encoded_at_index_2(self):
        import json
        result = _indextts_batch_request_data(texts=["hello", "world"], voice_description=None, reference_audio=None)
        # index 2 is JSON-encoded text list
        parsed = json.loads(result[2])
        assert parsed == ["hello", "world"]


# ---------------------------------------------------------------------------
# _normalize_indextts_queue_failure
# ---------------------------------------------------------------------------

class TestNormalizeIndexttsQueueFailure:
    def test_plain_error_passthrough(self):
        exc = ValueError("connection refused")
        assert _normalize_indextts_queue_failure(exc) == "connection refused"

    def test_empty_error_uses_class_name(self):
        exc = ValueError("")
        result = _normalize_indextts_queue_failure(exc)
        assert result == "ValueError"

    def test_opaque_null_error_normalized(self):
        exc = ValueError("Space queue failed: {'error': None}")
        result = _normalize_indextts_queue_failure(exc)
        assert "retry shortly" in result
        assert "error=null" in result.lower() or "overloaded" in result


# ---------------------------------------------------------------------------
# _find_gradio_audio_reference
# ---------------------------------------------------------------------------

class TestFindGradioAudioReference:
    def test_dict_with_wav_path(self):
        ref = {"path": "/tmp/output.wav"}
        assert _find_gradio_audio_reference(ref) == ref

    def test_dict_with_mp3_url(self):
        ref = {"url": "https://example.com/audio.mp3"}
        assert _find_gradio_audio_reference(ref) == ref

    def test_dict_with_audio_mime_type(self):
        ref = {"mime_type": "audio/wav", "url": "..."}
        assert _find_gradio_audio_reference(ref) == ref

    def test_plain_wav_string(self):
        assert _find_gradio_audio_reference("/tmp/test.wav") == "/tmp/test.wav"

    def test_file_eq_path(self):
        assert _find_gradio_audio_reference("/gradio_api/file=/tmp/out.wav") == "/gradio_api/file=/tmp/out.wav"

    def test_nested_in_list(self):
        ref = {"path": "/tmp/deep.wav"}
        assert _find_gradio_audio_reference([{"other": "value"}, ref]) == ref

    def test_nested_in_dict(self):
        ref = {"path": "/tmp/inner.wav"}
        assert _find_gradio_audio_reference({"container": ref}) == ref

    def test_returns_none_for_non_audio(self):
        assert _find_gradio_audio_reference({"path": "/tmp/doc.pdf"}) is None

    def test_stream_excluded_from_direct_match(self):
        # is_stream=True prevents the dict itself from being returned as a reference,
        # but the path string within it is still found via recursive descent.
        ref = {"path": "/tmp/stream.wav", "is_stream": True}
        result = _find_gradio_audio_reference(ref)
        # The dict is skipped but the path string "/tmp/stream.wav" is found via recursion
        assert result == "/tmp/stream.wav"

    def test_returns_none_for_empty(self):
        assert _find_gradio_audio_reference({}) is None


# ---------------------------------------------------------------------------
# _find_gradio_audio_references
# ---------------------------------------------------------------------------

class TestFindGradioAudioReferences:
    def test_finds_multiple(self):
        refs = [{"path": "/tmp/a.wav"}, {"path": "/tmp/b.wav"}]
        result = _find_gradio_audio_references(refs)
        assert len(result) == 2

    def test_deduplicates(self):
        ref = {"path": "/tmp/a.wav"}
        result = _find_gradio_audio_references([ref, ref])
        assert len(result) == 1

    def test_nested_discovery(self):
        data = {"outputs": [{"audio": {"path": "/tmp/out.wav"}}]}
        result = _find_gradio_audio_references(data)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _gradio_update_value
# ---------------------------------------------------------------------------

class TestGradioUpdateValue:
    def test_extracts_value_from_update(self):
        assert _gradio_update_value({"__type__": "update", "value": "hello"}) == "hello"

    def test_passthrough_non_update(self):
        assert _gradio_update_value("plain") == "plain"

    def test_passthrough_dict_without_type(self):
        d = {"key": "val"}
        assert _gradio_update_value(d) == d


# ---------------------------------------------------------------------------
# _gradio_output_values
# ---------------------------------------------------------------------------

class TestGradioOutputValues:
    def test_extracts_data_list(self):
        result = {"data": ["a", "b", "c"]}
        assert _gradio_output_values(result) == ["a", "b", "c"]

    def test_empty_when_no_data(self):
        assert _gradio_output_values({}) == []

    def test_update_values_unwrapped(self):
        result = {"data": [{"__type__": "update", "value": "hi"}, "plain"]}
        assert _gradio_output_values(result) == ["hi", "plain"]


# ---------------------------------------------------------------------------
# _gradio_file_key
# ---------------------------------------------------------------------------

class TestGradioFileKey:
    def test_string_ref(self):
        assert _gradio_file_key("/tmp/foo.wav") == "/tmp/foo.wav"

    def test_dict_url_preferred(self):
        ref = {"url": "http://example.com/foo.wav", "path": "/tmp/foo.wav"}
        assert _gradio_file_key(ref) == "http://example.com/foo.wav"

    def test_dict_path_fallback(self):
        ref = {"path": "/tmp/bar.wav"}
        assert _gradio_file_key(ref) == "/tmp/bar.wav"

    def test_dict_name_fallback(self):
        ref = {"name": "audio.wav"}
        assert _gradio_file_key(ref) == "audio.wav"


# ---------------------------------------------------------------------------
# _dedupe_gradio_references
# ---------------------------------------------------------------------------

class TestDedupeGradioReferences:
    def test_removes_duplicate_dicts(self):
        ref = {"url": "http://example.com/a.wav"}
        result = _dedupe_gradio_references([ref, ref, ref])
        assert len(result) == 1

    def test_keeps_unique_entries(self):
        refs = [{"url": "http://example.com/a.wav"}, {"url": "http://example.com/b.wav"}]
        result = _dedupe_gradio_references(refs)
        assert len(result) == 2

    def test_empty_list(self):
        assert _dedupe_gradio_references([]) == []


# ---------------------------------------------------------------------------
# _find_gradio_file_reference
# ---------------------------------------------------------------------------

class TestFindGradioFileReference:
    def test_finds_zip_in_dict(self):
        ref = {"path": "/tmp/batch.zip"}
        assert _find_gradio_file_reference(ref, suffixes=[".zip"]) == ref

    def test_finds_wav_string(self):
        assert _find_gradio_file_reference("/tmp/foo.wav", suffixes=[".wav"]) == "/tmp/foo.wav"

    def test_nested_in_list(self):
        ref = {"path": "/tmp/result.zip"}
        assert _find_gradio_file_reference([None, ref], suffixes=[".zip"]) == ref

    def test_returns_none_for_wrong_suffix(self):
        ref = {"path": "/tmp/foo.mp3"}
        assert _find_gradio_file_reference(ref, suffixes=[".wav"]) is None

    def test_stream_excluded_from_dict_match(self):
        # is_stream=True prevents the dict from matching, but path value still found via recursion
        ref = {"path": "/tmp/foo.zip", "is_stream": True}
        # The dict itself is excluded, but the string "/tmp/foo.zip" is found recursively
        assert _find_gradio_file_reference(ref, suffixes=[".zip"]) == "/tmp/foo.zip"


# ---------------------------------------------------------------------------
# _extract_audio_files_from_zip
# ---------------------------------------------------------------------------

def _make_zip_bytes(entries: dict[str, bytes]) -> bytes:
    """Build an in-memory ZIP archive from a name→bytes dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


class TestExtractAudioFilesFromZip:
    def test_extracts_wav_files(self):
        data = _make_zip_bytes({"audio/a.wav": b"RIFF", "audio/b.wav": b"RIFF"})
        result = _extract_audio_files_from_zip(data)
        assert len(result) == 2
        names = [r["name"] for r in result]
        assert "audio/a.wav" in names

    def test_skips_non_audio_files(self):
        data = _make_zip_bytes({"out.wav": b"RIFF", "meta.json": b"{}"})
        result = _extract_audio_files_from_zip(data)
        assert len(result) == 1
        assert result[0]["name"] == "out.wav"

    def test_includes_mp3_and_flac(self):
        data = _make_zip_bytes({"track.mp3": b"\xff\xfb", "track.flac": b"fLaC"})
        result = _extract_audio_files_from_zip(data)
        assert len(result) == 2

    def test_inline_bytes_present(self):
        data = _make_zip_bytes({"test.wav": b"RIFF1234"})
        result = _extract_audio_files_from_zip(data)
        assert result[0]["_inline_bytes"] == b"RIFF1234"

    def test_sorted_order(self):
        data = _make_zip_bytes({"b.wav": b"B", "a.wav": b"A"})
        result = _extract_audio_files_from_zip(data)
        assert result[0]["name"] == "a.wav"
        assert result[1]["name"] == "b.wav"

    def test_empty_zip(self):
        data = _make_zip_bytes({})
        assert _extract_audio_files_from_zip(data) == []


# ---------------------------------------------------------------------------
# _extract_hf_whisper_text
# ---------------------------------------------------------------------------

class TestExtractHfWhisperText:
    def test_top_level_text_key(self):
        assert _extract_hf_whisper_text({"text": "hello world"}) == "hello world"

    def test_transcription_key(self):
        assert _extract_hf_whisper_text({"transcription": "test"}) == "test"

    def test_nested_chunks(self):
        payload = {"chunks": [{"text": "hello"}, {"text": "world"}]}
        assert _extract_hf_whisper_text(payload) == "hello world"

    def test_nested_segments(self):
        payload = {"segments": [{"text": "  hi  "}]}
        assert _extract_hf_whisper_text(payload) == "hi"

    def test_plain_string_returned(self):
        assert _extract_hf_whisper_text("direct text") == "direct text"

    def test_list_of_strings(self):
        assert _extract_hf_whisper_text(["hello", "world"]) == "hello world"

    def test_empty_dict_returns_empty(self):
        assert _extract_hf_whisper_text({}) == ""

    def test_none_returns_empty(self):
        assert _extract_hf_whisper_text(None) == ""  # type: ignore[arg-type]
from wallet_interface.helpers._tts_gradio import _default_indextts_reference_wav


# ---------------------------------------------------------------------------
# _default_indextts_reference_wav
# ---------------------------------------------------------------------------


class TestDefaultIndexttsReferenceWav:
    def test_returns_bytes(self):
        result = _default_indextts_reference_wav()
        assert isinstance(result, bytes)

    def test_starts_with_riff_header(self):
        result = _default_indextts_reference_wav()
        assert result[:4] == b"RIFF"

    def test_is_wave_format(self):
        import io
        import wave
        result = _default_indextts_reference_wav()
        with wave.open(io.BytesIO(result), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 24_000

    def test_duration_is_approximately_1_5_seconds(self):
        import io, wave
        result = _default_indextts_reference_wav()
        with wave.open(io.BytesIO(result), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / rate
        assert abs(duration - 1.5) < 0.01

    def test_non_empty_audio_content(self):
        result = _default_indextts_reference_wav()
        # Should have non-silent audio (not all zeros)
        audio_bytes = result[44:]  # skip WAV header
        assert any(b != 0 for b in audio_bytes)

    def test_consistent_output(self):
        # Should produce identical bytes on repeated calls
        result1 = _default_indextts_reference_wav()
        result2 = _default_indextts_reference_wav()
        assert result1 == result2

    def test_minimum_size(self):
        result = _default_indextts_reference_wav()
        # 1.5s * 24000 Hz * 2 bytes + 44-byte header
        expected_min = 1 * 24000 * 2  # at least 1 second worth
        assert len(result) >= expected_min
