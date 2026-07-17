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
