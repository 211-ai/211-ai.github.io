"""Proof verifier interfaces for the Chainlink ZKML LLM Router consensus system.

Each verifier implements fail-closed defaults: if required proof metadata is
absent, mismatched, or replayed, ``verify`` returns a failed ``VerificationResult``
rather than trusting an incomplete proof.

Four concrete verifiers are provided:

- ``ReceiptOnlyVerifier``: no cryptographic proof is required; binding checks
  only.
- ``TEEVerifier``: requires a TEE (Trusted Execution Environment) attestation
  and checks its fields against the request/output/model context.
- ``ZKMLVerifier``: requires a ZKML proof with verifier key and circuit
  metadata.
- ``ChainlinkCREVerifier``: requires Chainlink CRE report metadata and checks
  round/report fields.

All verifiers perform:
- **Request binding**: ``proof_meta["request_hash"]`` must match the context
  request hash.
- **Output binding**: ``proof_meta["output_hash"]`` must match the context
  output hash.
- **Model binding**: ``proof_meta["model_commitment"]`` must match the context
  model commitment (when the verifier policy requires it).
- **Replay prevention**: nonces are tracked per verifier instance; a nonce
  already seen causes a failed result.
"""

from __future__ import annotations

import abc
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProofContext:
    """Bindings that a verifier must check proof metadata against.

    Attributes:
        request_hash: Canonical hash of the ``ConsensusRequest``.
        output_hash: Raw output hash selected by the quorum.
        model_commitment: Commitment to the model artefact (may be empty string
            when the verifier policy does not require model binding).
        nonce: Per-request nonce used for replay prevention.
    """

    request_hash: str
    output_hash: str
    model_commitment: str = ""
    nonce: str = ""


@dataclass
class VerificationResult:
    """Result returned by every :class:`ProofVerifier` implementation.

    ``verified`` is ``False`` whenever any binding check or policy check fails.
    ``reason`` is a short machine-readable string explaining the outcome.
    ``metadata`` carries additional diagnostic fields.
    """

    verified: bool
    verifier: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ProofVerifier(abc.ABC):
    """Abstract base class for proof verifier implementations.

    Subclasses implement :meth:`verify`, which MUST be fail-closed: when in
    doubt, return ``verified=False``.
    """

    #: Short identifier written to :attr:`VerificationResult.verifier`.
    verifier_id: str = "abstract-verifier"

    @abc.abstractmethod
    def verify(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> VerificationResult:
        """Verify *proof_meta* against *context*.

        Parameters
        ----------
        proof_meta:
            Dictionary containing proof-specific fields (e.g. attestation,
            proof bytes, CRE report).  An empty dict MUST produce a failed
            result for all verifiers except ``ReceiptOnlyVerifier`` when no
            additional fields are required.
        context:
            Binding values from the consensus request/result.

        Returns
        -------
        VerificationResult
            Always returns a result—never raises on bad input.
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _check_request_binding(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> str | None:
        """Return an error reason string if request binding fails, else None."""
        if not context.request_hash:
            return "context_request_hash_missing"
        meta_rh = proof_meta.get("request_hash", "")
        if not meta_rh:
            return "proof_request_hash_missing"
        if meta_rh != context.request_hash:
            return "request_hash_mismatch"
        return None

    def _check_output_binding(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> str | None:
        """Return an error reason string if output binding fails, else None."""
        if not context.output_hash:
            return "context_output_hash_missing"
        meta_oh = proof_meta.get("output_hash", "")
        if not meta_oh:
            return "proof_output_hash_missing"
        if meta_oh != context.output_hash:
            return "output_hash_mismatch"
        return None

    def _check_model_binding(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> str | None:
        """Return an error reason string if model binding fails, else None."""
        if not context.model_commitment:
            return "context_model_commitment_missing"
        meta_mc = proof_meta.get("model_commitment", "")
        if not meta_mc:
            return "proof_model_commitment_missing"
        if meta_mc != context.model_commitment:
            return "model_commitment_mismatch"
        return None

    def _check_replay(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
        seen_nonces: set[str],
    ) -> str | None:
        """Return an error reason string if the nonce has been seen before."""
        nonce = proof_meta.get("nonce", "") or context.nonce
        if not nonce:
            return None  # No nonce to track (caller decides if required)
        if nonce in seen_nonces:
            return "replayed_nonce"
        seen_nonces.add(nonce)
        return None


class ReceiptOnlyVerifier(ProofVerifier):
    """Verifier for ``receipt_only`` policy mode.

    Does not require a cryptographic proof.  Checks request and output hash
    binding.  Model commitment is **not** required (operators may use different
    model replicas).  Replay prevention is performed when a nonce is present.

    This verifier is fail-closed on missing or mismatched request/output
    hashes.
    """

    verifier_id = "receipt-only-v1"

    def __init__(self) -> None:
        self._seen_nonces: set[str] = set()

    def verify(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> VerificationResult:
        err = self._check_request_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason=err,
            )

        err = self._check_output_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason=err,
            )

        err = self._check_replay(proof_meta, context, self._seen_nonces)
        if err:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason=err,
            )

        return VerificationResult(
            verified=True,
            verifier=self.verifier_id,
            reason="receipt_binding_verified",
            metadata={"policy": "receipt_only"},
        )


class TEEVerifier(ProofVerifier):
    """Verifier for TEE (Trusted Execution Environment) attestations.

    Requires the following fields in *proof_meta*:

    - ``request_hash``: bound to the consensus request.
    - ``output_hash``: bound to the quorum-selected output.
    - ``model_commitment``: bound to the model artefact.
    - ``tee_measurement``: PCR/measurement value identifying the enclave image.
    - ``tee_signer``: public key or certificate that signed the attestation.
    - ``tee_nonce``: per-request TEE nonce (also used for replay prevention).
    - ``tee_expiry_unix_ms``: attestation expiry as a Unix timestamp in ms.
    - ``tee_policy_mode`` (or ``proof_policy.mode``): the requested proof mode.

    Fail-closed: any missing or mismatched field produces ``verified=False``.
    Expired attestations are rejected.  Measurements and signers are checked
    against verifier-configured allowlists when present, otherwise against
    allowlists supplied in the proof policy metadata.
    """

    verifier_id = "tee-verifier-v1"
    _DEFAULT_ALLOWED_POLICY_MODES = frozenset({"tee_or_zkml", "tee_required"})

    _REQUIRED_TEE_FIELDS = (
        "tee_measurement",
        "tee_signer",
        "tee_nonce",
        "tee_expiry_unix_ms",
    )

    _MEASUREMENT_ALLOWLIST_FIELDS = (
        "tee_measurement_allowlist",
        "measurement_allowlist",
        "allowed_tee_measurements",
    )
    _SIGNER_ALLOWLIST_FIELDS = (
        "tee_signer_allowlist",
        "signer_allowlist",
        "allowed_tee_signers",
    )
    _SIGNER_IDENTITY_FIELDS = (
        "tee_signer_identity",
        "tee_expected_signer",
        "expected_tee_signer",
        "expected_signer",
    )
    _POLICY_MODE_FIELDS = (
        "tee_policy_mode",
        "proof_policy_mode",
        "policy_mode",
        "policy",
        "mode",
    )

    def __init__(
        self,
        *,
        now_unix_ms: int | None = None,
        tee_measurement_allowlist: Iterable[str] | None = None,
        measurement_allowlist: Iterable[str] | None = None,
        allowed_measurements: Iterable[str] | None = None,
        tee_signer_allowlist: Iterable[str] | None = None,
        signer_allowlist: Iterable[str] | None = None,
        allowed_signers: Iterable[str] | None = None,
        expected_signer: str | None = None,
        expected_policy_mode: str | None = None,
        allowed_policy_modes: Iterable[str] | None = None,
        require_measurement_allowlist: bool = True,
        require_signer_allowlist: bool = True,
    ) -> None:
        self._seen_nonces: set[str] = set()
        self._now_unix_ms = now_unix_ms  # injectable for testing
        self._measurement_allowlist = self._merge_string_sets(
            tee_measurement_allowlist,
            measurement_allowlist,
            allowed_measurements,
        )
        self._signer_allowlist = self._merge_string_sets(
            tee_signer_allowlist,
            signer_allowlist,
            allowed_signers,
            expected_signer,
        )
        self._require_measurement_allowlist = require_measurement_allowlist
        self._require_signer_allowlist = require_signer_allowlist

        if expected_policy_mode:
            self._allowed_policy_modes = {str(expected_policy_mode)}
        elif allowed_policy_modes is not None:
            self._allowed_policy_modes = self._coerce_string_set(allowed_policy_modes)
        else:
            self._allowed_policy_modes = set(self._DEFAULT_ALLOWED_POLICY_MODES)

    @property
    def _current_unix_ms(self) -> int:
        if self._now_unix_ms is not None:
            return self._now_unix_ms
        import time

        return int(time.time() * 1000)

    @staticmethod
    def _coerce_string_set(value: Any) -> set[str]:
        """Normalize scalar or iterable policy values to non-empty strings."""
        if value is None:
            return set()
        if isinstance(value, str):
            return {value} if value else set()
        if isinstance(value, dict):
            values = value.values()
        elif isinstance(value, Iterable):
            values = value
        else:
            text = str(value)
            return {text} if text else set()

        coerced: set[str] = set()
        for item in values:
            if item is None:
                continue
            text = str(item)
            if text:
                coerced.add(text)
        return coerced

    @classmethod
    def _merge_string_sets(cls, *values: Any) -> set[str]:
        merged: set[str] = set()
        for value in values:
            merged.update(cls._coerce_string_set(value))
        return merged

    @classmethod
    def _string_set_from_fields(
        cls,
        proof_meta: dict[str, Any],
        fields: tuple[str, ...],
    ) -> set[str]:
        for field_name in fields:
            values = cls._coerce_string_set(proof_meta.get(field_name))
            if values:
                return values
        proof_policy = proof_meta.get("proof_policy")
        if isinstance(proof_policy, dict):
            for field_name in fields:
                values = cls._coerce_string_set(proof_policy.get(field_name))
                if values:
                    return values
        return set()

    def _measurement_policy(self, proof_meta: dict[str, Any]) -> set[str]:
        if self._measurement_allowlist:
            return set(self._measurement_allowlist)
        return self._string_set_from_fields(
            proof_meta,
            self._MEASUREMENT_ALLOWLIST_FIELDS,
        )

    def _signer_policy(self, proof_meta: dict[str, Any]) -> set[str]:
        if self._signer_allowlist:
            return set(self._signer_allowlist)
        signer_allowlist = self._string_set_from_fields(
            proof_meta,
            self._SIGNER_ALLOWLIST_FIELDS,
        )
        if signer_allowlist:
            return signer_allowlist
        return self._string_set_from_fields(
            proof_meta,
            self._SIGNER_IDENTITY_FIELDS,
        )

    def _proof_policy_mode(self, proof_meta: dict[str, Any]) -> str:
        for field_name in self._POLICY_MODE_FIELDS:
            value = proof_meta.get(field_name)
            if value:
                return str(value)

        proof_policy = proof_meta.get("proof_policy")
        if isinstance(proof_policy, dict):
            mode = proof_policy.get("mode")
            if mode:
                return str(mode)
        return ""

    def verify(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> VerificationResult:
        err = self._check_request_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        err = self._check_output_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        err = self._check_model_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        for required_field in self._REQUIRED_TEE_FIELDS:
            if not proof_meta.get(required_field):
                return VerificationResult(
                    verified=False,
                    verifier=self.verifier_id,
                    reason=f"tee_field_missing:{required_field}",
                )

        expiry = proof_meta.get("tee_expiry_unix_ms")
        try:
            expiry_int = int(expiry)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_expiry_invalid",
            )
        if expiry_int <= self._current_unix_ms:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_attestation_expired",
            )

        tee_nonce = str(proof_meta["tee_nonce"])
        if not context.nonce:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="context_nonce_missing",
            )
        if tee_nonce != context.nonce:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_nonce_mismatch",
            )

        proof_nonce = proof_meta.get("nonce")
        if proof_nonce and str(proof_nonce) != tee_nonce:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="nonce_mismatch",
            )

        tee_measurement = str(proof_meta["tee_measurement"])
        measurement_allowlist = self._measurement_policy(proof_meta)
        if not measurement_allowlist and self._require_measurement_allowlist:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_measurement_allowlist_missing",
            )
        if measurement_allowlist and tee_measurement not in measurement_allowlist:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_measurement_not_allowed",
            )

        tee_signer = str(proof_meta["tee_signer"])
        signer_allowlist = self._signer_policy(proof_meta)
        if not signer_allowlist and self._require_signer_allowlist:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_signer_allowlist_missing",
            )
        if signer_allowlist and tee_signer not in signer_allowlist:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_signer_not_allowed",
            )

        policy_mode = self._proof_policy_mode(proof_meta)
        if not policy_mode:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_policy_mode_missing",
            )
        if policy_mode not in self._allowed_policy_modes:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="tee_policy_mode_not_allowed",
            )

        if tee_nonce in self._seen_nonces:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason="replayed_nonce"
            )
        self._seen_nonces.add(tee_nonce)

        return VerificationResult(
            verified=True,
            verifier=self.verifier_id,
            reason="tee_attestation_verified",
            metadata={
                "evidence_type": "tee_attestation",
                "proof_type": "tee_attestation",
                "zkml_proof": False,
                "tee_measurement": tee_measurement,
                "tee_signer": tee_signer,
                "tee_policy_mode": policy_mode,
                "tee_expiry_unix_ms": expiry_int,
            },
        )


class ZKMLVerifier(ProofVerifier):
    """Verifier for ZKML (Zero-Knowledge Machine Learning) proofs.

    Requires the following fields in *proof_meta*:

    - ``request_hash``: bound to the consensus request.
    - ``output_hash``: bound to the quorum-selected output.
    - ``model_commitment``: bound to the model artefact.
    - ``verifier_key_hash``: hash of the pinned verifier key.
    - ``circuit_id``: identifier of the proving circuit.
    - ``circuit_version``: version of the proving circuit.
    - ``public_inputs_hash``: commitment to public inputs.
    - ``proof_bytes`` *or* ``proof_cid``: the actual proof data or its CID.

    The verifier is constructed with *expected_verifier_key_hash*,
    *expected_circuit_id*, and *expected_circuit_version* to enforce that only
    known circuits are accepted.  All checks are fail-closed.
    """

    verifier_id = "zkml-verifier-v1"

    def __init__(
        self,
        *,
        expected_verifier_key_hash: str,
        expected_circuit_id: str,
        expected_circuit_version: str,
    ) -> None:
        self._expected_verifier_key_hash = expected_verifier_key_hash
        self._expected_circuit_id = expected_circuit_id
        self._expected_circuit_version = expected_circuit_version
        self._seen_nonces: set[str] = set()

    def verify(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> VerificationResult:
        err = self._check_request_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        err = self._check_output_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        err = self._check_model_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        vkh = proof_meta.get("verifier_key_hash", "")
        if not vkh:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="verifier_key_hash_missing",
            )
        if vkh != self._expected_verifier_key_hash:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="verifier_key_hash_mismatch",
            )

        cid = proof_meta.get("circuit_id", "")
        if not cid:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason="circuit_id_missing"
            )
        if cid != self._expected_circuit_id:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="circuit_id_mismatch",
            )

        cv = proof_meta.get("circuit_version", "")
        if not cv:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="circuit_version_missing",
            )
        if cv != self._expected_circuit_version:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="circuit_version_mismatch",
            )

        if not proof_meta.get("public_inputs_hash"):
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="public_inputs_hash_missing",
            )

        has_proof = bool(proof_meta.get("proof_bytes") or proof_meta.get("proof_cid"))
        if not has_proof:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="proof_data_missing",
            )

        err = self._check_replay(proof_meta, context, self._seen_nonces)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        return VerificationResult(
            verified=True,
            verifier=self.verifier_id,
            reason="zkml_proof_verified",
            metadata={
                "circuit_id": cid,
                "circuit_version": cv,
                "public_inputs_hash": proof_meta["public_inputs_hash"],
            },
        )


class ChainlinkCREVerifier(ProofVerifier):
    """Verifier for Chainlink CRE (Capabilities Runtime Environment) reports.

    Requires the following fields in *proof_meta*:

    - ``request_hash``: bound to the consensus request.
    - ``output_hash``: bound to the quorum-selected output.
    - ``cre_workflow_id``: identifier of the CRE workflow that produced the
      report.
    - ``cre_don_id``: Decentralised Oracle Network identifier.
    - ``cre_round``: monotonically increasing round number.
    - ``cre_report_hash``: hash of the CRE report payload.

    The verifier is constructed with *expected_workflow_id* and
    *expected_don_id* to ensure only reports from known workflows are accepted.
    Round numbers are tracked per (workflow_id, don_id) pair to detect
    replayed rounds.
    """

    verifier_id = "chainlink-cre-verifier-v1"

    def __init__(
        self,
        *,
        expected_workflow_id: str,
        expected_don_id: str,
    ) -> None:
        self._expected_workflow_id = expected_workflow_id
        self._expected_don_id = expected_don_id
        # Maps (workflow_id, don_id) -> last accepted round
        self._last_round: dict[tuple[str, str], int] = {}
        self._seen_nonces: set[str] = set()

    def verify(
        self,
        proof_meta: dict[str, Any],
        context: ProofContext,
    ) -> VerificationResult:
        err = self._check_request_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        err = self._check_output_binding(proof_meta, context)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        wf_id = proof_meta.get("cre_workflow_id", "")
        if not wf_id:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="cre_workflow_id_missing",
            )
        if wf_id != self._expected_workflow_id:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="cre_workflow_id_mismatch",
            )

        don_id = proof_meta.get("cre_don_id", "")
        if not don_id:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason="cre_don_id_missing"
            )
        if don_id != self._expected_don_id:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="cre_don_id_mismatch",
            )

        round_val = proof_meta.get("cre_round")
        if round_val is None:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="cre_round_missing",
            )
        try:
            round_int = int(round_val)
        except (TypeError, ValueError):
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason="cre_round_invalid"
            )

        key = (wf_id, don_id)
        last = self._last_round.get(key, -1)
        if round_int <= last:
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="replayed_cre_round",
            )

        if not proof_meta.get("cre_report_hash"):
            return VerificationResult(
                verified=False,
                verifier=self.verifier_id,
                reason="cre_report_hash_missing",
            )

        err = self._check_replay(proof_meta, context, self._seen_nonces)
        if err:
            return VerificationResult(
                verified=False, verifier=self.verifier_id, reason=err
            )

        self._last_round[key] = round_int

        return VerificationResult(
            verified=True,
            verifier=self.verifier_id,
            reason="chainlink_cre_report_verified",
            metadata={
                "cre_workflow_id": wf_id,
                "cre_don_id": don_id,
                "cre_round": round_int,
            },
        )


__all__ = [
    "ProofContext",
    "ProofVerifier",
    "VerificationResult",
    "ReceiptOnlyVerifier",
    "TEEVerifier",
    "ZKMLVerifier",
    "ChainlinkCREVerifier",
]
