"""Application-facing wallet service for 211-AI workflows."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from ._vendor import ensure_ipfs_datasets_py_path
from .service_matching import ServiceMatch, ServiceRecord, load_services_jsonl, match_services

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet import (  # noqa: E402
    DeterministicLocationRegionProofBackend,
    LocalWalletRepository,
    ProofBackend,
    SimulatedProofBackend,
    WalletService,
    create_encrypted_blob_store,
)
from ipfs_datasets_py.wallet.audit import append_audit_event  # noqa: E402
from ipfs_datasets_py.wallet.ucan import (  # noqa: E402
    resource_for_export,
    resource_for_location,
    resource_for_record,
    resource_for_wallet,
)
from .proof_backends import HttpLocationRegionProofBackend


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_config_from_env() -> str | Dict[str, Any] | None:
    """Read wallet encrypted storage config from environment variables."""

    raw_config = os.getenv("WALLET_STORAGE_CONFIG")
    if raw_config:
        try:
            parsed = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise ValueError("WALLET_STORAGE_CONFIG must be valid JSON") from exc
        if not isinstance(parsed, (str, dict)):
            raise ValueError("WALLET_STORAGE_CONFIG must decode to a string or object")
        return parsed

    storage_type = os.getenv("WALLET_STORAGE_TYPE")
    if not storage_type:
        return None

    config: Dict[str, Any] = {"type": storage_type}
    if root := os.getenv("WALLET_STORAGE_ROOT"):
        config["root"] = root
    if bucket := os.getenv("WALLET_STORAGE_BUCKET"):
        config["bucket"] = bucket
    if prefix := os.getenv("WALLET_STORAGE_PREFIX"):
        config["prefix"] = prefix
    if pin := os.getenv("WALLET_STORAGE_PIN"):
        config["pin"] = pin.lower() not in {"0", "false", "no"}
    if mirrors := os.getenv("WALLET_STORAGE_MIRRORS"):
        try:
            parsed_mirrors = json.loads(mirrors)
        except json.JSONDecodeError as exc:
            raise ValueError("WALLET_STORAGE_MIRRORS must be valid JSON") from exc
        if not isinstance(parsed_mirrors, list):
            raise ValueError("WALLET_STORAGE_MIRRORS must decode to a list")
        return {"primary": config, "mirrors": parsed_mirrors}
    return config


def _allow_simulated_proofs_from_env() -> bool:
    """Read wallet proof mode from environment variables."""

    explicit = os.getenv("WALLET_ALLOW_SIMULATED_PROOFS")
    if explicit is not None:
        return explicit.lower() not in {"0", "false", "no", "off"}

    mode = os.getenv("WALLET_PROOF_MODE", "development").lower()
    if mode in {"development", "dev", "test", "local"}:
        return True
    if mode in {"production", "prod"}:
        return False
    raise ValueError("WALLET_PROOF_MODE must be development or production")


def _proof_backend_from_env() -> ProofBackend | None:
    backend = os.getenv("WALLET_PROOF_BACKEND", "").strip().lower()
    if not backend or backend in {"default", "simulated"}:
        return None if not backend or backend == "default" else SimulatedProofBackend()
    if backend in {"deterministic", "deterministic-location-region", "integration"}:
        return DeterministicLocationRegionProofBackend()
    if backend in {"http", "http-location-region", "remote-http", "verifier-http"}:
        verifier_headers: Dict[str, str] = {}
        if header_name := str(os.getenv("WALLET_PROOF_HTTP_HEADER_NAME") or "").strip():
            header_value = str(os.getenv("WALLET_PROOF_HTTP_HEADER_VALUE") or "").strip()
            if not header_value:
                raise ValueError("WALLET_PROOF_HTTP_HEADER_VALUE is required when header name is set")
            verifier_headers[header_name] = header_value
        return HttpLocationRegionProofBackend(
            base_url=str(os.getenv("WALLET_PROOF_SERVICE_URL") or "").strip(),
            verifier_id=str(os.getenv("WALLET_PROOF_VERIFIER_ID") or "remote-location-region-v1").strip(),
            proof_system=str(os.getenv("WALLET_PROOF_SYSTEM") or "groth16").strip(),
            circuit_id=str(os.getenv("WALLET_PROOF_CIRCUIT_ID") or "location-region").strip(),
            prove_path=str(os.getenv("WALLET_PROOF_PROVE_PATH") or "/prove/location-region").strip(),
            verify_path=str(os.getenv("WALLET_PROOF_VERIFY_PATH") or "/verify").strip(),
            bearer_token=str(os.getenv("WALLET_PROOF_BEARER_TOKEN") or "").strip() or None,
            extra_headers=verifier_headers,
            timeout_seconds=float(str(os.getenv("WALLET_PROOF_TIMEOUT_SECONDS") or "30").strip()),
        )
    raise ValueError(
        "WALLET_PROOF_BACKEND must be default, simulated, deterministic-location-region, or http-location-region"
    )


def _repository_root_from_env() -> str | None:
    return os.getenv("WALLET_REPOSITORY_ROOT")


def _flag_from_env(name: str, *, default: bool) -> bool:
    explicit = os.getenv(name)
    if explicit is None:
        return default
    return explicit.lower() not in {"0", "false", "no", "off"}


class WalletInterfaceService:
    """Thin 211-AI interface around `ipfs_datasets_py.wallet`."""

    def __init__(
        self,
        *,
        wallet_service: WalletService | None = None,
        storage_config: str | Mapping[str, Any] | None = None,
        storage_backends: Mapping[str, object] | None = None,
        proof_backend: ProofBackend | None = None,
        allow_simulated_proofs: bool | None = None,
        ipfs_backend: object | None = None,
        s3_client: object | None = None,
        filecoin_backend: object | None = None,
        repository_root: str | Path | None = None,
        auto_persist: bool | None = None,
        auto_load_repository: bool | None = None,
        services: Sequence[ServiceRecord] | None = None,
    ) -> None:
        if wallet_service is None:
            storage = create_encrypted_blob_store(
                storage_config if storage_config is not None else _storage_config_from_env(),
                ipfs_backend=ipfs_backend,
                s3_client=s3_client,
                filecoin_backend=filecoin_backend,
                backends=storage_backends,
            )
            wallet_service = WalletService(
                storage_backend=storage,
                proof_backend=proof_backend if proof_backend is not None else _proof_backend_from_env(),
                allow_simulated_proofs=(
                    _allow_simulated_proofs_from_env()
                    if allow_simulated_proofs is None
                    else allow_simulated_proofs
                ),
            )
        self.wallet_service = wallet_service
        resolved_repository_root = repository_root if repository_root is not None else _repository_root_from_env()
        self.repository = LocalWalletRepository(resolved_repository_root) if resolved_repository_root else None
        self.auto_persist = (
            _flag_from_env("WALLET_AUTO_PERSIST", default=True)
            if auto_persist is None
            else auto_persist
        )
        should_auto_load = (
            _flag_from_env("WALLET_AUTO_LOAD_REPOSITORY", default=True)
            if auto_load_repository is None
            else auto_load_repository
        )
        if self.repository is not None and should_auto_load:
            self.repository.load_all(self.wallet_service)
        self.services = list(services or [])

    @classmethod
    def from_services_jsonl(
        cls,
        path: str | Path,
        *,
        wallet_service: WalletService | None = None,
        storage_config: str | Mapping[str, Any] | None = None,
        storage_backends: Mapping[str, object] | None = None,
        proof_backend: ProofBackend | None = None,
        allow_simulated_proofs: bool | None = None,
        ipfs_backend: object | None = None,
        s3_client: object | None = None,
        filecoin_backend: object | None = None,
        repository_root: str | Path | None = None,
        auto_persist: bool | None = None,
        auto_load_repository: bool | None = None,
    ) -> "WalletInterfaceService":
        return cls(
            wallet_service=wallet_service,
            storage_config=storage_config,
            storage_backends=storage_backends,
            proof_backend=proof_backend,
            allow_simulated_proofs=allow_simulated_proofs,
            ipfs_backend=ipfs_backend,
            s3_client=s3_client,
            filecoin_backend=filecoin_backend,
            repository_root=repository_root,
            auto_persist=auto_persist,
            auto_load_repository=auto_load_repository,
            services=load_services_jsonl(path),
        )

    def save_wallet_snapshot(self, wallet_id: str) -> Path:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        return self.repository.save(self.wallet_service, wallet_id)

    def load_wallet_snapshot(self, wallet_id: str) -> None:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        self.repository.load(self.wallet_service, wallet_id)

    def verify_wallet_snapshot(self, wallet_id: str) -> Dict[str, Any]:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        return self.repository.verify(wallet_id)

    def save_all_wallet_snapshots(self) -> list[Path]:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        return self.repository.save_all(self.wallet_service)

    def load_all_wallet_snapshots(self) -> list[str]:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        return self.repository.load_all(self.wallet_service)

    def list_wallet_snapshots(self) -> list[str]:
        if self.repository is None:
            return []
        return self.repository.list_wallet_ids()

    def ops_health(self, *, verify_storage: bool = False) -> Dict[str, Any]:
        """Return actionable deployment health for wallet operations."""

        checks: list[Dict[str, Any]] = []

        def add_check(name: str, status: str, summary: str, **details: Any) -> None:
            checks.append(
                {
                    "name": name,
                    "status": status,
                    "summary": summary,
                    "details": details,
                }
            )

        if self.repository is None:
            add_check(
                "repository",
                "warning",
                "Wallet repository is not configured; API restarts keep only in-memory wallet state.",
                configured=False,
                env_var="WALLET_REPOSITORY_ROOT",
            )
        else:
            try:
                snapshot_wallet_ids = self.repository.list_wallet_ids()
                live_wallet_ids = sorted(self.wallet_service.wallets)
                missing_snapshots = [wallet_id for wallet_id in live_wallet_ids if wallet_id not in snapshot_wallet_ids]
                add_check(
                    "repository",
                    "warning" if missing_snapshots else "ok",
                    (
                        "Wallet repository is configured, but some live wallets have not been snapshotted."
                        if missing_snapshots
                        else "Wallet repository is configured and live wallets have snapshots."
                    ),
                    configured=True,
                    wallet_snapshot_count=len(snapshot_wallet_ids),
                    live_wallet_count=len(live_wallet_ids),
                    missing_snapshot_wallet_ids=missing_snapshots,
                )
            except Exception as exc:  # pragma: no cover - backend-specific failure path.
                add_check("repository", "error", str(exc), configured=True)

        storage_name = self.wallet_service.storage.__class__.__name__
        active_records = [
            record
            for record in self.wallet_service.records.values()
            if record.status == "active"
        ]
        storage_failures: list[Dict[str, Any]] = []
        if verify_storage:
            for record in active_records:
                try:
                    report = self.wallet_service.verify_record_storage(record.wallet_id, record.record_id)
                except Exception as exc:  # pragma: no cover - backend-specific failure path.
                    storage_failures.append(
                        {
                            "wallet_id": record.wallet_id,
                            "record_id": record.record_id,
                            "error": str(exc),
                        }
                    )
                    continue
                if not report.ok:
                    storage_failures.append(
                        {
                            "wallet_id": record.wallet_id,
                            "record_id": record.record_id,
                            "payload_failures": [
                                status.to_dict() for status in report.payload if not status.ok
                            ],
                            "metadata_failures": [
                                status.to_dict() for status in report.metadata if not status.ok
                            ],
                        }
                    )
        add_check(
            "storage_availability",
            "error" if storage_failures else "ok",
            (
                f"{len(storage_failures)} active records failed encrypted storage verification."
                if storage_failures
                else "Encrypted storage backend is configured and no verified records failed."
            ),
            backend=storage_name,
            active_record_count=len(active_records),
            verified=verify_storage,
            failures=storage_failures,
        )

        proof_backend_name = self.wallet_service.proof_backend.__class__.__name__
        simulated_enabled = bool(self.wallet_service.allow_simulated_proofs)
        proof_status = "warning" if simulated_enabled else "ok"
        proof_summary = (
            "Simulated proof receipts are enabled; configure a production proof backend before launch."
            if simulated_enabled
            else "Production proof mode rejects simulated proof receipts."
        )
        proof_health_details: Dict[str, Any] | None = None
        if not simulated_enabled and hasattr(self.wallet_service.proof_backend, "healthcheck"):
            try:
                raw_health = getattr(self.wallet_service.proof_backend, "healthcheck")()
                if isinstance(raw_health, Mapping):
                    proof_health_details = dict(raw_health)
                    if not bool(raw_health.get("ok", False)):
                        proof_status = "error"
                        proof_summary = "Configured proof backend health check failed."
                    elif str(raw_health.get("status") or "").lower() not in {"", "ok", "healthy", "ready"}:
                        proof_status = "warning"
                        proof_summary = "Configured proof backend reported a non-ready health status."
                else:
                    proof_status = "error"
                    proof_summary = "Configured proof backend health check returned an invalid payload."
                    proof_health_details = {"ok": False, "details": raw_health}
            except Exception as exc:  # pragma: no cover - backend/network specific failure path.
                proof_status = "error"
                proof_summary = "Configured proof backend health check raised an exception."
                proof_health_details = {"ok": False, "error": str(exc)}
        add_check(
            "proof_registry",
            proof_status,
            proof_summary,
            backend=proof_backend_name,
            verifier_id=getattr(self.wallet_service.proof_backend, "verifier_id", None),
            proof_system=getattr(self.wallet_service.proof_backend, "proof_system", None),
            backend_mode=getattr(self.wallet_service.proof_backend, "mode", None),
            is_simulated_backend=bool(getattr(self.wallet_service.proof_backend, "is_simulated", False)),
            backend_health=proof_health_details,
            allow_simulated_proofs=simulated_enabled,
            env_vars=["WALLET_PROOF_MODE", "WALLET_PROOF_BACKEND", "WALLET_ALLOW_SIMULATED_PROOFS"],
        )

        revoked_grant_ids = {
            grant.grant_id for grant in self.wallet_service.grants.values() if grant.status == "revoked"
        }
        dangling_key_wraps = []
        for version in self.wallet_service.versions.values():
            for key_wrap in version.key_wraps:
                if key_wrap.grant_id in revoked_grant_ids and key_wrap.status == "active":
                    dangling_key_wraps.append(
                        {
                            "record_id": key_wrap.record_id,
                            "version_id": key_wrap.version_id,
                            "recipient_did": key_wrap.recipient_did,
                            "grant_id": key_wrap.grant_id,
                        }
                    )
        add_check(
            "revocation_propagation",
            "error" if dangling_key_wraps else "ok",
            (
                f"{len(dangling_key_wraps)} active key wraps still reference revoked grants."
                if dangling_key_wraps
                else "Revoked grants do not have active delegated key wraps."
            ),
            revoked_grant_count=len(revoked_grant_ids),
            dangling_key_wraps=dangling_key_wraps,
        )

        budget_spent = dict(sorted(self.wallet_service.analytics_query_budget_spent.items()))
        negative_budgets = {key: value for key, value in budget_spent.items() if value < 0}
        add_check(
            "privacy_budget",
            "error" if negative_budgets else "ok",
            (
                "Privacy budget ledger contains invalid negative spend values."
                if negative_budgets
                else "Privacy budget ledger is readable."
            ),
            budget_key_count=len(budget_spent),
            spent=budget_spent,
            invalid_negative_spend=negative_budgets,
        )

        if any(check["status"] == "error" for check in checks):
            status = "error"
        elif any(check["status"] == "warning" for check in checks):
            status = "warning"
        else:
            status = "ok"

        report = {
            "status": status,
            "generated_at": _utc_now(),
            "wallet_count": len(self.wallet_service.wallets),
            "check_count": len(checks),
            "checks": checks,
        }
        self._audit_ops_health(report)
        self._persist_all_wallets_if_configured()
        return report

    def _audit_ops_health(self, report: Mapping[str, Any]) -> None:
        check_statuses = {
            str(check.get("name")): str(check.get("status"))
            for check in report.get("checks", [])
            if isinstance(check, Mapping)
        }
        for wallet_id in sorted(self.wallet_service.wallets):
            append_audit_event(
                self.wallet_service.audit_events.setdefault(wallet_id, []),
                wallet_id=wallet_id,
                actor_did="did:wallet:ops",
                action="ops/health",
                resource=resource_for_wallet(wallet_id),
                decision="deny" if report.get("status") == "error" else "allow",
                details={
                    "status": report.get("status"),
                    "check_statuses": check_statuses,
                },
            )

    def _persist_wallet_if_configured(self, wallet_id: str) -> None:
        if self.repository is not None and self.auto_persist:
            self.repository.save(self.wallet_service, wallet_id)

    def _persist_all_wallets_if_configured(self) -> None:
        if self.repository is not None and self.auto_persist:
            self.repository.save_all(self.wallet_service)

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
        wallet = self.wallet_service.create_wallet(
            owner_did=owner_did,
            controller_dids=list(controller_dids) if controller_dids is not None else None,
            governance_policy=governance_policy,
        )
        self._persist_wallet_if_configured(wallet.wallet_id)
        return wallet

    def get_wallet(self, wallet_id: str):
        return self.wallet_service.get_wallet(wallet_id)

    def add_controller(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        controller_did: str,
        controller_secret: bytes | None = None,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.add_controller(
            wallet_id,
            actor_did=actor_did,
            controller_did=controller_did,
            controller_secret=controller_secret,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet

    def remove_controller(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        controller_did: str,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.remove_controller(
            wallet_id,
            actor_did=actor_did,
            controller_did=controller_did,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet

    def add_device(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        device_did: str,
        device_secret: bytes | None = None,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.add_device(
            wallet_id,
            actor_did=actor_did,
            device_did=device_did,
            device_secret=device_secret,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet

    def revoke_device(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        device_did: str,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.revoke_device(
            wallet_id,
            actor_did=actor_did,
            device_did=device_did,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet

    def set_recovery_policy(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        contact_dids: Sequence[str],
        threshold: int = 1,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.set_recovery_policy(
            wallet_id,
            actor_did=actor_did,
            contact_dids=list(contact_dids),
            threshold=threshold,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet

    def recover_controller(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        controller_did: str,
        controller_secret: bytes | None = None,
        approval_id: str | None = None,
    ):
        wallet = self.wallet_service.recover_controller(
            wallet_id,
            actor_did=actor_did,
            controller_did=controller_did,
            controller_secret=controller_secret,
            approval_id=approval_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return wallet

    def add_location(self, wallet_id: str, *, actor_did: str, lat: float, lon: float):
        record = self.wallet_service.add_location(wallet_id, actor_did=actor_did, lat=lat, lon=lon)
        self._persist_wallet_if_configured(wallet_id)
        return record

    def add_document(
        self,
        wallet_id: str,
        path: str | Path,
        *,
        actor_did: str,
        actor_secret: bytes | None = None,
        metadata: Dict[str, Any] | None = None,
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
        metadata: Dict[str, Any] | None = None,
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
        metadata: Dict[str, Any] | None = None,
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

        caveats: Dict[str, Any] = dict(extra_caveats or {})
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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

    def create_document_vector_profile_with_invocation(
        self,
        wallet_id: str,
        record_id: str,
        *,
        actor_did: str,
        invocation,
        actor_secret: bytes | None = None,
        chunk_size_words: int = 80,
    ) -> Dict[str, Any]:
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

    def analyze_records_redacted(
        self,
        wallet_id: str,
        record_ids: Sequence[str],
        *,
        actor_did: str,
        grant_id: str | None = None,
        actor_secret: bytes | None = None,
    ) -> Dict[str, Any]:
        result = self.wallet_service.analyze_documents_with_redaction(
            wallet_id,
            list(record_ids),
            actor_did=actor_did,
            grant_id=grant_id,
            actor_secret=actor_secret,
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
    ) -> Dict[str, Any]:
        grant = self.wallet_service.grants.get(grant_id)
        caveats: Dict[str, Any] = dict(extra or {})
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
    ) -> List[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
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
        caveats: Dict[str, Any] | None = None,
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

    def verify_export_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        bundle_hash = self.wallet_service.export_bundle_hash(bundle)
        embedded_hash = bundle.get("bundle_hash")
        return {
            "valid": self.wallet_service.verify_export_bundle(bundle),
            "bundle_id": bundle.get("bundle_id"),
            "bundle_hash": embedded_hash,
            "computed_hash": bundle_hash,
        }

    def import_export_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        result = self.wallet_service.import_export_bundle(bundle)
        wallet_id = result.get("wallet_id")
        if isinstance(wallet_id, str) and wallet_id:
            self._persist_wallet_if_configured(wallet_id)
        return result

    def verify_export_bundle_storage(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
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
        matches = match_services(
            self.services,
            need_terms=need_terms,
            location_claim=claim.to_dict(),
            limit=limit,
        )
        self._persist_wallet_if_configured(wallet_id)
        return matches

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
        grant = self.wallet_service.create_grant(
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
        self._persist_wallet_if_configured(wallet_id)
        return grant

    def create_location_region_proof_grant(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        expires_at: str | None = None,
    ):
        grant = self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_location(wallet_id, location_record_id)],
            abilities=["location/prove_region"],
            caveats={"purpose": "service_matching", "proof_type": "location_region"},
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return grant

    def create_location_region_proof(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        actor_did: str,
        region_id: str,
        grant_id: str | None = None,
    ):
        proof = self.wallet_service.create_location_region_proof(
            wallet_id,
            location_record_id,
            actor_did=actor_did,
            region_id=region_id,
            grant_id=grant_id,
        )
        self._persist_wallet_if_configured(wallet_id)
        return proof

    def issue_coarse_location_invocation(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        grant_id: str,
        actor_did: str,
        actor_secret: bytes | None = None,
        expires_at: str | None = None,
        purpose: str | None = None,
        user_present: bool = False,
    ):
        invocation = self.wallet_service.issue_invocation(
            wallet_id,
            grant_id=grant_id,
            actor_did=actor_did,
            resource=resource_for_location(wallet_id, location_record_id),
            ability="location/read_coarse",
            actor_secret=actor_secret,
            caveats=self._invocation_caveats(
                grant_id,
                fallback_purpose="service_matching",
                purpose=purpose,
                user_present=user_present,
                extra={"precision": "coarse"},
            ),
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return invocation

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
        matches = match_services(
            self.services,
            need_terms=need_terms,
            location_claim=claim.to_dict(),
            limit=limit,
        )
        self._persist_wallet_if_configured(wallet_id)
        return matches

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
        consent = self.wallet_service.create_analytics_consent(
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
        self._persist_wallet_if_configured(wallet_id)
        return consent

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
        status: str = "approved",
        expires_at: str | None = None,
    ):
        template = self.wallet_service.create_analytics_template(
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
            status=status,
            expires_at=expires_at,
        )
        self._persist_all_wallets_if_configured()
        return template

    def list_analytics_templates(self, *, include_inactive: bool = False):
        return self.wallet_service.list_analytics_templates(include_inactive=include_inactive)

    def list_analytics_consents(self, wallet_id: str, *, status: str = "all"):
        self.wallet_service._wallet(wallet_id)
        consents = [
            consent
            for consent in self.wallet_service.analytics_consents.values()
            if consent.wallet_id == wallet_id
        ]
        if status != "all":
            consents = [consent for consent in consents if consent.status == status]
        return sorted(consents, key=lambda item: item.created_at, reverse=True)

    def create_analytics_consent_from_template(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        template_id: str,
        expires_at: str | None = None,
    ):
        template = self.wallet_service.analytics_templates[template_id]
        consent = self.wallet_service.create_analytics_consent(
            wallet_id,
            actor_did=actor_did,
            template_id=template.template_id,
            allowed_record_types=list(template.allowed_record_types),
            allowed_derived_fields=list(template.allowed_derived_fields),
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return consent

    def revoke_analytics_consent(self, wallet_id: str, consent_id: str, *, actor_did: str):
        consent = self.wallet_service.revoke_analytics_consent(
            wallet_id,
            consent_id,
            actor_did=actor_did,
        )
        self._persist_wallet_if_configured(wallet_id)
        return consent

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
        contribution = self.wallet_service.create_analytics_contribution(
            wallet_id,
            actor_did=actor_did,
            consent_id=consent_id,
            template_id=template_id,
            fields=dict(fields),
        )
        self._persist_wallet_if_configured(wallet_id)
        return contribution

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
        result = self.wallet_service.run_aggregate_count(
            template_id,
            min_cohort_size=min_cohort_size,
            epsilon=epsilon,
            budget_key=budget_key,
            budget_limit=budget_limit,
            actor_did=actor_did,
        )
        self._persist_all_wallets_if_configured()
        return result

    def run_private_aggregate_count_by_fields(
        self,
        template_id: str,
        *,
        group_by: Sequence[str],
        epsilon: float | None = None,
        min_cohort_size: int | None = None,
        budget_key: str | None = None,
        budget_limit: float | None = None,
        actor_did: str = "did:service:211-ai-analytics",
    ):
        result = self.wallet_service.run_aggregate_count_by_fields(
            template_id,
            group_by=list(group_by),
            min_cohort_size=min_cohort_size,
            epsilon=epsilon,
            budget_key=budget_key,
            budget_limit=budget_limit,
            actor_did=actor_did,
        )
        self._persist_all_wallets_if_configured()
        return result

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
            "group_by": list(result.group_by),
            "cohorts": [dict(cohort) for cohort in result.cohorts],
            "suppressed_cohort_count": result.suppressed_cohort_count,
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
