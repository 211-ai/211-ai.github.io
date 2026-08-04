#!/usr/bin/env python3
"""Stage a minimal offline Abby resolver+MP3 fixture for multiturn smoke tests.

This does **not** replace the sealed production canonical release.  It only
creates enough content-addressed audio under ``tmp_assets/hf-abby-tts-canonical-
dataset`` so selected multiturn e2e tests can exercise the resolver path without
Hugging Face.

Requires ``ffmpeg`` with ``libmp3lame``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset"

SAMPLES = (
    (
        "smoke-app-surface.mp3",
        "app_surface_navigation",
        "Open your Wallet documents surface and show your photo ID first for intake next step.",
        440,
    ),
    (
        "smoke-grounded.mp3",
        "grounded_211_answer",
        "Here is one solid option for local food help near you. Call two one one for more choices.",
        520,
    ),
    (
        "smoke-live-agent.mp3",
        "live_agent",
        "I can connect you with a live person right now if you still want human help.",
        380,
    ),
)


def _require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required to stage the smoke fixture")
    return ffmpeg


def _write_mp3(ffmpeg: str, path: Path, *, frequency_hz: int, duration_s: float = 0.25) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency_hz}:duration={duration_s}",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "5",
        str(path),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"ffmpeg failed for {path.name}: {completed.stderr[-500:]}")


def stage(stage_root: Path) -> Path:
    ffmpeg = _require_ffmpeg()
    audio_root = stage_root / "audio"
    metadata_root = stage_root / "metadata"
    audio_root.mkdir(parents=True, exist_ok=True)
    metadata_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for name, route, text, frequency in SAMPLES:
        path = audio_root / name
        _write_mp3(ffmpeg, path, frequency_hz=frequency)
        payload = path.read_bytes()
        rel = f"audio/{name}"
        rows.append(
            {
                "audio_id": f"smoke-{route}",
                "spoken_text": text,
                "content_sha256": sha256(payload).hexdigest(),
                "byte_length": len(payload),
                "mime_type": "audio/mpeg",
                "sample_rate_hz": 24000,
                "channels": 1,
                "metadata": {
                    "routes": [route],
                    "dataset_audio_path": rel,
                    "smoke_fixture": True,
                },
            }
        )

    resolver = metadata_root / "abby_tts_precomputed_audio_resolver.jsonl"
    resolver.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return resolver


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage-root",
        type=Path,
        default=DEFAULT_STAGE,
        help="Output stage root (default: tmp_assets/hf-abby-tts-canonical-dataset)",
    )
    args = parser.parse_args(argv)
    resolver = stage(args.stage_root.resolve())
    print(f"staged smoke resolver: {resolver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
