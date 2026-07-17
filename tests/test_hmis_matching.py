from __future__ import annotations

from wallet_interface.hmis.matching import match_hmis_clients, match_hmis_households



def test_client_matching_auto_verifies_single_high_confidence_match() -> None:
    result = match_hmis_clients(
        {"name": "Jane Doe", "date_of_birth": "1990-04-05", "program_ref": "shelter-a"},
        [
            {
                "external_client_id": "client-1",
                "name": "Jane Doe",
                "date_of_birth": "1990-04-05",
                "program_ref": "shelter-a",
            }
        ],
    )

    assert result.decision == "single_match"
    assert result.auto_verified_candidate_id == "client-1"
    assert result.candidates[0].score >= 0.85



def test_client_matching_preserves_rejected_candidates_and_blocks_ambiguity() -> None:
    result = match_hmis_clients(
        {"name": "Alex Smith", "date_of_birth": "1984-01-02"},
        [
            {"external_client_id": "client-1", "name": "Alex Smith", "date_of_birth": "1984-01-02"},
            {"external_client_id": "client-2", "name": "Alex Smith", "date_of_birth": "1984-01-02"},
        ],
        rejected_candidate_ids=("client-2",),
    )

    assert result.decision == "ambiguous"
    assert result.auto_verified_candidate_id is None
    assert result.rejected_candidates[0].external_id == "client-2"



def test_household_matching_scores_partial_matches() -> None:
    result = match_hmis_households(
        {"name": "Rivera Household", "program_ref": "rapid-rehousing"},
        [
            {
                "external_household_id": "household-1",
                "household_name": "Rivera Household",
                "program_ref": "rapid-rehousing",
                "member_count": 3,
            }
        ],
    )

    assert result.candidates[0].matched_fields == ("name", "program_ref", "member_count")
