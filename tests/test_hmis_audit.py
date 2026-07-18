from __future__ import annotations

from wallet_interface.hmis.audit import HmisAuditStore
from wallet_interface.hmis.models import HmisSyncEvent


def test_hmis_audit_store_persists_and_reload_events(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    store = HmisAuditStore(path=path)
    store.emit(
        HmisSyncEvent(
            event_id="evt-1",
            action_type="lookup_client",
            actor_id="did:key:worker",
            local_ref="wallet:1",
            status="success",
            occurred_at="2026-01-01T00:00:00+00:00",
        )
    )
    store.record(
        action_type="submit_referral",
        actor_id="did:key:worker",
        local_ref="ref-1",
        status="retryable",
        response_summary="timeout",
    )

    reloaded = HmisAuditStore(path=path)
    events = reloaded.list_events()

    assert len(events) == 2
    assert reloaded.latest_for_local_ref("ref-1") is not None
    assert reloaded.list_events(status="success")[0].event_id == "evt-1"
