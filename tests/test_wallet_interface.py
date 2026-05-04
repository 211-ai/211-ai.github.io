from __future__ import annotations

import json
from pathlib import Path

import pytest

from wallet_interface import ServiceRecord, WalletInterfaceService, match_services
from ipfs_datasets_py.wallet.crypto import random_key
from ipfs_datasets_py.wallet.ucan import resource_for_export, resource_for_location, resource_for_record


OWNER = "did:key:owner"
ADVOCATE = "did:key:advocate"
SECOND_CONTROLLER = "did:key:second-controller"


def _services():
    return [
        ServiceRecord(
            id="housing-1",
            name="Portland Housing Help",
            description="Rent assistance and emergency shelter navigation.",
            categories="housing shelter rent",
            city="Portland",
            state="OR",
            zip="97201",
            phone="211",
            website="https://example.org/housing",
        ),
        ServiceRecord(
            id="food-1",
            name="Food Pantry",
            description="Weekly groceries and SNAP application help.",
            categories="food snap",
            city="Eugene",
            state="OR",
            zip="97401",
            phone="211",
            website="https://example.org/food",
        ),
    ]


def test_match_services_uses_need_terms_and_coarse_location():
    matches = match_services(
        _services(),
        need_terms=["housing"],
        location_claim={
            "claim_type": "coarse_location",
            "public_value": {"city": "Portland", "state": "OR"},
            "precision": "city",
        },
    )

    assert matches[0].service.id == "housing-1"
    assert "matches need:housing" in matches[0].reasons
    assert "matches coarse city" in matches[0].reasons


def test_match_services_rejects_precise_location():
    with pytest.raises(ValueError, match="requires coarse"):
        match_services(
            _services(),
            need_terms=["housing"],
            location_claim={"public_value": {"lat": 45.515232, "lon": -122.678385}, "precision": "precise"},
        )


def test_wallet_interface_matches_with_delegate_coarse_location_grant():
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    location = app.add_location(wallet.wallet_id, actor_did=OWNER, lat=45.515232, lon=-122.678385)
    grant = app.wallet_service.create_grant(
        wallet_id=wallet.wallet_id,
        issuer_did=OWNER,
        audience_did=ADVOCATE,
        resources=[resource_for_location(wallet.wallet_id, location.record_id)],
        abilities=["location/read_coarse"],
    )

    matches = app.match_services_for_wallet(
        wallet.wallet_id,
        location.record_id,
        actor_did=ADVOCATE,
        grant_id=grant.grant_id,
        need_terms=["housing"],
    )

    assert matches[0].service.id == "housing-1"
    assert app.wallet_service.decrypt_record


def test_wallet_interface_matches_with_coarse_location_invocation():
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    location = app.add_location(wallet.wallet_id, actor_did=OWNER, lat=45.515232, lon=-122.678385)
    delegate_secret = b"l" * 32
    grant = app.create_coarse_location_grant(
        wallet.wallet_id,
        location.record_id,
        issuer_did=OWNER,
        audience_did=ADVOCATE,
        audience_secret=delegate_secret,
    )
    invocation = app.issue_coarse_location_invocation(
        wallet.wallet_id,
        location.record_id,
        grant_id=grant.grant_id,
        actor_did=ADVOCATE,
        actor_secret=delegate_secret,
    )

    matches = app.match_services_for_wallet_with_invocation(
        wallet.wallet_id,
        location.record_id,
        actor_did=ADVOCATE,
        actor_secret=delegate_secret,
        invocation=invocation,
        need_terms=["housing"],
    )
    actions = [event["action"] for event in app.audit_timeline(wallet.wallet_id)]

    assert matches[0].service.id == "housing-1"
    assert "invocation/issue" in actions
    assert "invocation/verify" in actions
    assert "location/read_coarse" in actions


def test_wallet_interface_matches_from_derived_facts():
    app = WalletInterfaceService(services=_services())

    matches = app.match_services_from_derived_facts(
        derived_facts={
            "needs": ["food"],
            "location_claim": {
                "claim_type": "coarse_location",
                "public_value": {"city": "Eugene", "state": "OR"},
                "precision": "city",
            },
        }
    )

    assert matches[0].service.id == "food-1"


def test_wallet_interface_document_analysis_grant_and_audit_timeline(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    owner_secret = b"o" * 32
    delegate_secret = b"d" * 32
    source = tmp_path / "benefits.txt"
    source.write_text("SNAP approval letter and utility shutoff risk.", encoding="utf-8")

    record = app.add_document(
        wallet.wallet_id,
        source,
        actor_did=OWNER,
        actor_secret=owner_secret,
        metadata={"title": "Benefits letter"},
    )
    grant = app.create_record_analysis_grant(
        wallet.wallet_id,
        record.record_id,
        issuer_did=OWNER,
        audience_did=ADVOCATE,
        issuer_secret=owner_secret,
        audience_secret=delegate_secret,
    )
    artifact = app.analyze_record_for_delegate(
        wallet.wallet_id,
        record.record_id,
        actor_did=ADVOCATE,
        grant_id=grant.grant_id,
        actor_secret=delegate_secret,
    )
    timeline = app.audit_timeline(wallet.wallet_id)
    [receipt] = app.list_grant_receipts(wallet.wallet_id, audience_did=ADVOCATE)

    assert artifact.artifact_type == "summary"
    assert receipt.grant_id == grant.grant_id
    assert receipt.audience_did == ADVOCATE
    assert receipt.status == "active"
    assert receipt.receipt_hash
    assert timeline[-1]["action"] == "record/analyze"
    assert any(event["action"] == "grant/create" for event in timeline)


def test_wallet_interface_analysis_invocation_flow(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    owner_secret = b"o" * 32
    delegate_secret = b"d" * 32
    source = tmp_path / "case-note.txt"
    source.write_text("Housing instability and SNAP recertification.", encoding="utf-8")
    record = app.add_document(wallet.wallet_id, source, actor_did=OWNER, actor_secret=owner_secret)
    grant = app.create_record_analysis_grant(
        wallet.wallet_id,
        record.record_id,
        issuer_did=OWNER,
        audience_did=ADVOCATE,
        issuer_secret=owner_secret,
        audience_secret=delegate_secret,
    )

    invocation = app.issue_record_analysis_invocation(
        wallet.wallet_id,
        record.record_id,
        grant_id=grant.grant_id,
        actor_did=ADVOCATE,
        actor_secret=delegate_secret,
    )
    artifact = app.analyze_record_with_invocation(
        wallet.wallet_id,
        record.record_id,
        actor_did=ADVOCATE,
        invocation=invocation,
        actor_secret=delegate_secret,
    )
    actions = [event["action"] for event in app.audit_timeline(wallet.wallet_id)]

    assert artifact.output_policy == "derived_only"
    assert "invocation/issue" in actions
    assert "invocation/verify" in actions


def test_wallet_interface_access_request_review_flow(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    owner_secret = b"o" * 32
    delegate_secret = b"d" * 32
    source = tmp_path / "access-request.txt"
    source.write_text("Food benefits and housing support notes.", encoding="utf-8")
    record = app.add_document(wallet.wallet_id, source, actor_did=OWNER, actor_secret=owner_secret)

    request = app.request_record_analysis_access(
        wallet.wallet_id,
        record.record_id,
        requester_did=ADVOCATE,
        purpose="benefits_screening",
    )
    inbox = app.list_access_requests(wallet.wallet_id)
    approved = app.approve_access_request(
        wallet.wallet_id,
        request_id=request.request_id,
        actor_did=OWNER,
        issuer_secret=owner_secret,
        audience_secret=delegate_secret,
        issue_invocation=True,
    )

    artifact = app.analyze_record_with_invocation(
        wallet.wallet_id,
        record.record_id,
        actor_did=ADVOCATE,
        invocation=app.wallet_service.invocations[approved.invocation_id],
        actor_secret=delegate_secret,
    )

    assert [item.request_id for item in inbox] == [request.request_id]
    assert approved.status == "approved"
    assert approved.grant_id is not None
    assert approved.invocation_id is not None
    assert artifact.artifact_type == "summary"


def test_wallet_interface_access_request_can_delegate_document_view(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    owner_secret = b"o" * 32
    delegate_secret = b"d" * 32
    source = tmp_path / "view-request.txt"
    source.write_text("Delegate may view this document after approval.", encoding="utf-8")
    record = app.add_document(wallet.wallet_id, source, actor_did=OWNER, actor_secret=owner_secret)

    request = app.request_record_access(
        wallet.wallet_id,
        record.record_id,
        requester_did=ADVOCATE,
        ability="record/decrypt",
        purpose="identity_verification",
    )
    approved = app.approve_access_request(
        wallet.wallet_id,
        request_id=request.request_id,
        actor_did=OWNER,
        issuer_secret=owner_secret,
        audience_secret=delegate_secret,
        issue_invocation=True,
    )
    plaintext = app.decrypt_record_with_invocation(
        wallet.wallet_id,
        record.record_id,
        actor_did=ADVOCATE,
        invocation=app.wallet_service.invocations[approved.invocation_id],
        actor_secret=delegate_secret,
    )

    assert approved.status == "approved"
    assert app.wallet_service.grants[approved.grant_id].abilities == ["record/decrypt"]
    assert plaintext == source.read_bytes()


def test_wallet_interface_revoked_access_blocks_invocation(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    owner_secret = b"o" * 32
    delegate_secret = b"d" * 32
    source = tmp_path / "revoked-view.txt"
    source.write_text("This view should be revoked.", encoding="utf-8")
    record = app.add_document(wallet.wallet_id, source, actor_did=OWNER, actor_secret=owner_secret)
    request = app.request_record_access(
        wallet.wallet_id,
        record.record_id,
        requester_did=ADVOCATE,
        ability="record/decrypt",
        purpose="identity_verification",
    )
    approved = app.approve_access_request(
        wallet.wallet_id,
        request_id=request.request_id,
        actor_did=OWNER,
        issuer_secret=owner_secret,
        audience_secret=delegate_secret,
        issue_invocation=True,
    )

    revoked = app.revoke_access_request(
        wallet.wallet_id,
        request_id=approved.request_id,
        actor_did=OWNER,
        reason="user withdrew consent",
    )

    assert revoked.status == "revoked"
    assert app.wallet_service.grants[approved.grant_id].status == "revoked"
    with pytest.raises(Exception, match="not active"):
        app.decrypt_record_with_invocation(
            wallet.wallet_id,
            record.record_id,
            actor_did=ADVOCATE,
            invocation=app.wallet_service.invocations[approved.invocation_id],
            actor_secret=delegate_secret,
        )


def test_wallet_interface_decrypt_access_request_respects_threshold_approval(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(
        OWNER,
        controller_dids=[OWNER, SECOND_CONTROLLER],
        approval_threshold=2,
    )
    owner_secret = b"o" * 32
    delegate_secret = b"d" * 32
    source = tmp_path / "threshold-view.txt"
    source.write_text("Threshold-protected document view.", encoding="utf-8")
    record = app.add_document(wallet.wallet_id, source, actor_did=OWNER, actor_secret=owner_secret)
    request = app.request_record_access(
        wallet.wallet_id,
        record.record_id,
        requester_did=ADVOCATE,
        ability="record/decrypt",
        purpose="identity_verification",
    )
    review = app.access_request_review_items(wallet.wallet_id)
    assert review[0]["approval_required"] is True
    assert review[0]["approval_count"] == 0

    with pytest.raises(Exception, match="approval_id is required"):
        app.approve_access_request(
            wallet.wallet_id,
            request_id=request.request_id,
            actor_did=OWNER,
            issuer_secret=owner_secret,
            audience_secret=delegate_secret,
        )

    approval = app.request_threshold_approval(
        wallet.wallet_id,
        requested_by=OWNER,
        operation="grant/create",
        resources=[resource_for_record(wallet.wallet_id, record.record_id)],
        abilities=["record/decrypt"],
    )
    review = app.access_request_review_items(wallet.wallet_id)
    assert review[0]["approval_id"] == approval.approval_id
    assert review[0]["approval_threshold"] == 2
    app.approve_threshold_approval(wallet.wallet_id, approval_id=approval.approval_id, approver_did=OWNER)
    approved_threshold = app.approve_threshold_approval(
        wallet.wallet_id,
        approval_id=approval.approval_id,
        approver_did=SECOND_CONTROLLER,
    )
    approved_access = app.approve_access_request(
        wallet.wallet_id,
        request_id=request.request_id,
        actor_did=OWNER,
        issuer_secret=owner_secret,
        audience_secret=delegate_secret,
        approval_id=approval.approval_id,
        issue_invocation=True,
    )

    assert approved_threshold.status == "approved"
    assert app.list_threshold_approvals(wallet.wallet_id, status="approved")[0].approval_id == approval.approval_id
    assert approved_access.status == "approved"


def test_wallet_interface_exposes_storage_health(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    source = tmp_path / "storage-health.txt"
    source.write_text("storage health plaintext", encoding="utf-8")
    record = app.add_document(wallet.wallet_id, source, actor_did=OWNER)

    report = app.verify_record_storage(wallet.wallet_id, record.record_id)
    repair = app.repair_record_storage(wallet.wallet_id, record.record_id, actor_did=OWNER)

    assert report.ok is True
    assert report.payload[0].role == "primary"
    assert repair.ok is True
    assert app.audit_timeline(wallet.wallet_id)[-1]["action"] == "storage/repair"


def test_wallet_interface_uses_configured_local_wallet_storage(tmp_path):
    app = WalletInterfaceService(
        services=_services(),
        storage_config={"type": "local", "root": tmp_path / "wallet-blobs"},
    )
    wallet = app.create_wallet(OWNER)

    record = app.add_text_document(
        wallet.wallet_id,
        actor_did=OWNER,
        filename="configured-storage.txt",
        text="encrypted local storage config",
    )
    version = app.wallet_service.versions[record.current_version_id]

    assert version.encrypted_payload_ref.storage_type == "local"
    assert version.encrypted_payload_ref.uri.startswith("local://")
    assert Path(version.encrypted_payload_ref.uri.removeprefix("local://")).exists()
    assert app.verify_record_storage(wallet.wallet_id, record.record_id).ok is True


def test_wallet_interface_reads_wallet_storage_env_config(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLET_STORAGE_TYPE", "local")
    monkeypatch.setenv("WALLET_STORAGE_ROOT", str(tmp_path / "env-wallet-blobs"))
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)

    record = app.add_text_document(
        wallet.wallet_id,
        actor_did=OWNER,
        filename="env-storage.txt",
        text="encrypted env storage config",
    )
    version = app.wallet_service.versions[record.current_version_id]

    assert version.encrypted_payload_ref.storage_type == "local"
    assert Path(version.encrypted_payload_ref.uri.removeprefix("local://")).exists()


def test_wallet_interface_repository_round_trips_wallet_snapshot(tmp_path):
    owner_secret = random_key()
    storage_config = {"type": "local", "root": tmp_path / "wallet-blobs"}
    app = WalletInterfaceService(
        services=_services(),
        storage_config=storage_config,
        repository_root=tmp_path / "wallet-repository",
    )
    wallet = app.create_wallet(OWNER)
    record = app.add_text_document(
        wallet.wallet_id,
        actor_did=OWNER,
        actor_secret=owner_secret,
        filename="repository.txt",
        text="repository persisted plaintext",
    )

    path = app.save_wallet_snapshot(wallet.wallet_id)
    report = app.verify_wallet_snapshot(wallet.wallet_id)

    restored = WalletInterfaceService(
        services=_services(),
        storage_config=storage_config,
        repository_root=tmp_path / "wallet-repository",
    )
    restored.load_wallet_snapshot(wallet.wallet_id)
    records = restored.list_records(wallet.wallet_id, data_type="document")
    plaintext = restored.wallet_service.decrypt_record(
        wallet.wallet_id,
        record.record_id,
        actor_did=OWNER,
        actor_secret=owner_secret,
    )

    assert path.exists()
    assert report["valid"] is True
    assert report["snapshot_hash"] == report["computed_hash"]
    assert app.list_wallet_snapshots() == [wallet.wallet_id]
    assert [item.record_id for item in records] == [record.record_id]
    assert plaintext.decode("utf-8") == "repository persisted plaintext"


def test_wallet_interface_auto_persists_and_loads_repository_snapshots(tmp_path):
    owner_secret = random_key()
    storage_config = {"type": "local", "root": tmp_path / "wallet-blobs"}
    repository_root = tmp_path / "wallet-repository"
    app = WalletInterfaceService(
        services=_services(),
        storage_config=storage_config,
        repository_root=repository_root,
    )
    wallet = app.create_wallet(OWNER)
    record = app.add_text_document(
        wallet.wallet_id,
        actor_did=OWNER,
        actor_secret=owner_secret,
        filename="auto-repository.txt",
        text="automatic repository persistence",
    )

    assert app.list_wallet_snapshots() == [wallet.wallet_id]

    restored = WalletInterfaceService(
        services=_services(),
        storage_config=storage_config,
        repository_root=repository_root,
    )
    records = restored.list_records(wallet.wallet_id, data_type="document")
    plaintext = restored.wallet_service.decrypt_record(
        wallet.wallet_id,
        record.record_id,
        actor_did=OWNER,
        actor_secret=owner_secret,
    )

    assert [item.record_id for item in records] == [record.record_id]
    assert plaintext.decode("utf-8") == "automatic repository persistence"


def test_wallet_interface_can_disable_auto_repository_persistence(tmp_path):
    app = WalletInterfaceService(
        services=_services(),
        repository_root=tmp_path / "wallet-repository",
        auto_persist=False,
    )
    wallet = app.create_wallet(OWNER)

    assert app.list_wallet_snapshots() == []
    assert not (tmp_path / "wallet-repository" / f"{wallet.wallet_id}.json").exists()


def test_wallet_interface_reads_repository_root_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WALLET_REPOSITORY_ROOT", str(tmp_path / "wallet-repository"))
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)

    path = app.save_wallet_snapshot(wallet.wallet_id)

    assert path.exists()
    assert app.list_wallet_snapshots() == [wallet.wallet_id]


def test_wallet_interface_private_analytics_count_release():
    app = WalletInterfaceService(services=_services())
    wallet1 = app.create_wallet("did:key:owner1")
    wallet2 = app.create_wallet("did:key:owner2")
    template_id = "housing_service_gap_v1"
    app.create_analytics_template(
        template_id=template_id,
        title="Housing service gaps",
        purpose="County-level housing planning",
        allowed_record_types=["location", "need"],
        allowed_derived_fields=["county", "need_category"],
        min_cohort_size=2,
        epsilon_budget=0.5,
        created_by="did:key:analyst",
    )

    for wallet, owner, county in [
        (wallet1, "did:key:owner1", "Multnomah"),
        (wallet2, "did:key:owner2", "Multnomah"),
    ]:
        consent = app.create_analytics_consent_from_template(
            wallet.wallet_id,
            actor_did=owner,
            template_id=template_id,
        )
        contribution = app.contribute_analytics_facts(
            wallet.wallet_id,
            actor_did=owner,
            consent_id=consent.consent_id,
            template_id=template_id,
            fields={"county": county, "need_category": "housing"},
        )
        assert app.wallet_service.verify_analytics_contribution(contribution.contribution_id) is True

    result = app.run_private_aggregate_count(template_id, epsilon=0.25)
    summary = app.summarize_aggregate_result(result)

    assert result.released is True
    assert result.count is None
    assert result.cohort_size == 0
    assert result.noisy_count is not None
    assert result.privacy_budget_spent == 0.25
    assert "differential-privacy:laplace" in result.privacy_notes
    assert app.list_analytics_templates()[0].template_id == template_id
    assert summary["count"] is None
    assert summary["noisy_count"] == result.noisy_count
    audit_actions = [event["action"] for event in app.audit_timeline(wallet1.wallet_id)]
    assert "analytics/query" in audit_actions


def test_wallet_interface_analytics_rejects_precise_location_fields():
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    template_id = "unsafe_location_study_v1"
    consent = app.create_analytics_consent(
        wallet.wallet_id,
        actor_did=OWNER,
        template_id=template_id,
        allowed_record_types=["location"],
        allowed_derived_fields=["lat"],
        min_cohort_size=2,
    )

    with pytest.raises(ValueError, match="precise coordinates"):
        app.contribute_analytics_facts(
            wallet.wallet_id,
            actor_did=OWNER,
            consent_id=consent.consent_id,
            template_id=template_id,
            fields={"lat": 45.515232},
        )


def test_wallet_interface_export_bundle_is_grant_scoped_and_encrypted(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(OWNER)
    source = tmp_path / "housing-notice.txt"
    source.write_text("Confidential housing notice", encoding="utf-8")
    document = app.add_document(wallet.wallet_id, source, actor_did=OWNER)
    location = app.add_location(wallet.wallet_id, actor_did=OWNER, lat=45.515232, lon=-122.678385)

    grant = app.create_export_grant(
        wallet.wallet_id,
        issuer_did=OWNER,
        audience_did=ADVOCATE,
        record_ids=[document.record_id, location.record_id],
    )
    bundle = app.create_export_bundle(
        wallet.wallet_id,
        actor_did=ADVOCATE,
        grant_id=grant.grant_id,
        record_ids=[document.record_id, location.record_id],
    )

    assert bundle["bundle_type"] == "wallet_export_v1"
    assert [record["data_type"] for record in bundle["records"]] == ["document", "location"]
    public_bundle = json.dumps(bundle)
    assert "Confidential housing notice" not in public_bundle
    assert "45.515232" not in public_bundle
    assert "-122.678385" not in public_bundle
    assert app.audit_timeline(wallet.wallet_id)[-1]["action"] == "export/create"


def test_wallet_interface_export_grant_respects_threshold_approval(tmp_path):
    app = WalletInterfaceService(services=_services())
    wallet = app.create_wallet(
        OWNER,
        controller_dids=[OWNER, SECOND_CONTROLLER],
        approval_threshold=2,
    )
    source = tmp_path / "export-approval.txt"
    source.write_text("Threshold gated export", encoding="utf-8")
    document = app.add_document(wallet.wallet_id, source, actor_did=OWNER)

    with pytest.raises(Exception, match="approval_id is required"):
        app.create_export_grant(
            wallet.wallet_id,
            issuer_did=OWNER,
            audience_did=ADVOCATE,
            record_ids=[document.record_id],
        )

    approval = app.request_threshold_approval(
        wallet.wallet_id,
        requested_by=OWNER,
        operation="grant/create",
        resources=[resource_for_export(wallet.wallet_id)],
        abilities=["export/create"],
    )
    app.approve_threshold_approval(wallet.wallet_id, approval_id=approval.approval_id, approver_did=OWNER)
    app.approve_threshold_approval(wallet.wallet_id, approval_id=approval.approval_id, approver_did=SECOND_CONTROLLER)
    grant = app.create_export_grant(
        wallet.wallet_id,
        issuer_did=OWNER,
        audience_did=ADVOCATE,
        record_ids=[document.record_id],
        approval_id=approval.approval_id,
    )

    assert grant.grant_id.startswith("grant-")
