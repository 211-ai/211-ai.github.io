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


_PRIVATE_WITNESS_KEYS = {
    "address",
    "lat",
    "latitude",
    "lng",
    "lon",
    "longitude",
    "nonce",
    "precise_location",
    "target_lat",
    "target_lon",
    "witness",
}
_SAFE_WITNESS_KEY_EXCEPTIONS = {"witness_commitment", "witness_record_ids"}


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

    - POST `{base_url}{prove_path}` with location-region prove inputs, returning a serialized
      `ProofReceipt`
    - POST `{base_url}{distance_prove_path}` with location-distance prove inputs, returning a serialized
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
        distance_prove_path: str = "/prove/location-distance",
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
        self.distance_prove_path = self._normalize_path(distance_prove_path)
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
        return self._receipt_from_response(response, wallet_id=wallet_id, proof_type="location_region")

    def prove_location_distance(
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
            "proof_type": "location_distance",
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
            f"{self.base_url}{self.distance_prove_path}",
            payload,
            dict(self.extra_headers),
            self.timeout_seconds,
        )
        return self._receipt_from_response(response, wallet_id=wallet_id, proof_type="location_distance")

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

    def validate_contract(
        self,
        *,
        wallet_id: str = "wallet-contract-test",
        witness_record_id: str = "record-contract-test",
        region_id: str = "contract-test-region",
    ) -> Dict[str, Any]:
        """Run a non-user health/prove/verify contract check against the verifier."""
        checks: list[Dict[str, Any]] = []

        def add_check(name: str, ok: bool, summary: str, details: Dict[str, Any] | None = None) -> None:
            checks.append(
                {
                    "name": name,
                    "status": "ok" if ok else "error",
                    "summary": summary,
                    "details": details or {},
                }
            )

        try:
            health = self.healthcheck()
            add_check(
                "health",
                bool(health.get("ok")) and str(health.get("status")) not in {"down", "error", "unavailable"},
                f"verifier health status is {health.get('status')}",
                health,
            )
        except Exception as exc:
            add_check("health", False, f"verifier health check failed: {exc}", {"error": str(exc)})
            return self._contract_result(checks)

        statement = {
            "claim": "location_in_region",
            "region_id": region_id,
            "witness_commitment": "contract-test-witness-commitment",
        }
        public_inputs = {
            "claim": "location_in_region",
            "region_id": region_id,
            "region_policy_hash": "contract-test-region-policy-hash",
        }
        witness = {
            "lat": 45.5152,
            "lon": -122.6784,
            "nonce": "wallet-contract-test-nonce",
            "address": "123 Contract Test St",
        }
        sensitive_values = {str(value) for value in witness.values()}

        try:
            receipt = self.prove_location_region(
                wallet_id=wallet_id,
                statement=statement,
                public_inputs=public_inputs,
                witness=witness,
                witness_record_ids=[witness_record_id],
            )
            receipt_dict = receipt.to_dict()
            add_check(
                "prove",
                receipt.proof_type == "location_region"
                and receipt.wallet_id == wallet_id
                and receipt.verifier_id == self.verifier_id
                and receipt.proof_system == self.proof_system
                and receipt.is_simulated is False
                and receipt.verification_status == "verified",
                "verifier returned a non-simulated verified location_region receipt",
                self._receipt_summary(receipt),
            )
            add_check(
                "public_input_safety",
                not self._contains_private_witness_data(receipt_dict, sensitive_values),
                "receipt and public inputs do not expose synthetic witness values",
                {"public_input_keys": sorted(receipt.public_inputs.keys())},
            )
        except Exception as exc:
            add_check("prove", False, f"verifier prove contract failed: {exc}", {"error": str(exc)})
            return self._contract_result(checks)

        try:
            verified = self.verify(receipt)
            add_check(
                "verify",
                verified,
                "verifier accepted its returned proof receipt",
                {"verified": verified},
            )
        except Exception as exc:
            add_check("verify", False, f"verifier verify contract failed: {exc}", {"error": str(exc)})

        return self._contract_result(checks, receipt=receipt)

    def validate_distance_contract(
        self,
        *,
        wallet_id: str = "wallet-contract-test",
        witness_record_id: str = "record-contract-test",
        target_id: str = "contract-test-service",
    ) -> Dict[str, Any]:
        """Run a non-user location-distance contract check against the verifier."""
        checks: list[Dict[str, Any]] = []

        def add_check(name: str, ok: bool, summary: str, details: Dict[str, Any] | None = None) -> None:
            checks.append(
                {
                    "name": name,
                    "status": "ok" if ok else "error",
                    "summary": summary,
                    "details": details or {},
                }
            )

        try:
            health = self.healthcheck()
            add_check(
                "health",
                bool(health.get("ok")) and str(health.get("status")) not in {"down", "error", "unavailable"},
                f"verifier health status is {health.get('status')}",
                health,
            )
        except Exception as exc:
            add_check("health", False, f"verifier health check failed: {exc}", {"error": str(exc)})
            return self._contract_result(checks)

        statement = {
            "claim": "location_within_distance",
            "target_id": target_id,
            "max_distance_km": 5.0,
            "target_policy_hash": "contract-test-target-policy-hash",
            "witness_commitment": "contract-test-witness-commitment",
        }
        public_inputs = {
            "claim": "location_within_distance",
            "target_id": target_id,
            "max_distance_km": 5.0,
            "target_policy_hash": "contract-test-target-policy-hash",
        }
        witness = {
            "lat": 45.5152,
            "lon": -122.6784,
            "target_lat": 45.52,
            "target_lon": -122.68,
            "max_distance_km": 5.0,
            "nonce": "wallet-contract-test-nonce",
            "address": "123 Contract Test St",
        }
        sensitive_values = {
            str(witness["lat"]),
            str(witness["lon"]),
            str(witness["target_lat"]),
            str(witness["target_lon"]),
            str(witness["nonce"]),
            str(witness["address"]),
        }

        try:
            receipt = self.prove_location_distance(
                wallet_id=wallet_id,
                statement=statement,
                public_inputs=public_inputs,
                witness=witness,
                witness_record_ids=[witness_record_id],
            )
            receipt_dict = receipt.to_dict()
            add_check(
                "prove",
                receipt.proof_type == "location_distance"
                and receipt.wallet_id == wallet_id
                and receipt.verifier_id == self.verifier_id
                and receipt.proof_system == self.proof_system
                and receipt.is_simulated is False
                and receipt.verification_status == "verified",
                "verifier returned a non-simulated verified location_distance receipt",
                self._receipt_summary(receipt),
            )
            add_check(
                "public_input_safety",
                not self._contains_private_witness_data(receipt_dict, sensitive_values),
                "receipt and public inputs do not expose synthetic wallet witness values",
                {"public_input_keys": sorted(receipt.public_inputs.keys())},
            )
        except Exception as exc:
            add_check("prove", False, f"verifier distance prove contract failed: {exc}", {"error": str(exc)})
            return self._contract_result(checks)

        try:
            verified = self.verify(receipt)
            add_check(
                "verify",
                verified,
                "verifier accepted its returned proof receipt",
                {"verified": verified},
            )
        except Exception as exc:
            add_check("verify", False, f"verifier verify contract failed: {exc}", {"error": str(exc)})

        return self._contract_result(checks, receipt=receipt)

    def _receipt_from_response(
        self,
        payload: Dict[str, Any],
        *,
        wallet_id: str,
        proof_type: str,
    ) -> ProofReceipt:
        if "receipt" in payload and isinstance(payload["receipt"], dict):
            payload = payload["receipt"]
        allowed = {field.name for field in fields(ProofReceipt)}
        normalized = {key: value for key, value in payload.items() if key in allowed}
        normalized.setdefault("wallet_id", wallet_id)
        normalized.setdefault("proof_type", proof_type)
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

    @classmethod
    def _contains_private_witness_data(cls, value: Any, sensitive_values: set[str]) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized_key = str(key).lower()
                if normalized_key in _PRIVATE_WITNESS_KEYS and normalized_key not in _SAFE_WITNESS_KEY_EXCEPTIONS:
                    return True
                if cls._contains_private_witness_data(item, sensitive_values):
                    return True
            return False
        if isinstance(value, list):
            return any(cls._contains_private_witness_data(item, sensitive_values) for item in value)
        if isinstance(value, (str, int, float)):
            rendered = str(value)
            return any(secret and secret in rendered for secret in sensitive_values)
        return False

    @staticmethod
    def _receipt_summary(receipt: ProofReceipt) -> Dict[str, Any]:
        return {
            "proof_id": receipt.proof_id,
            "proof_type": receipt.proof_type,
            "wallet_id": receipt.wallet_id,
            "verifier_id": receipt.verifier_id,
            "proof_system": receipt.proof_system,
            "circuit_id": receipt.circuit_id,
            "is_simulated": receipt.is_simulated,
            "verification_status": receipt.verification_status,
            "proof_artifact_ref": receipt.proof_artifact_ref,
        }

    def _contract_result(self, checks: list[Dict[str, Any]], receipt: ProofReceipt | None = None) -> Dict[str, Any]:
        ok = all(check["status"] == "ok" for check in checks)
        return {
            "ok": ok,
            "status": "ok" if ok else "error",
            "backend": self.__class__.__name__,
            "base_url": self.base_url,
            "verifier_id": self.verifier_id,
            "proof_system": self.proof_system,
            "circuit_id": self.circuit_id,
            "checks": checks,
            "receipt": self._receipt_summary(receipt) if receipt else None,
        }
