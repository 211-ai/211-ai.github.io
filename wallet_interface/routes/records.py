"""Route factory for records endpoints."""

from __future__ import annotations

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..api import *  # noqa: F401,F403
from ..schemas import *  # noqa: F401,F403

def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.get("/wallets/{wallet_id}/records")
    def list_records(wallet_id: str, data_type: str | None = None) -> Dict[str, Any]:
        try:
            records = app_service.list_records(wallet_id, data_type=data_type)
            return {"records": [app_service.record_to_dict(record) for record in records]}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.patch("/wallets/{wallet_id}/records/{record_id}/metadata")
    def update_record_metadata(
        wallet_id: str,
        record_id: str,
        request: WalletRecordMetadataRequest,
    ) -> Dict[str, Any]:
        try:
            record = app_service.update_record_metadata(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                metadata=request.metadata,
            )
            if _should_publish_record_metadata_ipld(request.metadata):
                metadata_patch = _publish_record_metadata_ipld(record)
                if metadata_patch:
                    record = app_service.update_record_metadata(
                        wallet_id,
                        record_id,
                        actor_did=request.actor_did,
                        metadata=metadata_patch,
                    )
            return record
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.delete("/wallets/{wallet_id}/records/{record_id}")
    def delete_record(
        wallet_id: str,
        record_id: str,
        request: DeleteWalletRecordRequest,
    ) -> Dict[str, Any]:
        try:
            return app_service.delete_record(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                unpin_ipfs=request.unpin_ipfs,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/portal/saved-services")
    def list_saved_services(wallet_id: str, status: str | None = None) -> Dict[str, Any]:
        try:
            return {
                "saved_services": [
                    record.to_dict() for record in app_service.list_saved_services(wallet_id, status=status)
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/portal/saved-services")
    def save_service(wallet_id: str, request: SavedServiceRequest) -> Dict[str, Any]:
        try:
            record = app_service.save_service_for_wallet(
                wallet_id,
                actor_did=request.actor_did,
                service_doc_id=request.service_doc_id,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                title=request.title,
                provider_name=request.provider_name,
                program_name=request.program_name,
                source_url=request.source_url,
                label=request.label,
                reason=request.reason,
                priority=request.priority,
                status=request.status,
                private_notes_record_id=request.private_notes_record_id,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.patch("/wallets/{wallet_id}/portal/saved-services/{saved_service_id}")
    def update_saved_service(wallet_id: str, saved_service_id: str, request: SavedServiceUpdateRequest) -> Dict[str, Any]:
        try:
            record = app_service.update_saved_service(
                wallet_id,
                saved_service_id,
                actor_did=request.actor_did,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                title=request.title,
                provider_name=request.provider_name,
                program_name=request.program_name,
                source_url=request.source_url,
                label=request.label,
                reason=request.reason,
                priority=request.priority,
                status=request.status,
                private_notes_record_id=request.private_notes_record_id,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/portal/plans")
    def list_service_plans(
        wallet_id: str,
        service_doc_id: str | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        try:
            return {
                "plans": [
                    record.to_dict()
                    for record in app_service.list_service_plans(
                        wallet_id,
                        service_doc_id=service_doc_id,
                        status=status,
                    )
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/portal/plans")
    def create_service_plan(wallet_id: str, request: ServicePlanRequest) -> Dict[str, Any]:
        try:
            record = app_service.create_service_plan(
                wallet_id,
                actor_did=request.actor_did,
                service_doc_id=request.service_doc_id,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                service_title=request.service_title,
                provider_name=request.provider_name,
                goal=request.goal,
                steps=request.steps,
                documents_needed=request.documents_needed,
                questions_to_ask=request.questions_to_ask,
                appointment_at=request.appointment_at,
                reminder_at=request.reminder_at,
                travel_target=request.travel_target,
                assigned_worker_recipient_id=request.assigned_worker_recipient_id,
                status=request.status,
                related_interaction_ids=request.related_interaction_ids,
                private_notes_record_id=request.private_notes_record_id,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.patch("/wallets/{wallet_id}/portal/plans/{plan_id}")
    def update_service_plan(wallet_id: str, plan_id: str, request: ServicePlanUpdateRequest) -> Dict[str, Any]:
        try:
            record = app_service.update_service_plan(
                wallet_id,
                plan_id,
                actor_did=request.actor_did,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                service_title=request.service_title,
                provider_name=request.provider_name,
                goal=request.goal,
                steps=request.steps,
                documents_needed=request.documents_needed,
                questions_to_ask=request.questions_to_ask,
                appointment_at=request.appointment_at,
                reminder_at=request.reminder_at,
                travel_target=request.travel_target,
                assigned_worker_recipient_id=request.assigned_worker_recipient_id,
                status=request.status,
                related_interaction_ids=request.related_interaction_ids,
                private_notes_record_id=request.private_notes_record_id,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/portal/interactions")
    def list_service_interactions(
        wallet_id: str,
        service_doc_id: str | None = None,
        interaction_type: str | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        try:
            return {
                "interactions": [
                    record.to_dict()
                    for record in app_service.list_service_interactions(
                        wallet_id,
                        service_doc_id=service_doc_id,
                        interaction_type=interaction_type,
                        status=status,
                    )
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/portal/interactions")
    def create_service_interaction(wallet_id: str, request: ServiceInteractionRequest) -> Dict[str, Any]:
        try:
            record = app_service.create_service_interaction(
                wallet_id,
                actor_did=request.actor_did,
                service_doc_id=request.service_doc_id,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                provider_name=request.provider_name,
                program_name=request.program_name,
                interaction_type=request.interaction_type,
                channel=request.channel,
                counterparty_name=request.counterparty_name,
                counterparty_contact=request.counterparty_contact,
                timestamp=request.timestamp,
                status=request.status,
                outcome=request.outcome,
                notes_record_id=request.notes_record_id,
                next_action=request.next_action,
                next_follow_up_at=request.next_follow_up_at,
                source_action_url=request.source_action_url,
                related_grant_ids=request.related_grant_ids,
                related_record_ids=request.related_record_ids,
                privacy_level=request.privacy_level,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.patch("/wallets/{wallet_id}/portal/interactions/{interaction_id}")
    def update_service_interaction(
        wallet_id: str,
        interaction_id: str,
        request: ServiceInteractionUpdateRequest,
    ) -> Dict[str, Any]:
        try:
            record = app_service.update_service_interaction(
                wallet_id,
                interaction_id,
                actor_did=request.actor_did,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                provider_name=request.provider_name,
                program_name=request.program_name,
                channel=request.channel,
                counterparty_name=request.counterparty_name,
                counterparty_contact=request.counterparty_contact,
                timestamp=request.timestamp,
                status=request.status,
                outcome=request.outcome,
                notes_record_id=request.notes_record_id,
                next_action=request.next_action,
                next_follow_up_at=request.next_follow_up_at,
                source_action_url=request.source_action_url,
                related_grant_ids=request.related_grant_ids,
                related_record_ids=request.related_record_ids,
                privacy_level=request.privacy_level,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/decrypt")
    def decrypt_record(
        wallet_id: str,
        record_id: str,
        request: DecryptRecordRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                plaintext = app_service.decrypt_record_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                )
            else:
                plaintext = app_service.decrypt_record_for_delegate(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                )
            return {
                "size_bytes": len(plaintext),
                "text": plaintext.decode("utf-8", errors="replace"),
                "base64": base64.b64encode(plaintext).decode("ascii"),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/analyze")
    def analyze_record(
        wallet_id: str,
        record_id: str,
        request: AnalyzeRecordRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                artifact = app_service.analyze_record_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            else:
                artifact = app_service.analyze_record_for_delegate(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id or "",
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            return artifact.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/analyze/redacted")
    def analyze_record_redacted(
        wallet_id: str,
        record_id: str,
        request: RedactedAnalyzeRecordRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.analyze_record_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            else:
                result = app_service.analyze_record_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/vector-profile")
    def create_document_vector_profile(
        wallet_id: str,
        record_id: str,
        request: VectorProfileRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.create_document_vector_profile_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    chunk_size_words=request.chunk_size_words,
                )
            else:
                result = app_service.create_document_vector_profile(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    chunk_size_words=request.chunk_size_words,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/extract-text/redacted")
    def extract_record_text_redacted(
        wallet_id: str,
        record_id: str,
        request: RedactedTextExtractionRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.extract_record_text_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                    max_bytes=request.max_bytes,
                    use_ocr=request.use_ocr,
                )
            else:
                result = app_service.extract_record_text_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                    max_bytes=request.max_bytes,
                    use_ocr=request.use_ocr,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/forms/analyze/redacted")
    def analyze_record_form_redacted(
        wallet_id: str,
        record_id: str,
        request: RedactedFormAnalysisRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.analyze_record_form_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_fields=request.max_fields,
                    use_ocr=request.use_ocr,
                )
            else:
                result = app_service.analyze_record_form_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_fields=request.max_fields,
                    use_ocr=request.use_ocr,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/analyze/redacted")
    def analyze_records_redacted(
        wallet_id: str,
        request: RedactedAnalyzeRecordsRequest,
    ) -> Dict[str, Any]:
        try:
            if not request.record_ids:
                raise ValueError("redacted cross-record analysis requires at least one record_id")
            result = app_service.analyze_records_redacted(
                wallet_id,
                request.record_ids,
                actor_did=request.actor_did,
                grant_id=request.grant_id,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
            )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/graphrag/redacted")
    def create_redacted_graphrag(
        wallet_id: str,
        request: RedactedGraphRAGRequest,
    ) -> Dict[str, Any]:
        try:
            if not request.record_ids:
                raise ValueError("redacted GraphRAG creation requires at least one record_id")
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.create_redacted_graphrag_with_invocation(
                    wallet_id,
                    request.record_ids,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
            else:
                result = app_service.create_redacted_graphrag(
                    wallet_id,
                    request.record_ids,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/metadata/generate")
    def generate_wallet_record_metadata(
        wallet_id: str,
        record_id: str,
        request: WalletRecordMetadataGenerationRequest,
    ) -> Dict[str, Any]:
        try:
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid, cost=4)
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            invocation = invocation_from_token(request.invocation_token) if request.invocation_token else None
            metadata_status = app_service.update_record_metadata(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                metadata={
                    "privacyProfileMessage": "Creating redacted GraphRAG, vector metadata, and wallet router labels.",
                    "privacyProfileStatus": "profiling",
                    **({"privacyProfileMimeType": request.mime_type} if request.mime_type else {}),
                },
            )

            derived_results: List[Dict[str, Any]] = []
            result_errors: List[str] = []
            for create_result in (
                lambda: app_service.analyze_record_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_chars=500,
                )
                if invocation
                else app_service.analyze_record_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=500,
                ),
                lambda: app_service.create_document_vector_profile_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    chunk_size_words=80,
                )
                if invocation
                else app_service.create_document_vector_profile(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    chunk_size_words=80,
                ),
                lambda: app_service.create_redacted_graphrag_with_invocation(
                    wallet_id,
                    [record_id],
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
                if invocation
                else app_service.create_redacted_graphrag(
                    wallet_id,
                    [record_id],
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                ),
                lambda: app_service.extract_record_text_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_chars=12_000,
                    max_bytes=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
                if invocation
                else app_service.extract_record_text_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=12_000,
                    max_bytes=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                ),
                lambda: app_service.analyze_record_form_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_fields=100,
                    use_ocr=request.use_ocr,
                )
                if invocation
                else app_service.analyze_record_form_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_fields=100,
                    use_ocr=request.use_ocr,
                ),
            ):
                try:
                    derived_results.append(create_result())
                except Exception as exc:
                    result_errors.append(str(exc))

            outputs = [_derived_output(result) for result in derived_results if _derived_output(result)]
            if not outputs:
                outputs.append(
                    _fallback_document_profile_output(
                        file_name=request.file_name or record_id,
                        mime_type=request.mime_type or _record_metadata_value(metadata_status, "privacyProfileMimeType") or "application/octet-stream",
                    )
                )
            organizer_profile = _generate_wallet_organizer_profile(
                wallet_id=wallet_id,
                wallet_cid=wallet_cid,
                file_name=request.file_name or _record_metadata_value(metadata_status, "fileName") or record_id,
                mime_type=request.mime_type or _record_metadata_value(metadata_status, "privacyProfileMimeType") or "application/octet-stream",
                outputs=outputs,
                provider=request.provider,
                model_name=request.model_name,
                kwargs=request.kwargs,
            )
            if organizer_profile:
                outputs.append(
                    {
                        "openrouter_organizer_profile": organizer_profile,
                        "output_policy": "redacted_wallet_router_organizer",
                    }
                )
            artifact_ids = [_derived_artifact_id(result) for result in derived_results]
            artifact_ids = [artifact_id for artifact_id in artifact_ids if artifact_id]
            public_inputs = _build_document_profile_public_inputs(
                artifact_ids=artifact_ids,
                file_name=request.file_name or _record_metadata_value(metadata_status, "fileName") or record_id,
                mime_type=request.mime_type or _record_metadata_value(metadata_status, "privacyProfileMimeType") or "application/octet-stream",
                outputs=outputs,
            )
            proof = app_service.create_document_profile_proof(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                public_inputs=public_inputs,
            )
            metadata_patch = {
                "privacyProfileArtifactIds": artifact_ids,
                "privacyProfileClassification": _classify_document_profile(public_inputs),
                "privacyProfileLabels": _read_string_list(public_inputs.get("organizer_labels")) or _default_labels_for_mime_type(str(public_inputs.get("mime_type") or "")),
                "privacyProfileMessage": "Safe document profile and proof are attached to this wallet record.",
                "privacyProfileMimeType": public_inputs.get("mime_type"),
                "privacyProfileNeedsRefresh": False,
                "privacyProfileProofId": proof.proof_id,
                "privacyProfilePublicInputs": public_inputs,
                "privacyProfileSearchText": _build_privacy_search_text(outputs, public_inputs),
                "privacyProfileStatus": "profiled",
                "privacyProfileSummary": _summarize_document_profile(public_inputs),
                "privacyProfileVectorTerms": _build_privacy_vector_terms(outputs, public_inputs),
                "walletRouterRateLimit": limit,
            }
            if result_errors:
                metadata_patch["privacyProfileWarnings"] = result_errors[:5]
            record = app_service.update_record_metadata(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                metadata=metadata_patch,
            )
            metadata_ipld_patch = _publish_record_metadata_ipld(record)
            if metadata_ipld_patch:
                record = app_service.update_record_metadata(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    metadata=metadata_ipld_patch,
                )
            return {
                "record": record,
                "metadata": record.get("metadata", {}),
                "proof": proof.to_dict(),
                "router": {
                    "wallet_id": wallet_id,
                    "wallet_cid": wallet_cid,
                    "provider": request.provider,
                    "model_name": request.model_name,
                    "rate_limit": limit,
                },
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/rotate-key")
    def rotate_record_key(
        wallet_id: str,
        record_id: str,
        request: RotateRecordKeyRequest,
    ) -> Dict[str, Any]:
        try:
            version = app_service.rotate_record_key(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
            )
            return version.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/services/match")
    def match_services_for_wallet(wallet_id: str, request: WalletServiceMatchRequest) -> Dict[str, Any]:
        try:
            if request.invocation_token:
                matches = app_service.match_services_for_wallet_with_invocation(
                    wallet_id,
                    request.location_record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=_key_from_optional_hex(request.actor_key_hex),
                    need_terms=list(request.need_terms),
                    limit=request.limit,
                )
            else:
                matches = app_service.match_services_for_wallet(
                    wallet_id,
                    request.location_record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    need_terms=list(request.need_terms),
                    limit=request.limit,
                )
            return {"matches": [_match_to_dict(match) for match in matches]}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/audit")
    def audit_timeline(wallet_id: str) -> Dict[str, Any]:
        try:
            return {"events": app_service.audit_timeline(wallet_id)}
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    return router
