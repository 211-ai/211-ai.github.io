from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.upload_hf_abby_tts_dataset import build_query_index, stage_abby_tts_dataset


class UploadHfAbbyTtsDatasetTests(unittest.TestCase):
    def test_stage_dataset_dedupes_text_hash_and_copies_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            docs_dir = repo_root / "docs"
            audio_dir = repo_root / "wallet_interface" / "ui" / "public" / "assets" / "audio" / "precomputed" / "pregenerated-text-slot-phone-indextts"
            docs_dir.mkdir(parents=True)
            audio_dir.mkdir(parents=True)

            text = "Call two one one for help"
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]
            manifest_path = docs_dir / "pregenerated_text_audio_slot_phone_public_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "updatedAt": "2026-05-29T00:00:00Z",
                        "responses": [
                            {
                                "id": f"abby-tts-slot-value-{text_hash}",
                                "textHash": text_hash,
                                "text": text,
                                "originalTexts": ["Call 211 for help"],
                                "routes": ["/services/help"],
                                "slottedIntentIds": ["contact_support"],
                                "slottedCanonicalQueryTemplates": ["call 211"],
                                "slottedResponseFrameIds": ["frame-help"],
                                "slottedResponseSignatures": ["sig-help"],
                                "slottedEdgeIds": ["edge-help"],
                                "serviceTags": ["help"],
                                "locationTags": ["oregon"],
                                "sourceTypes": ["audio_plan.slot_value"],
                                "sourceIds": ["audio-slot::phone::demo"],
                                "status": "generated_mp3",
                                "preferredAudioPath": f"wallet_interface/ui/public/assets/audio/precomputed/pregenerated-text-slot-phone-indextts/abby-tts-{text_hash}.mp3",
                                "preferredMimeType": "audio/mpeg",
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            source_audio = audio_dir / f"abby-tts-{text_hash}.mp3"
            source_audio.write_bytes(b"fake mp3 bytes")

            stage_dir = repo_root / "tmp_assets" / "hf-abby-tts-dataset"
            result = stage_abby_tts_dataset(
                repo_root=repo_root,
                manifest_paths=[manifest_path],
                provenance_paths=[manifest_path],
                audio_roots=[repo_root / "wallet_interface" / "ui" / "public" / "assets" / "audio" / "precomputed"],
                stage_dir=stage_dir,
                repo_id="endomorphosis/211-info",
                remote_prefix="audio/abby-tts/current",
                write_parquet_files=False,
            )

            self.assertEqual(result["recordCount"], 1)
            self.assertEqual(result["audioAvailableCount"], 1)
            self.assertEqual(result["runtimeManifestResponseCount"], 1)
            staged_audio = stage_dir / "audio" / f"abby-tts-{text_hash}.mp3"
            self.assertTrue(staged_audio.exists())
            self.assertEqual(staged_audio.read_bytes(), b"fake mp3 bytes")

            jsonl_path = stage_dir / "metadata" / "abby_tts_responses.jsonl"
            rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["id"], f"abby-tts-{text_hash}")
            self.assertEqual(row["textHash"], text_hash)
            self.assertEqual(row["manifestIds"], [f"abby-tts-slot-value-{text_hash}"])
            self.assertEqual(row["datasetAudioPath"], f"audio/abby-tts-{text_hash}.mp3")
            self.assertEqual(row["routes"], ["/services/help"])
            self.assertEqual(row["slottedIntentIds"], ["contact_support"])
            self.assertEqual(row["slottedCanonicalQueryTemplates"], ["call 211"])
            self.assertEqual(row["slottedResponseFrameIds"], ["frame-help"])
            self.assertEqual(row["slottedResponseSignatures"], ["sig-help"])
            self.assertEqual(row["slottedEdgeIds"], ["edge-help"])
            self.assertEqual(row["sourceTypes"], ["audio_plan.slot_value"])

            runtime_manifest = json.loads((stage_dir / "metadata" / "abby_tts_runtime_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(runtime_manifest["responseCount"], 1)
            runtime_entry = runtime_manifest["responses"][0]
            self.assertEqual(runtime_entry["id"], f"abby-tts-{text_hash}")
            self.assertEqual(runtime_entry["preferredAudioUrl"], "https://huggingface.co/datasets/endomorphosis/211-info/resolve/main/audio/abby-tts/current/audio/abby-tts-" + text_hash + ".mp3")
            self.assertEqual(runtime_entry["routes"], ["/services/help"])
            self.assertEqual(runtime_entry["slottedIntentIds"], ["contact_support"])
            resolver_rows = [
                json.loads(line)
                for line in (stage_dir / "metadata" / "abby_tts_precomputed_audio_resolver.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(resolver_rows[0]["spoken_text"], text)
            self.assertEqual(resolver_rows[0]["content_sha256"], hashlib.sha256(b"fake mp3 bytes").hexdigest())
            self.assertEqual(resolver_rows[0]["provider"], "abby_indextts")
            self.assertEqual(resolver_rows[0]["codec"], "mp3")

            provenance_copy = stage_dir / "provenance" / "docs" / manifest_path.name
            self.assertTrue(provenance_copy.exists())

    def test_stage_dataset_ingests_bucket_recovery_vocabulary_and_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            docs_dir = repo_root / "docs"
            docs_dir.mkdir(parents=True)

            spoken = "Call two one one for shelter help."
            text_hash = hashlib.sha256(spoken.encode("utf-8")).hexdigest()[:20]
            manifest_path = docs_dir / "pregenerated_text_response_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "responses": [
                            {
                                "id": f"abby-tts-{text_hash}",
                                "textHash": text_hash,
                                "text": spoken,
                                "sourceTypes": ["simulation.assistant"],
                                "status": "planned",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            bucket_dir = repo_root / "data" / "abby_voice" / "canonical"
            bucket_dir.mkdir(parents=True)
            normalized_jsonl = bucket_dir / "bucket-audio-normalized.jsonl"
            bucket_path = f"runs/demo/audio/abby-tts-{text_hash}.mp3"
            vocab_hash = hashlib.sha256(b"shelter").hexdigest()
            normalized_jsonl.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "object_class": "response_linkable",
                                "path": bucket_path,
                                "mapping_status": "selected_for_response",
                                "mapping_method": "accepted_plan_selection",
                                "media_extension": "mp3",
                                "size_bytes": 11,
                                "xet_hash": "xet-selected",
                                "legacy_text_hash": text_hash,
                                "canonical_text_sha256": hashlib.sha256(spoken.encode("utf-8")).hexdigest(),
                                "response_id": "response-demo",
                            }
                        ),
                        json.dumps(
                            {
                                "object_class": "response_linkable",
                                "path": "runs/demo/audio/abby-tts-vocab.mp3",
                                "mapping_status": "mapped_to_vocabulary",
                                "mapping_method": "bm25_text_hash",
                                "media_extension": "mp3",
                                "size_bytes": 7,
                                "xet_hash": "xet-vocab",
                                "legacy_text_hash": vocab_hash[:20],
                                "canonical_text_sha256": vocab_hash,
                                "subject_kind": "bm25_term",
                                "subject_id": f"abby-tts-vocab-{vocab_hash[:20]}",
                                "source_text": "shelter",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            audio_bytes = b"fake bucket mp3"
            raw_sha = hashlib.sha256(audio_bytes).hexdigest()
            cache_root = repo_root / "tmp_assets" / "abby-voice-audio-recovery" / "accelerator-artifacts"
            cached_audio = cache_root / raw_sha[:2] / f"{raw_sha}.mp3"
            cached_audio.parent.mkdir(parents=True)
            cached_audio.write_bytes(audio_bytes)
            recovery_json = bucket_dir / "recovery.json"
            recovery_json.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "bucket_path": bucket_path,
                                "raw_sha256": raw_sha,
                                "record_id": "verified-demo",
                                "spoken_text": spoken,
                                "media_type": "audio/mpeg",
                                "verified_size_bytes": len(audio_bytes),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            template_path = docs_dir / "slotted_response_dag.json"
            template_path.write_text(
                json.dumps(
                    {
                        "nodes": {
                            "responseFrames": [
                                {
                                    "id": "frame-demo",
                                    "type": "response_frame",
                                    "responseSignature": "Call {phone}.",
                                    "reuseCount": 3,
                                    "responseSlotKinds": {"phone": 1},
                                    "recordIds": ["demo#turn-1"],
                                }
                            ],
                            "intents": [
                                {
                                    "id": "intent-demo",
                                    "type": "intent",
                                    "canonicalQueryTemplate": "I need shelter",
                                    "reuseCount": 2,
                                    "recordIds": ["demo#turn-1"],
                                }
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )

            stage_dir = repo_root / "tmp_assets" / "hf-abby-tts-canonical"
            result = stage_abby_tts_dataset(
                repo_root=repo_root,
                manifest_paths=[manifest_path],
                provenance_paths=[manifest_path, normalized_jsonl, recovery_json, template_path],
                audio_roots=[],
                stage_dir=stage_dir,
                repo_id="endomorphosis/211-info",
                remote_prefix="audio/abby-tts/canonical",
                write_parquet_files=False,
                bucket_normalized_jsonl_path=normalized_jsonl,
                bucket_recovery_json_path=recovery_json,
                bucket_audio_cache_root=cache_root,
                template_metadata_paths=[template_path],
            )

            self.assertEqual(result["bucketSelectedAudioLinkedCount"], 1)
            self.assertEqual(result["bucketStatusCounts"]["selected_for_response"], 1)
            self.assertEqual(result["bucketStatusCounts"]["mapped_to_vocabulary"], 1)
            self.assertEqual(result["slottedResponseFrameCount"], 1)
            self.assertEqual(result["slottedIntentCount"], 1)
            self.assertEqual(result["precomputedAudioResolverRowCount"], 1)
            self.assertEqual((stage_dir / "audio" / f"abby-tts-{text_hash}.mp3").read_bytes(), audio_bytes)

            vocab_rows = [
                json.loads(line)
                for line in (stage_dir / "metadata" / "abby_tts_vocabulary.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(vocab_rows[0]["text"], "shelter")
            bucket_rows = [
                json.loads(line)
                for line in (stage_dir / "metadata" / "abby_tts_bucket_audio_objects.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(bucket_rows), 2)
            self.assertEqual(bucket_rows[0]["datasetRecordId"], f"abby-tts-{text_hash}")

    def test_build_query_index_groups_records_by_lookup_facets(self) -> None:
        query_index = build_query_index(
            [
                {
                    "id": "abby-tts-1234567890abcdef1234",
                    "textHash": "1234567890abcdef1234",
                    "text": "Call two one one",
                    "datasetAudioPath": "audio/abby-tts-1234567890abcdef1234.mp3",
                    "datasetAudioUrl": "https://huggingface.co/datasets/endomorphosis/211-info/resolve/main/audio/abby-tts/current/audio/abby-tts-1234567890abcdef1234.mp3",
                    "audioAvailable": True,
                    "routes": ["/services/help"],
                    "serviceTags": ["help"],
                    "locationTags": ["oregon"],
                    "sourceTypes": ["audio_plan.slot_value"],
                    "manifestPaths": ["docs/pregenerated_text_audio_slot_phone_public_manifest.json"],
                    "statuses": ["generated_mp3"],
                }
            ]
        )

        self.assertEqual(query_index["byTextHash"]["1234567890abcdef1234"], "abby-tts-1234567890abcdef1234")
        self.assertEqual(query_index["byRoute"]["/services/help"], ["abby-tts-1234567890abcdef1234"])
        self.assertEqual(query_index["byServiceTag"]["help"], ["abby-tts-1234567890abcdef1234"])
        self.assertEqual(query_index["byLocationTag"]["oregon"], ["abby-tts-1234567890abcdef1234"])


if __name__ == "__main__":
    unittest.main()
