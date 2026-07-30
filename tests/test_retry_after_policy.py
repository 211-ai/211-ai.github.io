from __future__ import annotations

from scripts import retry_after_policy as policy


def test_hf_countdown_is_anchored_to_checkpoint_update_time() -> None:
    anchor = policy.parse_timestamp("2026-07-29T00:00:00Z")
    assert anchor is not None

    schedule = policy.parse_retry_after(
        "01:02:03",
        now_epoch=anchor + 600.0,
        relative_anchor_epoch=anchor,
    )

    assert schedule is not None
    assert schedule.value_kind == "relative"
    assert schedule.retry_at_epoch == anchor + 3723.0


def test_decision_subtracts_elapsed_time_since_checkpoint_and_adds_grace() -> None:
    anchor = policy.parse_timestamp("2026-07-29T00:00:00Z")
    assert anchor is not None

    decision = policy.retry_after_decision_from_state(
        {"updatedAt": "2026-07-29T00:00:00Z", "retryAfter": "01:00:00"},
        now_epoch=anchor + 600.0,
        fallback_seconds=300.0,
        minimum_seconds=60.0,
        grace_seconds=15.0,
    )

    assert decision.used_fallback is False
    assert decision.delay_seconds == 3015.0
    assert decision.retry_at_utc == "2026-07-29T01:00:15Z"


def test_live_publicus_hhmmss_hint_targets_checkpoint_time_plus_duration() -> None:
    now = policy.parse_timestamp("2026-07-29T02:00:00Z")
    assert now is not None

    decision = policy.retry_after_decision_from_state(
        {"updatedAt": "2026-07-29T01:29:40Z", "retryAfter": "20:10:39"},
        now_epoch=now,
        fallback_seconds=300.0,
        minimum_seconds=60.0,
        grace_seconds=15.0,
    )

    assert decision.retry_at_utc == "2026-07-29T21:40:34Z"
    assert decision.delay_seconds == 70834.0


def test_absolute_http_retry_after_is_supported() -> None:
    now = policy.parse_timestamp("2026-07-29T00:00:00Z")
    assert now is not None

    decision = policy.retry_after_decision_from_state(
        {"retryAfter": "Wed, 29 Jul 2026 01:00:00 GMT"},
        now_epoch=now,
        fallback_seconds=300.0,
        minimum_seconds=60.0,
        grace_seconds=15.0,
    )

    assert decision.value_kind == "absolute"
    assert decision.delay_seconds == 3615.0


def test_missing_or_malformed_retry_after_uses_bounded_fallback() -> None:
    missing = policy.retry_after_decision_from_state(
        {},
        now_epoch=1000.0,
        fallback_seconds=300.0,
        minimum_seconds=60.0,
        grace_seconds=15.0,
    )
    malformed = policy.retry_after_decision_from_state(
        {"retryAfter": "later"},
        now_epoch=1000.0,
        fallback_seconds=30.0,
        minimum_seconds=60.0,
        grace_seconds=15.0,
    )

    assert missing.used_fallback is True
    assert missing.delay_seconds == 300.0
    assert malformed.used_fallback is True
    assert malformed.delay_seconds == 60.0
