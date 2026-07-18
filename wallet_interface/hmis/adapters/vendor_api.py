"""Fixture-driven HMIS vendor API adapter skeleton."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..errors import HmisAdapterError
from ..models import HmisActionType, HmisAdapterCapabilities, HmisAdapterResult

TransportCallable = Callable[[str, Mapping[str, Any], Mapping[str, str]], Mapping[str, Any]]


@dataclass(slots=True)
class VendorApiHmisAdapter:
    auth_token: str | None = None
    fixture_responses: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    transport: TransportCallable | None = None
    name: str = "vendor-api"

    def capabilities(self) -> HmisAdapterCapabilities:
        return HmisAdapterCapabilities(
            supports_lookup=True,
            supports_referral_submit=True,
            supports_enrollment_submit=True,
            supports_status_sync=True,
            supports_reconciliation=True,
        )

    def build_auth_headers(self) -> dict[str, str]:
        if not self.auth_token:
            return {}
        return {"authorization": "******"}

    def translate_payload(self, action_type: HmisActionType, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "operation": action_type,
            "record": dict(payload),
        }

    def execute(
        self,
        *,
        action_type: HmisActionType,
        payload: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> HmisAdapterResult:
        del context
        translated = self.translate_payload(action_type, payload)
        try:
            if self.transport is not None:
                response = dict(self.transport(action_type, translated, self.build_auth_headers()))
            else:
                response = dict(self.fixture_responses.get(action_type) or {})
        except Exception as exc:  # pragma: no cover - defensive normalization
            return HmisAdapterResult.failure(
                action_type=action_type,
                adapter_name=self.name,
                summary=f"vendor API execution failed for {action_type}",
                errors=(str(exc),),
                retryable=True,
                normalized_payload=translated,
            )

        if not response:
            return HmisAdapterResult.failure(
                action_type=action_type,
                adapter_name=self.name,
                summary=f"vendor API fixture missing for {action_type}",
                errors=(f"missing fixture response for {action_type}",),
                normalized_payload=translated,
            )

        if response.get("ok", True) is False:
            return HmisAdapterResult.failure(
                action_type=action_type,
                adapter_name=self.name,
                summary=str(response.get("summary") or f"vendor API rejected {action_type}"),
                errors=tuple(str(item) for item in response.get("errors") or ["vendor API rejected request"]),
                retryable=bool(response.get("retryable")),
                reconciliation_required=bool(response.get("reconciliation_required")),
                normalized_payload=translated,
                warnings=tuple(str(item) for item in response.get("warnings") or []),
            )

        external_refs = {
            key: str(value)
            for key, value in dict(response.get("external_refs") or {}).items()
            if str(key).strip() and value is not None
        }
        normalized_payload = dict(response.get("normalized_payload") or translated)
        return HmisAdapterResult.success(
            action_type=action_type,
            adapter_name=self.name,
            summary=str(response.get("summary") or f"vendor API accepted {action_type}"),
            external_refs=external_refs,
            normalized_payload=normalized_payload,
            warnings=tuple(str(item) for item in response.get("warnings") or []),
        )


__all__ = ["VendorApiHmisAdapter"]
