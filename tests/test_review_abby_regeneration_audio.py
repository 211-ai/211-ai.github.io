from __future__ import annotations

from scripts.review_abby_regeneration_audio import (
    content_word_coverage_bp,
    normalized_review_text,
    normalized_similarity_bp,
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
