from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import wave
import zipfile
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import precompute_indextts_responses as precompute

from ipfs_accelerate_py.voice_jobs.executor import (
    ArtifactPolicy,
    VoiceJobExecutionError,
)
from ipfs_accelerate_py.voice_jobs.regeneration import (
    RegenerationEndpointContract,
    RegenerationRunnerPolicy,
    VoiceRegenerationError,
    VoiceRegenerationRunner,
)
from ipfs_datasets_py.voice.regeneration import (
    AbbyVoiceRegenerationError,
    AbbyVoiceRegenerationPlan,
    read_regeneration_plan,
)


def _runner_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24_000)
        audio.writeframes(b"\x01\x00" * 240)
    return buffer.getvalue()


def _pcm16_wav_bytes(
    samples: tuple[int, ...],
    *,
    sample_rate: int = 1_000,
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(
            b"".join(
                sample.to_bytes(2, "little", signed=True)
                for sample in samples
            )
        )
    return buffer.getvalue()


def test_atomic_audio_write_keeps_final_file_on_publish_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "response.wav"
    destination.write_bytes(b"previous-complete-audio")
    replacement = _runner_wav_bytes()
    observed_temporary_paths: list[Path] = []

    monkeypatch.setattr(
        precompute,
        "local_audio_is_structurally_valid",
        lambda path: path.read_bytes() == replacement,
    )

    def fail_replace(source: Path, target: Path) -> None:
        source_path = Path(source)
        observed_temporary_paths.append(source_path)
        assert source_path.parent == destination.parent
        assert source_path.suffix == destination.suffix
        assert source_path.read_bytes() == replacement
        assert Path(target) == destination
        assert destination.read_bytes() == b"previous-complete-audio"
        raise OSError("simulated interruption before atomic replace")

    monkeypatch.setattr(precompute.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated interruption"):
        precompute.write_audio_bytes_atomic(destination, replacement)

    assert destination.read_bytes() == b"previous-complete-audio"
    assert observed_temporary_paths
    assert all(not path.exists() for path in observed_temporary_paths)


def test_atomic_audio_write_preserves_final_file_on_trailing_silence_rejection(
    monkeypatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "response.wav"
    previous = _runner_wav_bytes()
    destination.write_bytes(previous)
    padded = _pcm16_wav_bytes((1_000, 0, 0))
    monkeypatch.setenv("WALLET_INDEXTTS_MAX_TRAILING_SILENCE_MS", "1")

    with pytest.raises(VoiceJobExecutionError) as captured:
        precompute.write_audio_bytes_atomic(destination, padded)

    assert captured.value.code == "audio_trailing_silence_exceeded"
    assert captured.value.retryable is True
    assert destination.read_bytes() == previous
    assert not list(tmp_path.glob(".response.*.wav"))


def test_atomic_mp3_conversion_keeps_final_file_when_ffmpeg_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    wav_path = tmp_path / "response.wav"
    wav_path.write_bytes(_runner_wav_bytes())
    mp3_path = tmp_path / "response.mp3"
    mp3_path.write_bytes(b"previous-complete-mp3")
    observed_temporary_paths: list[Path] = []

    def fail_ffmpeg(command: list[str], *, check: bool) -> None:
        assert check is True
        temporary_path = Path(command[-1])
        observed_temporary_paths.append(temporary_path)
        assert temporary_path.parent == mp3_path.parent
        assert temporary_path.suffix == mp3_path.suffix
        assert temporary_path != mp3_path
        temporary_path.write_bytes(b"partial-new-mp3")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(precompute.subprocess, "run", fail_ffmpeg)

    with pytest.raises(subprocess.CalledProcessError):
        precompute.convert_wav_to_mp3(wav_path, mp3_path, force=True)

    assert mp3_path.read_bytes() == b"previous-complete-mp3"
    assert observed_temporary_paths
    assert all(not path.exists() for path in observed_temporary_paths)


def test_local_audio_validation_prefers_ffprobe(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "response.mp3"
    audio_path.write_bytes(b"nonempty cache candidate")
    commands: list[list[str]] = []

    monkeypatch.setattr(precompute.shutil, "which", lambda executable: f"/usr/bin/{executable}")

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False
        assert kwargs["timeout"] == 10
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "codec_type": "audio",
                            "codec_name": "mp3",
                            "channels": 1,
                            "sample_rate": "24000",
                            "nb_read_frames": "12",
                        }
                    ]
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(precompute.subprocess, "run", fake_run)

    assert precompute.local_audio_is_structurally_valid(audio_path) is True
    assert commands
    assert commands[0][0] == "/usr/bin/ffprobe"
    assert "-select_streams" in commands[0]


def test_invalid_nonempty_cache_is_discarded_without_ffprobe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    valid_path = tmp_path / "valid.wav"
    valid_path.write_bytes(_runner_wav_bytes())
    invalid_path = tmp_path / "truncated.wav"
    invalid_path.write_bytes(_runner_wav_bytes()[:-20])

    monkeypatch.setattr(precompute.shutil, "which", lambda _executable: None)

    assert precompute.local_audio_is_structurally_valid(valid_path) is True
    assert precompute.discard_invalid_local_audio_cache(valid_path) is False
    assert precompute.discard_invalid_local_audio_cache(invalid_path) is True
    assert valid_path.exists()
    assert not invalid_path.exists()


@pytest.mark.parametrize(
    "stale_reference_first",
    [False, True],
    ids=("normal", "refresh-stale-reference"),
)
@pytest.mark.parametrize(
    "cache_kind",
    ["truncated", "padded-tail"],
)
def test_main_regenerates_invalid_or_padded_local_cache(
    monkeypatch,
    tmp_path: Path,
    stale_reference_first: bool,
    cache_kind: str,
) -> None:
    text = "A safe response that must be regenerated."
    normalized_text = precompute.normalize_indextts_spoken_text(text)
    response_id = f"abby-tts-{precompute.stable_id(normalized_text)}"
    response_manifest = tmp_path / "responses.json"
    response_manifest.write_text(
        json.dumps({"responses": [{"text": text}]}),
        encoding="utf-8",
    )
    reference_audio = tmp_path / "reference.wav"
    reference_audio.write_bytes(_runner_wav_bytes())
    output_dir = tmp_path / "audio"
    output_dir.mkdir()
    cached_wav = output_dir / f"{response_id}.wav"
    cached_content = (
        b"RIFF nonempty but truncated"
        if cache_kind == "truncated"
        else _pcm16_wav_bytes((1_000,) + (0,) * 1_001)
    )
    cached_wav.write_bytes(cached_content)
    generated_audio = _runner_wav_bytes()
    manifest_path = tmp_path / "manifest.json"
    public_manifest_path = tmp_path / "public-manifest.json"
    synthesis_calls: list[list[str]] = []
    reference_uploads: list[str] = []

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "precompute_indextts_responses.py",
            "--response-manifest",
            str(response_manifest),
            "--reference-audio",
            str(reference_audio),
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(manifest_path),
            "--public-manifest",
            str(public_manifest_path),
            "--slotted-response-index",
            str(tmp_path / "missing-slotted-index.json"),
            "--remote-batch-size",
            "1",
            "--no-mp3",
        ],
    )
    monkeypatch.setattr(precompute, "load_secret_env", lambda: None)
    monkeypatch.setattr(precompute, "describe_indextts_auth", lambda: "test auth")
    monkeypatch.setattr(precompute, "indextts_config", lambda: {"dependencies": []})
    monkeypatch.setattr(precompute, "indextts_fn_index", lambda _config: 6)
    monkeypatch.setattr(
        precompute,
        "indextts_contract_summary",
        lambda _config, _fn_index: {"deploymentDriftReason": ""},
    )

    def fake_upload_reference(path: Path) -> dict[str, str]:
        upload_path = (
            f"/tmp/gradio/upload-{len(reference_uploads) + 1}/{path.name}"
        )
        reference_uploads.append(upload_path)
        return {"path": upload_path}

    monkeypatch.setattr(precompute, "upload_reference", fake_upload_reference)
    refreshable_gradio_file = precompute.RefreshableGradioFile
    monkeypatch.setattr(
        precompute,
        "RefreshableGradioFile",
        lambda uploader: refreshable_gradio_file(
            uploader,
            sleeper=lambda _delay: None,
        ),
    )

    def fake_synthesize_batch(
        texts: list[str],
        *_args: object,
        **_kwargs: object,
    ) -> list[dict[str, object]]:
        synthesis_calls.append(texts)
        if stale_reference_first and len(synthesis_calls) == 1:
            reference = _args[2]
            assert isinstance(reference, Mapping)
            raise RuntimeError(
                "FileNotFoundError: [Errno 2] No such file or directory: "
                f"'{reference['path']}'"
            )
        return [
            {
                "audio": generated_audio,
                "mimeType": "audio/wav",
                "latencyMs": 1,
                "batchMode": "single",
            }
        ]

    monkeypatch.setattr(precompute, "synthesize_batch", fake_synthesize_batch)
    monkeypatch.setattr(
        precompute,
        "local_audio_is_structurally_valid",
        lambda path: (
            path.read_bytes() == generated_audio
            or (
                cache_kind == "padded-tail"
                and path.read_bytes() == cached_content
            )
        ),
    )

    precompute.main()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_call_count = 2 if stale_reference_first else 1
    assert synthesis_calls == [[normalized_text]] * expected_call_count
    assert len(reference_uploads) == expected_call_count
    assert cached_wav.read_bytes() == generated_audio
    assert payload["responses"][0]["status"] == "generated"


def _regeneration_plan() -> AbbyVoiceRegenerationPlan:
    records = [
        {
            "audioId": f"audio-{name}",
            "responseId": f"response-{name}",
            "selectedDatasetAudioPath": f"audio/{name}.wav",
            "selectedText": text,
            "normalizedRepairText": text,
            "riskReasons": ["historical_tts_artifact"],
        }
        for name, text in (
            ("retry", "Retry this safe response."),
            ("quarantine", "Quarantine this unsafe response."),
            ("exhaust", "Exhaust this unavailable response."),
        )
    ]
    return AbbyVoiceRegenerationPlan.from_records(records)


def test_indextts_batch_fn_index_discovers_configured_api(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_API_NAME", "gen_batch")

    assert precompute.indextts_batch_fn_index({"dependencies": [{"id": 6, "api_name": "/gen_single"}, {"id": 9, "api_name": "/gen_batch"}]}) == 9


def test_publicus_defaults_and_cached_huggingface_token(monkeypatch) -> None:
    for name in (
        *precompute.INDEXTTS_TOKEN_ENV_NAMES,
        "WALLET_INDEXTTS_SPACE_URL",
        "WALLET_INDEXTTS_MODEL_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(precompute, "load_resolve_secret", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(get_token=lambda: "hf_cached_publicus_token"),
    )

    precompute.load_secret_env()

    assert precompute.indextts_base_url() == "https://publicus-indextts-2-demo.hf.space"
    assert precompute.indextts_model_name() == "Publicus/IndexTTS-2-Demo"
    assert precompute.current_huggingface_token() == "hf_cached_publicus_token"
    assert precompute.indextts_headers()["Authorization"] == "Bearer hf_cached_publicus_token"


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


def test_request_data_defaults_to_legacy_single_contract() -> None:
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.request_data("one", reference, "Same voice")

    assert len(data) == 24
    assert data[2] == "one"
    assert data[13] == "Same voice"
    assert data[16] is True


def test_request_data_supports_new_segments_bucket_contract() -> None:
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.request_data("one", reference, "Same voice", input_count=25)

    assert len(data) == 25
    assert data[16] == 0
    assert data[17] is True


def test_batch_request_data_supports_legacy_batch_contract() -> None:
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.batch_request_data(["one", "two"], reference, "Same voice", input_count=24)

    assert len(data) == 24
    assert data[2] == '["one", "two"]'
    assert data[16] is True


def test_lookup_dependency_input_count_reads_dependency_inputs() -> None:
    assert precompute.lookup_dependency_input_count(
        {"dependencies": [{"id": 6, "api_name": "/gen_single", "inputs": list(range(25))}]},
        6,
    ) == 25


def test_indextts_config_delegates_to_generic_space_client(monkeypatch) -> None:
    class FakeClient:
        def get_config(self) -> dict[str, object]:
            return {"dependencies": [{"id": 1, "api_name": "/gen_single"}]}

    monkeypatch.setattr(precompute, "indextts_space_client", lambda: FakeClient())

    assert precompute.indextts_config() == {"dependencies": [{"id": 1, "api_name": "/gen_single"}]}


def test_wait_for_result_delegates_to_generic_space_client(monkeypatch) -> None:
    class FakeClient:
        def wait_for_queue_result(
            self,
            session_hash: str,
            *,
            timeout_seconds: float,
            poll_interval_seconds: float,
        ) -> dict[str, object]:
            assert session_hash == "session-123"
            assert timeout_seconds > 0
            assert poll_interval_seconds == 0.5
            return {"data": [{"path": "/tmp/out.wav"}]}

    monkeypatch.setattr(precompute, "indextts_space_client", lambda: FakeClient())

    assert precompute.wait_for_result("session-123") == {"data": [{"path": "/tmp/out.wav"}]}


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
    assert all("not found" in str(item.get("batchFallbackReason") or "") for item in result)


def test_synthesize_batch_split_fallback_salvages_large_batch(monkeypatch) -> None:
    def fake_direct_batch(
        texts: list[str],
        config: Mapping[str, object],
        reference_audio: Mapping[str, object],
        voice_description: str,
    ) -> list[dict[str, object]]:
        if len(texts) > 2:
            raise RuntimeError("ZeroGPU worker error")
        return [
            {
                "audio": f"RIFF-{text}".encode(),
                "mimeType": "audio/wav",
                "latencyMs": 4,
                "batchLatencyMs": 4,
                "batchMode": "batch",
            }
            for text in texts
        ]

    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_ENABLED", "1")
    monkeypatch.setattr(precompute, "direct_batch_synthesis", fake_direct_batch)

    result = precompute.synthesize_batch(
        ["one", "two", "three", "four", "five", "six", "seven", "eight"],
        {"dependencies": [{"id": 6, "api_name": "/gen_single"}, {"id": 9, "api_name": "/gen_batch"}]},
        6,
        {"path": "/tmp/ref.wav"},
        "Same voice",
    )

    assert len(result) == 8
    assert all(item["batchMode"] == "batch-split-fallback" for item in result)
    assert all(item["batchRequestedSize"] == 8 for item in result)
    assert all(item["batchExecutedSize"] == 2 for item in result)
    assert all(item["batchSplitDepth"] == 2 for item in result)
    assert all("ZeroGPU worker error" in str(item.get("batchFallbackReason") or "") for item in result)


def test_adaptive_split_batch_synthesis_falls_back_to_single_for_irreducible_failure(monkeypatch) -> None:
    calls: list[str] = []

    def fake_direct_batch(
        texts: list[str],
        config: Mapping[str, object],
        reference_audio: Mapping[str, object],
        voice_description: str,
    ) -> list[dict[str, object]]:
        raise RuntimeError("ZeroGPU worker error")

    def fake_synthesize(
        text: str,
        config: Mapping[str, object],
        fn_index: int,
        reference_audio: Mapping[str, object],
        voice_description: str,
    ) -> dict[str, object]:
        calls.append(text)
        return {"audio": b"RIFFstubWAVE", "mimeType": "audio/wav", "latencyMs": 3}

    monkeypatch.setattr(precompute, "direct_batch_synthesis", fake_direct_batch)
    monkeypatch.setattr(precompute, "synthesize", fake_synthesize)

    result = precompute.synthesize_batch(
        ["hello"],
        {"dependencies": [{"id": 6, "api_name": "/gen_single"}, {"id": 9, "api_name": "/gen_batch"}]},
        6,
        {"path": "/tmp/ref.wav"},
        "Same voice",
    )

    assert calls == ["hello"]
    assert result[0]["batchMode"] == "sequential-split-fallback"
    assert result[0]["batchRequestedSize"] == 1
    assert result[0]["batchExecutedSize"] == 1
    assert "ZeroGPU worker error" in str(result[0].get("batchFallbackReason") or "")


def test_space_queue_failed_without_details_is_transient() -> None:
    assert precompute.is_indextts_transient_worker_error("Space queue failed: {'error': None}") is True


def test_generated_audio_quality_error_is_transient() -> None:
    error = VoiceJobExecutionError(
        "audio_trailing_silence_exceeded",
        retryable=True,
    )

    assert precompute.is_indextts_transient_worker_error(error) is True
    assert precompute.batch_failure_result(
        error,
        batch_mode="batch",
        fallback_reason="",
        requested_batch_size=1,
        executed_batch_size=1,
        split_depth=0,
    )["retriable"] is True


def test_indextts_contract_summary_reports_missing_batch_alias(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_API_NAME", "/gen_batch")

    summary = precompute.indextts_contract_summary(
        {"dependencies": [{"id": 6, "api_name": "/gen_single", "inputs": list(range(24))}]},
        6,
    )

    assert summary["singleContract"] == "legacy-24-field"
    assert summary["batchRegistered"] is False
    assert summary["recommendedMode"] == "parallel-gen-single"
    assert summary["remoteBucketPipelineReady"] is False
    assert "/gen_single" in summary["registeredApiNames"]
    assert "deploymentDriftReason" in summary


def test_indextts_contract_summary_reports_registered_batch_alias(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_API_NAME", "/gen_batch")
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_UPLOAD_API_NAME", "/gen_batch_with_upload")
    monkeypatch.setenv("WALLET_INDEXTTS_UPLOAD_RESULTS_API_NAME", "/upload_generated_results")
    monkeypatch.setenv("WALLET_INDEXTTS_AUTO_UPLOAD_RESULTS_API_NAME", "/maybe_auto_upload_generated_results")

    summary = precompute.indextts_contract_summary(
        {
            "dependencies": [
                {"id": 6, "api_name": "/gen_single", "inputs": list(range(25))},
                {"id": 9, "api_name": "/gen_batch", "inputs": list(range(25))},
                {"id": 10, "api_name": "/gen_batch_with_upload", "inputs": list(range(25))},
                {"id": 11, "api_name": "/upload_generated_results", "inputs": []},
            ]
        },
        6,
    )

    assert summary["singleContract"] == "segments-bucket-25-field"
    assert summary["batchRegistered"] is True
    assert summary["batchFnIndex"] == 9
    assert summary["batchContract"] == "segments-bucket-25-field"
    assert summary["batchUploadRegistered"] is True
    assert summary["batchUploadInputCount"] == 25
    assert summary["uploadResultsRegistered"] is True
    assert summary["remoteBucketPipelineReady"] is True
    assert summary["recommendedMode"] == "gen_batch_with_upload"


def test_publicus_endpoint_contract_detects_single_and_batch_functions() -> None:
    receipt = precompute.probe_indextts_endpoint_contract(
        config={
            "dependencies": [
                {"id": 6, "api_name": "/gen_single", "inputs": list(range(25))},
                {"id": 7, "api_name": "/gen_batch", "inputs": list(range(25))},
            ]
        }
    )

    assert receipt["compatible"] is True
    assert receipt["function_index"] == 6
    assert receipt["input_count"] == 25
    assert receipt["batch_function_index"] == 7
    assert receipt["batch_input_count"] == 25
    assert receipt["expected"]["require_batch_match"] is True


def test_publicus_endpoint_contract_rejects_missing_batch_unless_explicitly_allowed() -> None:
    config = {
        "dependencies": [
            {"id": 6, "api_name": "/gen_single", "inputs": list(range(25))},
        ]
    }

    with pytest.raises(RuntimeError, match="batch_api_name_not_registered"):
        precompute.probe_indextts_endpoint_contract(config=config)

    receipt = precompute.probe_indextts_endpoint_contract(
        config=config,
        require_batch_match=False,
    )
    assert receipt["compatible"] is True
    assert receipt["batch_function_index"] is None


def test_endpoint_contract_probe_is_read_only_and_fails_closed_on_drift() -> None:
    calls: list[str] = []

    class FakeClient:
        space_url = "https://fixture-indextts.example"

        def get_config(self) -> dict[str, object]:
            calls.append("get_config")
            return {
                "dependencies": [
                    {
                        "id": 6,
                        "api_name": "/gen_single",
                        "inputs": list(range(24)),
                    }
                ]
            }

        def queue_join(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("read-only probe attempted generation")

        def upload_file(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("read-only probe attempted upload")

    receipt = precompute.probe_indextts_endpoint_contract(
        client=FakeClient(),
        expected_input_count=24,
        require_batch_match=False,
    )

    assert calls == ["get_config"]
    assert receipt["compatible"] is True
    assert receipt["read_only"] is True
    assert receipt["generation_request_count"] == 0
    assert receipt["upload_request_count"] == 0
    assert receipt["api_name"] == "/gen_single"
    assert receipt["function_index"] == 6
    assert receipt["input_count"] == 24
    assert (
        RegenerationEndpointContract.from_mapping(receipt).contract_id
        == receipt["contract_id"]
    )
    serialized = json.dumps(receipt, sort_keys=True)
    assert "authorization" not in serialized.casefold()
    assert "token" not in serialized.casefold()

    with pytest.raises(RuntimeError, match="input_count_mismatch"):
        precompute.probe_indextts_endpoint_contract(
            client=FakeClient(),
            expected_input_count=25,
            require_batch_match=False,
        )


def test_package_canary_manifest_is_deterministic_bounded_and_no_dispatch(
    monkeypatch,
) -> None:
    provider_touched = False

    def forbidden_provider(*_args: object, **_kwargs: object) -> bytes:
        nonlocal provider_touched
        provider_touched = True
        raise AssertionError("manifest construction attempted provider dispatch")

    monkeypatch.setattr(precompute, "synthesize", forbidden_provider)
    contract = precompute.probe_indextts_endpoint_contract(
        client=type(
            "FakeClient",
            (),
            {
                "space_url": "https://fixture-indextts.example",
                "get_config": lambda self: {
                    "dependencies": [
                        {
                            "id": 6,
                            "api_name": "/gen_single",
                            "inputs": list(range(24)),
                        }
                    ]
                },
            },
        )(),
        expected_input_count=24,
        require_batch_match=False,
    )
    plan = _regeneration_plan()

    first = precompute.build_canary_dispatch_manifest(
        plan,
        contract,
        max_items=2,
        max_attempts_per_item=2,
        max_provider_requests=4,
        cost_microusd_per_request=7,
        max_cost_microusd=28,
    )
    second = precompute.build_canary_dispatch_manifest(
        AbbyVoiceRegenerationPlan(items=tuple(reversed(plan.items))),
        contract,
        max_items=2,
        max_attempts_per_item=2,
        max_provider_requests=4,
        cost_microusd_per_request=7,
        max_cost_microusd=28,
    )

    assert first == second
    assert provider_touched is False
    assert first["schema_version"] == "abby_voice_regeneration_dispatch_v1"
    assert first["dispatch_authorized"] is False
    assert first["remote_mutation_authority"] is False
    assert first["provider_request_count"] == 0
    assert first["state"] == "awaiting_operator_approval"
    assert first["item_count"] == 2
    assert first["limits"]["max_provider_requests"] == 4
    assert first["limits"]["max_cost_microusd"] == 28
    assert all(len(item["task_id"]) == 64 for item in first["items"])


def test_regeneration_plan_file_round_trip_is_canonical(tmp_path: Path) -> None:
    plan = _regeneration_plan()
    plan_path = tmp_path / "regeneration-plan.json"
    plan_path.write_text(json.dumps(plan.to_dict()), encoding="utf-8")

    loaded = read_regeneration_plan(plan_path)

    assert loaded.canonical_bytes() == plan.canonical_bytes()
    assert loaded.plan_id == plan.plan_id

    tampered = plan.to_dict()
    tampered["item_count"] += 1
    plan_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(
        AbbyVoiceRegenerationError,
        match="not its canonical serialized representation",
    ):
        read_regeneration_plan(plan_path)


def test_fake_provider_runner_retries_quarantines_exhausts_and_resumes(
    tmp_path: Path,
) -> None:
    contract = RegenerationEndpointContract(
        endpoint_url="https://fixture-indextts.example",
        api_name="/gen_single",
        function_index=6,
        input_count=24,
        recommended_mode="parallel-gen-single",
        config_sha256="a" * 64,
    )
    policy = RegenerationRunnerPolicy(
        max_items=3,
        max_attempts_per_item=2,
        max_provider_requests=6,
        cost_microusd_per_request=5,
        max_cost_microusd=30,
    )
    manifest = _regeneration_plan().canary_dispatch_manifest(
        endpoint_contract=contract,
        size=3,
        runner_policy=policy,
    )
    calls: dict[str, int] = {}

    def fake_provider(text: str, **_kwargs: object) -> bytes:
        calls[text] = calls.get(text, 0) + 1
        if text.startswith("Retry") and calls[text] == 1:
            raise VoiceJobExecutionError("provider_timeout", retryable=True)
        if text.startswith("Quarantine"):
            raise VoiceJobExecutionError("unsafe_spoken_text", retryable=False)
        if text.startswith("Exhaust"):
            raise VoiceJobExecutionError("provider_unavailable", retryable=True)
        return _runner_wav_bytes()

    checkpoint = tmp_path / "run-receipt.json"
    runner = VoiceRegenerationRunner(
        provider=fake_provider,
        contract_probe=lambda: contract,
        checkpoint_path=checkpoint,
        artifact_policy=ArtifactPolicy(output_root=tmp_path / "artifacts"),
        sleep=lambda _seconds: None,
    )

    with pytest.raises(VoiceRegenerationError, match="dispatch_authorized"):
        runner.run(manifest)
    assert calls == {}

    receipt = runner.run(manifest, dispatch_authorized=True)

    assert receipt["summary"] == {
        "pending": 0,
        "provider_exhausted": 1,
        "quarantined": 1,
        "regenerated": 1,
    }
    assert receipt["provider_request_count"] == 5
    assert receipt["cost_microusd_spent"] == 25
    assert sorted(calls.values()) == [1, 2, 2]
    statuses = {item["status"] for item in receipt["items"]}
    assert statuses == {"regenerated", "quarantined", "provider_exhausted"}
    checkpoint_text = checkpoint.read_text(encoding="utf-8")
    assert "unsafe_spoken_text" in checkpoint_text
    assert "provider_unavailable" in checkpoint_text
    assert "_runner_wav_bytes" not in checkpoint_text
    assert "RIFF" not in checkpoint_text

    calls_before_resume = dict(calls)
    resumed = VoiceRegenerationRunner(
        provider=fake_provider,
        contract_probe=lambda: contract,
        checkpoint_path=checkpoint,
        artifact_policy=ArtifactPolicy(output_root=tmp_path / "artifacts"),
        sleep=lambda _seconds: None,
    ).run(manifest, dispatch_authorized=True)

    assert resumed == receipt
    assert calls == calls_before_resume


def test_runner_rejects_tampered_regenerated_checkpoint(tmp_path: Path) -> None:
    contract = RegenerationEndpointContract(
        endpoint_url="https://fixture-indextts.example",
        api_name="/gen_single",
        function_index=6,
        input_count=24,
        recommended_mode="parallel-gen-single",
        config_sha256="b" * 64,
    )
    policy = RegenerationRunnerPolicy(
        max_items=1,
        max_attempts_per_item=1,
        max_provider_requests=1,
        max_cost_microusd=1,
    )
    manifest = _regeneration_plan().canary_dispatch_manifest(
        endpoint_contract=contract,
        size=1,
        runner_policy=policy,
    )
    checkpoint = tmp_path / "run-receipt.json"
    runner = VoiceRegenerationRunner(
        provider=lambda _text, **_kwargs: _runner_wav_bytes(),
        contract_probe=lambda: contract,
        checkpoint_path=checkpoint,
        artifact_policy=ArtifactPolicy(output_root=tmp_path / "artifacts"),
    )
    runner.run(manifest, dispatch_authorized=True)
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["items"][0]["result"] = None
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        VoiceRegenerationError,
        match="requires a canonical result",
    ):
        runner.run(manifest, dispatch_authorized=True)


def test_runner_reprobes_and_rejects_endpoint_drift_before_dispatch(
    tmp_path: Path,
) -> None:
    original = RegenerationEndpointContract(
        endpoint_url="https://fixture-indextts.example",
        api_name="/gen_single",
        function_index=6,
        input_count=24,
        recommended_mode="parallel-gen-single",
        config_sha256="c" * 64,
    )
    drifted = RegenerationEndpointContract(
        endpoint_url="https://fixture-indextts.example",
        api_name="/gen_single",
        function_index=7,
        input_count=24,
        recommended_mode="parallel-gen-single",
        config_sha256="d" * 64,
    )
    manifest = _regeneration_plan().canary_dispatch_manifest(
        endpoint_contract=original,
        size=1,
        runner_policy=RegenerationRunnerPolicy(
            max_items=1,
            max_attempts_per_item=1,
            max_provider_requests=1,
            max_cost_microusd=1,
        ),
    )
    provider_calls = 0

    def forbidden_provider(_text: str, **_kwargs: object) -> bytes:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("endpoint drift attempted provider dispatch")

    runner = VoiceRegenerationRunner(
        provider=forbidden_provider,
        contract_probe=lambda: drifted,
        checkpoint_path=tmp_path / "run-receipt.json",
    )

    with pytest.raises(VoiceRegenerationError, match="endpoint contract changed"):
        runner.run(manifest, dispatch_authorized=True)

    assert provider_calls == 0
    assert runner.checkpoint_path.exists() is False


def test_ensure_upload_capable_batch_contract_rejects_local_sync_fallback(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_API_NAME", "/gen_batch")
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_UPLOAD_API_NAME", "/gen_batch_with_upload")

    with pytest.raises(RuntimeError, match="upload-capable batch pipeline"):
        precompute.ensure_upload_capable_batch_contract(
            {
                "dependencies": [
                    {"id": 6, "api_name": "/gen_single", "inputs": list(range(25))},
                    {"id": 9, "api_name": "/gen_batch", "inputs": list(range(25))},
                ]
            },
            6,
        )


def test_normalize_slot_value_text_keeps_address_digits_spaced_and_ordinals_intact() -> None:
    normalized = precompute.normalize_slot_value_text("address", "530 NW 27th Street Corvallis, OR 97330")

    assert "five three zero" in normalized
    assert "twenty seventh Street" in normalized
    assert "nine seven three three zero" in normalized
    assert "fivethreezero" not in normalized
    assert "twoseventh" not in normalized


def test_phone_text_normalization_removes_parentheses_and_negative_prone_hyphens() -> None:
    normalized = precompute.normalize_indextts_spoken_text(
        "Call (503) 771-7914 ext. 42. Backup: 5-4-1, 9-6-7, 8-6-3-0. "
        "Other: 5 4 1, 6 8 2, 1 0 0 1. Main: 503, 236, 4580. "
        "Dots: 503. 988. 338. 7. Commas: 50, 33, 68, 98, 95. Dash: 5 4 1 — 6 8 9 — 3 1 1 1."
    )

    assert "five zero three, seven seven one, seven nine one four" in normalized
    assert "extension four two" in normalized
    assert "five four one, nine six seven, eight six three zero" in normalized
    assert "five four one, six eight two, one zero zero one" in normalized
    assert "five zero three, two three six, four five eight zero" in normalized
    assert "five zero three, nine eight eight, three three eight seven" in normalized
    assert "five zero three, three six eight, nine eight nine five" in normalized
    assert "five four one, six eight nine, three one one one" in normalized
    assert "(" not in normalized
    assert ")" not in normalized
    assert "-" not in normalized


def test_phone_slot_value_normalization_uses_words_not_punctuation() -> None:
    normalized = precompute.normalize_slot_value_text("phone", "+1 (503) 555-0100")

    assert normalized == "five zero three, five five five, zero one zero zero"
    assert "negative" not in normalized
    assert "(" not in normalized
    assert "-" not in normalized


def test_range_and_parenthetical_normalization_removes_tts_punctuation_traps() -> None:
    normalized = precompute.normalize_indextts_spoken_text(
        "Emergency Diaper Closet serves families with kids ages 0–5 (Lane County Diaper Bank). "
        "The address was rendered as 5-0-thirteenth Street. "
        "Choose Downtown clinic at 11-32 Southwest thirteenth Avenue or East Burnside clinic at 16-144 East Burnside Street."
    )

    assert "ages zero to five" in normalized
    assert "Lane County Diaper Bank" in normalized
    assert "five zero thirteenth Street" in normalized
    assert re.search(
        r"one one three two South(?:west| West) thirteenth Avenue",
        normalized,
    )
    assert "one six one four four East Burnside Street" in normalized
    assert "(" not in normalized
    assert ")" not in normalized
    assert "0–5" not in normalized
    assert "5-0-thirteenth" not in normalized
    assert "11-32" not in normalized
    assert "16-144" not in normalized


@pytest.mark.parametrize(
    "raw_address",
    (
        "11-32 Southwest 13th Avenue, Portland, OR 97205",
        "11-32 SW 13th Ave, Portland, OR 97205",
    ),
)
def test_address_slot_normalization_removes_hyphens_with_abbreviated_tokens(
    raw_address: str,
) -> None:
    normalized = precompute.normalize_slot_value_text("address", raw_address)

    assert re.search(
        r"one one three two South(?:west| West) thirteenth Avenue",
        normalized,
    )
    assert "11-32" not in normalized
    assert "-32" not in normalized
    assert "-" not in normalized


@pytest.mark.parametrize(
    ("kind", "raw_value"),
    (
        ("phone", "+1 (503) 555-0100"),
        (
            "address",
            "11-32 SW 13th Ave (main office), Portland, OR 97205",
        ),
    ),
)
def test_telephone_factual_slot_audio_text_has_no_spoken_punctuation_markers(
    kind: str,
    raw_value: str,
) -> None:
    normalized = precompute.normalize_slot_value_text(kind, raw_value)
    lowered = normalized.casefold()

    assert "negative" not in lowered
    assert "parenthesis" not in lowered
    assert "parentheses" not in lowered
    assert "hyphen" not in lowered
    assert " dash " not in f" {lowered} "
    assert "(" not in normalized and ")" not in normalized
    assert not re.search(r"\d\s*[-–—]\s*\d", normalized)


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


def test_detects_indextts_quota_exceeded_message() -> None:
    message = (
        "IndexTTS queue failed: {'error': 'You have exceeded your Pro ZeroGPU quota "
        "(60s requested vs. 53s left). Try again in 23:05:50.'}"
    )

    assert precompute.is_indextts_quota_exceeded_error(message) is True
    assert precompute.indextts_retry_after_hint(message) == "23:05:50"


def test_raise_if_indextts_quota_exceeded_raises_typed_error() -> None:
    message = "ZeroGPU quota exceeded. Try again in 01:02:03."

    try:
        precompute.raise_if_indextts_quota_exceeded(message)
    except precompute.IndexTTSQuotaExceededError as exc:
        assert exc.retry_after == "01:02:03"
    else:
        raise AssertionError("Expected IndexTTSQuotaExceededError")


def test_bucket_sync_targets_default_to_audio_and_metadata_subpaths() -> None:
    targets = precompute.bucket_sync_targets("hf://buckets/Publicus/abby-voice")

    assert targets == {
        "bucketUri": "hf://buckets/Publicus/abby-voice",
        "audioUri": "hf://buckets/Publicus/abby-voice/audio",
        "metadataUri": "hf://buckets/Publicus/abby-voice/metadata",
    }


def test_sync_generated_outputs_to_bucket_invokes_hf_sync_for_audio_and_metadata(monkeypatch, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "sample.mp3").write_bytes(b"mp3")
    manifest_path = tmp_path / "manifest.json"
    public_manifest_path = tmp_path / "public-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    public_manifest_path.write_text("{}", encoding="utf-8")

    calls: list[list[str]] = []

    monkeypatch.setattr(precompute, "load_secret_env", lambda: None)
    monkeypatch.setattr(precompute, "hf_cli_executable", lambda: "/usr/bin/hf")

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="synced", stderr="")

    monkeypatch.setattr(precompute.subprocess, "run", fake_run)

    summary = precompute.sync_generated_outputs_to_bucket(
        output_dir,
        manifest_path,
        public_manifest_path,
        "hf://buckets/Publicus/abby-voice",
    )

    assert calls[0] == ["/usr/bin/hf", "sync", str(output_dir), "hf://buckets/Publicus/abby-voice/audio"]
    assert calls[1][0:2] == ["/usr/bin/hf", "sync"]
    assert calls[1][-1] == "hf://buckets/Publicus/abby-voice/metadata"
    assert summary["audioUri"] == "hf://buckets/Publicus/abby-voice/audio"
    assert summary["metadataUri"] == "hf://buckets/Publicus/abby-voice/metadata"


def test_bucket_audio_uris_builds_deterministic_object_paths() -> None:
    uris = precompute.bucket_audio_uris("hf://buckets/Publicus/abby-voice/run-1", "abby-tts-1234")

    assert uris == {
        "bucketAudioUri": "hf://buckets/Publicus/abby-voice/run-1/audio/abby-tts-1234.wav",
        "bucketMp3Uri": "hf://buckets/Publicus/abby-voice/run-1/audio/abby-tts-1234.mp3",
    }


def test_cached_bucket_audio_entry_prefers_remote_mp3(monkeypatch) -> None:
    class FakeBucketBackend:
        def __init__(self, existing: set[str]):
            self.existing = existing

        def exists(self, remote_path: str) -> bool:
            return remote_path in self.existing

    monkeypatch.setattr(
        precompute,
        "hf_bucket_backend",
        lambda bucket_uri: FakeBucketBackend({"audio/abby-tts-1234.mp3"}),
    )
    validated: list[str] = []
    monkeypatch.setattr(
        precompute,
        "validate_indextts_bucket_audio",
        lambda _backend, remote_path: validated.append(remote_path) or {},
    )

    entry = precompute.cached_bucket_audio_entry(
        {"id": "abby-tts-1234", "text": "hello"},
        bucket_uri="hf://buckets/Publicus/abby-voice/run-1",
        prefer_mp3=True,
    )

    assert entry is not None
    assert entry["status"] == "cached_bucket_mp3"
    assert entry["preferredAudioPath"] == "hf://buckets/Publicus/abby-voice/run-1/audio/abby-tts-1234.mp3"
    assert entry["preferredBucketAudioUri"] == entry["preferredAudioPath"]
    assert entry["bucketAudioUri"] == "hf://buckets/Publicus/abby-voice/run-1/audio/abby-tts-1234.wav"
    assert validated == ["audio/abby-tts-1234.mp3"]


def test_cached_bucket_audio_rejects_quality_failed_remote_object(
    monkeypatch,
) -> None:
    class FakeBucketBackend:
        def exists(self, remote_path: str) -> bool:
            return remote_path.endswith(".mp3")

    monkeypatch.setattr(
        precompute,
        "hf_bucket_backend",
        lambda _bucket_uri: FakeBucketBackend(),
    )
    monkeypatch.setattr(
        precompute,
        "validate_indextts_bucket_audio",
        lambda _backend, _remote_path: (_ for _ in ()).throw(
            VoiceJobExecutionError(
                "audio_trailing_silence_exceeded",
                retryable=True,
            )
        ),
    )

    entry = precompute.cached_bucket_audio_entry(
        {"id": "abby-tts-padded", "text": "hello"},
        bucket_uri="hf://buckets/Publicus/abby-voice/run-1",
        prefer_mp3=True,
    )

    assert entry is None


def test_batch_upload_request_data_defaults_to_live_29_field_contract(monkeypatch) -> None:
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_SUBDIR", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_MODE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_AUTO_UPLOAD_ENABLED", raising=False)
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.batch_upload_request_data(
        ["hello", "world"],
        reference,
        "Same voice",
        "hf://buckets/Publicus/abby-voice/run-1",
    )

    assert len(data) == 29
    assert data[2] == '["hello", "world"]'
    assert data[25] == "hf://buckets/Publicus/abby-voice/run-1"
    assert data[26] == ""
    assert data[27] == "auto"
    assert data[28] is True


def test_batch_upload_request_data_preserves_legacy_26_field_contract(monkeypatch) -> None:
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", raising=False)
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.batch_upload_request_data(
        ["hello"],
        reference,
        "Same voice",
        "hf://buckets/Publicus/abby-voice/run-1",
        input_count=26,
    )

    assert len(data) == 26
    assert data[25] == "hf://buckets/Publicus/abby-voice/run-1"


def test_batch_upload_request_data_supports_live_tail_overrides(monkeypatch) -> None:
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", raising=False)
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.batch_upload_request_data(
        ["hello"],
        reference,
        "Same voice",
        "hf://buckets/Publicus/abby-voice",
        upload_subdir="runs/canary",
        upload_mode="batch_files",
        auto_upload_enabled=False,
    )

    assert data[25:] == [
        "hf://buckets/Publicus/abby-voice",
        "runs/canary",
        "batch_files",
        False,
    ]


def test_batch_upload_request_data_supports_template(monkeypatch) -> None:
    monkeypatch.setenv(
        "WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE",
        '[{reference_audio}, {texts}, {voice_description}, {bucket_uri}]',
    )
    reference = {"path": "/tmp/ref.wav", "meta": {"_type": "gradio.FileData"}}

    data = precompute.batch_upload_request_data(
        ["hi"],
        reference,
        "Same voice",
        "hf://buckets/Publicus/abby-voice/run-1",
    )

    assert data == [reference, ["hi"], "Same voice", "hf://buckets/Publicus/abby-voice/run-1"]


def test_direct_batch_upload_synthesis_uses_actual_returned_filenames(monkeypatch) -> None:
    queued: list[tuple[int, list]] = []

    class FakeClient:
        def queue_join(self, fn_index: int, data: list, **_: object) -> str:
            queued.append((fn_index, data))
            return "session-upload-1"

    monkeypatch.setattr(precompute, "indextts_space_client", lambda: FakeClient())
    monkeypatch.setattr(
        precompute,
        "wait_for_result",
        lambda session_hash: {
            "data": [
                {"path": "/tmp/gradio/spk_1780000000-item-1.wav"},
                [
                    {"path": "/tmp/gradio/spk_1780000000-item-1.wav"},
                    {"path": "/tmp/gradio/spk_1780000000-item-2.wav"},
                ],
                {"path": "/tmp/gradio/spk_1780000000-batch.zip"},
            ]
        },
    )
    monkeypatch.setattr(precompute, "indextts_batch_upload_api_name", lambda: "/gen_batch_with_upload")
    monkeypatch.setattr(precompute, "lookup_dependency_id_by_api_name", lambda _config, _name: 10)
    monkeypatch.setattr(precompute, "lookup_dependency_input_count", lambda _config, _fn: 29)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", raising=False)

    config = {"dependencies": [{"id": 10, "api_name": "/gen_batch_with_upload", "inputs": list(range(29))}]}
    reference = {"path": "/tmp/ref.wav"}

    results = precompute.direct_batch_upload_synthesis(
        ["hello", "world"],
        config,
        reference,
        "Same voice",
        "hf://buckets/Publicus/abby-voice/run-1",
        ["abby-tts-aaa", "abby-tts-bbb"],
    )

    assert len(results) == 2
    assert len(queued) == 1
    assert len(queued[0][1]) == 29
    assert queued[0][1][25:] == [
        "hf://buckets/Publicus/abby-voice/run-1",
        "",
        "auto",
        True,
    ]
    assert results[0]["batchMode"] == "batch-upload"
    assert results[0]["responseId"] == "abby-tts-aaa"
    assert results[0]["uploadedFilename"] == "spk_1780000000-item-1.wav"
    assert results[0]["bucketAudioUri"] == (
        "hf://buckets/Publicus/abby-voice/run-1/spk_1780000000-item-1.wav"
    )
    assert results[1]["bucketAudioUri"] == (
        "hf://buckets/Publicus/abby-voice/run-1/spk_1780000000-item-2.wav"
    )
    assert "abby-tts-aaa" not in results[0]["bucketAudioUri"]
    assert "bucketMp3Uri" not in results[0]
    assert results[0]["preferredBucketAudioUri"] == results[0]["bucketAudioUri"]
    assert "audio" not in results[0]


def test_direct_batch_upload_fails_closed_without_authoritative_filenames(monkeypatch) -> None:
    class FakeClient:
        def queue_join(self, fn_index: int, data: list, **_: object) -> str:
            return "session-upload-1"

    monkeypatch.setattr(precompute, "indextts_space_client", lambda: FakeClient())
    monkeypatch.setattr(precompute, "wait_for_result", lambda session_hash: {"data": []})
    monkeypatch.setattr(precompute, "indextts_batch_upload_api_name", lambda: "/gen_batch_with_upload")
    monkeypatch.setattr(precompute, "lookup_dependency_id_by_api_name", lambda _config, _name: 8)
    monkeypatch.setattr(precompute, "lookup_dependency_input_count", lambda _config, _fn: 29)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_UPLOAD_DATA_TEMPLATE", raising=False)
    monkeypatch.delenv("WALLET_INDEXTTS_BATCH_DATA_TEMPLATE", raising=False)

    with pytest.raises(
        precompute.IndexTTSUploadResultUnverifiableError,
        match="authoritative audio filename",
    ):
        precompute.direct_batch_upload_synthesis(
            ["hello"],
            {"dependencies": []},
            {"path": "/tmp/ref.wav"},
            "Same voice",
            "hf://buckets/Publicus/abby-voice/run-1",
            ["abby-tts-aaa"],
        )
