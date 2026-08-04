"""Offline tests for Abby action audio staging + exact resolver (VOICE-ACTION-025)."""

from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.stage_abby_action_audio import (
    DEFAULT_FRAMES_PATH,
    REQUIRED_ROLES,
    RESOLVER_FILENAME,
    SMOKE_SYNTHESIS_IDENTITY,
    SOURCE_LABEL,
    TASK_ID,
    StageError,
    build_offline_resolver,
    build_resolver_row,
    load_frame_records,
    load_resolver_rows,
    load_staged_audio_bytes,
    resolve_all_staged_rows,
    select_pilot_frames,
    spoken_text_sha256,
    stage_action_audio,
    synthesize_fixture_wav,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STAGE_SCRIPT = REPO_ROOT / "scripts" / "stage_abby_action_audio.py"

from ipfs_accelerate_py.voice_audio_resolver import (  # noqa: E402
    REASON_EXACT_MATCH,
    REASON_SPOKEN_TEXT_MISMATCH,
    REASON_STALE_SLOT_INVALIDATED,
    SynthesisIdentity,
    spoken_text_sha256 as runtime_spoken_text_sha256,
)


def _identity_from_row(row: dict) -> SynthesisIdentity:
    return SynthesisIdentity(
        provider=str(row["provider"]),
        model=str(row["model"]),
        voice=str(row["voice"]),
        provider_version=str(row["provider_version"]),
        locale=str(row["locale"]),
        codec=str(row["codec"]),
        sample_rate_hz=int(row["sample_rate_hz"]),
        channels=int(row["channels"]),
        generation_settings=dict(row.get("generation_settings") or {}),
    )


def test_speech_frame_corpus_exists_for_staging() -> None:
    assert DEFAULT_FRAMES_PATH.is_file(), f"missing frames corpus: {DEFAULT_FRAMES_PATH}"
    frames = load_frame_records(DEFAULT_FRAMES_PATH)
    selected = select_pilot_frames(frames)
    assert len(selected) == 40
    roles_by_action: dict[str, set[str]] = {}
    for row in selected:
        roles_by_action.setdefault(str(row["logical_action"]), set()).add(str(row["role"]))
    assert len(roles_by_action) == 10
    for action, roles in roles_by_action.items():
        assert roles == set(REQUIRED_ROLES), action


def test_fixture_wav_is_deterministic_and_nonempty() -> None:
    text = "I opened the requested app screen."
    first = synthesize_fixture_wav(text)
    second = synthesize_fixture_wav(text)
    assert first == second
    assert first[:4] == b"RIFF"
    assert len(first) > 44
    other = synthesize_fixture_wav("Okay, I will not open that app screen.")
    assert sha256(first).hexdigest() != sha256(other).hexdigest()


def test_spoken_text_sha_aligns_with_runtime_resolver() -> None:
    text = "I created the calendar reminder."
    assert spoken_text_sha256(text) == runtime_spoken_text_sha256(text)


def test_smoke_stage_produces_resolver_rows_for_pilot_confirm_outcome(
    tmp_path: Path,
) -> None:
    stage_root = tmp_path / "action-audio-smoke"
    summary = stage_action_audio(
        frames_path=DEFAULT_FRAMES_PATH,
        stage_root=stage_root,
        smoke=True,
    )
    assert summary["complete"] is True
    assert summary["row_count"] == 40
    assert summary["logical_action_count"] == 10
    assert summary["confirm_count"] == 10
    assert summary["outcome_count"] == 30
    assert set(summary["roles"]) == set(REQUIRED_ROLES)

    resolver_path = Path(summary["resolver_path"])
    assert resolver_path.is_file()
    assert resolver_path.name == RESOLVER_FILENAME
    rows = load_resolver_rows(resolver_path)
    assert len(rows) == 40

    seen_frames: set[str] = set()
    for row in rows:
        assert row["schema"].startswith("voice-action/")
        assert row["task_id"] == TASK_ID
        assert row["source"] == SOURCE_LABEL
        assert row["role"] in REQUIRED_ROLES
        assert row["frame_id"]
        assert row["spoken_text"]
        assert row["content_sha256"]
        assert row["text_sha256"] == spoken_text_sha256(row["spoken_text"])
        assert row["template_id"] == row["frame_id"]
        assert row["metadata"]["audio_status"] == "staged"
        assert row["metadata"]["smoke_fixture"] is True
        assert row["metadata"]["dataset_audio_path"].startswith("audio/action/")
        audio_path = stage_root / row["metadata"]["dataset_audio_path"]
        assert audio_path.is_file()
        payload = audio_path.read_bytes()
        assert sha256(payload).hexdigest() == row["content_sha256"]
        seen_frames.add(str(row["frame_id"]))

    # Full pilot confirm + outcome coverage.
    assert len(seen_frames) == 40
    for action in summary["logical_actions"]:
        assert f"frame.action.confirm.{action}.v1" in seen_frames
        assert f"frame.action.outcome.{action}.success.v1" in seen_frames
        assert f"frame.action.outcome.{action}.denied.v1" in seen_frames
        assert f"frame.action.outcome.{action}.failed.v1" in seen_frames


def test_offline_resolver_exact_match_succeeds_for_staged_rows(
    tmp_path: Path,
) -> None:
    stage_root = tmp_path / "action-audio-resolver"
    summary = stage_action_audio(
        frames_path=DEFAULT_FRAMES_PATH,
        stage_root=stage_root,
        smoke=True,
    )
    rows = load_resolver_rows(Path(summary["resolver_path"]))
    by_sha, by_id = load_staged_audio_bytes(stage_root, rows)
    assert len(by_sha) == 40
    assert len(by_id) == 40

    resolver = build_offline_resolver(stage_root)
    assert resolver.artifact_count == 40

    for row in rows:
        identity = _identity_from_row(row)
        resolution = resolver.resolve(
            str(row["spoken_text"]),
            identity,
            template_id=str(row["template_id"]),
        )
        assert resolution.hit is True
        assert resolution.reason == REASON_EXACT_MATCH
        assert resolution.audio is not None
        assert sha256(resolution.audio).hexdigest() == row["content_sha256"]
        assert resolution.artifact is not None
        assert resolution.artifact.audio_id == row["audio_id"]
        assert resolution.artifact.spoken_text_sha256 == row["text_sha256"]

    hits = resolve_all_staged_rows(stage_root)
    assert len(hits) == 40
    assert all(item["status"] == "hit" for item in hits)
    assert all(item["reason"] == REASON_EXACT_MATCH for item in hits)


def test_offline_resolver_misses_on_spoken_text_mismatch(tmp_path: Path) -> None:
    stage_root = tmp_path / "action-audio-miss"
    summary = stage_action_audio(
        frames_path=DEFAULT_FRAMES_PATH,
        stage_root=stage_root,
        smoke=True,
    )
    rows = load_resolver_rows(Path(summary["resolver_path"]))
    resolver = build_offline_resolver(stage_root)
    sample = rows[0]
    identity = _identity_from_row(sample)

    # Unknown template id → pure spoken-text miss (not stale-slot).
    plain_miss = resolver.resolve(
        "This spoken text was never staged for action audio.",
        identity,
    )
    assert plain_miss.hit is False
    assert plain_miss.reason == REASON_SPOKEN_TEXT_MISMATCH

    # Known frame/template id with different text → stale-slot invalidation.
    stale = resolver.resolve(
        "This spoken text was never staged for action audio.",
        identity,
        template_id=str(sample["template_id"]),
    )
    assert stale.hit is False
    assert stale.reason == REASON_STALE_SLOT_INVALIDATED


def test_build_resolver_row_requires_frame_identity() -> None:
    audio = synthesize_fixture_wav("hello")
    with pytest.raises(StageError, match="frame_id and spoken_text"):
        build_resolver_row(
            frame={"spoken_text": ""},
            audio_bytes=audio,
            dataset_audio_path="audio/action/x.wav",
        )


def test_smoke_cli_exits_zero_and_writes_resolver(tmp_path: Path) -> None:
    stage_root = tmp_path / "cli-smoke"
    result = subprocess.run(
        [
            sys.executable,
            str(STAGE_SCRIPT),
            "--smoke",
            "--stage-root",
            str(stage_root),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert TASK_ID in result.stdout
    assert "resolver rows" in result.stdout or "wrote" in result.stdout
    assert "exact-match OK" in result.stdout
    resolver = stage_root / "metadata" / RESOLVER_FILENAME
    assert resolver.is_file()
    rows = [
        json.loads(line)
        for line in resolver.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 40
    # Smoke identity is stable and distinct from production IndexTTS defaults.
    assert rows[0]["provider"] == SMOKE_SYNTHESIS_IDENTITY["provider"]
