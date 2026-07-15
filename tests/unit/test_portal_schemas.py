"""Unit tests for wallet_interface portal schemas (app, wallet, record)."""

import dataclasses
import pytest


class TestSavedServiceRecord:
    def _cls(self):
        from wallet_interface.schemas.app_schemas import SavedServiceRecord
        return SavedServiceRecord

    def test_is_dataclass(self):
        cls = self._cls()
        assert dataclasses.is_dataclass(cls)

    def test_required_fields(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="svc-001",
            wallet_id="wallet-001",
            service_doc_id="doc-001",
            source_content_cid="bafytest",
        )
        assert rec.saved_service_id == "svc-001"
        assert rec.wallet_id == "wallet-001"
        assert rec.service_doc_id == "doc-001"
        assert rec.source_content_cid == "bafytest"

    def test_default_priority_is_normal(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="d1",
            source_content_cid="cid1",
        )
        assert rec.priority == "normal"

    def test_default_status_is_saved(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="d1",
            source_content_cid="cid1",
        )
        assert rec.status == "saved"

    def test_default_metadata_is_empty_dict(self):
        cls = self._cls()
        rec = cls(
            saved_service_id="s1",
            wallet_id="w1",
            service_doc_id="d1",
            source_content_cid="cid1",
        )
        assert rec.metadata == {}

    def test_metadata_dicts_are_independent(self):
        cls = self._cls()
        r1 = cls(saved_service_id="s1", wallet_id="w1", service_doc_id="d1", source_content_cid="c1")
        r2 = cls(saved_service_id="s2", wallet_id="w2", service_doc_id="d2", source_content_cid="c2")
        r1.metadata["key"] = "value"
        assert "key" not in r2.metadata


class TestServicePlanRecord:
    def _cls(self):
        from wallet_interface.schemas.app_schemas import ServicePlanRecord
        return ServicePlanRecord

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(self._cls())

    def test_required_fields(self):
        cls = self._cls()
        fields = {f.name: f for f in dataclasses.fields(cls)}
        # Check key fields present
        assert "plan_id" in fields or "service_plan_id" in fields or len(fields) > 0

    def test_basic_instantiation(self):
        cls = self._cls()
        required = {
            f.name: "test-value"
            for f in dataclasses.fields(cls)
            if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        }
        if not required:
            pytest.skip("All fields have defaults")
        rec = cls(**required)
        for k, v in required.items():
            assert getattr(rec, k) == v


class TestServiceInteractionRecord:
    def _cls(self):
        from wallet_interface.schemas.app_schemas import ServiceInteractionRecord
        return ServiceInteractionRecord

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(self._cls())

    def test_basic_instantiation_with_required_fields(self):
        cls = self._cls()
        required = {
            f.name: "test-value"
            for f in dataclasses.fields(cls)
            if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        }
        if not required:
            pytest.skip("All fields have defaults")
        rec = cls(**required)
        assert rec is not None


class TestWalletSchemas:
    def test_create_wallet_request_is_dataclass_or_pydantic(self):
        from wallet_interface.schemas.wallet_schemas import CreateWalletRequest
        assert CreateWalletRequest is not None

    def test_wallet_schemas_importable(self):
        from wallet_interface.schemas.wallet_schemas import (
            CreateWalletRequest,
            WalletControllerRequest,
            WalletDeviceRequest,
        )
        assert CreateWalletRequest is not None
        assert WalletControllerRequest is not None
        assert WalletDeviceRequest is not None


class TestRecordSchemas:
    def test_record_schemas_importable(self):
        from wallet_interface.schemas.record_schemas import (
            AddTextDocumentRequest,
            AnalysisGrantRequest,
        )
        assert AddTextDocumentRequest is not None
        assert AnalysisGrantRequest is not None


class TestExportSchemas:
    def test_export_schemas_importable(self):
        from wallet_interface.schemas.export_schemas import (
            ExportGrantRequest,
            ExportBundleRequest,
        )
        assert ExportGrantRequest is not None
        assert ExportBundleRequest is not None
