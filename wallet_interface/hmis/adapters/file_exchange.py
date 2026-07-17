"""Deterministic file-exchange HMIS adapter skeleton."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..models import HmisActionType, HmisAdapterCapabilities, HmisAdapterResult


@dataclass(slots=True)
class FileExchangeHmisAdapter:
    staging_dir: Path
    fixture_imports: Sequence[Mapping[str, Any]] = ()
    name: str = "file-exchange"
    _staged_metadata: dict[str, dict[str, Any]] = field(default_factory=dict)

    def capabilities(self) -> HmisAdapterCapabilities:
        return HmisAdapterCapabilities(
            supports_referral_submit=True,
            supports_status_sync=True,
            supports_reconciliation=True,
        )

    def _payload_hash(self, payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    def _batch_id(self, payload: Mapping[str, Any]) -> str:
        return f"batch-{self._payload_hash(payload)[:16]}"

    def _outbound_path(self, batch_id: str) -> Path:
        return self.staging_dir / "outbound" / f"{batch_id}.json"

    def staged_metadata(self, batch_id: str) -> dict[str, Any] | None:
        return self._staged_metadata.get(batch_id)

    def execute(
        self,
        *,
        action_type: HmisActionType,
        payload: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> HmisAdapterResult:
        if action_type == "submit_referral":
            return self._submit_referral(payload)
        if action_type in {"sync_referral_status", "resolve_reconciliation_item"}:
            return self._reconcile(payload, context=context)
        return HmisAdapterResult.failure(
            action_type=action_type,
            adapter_name=self.name,
            summary=f"file exchange adapter does not implement {action_type}",
            errors=(f"unsupported action: {action_type}",),
        )

    def _submit_referral(self, payload: Mapping[str, Any]) -> HmisAdapterResult:
        batch_id = self._batch_id(payload)
        path = self._outbound_path(batch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        batch_payload = {
            "batch_id": batch_id,
            "submitted_at": str(payload.get("submitted_at") or ""),
            "records": [dict(payload)],
        }
        path.write_text(json.dumps(batch_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        metadata = {
            "batch_id": batch_id,
            "path": str(path),
            "record_count": 1,
            "payload_hash": self._payload_hash(payload),
        }
        self._staged_metadata[batch_id] = metadata
        return HmisAdapterResult.success(
            action_type="submit_referral",
            adapter_name=self.name,
            summary="staged outbound HMIS referral batch",
            external_refs={"batch_id": batch_id, "referral_id": batch_id},
            normalized_payload={"staging": metadata, "records": [dict(payload)]},
        )

    def _reconcile(
        self,
        payload: Mapping[str, Any],
        *,
        context: Mapping[str, Any] | None,
    ) -> HmisAdapterResult:
        imports = list(context.get("imports") or self.fixture_imports) if context is not None else list(self.fixture_imports)
        local_ref = str(payload.get("local_ref") or payload.get("local_referral_ref") or "")
        for row in imports:
            if str(row.get("local_ref") or row.get("local_referral_ref") or "") != local_ref:
                continue
            status = str(row.get("status") or "accepted").lower()
            if status in {"accepted", "success", "active", "closed"}:
                return HmisAdapterResult.success(
                    action_type="sync_referral_status",
                    adapter_name=self.name,
                    summary=f"reconciled referral status: {status}",
                    external_refs={"referral_id": str(row.get("external_referral_id") or row.get("referral_id") or local_ref)},
                    normalized_payload=dict(row),
                )
            return HmisAdapterResult.failure(
                action_type="sync_referral_status",
                adapter_name=self.name,
                summary=f"reconciliation import reported {status}",
                errors=(str(row.get("detail") or status),),
                retryable=status in {"retry", "pending", "waitlisted"},
                reconciliation_required=status not in {"retry", "pending", "waitlisted"},
                normalized_payload=dict(row),
            )
        return HmisAdapterResult.failure(
            action_type="sync_referral_status",
            adapter_name=self.name,
            summary="no reconciliation import matched the referral",
            errors=("missing import row",),
            retryable=True,
            normalized_payload=dict(payload),
        )


__all__ = ["FileExchangeHmisAdapter"]
