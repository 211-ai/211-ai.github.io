"""Unit tests for HmisDomainServiceMixin in wallet_interface/services/hmis_service.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from wallet_interface.services.hmis_service import (
    DEFAULT_HMIS_FIXTURES,
    HMIS_AUDIT_FILENAME,
    HMIS_STATE_FILENAME,
    HMIS_STATE_TYPE,
    HmisDomainServiceMixin,
    _empty_hmis_state,
    _mask_hmis_candidate,
    _mask_name,
)

# ---------------------------------------------------------------------------
# Module-level helper tests
# ---------------------------------------------------------------------------


class TestMaskName:
    def test_single_word(self):
        assert _mask_name("Alice") == "A***"

    def test_two_words(self):
        result = _mask_name("Jane Doe")
        assert result == "J*** D***"

    def test_empty_string(self):
        assert _mask_name("") == ""

    def test_extra_whitespace(self):
        result = _mask_name("  Alice   Smith  ")
        assert result == "A*** S***"

    def test_none_like(self):
        # _mask_name coerces via str()
        assert _mask_name(None) == ""  # type: ignore[arg-type]


class TestMaskHmisCandidate:
    def test_masks_name(self):
        result = _mask_hmis_candidate({"name": "Jane Doe"})
        assert result["name"] == "J*** D***"
        assert result["masked"] is True

    def test_masks_phone_last_four(self):
        result = _mask_hmis_candidate({"phone": "503-555-0199"})
        assert result["phone"] == "***-***-0199"

    def test_masks_email(self):
        result = _mask_hmis_candidate({"email": "jane@example.org"})
        assert result["email"] == "j***@example.org"

    def test_masks_email_no_domain(self):
        result = _mask_hmis_candidate({"email": "noatsign"})
        assert result["email"] == "***"

    def test_masks_date_of_birth_to_year(self):
        result = _mask_hmis_candidate({"date_of_birth": "1990-04-05"})
        assert result["date_of_birth"] == "1990"

    def test_masks_household_name(self):
        result = _mask_hmis_candidate({"household_name": "Doe Family"})
        assert result["household_name"] == "D*** F***"

    def test_preserves_other_fields(self):
        result = _mask_hmis_candidate({"external_id": "abc", "score": 0.9})
        assert result["external_id"] == "abc"
        assert result["score"] == 0.9

    def test_does_not_mutate_original(self):
        original = {"name": "Jane Doe", "score": 1.0}
        _mask_hmis_candidate(original)
        assert original["name"] == "Jane Doe"


class TestEmptyHmisState:
    def test_snapshot_type(self):
        state = _empty_hmis_state()
        assert state["snapshot_type"] == HMIS_STATE_TYPE

    def test_empty_collections(self):
        state = _empty_hmis_state()
        assert state["referral_drafts"] == []
        assert state["verified_links"] == []
        assert state["rejected_matches"] == []
        assert state["reconciliation_items"] == []
        assert state["submissions"] == {}


class TestDefaultFixtures:
    def test_has_clients(self):
        assert len(DEFAULT_HMIS_FIXTURES["clients"]) >= 2

    def test_has_households(self):
        assert len(DEFAULT_HMIS_FIXTURES["households"]) >= 2

    def test_has_programs(self):
        assert len(DEFAULT_HMIS_FIXTURES["programs"]) >= 2

    def test_clients_have_required_fields(self):
        for client in DEFAULT_HMIS_FIXTURES["clients"]:
            assert "external_client_id" in client
            assert "name" in client


# ---------------------------------------------------------------------------
# Stub service that exercises HmisDomainServiceMixin without real deps
# ---------------------------------------------------------------------------


def _make_stub_service(tmp_path: Path):
    """Build a minimal stub instance of HmisDomainServiceMixin for tests."""

    class StubRepository:
        root = tmp_path

    class StubWalletService:
        def _wallet(self, wallet_id):
            return {"wallet_id": wallet_id}

    class StubService(HmisDomainServiceMixin):
        def __init__(self):
            self.repository = StubRepository()
            self.wallet_service = StubWalletService()
            self._hmis_fixture_imports = ()

        def _require_portal_actor(self, wallet_id, actor_did):
            pass  # no-op for unit tests

    return StubService()


# ---------------------------------------------------------------------------
# State persistence helpers
# ---------------------------------------------------------------------------


class TestHmisStatePersistence:
    def test_ensure_state_returns_empty_when_no_file(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        state = svc._ensure_hmis_state()
        assert state["snapshot_type"] == HMIS_STATE_TYPE
        assert state["referral_drafts"] == []

    def test_ensure_state_uses_cache(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        state1 = svc._ensure_hmis_state()
        state1["referral_drafts"].append({"id": "x"})
        state2 = svc._ensure_hmis_state()
        assert state2["referral_drafts"] == [{"id": "x"}]

    def test_save_and_reload_state(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        state = svc._ensure_hmis_state()
        state["referral_drafts"].append({"referral_draft_id": "test-draft"})
        svc._save_hmis_state()

        # Create a fresh instance to reload from disk
        svc2 = _make_stub_service(tmp_path)
        state2 = svc2._ensure_hmis_state()
        assert any(d.get("referral_draft_id") == "test-draft" for d in state2["referral_drafts"])

    def test_save_state_creates_file(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc._ensure_hmis_state()
        svc._save_hmis_state()
        assert (tmp_path / HMIS_STATE_FILENAME).exists()

    def test_load_state_rejects_wrong_type(self, tmp_path):
        bad_state = {"snapshot_type": "wrong-type", "referral_drafts": []}
        (tmp_path / HMIS_STATE_FILENAME).write_text(json.dumps(bad_state), encoding="utf-8")
        svc = _make_stub_service(tmp_path)
        with pytest.raises(ValueError, match="Unsupported HMIS state snapshot type"):
            svc._ensure_hmis_state()

    def test_state_path_uses_repository_root(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        assert svc._hmis_state_path() == tmp_path / HMIS_STATE_FILENAME

    def test_audit_path_uses_repository_root(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        assert svc._hmis_audit_path() == tmp_path / HMIS_AUDIT_FILENAME


# ---------------------------------------------------------------------------
# HMIS state operations: verify_hmis_match / reject_hmis_match
# ---------------------------------------------------------------------------


class TestVerifyHmisMatch:
    def test_adds_verified_link(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.verify_hmis_match(
            "wallet-1",
            actor_did="did:actor:test",
            entity_type="client",
            local_ref="local-1",
            external_id="ext-100",
            confidence=0.95,
        )
        assert result["status"] == "verified"
        assert result["confidence"] == 0.95
        state = svc._ensure_hmis_state()
        assert any(lnk["external_id"] == "ext-100" for lnk in state["verified_links"])

    def test_deduplicates_existing_link(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.verify_hmis_match(
            "wallet-1",
            actor_did="did:actor:test",
            entity_type="client",
            local_ref="local-1",
            external_id="ext-100",
            confidence=0.8,
        )
        svc.verify_hmis_match(
            "wallet-1",
            actor_did="did:actor:test",
            entity_type="client",
            local_ref="local-1",
            external_id="ext-200",
            confidence=0.99,
        )
        state = svc._ensure_hmis_state()
        matches = [lnk for lnk in state["verified_links"] if lnk["local_ref"] == "local-1"]
        assert len(matches) == 1
        assert matches[0]["external_id"] == "ext-200"


class TestRejectHmisMatch:
    def test_adds_rejected_record(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.reject_hmis_match(
            "wallet-1",
            actor_did="did:actor:test",
            entity_type="client",
            local_ref="local-1",
            external_id="ext-999",
            reason="wrong person",
        )
        assert result["reason"] == "wrong person"
        state = svc._ensure_hmis_state()
        assert any(r["external_id"] == "ext-999" for r in state["rejected_matches"])

    def test_rejected_id_excluded_from_next_lookup(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.reject_hmis_match(
            "wallet-1",
            actor_did="did:actor:test",
            entity_type="client",
            local_ref="local-1",
            external_id="client-100",
            reason="not a match",
        )
        state = svc._ensure_hmis_state()
        rejected_ids = [
            r["external_id"]
            for r in state["rejected_matches"]
            if r["wallet_id"] == "wallet-1" and r["entity_type"] == "client"
        ]
        assert "client-100" in rejected_ids


# ---------------------------------------------------------------------------
# Program links
# ---------------------------------------------------------------------------


class TestListHmisProgramLinks:
    def test_returns_empty_when_no_links(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        with patch.object(svc, "_load_program_links", return_value=[]):
            result = svc.list_hmis_program_links("wallet-1", actor_did="did:actor:test")
        assert result["status"] == "ok"
        assert result["program_links"] == []

    def test_filters_by_name(self, tmp_path):
        links = {
            "program_links": [
                {"program_name": "Shelter A", "provider_name": "Safe Harbor", "local_program_ref": "shelter-a"},
                {"program_name": "Food Bank", "provider_name": "Pantry Inc", "local_program_ref": "food-1"},
            ]
        }
        (tmp_path / "state" / "hmis").mkdir(parents=True)
        (tmp_path / "state" / "hmis" / "program_links.json").write_text(json.dumps(links))
        # Override Path resolution so _load_program_links finds it
        svc = _make_stub_service(tmp_path)
        with patch.object(svc, "_load_program_links", return_value=links["program_links"]):
            result = svc.list_hmis_program_links("wallet-1", actor_did="did:actor:test", name="shelter")
        assert len(result["program_links"]) == 1
        assert result["program_links"][0]["local_program_ref"] == "shelter-a"

    def test_filters_by_program_ref_substring(self, tmp_path):
        links = [
            {"program_name": "Shelter A", "provider_name": "Safe Harbor", "local_program_ref": "shelter-a"},
            {"program_name": "Food Bank", "provider_name": "Pantry Inc", "local_program_ref": "food-1"},
        ]
        svc = _make_stub_service(tmp_path)
        with patch.object(svc, "_load_program_links", return_value=links):
            result = svc.list_hmis_program_links("wallet-1", actor_did="did:actor:test", program_ref="shelter")
        assert len(result["program_links"]) == 1
        assert result["program_links"][0]["local_program_ref"] == "shelter-a"

    def test_returns_all_when_no_filter(self, tmp_path):
        links = [
            {"program_name": "Shelter A", "provider_name": "Safe Harbor", "local_program_ref": "shelter-a"},
            {"program_name": "Food Bank", "provider_name": "Pantry Inc", "local_program_ref": "food-1"},
        ]
        svc = _make_stub_service(tmp_path)
        with patch.object(svc, "_load_program_links", return_value=links):
            result = svc.list_hmis_program_links("wallet-1", actor_did="did:actor:test")
        assert len(result["program_links"]) == 2


# ---------------------------------------------------------------------------
# Referral drafts
# ---------------------------------------------------------------------------


class TestListHmisReferralDrafts:
    def test_returns_empty_for_new_wallet(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.list_hmis_referral_drafts("wallet-999")
        assert result == []

    def test_filters_by_wallet_id(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        state = svc._ensure_hmis_state()
        state["referral_drafts"].append({
            "referral_draft_id": "draft-a",
            "wallet_id": "wallet-1",
            "actor_id": "did:actor:test",
            "local_subject_ref": "ref-1",
            "destination_program_ref": "shelter-a",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        state["referral_drafts"].append({
            "referral_draft_id": "draft-b",
            "wallet_id": "wallet-2",
            "actor_id": "did:actor:test",
            "local_subject_ref": "ref-2",
            "destination_program_ref": "shelter-b",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        drafts = svc.list_hmis_referral_drafts("wallet-1")
        assert len(drafts) == 1
        assert drafts[0].referral_draft_id == "draft-a"

    def test_filters_by_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        state = svc._ensure_hmis_state()
        for status in ("draft", "ready", "draft"):
            state["referral_drafts"].append({
                "referral_draft_id": f"draft-{status}-{len(state['referral_drafts'])}",
                "wallet_id": "wallet-1",
                "actor_id": "did:actor:test",
                "local_subject_ref": "ref",
                "destination_program_ref": "prog",
                "status": status,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            })
        ready = svc.list_hmis_referral_drafts("wallet-1", status="ready")
        assert len(ready) == 1
        assert ready[0].status == "ready"


# ---------------------------------------------------------------------------
# Reconciliation queue helpers
# ---------------------------------------------------------------------------


class TestReconciliationQueue:
    def test_list_reconciliation_queue_returns_wallet_items(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        # Should return empty list when no items
        result = svc.list_hmis_reconciliation_queue("wallet-1")
        assert result["status"] == "ok"
        assert result["items"] == []

    def test_run_reconciliation_job_dry_run(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.run_hmis_reconciliation_job(dry_run=True)
        assert result["status"] == "dry-run"
        assert "queue_depth" in result

    def test_run_reconciliation_job_ok(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.run_hmis_reconciliation_job(dry_run=False)
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Phase 2: Lookup tests
# ---------------------------------------------------------------------------


class TestLookupHmisClients:
    def test_returns_ok_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff", name="Jane")
        assert result["status"] == "ok"

    def test_returns_clients_list(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff", name="Jane")
        assert "clients" in result

    def test_clients_are_masked(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff", name="Jane Doe")
        for client in result["clients"]:
            if "name" in client:
                assert "***" in client["name"]

    def test_returns_decision_field(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff")
        assert "decision" in result

    def test_empty_query_returns_candidates(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff")
        assert isinstance(result["clients"], list)

    def test_rejected_candidates_excluded(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        # First reject a match, then lookup should exclude it from main candidates
        svc.reject_hmis_match(
            "wallet-1",
            actor_did="did:test:staff",
            entity_type="client",
            local_ref="wallet-1",
            external_id="client-100",
            reason="wrong_person",
        )
        result = svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff", name="Jane")
        main_ids = [c.get("external_id") for c in result["clients"]]
        assert "client-100" not in main_ids


class TestLookupHmisHouseholds:
    def test_returns_ok_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_households("wallet-1", actor_did="did:test:staff", name="Doe")
        assert result["status"] == "ok"

    def test_returns_households_list(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_households("wallet-1", actor_did="did:test:staff")
        assert "households" in result

    def test_households_are_masked(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_households("wallet-1", actor_did="did:test:staff", name="Doe Household")
        for household in result["households"]:
            if "household_name" in household:
                assert "***" in household["household_name"]

    def test_returns_decision_field(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.lookup_hmis_households("wallet-1", actor_did="did:test:staff")
        assert "decision" in result


# ---------------------------------------------------------------------------
# Phase 3: Referral draft create / update / validate tests
# ---------------------------------------------------------------------------


class TestCreateHmisReferralDraft:
    def test_creates_draft_successfully(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test referral",
        )
        assert draft.referral_draft_id.startswith("hmis-referral-draft-")
        assert draft.wallet_id == "wallet-1"

    def test_draft_with_required_fields_is_ready(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test referral",
        )
        assert draft.status == "ready"
        assert draft.validation_errors == []

    def test_draft_missing_subject_has_error(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="",
            destination_program_ref="shelter-a",
            summary="Test referral",
        )
        assert draft.status == "draft"
        assert any("local_subject_ref" in e for e in draft.validation_errors)

    def test_draft_persisted_in_state(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test referral",
        )
        drafts = svc.list_hmis_referral_drafts("wallet-1")
        assert any(d.referral_draft_id == draft.referral_draft_id for d in drafts)

    def test_draft_metadata_stored(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test referral",
            metadata={"case_worker": "Alice"},
        )
        assert draft.metadata.get("case_worker") == "Alice"


class TestUpdateHmisReferralDraft:
    def _create_draft(self, svc):
        return svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Initial summary",
        )

    def test_update_summary_field(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = self._create_draft(svc)
        updated = svc.update_hmis_referral_draft(
            "wallet-1",
            draft.referral_draft_id,
            actor_did="did:test:staff",
            summary="Updated summary",
        )
        assert updated.summary == "Updated summary"

    def test_update_program_ref(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = self._create_draft(svc)
        updated = svc.update_hmis_referral_draft(
            "wallet-1",
            draft.referral_draft_id,
            actor_did="did:test:staff",
            destination_program_ref="rapid-rehousing",
        )
        assert updated.destination_program_ref == "rapid-rehousing"

    def test_update_nonexistent_draft_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            svc.update_hmis_referral_draft(
                "wallet-1",
                "nonexistent-draft-id",
                actor_did="did:test:staff",
                summary="New summary",
            )

    def test_update_merges_metadata(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test",
            metadata={"key_a": "val_a"},
        )
        updated = svc.update_hmis_referral_draft(
            "wallet-1",
            draft.referral_draft_id,
            actor_did="did:test:staff",
            metadata={"key_b": "val_b"},
        )
        assert updated.metadata.get("key_a") == "val_a"
        assert updated.metadata.get("key_b") == "val_b"


class TestValidateHmisReferralDraft:
    def test_valid_draft_has_no_errors(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test referral",
        )
        result = svc.validate_hmis_referral_draft(
            "wallet-1",
            draft.referral_draft_id,
            actor_did="did:test:staff",
        )
        assert result["errors"] == []
        assert result["status"] == "ready"

    def test_nonexistent_draft_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            svc.validate_hmis_referral_draft("wallet-1", "no-such-id", actor_did="did:test:staff")

    def test_returns_referral_draft_in_result(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test referral",
        )
        result = svc.validate_hmis_referral_draft(
            "wallet-1",
            draft.referral_draft_id,
            actor_did="did:test:staff",
        )
        assert "referral_draft" in result
        assert result["referral_draft"]["referral_draft_id"] == draft.referral_draft_id


# ---------------------------------------------------------------------------
# Phase 4: Submission and sync tests
# ---------------------------------------------------------------------------


class TestSubmitHmisReferralDraft:
    def _ready_draft(self, svc):
        return svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Complete referral with all fields",
            provider_name="Safe Harbor",
            program_name="Emergency Shelter",
        )

    def test_submit_ready_draft_returns_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = self._ready_draft(svc)
        result = svc.submit_hmis_referral_draft("wallet-1", draft.referral_draft_id, actor_did="did:test:staff")
        assert result["status"] in {"submitted", "retryable", "needs_review"}

    def test_submit_nonexistent_draft_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            svc.submit_hmis_referral_draft("wallet-1", "no-such-id", actor_did="did:test:staff")

    def test_submit_invalid_draft_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        # Create draft with missing required field (no summary)
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="",  # empty summary will cause validation error
        )
        with pytest.raises(ValueError, match="validation errors"):
            svc.submit_hmis_referral_draft("wallet-1", draft.referral_draft_id, actor_did="did:test:staff")

    def test_submit_returns_referral_draft(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = self._ready_draft(svc)
        result = svc.submit_hmis_referral_draft("wallet-1", draft.referral_draft_id, actor_did="did:test:staff")
        assert "referral_draft" in result
        assert result["referral_draft"]["referral_draft_id"] == draft.referral_draft_id


class TestListHmisSyncTimeline:
    def test_returns_ok_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.list_hmis_sync_timeline("wallet-1")
        assert result["status"] == "ok"

    def test_returns_events_list(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.list_hmis_sync_timeline("wallet-1")
        assert "events" in result
        assert isinstance(result["events"], list)

    def test_events_contain_required_fields(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        # Perform a lookup to create an audit event
        svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff", name="Jane")
        result = svc.list_hmis_sync_timeline("wallet-1")
        for event in result["events"]:
            assert "event_id" in event
            assert "action_type" in event
            assert "status" in event

    def test_filter_by_local_ref(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff")
        result = svc.list_hmis_sync_timeline("wallet-1", local_ref="wallet-1")
        assert result["status"] == "ok"

    def test_filters_out_events_from_other_wallets(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.lookup_hmis_clients("wallet-1", actor_did="did:test:staff", name="Jane")
        svc.lookup_hmis_clients("wallet-2", actor_did="did:test:staff", name="John")

        result = svc.list_hmis_sync_timeline("wallet-1")

        assert result["events"]
        assert {event["metadata"].get("wallet_id") for event in result["events"]} == {"wallet-1"}


class TestHmisProgramLinksLoading:
    def test_uses_configured_repository_root(self, tmp_path, monkeypatch):
        svc = _make_stub_service(tmp_path)
        links = {
            "program_links": [
                {
                    "local_program_ref": "shelter-a",
                    "external_project_id": "HMIS-PROJECT-100",
                    "program_name": "Emergency Shelter",
                }
            ]
        }
        path = tmp_path / "state" / "hmis" / "program_links.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(links), encoding="utf-8")
        monkeypatch.chdir(tmp_path / "state")

        assert svc._load_program_links() == links["program_links"]


class TestRetryHmisReconciliationItem:
    def test_retry_nonexistent_item_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            svc.retry_hmis_reconciliation_item("wallet-1", "no-such-item", actor_did="did:test:staff")

    def test_retry_item_returns_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        # Submit a referral to create a reconciliation item via error path
        # Build ready draft first
        draft = svc.create_hmis_referral_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            summary="Test",
            provider_name="Safe Harbor",
            program_name="Emergency Shelter",
        )
        # Manually inject a reconciliation item
        from wallet_interface.hmis.service import HmisReconciliationItem

        state = svc._ensure_hmis_state()
        item = HmisReconciliationItem(
            item_id="recon-test-001",
            wallet_id="wallet-1",
            referral_draft_id=draft.referral_draft_id,
            local_ref=draft.referral_draft_id,
            reason="test_retry",
            status="open",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        state.setdefault("reconciliation_items", []).append(item.to_dict())
        # Invalidate cache so the service reloads
        svc._hmis_submission_service_cache = None  # type: ignore[attr-defined]
        result = svc.retry_hmis_reconciliation_item("wallet-1", "recon-test-001", actor_did="did:test:staff")
        assert "status" in result


# ---------------------------------------------------------------------------
# Phase 5: Enrollment draft tests
# ---------------------------------------------------------------------------


class TestEmptyHmisStateHasEnrollmentDrafts:
    def test_enrollment_drafts_in_empty_state(self):
        from wallet_interface.services.hmis_service import _empty_hmis_state

        state = _empty_hmis_state()
        assert "enrollment_drafts" in state
        assert state["enrollment_drafts"] == []


class TestListHmisEnrollmentDrafts:
    def test_returns_empty_for_new_wallet(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        result = svc.list_hmis_enrollment_drafts("wallet-1")
        assert result == []

    def test_filters_by_wallet_id(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        svc.create_hmis_enrollment_draft(
            "wallet-2",
            actor_did="did:test:staff",
            local_subject_ref="subject-2",
            destination_program_ref="shelter-b",
        )
        wallet1_drafts = svc.list_hmis_enrollment_drafts("wallet-1")
        assert all(d.get("wallet_id") == "wallet-1" for d in wallet1_drafts)
        assert len(wallet1_drafts) == 1

    def test_filters_by_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        ready_drafts = svc.list_hmis_enrollment_drafts("wallet-1", status="ready")
        draft_drafts = svc.list_hmis_enrollment_drafts("wallet-1", status="draft")
        assert len(ready_drafts) + len(draft_drafts) >= 1


class TestCreateHmisEnrollmentDraft:
    def test_creates_draft_successfully(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        assert draft["enrollment_draft_id"].startswith("hmis-enrollment-draft-")
        assert draft["wallet_id"] == "wallet-1"

    def test_draft_with_required_fields_is_ready(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        assert draft["status"] == "ready"
        assert draft["validation_errors"] == []

    def test_draft_missing_subject_has_error(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="",
            destination_program_ref="shelter-a",
        )
        assert draft["status"] == "draft"
        assert any("local_subject_ref" in e for e in draft["validation_errors"])

    def test_draft_missing_program_ref_has_error(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="",
        )
        assert draft["status"] == "draft"
        assert any("destination_program_ref" in e for e in draft["validation_errors"])

    def test_draft_persisted_in_state(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        all_drafts = svc.list_hmis_enrollment_drafts("wallet-1")
        assert any(d.get("enrollment_draft_id") == draft["enrollment_draft_id"] for d in all_drafts)

    def test_optional_fields_stored(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
            entry_date="2026-07-01",
            household_ref="household-100",
            summary="New enrollment for shelter",
            metadata={"priority": "high"},
        )
        assert draft["entry_date"] == "2026-07-01"
        assert draft["household_ref"] == "household-100"
        assert draft["summary"] == "New enrollment for shelter"
        assert draft["metadata"]["priority"] == "high"

    def test_creates_audit_record(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        timeline = svc.list_hmis_sync_timeline("wallet-1")
        action_types = [e["action_type"] for e in timeline["events"]]
        assert "create_enrollment_draft" in action_types


class TestSubmitHmisEnrollmentDraft:
    def test_submit_ready_draft_returns_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        result = svc.submit_hmis_enrollment_draft(
            "wallet-1",
            draft["enrollment_draft_id"],
            actor_did="did:test:staff",
        )
        assert result["status"] in {"submitted", "retryable", "needs_review"}

    def test_submit_nonexistent_draft_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            svc.submit_hmis_enrollment_draft("wallet-1", "no-such-id", actor_did="did:test:staff")

    def test_submit_invalid_draft_raises(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="",
            destination_program_ref="shelter-a",
        )
        with pytest.raises(ValueError, match="validation errors"):
            svc.submit_hmis_enrollment_draft(
                "wallet-1",
                draft["enrollment_draft_id"],
                actor_did="did:test:staff",
            )

    def test_submit_returns_enrollment_draft(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        result = svc.submit_hmis_enrollment_draft(
            "wallet-1",
            draft["enrollment_draft_id"],
            actor_did="did:test:staff",
        )
        assert "enrollment_draft" in result
        assert result["enrollment_draft"]["enrollment_draft_id"] == draft["enrollment_draft_id"]

    def test_submit_updates_draft_status(self, tmp_path):
        svc = _make_stub_service(tmp_path)
        draft = svc.create_hmis_enrollment_draft(
            "wallet-1",
            actor_did="did:test:staff",
            local_subject_ref="subject-1",
            destination_program_ref="shelter-a",
        )
        svc.submit_hmis_enrollment_draft(
            "wallet-1",
            draft["enrollment_draft_id"],
            actor_did="did:test:staff",
        )
        drafts = svc.list_hmis_enrollment_drafts("wallet-1")
        updated = next(d for d in drafts if d["enrollment_draft_id"] == draft["enrollment_draft_id"])
        assert updated["status"] != "ready"
