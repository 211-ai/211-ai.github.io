"""Unit tests for wallet_interface proof, record, and export request schemas.

Covers:
  wallet_interface/schemas/proof_schemas.py
  wallet_interface/schemas/record_schemas.py
  wallet_interface/schemas/export_schemas.py
"""

from __future__ import annotations

import pytest


def _skip_if_no_pydantic():
    try:
        import pydantic  # noqa: F401
    except ImportError:
        pytest.skip("pydantic not installed")


# ---------------------------------------------------------------------------
# proof_schemas
# ---------------------------------------------------------------------------

class TestCoarseLocationGrantRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import CoarseLocationGrantRequest

        req = CoarseLocationGrantRequest(issuer_did="did:key:owner", audience_did="did:key:delegate")
        assert req.issuer_did == "did:key:owner"
        assert req.audience_did == "did:key:delegate"
        assert req.issuer_key_hex is None
        assert req.audience_key_hex is None
        assert req.expires_at is None

    def test_optional_fields_accepted(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import CoarseLocationGrantRequest

        req = CoarseLocationGrantRequest(
            issuer_did="did:key:a",
            audience_did="did:key:b",
            issuer_key_hex="aabbcc",
            audience_key_hex="ddeeff",
            expires_at="2099-01-01T00:00:00Z",
        )
        assert req.issuer_key_hex == "aabbcc"
        assert req.expires_at == "2099-01-01T00:00:00Z"


class TestCoarseLocationInvocationRequest:
    def test_defaults(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import CoarseLocationInvocationRequest

        req = CoarseLocationInvocationRequest(grant_id="g1", actor_did="did:key:actor")
        assert req.grant_id == "g1"
        assert req.user_present is False
        assert req.purpose is None

    def test_user_present_true(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import CoarseLocationInvocationRequest

        req = CoarseLocationInvocationRequest(
            grant_id="g1", actor_did="did:key:actor", user_present=True
        )
        assert req.user_present is True


class TestLocationRegionProofGrantRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import LocationRegionProofGrantRequest

        req = LocationRegionProofGrantRequest(issuer_did="did:key:a", audience_did="did:key:b")
        assert req.expires_at is None


class TestLocationRegionProofRequest:
    def test_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import LocationRegionProofRequest

        req = LocationRegionProofRequest(actor_did="did:key:actor", region_id="multnomah_county")
        assert req.region_id == "multnomah_county"
        assert req.grant_id is None


class TestLocationDistanceProofGrantRequest:
    def test_numeric_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import LocationDistanceProofGrantRequest

        req = LocationDistanceProofGrantRequest(
            issuer_did="did:key:a",
            audience_did="did:key:b",
            target_id="shelter-123",
            max_distance_km=5.0,
        )
        assert req.max_distance_km == 5.0
        assert req.target_id == "shelter-123"


class TestLocationDistanceProofRequest:
    def test_coordinates(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import LocationDistanceProofRequest

        req = LocationDistanceProofRequest(
            actor_did="did:key:actor",
            target_id="shelter-1",
            target_lat=45.5,
            target_lon=-122.7,
            max_distance_km=2.0,
        )
        assert req.target_lat == 45.5
        assert req.target_lon == -122.7
        assert req.grant_id is None


class TestDocumentPrivacyProfileProofRequest:
    def test_default_public_inputs(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import DocumentPrivacyProfileProofRequest

        req = DocumentPrivacyProfileProofRequest(actor_did="did:key:actor")
        assert req.public_inputs == {}

    def test_custom_public_inputs(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.proof_schemas import DocumentPrivacyProfileProofRequest

        req = DocumentPrivacyProfileProofRequest(
            actor_did="did:key:actor",
            public_inputs={"category": "benefits"},
        )
        assert req.public_inputs["category"] == "benefits"


# ---------------------------------------------------------------------------
# record_schemas
# ---------------------------------------------------------------------------

class TestAddTextDocumentRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import AddTextDocumentRequest

        req = AddTextDocumentRequest(actor_did="did:key:actor", text="hello world")
        assert req.filename == "document.txt"
        assert req.title is None
        assert req.key_hex is None

    def test_custom_filename(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import AddTextDocumentRequest

        req = AddTextDocumentRequest(actor_did="did:key:actor", text="body", filename="notes.txt")
        assert req.filename == "notes.txt"


class TestRecordGrantRequest:
    def test_defaults(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import RecordGrantRequest

        req = RecordGrantRequest(issuer_did="did:key:issuer", audience_did="did:key:audience")
        assert "record/analyze" in req.abilities
        assert req.purpose == "service_matching"
        assert req.user_presence_required is False
        assert req.caveats == {}
        assert req.max_delegation_depth is None

    def test_custom_abilities(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import RecordGrantRequest

        req = RecordGrantRequest(
            issuer_did="did:key:issuer",
            audience_did="did:key:audience",
            abilities=["record/read", "record/analyze"],
        )
        assert "record/read" in req.abilities


class TestAnalysisGrantRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import AnalysisGrantRequest

        req = AnalysisGrantRequest(issuer_did="did:key:a", audience_did="did:key:b")
        assert req.issuer_key_hex is None


class TestAnalysisInvocationRequest:
    def test_defaults(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import AnalysisInvocationRequest

        req = AnalysisInvocationRequest(grant_id="g1", actor_did="did:key:actor")
        assert req.user_present is False
        assert req.output_types == []


class TestAccessRequestCreateRequest:
    def test_defaults(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import AccessRequestCreateRequest

        req = AccessRequestCreateRequest(record_id="rec-1", requester_did="did:key:req")
        assert req.ability == "record/analyze"
        assert req.purpose == "service_matching"
        assert req.audience_did is None


class TestAccessRequestDecisionRequest:
    def test_fields_present(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import AccessRequestDecisionRequest

        req = AccessRequestDecisionRequest(actor_did="did:key:actor")
        assert req.actor_did == "did:key:actor"
        assert req.issue_invocation is False
        assert req.reason is None


class TestRevokeGrantRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import RevokeGrantRequest

        req = RevokeGrantRequest(actor_did="did:key:actor")
        assert req.actor_did == "did:key:actor"


class TestEmergencyRevokeRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import EmergencyRevokeRequest

        req = EmergencyRevokeRequest(actor_did="did:key:actor")
        assert req.actor_did == "did:key:actor"


class TestDelegateGrantRequest:
    def test_defaults(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import DelegateGrantRequest

        req = DelegateGrantRequest(
            issuer_did="did:key:a",
            audience_did="did:key:b",
        )
        assert req.abilities == []
        assert req.resources == []


class TestSavedServiceRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import SavedServiceRequest

        req = SavedServiceRequest(
            actor_did="did:key:actor",
            service_doc_id="doc-1",
            source_content_cid="bafybeig...",
        )
        assert req.service_doc_id == "doc-1"
        assert req.label == ""

    def test_optional_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import SavedServiceRequest

        req = SavedServiceRequest(
            actor_did="did:key:a",
            service_doc_id="d",
            source_content_cid="cid",
            label="shelter",
        )
        assert req.label == "shelter"


class TestServicePlanRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import ServicePlanRequest

        req = ServicePlanRequest(actor_did="did:key:actor", service_doc_id="doc-1")
        assert req.service_doc_id == "doc-1"
        assert req.goal == ""

    def test_steps_default_empty(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.record_schemas import ServicePlanRequest

        req = ServicePlanRequest(actor_did="did:key:actor", service_doc_id="d")
        assert req.steps == []


# ---------------------------------------------------------------------------
# export_schemas
# ---------------------------------------------------------------------------

class TestExportGrantRequest:
    def test_required_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.export_schemas import ExportGrantRequest

        req = ExportGrantRequest(issuer_did="did:key:issuer", audience_did="did:key:audience")
        assert req.issuer_did == "did:key:issuer"
        assert req.expires_at is None

    def test_record_ids_default_empty(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.export_schemas import ExportGrantRequest

        req = ExportGrantRequest(issuer_did="did:key:a", audience_did="did:key:b")
        assert req.record_ids == []


class TestExportBundleRequest:
    def test_fields(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.export_schemas import ExportBundleRequest

        req = ExportBundleRequest(actor_did="did:key:actor", grant_id="grant-1")
        assert req.actor_did == "did:key:actor"
        assert req.grant_id == "grant-1"
        assert req.record_ids == []


class TestExportBundleVerifyRequest:
    def test_required_bundle_field(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.export_schemas import ExportBundleVerifyRequest

        req = ExportBundleVerifyRequest(bundle={"bundle_id": "b1"})
        assert req.bundle["bundle_id"] == "b1"


class TestExportBundleImportRequest:
    def test_required_bundle_field(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.export_schemas import ExportBundleImportRequest

        req = ExportBundleImportRequest(bundle={"bundle_id": "b1"})
        assert req.bundle["bundle_id"] == "b1"


class TestExportInvocationRequest:
    def test_defaults(self):
        _skip_if_no_pydantic()
        from wallet_interface.schemas.export_schemas import ExportInvocationRequest

        req = ExportInvocationRequest(grant_id="grant-1", actor_did="did:key:actor")
        assert req.grant_id == "grant-1"
        assert req.user_present is False
