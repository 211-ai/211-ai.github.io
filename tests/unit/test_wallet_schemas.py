"""Unit tests for wallet_interface/schemas/ domain models.

These tests cover the pure Python dataclasses in app_schemas and the
Pydantic request schemas in wallet_schemas. They run without network
access or optional heavy dependencies.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# app_schemas — pure dataclasses, no optional deps required
# ---------------------------------------------------------------------------

class TestSavedServiceRecord:
    def _cls(self):
        from wallet_interface.schemas.app_schemas import SavedServiceRecord
        return SavedServiceRecord

    def test_required_fields(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="doc1",
            source_content_cid="bafyabc",
        )
        assert rec.saved_service_id == "s1"
        assert rec.wallet_id == "w1"
        assert rec.service_doc_id == "doc1"
        assert rec.source_content_cid == "bafyabc"

    def test_defaults(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="doc1",
            source_content_cid="bafyabc",
        )
        assert rec.priority == "normal"
        assert rec.status == "saved"
        assert rec.metadata == {}

    def test_to_dict_round_trip(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="doc1",
            source_content_cid="bafyabc",
            title="Housing Help",
            priority="high",
        )
        d = rec.to_dict()
        assert d["saved_service_id"] == "s1"
        assert d["title"] == "Housing Help"
        assert d["priority"] == "high"
        restored = cls.from_dict(d)
        assert restored.saved_service_id == rec.saved_service_id
        assert restored.title == rec.title
        assert restored.priority == rec.priority

    def test_from_dict_missing_keys_uses_defaults(self):
        cls = self._cls()
        rec = cls.from_dict({"saved_service_id": "s2", "wallet_id": "w1", "service_doc_id": "doc1", "source_content_cid": "bafyxyz"})
        assert rec.priority == "normal"
        assert rec.status == "saved"
        assert rec.metadata == {}

    def test_metadata_is_independent_copy(self):
        cls = self._cls()
        original = {"key": "value"}
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="doc1",
            source_content_cid="bafyabc",
            metadata=original,
        )
        d = rec.to_dict()
        d["metadata"]["extra"] = "injected"
        assert "extra" not in rec.metadata


class TestServicePlanRecord:
    def _cls(self):
        from wallet_interface.schemas.app_schemas import ServicePlanRecord
        return ServicePlanRecord

    def test_required_fields(self):
        cls = self._cls()
        plan = cls(plan_id="p1", wallet_id="w1", service_doc_id="doc1")
        assert plan.plan_id == "p1"
        assert plan.wallet_id == "w1"
        assert plan.status == "active"

    def test_steps_deduplicated_on_from_dict(self):
        cls = self._cls()
        plan = cls.from_dict({
            "plan_id": "p1",
            "wallet_id": "w1",
            "service_doc_id": "doc1",
            "steps": ["call", "call", "visit", ""],
        })
        assert plan.steps == ["call", "visit"]

    def test_to_dict_preserves_lists(self):
        cls = self._cls()
        plan = cls(
            plan_id="p1",
            wallet_id="w1",
            service_doc_id="doc1",
            steps=["step-a", "step-b"],
            documents_needed=["id", "proof"],
        )
        d = plan.to_dict()
        assert d["steps"] == ["step-a", "step-b"]
        assert d["documents_needed"] == ["id", "proof"]

    def test_round_trip(self):
        cls = self._cls()
        plan = cls(
            plan_id="p1",
            wallet_id="w1",
            service_doc_id="doc1",
            goal="Get housing assistance",
            status="active",
        )
        restored = cls.from_dict(plan.to_dict())
        assert restored.plan_id == plan.plan_id
        assert restored.goal == plan.goal
        assert restored.status == plan.status


class TestServiceInteractionRecord:
    def _cls(self):
        from wallet_interface.schemas.app_schemas import ServiceInteractionRecord
        return ServiceInteractionRecord

    def test_defaults(self):
        cls = self._cls()
        rec = cls(
            interaction_id="i1",
            wallet_id="w1",
            service_doc_id="doc1",
        )
        assert rec.privacy_level == "private"
        assert rec.related_grant_ids == []
        assert rec.metadata == {}

    def test_round_trip(self):
        cls = self._cls()
        rec = cls(
            interaction_id="i1",
            wallet_id="w1",
            service_doc_id="doc1",
            interaction_type="phone_call",
            channel="phone",
            outcome="Appointment scheduled",
        )
        restored = cls.from_dict(rec.to_dict())
        assert restored.interaction_id == rec.interaction_id
        assert restored.outcome == rec.outcome
        assert restored.interaction_type == rec.interaction_type

    def test_related_ids_deduplicated(self):
        cls = self._cls()
        rec = cls.from_dict({
            "interaction_id": "i1",
            "wallet_id": "w1",
            "service_doc_id": "doc1",
            "related_grant_ids": ["g1", "g1", "g2"],
        })
        assert rec.related_grant_ids == ["g1", "g2"]


# ---------------------------------------------------------------------------
# wallet_schemas — Pydantic request models
# ---------------------------------------------------------------------------

_PYDANTIC_AVAILABLE = True
try:
    import pydantic  # noqa: F401
except ImportError:
    _PYDANTIC_AVAILABLE = False

pytestmark_pydantic = pytest.mark.skipif(
    not _PYDANTIC_AVAILABLE, reason="pydantic not installed"
)


class TestCreateWalletRequestSchema:
    @pytestmark_pydantic
    def test_required_owner_did(self):
        from wallet_interface.schemas.wallet_schemas import CreateWalletRequest
        req = CreateWalletRequest(owner_did="did:key:abc")
        assert req.owner_did == "did:key:abc"

    @pytestmark_pydantic
    def test_defaults(self):
        from wallet_interface.schemas.wallet_schemas import CreateWalletRequest
        req = CreateWalletRequest(owner_did="did:key:abc")
        assert req.controller_dids == []
        assert req.approval_threshold is None

    @pytestmark_pydantic
    def test_controller_dids_populated(self):
        from wallet_interface.schemas.wallet_schemas import CreateWalletRequest
        req = CreateWalletRequest(
            owner_did="did:key:abc",
            controller_dids=["did:key:ctrl1", "did:key:ctrl2"],
            approval_threshold=2,
        )
        assert len(req.controller_dids) == 2
        assert req.approval_threshold == 2


class TestAddLocationRequestSchema:
    @pytestmark_pydantic
    def test_lat_lon_required(self):
        from wallet_interface.schemas.wallet_schemas import AddLocationRequest
        req = AddLocationRequest(actor_did="did:key:user", lat=45.523064, lon=-122.676483)
        assert req.lat == pytest.approx(45.523064)
        assert req.lon == pytest.approx(-122.676483)


class TestWalletRecoveryPolicySchema:
    @pytestmark_pydantic
    def test_threshold_default(self):
        from wallet_interface.schemas.wallet_schemas import WalletRecoveryPolicyRequest
        req = WalletRecoveryPolicyRequest(actor_did="did:key:x")
        assert req.threshold == 1
        assert req.contact_dids == []

    @pytestmark_pydantic
    def test_custom_threshold(self):
        from wallet_interface.schemas.wallet_schemas import WalletRecoveryPolicyRequest
        req = WalletRecoveryPolicyRequest(
            actor_did="did:key:x",
            contact_dids=["did:key:a", "did:key:b"],
            threshold=2,
        )
        assert req.threshold == 2
        assert len(req.contact_dids) == 2


# ---------------------------------------------------------------------------
# schemas __init__ re-exports everything correctly
# ---------------------------------------------------------------------------

class TestSchemasPackageExports:
    def test_app_schemas_importable(self):
        from wallet_interface.schemas import (  # noqa: F401
            SavedServiceRecord,
            ServiceInteractionRecord,
            ServicePlanRecord,
        )
        assert SavedServiceRecord is not None
        assert ServicePlanRecord is not None
        assert ServiceInteractionRecord is not None

    @pytestmark_pydantic
    def test_wallet_schemas_importable(self):
        from wallet_interface.schemas.wallet_schemas import AddLocationRequest, CreateWalletRequest  # noqa: F401
        assert CreateWalletRequest is not None

    @pytestmark_pydantic
    def test_proof_schemas_importable(self):
        from wallet_interface.schemas import LocationDistanceProofRequest, LocationRegionProofRequest  # noqa: F401
        assert LocationRegionProofRequest is not None

    @pytestmark_pydantic
    def test_export_schemas_importable(self):
        from wallet_interface.schemas import ExportBundleRequest  # noqa: F401
        assert ExportBundleRequest is not None
