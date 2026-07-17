from __future__ import annotations

from wallet_interface import WalletInterfaceService



def test_hmis_end_to_end_lookup_match_draft_submit_and_reconcile(tmp_path) -> None:
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository")
    wallet = service.create_wallet("did:key:worker")

    lookup = service.lookup_hmis_clients(
        wallet.wallet_id,
        actor_did="did:key:worker",
        name="Jane Doe",
        date_of_birth="1990-04-05",
        program_ref="shelter-a",
    )
    client = lookup["clients"][0]
    verified = service.verify_hmis_match(
        wallet.wallet_id,
        actor_did="did:key:worker",
        entity_type="client",
        local_ref="wallet:subject-1",
        external_id=str(client["external_id"]),
        confidence=float(client["score"]),
    )
    rejected = service.reject_hmis_match(
        wallet.wallet_id,
        actor_did="did:key:worker",
        entity_type="client",
        local_ref="wallet:subject-1",
        external_id="client-200",
        reason="duplicate household member",
    )

    draft = service.create_hmis_referral_draft(
        wallet.wallet_id,
        actor_did="did:key:worker",
        local_subject_ref="wallet:subject-1",
        destination_program_ref="shelter-a",
        provider_name="Safe Harbor Shelter",
        program_name="Emergency Shelter",
        summary="Client requests emergency shelter placement.",
    )
    validation = service.validate_hmis_referral_draft(wallet.wallet_id, draft.referral_draft_id, actor_did="did:key:worker")
    submission = service.submit_hmis_referral_draft(wallet.wallet_id, draft.referral_draft_id, actor_did="did:key:worker")

    service._fixture_imports = [
        {"local_ref": draft.referral_draft_id, "status": "accepted", "external_referral_id": "hmis-ref-1"}
    ]
    helper = service.submission_service
    helper.enqueue_reconciliation(
        wallet_id=wallet.wallet_id,
        referral_draft_id=draft.referral_draft_id,
        local_ref=draft.referral_draft_id,
        reason="awaiting final import",
    )
    service._save_state()
    dry_run = service.run_hmis_reconciliation_job(dry_run=True)
    reconciled = service.run_hmis_reconciliation_job(dry_run=False)
    timeline = service.list_hmis_sync_timeline(wallet.wallet_id)
    queue = service.list_hmis_reconciliation_queue(wallet.wallet_id)

    assert verified["status"] == "verified"
    assert rejected["reason"] == "duplicate household member"
    assert validation["status"] == "ready"
    assert submission["status"] == "submitted"
    assert dry_run["status"] == "dry-run"
    assert reconciled["resolved_count"] >= 1
    assert any(event["action_type"] == "submit_referral" for event in timeline["events"])
    assert queue["items"][0]["status"] == "resolved"
