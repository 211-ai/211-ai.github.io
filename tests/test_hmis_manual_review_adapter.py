from __future__ import annotations

from wallet_interface.hmis.adapters.manual_review import ManualReviewHmisAdapter


FIXTURES = [
    {
        "entity_type": "client",
        "external_client_id": "client-1",
        "name": "Jane Doe",
        "date_of_birth": "1990-04-05",
        "program_ref": "shelter-a",
    },
    {
        "entity_type": "program",
        "external_project_id": "project-1",
        "external_program_id": "program-1",
        "local_program_ref": "shelter-a",
        "program_name": "Safe Harbor Shelter",
    },
]



def test_manual_review_adapter_lookup_filters_fixture_results() -> None:
    adapter = ManualReviewHmisAdapter(fixtures=FIXTURES)

    result = adapter.execute(action_type="lookup_client", payload={"name": "Jane"})

    assert result.ok is True
    assert result.normalized_payload["candidate_count"] == 1



def test_manual_review_adapter_creates_review_packet() -> None:
    adapter = ManualReviewHmisAdapter(fixtures=FIXTURES)

    result = adapter.execute(
        action_type="create_referral_draft",
        payload={"local_subject_ref": "wallet:1", "destination_program_ref": "shelter-a", "provider_name": "Safe Harbor"},
    )

    assert result.ok is True
    assert result.normalized_payload["draft_packet"]["review_mode"] == "manual"
