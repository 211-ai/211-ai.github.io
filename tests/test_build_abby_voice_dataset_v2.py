from __future__ import annotations

import json
from hashlib import sha256

from ipfs_datasets_py.voice.normalize import NormalizationConfig
from scripts.build_abby_voice_dataset_v2 import normalize_paths


def test_explicit_audio_root_resolves_repo_relative_manifest_paths(tmp_path) -> None:
    repo_root = tmp_path / "repo"
    audio_path = repo_root / "tmp_assets" / "canonical" / "audio" / "sample.mp3"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"synthetic canonical MP3 fixture")

    spoken_text = "Your requested information is ready."
    text_hash = sha256(spoken_text.encode("utf-8")).hexdigest()[:20]
    manifest_path = (
        repo_root
        / "tmp_assets"
        / "canonical"
        / "metadata"
        / "regeneration-audio-manifest.json"
    )
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "responses": [
                    {
                        "id": f"abby-tts-{text_hash}",
                        "textHash": text_hash,
                        "text": spoken_text,
                        "mp3Path": "tmp_assets/canonical/audio/sample.mp3",
                        "mp3MimeType": "audio/mpeg",
                        "mp3Bytes": audio_path.stat().st_size,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = normalize_paths(
        [manifest_path],
        config=NormalizationConfig(require_audio=True),
        audio_root=repo_root,
    )

    assert len(result.responses) == 1
    assert len(result.audio) == 1
    assert result.audio[0].content_sha256 == sha256(audio_path.read_bytes()).hexdigest()
    assert not result.warnings
