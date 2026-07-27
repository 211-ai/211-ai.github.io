from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipfs_datasets_py.huggingface.bucket import (
    HuggingFaceBucketListing,
    HuggingFaceBucketListingObject,
)
from ipfs_datasets_py.voice.dataset_merge import (
    ABBY_VOICE_NORMALIZED_BUILD_SCHEMA_VERSION,
)
from ipfs_datasets_py.voice.normalize import (
    NORMALIZATION_VERSION,
    QUALITY_REPORT_VERSION,
)
from ipfs_datasets_py.voice.reconcile import (
    AudioDisposition,
    AudioDispositionReason,
    AudioDispositionStatus,
    AudioReconciliationResult,
)
from ipfs_datasets_py.voice.release_loader import AbbyVoiceReleaseLoader
from ipfs_datasets_py.voice.schema import (
    ABBY_VOICE_AUDIO_V2,
    AbbyVoiceAudio,
    AbbyVoiceProvenance,
    stable_audio_id,
    stable_provenance_id,
)
from scripts import reconcile_abby_voice_bucket_audio as recovery


def _source_row(text: str) -> dict[str, object]:
    legacy_hash = sha256(" ".join(text.split()).encode()).hexdigest()[:20]
    return {
        "id": f"abby-tts-{legacy_hash}",
        "textHash": legacy_hash,
        "text": text,
        "originalTexts": [text],
        "routes": ["referral"],
        "sourceIds": ["document-one"],
    }


def _fixture_plan() -> tuple[
    dict[str, object],
    str,
    HuggingFaceBucketListing,
    recovery.NormalizationResult,
    recovery.AbbyVoiceBucketAudioPlan,
]:
    source = _source_row("Call 211 now for help.")
    manifest = {"responses": [source]}
    source_bytes = json.dumps(manifest, sort_keys=True).encode()
    source_digest = sha256(source_bytes).hexdigest()
    path = (
        "runs/abby-full-preprocess-20260622T152102Z/phase4-residual/audio/"
        f"abby-tts-{source['textHash']}.mp3"
    )
    listing = HuggingFaceBucketListing(
        bucket_id="Publicus/abby-voice",
        objects=(
            HuggingFaceBucketListingObject(
                path=path,
                size_bytes=123,
                xet_hash="a" * 64,
                media_type="audio/mpeg",
            ),
        ),
    )
    normalized, plan = recovery.build_recovery_plan(
        source_manifest=manifest,
        source_sha256=source_digest,
        listing=listing,
        source_uri=f"fixture://source@sha256:{source_digest}",
    )
    return manifest, source_digest, listing, normalized, plan


def _write_fixture(
    tmp_path: Path,
    *,
    update_latest: bool = True,
) -> tuple[
    dict[str, object],
    str,
    HuggingFaceBucketListing,
    recovery.NormalizationResult,
    recovery.AbbyVoiceBucketAudioPlan,
    dict[str, object],
]:
    manifest, source_digest, listing, normalized, plan = _fixture_plan()
    result = recovery.write_plan_artifacts(
        output_dir=tmp_path,
        source_sha256=source_digest,
        listing=listing,
        normalization=normalized,
        plan=plan,
        update_latest=update_latest,
    )
    return manifest, source_digest, listing, normalized, plan, result


def _canonical_jsonl(values: tuple[object, ...]) -> bytes:
    return b"".join(
        (
            json.dumps(
                value.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        for value in values
    )


def _write_normalized_release_fixture(
    tmp_path: Path,
) -> tuple[Path, str, recovery.NormalizationResult]:
    *_unused, normalized, _plan = _fixture_plan()
    root = tmp_path / "normalized"
    row_counts = {
        "audio.jsonl": len(normalized.audio),
        "duplicate-ledger.jsonl": 0,
        "provenance.jsonl": len(normalized.provenance),
        "quarantine.jsonl": 0,
        "responses.jsonl": len(normalized.responses),
        "templates.jsonl": len(normalized.templates),
        "warnings.jsonl": 0,
    }
    artifacts = {
        "audio.jsonl": _canonical_jsonl(normalized.audio),
        "duplicate-ledger.jsonl": b"",
        "provenance.jsonl": _canonical_jsonl(normalized.provenance),
        "quality-report.json": recovery._json_bytes(
            {
                "accepted": {
                    "audio": len(normalized.audio),
                    "provenance": len(normalized.provenance),
                    "responses": len(normalized.responses),
                    "templates": len(normalized.templates),
                },
                "input_record_count": normalized.input_record_count,
                "normalization_version": NORMALIZATION_VERSION,
                "schema_version": QUALITY_REPORT_VERSION,
                "source_manifest_count": normalized.source_manifest_count,
            }
        ),
        "quarantine.jsonl": b"",
        "responses.jsonl": _canonical_jsonl(normalized.responses),
        "splits.json": recovery._json_bytes(dict(normalized.splits)),
        "templates.jsonl": _canonical_jsonl(normalized.templates),
        "warnings.jsonl": b"",
    }
    manifest = {
        "deterministic": True,
        "files": [
            {
                "byte_length": len(content),
                "path": name,
                "sha256": sha256(content).hexdigest(),
                **(
                    {"row_count": row_counts[name]}
                    if name in row_counts
                    else {}
                ),
            }
            for name, content in sorted(artifacts.items())
        ],
        "input_record_count": normalized.input_record_count,
        "normalization_version": NORMALIZATION_VERSION,
        "schema_version": ABBY_VOICE_NORMALIZED_BUILD_SCHEMA_VERSION,
        "source_manifest_count": normalized.source_manifest_count,
    }
    root.mkdir()
    for name, content in artifacts.items():
        (root / name).write_bytes(content)
    manifest_bytes = recovery._json_bytes(manifest)
    (root / "manifest.json").write_bytes(manifest_bytes)
    return root, sha256(manifest_bytes).hexdigest(), normalized


def _write_admission_release_fixture(
    tmp_path: Path,
    *,
    normalized: recovery.NormalizationResult,
) -> tuple[Path, AudioReconciliationResult]:
    response = normalized.responses[0]
    content_sha256 = sha256(b"historical admitted audio").hexdigest()
    audio_id = stable_audio_id(content_sha256, segment_kind="response")
    source_uri = "ipfs://bafy-admitted-audio"
    provenance_id = stable_provenance_id(
        audio_id,
        source_uri,
        "reconcile_voice_job_result",
        content_sha256,
    )
    audio = AbbyVoiceAudio(
        audio_id=audio_id,
        spoken_text=response.spoken_text,
        content_sha256=content_sha256,
        response_id=response.response_id,
        uri=source_uri,
        segment_kind="response",
        mime_type="audio/mpeg",
        codec="mp3",
        byte_length=123,
        duration_ms=1000,
        sample_rate_hz=22050,
        channels=1,
        provenance_ids=(provenance_id,),
        license_id=response.license_id,
        consent_status=response.consent_status,
    )
    provenance = AbbyVoiceProvenance(
        provenance_id=provenance_id,
        subject_id=audio.audio_id,
        subject_schema_version=ABBY_VOICE_AUDIO_V2,
        transformation_name="reconcile_voice_job_result",
        transformation_version="1.0.0",
        source_uri=source_uri,
        source_revision="recovery:test",
        source_sha256=audio.content_sha256,
        locale=response.locale,
        license_id=response.license_id,
        consent_status=response.consent_status,
    )
    disposition = AudioDisposition(
        source_ref=f"voice-job:task-admit:{response.response_id}",
        source_sha256="d" * 64,
        status=AudioDispositionStatus.LINKED,
        reason=AudioDispositionReason.PROMOTED,
        subject_id=response.response_id,
        task_id="task-admit",
        work_item_id="work-admit",
        audio_id=audio.audio_id,
        artifact_sha256=audio.content_sha256,
        policy_identity="policy:legacy-bucket-audio",
    )
    admission = AudioReconciliationResult(
        linked_audio=(audio,),
        provenance=(provenance,),
        dispositions=(disposition,),
        policy_identity="policy:legacy-bucket-audio",
    )
    receipt = recovery.write_admission_artifacts(
        output_dir=tmp_path / "admission",
        recovery_id="recovery:test",
        revalidation_plan_id="revalidation:test",
        admission=admission,
    )
    return Path(receipt["output_dir"]), admission


def test_build_and_write_plan_artifacts_bind_source_listing_and_aliases(
    tmp_path: Path,
) -> None:
    (
        _manifest,
        _source_digest,
        listing,
        normalized,
        plan,
        result,
    ) = _write_fixture(tmp_path)
    plan_dir = tmp_path / plan.plan_id

    assert len(normalized.responses) == 1
    assert len(plan.aliases) == len(plan.selections) == 1
    assert plan.bucket_id == listing.bucket_id
    assert plan.listing_sha256 == listing.listing_sha256
    assert result["estimated_selected_bytes"] == 123
    assert result["output_dir"] == str(plan_dir.resolve())
    assert result["published"] is True
    assert result["idempotent"] is False
    persisted_listing = HuggingFaceBucketListing.from_json(
        (plan_dir / "bucket-listing.json").read_bytes()
    )
    persisted_plan = recovery.AbbyVoiceBucketAudioPlan.from_json(
        (plan_dir / "recovery-plan.json").read_bytes()
    )
    loaded_listing, loaded_plan = recovery.load_plan_artifacts(plan_dir)
    assert persisted_listing == listing
    assert persisted_plan == plan
    assert loaded_listing == listing
    assert loaded_plan == plan
    assert json.loads(
        (plan_dir / "recovery-plan-summary.json").read_text(encoding="utf-8")
    )["stage"] == "planned_unverified"


def test_plan_artifact_checksums_cover_every_payload_and_latest_pointer(
    tmp_path: Path,
) -> None:
    *_fixture, plan, result = _write_fixture(tmp_path)
    plan_dir = tmp_path / plan.plan_id
    manifest_path = plan_dir / recovery.PLAN_ARTIFACT_MANIFEST_NAME
    checksum_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert checksum_manifest["schema_version"] == (
        recovery.PLAN_ARTIFACT_MANIFEST_SCHEMA_VERSION
    )
    assert checksum_manifest["plan_id"] == plan.plan_id
    assert set(checksum_manifest["files"]) == {
        "bucket-audio-inventory.json",
        "bucket-audio-inventory.jsonl",
        "bucket-listing.json",
        "recovery-plan.json",
        "recovery-plan-summary.json",
    }
    assert set(path.name for path in plan_dir.iterdir()) == {
        *checksum_manifest["files"],
        recovery.PLAN_ARTIFACT_MANIFEST_NAME,
    }
    for name, metadata in checksum_manifest["files"].items():
        content = (plan_dir / name).read_bytes()
        assert metadata == {
            "byte_length": len(content),
            "sha256": sha256(content).hexdigest(),
        }

    manifest_bytes = manifest_path.read_bytes()
    assert result["checksum_manifest"] == {
        "path": str(manifest_path),
        "sha256": sha256(manifest_bytes).hexdigest(),
    }
    latest = json.loads(
        (tmp_path / recovery.LATEST_PLAN_POINTER_NAME).read_text(encoding="utf-8")
    )
    assert latest == {
        "schema_version": recovery.LATEST_PLAN_POINTER_SCHEMA_VERSION,
        "plan_id": plan.plan_id,
        "artifact_dir": plan.plan_id,
        "manifest": f"{plan.plan_id}/{recovery.PLAN_ARTIFACT_MANIFEST_NAME}",
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
    }


def test_rerunning_the_same_plan_is_idempotent_and_does_not_rewrite_files(
    tmp_path: Path,
) -> None:
    (
        _manifest,
        source_digest,
        listing,
        normalized,
        plan,
        first,
    ) = _write_fixture(tmp_path, update_latest=False)
    plan_path = tmp_path / plan.plan_id / "recovery-plan.json"
    inode_before = plan_path.stat().st_ino
    mtime_before = plan_path.stat().st_mtime_ns

    second = recovery.write_plan_artifacts(
        output_dir=tmp_path,
        source_sha256=source_digest,
        listing=listing,
        normalization=normalized,
        plan=plan,
        update_latest=False,
    )

    assert first["published"] is True
    assert first["idempotent"] is False
    assert second["published"] is False
    assert second["idempotent"] is True
    assert second["output_dir"] == first["output_dir"]
    assert plan_path.stat().st_ino == inode_before
    assert plan_path.stat().st_mtime_ns == mtime_before
    assert not (tmp_path / recovery.LATEST_PLAN_POINTER_NAME).exists()
    assert not list(tmp_path.glob(".*.partial"))


def test_existing_mismatched_plan_bundle_is_never_overwritten(
    tmp_path: Path,
) -> None:
    (
        _manifest,
        source_digest,
        listing,
        normalized,
        plan,
        _first,
    ) = _write_fixture(tmp_path, update_latest=False)
    plan_path = tmp_path / plan.plan_id / "recovery-plan.json"
    corrupt_bytes = b'{"tampered":true}\n'
    plan_path.write_bytes(corrupt_bytes)

    with pytest.raises(ValueError, match="immutable plan artifact mismatch"):
        recovery.write_plan_artifacts(
            output_dir=tmp_path,
            source_sha256=source_digest,
            listing=listing,
            normalization=normalized,
            plan=plan,
            update_latest=False,
        )

    assert plan_path.read_bytes() == corrupt_bytes
    assert not list(tmp_path.glob(".*.partial"))


def test_failed_staging_never_exposes_a_partial_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _manifest,
        source_digest,
        listing,
        normalized,
        plan,
    ) = _fixture_plan()
    original_write = recovery._write_new_file

    def fail_before_manifest(path: Path, content: bytes) -> None:
        if path.name == recovery.PLAN_ARTIFACT_MANIFEST_NAME:
            raise OSError("simulated staging failure")
        original_write(path, content)

    monkeypatch.setattr(recovery, "_write_new_file", fail_before_manifest)
    with pytest.raises(OSError, match="simulated staging failure"):
        recovery.write_plan_artifacts(
            output_dir=tmp_path,
            source_sha256=source_digest,
            listing=listing,
            normalization=normalized,
            plan=plan,
        )

    assert not (tmp_path / plan.plan_id).exists()
    assert not (tmp_path / recovery.LATEST_PLAN_POINTER_NAME).exists()
    assert not list(tmp_path.glob(".*.partial"))


def test_load_source_requires_the_exact_byte_pin(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"responses":[]}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        recovery._load_source(source, expected_sha256="0" * 64)


def test_stable_discovery_requires_identical_complete_views() -> None:
    *_unused, listing, _normalized, _plan = _fixture_plan()
    changed = recovery.HuggingFaceBucketListing(
        bucket_id=listing.bucket_id,
        objects=(
            *listing.objects,
            HuggingFaceBucketListingObject(
                path="runs/other/audio/abby-tts-00000000000000000000.mp3",
                size_bytes=1,
                xet_hash="b" * 64,
                media_type="audio/mpeg",
            ),
        ),
    )

    class Store:
        def __init__(self, values):
            self.values = iter(values)

        def discover(self, *, prefix: str):
            assert prefix == ""
            return next(self.values)

    assert recovery.discover_stable_listing(
        store=Store([listing, listing]),
        prefix="",
    ) == listing
    with pytest.raises(ValueError, match="was not stable"):
        recovery.discover_stable_listing(
            store=Store([listing, changed]),
            prefix="",
        )
    with pytest.raises(ValueError, match="at least two"):
        recovery.discover_stable_listing(
            store=Store([listing]),
            prefix="",
            passes=1,
        )


def test_ffprobe_adapter_requires_positive_audio_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temporary_paths: list[Path] = []

    def runner(command, **_kwargs):
        if command[1:] == ["-version"]:
            executable = Path(command[0]).name
            return SimpleNamespace(
                returncode=0,
                stdout=f"{executable} version fixture-1\n",
                stderr="",
            )
        if "-show_entries" not in command:
            temporary = Path(command[command.index("-i") + 1])
            temporary_paths.append(temporary)
            assert temporary.read_bytes() == b"fixture-audio"
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        temporary = Path(command[-1])
        temporary_paths.append(temporary)
        assert temporary.read_bytes() == b"fixture-audio"
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "codec_type": "audio",
                            "codec_name": "mp3",
                            "sample_rate": "24000",
                            "channels": 1,
                        }
                    ],
                    "format": {"duration": "1.25"},
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(
        recovery.shutil, "which", lambda value: f"/fixture/{value}"
    )
    probe = recovery.build_ffprobe_decode_probe(
        executable="fixture-ffprobe",
        runner=runner,
        temp_dir=tmp_path,
    )
    evidence = probe(b"fixture-audio", "audio/mpeg")

    assert evidence.passed is True
    assert evidence.probe_name == "ffprobe+ffmpeg"
    assert evidence.probe_version == (
        "fixture-ffprobe version fixture-1 | ffmpeg version fixture-1"
    )
    assert evidence.details["full_frame_decode"] is True
    assert evidence.details["duration_seconds"] == 1.25
    assert evidence.details["sample_rates_hz"] == [24000]
    assert temporary_paths and not temporary_paths[0].exists()


def test_recovery_artifacts_are_immutable_and_explicitly_pending_asr(
    tmp_path: Path,
) -> None:
    *_unused, listing, _normalized, plan = _fixture_plan()
    payload = b"ID3" + (b"\0" * 120)
    assert len(payload) == listing.objects[0].size_bytes

    class Client:
        def download_bucket_file(
            self,
            *,
            bucket_id: str,
            path: str,
            destination: Path,
            expected_xet_hash: str,
            expected_size_bytes: int,
        ) -> int:
            assert bucket_id == plan.bucket_id
            assert path == plan.selections[0].selected.path
            assert expected_xet_hash == "a" * 64
            assert expected_size_bytes == len(payload)
            return destination.write_bytes(payload)

    result = recovery.recover_abby_voice_bucket_audio(
        plan=plan,
        store=recovery.HuggingFaceBucketStore(plan.bucket_id, client=Client()),
        cache_dir=tmp_path / "cache",
        limit=1,
    )
    published = recovery.write_recovery_artifacts(
        output_dir=tmp_path / "runs",
        recovery=result,
    )
    output_dir = Path(published["output_dir"])
    summary = json.loads(
        (output_dir / "recovery-summary.json").read_text(encoding="utf-8")
    )

    assert published["published"] is True
    assert summary["publishable"] is False
    assert summary["stage"] == (
        "staged_pending_asr_and_critical_slot_validation"
    )
    assert summary["staged_pending_asr_count"] == 1
    assert (
        output_dir / "staging-candidates.pending-asr.jsonl"
    ).read_bytes()
    assert (output_dir / "failure-dispositions.jsonl").read_bytes() == b""
    assert recovery.write_recovery_artifacts(
        output_dir=tmp_path / "runs",
        recovery=result,
    )["idempotent"] is True
    assert recovery.load_recovery_artifacts(output_dir) == result

    inventory_path = output_dir / "verified-inventory.json"
    inventory_path.write_bytes(inventory_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum mismatch"):
        recovery.load_recovery_artifacts(output_dir)


def test_schedule_builds_asr_validation_plan_without_tts_or_inline_audio(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    *_unused, listing, _normalized, plan = _fixture_plan()
    payload = b"ID3" + (b"\0" * 120)

    class Client:
        def download_bucket_file(
            self,
            *,
            bucket_id: str,
            path: str,
            destination: Path,
            expected_xet_hash: str,
            expected_size_bytes: int,
        ) -> int:
            return destination.write_bytes(payload)

    cache_dir = tmp_path / "cache"
    recovered = recovery.recover_abby_voice_bucket_audio(
        plan=plan,
        store=recovery.HuggingFaceBucketStore(plan.bucket_id, client=Client()),
        cache_dir=cache_dir,
        limit=1,
        decode_probe=lambda _payload, _media: recovery.DecodeProbeEvidence(
            probe_name="ffmpeg",
            probe_version="fixture-1",
            passed=True,
            details={"full_frame_decode": True},
        ),
    )
    published = recovery.write_recovery_artifacts(
        output_dir=tmp_path / "recovery-runs",
        recovery=recovered,
    )

    exit_code = recovery.main(
        [
            "schedule",
            "--recovery-dir",
            published["output_dir"],
            "--cache-dir",
            str(cache_dir),
            "--artifact-root",
            str(tmp_path / "accelerator-artifacts"),
            "--output-dir",
            str(tmp_path / "revalidation-plans"),
        ]
    )
    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["tts_job_count"] == 0
    assert result["asr_job_count"] == 1
    assert result["audio_validation_job_count"] == 1
    assert result["publishable"] is False
    assert result["queue_submission"]["requested"] is False
    output_dir = Path(result["output_dir"])
    jobs = (output_dir / "voice-jobs.jsonl").read_text(encoding="utf-8")
    assert '"task_type":"voice.asr"' in jobs
    assert '"task_type":"voice.audio-validate"' in jobs
    assert '"task_type":"voice.tts"' not in jobs
    assert "file://" not in jobs
    assert "audio_bytes" not in jobs


def test_merge_release_builds_valid_reciprocally_linked_local_release(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    normalized_dir, manifest_sha256, normalized = (
        _write_normalized_release_fixture(tmp_path)
    )
    admission_dir, admission = _write_admission_release_fixture(
        tmp_path,
        normalized=normalized,
    )
    output_dir = tmp_path / "release"
    repository_commit = "commit:fixture-release"

    exit_code = recovery.main(
        [
            "merge-release",
            "--normalized-dir",
            str(normalized_dir),
            "--expected-normalized-manifest-sha256",
            manifest_sha256,
            "--admission-dir",
            str(admission_dir),
            "--output-dir",
            str(output_dir),
            "--release-id",
            "abby-voice-fixture-v1",
            "--repository-commit",
            repository_commit,
        ]
    )

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    linked_audio = admission.linked_audio[0]
    expected_parents = {
        f"abby-voice-normalized-build:sha256:{manifest_sha256}",
        admission.reconciliation_id,
        "recovery:test",
        "revalidation:test",
    }
    assert result["local_only"] is True
    assert result["remote_write_attempted"] is False
    assert result["published"] is False
    assert result["publication_status"] == "not_requested"
    assert result["output_dir"] == str(output_dir.resolve())
    assert result["release"]["output_dir"] == str(output_dir.resolve())
    assert result["release"]["manifest_path"] == str(
        output_dir.resolve() / "release-manifest.json"
    )
    assert result["release_validation"]["valid"] is True
    assert set(result["parent_source_ids"]) == expected_parents
    assert not list(tmp_path.glob(".*.partial"))

    loaded = AbbyVoiceReleaseLoader().load_local(
        output_dir,
        commit_sha=repository_commit,
    )
    loaded_response = next(
        item
        for item in loaded.responses
        if item.response_id == normalized.responses[0].response_id
    )
    assert loaded_response.audio_ids == (linked_audio.audio_id,)
    assert loaded.audio == (linked_audio,)
    assert loaded.graphrag_index.bundle.responses == loaded.responses
    assert loaded.graphrag_index.bundle.audio == loaded.audio

    release_manifest = json.loads(
        (output_dir / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert release_manifest["descriptors"]
    assert all(
        set(descriptor["parent_ids"]) == expected_parents
        for descriptor in release_manifest["descriptors"]
    )


def test_merge_release_rejects_resealed_tampered_admission_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    normalized_dir, manifest_sha256, normalized = (
        _write_normalized_release_fixture(tmp_path)
    )
    admission_dir, _admission = _write_admission_release_fixture(
        tmp_path,
        normalized=normalized,
    )
    linked_path = admission_dir / "linked-audio.jsonl"
    linked_path.write_bytes(b"")
    manifest_path = admission_dir / recovery.PLAN_ARTIFACT_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["linked-audio.jsonl"] = {
        "byte_length": 0,
        "sha256": sha256(b"").hexdigest(),
    }
    manifest_path.write_bytes(recovery._json_bytes(manifest))
    output_dir = tmp_path / "release"

    exit_code = recovery.main(
        [
            "merge-release",
            "--normalized-dir",
            str(normalized_dir),
            "--expected-normalized-manifest-sha256",
            manifest_sha256,
            "--admission-dir",
            str(admission_dir),
            "--output-dir",
            str(output_dir),
            "--release-id",
            "abby-voice-fixture-v1",
            "--repository-commit",
            "commit:fixture-release",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "derived artifacts do not match" in captured.err
    assert not output_dir.exists()
    assert not list(tmp_path.glob(".*.partial"))


def test_merge_release_rejects_tampered_normalized_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    normalized_dir, manifest_sha256, normalized = (
        _write_normalized_release_fixture(tmp_path)
    )
    admission_dir, _admission = _write_admission_release_fixture(
        tmp_path,
        normalized=normalized,
    )
    responses_path = normalized_dir / "responses.jsonl"
    responses_path.write_bytes(responses_path.read_bytes() + b" ")
    output_dir = tmp_path / "release"

    exit_code = recovery.main(
        [
            "merge-release",
            "--normalized-dir",
            str(normalized_dir),
            "--expected-normalized-manifest-sha256",
            manifest_sha256,
            "--admission-dir",
            str(admission_dir),
            "--output-dir",
            str(output_dir),
            "--release-id",
            "abby-voice-fixture-v1",
            "--repository-commit",
            "commit:fixture-release",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "artifact checksum mismatch: responses.jsonl" in captured.err
    assert not output_dir.exists()
    assert not list(tmp_path.glob(".*.partial"))


def test_merge_release_refuses_existing_output_without_modifying_it(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "release"
    output_dir.mkdir()
    marker = output_dir / "owned-by-caller.txt"
    marker.write_text("preserve me", encoding="utf-8")

    exit_code = recovery.main(
        [
            "merge-release",
            "--normalized-dir",
            str(tmp_path / "missing-normalized"),
            "--expected-normalized-manifest-sha256",
            "a" * 64,
            "--admission-dir",
            str(tmp_path / "missing-admission"),
            "--output-dir",
            str(output_dir),
            "--release-id",
            "abby-voice-fixture-v1",
            "--repository-commit",
            "commit:fixture-release",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "output directory must not already exist" in captured.err
    assert marker.read_text(encoding="utf-8") == "preserve me"
    assert {item.name for item in output_dir.iterdir()} == {marker.name}
    assert not list(tmp_path.glob(".*.partial"))
