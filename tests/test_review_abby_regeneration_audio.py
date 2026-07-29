from __future__ import annotations

import pytest

from scripts.review_abby_regeneration_audio import (
    content_word_coverage_bp,
    normalized_review_text,
    normalized_similarity_bp,
    select_review_rows,
)


def test_review_normalization_equates_spoken_and_numeric_phone_forms() -> None:
    expected = "Call five zero three, five five five, zero one zero zero."
    observed = "Call 503-555-0100."

    assert normalized_review_text(expected) == normalized_review_text(observed)
    assert normalized_similarity_bp(expected, observed) == 10_000
    assert content_word_coverage_bp(expected, observed) == 10_000


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
