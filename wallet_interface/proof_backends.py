"""External proof backend adapters for the 211-AI wallet interface."""

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any, Callable, Dict
from urllib import request as urllib_request

from ._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet.models import ProofReceipt  # noqa: E402
from ipfs_datasets_py.wallet.proofs import verifier_digest  # noqa: E402


def _default_request_json(
    method: str,
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout_seconds: float,
) -> Dict[str, Any]:
    request_headers = {"content-type": "application/json", **headers}
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("Proof verifier response must be a JSON object")
    return data


class HttpLocationRegionProofBackend:
    """HTTP-backed location-region proof adapter.

    This is a narrow production adapter for an external verifier service. The
    service contract is intentionally small:

    - POST `{base_url}{prove_path}` with prove inputs, returning a serialized
      `ProofReceipt`
    - POST `{base_url}{verify_path}` with `{"receipt": ...}`, returning
      `{"verified": true|false}`
    """

    mode = "production"
    is_simulated = False

    def __init__(
        self,
        *,
        base_url: str,
        verifier_id: str,
        proof_system: str,
        circuit_id: str | None = None,
        prove_path: str = "/prove/location-region",
        verify_path: str = "/verify",
        health_path: str = "/health",
        bearer_token: str | None = None,
        extra_headers: Dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
        request_json: Callable[[str, str, Dict[str, Any], Dict[str, str], float], Dict[str, Any]] | None = None,
    ) -> None:
        resolved_base_url = str(base_url or "").strip().rstrip("/")
        if not resolved_base_url:
            raise ValueError("HTTP proof backend requires a base_url")
        self.base_url = resolved_base_url
        self.verifier_id = str(verifier_id or "").strip()
        self.proof_system = str(proof_system or "").strip()
        if not self.verifier_id or not self.proof_system:
            raise ValueError("HTTP proof backend requires verifier_id and proof_system")
        self.circuit_id = str(circuit_id or "").strip() or None
        self.prove_path = self._normalize_path(prove_path)
        self.verify_path = self._normalize_path(verify_path)
        self.health_path = self._normalize_path(health_path)
        self.timeout_seconds = float(timeout_seconds)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.extra_headers = dict(extra_headers or {})
        if bearer_token:
            self.extra_headers["authorization"] = f"Bearer {bearer_token}"
        self.request_json = request_json or _default_request_json

    @staticmethod
    def _normalize_path(path: str) -> str:
        value = str(path or "").strip()
        if not value:
            raise ValueError("proof backend path must not be empty")
        return value if value.startswith("/") else f"/{value}"

    def prove_location_region(
        self,
        *,
        wallet_id: str,
        statement: Dict[str, Any],
        public_inputs: Dict[str, Any],
        witness: Dict[str, Any],
        witness_record_ids: list[str],
    ) -> ProofReceipt:
        payload = {
            "wallet_id": wallet_id,
            "proof_type": "location_region",
            "statement": statement,
            "public_inputs": public_inputs,
            "witness": witness,
            "witness_record_ids": list(witness_record_ids),
            "verifier_id": self.verifier_id,
            "proof_system": self.proof_system,
            "circuit_id": self.circuit_id,
        }
        response = self.request_json(
            "POST",
            f"{self.base_url}{self.prove_path}",
            payload,
            dict(self.extra_headers),
            self.timeout_seconds,
        )
        return self._receipt_from_response(response, wallet_id=wallet_id)

    def verify(self, receipt: ProofReceipt) -> bool:
        response = self.request_json(
            "POST",
            f"{self.base_url}{self.verify_path}",
            {"receipt": receipt.to_dict()},
            dict(self.extra_headers),
            self.timeout_seconds,
        )
        return bool(response.get("verified"))

    def healthcheck(self) -> Dict[str, Any]:
        response = self.request_json(
            "POST",
            f"{self.base_url}{self.health_path}",
            {"verifier_id": self.verifier_id, "proof_system": self.proof_system},
            dict(self.extra_headers),
            self.timeout_seconds,
        )
        return {
            "ok": bool(response.get("ok", True)),
            "status": str(response.get("status") or "ok"),
            "details": response,
        }

    def _receipt_from_response(self, payload: Dict[str, Any], *, wallet_id: str) -> ProofReceipt:
        if "receipt" in payload and isinstance(payload["receipt"], dict):
            payload = payload["receipt"]
        allowed = {field.name for field in fields(ProofReceipt)}
        normalized = {key: value for key, value in payload.items() if key in allowed}
        normalized.setdefault("wallet_id", wallet_id)
        normalized.setdefault("proof_type", "location_region")
        normalized.setdefault("verifier_id", self.verifier_id)
        normalized.setdefault("proof_system", self.proof_system)
        normalized.setdefault("circuit_id", self.circuit_id)
        normalized.setdefault("is_simulated", False)
        normalized.setdefault(
            "verifier_digest",
            verifier_digest(
                str(normalized["verifier_id"]),
                str(normalized["proof_system"]),
            ),
        )
        return ProofReceipt(**normalized)
