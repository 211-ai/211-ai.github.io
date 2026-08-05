from __future__ import annotations

from ipfs_datasets_py.voice.regeneration import AbbyVoiceRegenerationPlan

from scripts.plan_abby_tts_regeneration import endpoint_response_manifest


def _row(index: int) -> dict[str, object]:
    return {
        "audioId": f"abby-tts-old-{index}",
        "responseId": f"response-{index}",
        "selectedDatasetAudioPath": f"audio/abby-tts-old-{index}.mp3",
        "selectedText": "Call 503-555-0100.",
        "normalizedRepairText": "Call 503-555-0100.",
        "recommendation": "regenerate_from_normalized_text",
        "riskReasons": ["raw_phone_number"],
    }


def test_endpoint_manifest_is_a_thin_projection_with_supersession_lineage() -> None:
    plan = AbbyVoiceRegenerationPlan.from_records([_row(1), _row(2)])

    manifest = endpoint_response_manifest(plan)

    assert manifest["planId"] == plan.plan_id
    assert manifest["responseCount"] == 2
    response = manifest["responses"][0]
    assert response["id"].startswith("abby-tts-")
    assert response["responseId"] in response["sourceIds"]
    assert response["supersededAudioId"] in response["sourceIds"]
    assert response["regenerationId"] in response["sourceIds"]
    assert "-" not in response["text"]
    assert not any(character.isdigit() for character in response["text"])
