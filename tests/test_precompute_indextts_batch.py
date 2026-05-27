from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping

from scripts import precompute_indextts_responses as precompute


def test_indextts_batch_fn_index_discovers_configured_api(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_API_NAME", "gen_batch")

    assert precompute.indextts_batch_fn_index({"dependencies": [{"id": 6, "api_name": "/gen_single"}, {"id": 9, "api_name": "/gen_batch"}]}) == 9


def test_batch_request_data_supports_template(monkeypatch) -> None:
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}
    monkeypatch.setenv(
        "WALLET_INDEXTTS_BATCH_DATA_TEMPLATE",
        '[{reference_audio}, {texts}, {voice_description}]',
    )

    assert precompute.batch_request_data(["one", "two"], reference, "Same voice") == [reference, ["one", "two"], "Same voice"]


def test_batch_request_data_default_matches_indextts_gradio_schema(monkeypatch) -> None:
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", raising=False)
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.batch_request_data(["one", "two"], reference, "Same voice")

    assert len(data) == 25
    assert data[0] == "Same as the voice reference"
    assert data[1] == reference
    assert data[2] == '["one", "two"]'
    assert data[13] == "Same voice"
    assert data[16] == 2


def test_synthesize_batch_falls_back_to_single_when_batch_missing(monkeypatch) -> None:
    calls: list[str] = []

    def fake_synthesize(
        text: str,
        config: Mapping[str, object],
        fn_index: int,
        reference_audio: Mapping[str, object],
        voice_description: str,
    ) -> dict[str, object]:
        calls.append(text)
        return {"audio": b"RIFFstubWAVE", "mimeType": "audio/wav", "latencyMs": 3}

    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_ENABLED", "1")
    monkeypatch.setattr(precompute, "synthesize", fake_synthesize)

    result = precompute.synthesize_batch(
        ["hello", "world"],
        {"dependencies": [{"id": 6, "api_name": "/gen_single"}]},
        6,
        {"path": "/tmp/ref.wav"},
        "Same voice",
    )

    assert calls == ["hello", "world"]
    assert [item["batchMode"] for item in result] == ["sequential-fallback", "sequential-fallback"]


def test_batch_audio_references_prefers_generated_file_list() -> None:
    result = {
        "data": [
            {"__type__": "update", "value": {"path": "/tmp/preview.wav"}},
            {"__type__": "update", "value": [{"path": "/tmp/item-1.wav"}, {"path": "/tmp/item-2.wav"}]},
            {"__type__": "update", "value": None},
        ]
    }

    assert precompute.batch_audio_references(result) == [{"path": "/tmp/item-1.wav"}, {"path": "/tmp/item-2.wav"}]


def test_batch_audio_references_extracts_zip_output(monkeypatch) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("item-1.wav", b"RIFFoneWAVE")
        archive.writestr("item-2.wav", b"RIFFtwoWAVE")
    monkeypatch.setattr(precompute, "fetch_gradio_file", lambda ref: (buffer.getvalue(), "application/zip"))
    result = {
        "data": [
            {"__type__": "update", "value": {"path": "/tmp/preview.wav"}},
            {"__type__": "update", "value": []},
            {"__type__": "update", "value": {"path": "/tmp/batch.zip"}},
        ]
    }

    refs = precompute.batch_audio_references(result)

    assert [ref["name"] for ref in refs] == ["item-1.wav", "item-2.wav"]
    assert refs[1]["_inline_bytes"] == b"RIFFtwoWAVE"
