from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import run_indextts_batch_generation as batch_runner


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_args(tmp_path: Path, **overrides: object) -> SimpleNamespace:
    payload = {
        "batch_size": 2,
        "remote_batch_size": 2,
        "parallel_workers": 1,
        "space_url": "https://publicus-indextts-2-demo.hf.space",
        "model_name": "Publicus/IndexTTS-2-Demo",
        "bucket_uri": "hf://buckets/Publicus/abby-voice/test-phase",
        "require_upload_capable_batch": True,
        "require_batch": True,
        "batch_retry_attempts": 1,
        "batch_retry_backoff_seconds": 0.1,
        "batch_retry_backoff_multiplier": 2.0,
        "batch_retry_max_backoff_seconds": 1.0,
        "max_runtime_seconds": 60.0,
        "start_offset": 0,
        "resume": True,
        "reset_state": False,
        "regeneration_full": False,
        "state": tmp_path / "state.json",
        "batch_manifest_dir": tmp_path / "batch-manifests",
        "progress_dir": tmp_path / "progress",
        "output_dir": tmp_path / "audio",
        "public_manifest": tmp_path / "public-manifest.json",
        "response_manifest": tmp_path / "responses.json",
        "dag": tmp_path / "dag.json",
        "results": tmp_path / "results.json",
        "stop_on_error": False,
        "force": False,
        "validate_transcripts": False,
        "transcript_validation_limit": 1,
        "transcript_validation_model": "tiny.en",
        "transcript_validation_language": "en",
        "transcript_validation_device": "auto",
        "transcript_validation_threshold": 0.72,
        "transcript_validation_soft_fail": False,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_cli_defaults_to_publicus_safe_batch_and_resume(monkeypatch) -> None:
    for name in (
        "WALLET_INDEXTTS_REMOTE_BATCH_SIZE",
        "WALLET_INDEXTTS_SPACE_URL",
        "WALLET_INDEXTTS_MODEL_NAME",
    ):
        monkeypatch.delenv(name, raising=False)

    args = batch_runner.parse_args([])

    assert args.space_url == "https://publicus-indextts-2-demo.hf.space"
    assert args.model_name == "Publicus/IndexTTS-2-Demo"
    assert args.remote_batch_size == 4
    assert args.require_batch is True
    assert args.resume is True


def test_regeneration_full_selects_canonical_dataset_paths() -> None:
    args = batch_runner.parse_args(["--regeneration-full"])

    assert args.response_manifest == batch_runner.DEFAULT_FULL_RESPONSE_MANIFEST
    assert args.state == batch_runner.DEFAULT_FULL_STATE
    assert args.batch_manifest_dir == batch_runner.DEFAULT_FULL_BATCH_MANIFEST_DIR
    assert args.progress_dir == batch_runner.DEFAULT_FULL_PROGRESS_DIR
    assert args.output_dir == batch_runner.DEFAULT_FULL_OUTPUT_DIR
    assert args.public_manifest == batch_runner.DEFAULT_FULL_PUBLIC_MANIFEST


def test_source_response_count_preserves_declared_3908_queue_items(tmp_path: Path) -> None:
    manifest = tmp_path / "regeneration-full-responses.json"
    _write_json(
        manifest,
        {
            "responseCount": 3908,
            "responses": [
                {"id": "one", "text": "One."},
                {"id": "two", "text": "Two."},
            ],
        },
    )

    assert batch_runner.source_response_count(manifest, fallback_total=2) == 3908


def test_build_precompute_command_passes_space_and_bucket_args(tmp_path: Path) -> None:
    args = _build_args(tmp_path)

    command = batch_runner.build_precompute_command(
        args,
        manifest=tmp_path / "batch-manifests" / "batch.json",
        progress=tmp_path / "progress" / "batch.progress.json",
        offset=4,
        remaining_seconds=30,
    )

    assert command[command.index("--space-url") + 1] == "https://publicus-indextts-2-demo.hf.space"
    assert command[command.index("--bucket-uri") + 1] == "hf://buckets/Publicus/abby-voice/test-phase"
    assert command[command.index("--model-name") + 1] == "Publicus/IndexTTS-2-Demo"
    assert "--require-upload-capable-batch" in command
    assert "--require-batch" in command
    assert command[command.index("--offset") + 1] == "4"


def test_build_precompute_command_omits_runtime_limit_when_unbounded(tmp_path: Path) -> None:
    args = _build_args(tmp_path, max_runtime_seconds=0.0)

    command = batch_runner.build_precompute_command(
        args,
        manifest=tmp_path / "batch-manifests" / "batch.json",
        progress=tmp_path / "progress" / "batch.progress.json",
        offset=4,
        remaining_seconds=None,
    )

    assert "--max-runtime-seconds" not in command


def test_runtime_deadline_is_unbounded_for_non_positive_values() -> None:
    assert batch_runner.runtime_deadline(100.0, 0.0) is None
    assert batch_runner.runtime_deadline(100.0, -1.0) is None
    assert batch_runner.runtime_deadline(100.0, None) is None
    assert batch_runner.runtime_deadline(100.0, 30.0) == 130.0


def test_space_queue_failed_without_details_is_retryable() -> None:
    assert batch_runner.is_retryable_failure_message("RuntimeError: Space queue failed: {'error': None}") is True


def test_main_resumes_valid_existing_checkpoint_by_default(monkeypatch, tmp_path: Path) -> None:
    args = _build_args(tmp_path)
    _write_json(
        args.state,
        {
            "schemaVersion": 1,
            "totalResponses": 4,
            "nextOffset": 2,
            "batchesCompleted": 1,
            "failures": 0,
        },
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(batch_runner, "parse_args", lambda: args)
    monkeypatch.setattr(batch_runner, "total_response_count", lambda response_manifest, dag, results: 4)

    def fake_run(command: list[str], cwd: Path) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(batch_runner.subprocess, "run", fake_run)

    exit_code = batch_runner.main()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert exit_code == batch_runner.EXIT_SUCCESS
    assert len(calls) == 1
    assert calls[0][calls[0].index("--offset") + 1] == "2"
    assert state["nextOffset"] == 4
    assert state["batchesCompleted"] == 2
    assert state["runIdentity"]["spaceUrl"] == "https://publicus-indextts-2-demo.hf.space"


def test_reset_state_explicitly_restarts_from_requested_offset(monkeypatch, tmp_path: Path) -> None:
    args = _build_args(tmp_path, reset_state=True)
    _write_json(
        args.state,
        {
            "totalResponses": 2,
            "nextOffset": 2,
            "batchesCompleted": 1,
            "failures": 0,
        },
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(batch_runner, "parse_args", lambda: args)
    monkeypatch.setattr(batch_runner, "total_response_count", lambda response_manifest, dag, results: 2)
    monkeypatch.setattr(
        batch_runner.subprocess,
        "run",
        lambda command, cwd: calls.append(command) or SimpleNamespace(returncode=0),
    )

    assert batch_runner.main() == batch_runner.EXIT_SUCCESS
    assert calls[0][calls[0].index("--offset") + 1] == "0"


def test_resume_rejects_checkpoint_for_different_response_total(monkeypatch, tmp_path: Path) -> None:
    args = _build_args(tmp_path)
    _write_json(
        args.state,
        {
            "totalResponses": 3,
            "nextOffset": 2,
        },
    )
    monkeypatch.setattr(batch_runner, "parse_args", lambda: args)
    monkeypatch.setattr(batch_runner, "total_response_count", lambda response_manifest, dag, results: 4)

    try:
        batch_runner.main()
    except RuntimeError as exc:
        assert "--reset-state" in str(exc)
    else:
        raise AssertionError("Expected incompatible checkpoint to fail closed")


def test_main_retries_transient_manifest_failures_before_advancing_offset(monkeypatch, tmp_path: Path) -> None:
    args = _build_args(tmp_path)
    manifest_path = args.batch_manifest_dir / "batch-00000-offset-000000.json"
    progress_path = args.progress_dir / "batch-00000-offset-000000.progress.json"
    calls: list[list[str]] = []
    sleeps: list[float] = []

    monkeypatch.setattr(batch_runner, "parse_args", lambda: args)
    monkeypatch.setattr(batch_runner, "total_response_count", lambda response_manifest, dag, results: 2)
    monkeypatch.setattr(batch_runner.time, "sleep", lambda seconds: sleeps.append(seconds))

    def fake_run(command: list[str], cwd: Path) -> SimpleNamespace:
        calls.append(command)
        if len(calls) == 1:
            _write_json(
                manifest_path,
                {
                    "responses": [
                        {
                            "status": "failed",
                            "error": "RuntimeError: IndexTTS queue failed: {'title': 'ZeroGPU worker error'}",
                        },
                        {
                            "status": "failed",
                            "error": "RuntimeError: IndexTTS queue failed: {'title': 'ZeroGPU worker error'}",
                        },
                    ]
                },
            )
        else:
            _write_json(
                manifest_path,
                {
                    "responses": [
                        {"status": "generated"},
                        {"status": "generated"},
                    ]
                },
            )
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text("{}", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(batch_runner.subprocess, "run", fake_run)

    exit_code = batch_runner.main()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert exit_code == batch_runner.EXIT_SUCCESS
    assert len(calls) == 2
    assert sleeps == [0.1]
    assert state["nextOffset"] == 2
    assert state["batchesCompleted"] == 1


def test_main_stops_without_advancing_offset_when_failures_persist(monkeypatch, tmp_path: Path) -> None:
    args = _build_args(tmp_path)
    manifest_path = args.batch_manifest_dir / "batch-00000-offset-000000.json"
    progress_path = args.progress_dir / "batch-00000-offset-000000.progress.json"
    calls: list[list[str]] = []

    monkeypatch.setattr(batch_runner, "parse_args", lambda: args)
    monkeypatch.setattr(batch_runner, "total_response_count", lambda response_manifest, dag, results: 2)
    monkeypatch.setattr(batch_runner.time, "sleep", lambda seconds: None)

    def fake_run(command: list[str], cwd: Path) -> SimpleNamespace:
        calls.append(command)
        _write_json(
            manifest_path,
            {
                "responses": [
                    {
                        "status": "failed",
                        "error": "RuntimeError: IndexTTS queue failed: {'title': 'ZeroGPU worker error'}",
                    },
                    {
                        "status": "failed",
                        "error": "RuntimeError: IndexTTS queue failed: {'title': 'ZeroGPU worker error'}",
                    },
                ]
            },
        )
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text("{}", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(batch_runner.subprocess, "run", fake_run)

    exit_code = batch_runner.main()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert exit_code == batch_runner.EXIT_BATCH_FAILED
    assert len(calls) == 2
    assert state["nextOffset"] == 0
    assert state["batchesCompleted"] == 0
    assert "ZeroGPU worker error" in state["stopReason"]


def test_main_returns_runtime_limit_when_deadline_expires(monkeypatch, tmp_path: Path) -> None:
    args = _build_args(tmp_path, max_runtime_seconds=1.0)
    time_values = iter([100.0, 101.5, 101.5, 101.5])

    monkeypatch.setattr(batch_runner, "parse_args", lambda: args)
    monkeypatch.setattr(batch_runner, "total_response_count", lambda response_manifest, dag, results: 2)
    monkeypatch.setattr(batch_runner.time, "time", lambda: next(time_values))

    exit_code = batch_runner.main()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert exit_code == batch_runner.EXIT_RUNTIME_LIMIT
    assert state["nextOffset"] == 0
    assert "Reached runtime deadline" in state["stopReason"]
