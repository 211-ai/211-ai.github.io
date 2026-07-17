"""Application-facing wallet service for 211-AI workflows."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ._vendor import ensure_ipfs_datasets_py_path
from .schemas.app_schemas import SavedServiceRecord, ServiceInteractionRecord, ServicePlanRecord
from .service_matching import ServiceMatch, ServiceRecord, load_services_jsonl, match_services
from .services import InteractionDomainServiceMixin, RecordDomainServiceMixin, WalletDomainServiceMixin

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet import (  # noqa: E402
    DeterministicLocationDistanceProofBackend,
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

from .proof_backends import HttpLocationRegionProofBackend  # noqa: E402
from .world_id import (  # noqa: E402
    WorldIdConfig,
    WorldIdRequestJson,
    WorldIdVerificationError,
    load_world_id_config,
    normalize_world_id_idkit_response,
    redact_world_id_payload,
    sign_world_id_request_from_config,
    verify_world_id_proof_from_config,
)

PROVIDER_STAFF_WORLD_ID_ACTION = "provider-staff-world-id-v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _storage_config_from_env() -> str | dict[str, Any] | None:
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

    config: dict[str, Any] = {"type": storage_type}
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
    if backend in {"deterministic-location-distance", "integration-location-distance"}:
        return DeterministicLocationDistanceProofBackend()
    if backend in {"http", "http-location-region", "remote-http", "verifier-http"}:
        verifier_headers: dict[str, str] = {}
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
            distance_prove_path=str(
                os.getenv("WALLET_PROOF_DISTANCE_PROVE_PATH") or "/prove/location-distance"
            ).strip(),
            verify_path=str(os.getenv("WALLET_PROOF_VERIFY_PATH") or "/verify").strip(),
            bearer_token=str(os.getenv("WALLET_PROOF_BEARER_TOKEN") or "").strip() or None,
            extra_headers=verifier_headers,
            timeout_seconds=float(str(os.getenv("WALLET_PROOF_TIMEOUT_SECONDS") or "30").strip()),
        )
    raise ValueError(
        "WALLET_PROOF_BACKEND must be default, simulated, deterministic-location-region, "
        "deterministic-location-distance, or http-location-region"
    )


def _repository_root_from_env() -> str | None:
    return os.getenv("WALLET_REPOSITORY_ROOT")


def _flag_from_env(name: str, *, default: bool) -> bool:
    explicit = os.getenv(name)
    if explicit is None:
        return default
    return explicit.lower() not in {"0", "false", "no", "off"}


PORTAL_STATE_TYPE = "wallet_repository_portal_state_v1"
PORTAL_STATE_FILENAME = "portal-state.json"


def _portal_now() -> str:
    return _utc_now()


def _portal_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def _unique_strings(values: Sequence[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _portal_resource(wallet_id: str, collection: str, entry_id: str) -> str:
    return f"{resource_for_wallet(wallet_id)}/portal/{collection}/{entry_id}"


class WalletInterfaceService(InteractionDomainServiceMixin, RecordDomainServiceMixin, WalletDomainServiceMixin):
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
        world_id_config: WorldIdConfig | None = None,
        world_id_request_json: WorldIdRequestJson | None = None,
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
        self.saved_services: dict[str, SavedServiceRecord] = {}
        self.service_plans: dict[str, ServicePlanRecord] = {}
        self.service_interactions: dict[str, ServiceInteractionRecord] = {}
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
            self._load_portal_state(required=False)
        self.services = list(services or [])
        self.world_id_config = world_id_config if world_id_config is not None else load_world_id_config()
        self.world_id_request_json = world_id_request_json

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
        world_id_config: WorldIdConfig | None = None,
        world_id_request_json: WorldIdRequestJson | None = None,
    ) -> WalletInterfaceService:
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
            world_id_config=world_id_config,
            world_id_request_json=world_id_request_json,
            services=load_services_jsonl(path),
        )

    def save_wallet_snapshot(self, wallet_id: str) -> Path:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        path = self.repository.save(self.wallet_service, wallet_id)
        self._save_portal_state()
        return path

    def load_wallet_snapshot(self, wallet_id: str) -> None:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        self.repository.load(self.wallet_service, wallet_id)
        self._load_portal_state(required=False)

    def verify_wallet_snapshot(self, wallet_id: str) -> dict[str, Any]:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        return self.repository.verify(wallet_id)

    def save_all_wallet_snapshots(self) -> list[Path]:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        paths = self.repository.save_all(self.wallet_service)
        self._save_portal_state()
        return paths

    def load_all_wallet_snapshots(self) -> list[str]:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        wallet_ids = self.repository.load_all(self.wallet_service)
        self._load_portal_state(required=False)
        return wallet_ids

    def list_wallet_snapshots(self) -> list[str]:
        if self.repository is None:
            return []
        return self.repository.list_wallet_ids()

    def ops_health(self, *, verify_storage: bool = False) -> dict[str, Any]:
        """Return actionable deployment health for wallet operations."""

        checks: list[dict[str, Any]] = []

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
        storage_failures: list[dict[str, Any]] = []
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
        proof_health_details: dict[str, Any] | None = None
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
            self._save_portal_state()

    def _persist_all_wallets_if_configured(self) -> None:
        if self.repository is not None and self.auto_persist:
            self.repository.save_all(self.wallet_service)
            self._save_portal_state()

    def _portal_state_path(self) -> Path:
        if self.repository is None:
            raise ValueError("Wallet repository is not configured")
        return self.repository.root / PORTAL_STATE_FILENAME

    def _portal_state_payload(self) -> dict[str, Any]:
        return {
            "snapshot_type": PORTAL_STATE_TYPE,
            "saved_services": [
                record.to_dict()
                for record in sorted(self.saved_services.values(), key=lambda item: (item.wallet_id, item.saved_service_id))
            ],
            "service_plans": [
                record.to_dict()
                for record in sorted(self.service_plans.values(), key=lambda item: (item.wallet_id, item.plan_id))
            ],
            "service_interactions": [
                record.to_dict()
                for record in sorted(
                    self.service_interactions.values(),
                    key=lambda item: (item.wallet_id, item.timestamp, item.interaction_id),
                )
            ],
        }

    def _save_portal_state(self) -> Path | None:
        if self.repository is None:
            return None
        path = self._portal_state_path()
        payload = self._portal_state_payload()
        tmp_path = path.with_name(f".{path.name}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp_path.replace(path)
        return path

    def _load_portal_state(self, *, required: bool = False) -> None:
        if self.repository is None:
            return
        path = self._portal_state_path()
        if not path.exists():
            if required:
                raise ValueError("Portal state snapshot not found")
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(payload.get("snapshot_type") or "") != PORTAL_STATE_TYPE:
            raise ValueError("Unsupported portal state snapshot type")
        self.saved_services = {
            record.saved_service_id: record
            for record in (
                SavedServiceRecord.from_dict(item)
                for item in payload.get("saved_services", [])
                if isinstance(item, Mapping)
            )
            if record.saved_service_id
        }
        self.service_plans = {
            record.plan_id: record
            for record in (
                ServicePlanRecord.from_dict(item)
                for item in payload.get("service_plans", [])
                if isinstance(item, Mapping)
            )
            if record.plan_id
        }
        self.service_interactions = {
            record.interaction_id: record
            for record in (
                ServiceInteractionRecord.from_dict(item)
                for item in payload.get("service_interactions", [])
                if isinstance(item, Mapping)
            )
            if record.interaction_id
        }

    def _wallet_principals(self, wallet_id: str) -> set[str]:
        wallet = self.wallet_service._wallet(wallet_id)
        return {str(wallet.owner_did), *[str(item) for item in wallet.controller_dids], *[str(item) for item in wallet.device_dids]}

    def _require_portal_actor(self, wallet_id: str, actor_did: str) -> None:
        actor = str(actor_did or "").strip()
        if not actor:
            raise ValueError("actor_did is required")
        if actor not in self._wallet_principals(wallet_id):
            raise ValueError("actor_did is not authorized for this wallet")

    def _portal_audit(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        action: str,
        resource: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        append_audit_event(
            self.wallet_service.audit_events.setdefault(wallet_id, []),
            wallet_id=wallet_id,
            actor_did=actor_did,
            action=action,
            resource=resource,
            decision="allow",
            details=dict(details or {}),
        )

    def get_world_id_config(self) -> dict[str, Any]:
        """Return browser-safe World ID configuration."""

        return dict(self.world_id_config.public_dict())

    def get_world_id_status(self, wallet_id: str, *, actor_did: str | None = None) -> dict[str, Any]:
        """Return sanitized World ID binding status for a wallet."""

        self.wallet_service._wallet(wallet_id)
        if actor_did is not None:
            self._require_portal_actor(wallet_id, actor_did)
        bindings = [
            binding.to_dict()
            for binding in sorted(
                self.wallet_service.list_world_id_bindings(wallet_id),
                key=lambda item: item.created_at,
            )
        ]
        active_bindings = [binding for binding in bindings if binding.get("status") == "active"]
        return {
            "enabled": self.world_id_config.enabled,
            "wallet": {
                "wallet_id": wallet_id,
                "binding_count": len(bindings),
                "active_binding_count": len(active_bindings),
                "bindings": bindings,
            },
        }

    def create_world_id_rp_signature(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        action: str | None = None,
        random_bytes: bytes | None = None,
        created_at: int | None = None,
    ) -> dict[str, Any]:
        """Create a fresh relying-party signature for the World ID IDKit client."""

        self._require_portal_actor(wallet_id, actor_did)
        selected_action = str(action or self.world_id_config.default_action).strip()
        if selected_action not in self.world_id_config.allowed_actions:
            raise ValueError("World ID action is not allowed")
        signature = sign_world_id_request_from_config(
            self.world_id_config,
            action=selected_action,
            random_bytes=random_bytes,
            created_at=created_at,
        )
        protocol_payload = signature.to_rp_context(self.world_id_config.rp_id)
        return {
            **protocol_payload,
            "signature": signature.signature,
            "action": selected_action,
            "app_id": self.world_id_config.app_id,
            "environment": self.world_id_config.environment,
            "credential_policy": self.world_id_config.credential_policy,
        }

    def create_provider_staff_world_id_rp_signature(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        provider_id: str,
        provider_staff_id: str,
        random_bytes: bytes | None = None,
        created_at: int | None = None,
    ) -> dict[str, Any]:
        """Create a World ID RP signature scoped to provider staff verification."""

        normalized_provider_id = str(provider_id or "").strip()
        normalized_staff_id = str(provider_staff_id or "").strip()
        if not normalized_provider_id:
            raise ValueError("provider organization policy is required before staff World ID verification")
        if not normalized_staff_id:
            raise ValueError("provider staff ID is required before staff World ID verification")
        payload = self.create_world_id_rp_signature(
            wallet_id,
            actor_did=actor_did,
            action=PROVIDER_STAFF_WORLD_ID_ACTION,
            random_bytes=random_bytes,
            created_at=created_at,
        )
        return {
            **payload,
            "action": PROVIDER_STAFF_WORLD_ID_ACTION,
            "provider_id": normalized_provider_id,
            "provider_staff_id": normalized_staff_id,
            "signal_context": "provider_staff_verification",
        }

    def register_world_id_verification(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        idkit_payload: Mapping[str, Any],
        request_json: WorldIdRequestJson | None = None,
    ) -> dict[str, Any]:
        """Verify an IDKit result and bind the resulting proof-of-human to a wallet."""

        self._require_portal_actor(wallet_id, actor_did)
        normalized = normalize_world_id_idkit_response(idkit_payload)
        selected_action = normalized.action or self.world_id_config.default_action
        if selected_action not in self.world_id_config.allowed_actions:
            raise ValueError("World ID action is not allowed")
        verifier = request_json or self.world_id_request_json
        verification = verify_world_id_proof_from_config(
            self.world_id_config,
            idkit_payload,
            request_json=verifier,
        )
        if not verification.success:
            raise WorldIdVerificationError(verification.message or "World ID verification failed")
        raw_nullifier = verification.nullifier or (normalized.nullifiers[0] if normalized.nullifiers else "")
        if not raw_nullifier:
            raise WorldIdVerificationError("World ID verification did not return a nullifier")
        signal_hash_ref = ""
        if normalized.signal_hashes:
            signal_hash_ref = "worldid-signal-ref:v1:" + hashlib.sha256(
                json.dumps(sorted(normalized.signal_hashes), sort_keys=True).encode("utf-8")
            ).hexdigest()
        binding = self.wallet_service.add_world_id_binding(
            wallet_id,
            actor_did=actor_did,
            rp_id=self.world_id_config.rp_id,
            app_id=self.world_id_config.app_id,
            action=verification.action or selected_action,
            protocol_version=normalized.protocol_version,
            environment=verification.environment or normalized.environment or self.world_id_config.environment,
            raw_nullifier=raw_nullifier,
            credential_identifiers=list(normalized.credential_identifiers),
            issuer_schema_ids=[
                schema_id for schema_id in (response.issuer_schema_id for response in normalized.responses) if schema_id
            ],
            session_id=normalized.session_id or verification.session_id,
            signal_hash_ref=signal_hash_ref,
            verification_status="verified",
            verified_at=verification.created_at or _utc_now(),
            expires_at_min=min(normalized.expires_at_min_values) if normalized.expires_at_min_values else None,
            metadata={
                "credential_policy": self.world_id_config.credential_policy,
                "idkit": normalized.public_dict(),
                "verification": redact_world_id_payload(verification.public_dict()),
            },
        )
        proof = self.wallet_service.proofs.get(binding.proof_receipt_id or "")
        self._persist_wallet_if_configured(wallet_id)
        return {
            "binding": binding.to_dict(),
            "proof": proof.to_dict() if proof is not None else None,
            "verification": redact_world_id_payload(verification.public_dict()),
        }

    def revoke_world_id_binding(
        self,
        wallet_id: str,
        binding_id: str,
        *,
        actor_did: str,
        reason: str | None = None,
    ):
        """Mark a World ID wallet binding revoked and persist the wallet snapshot."""

        self._require_portal_actor(wallet_id, actor_did)
        binding = self.wallet_service.get_world_id_binding(binding_id)
        if binding.wallet_id != wallet_id:
            raise ValueError("World ID binding does not belong to this wallet")
        if binding.status != "revoked":
            binding.status = "revoked"
            binding.updated_at = _utc_now()
            binding.metadata = {**dict(binding.metadata), "revoked_reason": str(reason or "").strip()}
            append_audit_event(
                self.wallet_service.audit_events.setdefault(wallet_id, []),
                wallet_id=wallet_id,
                actor_did=actor_did,
                action="wallet/world_id_revoke",
                resource=f"wallet://{wallet_id}/world-id-bindings/{binding.binding_id}",
                decision="allow",
                details={"binding_id": binding.binding_id, "reason": str(reason or "").strip()},
            )
            self._persist_wallet_if_configured(wallet_id)
        return binding

    def match_services_for_wallet(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        actor_did: str,
        need_terms: Sequence[str],
        grant_id: str | None = None,
        limit: int = 10,
    ) -> list[ServiceMatch]:
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

    def create_location_distance_proof_grant(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        issuer_did: str,
        audience_did: str,
        target_id: str,
        max_distance_km: float,
        expires_at: str | None = None,
    ):
        grant = self.wallet_service.create_grant(
            wallet_id=wallet_id,
            issuer_did=issuer_did,
            audience_did=audience_did,
            resources=[resource_for_location(wallet_id, location_record_id)],
            abilities=["location/prove_distance"],
            caveats={
                "purpose": "service_matching",
                "proof_type": "location_distance",
                "target_id": target_id,
                "max_distance_km": float(max_distance_km),
            },
            expires_at=expires_at,
        )
        self._persist_wallet_if_configured(wallet_id)
        return grant

    def create_location_distance_proof(
        self,
        wallet_id: str,
        location_record_id: str,
        *,
        actor_did: str,
        target_id: str,
        target_lat: float,
        target_lon: float,
        max_distance_km: float,
        grant_id: str | None = None,
    ):
        proof = self.wallet_service.create_location_distance_proof(
            wallet_id,
            location_record_id,
            actor_did=actor_did,
            target_id=target_id,
            target_lat=target_lat,
            target_lon=target_lon,
            max_distance_km=max_distance_km,
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
    ) -> list[ServiceMatch]:
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
        derived_facts: dict[str, Any],
        limit: int = 10,
    ) -> list[ServiceMatch]:
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
        fields: dict[str, Any],
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

    def summarize_aggregate_result(self, result) -> dict[str, Any]:
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

    def _reject_precise_analytics_fields(self, fields: dict[str, Any]) -> None:
        for key, value in fields.items():
            normalized_key = key.lower()
            if normalized_key in {"lat", "lon", "latitude", "longitude"}:
                raise ValueError("analytics contributions require derived or coarse fields, not precise coordinates")
            if normalized_key.startswith("precise_"):
                raise ValueError("analytics contributions require derived or coarse fields, not precise fields")
            if isinstance(value, dict):
                match_services([], need_terms=[], location_claim=value)



def _hmis_now() -> str:
    return datetime.now(UTC).isoformat()


HMIS_STATE_TYPE = "wallet_repository_hmis_state_v1"
HMIS_STATE_FILENAME = "hmis-state.json"
HMIS_AUDIT_FILENAME = "hmis-audit.jsonl"


DEFAULT_HMIS_FIXTURES = {
    "clients": [
        {
            "entity_type": "client",
            "external_client_id": "client-100",
            "name": "Jane Doe",
            "date_of_birth": "1990-04-05",
            "program_ref": "shelter-a",
            "phone": "503-555-0100",
            "email": "jane@example.org",
            "last_sync_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "entity_type": "client",
            "external_client_id": "client-200",
            "name": "Alex Smith",
            "date_of_birth": "1984-01-02",
            "program_ref": "rapid-rehousing",
            "phone": "503-555-0200",
            "email": "alex@example.org",
            "last_sync_at": "2026-07-02T10:00:00+00:00",
        },
    ],
    "households": [
        {
            "entity_type": "household",
            "external_household_id": "household-100",
            "household_name": "Doe Household",
            "program_ref": "shelter-a",
            "member_count": 2,
            "last_sync_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "entity_type": "household",
            "external_household_id": "household-200",
            "household_name": "Rivera Household",
            "program_ref": "rapid-rehousing",
            "member_count": 3,
            "last_sync_at": "2026-07-02T10:00:00+00:00",
        },
    ],
    "programs": [
        {
            "entity_type": "program",
            "local_program_ref": "shelter-a",
            "program_name": "Emergency Shelter",
            "provider_name": "Safe Harbor Shelter",
            "external_program_id": "HMIS-PROGRAM-100",
            "external_project_id": "HMIS-PROJECT-100",
            "last_sync_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "entity_type": "program",
            "local_program_ref": "rapid-rehousing",
            "program_name": "Rapid Rehousing",
            "provider_name": "Bridge Housing Network",
            "external_program_id": "HMIS-PROGRAM-200",
            "external_project_id": "HMIS-PROJECT-200",
            "last_sync_at": "2026-07-02T10:00:00+00:00",
        },
    ],
}


def _hmis_repository_root(self: WalletInterfaceService) -> Path:
    if self.repository is not None:
        return self.repository.root
    return Path.cwd()



def _hmis_state_path(self: WalletInterfaceService) -> Path:
    return _hmis_repository_root(self) / HMIS_STATE_FILENAME



def _hmis_audit_path(self: WalletInterfaceService) -> Path:
    return _hmis_repository_root(self) / HMIS_AUDIT_FILENAME



def _empty_hmis_state() -> dict[str, Any]:
    return {
        "snapshot_type": HMIS_STATE_TYPE,
        "referral_drafts": [],
        "verified_links": [],
        "rejected_matches": [],
        "reconciliation_items": [],
        "submissions": {},
    }



def _ensure_hmis_state(self: WalletInterfaceService) -> dict[str, Any]:
    cached = getattr(self, "_hmis_state_cache", None)
    if isinstance(cached, dict):
        return cached
    path = _hmis_state_path(self)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if str(payload.get("snapshot_type") or "") != HMIS_STATE_TYPE:
            raise ValueError("Unsupported HMIS state snapshot type")
    else:
        payload = _empty_hmis_state()
    setattr(self, "_hmis_state_cache", payload)
    return payload



def _save_hmis_state(self: WalletInterfaceService) -> Path:
    payload = _ensure_hmis_state(self)
    path = _hmis_state_path(self)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return path



def _hmis_audit_store(self: WalletInterfaceService):
    from .hmis.audit import HmisAuditStore

    store = getattr(self, "_hmis_audit_store", None)
    if store is None:
        store = HmisAuditStore(path=_hmis_audit_path(self))
        setattr(self, "_hmis_audit_store", store)
    return store



def _load_hmis_fixture_group(self: WalletInterfaceService, name: str) -> list[dict[str, Any]]:
    root = _hmis_repository_root(self)
    path = root / "tests" / "fixtures" / "hmis" / f"{name}.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, Mapping)]
    return [dict(item) for item in DEFAULT_HMIS_FIXTURES[name]]



def _load_program_links(self: WalletInterfaceService) -> list[dict[str, Any]]:
    path = Path("state/hmis/program_links.json")
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(item) for item in payload.get("program_links", []) if isinstance(item, Mapping)]



def _mask_name(value: str) -> str:
    parts = [part for part in str(value or "").strip().split() if part]
    return " ".join(f"{part[:1]}***" for part in parts)



def _mask_hmis_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    masked = dict(candidate)
    if "name" in masked:
        masked["name"] = _mask_name(str(masked.get("name") or ""))
    if "household_name" in masked:
        masked["household_name"] = _mask_name(str(masked.get("household_name") or ""))
    if "phone" in masked:
        masked["phone"] = "***-***-" + str(masked.get("phone") or "")[-4:]
    if "email" in masked:
        local, _, domain = str(masked.get("email") or "").partition("@")
        masked["email"] = (local[:1] + "***@" + domain) if domain else "***"
    if masked.get("date_of_birth"):
        masked["date_of_birth"] = str(masked["date_of_birth"])[:4]
    masked["masked"] = True
    return masked



def _hmis_manual_adapter(self: WalletInterfaceService):
    from .hmis.adapters.manual_review import ManualReviewHmisAdapter

    fixtures = [
        *_load_hmis_fixture_group(self, "clients"),
        *_load_hmis_fixture_group(self, "households"),
        *_load_hmis_fixture_group(self, "programs"),
    ]
    return ManualReviewHmisAdapter(fixtures=fixtures)



def _hmis_submission_service(self: WalletInterfaceService):
    from .hmis import FileExchangeHmisAdapter, HmisService
    from .hmis.service import HmisReconciliationItem

    service = getattr(self, "_hmis_submission_service_cache", None)
    if service is None:
        adapter = FileExchangeHmisAdapter(
            staging_dir=_hmis_repository_root(self) / "data" / "hmis",
            fixture_imports=getattr(self, "_hmis_fixture_imports", ()),
        )
        service = HmisService(adapter=adapter, audit_store=_hmis_audit_store(self))
        state = _ensure_hmis_state(self)
        service.reconciliation_queue = [
            HmisReconciliationItem.from_dict(item)
            for item in state.get("reconciliation_items", [])
            if isinstance(item, Mapping)
        ]
        setattr(self, "_hmis_submission_service_cache", service)
    return service



def _store_reconciliation_queue(self: WalletInterfaceService) -> None:
    service = _hmis_submission_service(self)
    state = _ensure_hmis_state(self)
    state["reconciliation_items"] = [item.to_dict() for item in service.list_reconciliation_items()]
    _save_hmis_state(self)



def lookup_hmis_clients(
    self: WalletInterfaceService,
    wallet_id: str,
    *,
    actor_did: str,
    name: str = "",
    date_of_birth: str = "",
    program_ref: str = "",
) -> dict[str, Any]:
    from .hmis.matching import match_hmis_clients

    self._require_portal_actor(wallet_id, actor_did)
    query = {"name": name, "date_of_birth": date_of_birth, "program_ref": program_ref}
    adapter_result = _hmis_manual_adapter(self).execute(action_type="lookup_client", payload=query)
    candidates = adapter_result.normalized_payload.get("candidates", [])
    state = _ensure_hmis_state(self)
    rejected = [
        item.get("external_id", "")
        for item in state.get("rejected_matches", [])
        if item.get("wallet_id") == wallet_id and item.get("entity_type") == "client"
    ]
    match_result = match_hmis_clients(query, candidates, rejected_candidate_ids=rejected)
    _hmis_audit_store(self).record(
        action_type="lookup_client",
        actor_id=actor_did,
        local_ref=wallet_id,
        adapter_name="manual-review",
        status="success",
        response_summary=adapter_result.summary,
        metadata={"candidate_count": len(match_result.candidates), "decision": match_result.decision},
    )
    return {
        "status": "ok",
        "summary": adapter_result.summary,
        "clients": [
            {
                **_mask_hmis_candidate(candidate.record),
                "external_id": candidate.external_id,
                "score": candidate.score,
                "matched_fields": list(candidate.matched_fields),
                "reasons": list(candidate.reasons),
            }
            for candidate in match_result.candidates
        ],
        "rejected_candidates": [
            {
                **_mask_hmis_candidate(candidate.record),
                "external_id": candidate.external_id,
                "score": candidate.score,
                "matched_fields": list(candidate.matched_fields),
            }
            for candidate in match_result.rejected_candidates
        ],
        "decision": match_result.decision,
        "last_sync_at": _hmis_now(),
    }



def lookup_hmis_households(
    self: WalletInterfaceService,
    wallet_id: str,
    *,
    actor_did: str,
    name: str = "",
    program_ref: str = "",
) -> dict[str, Any]:
    from .hmis.matching import match_hmis_households

    self._require_portal_actor(wallet_id, actor_did)
    query = {"name": name, "program_ref": program_ref}
    adapter_result = _hmis_manual_adapter(self).execute(action_type="lookup_household", payload=query)
    candidates = adapter_result.normalized_payload.get("candidates", [])
    state = _ensure_hmis_state(self)
    rejected = [
        item.get("external_id", "")
        for item in state.get("rejected_matches", [])
        if item.get("wallet_id") == wallet_id and item.get("entity_type") == "household"
    ]
    match_result = match_hmis_households(query, candidates, rejected_candidate_ids=rejected)
    _hmis_audit_store(self).record(
        action_type="lookup_household",
        actor_id=actor_did,
        local_ref=wallet_id,
        adapter_name="manual-review",
        status="success",
        response_summary=adapter_result.summary,
        metadata={"candidate_count": len(match_result.candidates), "decision": match_result.decision},
    )
    return {
        "status": "ok",
        "summary": adapter_result.summary,
        "households": [
            {
                **_mask_hmis_candidate(candidate.record),
                "external_id": candidate.external_id,
                "score": candidate.score,
                "matched_fields": list(candidate.matched_fields),
            }
            for candidate in match_result.candidates
        ],
        "decision": match_result.decision,
        "last_sync_at": _hmis_now(),
    }



def list_hmis_program_links(
    self: WalletInterfaceService,
    wallet_id: str,
    *,
    actor_did: str,
    name: str = "",
    program_ref: str = "",
) -> dict[str, Any]:
    self._require_portal_actor(wallet_id, actor_did)
    results = []
    name_query = str(name or "").strip().lower()
    program_query = str(program_ref or "").strip().lower()
    for item in _load_program_links(self):
        haystacks = [
            str(item.get("program_name") or "").lower(),
            str(item.get("provider_name") or "").lower(),
            str(item.get("local_program_ref") or "").lower(),
        ]
        if name_query and not any(name_query in hay for hay in haystacks):
            continue
        if program_query and program_query not in haystacks:
            continue
        results.append(item)
    _hmis_audit_store(self).record(
        action_type="list_program_links",
        actor_id=actor_did,
        local_ref=wallet_id,
        adapter_name="registry",
        status="success",
        response_summary=f"returned {len(results)} HMIS program link(s)",
    )
    return {"status": "ok", "program_links": results, "programs": results, "summary": f"returned {len(results)} program links"}



def list_hmis_referral_drafts(self: WalletInterfaceService, wallet_id: str, *, status: str | None = None):
    from .hmis.service import HmisReferralDraftRecord

    self.wallet_service._wallet(wallet_id)
    drafts = [
        HmisReferralDraftRecord.from_dict(item)
        for item in _ensure_hmis_state(self).get("referral_drafts", [])
        if isinstance(item, Mapping) and str(item.get("wallet_id") or "") == wallet_id
    ]
    if status is not None:
        drafts = [draft for draft in drafts if draft.status == status]
    return sorted(drafts, key=lambda item: (item.updated_at or item.created_at, item.referral_draft_id))



def create_hmis_referral_draft(
    self: WalletInterfaceService,
    wallet_id: str,
    *,
    actor_did: str,
    local_subject_ref: str,
    destination_program_ref: str,
    service_plan_id: str = "",
    service_doc_id: str = "",
    provider_name: str = "",
    program_name: str = "",
    summary: str = "",
    eligibility_notes: str = "",
    contact_notes: str = "",
    source_content_cid: str = "",
    source_page_cid: str = "",
    metadata: Mapping[str, Any] | None = None,
):
    from .hmis.service import HmisReferralDraftRecord

    self._require_portal_actor(wallet_id, actor_did)
    now = _hmis_now()
    state = _ensure_hmis_state(self)
    draft = HmisReferralDraftRecord(
        referral_draft_id=f"hmis-referral-draft-{uuid4().hex}",
        wallet_id=wallet_id,
        actor_id=actor_did,
        local_subject_ref=str(local_subject_ref or "").strip(),
        destination_program_ref=str(destination_program_ref or "").strip(),
        service_plan_id=str(service_plan_id or ""),
        service_doc_id=str(service_doc_id or ""),
        provider_name=str(provider_name or ""),
        program_name=str(program_name or ""),
        summary=str(summary or ""),
        eligibility_notes=str(eligibility_notes or ""),
        contact_notes=str(contact_notes or ""),
        source_content_cid=str(source_content_cid or ""),
        source_page_cid=str(source_page_cid or ""),
        status="draft",
        created_at=now,
        updated_at=now,
        metadata=dict(metadata or {}),
    )
    validator = _hmis_submission_service(self)
    errors, warnings = validator.validate_referral_draft(draft)
    draft.validation_errors = errors
    draft.warnings = warnings
    if not errors:
        draft.status = "ready"
    state["referral_drafts"].append(draft.to_dict())
    _save_hmis_state(self)
    _hmis_audit_store(self).record(
        action_type="create_referral_draft",
        actor_id=actor_did,
        local_ref=draft.referral_draft_id,
        adapter_name="manual-review",
        status="success",
        response_summary="created HMIS referral draft",
        metadata={"wallet_id": wallet_id, "status": draft.status},
    )
    return draft



def update_hmis_referral_draft(
    self: WalletInterfaceService,
    wallet_id: str,
    referral_draft_id: str,
    *,
    actor_did: str,
    local_subject_ref: str | None = None,
    destination_program_ref: str | None = None,
    service_plan_id: str | None = None,
    service_doc_id: str | None = None,
    provider_name: str | None = None,
    program_name: str | None = None,
    summary: str | None = None,
    eligibility_notes: str | None = None,
    contact_notes: str | None = None,
    source_content_cid: str | None = None,
    source_page_cid: str | None = None,
    metadata: Mapping[str, Any] | None = None,
):
    self._require_portal_actor(wallet_id, actor_did)
    drafts = list_hmis_referral_drafts(self, wallet_id)
    draft = next((item for item in drafts if item.referral_draft_id == referral_draft_id), None)
    if draft is None:
        raise ValueError("HMIS referral draft not found")
    for field_name, value in {
        "local_subject_ref": local_subject_ref,
        "destination_program_ref": destination_program_ref,
        "service_plan_id": service_plan_id,
        "service_doc_id": service_doc_id,
        "provider_name": provider_name,
        "program_name": program_name,
        "summary": summary,
        "eligibility_notes": eligibility_notes,
        "contact_notes": contact_notes,
        "source_content_cid": source_content_cid,
        "source_page_cid": source_page_cid,
    }.items():
        if value is not None:
            setattr(draft, field_name, str(value or ""))
    if metadata is not None:
        draft.metadata = {**draft.metadata, **dict(metadata)}
    draft.updated_at = _hmis_now()
    errors, warnings = _hmis_submission_service(self).validate_referral_draft(draft)
    draft.validation_errors = errors
    draft.warnings = warnings
    draft.status = "ready" if not errors else "draft"
    state = _ensure_hmis_state(self)
    state["referral_drafts"] = [
        draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item
        for item in state.get("referral_drafts", [])
    ]
    _save_hmis_state(self)
    _hmis_audit_store(self).record(
        action_type="validate_referral_draft",
        actor_id=actor_did,
        local_ref=referral_draft_id,
        adapter_name="manual-review",
        status="success",
        response_summary="updated HMIS referral draft",
        metadata={"status": draft.status},
    )
    return draft



def validate_hmis_referral_draft(
    self: WalletInterfaceService,
    wallet_id: str,
    referral_draft_id: str,
    *,
    actor_did: str,
) -> dict[str, Any]:
    self._require_portal_actor(wallet_id, actor_did)
    draft = next((item for item in list_hmis_referral_drafts(self, wallet_id) if item.referral_draft_id == referral_draft_id), None)
    if draft is None:
        raise ValueError("HMIS referral draft not found")
    errors, warnings = _hmis_submission_service(self).validate_referral_draft(draft)
    draft.validation_errors = errors
    draft.warnings = warnings
    draft.status = "ready" if not errors else "draft"
    state = _ensure_hmis_state(self)
    state["referral_drafts"] = [
        draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item
        for item in state.get("referral_drafts", [])
    ]
    _save_hmis_state(self)
    _hmis_audit_store(self).record(
        action_type="validate_referral_draft",
        actor_id=actor_did,
        local_ref=referral_draft_id,
        adapter_name="manual-review",
        status="success",
        response_summary="validated HMIS referral draft",
        metadata={"validation_errors": list(errors), "warnings": list(warnings)},
    )
    return {"status": draft.status, "errors": errors, "warnings": warnings, "referral_draft": draft.to_dict()}



def submit_hmis_referral_draft(
    self: WalletInterfaceService,
    wallet_id: str,
    referral_draft_id: str,
    *,
    actor_did: str,
) -> dict[str, Any]:
    from .hmis.models import HmisConsentRecord

    self._require_portal_actor(wallet_id, actor_did)
    draft = next((item for item in list_hmis_referral_drafts(self, wallet_id) if item.referral_draft_id == referral_draft_id), None)
    if draft is None:
        raise ValueError("HMIS referral draft not found")
    errors, warnings = _hmis_submission_service(self).validate_referral_draft(draft)
    if errors:
        raise ValueError("HMIS referral draft has validation errors")
    consent = HmisConsentRecord(
        consent_id=f"consent-{wallet_id}",
        subject_ref=draft.local_subject_ref,
        status="active",
        basis="client_consent",
        purpose="HMIS referral submission",
        authorized_scopes=("hmis_submit_referral",),
        authorized_program_refs=(draft.destination_program_ref,),
        effective_at="2026-01-01T00:00:00+00:00",
    )
    result = _hmis_submission_service(self).submit_referral(
        draft,
        actor_id=actor_did,
        consent=consent,
        required_scope="hmis_submit_referral",
        context={"imports": getattr(self, "_hmis_fixture_imports", ())},
    )
    draft.updated_at = _hmis_now()
    if result.adapter_result.ok:
        draft.status = "submitted"
        draft.external_referral_id = result.adapter_result.external_refs.get("referral_id") or result.adapter_result.external_refs.get("batch_id") or ""
    else:
        draft.status = "retryable" if result.adapter_result.retryable else "needs_review"
    draft.warnings = [*warnings, *list(result.adapter_result.warnings)]
    state = _ensure_hmis_state(self)
    state["referral_drafts"] = [
        draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item
        for item in state.get("referral_drafts", [])
    ]
    state.setdefault("submissions", {})[referral_draft_id] = {
        "status": draft.status,
        "summary": result.adapter_result.summary,
        "external_refs": dict(result.adapter_result.external_refs),
    }
    _store_reconciliation_queue(self)
    return {"status": draft.status, "summary": result.adapter_result.summary, "referral_draft": draft.to_dict(), "external_refs": dict(result.adapter_result.external_refs)}



def verify_hmis_match(
    self: WalletInterfaceService,
    wallet_id: str,
    *,
    actor_did: str,
    entity_type: str,
    local_ref: str,
    external_id: str,
    confidence: float,
) -> dict[str, Any]:
    self._require_portal_actor(wallet_id, actor_did)
    state = _ensure_hmis_state(self)
    link = {
        "wallet_id": wallet_id,
        "entity_type": entity_type,
        "local_ref": local_ref,
        "external_id": external_id,
        "confidence": float(confidence),
        "status": "verified",
        "reviewed_by": actor_did,
        "reviewed_at": _hmis_now(),
    }
    state["verified_links"] = [
        item
        for item in state.get("verified_links", [])
        if not (
            item.get("wallet_id") == wallet_id
            and item.get("entity_type") == entity_type
            and item.get("local_ref") == local_ref
        )
    ]
    state["verified_links"].append(link)
    _save_hmis_state(self)
    _hmis_audit_store(self).record(
        action_type="link_external_record",
        actor_id=actor_did,
        local_ref=local_ref,
        external_ref=external_id,
        adapter_name="manual-review",
        status="success",
        response_summary="verified HMIS record link",
    )
    return link



def reject_hmis_match(
    self: WalletInterfaceService,
    wallet_id: str,
    *,
    actor_did: str,
    entity_type: str,
    local_ref: str,
    external_id: str,
    reason: str,
) -> dict[str, Any]:
    self._require_portal_actor(wallet_id, actor_did)
    state = _ensure_hmis_state(self)
    record = {
        "wallet_id": wallet_id,
        "entity_type": entity_type,
        "local_ref": local_ref,
        "external_id": external_id,
        "reason": reason,
        "rejected_by": actor_did,
        "rejected_at": _hmis_now(),
    }
    state.setdefault("rejected_matches", []).append(record)
    _save_hmis_state(self)
    _hmis_audit_store(self).record(
        action_type="reject_match",
        actor_id=actor_did,
        local_ref=local_ref,
        external_ref=external_id,
        adapter_name="manual-review",
        status="success",
        response_summary="rejected HMIS match candidate",
        metadata={"reason": reason},
    )
    return record



def list_hmis_sync_timeline(self: WalletInterfaceService, wallet_id: str, *, local_ref: str | None = None) -> dict[str, Any]:
    self.wallet_service._wallet(wallet_id)
    events = _hmis_audit_store(self).list_events(local_ref=local_ref or None)
    return {
        "status": "ok",
        "events": [
            {
                "event_id": event.event_id,
                "action_type": event.action_type,
                "actor_id": event.actor_id,
                "local_ref": event.local_ref,
                "external_ref": event.external_ref,
                "adapter_name": event.adapter_name,
                "status": event.status,
                "response_summary": event.response_summary,
                "occurred_at": event.occurred_at,
                "retry_count": event.retry_count,
                "metadata": dict(event.metadata),
            }
            for event in events
        ],
    }



def list_hmis_reconciliation_queue(self: WalletInterfaceService, wallet_id: str, *, status: str | None = None) -> dict[str, Any]:
    self.wallet_service._wallet(wallet_id)
    items = [item for item in _hmis_submission_service(self).list_reconciliation_items(status=status) if item.wallet_id == wallet_id]
    return {"status": "ok", "items": [item.to_dict() for item in items]}



def retry_hmis_reconciliation_item(self: WalletInterfaceService, wallet_id: str, item_id: str, *, actor_did: str) -> dict[str, Any]:
    self._require_portal_actor(wallet_id, actor_did)
    service = _hmis_submission_service(self)
    item = next((row for row in service.list_reconciliation_items() if row.item_id == item_id and row.wallet_id == wallet_id), None)
    if item is None:
        raise ValueError("HMIS reconciliation item not found")
    result = service.retry_reconciliation_item(item, actor_id=actor_did, context={"imports": getattr(self, "_hmis_fixture_imports", ())})
    _store_reconciliation_queue(self)
    return {
        "status": item.status,
        "summary": result.adapter_result.summary,
        "item": item.to_dict(),
        "external_refs": dict(result.adapter_result.external_refs),
    }



def run_hmis_reconciliation_job(self: WalletInterfaceService, *, dry_run: bool = False) -> dict[str, Any]:
    service = _hmis_submission_service(self)
    open_items = [item for item in service.list_reconciliation_items() if item.status == "open"]
    resolved = 0
    reviewed = 0
    for item in open_items:
        if dry_run:
            continue
        result = service.retry_reconciliation_item(item, actor_id="did:wallet:hmis-reconciliation", context={"imports": getattr(self, "_hmis_fixture_imports", ())})
        if result.adapter_result.ok:
            resolved += 1
            draft = next((row for row in list_hmis_referral_drafts(self, item.wallet_id) if row.referral_draft_id == item.referral_draft_id), None)
            if draft is not None:
                draft.status = "reconciled"
                draft.updated_at = _hmis_now()
                state = _ensure_hmis_state(self)
                state["referral_drafts"] = [
                    draft.to_dict() if row.get("referral_draft_id") == draft.referral_draft_id else row
                    for row in state.get("referral_drafts", [])
                ]
        elif item.status == "needs_review":
            reviewed += 1
    if not dry_run:
        _store_reconciliation_queue(self)
    queue_items = service.list_reconciliation_items()
    return {
        "status": "dry-run" if dry_run else "ok",
        "queue_depth": len(queue_items),
        "open_count": sum(1 for item in queue_items if item.status == "open"),
        "resolved_count": sum(1 for item in queue_items if item.status == "resolved") if dry_run else resolved,
        "needs_review_count": sum(1 for item in queue_items if item.status == "needs_review") if dry_run else reviewed,
    }


WalletInterfaceService.lookup_hmis_clients = lookup_hmis_clients
WalletInterfaceService.lookup_hmis_households = lookup_hmis_households
WalletInterfaceService.list_hmis_program_links = list_hmis_program_links
WalletInterfaceService.list_hmis_referral_drafts = list_hmis_referral_drafts
WalletInterfaceService.create_hmis_referral_draft = create_hmis_referral_draft
WalletInterfaceService.update_hmis_referral_draft = update_hmis_referral_draft
WalletInterfaceService.validate_hmis_referral_draft = validate_hmis_referral_draft
WalletInterfaceService.submit_hmis_referral_draft = submit_hmis_referral_draft
WalletInterfaceService.verify_hmis_match = verify_hmis_match
WalletInterfaceService.reject_hmis_match = reject_hmis_match
WalletInterfaceService.list_hmis_sync_timeline = list_hmis_sync_timeline
WalletInterfaceService.list_hmis_reconciliation_queue = list_hmis_reconciliation_queue
WalletInterfaceService.retry_hmis_reconciliation_item = retry_hmis_reconciliation_item
WalletInterfaceService.run_hmis_reconciliation_job = run_hmis_reconciliation_job
