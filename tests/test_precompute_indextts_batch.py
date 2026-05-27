from __future__ import annotations

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
