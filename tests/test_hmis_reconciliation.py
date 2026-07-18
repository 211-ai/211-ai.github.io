from __future__ import annotations

from wallet_interface import WalletInterfaceService


def test_hmis_reconciliation_job_resolves_fixture_backed_queue_item(tmp_path) -> None:
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository")
    wallet = service.create_wallet("did:key:worker")
    draft = service.create_hmis_referral_draft(
        wallet.wallet_id,
        actor_did="did:key:worker",
        local_subject_ref="wallet:subject-1",
        destination_program_ref="shelter-a",
        provider_name="Safe Harbor Shelter",
        program_name="Emergency Shelter",
        summary="Client requests emergency shelter placement.",
    )
    service._fixture_imports = [
        {"local_ref": draft.referral_draft_id, "status": "accepted", "external_referral_id": "hmis-ref-1"}
    ]
    helper = service.submission_service
    helper.enqueue_reconciliation(
        wallet_id=wallet.wallet_id,
        referral_draft_id=draft.referral_draft_id,
        local_ref=draft.referral_draft_id,
        reason="awaiting status import",
    )
    service._save_state()

    result = service.run_hmis_reconciliation_job(dry_run=False)
    queue = service.list_hmis_reconciliation_queue(wallet.wallet_id)

    assert result["status"] == "ok"
    assert result["resolved_count"] >= 1
    assert queue["items"][0]["status"] == "resolved"
