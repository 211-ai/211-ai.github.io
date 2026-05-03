"""Application-facing wallet service for 211-AI workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence

from ._vendor import ensure_ipfs_datasets_py_path
from .service_matching import ServiceMatch, ServiceRecord, load_services_jsonl, match_services

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet import WalletService  # noqa: E402
from ipfs_datasets_py.wallet.ucan import resource_for_location, resource_for_record  # noqa: E402


class WalletInterfaceService:
    """Thin 211-AI interface around `ipfs_datasets_py.wallet`."""

    def __init__(
        self,
        *,
        wallet_service: WalletService | None = None,
        services: Sequence[ServiceRecord] | None = None,
    ) -> None:
        self.wallet_service = wallet_service or WalletService()
        self.services = list(services or [])

    @classmethod
    def from_services_jsonl(cls, path: str | Path, *, wallet_service: WalletService | None = None) -> "WalletInterfaceService":
        return cls(wallet_service=wallet_service, services=load_services_jsonl(path))

    def create_wallet(
        self,
        owner_did: str,
        *,
        controller_dids: Sequence[str] | None = None,
        approval_threshold: int | None = None,
    ):
        governance_policy = None
        if approval_threshold is not None:
            controllers = list(controller_dids or [owner_did])
            if owner_did not in controllers:
                controllers = [owner_did, *controllers]
            governance_policy = {
                "threshold": approval_threshold,
                "approver_dids": controllers,
            }
        return self.wallet_service.create_wallet(
            owner_did=owner_did,
            controller_dids=list(controller_dids) if controller_dids is not None else None,
            governance_policy=governance_policy,
        )

    def add_location(self, wallet_id: str, *, actor_did: str, lat: float, lon: float):
        return self.wallet_service.add_location(wallet_id, actor_did=actor_did, lat=lat, lon=lon)

    def add_document(
        self,
        wallet_id: str,
        path: str | Path,
        *,
        actor_did: str,
        actor_secret: bytes | None = None,
        metadata: Dict[str, Any] | None = None,
    ):
        return self.wallet_service.add_document(
            wallet_id,
            path,
            actor_did=actor_did,
            actor_secret=actor_secret,
            metadata=metadata,
        )

    def add_text_document(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        text: str,
        actor_secret: bytes | None = None,
        filename: str = "document.txt",
        metadata: Dict[str, Any] | None = None,
    ):
        private_metadata = {"filename": filename, **(metadata or {})}
        return self.wallet_service.add_record(
            wallet_id,
            data_type="document",
            plaintext=text.encode("utf-8"),
            actor_did=actor_did,
            actor_secret=actor_secret,
            private_metadata=private_metadata,
            sensitivity="restricted",
            public_descriptor="document",
        )

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
        return self.wallet_service.create_grant(
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
        return self.wallet_service.analyze_record_summary(
            wallet_id,
            record_id,
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
            max_chars=max_chars,
        )

    def issue_record_analysis_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        grant_id: str,
        actor_did: str,
        actor_secret: bytes | None = None,
        expires_at: str | None = None,
    ):
        return self.wallet_service.issue_invocation(
            wallet_id,
            grant_id=grant_id,
            actor_did=actor_did,
            resource=resource_for_record(wallet_id, record_id),
            ability="record/analyze",
            actor_secret=actor_secret,
            caveats={"purpose": "service_matching"},
            expires_at=expires_at,
        )

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
        return self.wallet_service.request_access(
            wallet_id,
            requester_did=requester_did,
            audience_did=audience_did,
            resources=[resource_for_record(wallet_id, record_id)],
            abilities=[ability],
            purpose=purpose,
            expires_at=expires_at,
        )

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
        return self.wallet_service.approve_access_request(
            wallet_id,
            request_id=request_id,
            actor_did=actor_did,
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
            approval_id=approval_id,
            issue_invocation=issue_invocation,
            invocation_expires_at=invocation_expires_at,
        )

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
        return self.wallet_service.request_approval(
            wallet_id,
            requested_by=requested_by,
            operation=operation,
            resources=list(resources),
            abilities=list(abilities),
            expires_at=expires_at,
        )

    def approve_threshold_approval(
        self,
        wallet_id: str,
        *,
        approval_id: str,
        approver_did: str,
    ):
        return self.wallet_service.approve_approval(
            wallet_id,
            approval_id=approval_id,
            approver_did=approver_did,
        )

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
        return self.wallet_service.reject_access_request(
            wallet_id,
            request_id=request_id,
            actor_did=actor_did,
            reason=reason,
        )

    def revoke_grant(self, wallet_id: str, grant_id: str, *, actor_did: str):
        return self.wallet_service.revoke_grant(wallet_id, grant_id, actor_did=actor_did)

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
        return self.wallet_service.analyze_record_summary_with_invocation(
            wallet_id,
            record_id,
            actor_did=actor_did,
            invocation=invocation,
            actor_secret=actor_secret,
            max_chars=max_chars,
        )

    def decrypt_record_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
    ) -> bytes:
        return self.wallet_service.decrypt_record_with_invocation(
            wallet_id,
            record_id,
            actor_did=actor_did,
            invocation=invocation,
            actor_secret=actor_secret,
        )

    def verify_record_storage(self, wallet_id: str, record_id: str):
        return self.wallet_service.verify_record_storage(wallet_id, record_id)

    def repair_record_storage(self, wallet_id: str, record_id: str, *, actor_did: str):
        return self.wallet_service.repair_record_storage(wallet_id, record_id, actor_did=actor_did)

    def audit_timeline(self, wallet_id: str) -> List[Dict[str, Any]]:
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

    def match_services_for_wallet(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        actor_did: str,
        need_terms: Sequence[str],
        grant_id: str | None = None,
        limit: int = 10,
    ) -> List[ServiceMatch]:
        claim = self.wallet_service.create_coarse_location_claim(
            wallet_id,
            location_record_id,
            actor_did=actor_did,
            grant_id=grant_id,
        )
        return match_services(
            self.services,
            need_terms=need_terms,
            location_claim=claim.to_dict(),
            limit=limit,
        )

    def create_coarse_location_grant(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        issuer_secret: bytes | None = None,
        audience_secret: bytes | None = None,
        expires_at: str | None = None,
    ):
        return self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_location(wallet_id, location_record_id)],
            abilities=["location/read_coarse"],
            caveats={"purpose": "service_matching", "precision": "coarse"},
            expires_at=expires_at,
            issuer_secret=issuer_secret,
            audience_secret=audience_secret,
        )

    def create_location_region_proof_grant(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        expires_at: str | None = None,
    ):
        return self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_location(wallet_id, location_record_id)],
            abilities=["location/prove_region"],
            caveats={"purpose": "service_matching", "proof_type": "location_region"},
            expires_at=expires_at,
        )

    def create_location_region_proof(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        actor_did: str,
        region_id: str,
        grant_id: str | None = None,
    ):
        return self.wallet_service.create_location_region_proof(
            wallet_id,
            location_record_id,
            actor_did=actor_did,
            region_id=region_id,
            grant_id=grant_id,
        )

    def issue_coarse_location_invocation(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        grant_id: str,
        actor_did: str,
        actor_secret: bytes | None = None,
        expires_at: str | None = None,
    ):
        return self.wallet_service.issue_invocation(
            wallet_id,
            grant_id=grant_id,
            actor_did=actor_did,
            resource=resource_for_location(wallet_id, location_record_id),
            ability="location/read_coarse",
            actor_secret=actor_secret,
            caveats={"purpose": "service_matching", "precision": "coarse"},
            expires_at=expires_at,
        )

    def match_services_for_wallet_with_invocation(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        need_terms: Sequence[str],
        limit: int = 10,
    ) -> List[ServiceMatch]:
        claim = self.wallet_service.create_coarse_location_claim_with_invocation(
            wallet_id,
            location_record_id,
            actor_did=actor_did,
            invocation=invocation,
            actor_secret=actor_secret,
        )
        return match_services(
            self.services,
            need_terms=need_terms,
            location_claim=claim.to_dict(),
            limit=limit,
        )

    def match_services_from_derived_facts(
        self,
        *,
        derived_facts: Dict[str, Any],
        limit: int = 10,
    ) -> List[ServiceMatch]:
        need_terms = derived_facts.get("need_terms") or derived_facts.get("needs") or []
        location_claim = derived_facts.get("location_claim")
        return match_services(
            self.services,
            need_terms=list(need_terms),
            location_claim=location_claim,
            limit=limit,
        )

    def create_analytics_consent(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        template_id: str,
        allowed_record_types: Sequence[str],
        allowed_derived_fields: Sequence[str],
        min_cohort_size: int = 10,
        epsilon_budget: float = 1.0,
        expires_at: str | None = None,
    ):
        return self.wallet_service.create_analytics_consent(
            wallet_id,
            actor_did=actor_did,
            template_id=template_id,
            allowed_record_types=list(allowed_record_types),
            allowed_derived_fields=list(allowed_derived_fields),
            aggregation_policy={
                "min_cohort_size": min_cohort_size,
                "epsilon_budget": epsilon_budget,
                "duplicate_policy": "reject_by_nullifier",
            },
            expires_at=expires_at,
        )

    def create_analytics_template(
        self,
        *,
        template_id: str,
        title: str,
        purpose: str,
        allowed_record_types: Sequence[str],
        allowed_derived_fields: Sequence[str],
        min_cohort_size: int,
        epsilon_budget: float,
        created_by: str,
        expires_at: str | None = None,
    ):
        return self.wallet_service.create_analytics_template(
            template_id=template_id,
            title=title,
            purpose=purpose,
            allowed_record_types=list(allowed_record_types),
            allowed_derived_fields=list(allowed_derived_fields),
            aggregation_policy={
                "min_cohort_size": min_cohort_size,
                "epsilon_budget": epsilon_budget,
                "duplicate_policy": "reject_by_nullifier",
            },
            created_by=created_by,
            expires_at=expires_at,
        )

    def list_analytics_templates(self):
        return self.wallet_service.list_analytics_templates()

    def create_analytics_consent_from_template(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        template_id: str,
        expires_at: str | None = None,
    ):
        template = self.wallet_service.analytics_templates[template_id]
        return self.wallet_service.create_analytics_consent(
            wallet_id,
            actor_did=actor_did,
            template_id=template.template_id,
            allowed_record_types=list(template.allowed_record_types),
            allowed_derived_fields=list(template.allowed_derived_fields),
            expires_at=expires_at,
        )

    def contribute_analytics_facts(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        consent_id: str,
        template_id: str,
        fields: Dict[str, Any],
    ):
        self._reject_precise_analytics_fields(fields)
        return self.wallet_service.create_analytics_contribution(
            wallet_id,
            actor_did=actor_did,
            consent_id=consent_id,
            template_id=template_id,
            fields=dict(fields),
        )

    def run_private_aggregate_count(
        self,
        template_id: str,
        *,
        epsilon: float,
        min_cohort_size: int | None = None,
        budget_key: str | None = None,
        budget_limit: float | None = None,
        actor_did: str = "did:service:211-ai-analytics",
    ):
        return self.wallet_service.run_aggregate_count(
            template_id,
            min_cohort_size=min_cohort_size,
            epsilon=epsilon,
            budget_key=budget_key,
            budget_limit=budget_limit,
            actor_did=actor_did,
        )

    def summarize_aggregate_result(self, result) -> Dict[str, Any]:
        return {
            "result_id": result.result_id,
            "template_id": result.template_id,
            "metric": result.metric,
            "released": result.released,
            "suppressed": result.suppressed,
            "count": result.count if result.exact_count_released else None,
            "noisy_count": result.noisy_count if result.released else None,
            "min_cohort_size": result.min_cohort_size,
            "epsilon": result.epsilon,
            "privacy_budget_key": result.privacy_budget_key,
            "privacy_budget_spent": result.privacy_budget_spent,
            "privacy_notes": list(result.privacy_notes),
        }

    def _reject_precise_analytics_fields(self, fields: Dict[str, Any]) -> None:
        for key, value in fields.items():
            normalized_key = key.lower()
            if normalized_key in {"lat", "lon", "latitude", "longitude"}:
                raise ValueError("analytics contributions require derived or coarse fields, not precise coordinates")
            if normalized_key.startswith("precise_"):
                raise ValueError("analytics contributions require derived or coarse fields, not precise fields")
            if isinstance(value, dict):
                match_services([], need_terms=[], location_claim=value)
