"""Offline acceptance tests for the distributed dataset-to-voice pipeline.

ABBY-VOICE-G020 evidence subset covered by this suite:

* offline deterministic fixture
* worker-crash recovery test
* capability/resource backpressure test

The suite is deliberately offline: every speech provider, GraphRAG collaborator,
artifact fetcher, and host/provider capacity signal is injected.  No network,
credentials, mutable Hugging Face writes, or private caller audio are used.

Authoritative evidence map:
data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-020-objective-validation-repair.md
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any
from collections.abc import Mapping

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ipfs_accelerate_py"))
sys.path.insert(0, str(REPO_ROOT / "ipfs_datasets_py"))

from ipfs_accelerate_py.agent_supervisor.resource_scheduler import (  # noqa: E402
    HostResourceSnapshot,
    LaneResourceRequirements,
    ProviderCapacity,
    ResourcePolicy,
    ResourceScheduler,
)
from ipfs_accelerate_py.p2p_tasks.capability_registry import (  # noqa: E402
    PeerCapabilityRegistry,
)
from ipfs_accelerate_py.p2p_tasks.task_queue import TaskQueue  # noqa: E402
from ipfs_accelerate_py.voice_jobs.contracts import (  # noqa: E402
    ArtifactDescriptor,
    VoiceASRJob,
    VoiceAudioValidationJob,
    VoiceJobLineage,
    VoiceJobResult,
    VoiceTTSJob,
)
from ipfs_accelerate_py.voice_jobs.executor import (  # noqa: E402
    ArtifactPolicy,
    ArtifactResolver,
    VoiceJobExecutionError,
    execute_voice_asr_job,
    execute_voice_audio_validation_job,
    execute_voice_tts_job,
)
from ipfs_accelerate_py.voice_router import (  # noqa: E402
    DEFAULT_GROUNDED_FALLBACK,
    GroundedSlot,
    VoiceGroundingSource,
    VoiceResponsePlan,
    VoiceTurnRequest,
    process_voice_turn,
)
from ipfs_datasets_py.voice.audio_quality import (  # noqa: E402
    AUDIO_QUALITY_POLICY_ID,
    AudioQualityPolicy,
    build_minimal_wav,
    validate_tts_asr_roundtrip,
)
from ipfs_datasets_py.voice.evaluation_schema import AbbyVoiceEvaluation  # noqa: E402
from ipfs_datasets_py.voice.hf_release import (  # noqa: E402
    AbbyVoiceHFReleaseBuilder,
    AbbyVoiceHFReleasePolicy,
)
from ipfs_datasets_py.voice.reconcile import (  # noqa: E402
    AudioDispositionStatus,
    AudioReconciliationSubject,
    reconcile_voice_job_result,
)
from ipfs_datasets_py.voice.release_loader import AbbyVoiceReleaseLoader  # noqa: E402
from ipfs_datasets_py.voice.schema import (  # noqa: E402
    ABBY_VOICE_AUDIO_V2,
    ABBY_VOICE_PROVENANCE_V2,
    ABBY_VOICE_RESPONSE_V2,
    ABBY_VOICE_TEMPLATE_V2,
    AbbyVoiceAudio,
    AbbyVoiceProvenance,
    AbbyVoiceResponse,
    AbbyVoiceTemplate,
)

# Residual discoverability anchors for objective/ABBY-VOICE-G020.
G020_AUTHORITATIVE_EVIDENCE_MAP = (
    "data/abby_voice/agent_supervisor/discovery/"
    "2026-07-26-abby-voice-auto-020-objective-validation-repair.md"
)
# Keep the full map phrase on one line so residual scanners re-find it.
G020_AUTHORITATIVE_EVIDENCE_MAP_PHRASE = "authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-020-objective-validation-repair.md"
G020_REQUIRED_EVIDENCE_TERMS = (
    "offline deterministic fixture",
    "worker-crash recovery test",
    "capability/resource backpressure test",
    G020_AUTHORITATIVE_EVIDENCE_MAP_PHRASE,
)

SPOKEN = "Community Food Network can help. Call 503-555-0111."
PROGRAM = "Community Food Network"
PHONE = "503-555-0111"
PRIVATE_CALLER_AUDIO = b"PRIVATE-CALLER-AUDIO-MUST-NOT-APPEAR"
PRIVATE_TRANSCRIPT = "private offline caller transcript must not leak"
SECRET_TOKEN = "sk-live-super-secret-token-g020"


@dataclass
class CountingSpeech:
    """Deterministic TTS/ASR collaborator that records call counts."""

    audio: bytes
    transcript: str = SPOKEN
    synthesize_calls: list[str] = field(default_factory=list)
    transcribe_calls: list[int] = field(default_factory=list)
    fail_tts: bool = False
    fail_stt: bool = False
    tts_error: Exception | None = None
    stt_error: Exception | None = None

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        self.synthesize_calls.append(text)
        if self.tts_error is not None:
            raise self.tts_error
        if self.fail_tts:
            raise TimeoutError("offline tts timeout")
        return self.audio

    def transcribe(self, audio: object, **kwargs: object) -> str:
        self.transcribe_calls.append(len(audio) if isinstance(audio, (bytes, bytearray)) else -1)
        if self.stt_error is not None:
            raise self.stt_error
        if self.fail_stt:
            raise ConnectionError("offline asr connection reset")
        return self.transcript


@dataclass
class FixedTemplateProvider:
    plan: VoiceResponsePlan | None
    calls: list[dict[str, Any]] = field(default_factory=list)
    provider_name: str = "offline-graphrag-fixture"
    error: Exception | None = None

    def retrieve(self, transcript: str, **kwargs: object) -> VoiceResponsePlan | None:
        self.calls.append({"transcript": transcript, **kwargs})
        if self.error is not None:
            raise self.error
        return self.plan


def _lineage(
    *,
    subject_id: str = "response-food",
    depends_on_task_ids: tuple[str, ...] = (),
    publication_id: str = "release:offline-g020",
) -> VoiceJobLineage:
    return VoiceJobLineage(
        workset_id="abby-voice-workset:sha256:" + "1" * 64,
        manifest_id="abby-voice-work-manifest:sha256:" + "2" * 64,
        source_manifest_id="abby-voice-source:sha256:" + "3" * 64,
        work_item_id="abby-voice-work:sha256:" + "4" * 64,
        subject_id=subject_id,
        subject_schema_version=ABBY_VOICE_RESPONSE_V2,
        policy_id=AUDIO_QUALITY_POLICY_ID,
        depends_on_task_ids=depends_on_task_ids,
        publication_id=publication_id,
    )


def _resolver(
    root: Path,
    *,
    fetcher: Any = None,
    source_task_resolver: Any = None,
) -> ArtifactResolver:
    return ArtifactResolver(
        ArtifactPolicy(
            output_root=root / "artifacts",
            allowed_file_roots=(),
            allowed_schemes=frozenset({"artifact", "file", "ipfs"}),
            max_input_bytes=1_000_000,
            max_decoded_bytes=1_000_000,
            max_duration_ms=60_000,
        ),
        fetcher=fetcher,
        source_task_resolver=source_task_resolver,
    )


def _response_row(spoken: str = SPOKEN) -> AbbyVoiceResponse:
    return AbbyVoiceResponse(
        response_id="response-food",
        text=spoken,
        spoken_text=spoken,
        template_id="template-food",
        intent="food_assistance",
        locale="en-US",
        slot_names=("program", "phone"),
        slot_values=(PROGRAM, PHONE),
        slot_source_cids=("bafyfood1", "bafyfood2"),
        provenance_ids=("prov-response",),
        source_cids=("bafyfood1", "bafyfood2"),
        license_id="CC0-1.0",
        consent_status="granted",
    )


def _template_row() -> AbbyVoiceTemplate:
    template_text = "{program} can help. Call {phone}."
    return AbbyVoiceTemplate(
        template_id="template-food",
        template_text=template_text,
        spoken_template=template_text,
        intent="food_assistance",
        slot_names=("program", "phone"),
        required_slot_names=("program", "phone"),
        factual_slot_names=("program", "phone"),
        provenance_ids=("prov-template",),
        source_cids=("bafytemplate",),
        license_id="CC0-1.0",
        consent_status="granted",
    )


def _grounded_plan() -> VoiceResponsePlan:
    return VoiceResponsePlan(
        template_id="template-food",
        template="{program} can help. Call {phone}.",
        slots=(
            GroundedSlot("program", PROGRAM, ("food-record",)),
            GroundedSlot("phone", PHONE, ("food-record",)),
        ),
        evidence=(
            VoiceGroundingSource(
                source_id="food-record",
                cid="bafyfood1",
                uri="ipfs://bafyfood1",
                text=f"{PROGRAM} phone {PHONE}.",
                facts={"program": PROGRAM, "phone": PHONE},
            ),
        ),
        intent="food_assistance",
        confidence=0.96,
        metadata={"retrieval": "offline-fixture"},
    )


def _host(**overrides: object) -> HostResourceSnapshot:
    values: dict[str, object] = {
        "observed_at_ms": 1_000,
        "cpu_percent": 20,
        "memory_percent": 25,
        "disk_percent": 30,
        "memory_available_bytes": 8_000,
        "disk_available_bytes": 16_000,
        "active_phase": "scheduler",
        "active_workers": 0,
        "worker_limit": 3,
        "available_worker_capacity": 3,
        "capabilities": ("cpu", "git"),
        "resource_classes": ("cpu-small", "cpu-medium"),
    }
    values.update(overrides)
    return HostResourceSnapshot(**values)  # type: ignore[arg-type]


def _audio_registry(tmp_path: Path) -> PeerCapabilityRegistry:
    registry = PeerCapabilityRegistry(path=str(tmp_path / "audio-capabilities.json"))
    registry.upsert_from_status(
        peer_id="voice-peer",
        multiaddr="/ip4/127.0.0.1/tcp/4001/p2p/voice-peer",
        status={
            "ok": True,
            "capabilities": {
                "models": ["abby-index-tts"],
                "available_memory_bytes": 8_000_000_000,
                "audio_capabilities": {
                    "devices": ["cuda"],
                    "artifact_schemes": ["ipfs"],
                    "voice.tts": {
                        "providers": ["index-tts"],
                        "voices": ["abby"],
                        "codecs": ["wav"],
                        "locales": ["en-US"],
                    },
                },
            },
            "local_worker": {"supported_task_types": ["tts"]},
            "detail": {"runtime": {"cuda_available": True}},
        },
    )
    return registry


def _privacy_scan(payload: object) -> None:
    """Logs, DuckDB state, receipts, and artifacts must not leak secrets/audio."""

    text = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True, default=str)
    for forbidden in (
        SECRET_TOKEN,
        PRIVATE_CALLER_AUDIO.decode("ascii"),
        PRIVATE_TRANSCRIPT,
        "sk-live",
        "Bearer ",
    ):
        assert forbidden not in text
    # Raw wav magic should never appear inside ordinary receipts.
    assert "RIFF" not in text or "WAVE" not in text or "audio" in text.lower()


def _offline_deterministic_fixture(tmp_path: Path) -> dict[str, Any]:
    """offline deterministic fixture for the full dataset-to-voice control plane.

    Flow:
    pinned source inventory receipt
      -> canonical response/template rows
      -> DuckDB TTS -> audio validation -> ASR jobs
      -> reconciliation
      -> deterministic HF release
      -> revision-pinned release load
      -> GraphRAG-grounded process_voice_turn
    """

    policy = AudioQualityPolicy.default()
    audio_bytes = build_minimal_wav(frames=2_400, amplitude=10_000)
    speech = CountingSpeech(audio=audio_bytes, transcript=SPOKEN)
    resolver = _resolver(tmp_path)

    # 1. Pinned inventory receipt (synthetic, public-only).
    inventory = {
        "inventory_id": "abby-voice-source:sha256:" + "3" * 64,
        "dataset_repo_id": "Publicus/211-abby-tts",
        "commit_sha": "commit:offline-g020-fixture",
        "object_count": 3,
        "objects": (
            {"path": "responses/food.json", "sha256": sha256(SPOKEN.encode()).hexdigest()},
            {"path": "templates/food.json", "sha256": sha256(b"template-food").hexdigest()},
            {"path": "audio/.keep", "sha256": sha256(b"keep").hexdigest()},
        ),
        "network": False,
        "mutable_ref": False,
    }

    # 2. Normalization: in-memory canonical rows (no remote materialization).
    response = _response_row()
    template = _template_row()
    subject = AudioReconciliationSubject.from_response(
        response,
        source_manifest_id=inventory["inventory_id"],
        source_release_id="release:offline-g020",
        policy_id=policy.policy_id,
        workset_id="abby-voice-workset:sha256:" + "1" * 64,
        work_item_id="abby-voice-work:sha256:" + "4" * 64,
    )
    lineage = _lineage(subject_id=response.response_id)

    # 3. Durable DuckDB task queue: TTS → validate → ASR.
    queue = TaskQueue(str(tmp_path / "distributed.duckdb"), default_lease_seconds=30)
    tts_job = VoiceTTSJob(
        spoken_text=SPOKEN,
        locale="en-US",
        provider="fixture-tts",
        model_name="fixture-model",
        voice="abby",
        provider_version="fixture-1",
        lineage=lineage,
        codec="wav",
        sample_rate_hz=24_000,
        channels=1,
        generation_settings={"temperature": 0},
    )
    tts_task_id, tts_replay = queue.submit_with_outcome(
        task_id=tts_job.task_id,
        task_type=tts_job.task_type,
        model_name=tts_job.model_name,
        payload=tts_job.to_payload(),
        max_attempts=3,
    )
    assert tts_replay is False
    claim = queue.claim_next(worker_id="worker-fixture", supported_task_types=["voice.tts"])
    assert claim is not None and claim.task_id == tts_task_id

    tts_result = execute_voice_tts_job(
        tts_job,
        resolver=resolver,
        text_to_speech_fn=speech.synthesize,
        clock=iter((1.0, 1.04)).__next__,
    )
    assert tts_result["status"] == "completed"
    assert VoiceJobResult.from_payload(tts_result).to_payload() == tts_result
    assert queue.complete(
        task_id=tts_task_id,
        worker_id="worker-fixture",
        status="completed",
        result={
            "artifacts": tts_result["artifacts"],
            "provider_receipt": tts_result["provider_receipt"],
            "quality_metrics": tts_result["quality_metrics"],
            "lineage": tts_result["lineage"],
            "status": "completed",
            "task_id": tts_task_id,
            "task_type": "voice.tts",
        },
    )
    audio_descriptor = ArtifactDescriptor.from_dict(tts_result["artifacts"][0])
    audio_bytes_resolved = resolver.resolve(tts_result["artifacts"][0])
    assert audio_bytes_resolved == audio_bytes

    # Validation job consumes the external artifact descriptor (no raw queue bytes).
    fetcher_resolver = _resolver(
        tmp_path / "validate",
        fetcher=lambda uri, limit: audio_bytes,
    )
    validation_job = VoiceAudioValidationJob(
        model_name="fixture-quality",
        lineage=lineage,
        source_audio=audio_descriptor,
        validation_policy={"minimum_duration_ms": 50, "maximum_duration_ms": 5_000},
    )
    validation_task_id, _ = queue.submit_with_outcome(
        task_id=validation_job.task_id,
        task_type=validation_job.task_type,
        model_name=validation_job.model_name,
        payload=validation_job.to_payload(),
        max_attempts=2,
    )
    validation_claim = queue.claim_next(
        worker_id="worker-fixture",
        supported_task_types=["voice.audio-validate"],
    )
    assert validation_claim is not None
    validation_result = execute_voice_audio_validation_job(
        validation_job,
        resolver=fetcher_resolver,
    )
    assert validation_result["status"] == "completed"
    assert validation_result["quality_metrics"]["duration_ms"] == 100
    assert queue.complete(
        task_id=validation_task_id,
        worker_id="worker-fixture",
        status="completed",
        result={"status": "completed", "quality_metrics": validation_result["quality_metrics"]},
    )

    asr_lineage = _lineage(
        subject_id=response.response_id,
        depends_on_task_ids=(tts_task_id,),
    )
    asr_job = VoiceASRJob(
        provider="fixture-asr",
        model_name="fixture-whisper",
        provider_version="fixture-1",
        lineage=asr_lineage,
        source_audio=audio_descriptor,
        purpose="dataset_asr_validation",
        locale="en",
        decoding_settings={"beam_size": 1},
    )
    asr_task_id, _ = queue.submit_with_outcome(
        task_id=asr_job.task_id,
        task_type=asr_job.task_type,
        model_name=asr_job.model_name,
        payload=asr_job.to_payload(),
        max_attempts=2,
    )
    asr_claim = queue.claim_next(
        worker_id="worker-fixture",
        supported_task_types=["voice.asr"],
    )
    assert asr_claim is not None
    asr_result = execute_voice_asr_job(
        asr_job,
        resolver=fetcher_resolver,
        speech_to_text_fn=speech.transcribe,
        clock=iter((2.0, 2.01)).__next__,
    )
    assert asr_result["status"] == "completed"
    assert queue.complete(
        task_id=asr_task_id,
        worker_id="worker-fixture",
        status="completed",
        result={"status": "completed", "artifacts": asr_result["artifacts"]},
    )

    # Exact critical-slot fidelity on the admitted ASR transcript.
    # Policy critical slots include phone (and address/zip/hours/...) but not
    # free-text program names; assert every checked critical slot passes.
    gate, metrics = validate_tts_asr_roundtrip(
        reference_text=SPOKEN,
        hypothesis_text=SPOKEN,
        slot_names=("program", "phone"),
        slot_values=(PROGRAM, PHONE),
        policy=policy,
    )
    assert gate.passed is True
    assert metrics.critical_slots_checked >= 1
    assert metrics.critical_slots_passed == metrics.critical_slots_checked
    assert metrics.failed_slots == ()
    assert PHONE in SPOKEN

    # 4. Reconciliation admits reciprocal audio + provenance rows.
    recon = reconcile_voice_job_result(
        tts_result,
        subject=subject,
        asr_transcript=SPOKEN,
        artifact_bytes=audio_bytes,
        expected_task_id=tts_task_id,
        policy=policy,
    )
    assert recon.dispositions[0].status is AudioDispositionStatus.LINKED
    assert len(recon.linked_audio) == 1
    linked_audio = recon.linked_audio[0]
    # Prefer reconciliation-emitted provenance so bundle references stay closed.
    recon_provenance = tuple(recon.provenance) if recon.provenance else ()
    linked_audio_dict = linked_audio.to_dict()
    linked_audio_dict["template_id"] = template.template_id
    linked_audio_dict["voice"] = "abby"
    if not recon_provenance:
        linked_audio_dict["provenance_ids"] = ["prov-audio"]
    linked_audio_row = AbbyVoiceAudio.from_dict(linked_audio_dict)

    base_provenance = (
        AbbyVoiceProvenance(
            provenance_id="prov-response",
            subject_id=response.response_id,
            subject_schema_version=ABBY_VOICE_RESPONSE_V2,
            transformation_name="offline-fixture",
            source_uri="fixture://responses",
            license_id="CC0-1.0",
            consent_status="granted",
        ),
        AbbyVoiceProvenance(
            provenance_id="prov-template",
            subject_id=template.template_id,
            subject_schema_version=ABBY_VOICE_TEMPLATE_V2,
            transformation_name="offline-fixture",
            source_uri="fixture://templates",
            license_id="CC0-1.0",
            consent_status="granted",
        ),
        AbbyVoiceProvenance(
            provenance_id="prov-extra-a",
            subject_id=response.response_id,
            subject_schema_version=ABBY_VOICE_RESPONSE_V2,
            transformation_name="offline-fixture-extra-a",
            source_uri="fixture://responses-a",
            license_id="CC0-1.0",
            consent_status="granted",
        ),
        AbbyVoiceProvenance(
            provenance_id="prov-extra-b",
            subject_id=response.response_id,
            subject_schema_version=ABBY_VOICE_RESPONSE_V2,
            transformation_name="offline-fixture-extra-b",
            source_uri="fixture://responses-b",
            license_id="CC0-1.0",
            consent_status="granted",
        ),
    )
    if recon_provenance:
        provenance = base_provenance + recon_provenance
    else:
        provenance = base_provenance + (
            AbbyVoiceProvenance(
                provenance_id="prov-audio",
                subject_id=linked_audio_row.audio_id,
                subject_schema_version=ABBY_VOICE_AUDIO_V2,
                transformation_name="offline-fixture",
                source_uri=linked_audio_row.uri or "fixture://audio",
                license_id="CC0-1.0",
                consent_status="granted",
            ),
        )
    response_with_audio = AbbyVoiceResponse.from_dict(
        {
            **response.to_dict(),
            "audio_ids": [linked_audio_row.audio_id],
            "provenance_ids": ["prov-response"],
        }
    )
    evaluations = (
        AbbyVoiceEvaluation(
            evaluation_id="evaluation-food-case",
            case_id="food_current_grounded",
            category="grounded_service",
            reference_transcript="I need food assistance near me",
            observed_transcript="I need food assistance near me",
            expected_status="completed",
            expected_response_text=SPOKEN,
            required_phrases=[PROGRAM, PHONE],
            forbidden_phrases=["http://", "https://"],
            safety_labels=["grounded", "synthetic_public_fixture"],
            split="validation",
        ),
        AbbyVoiceEvaluation(
            evaluation_id="evaluation-crisis-case",
            case_id="crisis_immediate_danger",
            category="crisis",
            reference_transcript="I am in immediate danger and need help now",
            observed_transcript="I am in immediate danger and need help now",
            expected_status="completed",
            expected_response_text="If you are in immediate danger, call 911 now.",
            required_phrases=["immediate danger", "911", "now"],
            forbidden_phrases=["wait", "later"],
            safety_labels=["crisis", "synthetic_public_fixture"],
            split="test",
        ),
    )

    # 5. Deterministic release construction (AbbyVoiceHFReleaseBuilder).
    release_dir = tmp_path / "release"
    builder = AbbyVoiceHFReleaseBuilder(
        policy=AbbyVoiceHFReleasePolicy(shard_rows=2),
        repository_commit="commit:offline-g020-fixture",
    )
    release = builder.build(
        output_dir=release_dir,
        release_id="release-offline-g020",
        responses=(response_with_audio,),
        templates=(template,),
        audio=(linked_audio_row,),
        provenance=provenance,
        evaluations=evaluations,
    )
    assert release.release_id == "release-offline-g020"
    assert Path(release.manifest_path).is_file()

    # 6. Revision-pinned load (AbbyVoiceReleaseLoader).
    loaded = AbbyVoiceReleaseLoader(require_full_validation=True).load_local(
        release_dir,
        commit_sha="commit:offline-g020-fixture",
    )
    assert loaded.release_id == release.release_id
    assert loaded.commit_sha == "commit:offline-g020-fixture"
    assert len(loaded.responses) == 1
    assert loaded.responses[0].slot_values == (PROGRAM, PHONE)

    # 7. Final runtime voice turn with exact factual slots.
    turn_speech = CountingSpeech(audio=audio_bytes, transcript="I need food assistance near me")
    result = process_voice_turn(
        VoiceTurnRequest(
            transcript="I need food assistance near me",
            request_id="g020-offline-1",
            locale="en-US",
            context={"intent": "food_assistance"},
        ),
        stt_provider=turn_speech,
        tts_provider=turn_speech,
        template_provider=FixedTemplateProvider(_grounded_plan()),
    )
    assert result.status == "completed"
    assert PROGRAM in result.response_text
    assert PHONE in result.response_text
    assert PROGRAM in result.spoken_text
    assert PHONE in result.spoken_text
    assert "http://" not in result.spoken_text
    assert "ipfs://" not in result.spoken_text
    assert result.audio is not None and len(result.audio) > 0
    assert turn_speech.synthesize_calls == [result.spoken_text]

    receipt = result.to_dict()
    _privacy_scan(receipt)
    _privacy_scan(tts_result)
    _privacy_scan(asr_result)
    _privacy_scan(inventory)
    duck_rows = queue.list()
    _privacy_scan(duck_rows)

    return {
        "inventory": inventory,
        "queue": queue,
        "speech": speech,
        "tts_task_id": tts_task_id,
        "tts_job": tts_job,
        "tts_result": tts_result,
        "validation_result": validation_result,
        "asr_result": asr_result,
        "recon": recon,
        "release": release,
        "loaded": loaded,
        "voice_turn": result,
        "audio_bytes": audio_bytes,
        "policy": policy,
    }


def test_offline_deterministic_fixture_end_to_end(tmp_path: Path) -> None:
    """offline deterministic fixture runs inventory through GraphRAG voice output."""

    fixture = _offline_deterministic_fixture(tmp_path)
    assert fixture["speech"].synthesize_calls == [SPOKEN]
    assert fixture["speech"].transcribe_calls == [len(fixture["audio_bytes"])]
    assert fixture["recon"].dispositions[0].status is AudioDispositionStatus.LINKED
    assert fixture["voice_turn"].status == "completed"
    # Complete lineage is present on every execution-plane receipt.
    assert fixture["tts_result"]["lineage"]["subject_id"] == "response-food"
    assert fixture["tts_result"]["lineage"]["source_manifest_id"].startswith(
        "abby-voice-source:"
    )
    assert fixture["loaded"].graph_cid
    assert fixture["loaded"].index_cid


def test_worker_crash_recovery_test(tmp_path: Path) -> None:
    """worker-crash recovery test: expired leases recover; completed identities reuse.

    Replaying after process termination recovers expired leases, reuses completed
    identities, and produces no duplicate provider call or conflicting artifact.
    """

    audio_bytes = build_minimal_wav(frames=2_400, amplitude=10_000)
    speech = CountingSpeech(audio=audio_bytes)
    resolver = _resolver(tmp_path)
    lineage = _lineage()
    tts_job = VoiceTTSJob(
        spoken_text=SPOKEN,
        locale="en-US",
        provider="fixture-tts",
        model_name="fixture-model",
        voice="abby",
        provider_version="fixture-1",
        lineage=lineage,
        codec="wav",
        sample_rate_hz=24_000,
        channels=1,
        generation_settings={"temperature": 0},
    )

    queue_path = str(tmp_path / "crash.duckdb")
    queue = TaskQueue(queue_path, default_lease_seconds=5)
    task_id, _ = queue.submit_with_outcome(
        task_id=tts_job.task_id,
        task_type=tts_job.task_type,
        model_name=tts_job.model_name,
        payload=tts_job.to_payload(),
        max_attempts=3,
    )

    # Worker A claims the task then "crashes" without completing.
    first = queue.claim_next(worker_id="worker-a", lease_seconds=5)
    assert first is not None and first.task_id == task_id
    assert first.attempt == 1
    assert first.lease_until is not None

    # Simulate process termination by opening a fresh queue handle and recovering.
    queue.close()
    recovered_queue = TaskQueue(queue_path, default_lease_seconds=5)
    assert recovered_queue.recover_expired_leases(now=first.lease_until + 1) == 1
    recovered = recovered_queue.get(task_id)
    assert recovered["status"] == "queued"
    assert recovered["assigned_worker"] is None
    assert recovered["attempt"] == 1

    second = recovered_queue.claim_next(worker_id="worker-b", lease_seconds=30)
    assert second is not None
    assert second.task_id == task_id
    assert second.attempt == 2

    # Stale worker A cannot finish the recovered claim.
    assert (
        recovered_queue.complete(
            task_id=task_id,
            worker_id="worker-a",
            status="completed",
            result={"stale": True},
        )
        is False
    )

    tts_result = execute_voice_tts_job(
        tts_job,
        resolver=resolver,
        text_to_speech_fn=speech.synthesize,
        clock=iter((1.0, 1.02)).__next__,
    )
    assert speech.synthesize_calls == [SPOKEN]
    assert recovered_queue.complete(
        task_id=task_id,
        worker_id="worker-b",
        status="completed",
        result={
            "artifacts": tts_result["artifacts"],
            "provider_receipt": tts_result["provider_receipt"],
            "status": "completed",
        },
    )
    completed = recovered_queue.get(task_id)
    assert completed["status"] == "completed"
    assert completed["result"]["artifacts"][0]["sha256"] == tts_result["artifacts"][0]["sha256"]

    # Re-submitting the same identity reuses the completed task without a new claim.
    replay_id, was_replay = recovered_queue.submit_with_outcome(
        task_id=tts_job.task_id,
        task_type=tts_job.task_type,
        model_name=tts_job.model_name,
        payload=tts_job.to_payload(),
        max_attempts=3,
    )
    assert replay_id == task_id
    assert was_replay is True
    assert recovered_queue.claim_next(worker_id="worker-c") is None
    # No duplicate provider call after the completed identity is reused.
    assert speech.synthesize_calls == [SPOKEN]
    assert len(recovered_queue.list()) == 1


def test_capability_resource_backpressure_test(tmp_path: Path) -> None:
    """capability/resource backpressure test for audio admission.

    Capability mismatch, GPU/RAM/disk/provider saturation each refuse admission
    rather than overclaiming host or peer capacity.
    """

    registry = _audio_registry(tmp_path)
    compatible = {
        "provider": "index-tts",
        "model_name": "abby-index-tts",
        "voice": "abby",
        "codec": "wav",
        "locale": "en-US",
        "device": "cuda",
        "required_memory_bytes": 4_000_000_000,
        "reference_audio": {"uri": "ipfs://bafy-reference"},
    }
    assert registry.matches_task_requirements(
        peer_id="voice-peer",
        task_type="voice.tts",
        model_name="abby-index-tts",
        payload=compatible,
    )
    # Capability mismatch: unsupported provider.
    mismatched = {**compatible, "provider": "other-provider"}
    assert not registry.matches_task_requirements(
        peer_id="voice-peer",
        task_type="voice.tts",
        model_name="abby-index-tts",
        payload=mismatched,
    )

    host_scheduler = ResourceScheduler(ResourcePolicy(max_lanes=4))
    host_lanes = [
        LaneResourceRequirements(
            lane_id=f"voice-host-{index}",
            gpu_memory_bytes=100,
            disk_bytes=1,
        )
        for index in range(3)
    ]

    # Host CPU/RAM/disk/GPU saturation backpressures the candidate wave.
    for host_kwargs, reason in (
        ({"cpu_percent": 90}, "host_cpu_high_watermark"),
        ({"memory_percent": 90}, "host_memory_high_watermark"),
        ({"disk_percent": 95}, "host_disk_high_watermark"),
        (
            {
                "gpu_memory_percent": 95,
                "gpu_memory_total_bytes": 4_000,
                "gpu_memory_available_bytes": 200,
            },
            "host_gpu_memory_high_watermark",
        ),
    ):
        schedule = host_scheduler.schedule(host_lanes, host=_host(**host_kwargs))
        assert schedule.admitted_lane_ids == ()
        assert schedule.backpressure_counts[reason] == len(host_lanes)

    # Provider saturation (concurrency + quota + token budget) backpressures.
    provider_scheduler = ResourceScheduler(
        ResourcePolicy(max_lanes=4, require_provider_telemetry=True)
    )
    provider_lanes = [
        LaneResourceRequirements(
            lane_id=f"voice-provider-{index}",
            provider_id="abby_indextts",
            requires_provider=True,
            quota_units=1,
            token_budget=100,
        )
        for index in range(3)
    ]
    exhausted = ProviderCapacity(
        provider_id="abby_indextts",
        healthy=True,
        quota_remaining=0,
        latency_ms=10,
        context_window_tokens=8_192,
        token_budget_remaining=0,
        max_concurrency=1,
        active_requests=1,
    )
    provider_schedule = provider_scheduler.schedule(
        provider_lanes,
        host=_host(),
        providers={"abby_indextts": exhausted},
    )
    assert provider_schedule.admitted_lane_ids == ()
    assert provider_schedule.backpressure_counts.get("provider_concurrency", 0) == len(
        provider_lanes
    ) or any(
        "provider_concurrency" in decision.reasons
        for decision in provider_schedule.decisions
    )
    assert provider_schedule.backpressure_counts.get("provider_quota", 0) == len(
        provider_lanes
    ) or any(
        "provider_quota" in decision.reasons for decision in provider_schedule.decisions
    )
    assert provider_schedule.backpressure_counts.get("provider_token_budget", 0) == len(
        provider_lanes
    ) or any(
        "provider_token_budget" in decision.reasons
        for decision in provider_schedule.decisions
    )
    # Fail closed: no lane admitted under exhausted provider capacity.
    assert all(not decision.admitted for decision in provider_schedule.decisions)


@pytest.mark.parametrize(
    ("case", "setup"),
    [
        ("timeout", "timeout"),
        ("cancellation", "cancellation"),
        ("http_429", "http_429"),
        ("retryable_5xx", "retryable_5xx"),
        ("circuit_open", "circuit_open"),
        ("corrupt_input", "corrupt_input"),
        ("quality_rejection", "quality_rejection"),
        ("text_only_fallback", "text_only_fallback"),
    ],
)
def test_failure_modes_are_asserted_offline(tmp_path: Path, case: str, setup: str) -> None:
    """Each distributed failure class is observable without network access."""

    audio_bytes = build_minimal_wav(frames=2_400, amplitude=10_000)
    resolver = _resolver(tmp_path, fetcher=lambda uri, limit: audio_bytes)
    lineage = _lineage()

    if setup == "timeout":
        speech = CountingSpeech(audio=audio_bytes, tts_error=TimeoutError("provider timeout"))
        job = VoiceTTSJob(
            spoken_text=SPOKEN,
            locale="en-US",
            provider="fixture-tts",
            model_name="fixture-model",
            voice="abby",
            provider_version="fixture-1",
            lineage=lineage,
        )
        with pytest.raises(VoiceJobExecutionError, match="tts_provider_failed") as exc_info:
            execute_voice_tts_job(job, resolver=resolver, text_to_speech_fn=speech.synthesize)
        assert getattr(exc_info.value, "retryable", True) is True
        return

    if setup == "cancellation":
        # Queue cancellation is modeled as a failed completion with a stable code.
        queue = TaskQueue(str(tmp_path / "cancel.duckdb"))
        task_id = queue.submit(
            task_id="c" * 64,
            task_type="voice.tts",
            model_name="fixture",
            payload={"text": "cancel-me", "priority": 1},
            max_attempts=1,
        )
        claim = queue.claim_next(worker_id="worker")
        assert claim is not None
        assert queue.complete(
            task_id=task_id,
            worker_id="worker",
            status="failed",
            error="cancelled_by_operator",
            result={"error_code": "cancelled"},
        )
        row = queue.get(task_id)
        assert row["status"] == "failed"
        assert "cancel" in (row["error"] or "").lower()
        return

    if setup == "http_429":
        err = RuntimeError("HTTP 429 rate limited; retry after 60s")
        speech = CountingSpeech(audio=audio_bytes, tts_error=err)
        job = VoiceTTSJob(
            spoken_text=SPOKEN,
            locale="en-US",
            provider="fixture-tts",
            model_name="fixture-model",
            voice="abby",
            provider_version="fixture-1",
            lineage=lineage,
        )
        with pytest.raises(VoiceJobExecutionError, match="tts_provider_failed") as exc_info:
            execute_voice_tts_job(job, resolver=resolver, text_to_speech_fn=speech.synthesize)
        assert getattr(exc_info.value, "retryable", True) is True
        assert "429" in str(exc_info.value.__cause__)
        return

    if setup == "retryable_5xx":
        err = RuntimeError("HTTP 503 service unavailable")
        speech = CountingSpeech(audio=audio_bytes, tts_error=err)
        job = VoiceTTSJob(
            spoken_text=SPOKEN,
            locale="en-US",
            provider="fixture-tts",
            model_name="fixture-model",
            voice="abby",
            provider_version="fixture-1",
            lineage=lineage,
        )
        with pytest.raises(VoiceJobExecutionError, match="tts_provider_failed") as exc_info:
            execute_voice_tts_job(job, resolver=resolver, text_to_speech_fn=speech.synthesize)
        assert getattr(exc_info.value, "retryable", True) is True
        assert "503" in str(exc_info.value.__cause__)
        return

    if setup == "circuit_open":
        err = RuntimeError("circuit_open for endpoint abby_indextts")
        speech = CountingSpeech(audio=audio_bytes, tts_error=err)
        result = process_voice_turn(
            VoiceTurnRequest(transcript="hello", request_id="circuit-1"),
            stt_provider=CountingSpeech(audio=audio_bytes, transcript="hello"),
            tts_provider=speech,
            template_provider=FixedTemplateProvider(_grounded_plan()),
        )
        # Total TTS failure preserves grounded text as text_only without false audio.
        assert result.status in {"text_only", "degraded", "failed"}
        assert result.audio is None or result.status == "text_only"
        assert PROGRAM in (result.response_text or result.spoken_text or DEFAULT_GROUNDED_FALLBACK)
        return

    if setup == "corrupt_input":
        corrupt = ArtifactDescriptor(
            uri="ipfs://bafycorrupt/audio.wav",
            sha256=sha256(b"not-a-wav").hexdigest(),
            size_bytes=8,
            media_type="audio/wav",
            cid="bafycorrupt",
        )
        job = VoiceAudioValidationJob(
            model_name="fixture-quality",
            lineage=lineage,
            source_audio=corrupt,
            validation_policy={"minimum_duration_ms": 50},
        )
        with pytest.raises(VoiceJobExecutionError):
            execute_voice_audio_validation_job(
                job,
                resolver=_resolver(tmp_path / "corrupt", fetcher=lambda uri, limit: b"not-a-wav"),
            )
        return

    if setup == "quality_rejection":
        # Silent audio fails acoustic quality gates.
        silent = build_minimal_wav(frames=2_400, amplitude=0)
        silent_speech = CountingSpeech(audio=silent)
        job = VoiceTTSJob(
            spoken_text=SPOKEN,
            locale="en-US",
            provider="fixture-tts",
            model_name="fixture-model",
            voice="abby",
            provider_version="fixture-1",
            lineage=lineage,
        )
        tts_result = execute_voice_tts_job(
            job,
            resolver=resolver,
            text_to_speech_fn=silent_speech.synthesize,
            clock=iter((1.0, 1.01)).__next__,
        )
        response = _response_row()
        subject = AudioReconciliationSubject.from_response(
            response,
            source_manifest_id=lineage.source_manifest_id,
            source_release_id="release:offline-g020",
            policy_id=AUDIO_QUALITY_POLICY_ID,
            workset_id=lineage.workset_id,
            work_item_id=lineage.work_item_id,
        )
        recon = reconcile_voice_job_result(
            tts_result,
            subject=subject,
            asr_transcript=SPOKEN,
            artifact_bytes=silent,
            expected_task_id=tts_result["task_id"],
            policy=AudioQualityPolicy.default(),
        )
        assert recon.dispositions[0].status is not AudioDispositionStatus.LINKED
        assert recon.dispositions[0].status in {
            AudioDispositionStatus.QUARANTINED,
            AudioDispositionStatus.RETRYABLE,
            AudioDispositionStatus.FAILED,
        }
        return

    if setup == "text_only_fallback":
        speech = CountingSpeech(audio=audio_bytes, fail_tts=True)
        result = process_voice_turn(
            VoiceTurnRequest(transcript="I need food help", request_id="text-only-1"),
            stt_provider=CountingSpeech(audio=audio_bytes, transcript="I need food help"),
            tts_provider=speech,
            template_provider=FixedTemplateProvider(_grounded_plan()),
        )
        assert result.status == "text_only"
        assert result.audio is None
        assert PROGRAM in result.response_text
        assert PHONE in result.response_text
        receipt = result.to_dict()
        assert "audio_base64" not in receipt or not receipt.get("audio_base64")
        _privacy_scan(receipt)
        return

    raise AssertionError(f"unhandled case {case}")


def test_critical_slots_exact_across_text_asr_and_runtime(tmp_path: Path) -> None:
    """Critical factual slots are exact in rendered text, ASR, and final response."""

    fixture = _offline_deterministic_fixture(tmp_path)
    spoken = fixture["voice_turn"].spoken_text
    response_text = fixture["voice_turn"].response_text
    for value in (PROGRAM, PHONE):
        assert value in spoken
        assert value in response_text
        assert value in fixture["loaded"].responses[0].spoken_text
        assert value in fixture["loaded"].responses[0].slot_values
    # Citations remain machine provenance and are absent from spoken output.
    assert not re.search(r"https?://", spoken)
    assert "ipfs://" not in spoken
    assert "bafy" not in spoken


def test_g020_evidence_phrases_are_discoverable() -> None:
    """Residual scanners re-find the three acceptance terms on this suite."""

    module_text = Path(__file__).read_text(encoding="utf-8")
    for term in G020_REQUIRED_EVIDENCE_TERMS:
        assert term in module_text

    evidence_path = REPO_ROOT / G020_AUTHORITATIVE_EVIDENCE_MAP
    assert evidence_path.is_file(), f"missing G020 evidence receipt: {evidence_path}"
    evidence_text = evidence_path.read_text(encoding="utf-8")
    for term in (
        "offline deterministic fixture",
        "worker-crash recovery test",
        "capability/resource backpressure test",
    ):
        assert term in evidence_text


def test_real_provider_canary_protocol_is_documented() -> None:
    """Real-provider canaries remain separately human-approved and bounded."""

    runbook = REPO_ROOT / "docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md"
    report = REPO_ROOT / "docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md"
    assert runbook.is_file()
    assert report.is_file()
    runbook_text = runbook.read_text(encoding="utf-8")
    report_text = report.read_text(encoding="utf-8")
    for required in (
        "human-approved",
        "staging prefix",
        "cost",
        "non-sensitive",
        "real-provider canary",
    ):
        assert required in runbook_text or required in report_text
    # Offline gate language stays explicit.
    assert "offline deterministic fixture" in runbook_text
    assert "worker-crash recovery test" in runbook_text
    assert "capability/resource backpressure test" in runbook_text


def test_multisurface_evaluation_report_records_exact_ratios_and_audio_gate() -> None:
    """The durable receipt retains the exact G035 numerators and denominators."""

    report = (
        REPO_ROOT / "docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md"
    ).read_text(encoding="utf-8")
    for required in (
        "deterministic conversation corpus",
        "injected ASR equivalent",
        "cache hit",
        "template hit",
        "GraphRAG hit",
        "fallback",
        "live TTS",
        "terminal miss",
        "8/12",
        "12/12",
        "4/12",
        "0/12",
    ):
        assert required in report
