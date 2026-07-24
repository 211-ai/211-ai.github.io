"""Record, grant, export, and storage helpers for WalletInterfaceService."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet.ucan import resource_for_export, resource_for_record  # noqa: E402


class RecordDomainServiceMixin:
    def add_document(
        self,
        wallet_id: str,
        path: str | Path,
        *,
        actor_did: str,
        actor_secret: bytes | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        record = self.wallet_service.add_document(
            wallet_id,
            path,
            actor_did=actor_did,
            actor_secret=actor_secret,
            metadata=metadata,
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def add_text_document(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        text: str,
        actor_secret: bytes | None = None,
        filename: str = "document.txt",
        metadata: dict[str, Any] | None = None,
    ):
        private_metadata = {"filename": filename, **(metadata or {})}
        record = self.wallet_service.add_record(
            wallet_id,
            data_type="document",
            plaintext=text.encode("utf-8"),
            actor_did=actor_did,
            actor_secret=actor_secret,
            private_metadata=private_metadata,
            sensitivity="restricted",
            public_descriptor="document",
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def add_binary_document(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        data: bytes,
        actor_secret: bytes | None = None,
        filename: str = "document.bin",
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        private_metadata = {
            "filename": filename,
            "content_type": content_type or "application/octet-stream",
            **(metadata or {}),
        }
        record = self.wallet_service.add_record(
            wallet_id,
            data_type="document",
            plaintext=data,
            actor_did=actor_did,
            actor_secret=actor_secret,
            private_metadata=private_metadata,
            sensitivity="restricted",
            public_descriptor="document",
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def list_records(self, wallet_id: str, *, data_type: str | None = None):
        self.wallet_service._wallet(wallet_id)
        records = [
            record
            for record in self.wallet_service.records.values()
            if record.wallet_id == wallet_id
        ]
        if data_type is not None:
            records = [record for record in records if record.data_type == data_type]
        return sorted(records, key=lambda item: item.created_at)

    def update_record_metadata(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Persist a record metadata patch through the canonical wallet service."""

        record = self.wallet_service.update_record_metadata(
            wallet_id,
            record_id,
            actor_did=actor_did,
            metadata=metadata,
        )
        self._persist_wallet_if_configured(wallet_id)
        return record

    def record_to_dict(self, record: Any) -> dict[str, Any]:
        """Serialize a DataRecord to a plain dict."""
        if hasattr(record, "to_dict"):
            return record.to_dict()
        return {k: v for k, v in vars(record).items() if not k.startswith("_")}


    def create_record_analysis_grant(
        self,
        wallet_id: str,
        record_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        issuer_secret: bytes | None = None,
        audience_secret: bytes | None = None,
        output_types: Sequence[str] = ("summary",),
        expires_at: str | None = None,
    ):
        grant = self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_record(wallet_id, record_id)],
            abilities=["record/analyze"],
            caveats={"output_types": list(output_types), "purpose": "service_matching"},
            expires_at=expires_at,
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
        )
        self._persist_wallet_if_configured(wallet_id)
        return grant


    def create_record_grant(
        self,
        wallet_id: str,
        record_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        abilities: Sequence[str],
        purpose: str = "service_matching",
        issuer_secret: bytes | None = None,
        audience_secret: bytes | None = None,
        approval_id: str | None = None,
        expires_at: str | None = None,
        max_delegation_depth: int | None = None,
        output_types: Sequence[str] | None = None,
        user_presence_required: bool = False,
        extra_caveats: Mapping[str, Any] | None = None,
    ):
        allowed_abilities = {"record/analyze", "record/decrypt", "record/share"}
        normalized_abilities = []
        for ability in abilities:
            if ability not in allowed_abilities:
                raise ValueError(f"record grants do not support ability: {ability}")
            if ability not in normalized_abilities:
                normalized_abilities.append(ability)
        if not normalized_abilities:
            raise ValueError("record grants require at least one ability")
        if normalized_abilities == ["record/share"]:
            raise ValueError("record/share must be paired with analyze or decrypt access")

        caveats: dict[str, Any] = dict(extra_caveats or {})
        caveats["purpose"] = purpose or caveats.get("purpose") or "service_matching"
        if output_types is not None:
            caveats["output_types"] = list(output_types)
        elif "output_types" not in caveats and "allowed_output_types" not in caveats:
            default_output_types = []
            if "record/analyze" in normalized_abilities:
                default_output_types.append("summary")
            if "record/decrypt" in normalized_abilities:
                default_output_types.append("plaintext")
            if default_output_types:
                caveats["output_types"] = default_output_types
        if user_presence_required:
            caveats["user_presence_required"] = True
        if max_delegation_depth is not None:
            caveats["max_delegation_depth"] = max(0, int(max_delegation_depth))

        grant = self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_record(wallet_id, record_id)],
            abilities=normalized_abilities,
            caveats=caveats,
            expires_at=expires_at,
            approval_id=approval_id,
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
        )
        self._persist_wallet_if_configured(wallet_id)
        return grant


    def analyze_record_for_delegate(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        grant_id: str,
        actor_secret: bytes | None = None,
        max_chars: int = 200,
    ):
        artifact = self.wallet_service.analyze_record_summary(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            max_chars=max_chars,
        )
        self._persist_wallet_if_configured(wallet_id)
        return artifact


    def analyze_record_redacted(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
        max_chars: int = 500,
    ) -> dict[str, Any]:
        result = self.wallet_service.analyze_document_with_redaction(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            max_chars=max_chars,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def analyze_record_redacted_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        max_chars: int = 500,
    ) -> dict[str, Any]:
        self.wallet_service.verify_invocation(
            wallet_id,
            invocation,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/analyze",
            actor_secret=actor_secret,
        )
        result = self.wallet_service.analyze_document_with_redaction(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=invocation.grant_id,
            actor_secret=actor_secret,
            max_chars=max_chars,
            invocation_caveats=invocation.caveats,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def create_document_vector_profile(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
        chunk_size_words: int = 80,
    ) -> dict[str, Any]:
        result = self.wallet_service.create_document_vector_profile(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            chunk_size_words=chunk_size_words,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result

    def create_document_profile_proof(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        public_inputs: Mapping[str, Any],
    ):
        """Create the canonical redacted document-profile proof receipt."""

        result = self.wallet_service.create_document_profile_proof(
            wallet_id,
            record_id,
            actor_did=actor_did,
            public_inputs=public_inputs,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def create_document_vector_profile_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        chunk_size_words: int = 80,
    ) -> dict[str, Any]:
        self.wallet_service.verify_invocation(
            wallet_id,
            invocation,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/analyze",
            actor_secret=actor_secret,
        )
        result = self.wallet_service.create_document_vector_profile(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=invocation.grant_id,
            actor_secret=actor_secret,
            chunk_size_words=chunk_size_words,
            invocation_caveats=invocation.caveats,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def extract_record_text_redacted(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
        max_chars: int = 20_000,
        max_bytes: int = 200_000,
        use_ocr: bool = True,
    ) -> dict[str, Any]:
        result = self.wallet_service.extract_document_text_with_redaction(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            max_chars=max_chars,
            max_bytes=max_bytes,
            use_ocr=use_ocr,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def extract_record_text_redacted_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        max_chars: int = 20_000,
        max_bytes: int = 200_000,
        use_ocr: bool = True,
    ) -> dict[str, Any]:
        self.wallet_service.verify_invocation(
            wallet_id,
            invocation,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/analyze",
            actor_secret=actor_secret,
        )
        result = self.wallet_service.extract_document_text_with_redaction(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=invocation.grant_id,
            actor_secret=actor_secret,
            max_chars=max_chars,
            max_bytes=max_bytes,
            use_ocr=use_ocr,
            invocation_caveats=invocation.caveats,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def analyze_record_form_redacted(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
        max_fields: int = 100,
        use_ocr: bool = False,
    ) -> dict[str, Any]:
        result = self.wallet_service.analyze_document_form_with_redaction(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            max_fields=max_fields,
            use_ocr=use_ocr,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def analyze_record_form_redacted_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        max_fields: int = 100,
        use_ocr: bool = False,
    ) -> dict[str, Any]:
        self.wallet_service.verify_invocation(
            wallet_id,
            invocation,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/analyze",
            actor_secret=actor_secret,
        )
        result = self.wallet_service.analyze_document_form_with_redaction(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=invocation.grant_id,
            actor_secret=actor_secret,
            max_fields=max_fields,
            use_ocr=use_ocr,
            invocation_caveats=invocation.caveats,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def analyze_records_redacted(
        self,
        wallet_id: str,
        record_ids: Sequence[str],
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
    ) -> dict[str, Any]:
        result = self.wallet_service.analyze_documents_with_redaction(
            wallet_id,
            list(record_ids),
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def create_redacted_graphrag(
        self,
        wallet_id: str,
        record_ids: Sequence[str],
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
        max_chars_per_record: int = 20_000,
        max_bytes_per_record: int = 200_000,
        use_ocr: bool = True,
    ) -> dict[str, Any]:
        result = self.wallet_service.create_redacted_graphrag(
            wallet_id,
            list(record_ids),
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            max_chars_per_record=max_chars_per_record,
            max_bytes_per_record=max_bytes_per_record,
            use_ocr=use_ocr,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def create_redacted_graphrag_with_invocation(
        self,
        wallet_id: str,
        record_ids: Sequence[str],
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        max_chars_per_record: int = 20_000,
        max_bytes_per_record: int = 200_000,
        use_ocr: bool = True,
    ) -> dict[str, Any]:
        ordered_record_ids = list(dict.fromkeys(record_ids))
        for record_id in ordered_record_ids:
            self.wallet_service.verify_invocation(
                wallet_id,
                invocation,
                actor_did=actor_did,
                resource=resource_for_record(wallet_id, record_id),
                ability="record/analyze",
                actor_secret=actor_secret,
            )
        result = self.wallet_service.create_redacted_graphrag(
            wallet_id,
            ordered_record_ids,
            actor_did=actor_did,
            grant_id=invocation.grant_id,
            actor_secret=actor_secret,
            max_chars_per_record=max_chars_per_record,
            max_bytes_per_record=max_bytes_per_record,
            use_ocr=use_ocr,
            invocation_caveats=invocation.caveats,
        )
        self._persist_wallet_if_configured(wallet_id)
        return result


    def issue_record_analysis_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        grant_id: str,
        actor_did: str,
        actor_secret: bytes | None = None,
        expires_at: str | None = None,
        purpose: str | None = None,
        output_types: Sequence[str] | None = None,
        user_present: bool = False,
    ):
        invocation = self.wallet_service.issue_invocation(
            wallet_id,
            grant_id=grant_id,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/analyze",
            actor_secret=actor_secret,
            caveats=self._invocation_caveats(
                grant_id,
                fallback_purpose="service_matching",
                purpose=purpose,
                output_types=output_types,
                user_present=user_present,
            ),
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return invocation


    def issue_record_decrypt_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        grant_id: str,
        actor_did: str,
        actor_secret: bytes | None = None,
        expires_at: str | None = None,
        purpose: str | None = None,
        output_types: Sequence[str] | None = None,
        user_present: bool = False,
    ):
        invocation = self.wallet_service.issue_invocation(
            wallet_id,
            grant_id=grant_id,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/decrypt",
            actor_secret=actor_secret,
            caveats=self._invocation_caveats(
                grant_id,
                fallback_purpose="document_view",
                purpose=purpose,
                output_types=output_types,
                user_present=user_present,
            ),
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return invocation


    def _invocation_caveats(
        self,
        grant_id: str,
        *,
        fallback_purpose: str,
        purpose: str | None = None,
        output_types: Sequence[str] | None = None,
        user_present: bool = False,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        grant = self.wallet_service.grants.get(grant_id)
        caveats: dict[str, Any] = dict(extra or {})
        grant_purpose = grant.caveats.get("purpose") if grant is not None else None
        caveats["purpose"] = purpose or (str(grant_purpose) if grant_purpose else fallback_purpose)
        if output_types:
            caveats["output_types"] = list(output_types)
        if user_present:
            caveats["user_present"] = True
        return caveats


    def request_record_access(
        self,
        wallet_id: str,
        record_id: str,
        *,
        requester_did: str,
        ability: str = "record/analyze",
        audience_did: str | None = None,
        purpose: str = "service_matching",
        expires_at: str | None = None,
    ):
        if ability not in {"record/analyze", "record/decrypt"}:
            raise ValueError("record access ability must be record/analyze or record/decrypt")
        request = self.wallet_service.request_access(
            wallet_id,
            requester_did=requester_did,
            audience_did=audience_did,
            resources=[resource_for_record(wallet_id, record_id)],
            abilities=[ability],
            purpose=purpose,
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return request


    def request_record_analysis_access(
        self,
        wallet_id: str,
        record_id: str,
        *,
        requester_did: str,
        audience_did: str | None = None,
        purpose: str = "service_matching",
        expires_at: str | None = None,
    ):
        return self.request_record_access(
            wallet_id,
            record_id,
            requester_did=requester_did,
            ability="record/analyze",
            audience_did=audience_did,
            purpose=purpose,
            expires_at=expires_at,
        )


    def list_access_requests(
        self,
        wallet_id: str,
        *,
        status: str | None = "pending",
        requester_did: str | None = None,
        audience_did: str | None = None,
    ):
        return self.wallet_service.list_access_requests(
            wallet_id,
            status=status,
            requester_did=requester_did,
            audience_did=audience_did,
        )


    def access_request_review_items(
        self,
        wallet_id: str,
        *,
        status: str | None = "pending",
        requester_did: str | None = None,
        audience_did: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.wallet_service.access_request_review_items(
            wallet_id,
            status=status,
            requester_did=requester_did,
            audience_did=audience_did,
        )


    def approve_access_request(
        self,
        wallet_id: str,
        *,
        request_id: str,
        actor_did: str,
        issuer_secret: bytes | None = None,
        audience_secret: bytes | None = None,
        approval_id: str | None = None,
        issue_invocation: bool = False,
        invocation_expires_at: str | None = None,
    ):
        request = self.wallet_service.approve_access_request(
            wallet_id,
            request_id=request_id,
            actor_did=actor_did,
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
            approval_id=approval_id,
            issue_invocation=issue_invocation,
            invocation_expires_at=invocation_expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return request


    def request_threshold_approval(
        self,
        wallet_id: str,
        *,
        requested_by: str,
        operation: str,
        resources: Sequence[str],
        abilities: Sequence[str],
        expires_at: str | None = None,
    ):
        approval = self.wallet_service.request_approval(
            wallet_id,
            requested_by=requested_by,
            operation=operation,
            resources=list(resources),
            abilities=list(abilities),
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return approval


    def approve_threshold_approval(
        self,
        wallet_id: str,
        *,
        approval_id: str,
        approver_did: str,
    ):
        approval = self.wallet_service.approve_approval(
            wallet_id,
            approval_id=approval_id,
            approver_did=approver_did,
        )
        self._persist_wallet_if_configured(wallet_id)
        return approval


    def list_threshold_approvals(self, wallet_id: str, *, status: str | None = None):
        self.wallet_service._wallet(wallet_id)
        approvals = [
            approval
            for approval in self.wallet_service.approval_requests.values()
            if approval.wallet_id == wallet_id
        ]
        if status is not None:
            approvals = [approval for approval in approvals if approval.status == status]
        return sorted(approvals, key=lambda item: item.created_at)


    def reject_access_request(
        self,
        wallet_id: str,
        *,
        request_id: str,
        actor_did: str,
        reason: str | None = None,
    ):
        request = self.wallet_service.reject_access_request(
            wallet_id,
            request_id=request_id,
            actor_did=actor_did,
            reason=reason,
        )
        self._persist_wallet_if_configured(wallet_id)
        return request


    def revoke_access_request(
        self,
        wallet_id: str,
        *,
        request_id: str,
        actor_did: str,
        reason: str | None = None,
    ):
        request = self.wallet_service.revoke_access_request(
            wallet_id,
            request_id=request_id,
            actor_did=actor_did,
            reason=reason,
        )
        self._persist_wallet_if_configured(wallet_id)
        return request


    def revoke_grant(self, wallet_id: str, grant_id: str, *, actor_did: str):
        grant = self.wallet_service.revoke_grant(wallet_id, grant_id, actor_did=actor_did)
        self._persist_wallet_if_configured(wallet_id)
        return grant


    def emergency_revoke(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        actor_secret: bytes | None = None,
        approval_id: str | None = None,
        rotate_keys: bool = True,
        reason: str | None = None,
    ) -> dict[str, Any]:
        report = self.wallet_service.emergency_revoke(
            wallet_id,
            actor_did=actor_did,
            actor_secret=actor_secret,
            approval_id=approval_id,
            rotate_keys=rotate_keys,
            reason=reason,
        )
        self._persist_wallet_if_configured(wallet_id)
        return report


    def delegate_grant(
        self,
        wallet_id: str,
        *,
        parent_grant_id: str,
        issuer_did: str,
        audience_did: str,
        resources: Sequence[str],
        abilities: Sequence[str],
        caveats: dict[str, Any] | None = None,
        expires_at: str | None = None,
        issuer_secret: bytes | None = None,
        audience_secret: bytes | None = None,
    ):
        grant = self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=list(resources),
            abilities=list(abilities),
            caveats=dict(caveats or {}),
            expires_at=expires_at,
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
            parent_grant_id=parent_grant_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return grant


    def list_grant_receipts(
        self,
        wallet_id: str,
        *,
        audience_did: str | None = None,
        status: str | None = None,
    ):
        return self.wallet_service.list_grant_receipts(
            wallet_id,
            audience_did=audience_did,
            status=status,
        )


    def create_export_grant(
        self,
        wallet_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        record_ids: Sequence[str],
        issuer_secret: bytes | None = None,
        audience_secret: bytes | None = None,
        purpose: str = "user_export",
        expires_at: str | None = None,
        approval_id: str | None = None,
        output_types: Sequence[str] | None = None,
    ):
        grant = self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_export(wallet_id)],
            abilities=["export/create"],
            caveats={
                "purpose": purpose,
                "record_ids": list(record_ids),
                "output_types": list(output_types) if output_types is not None else ["encrypted_export_bundle"],
            },
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
            expires_at=expires_at,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return grant


    def create_export_bundle(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        grant_id: str | None = None,
        record_ids: Sequence[str] | None = None,
        include_proofs: bool = True,
        include_derived_artifacts: bool = True,
    ):
        bundle = self.wallet_service.create_export_bundle(
            wallet_id,
            actor_did=actor_did,
            grant_id=grant_id,
            record_ids=list(record_ids) if record_ids is not None else None,
            include_proofs=include_proofs,
            include_derived_artifacts=include_derived_artifacts,
        )
        self._persist_wallet_if_configured(wallet_id)
        return bundle


    def issue_export_invocation(
        self,
        wallet_id: str,
        *,
        grant_id: str,
        actor_did: str,
        actor_secret: bytes | None = None,
        record_ids: Sequence[str] | None = None,
        expires_at: str | None = None,
        purpose: str | None = None,
        output_types: Sequence[str] | None = None,
        user_present: bool = False,
    ):
        caveats = self._invocation_caveats(
            grant_id,
            fallback_purpose="user_export",
            purpose=purpose,
            output_types=output_types,
            user_present=user_present,
        )
        if record_ids is not None:
            caveats["record_ids"] = list(record_ids)
        invocation = self.wallet_service.issue_invocation(
            wallet_id,
            grant_id=grant_id,
            actor_did=actor_did,
            resource=resource_for_export(wallet_id),
            ability="export/create",
            actor_secret=actor_secret,
            caveats=caveats,
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return invocation


    def create_export_bundle_with_invocation(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        record_ids: Sequence[str] | None = None,
        include_proofs: bool = True,
        include_derived_artifacts: bool = True,
    ):
        bundle = self.wallet_service.create_export_bundle_with_invocation(
            wallet_id,
            actor_did=actor_did,
            invocation=invocation,
            actor_secret=actor_secret,
            record_ids=list(record_ids) if record_ids is not None else None,
            include_proofs=include_proofs,
            include_derived_artifacts=include_derived_artifacts,
        )
        self._persist_wallet_if_configured(wallet_id)
        return bundle


    def verify_export_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        bundle_hash = self.wallet_service.export_bundle_hash(bundle)
        embedded_hash = bundle.get("bundle_hash")
        hash_valid = isinstance(embedded_hash, str) and embedded_hash == bundle_hash
        schema_valid = False
        schema_error = None
        if hash_valid:
            try:
                self.wallet_service.validate_export_bundle_schema(bundle)
                schema_valid = True
            except Exception as exc:
                schema_error = str(exc)
        return {
            "valid": hash_valid and schema_valid,
            "hash_valid": hash_valid,
            "schema_valid": schema_valid,
            "bundle_id": bundle.get("bundle_id"),
            "bundle_hash": embedded_hash,
            "computed_hash": bundle_hash,
            **({"schema_error": schema_error} if schema_error else {}),
        }


    def import_export_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        result = self.wallet_service.import_export_bundle(bundle)
        wallet_id = result.get("wallet_id")
        if isinstance(wallet_id, str) and wallet_id:
            self._persist_wallet_if_configured(wallet_id)
        return result


    def verify_export_bundle_storage(self, bundle: dict[str, Any]) -> dict[str, Any]:
        return self.wallet_service.verify_export_bundle_storage(bundle)


    def analyze_record_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        max_chars: int = 200,
    ):
        artifact = self.wallet_service.analyze_record_summary_with_invocation(
            wallet_id,
            record_id,
            actor_did=actor_did,
            invocation=invocation,
            actor_secret=actor_secret,
            max_chars=max_chars,
        )
        self._persist_wallet_if_configured(wallet_id)
        return artifact


    def decrypt_record_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
    ) -> bytes:
        plaintext = self.wallet_service.decrypt_record_with_invocation(
            wallet_id,
            record_id,
            actor_did=actor_did,
            invocation=invocation,
            actor_secret=actor_secret,
        )
        self._persist_wallet_if_configured(wallet_id)
        return plaintext


    def decrypt_record_for_delegate(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
    ) -> bytes:
        plaintext = self.wallet_service.decrypt_record(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
        )
        self._persist_wallet_if_configured(wallet_id)
        return plaintext


    def rotate_record_key(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        actor_secret: bytes | None = None,
    ):
        version = self.wallet_service.rotate_record_key(
            wallet_id,
            record_id,
            actor_did=actor_did,
            actor_secret=actor_secret,
        )
        self._persist_wallet_if_configured(wallet_id)
        return version


    def verify_record_storage(self, wallet_id: str, record_id: str):
        return self.wallet_service.verify_record_storage(wallet_id, record_id)


    def verify_wallet_storage(self, wallet_id: str):
        return self.wallet_service.verify_wallet_storage(wallet_id)


    def repair_record_storage(self, wallet_id: str, record_id: str, *, actor_did: str):
        report = self.wallet_service.repair_record_storage(wallet_id, record_id, actor_did=actor_did)
        self._persist_wallet_if_configured(wallet_id)
        return report


    def repair_wallet_storage(self, wallet_id: str, *, actor_did: str):
        report = self.wallet_service.repair_wallet_storage(wallet_id, actor_did=actor_did)
        self._persist_wallet_if_configured(wallet_id)
        return report


    def audit_timeline(self, wallet_id: str) -> list[dict[str, Any]]:
        return [
            {
                "created_at": event.created_at,
                "actor_did": event.actor_did,
                "action": event.action,
                "resource": event.resource,
                "decision": event.decision,
                "grant_id": event.grant_id,
            }
            for event in self.wallet_service.get_audit_log(wallet_id)
        ]


    def list_proof_receipts(self, wallet_id: str):
        self.wallet_service._wallet(wallet_id)
        return sorted(
            [
                proof
                for proof in self.wallet_service.proofs.values()
                if proof.wallet_id == wallet_id
            ],
            key=lambda item: item.created_at,
        )
