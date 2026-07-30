from __future__ import annotations

import pytest

from scripts.review_abby_regeneration_audio import (
    content_word_coverage_bp,
    normalized_review_text,
    normalized_similarity_bp,
    numeric_sequences_match,
    select_review_rows,
)


def test_review_normalization_equates_spoken_and_numeric_phone_forms() -> None:
    expected = "Call five zero three, five five five, zero one zero zero."
    observed = "Call 503-555-0100."

    assert normalized_review_text(expected) == normalized_review_text(observed)
    assert normalized_similarity_bp(expected, observed) == 10_000
    assert content_word_coverage_bp(expected, observed) == 10_000
    assert numeric_sequences_match(expected, observed) is True


def test_review_normalization_equates_singleton_hyphens_and_curly_contractions() -> None:
    expected = (
        "You’re doing the right thing. Call five four one, two two one, "
        "zero eight two four. I’ll repeat: five four one, two two one, "
        "zero eight two four."
    )
    observed = (
        "You're doing the right thing. Call 5-4-1-2-2-1-0-8-2-4. "
        "I'll repeat 5-4-1-2-2-1-0-8-2-4."
    )

    assert normalized_review_text(expected) == normalized_review_text(observed)
    assert normalized_similarity_bp(expected, observed) == 10_000
    assert content_word_coverage_bp(expected, observed) == 10_000
    assert numeric_sequences_match(expected, observed) is True


def test_review_normalization_does_not_hide_a_wrong_digit() -> None:
    expected = "Call five zero three, five five five, zero one zero zero."
    observed = "Call 503-555-0101."

    assert normalized_review_text(expected) != normalized_review_text(observed)
    assert numeric_sequences_match(expected, observed) is False


def test_review_metrics_reject_true_repetition() -> None:
    expected = "The shelter is open tonight."
    observed = "The shelter is open tonight. The shelter is open tonight."

    assert normalized_similarity_bp(expected, observed) < 7_800


def test_review_metrics_detect_missing_required_content() -> None:
    expected = "Call the shelter at five zero three, five five five, zero one zero zero."
    observed = "Okay."

    assert normalized_similarity_bp(expected, observed) < 7_800
    assert content_word_coverage_bp(expected, observed) < 6_500


def test_review_row_selection_preserves_requested_order() -> None:
    rows = [{"id": "first"}, {"id": "second"}, {"id": "third"}]

    assert select_review_rows(rows, ["third", "first"]) == [
        {"id": "third"},
        {"id": "first"},
    ]


def test_review_row_selection_rejects_missing_or_duplicate_ids() -> None:
    rows = [{"id": "first"}]

    with pytest.raises(ValueError, match="must be unique"):
        select_review_rows(rows, ["first", "first"])
    with pytest.raises(ValueError, match="absent"):
        select_review_rows(rows, ["missing"])
