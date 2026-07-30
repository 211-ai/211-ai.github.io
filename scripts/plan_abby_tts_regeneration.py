#!/usr/bin/env python3
"""Build deterministic Abby TTS regeneration worksets and endpoint manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
if str(DATASETS_ROOT) not in sys.path:
    sys.path.insert(0, str(DATASETS_ROOT))

from ipfs_datasets_py.voice.regeneration import (  # noqa: E402
    AbbyVoiceRegenerationPlan,
    read_regeneration_queue,
)

DEFAULT_QUEUE = (
    REPO_ROOT
    / "tmp_assets"
    / "hf-abby-tts-canonical-dataset"
    / "metadata"
    / "abby_tts_regeneration_queue.jsonl"
)


def endpoint_response_manifest(
    plan: AbbyVoiceRegenerationPlan,
) -> dict[str, Any]:
    """Project a package plan into the legacy endpoint wrapper's thin schema."""

    responses: list[dict[str, Any]] = []
    for item in plan.items:
        responses.append(
            {
                "id": f"abby-tts-{item.text_sha256[:20]}",
                "text": item.spoken_text,
                "originalTexts": [item.selected_text, item.queue_repair_text],
                "sourceTypes": ["regeneration.queue"],
                "sourceIds": [
                    item.response_id,
                    item.superseded_audio_id,
                    item.regeneration_id,
                ],
                "regenerationId": item.regeneration_id,
                "responseId": item.response_id,
                "riskReasons": list(item.risk_reasons),
                "supersededAudioId": item.superseded_audio_id,
                "targetTextSha256": item.text_sha256,
            }
        )
    return {
        "schemaVersion": "abby_tts_endpoint_regeneration_manifest_v1",
        "planId": plan.plan_id,
        "policyId": plan.policy_id,
        "sourceManifestId": plan.source_manifest_id,
        "responseCount": len(responses),
        "responses": responses,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument(
        "--canary-size",
        type=int,
        default=None,
        help="Select a stable hash-distributed canary from the complete queue.",
    )
    parser.add_argument("--plan-out", type=Path, default=None)
    parser.add_argument("--workset-out", type=Path, default=None)
    parser.add_argument("--response-manifest-out", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = read_regeneration_queue(args.queue)
    full_count = len(plan.items)
    if args.canary_size is not None:
        plan = plan.canary(args.canary_size)

    workset = plan.to_voice_workset()
    endpoint_manifest = endpoint_response_manifest(plan)
    if args.plan_out is not None:
        _write_json(args.plan_out, plan.to_dict())
    if args.workset_out is not None:
        _write_json(args.workset_out, workset.to_dict())
    if args.response_manifest_out is not None:
        _write_json(args.response_manifest_out, endpoint_manifest)

    print(
        json.dumps(
            {
                "asrJobs": len(workset.asr_manifest.items),
                "endpointResponses": endpoint_manifest["responseCount"],
                "fullQueueItems": full_count,
                "planId": plan.plan_id,
                "policyId": plan.policy_id,
                "sourceManifestId": plan.source_manifest_id,
                "ttsJobs": len(workset.tts_manifest.items),
                "validationJobs": len(workset.validation_manifest.items),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
