#!/usr/bin/env python3
"""Stage or generate precomputed audio for Abby action speech frames.

VOICE-ACTION-025 / VOICE-ACTION-G120

Reads the pilot action speech-frame corpus (VOICE-ACTION-024) and stages
offline, content-addressed WAV fixtures plus exact-match resolver rows that
``PrecomputedVoiceAudioResolver`` can load without network, IndexTTS, or
ffmpeg.

Smoke mode covers every pilot confirm / success / deny / fail frame so the
offline resolver exact-match path is exercisable end-to-end.  Production HF
publish remains a separate gated task; this script only owns local staging
fixtures.

Usage:
  python scripts/stage_abby_action_audio.py --smoke
  python scripts/stage_abby_action_audio.py --smoke --stage-root /tmp/action-audio
"""

from __future__ import annotations

import argparse
import io
import json
import math
import struct
import sys
import unicodedata
import wave
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "ipfs_accelerate_py"
for _import_root in (REPO_ROOT, IPFS_ACCELERATE_ROOT):
    _path = str(_import_root)
    if _import_root.is_dir() and _path not in sys.path:
        sys.path.insert(0, _path)

TASK_ID: Final = "VOICE-ACTION-025"
SOURCE_LABEL: Final = "voice-action-025/abby-action-audio-smoke"
SCHEMA: Final = "voice-action/action-audio-resolver-row@1"
SCHEMA_VERSION: Final = "abby_action_audio_resolver_v1"

DEFAULT_FRAMES_REL: Final = "docs/phone_dialog_generation/action_speech_frames.jsonl"
DEFAULT_FRAMES_PATH = REPO_ROOT / DEFAULT_FRAMES_REL
DEFAULT_STAGE_REL: Final = "tmp_assets/abby-action-audio-smoke"
DEFAULT_STAGE_ROOT = REPO_ROOT / DEFAULT_STAGE_REL
RESOLVER_FILENAME: Final = "abby_action_precomputed_audio_resolver.jsonl"
SUMMARY_FILENAME: Final = "abby_action_audio_stage_summary.json"

# Required spoken roles for pilot confirm + outcome coverage.
REQUIRED_ROLES: Final[tuple[str, ...]] = ("confirm", "success", "deny", "fail")

# Shared synthesis identity for smoke fixtures. Exact-match resolution requires
# the same identity at resolve time; production IndexTTS rows may differ.
SMOKE_SYNTHESIS_IDENTITY: Final[dict[str, Any]] = {
    "provider": "abby_action_fixture",
    "model": "action-fixture-v1",
    "voice": "abby",
    "provider_version": "1.0.0",
    "locale": "en-US",
    "codec": "wav",
    "sample_rate_hz": 24_000,
    "channels": 1,
    "generation_settings": {
        "temperature": 0.0,
        "fixture": True,
        "task_id": TASK_ID,
    },
}

SAMPLE_RATE_HZ: Final = int(SMOKE_SYNTHESIS_IDENTITY["sample_rate_hz"])
CHANNELS: Final = int(SMOKE_SYNTHESIS_IDENTITY["channels"])
SAMPLE_WIDTH: Final = 2  # 16-bit PCM


class StageError(RuntimeError):
    """Fail-closed staging error."""


def normalize_spoken_text(text: str) -> str:
    """Match ``voice_audio_resolver`` spoken-text normalization (NFC + strip)."""

    value = unicodedata.normalize("NFC", str(text or ""))
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def spoken_text_sha256(spoken_text: str) -> str:
    """SHA-256 of normalized spoken text (matches voice_audio_resolver)."""

    # Prefer the runtime helper when available so fixture hashes stay aligned.
    try:
        from ipfs_accelerate_py.voice_audio_resolver import (  # type: ignore
            spoken_text_sha256 as _runtime_sha,
        )

        return str(_runtime_sha(spoken_text))
    except Exception:
        return sha256(normalize_spoken_text(spoken_text).encode("utf-8")).hexdigest()


def load_frame_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise StageError(f"missing action speech-frame corpus: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StageError(
                f"malformed speech-frame JSONL at line {line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise StageError(f"speech-frame row must be an object at line {line_number}")
        rows.append(payload)
    if not rows:
        raise StageError(f"speech-frame corpus is empty: {path}")
    return rows


def select_pilot_frames(
    frames: Sequence[Mapping[str, Any]],
    *,
    roles: Sequence[str] = REQUIRED_ROLES,
) -> list[dict[str, Any]]:
    """Return sorted pilot frames for the requested confirm/outcome roles."""

    role_set = set(roles)
    selected: list[dict[str, Any]] = []
    for row in frames:
        role = str(row.get("role") or "").strip()
        if role not in role_set:
            continue
        frame_id = str(row.get("frame_id") or "").strip()
        spoken = normalize_spoken_text(str(row.get("spoken_text") or ""))
        logical_action = str(row.get("logical_action") or "").strip()
        if not frame_id or not spoken or not logical_action:
            raise StageError(
                f"incomplete speech frame (frame_id={frame_id!r}, "
                f"logical_action={logical_action!r}, role={role!r})"
            )
        selected.append(dict(row))

    if not selected:
        raise StageError("no pilot confirm/outcome frames selected for staging")

    # Stable order: logical_action, then role order in REQUIRED_ROLES.
    role_rank = {role: index for index, role in enumerate(REQUIRED_ROLES)}
    selected.sort(
        key=lambda row: (
            str(row.get("logical_action") or ""),
            role_rank.get(str(row.get("role") or ""), 99),
            str(row.get("frame_id") or ""),
        )
    )
    return selected


def _fixture_tone_params(spoken_text: str) -> tuple[float, float]:
    """Derive a deterministic short tone from spoken text (offline, no TTS)."""

    digest = sha256(normalize_spoken_text(spoken_text).encode("utf-8")).digest()
    frequency_hz = 220.0 + float(digest[0] % 48) * 15.0  # 220–925 Hz
    duration_s = 0.08 + float(digest[1] % 40) * 0.002  # ~80–158 ms
    return frequency_hz, duration_s


def synthesize_fixture_wav(
    spoken_text: str,
    *,
    sample_rate_hz: int = SAMPLE_RATE_HZ,
    channels: int = CHANNELS,
) -> bytes:
    """Generate a deterministic 16-bit PCM WAV fixture for *spoken_text*.

    Audio is a short pure-tone stand-in so offline exact-match resolution can
    run without IndexTTS, Whisper, or ffmpeg.  Distinct spoken texts yield
    distinct digests (frequency/duration vary by text hash).
    """

    if sample_rate_hz <= 0:
        raise StageError("sample_rate_hz must be positive")
    if channels <= 0:
        raise StageError("channels must be positive")

    frequency_hz, duration_s = _fixture_tone_params(spoken_text)
    frame_count = max(1, int(sample_rate_hz * duration_s))
    amplitude = 0.28
    samples = bytearray()
    for index in range(frame_count):
        t = index / float(sample_rate_hz)
        # Soft attack/release to avoid pure DC clicks; still fully deterministic.
        envelope = 1.0
        attack = min(32, frame_count // 4)
        release = min(32, frame_count // 4)
        if index < attack:
            envelope = index / float(max(1, attack))
        elif index >= frame_count - release:
            envelope = (frame_count - index) / float(max(1, release))
        value = int(
            max(
                -32767,
                min(
                    32767,
                    round(
                        math.sin(2.0 * math.pi * frequency_hz * t)
                        * amplitude
                        * envelope
                        * 32767.0
                    ),
                ),
            )
        )
        frame = struct.pack("<h", value)
        samples.extend(frame * channels)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(bytes(samples))
    payload = buffer.getvalue()
    if not payload:
        raise StageError("fixture WAV synthesis produced empty bytes")
    return payload


def audio_relpath_for_frame(frame_id: str, content_sha256: str) -> str:
    safe_frame = "".join(
        ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in frame_id
    )
    short = content_sha256[:12]
    return f"audio/action/{safe_frame}.{short}.wav"


def build_resolver_row(
    *,
    frame: Mapping[str, Any],
    audio_bytes: bytes,
    dataset_audio_path: str,
    synthesis_identity: Mapping[str, Any] | None = None,
    smoke_fixture: bool = True,
) -> dict[str, Any]:
    identity = dict(synthesis_identity or SMOKE_SYNTHESIS_IDENTITY)
    spoken = normalize_spoken_text(str(frame.get("spoken_text") or ""))
    text_sha = spoken_text_sha256(spoken)
    content_sha = sha256(audio_bytes).hexdigest()
    frame_id = str(frame.get("frame_id") or "").strip()
    logical_action = str(frame.get("logical_action") or "").strip()
    role = str(frame.get("role") or "").strip()
    if not frame_id or not spoken:
        raise StageError("frame_id and spoken_text are required for resolver rows")

    row: dict[str, Any] = {
        "audio_id": f"action-audio-{frame_id}",
        "byte_length": len(audio_bytes),
        "channels": int(identity.get("channels") or CHANNELS),
        "codec": str(identity.get("codec") or "wav"),
        "content_sha256": content_sha,
        "frame_id": frame_id,
        "generation_settings": dict(identity.get("generation_settings") or {}),
        "locale": str(identity.get("locale") or "en-US"),
        "logical_action": logical_action,
        "metadata": {
            "audio_status": "staged",
            "dataset_audio_path": dataset_audio_path,
            "frame_id": frame_id,
            "logical_action": logical_action,
            "role": role,
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "smoke_fixture": bool(smoke_fixture),
            "source": SOURCE_LABEL,
            "task_id": TASK_ID,
        },
        "mime_type": "audio/wav",
        "model": str(identity.get("model") or "action-fixture-v1"),
        "provider": str(identity.get("provider") or "abby_action_fixture"),
        "provider_version": str(identity.get("provider_version") or "1.0.0"),
        "role": role,
        "sample_rate_hz": int(identity.get("sample_rate_hz") or SAMPLE_RATE_HZ),
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE_LABEL,
        "spoken_text": spoken,
        "task_id": TASK_ID,
        "template_id": frame_id,
        "text_sha256": text_sha,
        "uri": dataset_audio_path,
        "voice": str(identity.get("voice") or "abby"),
    }
    return row


def stage_action_audio(
    *,
    frames_path: Path = DEFAULT_FRAMES_PATH,
    stage_root: Path = DEFAULT_STAGE_ROOT,
    roles: Sequence[str] = REQUIRED_ROLES,
    synthesis_identity: Mapping[str, Any] | None = None,
    smoke: bool = True,
) -> dict[str, Any]:
    """Stage fixture audio + resolver rows for pilot confirm/outcome frames.

    Returns a summary dict including paths and row counts.  Writes:

    - ``{stage_root}/audio/action/*.wav``
    - ``{stage_root}/metadata/abby_action_precomputed_audio_resolver.jsonl``
    - ``{stage_root}/metadata/abby_action_audio_stage_summary.json``
    """

    frames = select_pilot_frames(load_frame_records(frames_path), roles=roles)
    identity = dict(synthesis_identity or SMOKE_SYNTHESIS_IDENTITY)

    stage_root = stage_root.resolve()
    audio_root = stage_root / "audio" / "action"
    metadata_root = stage_root / "metadata"
    audio_root.mkdir(parents=True, exist_ok=True)
    metadata_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    audio_bytes_by_sha256: dict[str, bytes] = {}
    audio_bytes_by_id: dict[str, bytes] = {}

    for frame in frames:
        spoken = normalize_spoken_text(str(frame.get("spoken_text") or ""))
        payload = synthesize_fixture_wav(
            spoken,
            sample_rate_hz=int(identity.get("sample_rate_hz") or SAMPLE_RATE_HZ),
            channels=int(identity.get("channels") or CHANNELS),
        )
        content_sha = sha256(payload).hexdigest()
        frame_id = str(frame["frame_id"])
        rel = audio_relpath_for_frame(frame_id, content_sha)
        abs_path = stage_root / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(payload)

        row = build_resolver_row(
            frame=frame,
            audio_bytes=payload,
            dataset_audio_path=rel,
            synthesis_identity=identity,
            smoke_fixture=smoke,
        )
        rows.append(row)
        audio_bytes_by_sha256[content_sha] = payload
        audio_bytes_by_id[str(row["audio_id"])] = payload

    # Stable resolver order by audio_id.
    rows.sort(key=lambda item: str(item.get("audio_id") or ""))

    resolver_path = metadata_root / RESOLVER_FILENAME
    resolver_text = (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        )
        + ("\n" if rows else "")
    )
    resolver_path.write_text(resolver_text, encoding="utf-8")

    actions = sorted({str(row["logical_action"]) for row in rows})
    roles_present = sorted({str(row["role"]) for row in rows})
    summary: dict[str, Any] = {
        "schema": "voice-action/action-audio-stage-summary@1",
        "task_id": TASK_ID,
        "source": SOURCE_LABEL,
        "smoke": bool(smoke),
        "stage_root": str(stage_root),
        "frames_path": str(frames_path.resolve()),
        "resolver_path": str(resolver_path),
        "resolver_relative": f"metadata/{RESOLVER_FILENAME}",
        "row_count": len(rows),
        "logical_action_count": len(actions),
        "logical_actions": actions,
        "roles": roles_present,
        "required_roles": list(roles),
        "confirm_count": sum(1 for row in rows if row.get("role") == "confirm"),
        "outcome_count": sum(1 for row in rows if row.get("role") != "confirm"),
        "synthesis_identity": identity,
        "complete": (
            len(rows) == len(actions) * len(list(roles))
            and set(roles_present) >= set(roles)
        ),
    }
    summary_path = metadata_root / SUMMARY_FILENAME
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary["summary_path"] = str(summary_path)
    # Attach in-memory maps for callers/tests (not serialized to disk).
    summary["_rows"] = rows
    summary["_audio_bytes_by_sha256"] = audio_bytes_by_sha256
    summary["_audio_bytes_by_id"] = audio_bytes_by_id
    return summary


def load_resolver_rows(resolver_path: Path) -> list[dict[str, Any]]:
    if not resolver_path.is_file():
        raise StageError(f"missing action audio resolver: {resolver_path}")
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        resolver_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StageError(
                f"malformed resolver JSONL at line {line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise StageError(f"resolver row must be an object at line {line_number}")
        rows.append(payload)
    return rows


def load_staged_audio_bytes(
    stage_root: Path,
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """Load audio bytes for staged rows; return (by_sha256, by_audio_id)."""

    by_sha: dict[str, bytes] = {}
    by_id: dict[str, bytes] = {}
    for row in rows:
        rel = ""
        metadata = row.get("metadata")
        if isinstance(metadata, Mapping):
            rel = str(metadata.get("dataset_audio_path") or "").strip()
        if not rel:
            rel = str(row.get("uri") or "").strip()
        if not rel:
            raise StageError(
                f"resolver row {row.get('audio_id')!r} missing dataset_audio_path/uri"
            )
        path = stage_root / rel
        if not path.is_file():
            raise StageError(f"missing staged audio file: {path}")
        payload = path.read_bytes()
        if not payload:
            raise StageError(f"empty staged audio file: {path}")
        digest = sha256(payload).hexdigest()
        expected = str(row.get("content_sha256") or "").strip().lower()
        if expected and digest != expected:
            raise StageError(
                f"audio digest mismatch for {row.get('audio_id')!r}: "
                f"expected {expected}, got {digest}"
            )
        by_sha[digest] = payload
        by_id[str(row.get("audio_id") or digest)] = payload
    return by_sha, by_id


def build_offline_resolver(
    stage_root: Path,
    *,
    resolver_path: Path | None = None,
):
    """Build a ``PrecomputedVoiceAudioResolver`` from a staged fixture tree."""

    from ipfs_accelerate_py.voice_audio_resolver import (  # type: ignore
        PrecomputedVoiceAudioResolver,
    )

    path = resolver_path or (stage_root / "metadata" / RESOLVER_FILENAME)
    rows = load_resolver_rows(path)
    by_sha, by_id = load_staged_audio_bytes(stage_root, rows)
    return PrecomputedVoiceAudioResolver.from_audio_rows(
        rows,
        audio_bytes_by_sha256=by_sha,
        audio_bytes_by_id=by_id,
    )


def resolve_all_staged_rows(
    stage_root: Path,
    *,
    resolver_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Exact-match resolve every staged row offline; raise on any miss."""

    from ipfs_accelerate_py.voice_audio_resolver import (  # type: ignore
        REASON_EXACT_MATCH,
        SynthesisIdentity,
    )

    path = resolver_path or (stage_root / "metadata" / RESOLVER_FILENAME)
    rows = load_resolver_rows(path)
    resolver = build_offline_resolver(stage_root, resolver_path=path)
    results: list[dict[str, Any]] = []
    for row in rows:
        identity = SynthesisIdentity(
            provider=str(row.get("provider") or SMOKE_SYNTHESIS_IDENTITY["provider"]),
            model=str(row.get("model") or SMOKE_SYNTHESIS_IDENTITY["model"]),
            voice=str(row.get("voice") or SMOKE_SYNTHESIS_IDENTITY["voice"]),
            provider_version=str(
                row.get("provider_version")
                or SMOKE_SYNTHESIS_IDENTITY["provider_version"]
            ),
            locale=str(row.get("locale") or SMOKE_SYNTHESIS_IDENTITY["locale"]),
            codec=str(row.get("codec") or SMOKE_SYNTHESIS_IDENTITY["codec"]),
            sample_rate_hz=int(
                row.get("sample_rate_hz") or SMOKE_SYNTHESIS_IDENTITY["sample_rate_hz"]
            ),
            channels=int(row.get("channels") or SMOKE_SYNTHESIS_IDENTITY["channels"]),
            generation_settings=(
                dict(row["generation_settings"])
                if isinstance(row.get("generation_settings"), Mapping)
                else dict(SMOKE_SYNTHESIS_IDENTITY["generation_settings"])
            ),
        )
        spoken = str(row.get("spoken_text") or "")
        resolution = resolver.resolve(
            spoken,
            identity,
            template_id=str(row.get("template_id") or row.get("frame_id") or "") or None,
        )
        if not resolution.hit or resolution.reason != REASON_EXACT_MATCH:
            raise StageError(
                f"exact-match failed for {row.get('audio_id')!r}: "
                f"status={resolution.status} reason={resolution.reason}"
            )
        results.append(
            {
                "audio_id": row.get("audio_id"),
                "frame_id": row.get("frame_id"),
                "logical_action": row.get("logical_action"),
                "role": row.get("role"),
                "status": resolution.status,
                "reason": resolution.reason,
                "content_sha256": row.get("content_sha256"),
            }
        )
    return results


def coverage_report_text(summary: Mapping[str, Any]) -> str:
    return (
        f"{TASK_ID} smoke stage: "
        f"{summary.get('row_count', 0)} resolver rows; "
        f"{summary.get('logical_action_count', 0)} actions; "
        f"confirm={summary.get('confirm_count', 0)}; "
        f"outcome={summary.get('outcome_count', 0)}; "
        f"roles={','.join(summary.get('roles') or [])}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage precomputed audio fixtures and exact-match resolver rows for "
            f"Abby pilot action speech frames ({TASK_ID})."
        )
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Stage offline fixture WAV + resolver rows for every pilot "
            "confirm/outcome speech frame (default mode when no other action "
            "is selected)."
        ),
    )
    parser.add_argument(
        "--frames",
        type=Path,
        default=DEFAULT_FRAMES_PATH,
        help=f"Action speech-frame JSONL (default: {DEFAULT_FRAMES_REL})",
    )
    parser.add_argument(
        "--stage-root",
        type=Path,
        default=DEFAULT_STAGE_ROOT,
        help=f"Stage root directory (default: {DEFAULT_STAGE_REL})",
    )
    parser.add_argument(
        "--verify-resolver",
        action="store_true",
        help="After staging, offline exact-match resolve every staged row",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    # Default to smoke when no mode flags are provided so the documented
    # validation command `python scripts/stage_abby_action_audio.py --smoke`
    # remains the canonical entry point (and bare invocation is still useful).
    if not args.smoke:
        args.smoke = True

    try:
        summary = stage_action_audio(
            frames_path=args.frames,
            stage_root=args.stage_root,
            smoke=True,
        )
        print(coverage_report_text(summary))
        print(f"{TASK_ID} wrote resolver: {summary['resolver_path']}")
        print(
            f"{TASK_ID} wrote {summary['row_count']} rows under {summary['stage_root']}"
        )
        if args.verify_resolver or args.smoke:
            hits = resolve_all_staged_rows(Path(summary["stage_root"]))
            print(
                f"{TASK_ID} offline resolver exact-match OK "
                f"({len(hits)}/{summary['row_count']} hits)"
            )
        if not summary.get("complete"):
            raise StageError(f"incomplete smoke stage coverage: {summary}")
    except StageError as exc:
        print(f"{TASK_ID} FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"{TASK_ID} FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
