"""Compatibility re-exports for World ID / IDKit helpers (WALPROC-G130 / WALPROC-G710).

This module is a thin 211-AI wrapper over the reusable Worldcoin package in
``ipfs_datasets_py.processors.wallets.worldcoin``.  It preserves the documented
import paths and exception identities used by 211-AI callers for one deprecation
window.

Aliases remain supported through package version ``0.2.0`` (inclusive) and are
scheduled for removal starting at ``0.3.0``.  The constants below make that
cutover window machine-readable without moving protocol ownership back into
this wrapper.

Ownership boundary
------------------
* **Reusable package** (``ipfs_datasets_py``): config, secrets descriptors,
  Keccak/hash-to-field, EIP-191 RP signing, IDKit parsing, Developer Portal
  verification, redaction, bindings, challenges, proofs, and World Chain.
* **This wrapper**: compatibility imports and ``__all__`` only — no crypto,
  hashing, HTTP, endpoint literals, secret resolution, proof parsing,
  normalization, redaction, binding, replay, or proof implementation.
* **211-AI application layer** (``app_service`` / routes / ops): actor and
  provider-staff policy, wallet persistence, audit naming, readiness probes that
  *delegate* to the package via these re-exports, and browser-safe response
  shaping.
"""

from __future__ import annotations

from ._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.processors.wallets.worldcoin import (  # noqa: E402
    DEFAULT_WORLD_ID_ACTION,
    DEFAULT_WORLD_ID_CREDENTIAL_POLICY,
    DEFAULT_WORLD_ID_HTTP_TIMEOUT_SECONDS,
    DEFAULT_WORLD_ID_SIGNATURE_TTL_SECONDS,
    DEFAULT_WORLD_ID_VERIFY_BASE_URL,
    SUPPORTED_WORLD_ID_ENVIRONMENTS,
    WorldIdConfig,
    WorldIdConfigError,
    WorldIdCredentialResponse,
    WorldIdIdkitResult,
    WorldIdPayloadError,
    WorldIdRequestJson,
    WorldIdRpSignature,
    WorldIdSecretConfig,
    WorldIdSignatureError,
    WorldIdVerificationError,
    WorldIdVerificationResult,
    compute_rp_signature_message,
    eip191_digest,
    hash_to_field,
    hash_to_field_hex,
    load_world_id_config,
    normalize_idkit_response,
    normalize_world_id_idkit_response,
    normalize_world_id_verification_response,
    redact_world_id_payload,
    sign_world_id_request,
    sign_world_id_request_from_config,
    verify_world_id_proof,
    verify_world_id_proof_from_config,
    world_id_keccak256,
)

# Inclusive compatibility version and first version where removal is allowed.
WRAPPER_ALIAS_COMPATIBILITY_PACKAGE_VERSION = "0.2.0"
WRAPPER_ALIAS_EXPIRY_PACKAGE_VERSION = "0.3.0"

__all__ = [
    "DEFAULT_WORLD_ID_ACTION",
    "DEFAULT_WORLD_ID_CREDENTIAL_POLICY",
    "DEFAULT_WORLD_ID_HTTP_TIMEOUT_SECONDS",
    "DEFAULT_WORLD_ID_SIGNATURE_TTL_SECONDS",
    "DEFAULT_WORLD_ID_VERIFY_BASE_URL",
    "SUPPORTED_WORLD_ID_ENVIRONMENTS",
    "WRAPPER_ALIAS_COMPATIBILITY_PACKAGE_VERSION",
    "WRAPPER_ALIAS_EXPIRY_PACKAGE_VERSION",
    "WorldIdConfig",
    "WorldIdConfigError",
    "WorldIdCredentialResponse",
    "WorldIdIdkitResult",
    "WorldIdPayloadError",
    "WorldIdRequestJson",
    "WorldIdRpSignature",
    "WorldIdSecretConfig",
    "WorldIdSignatureError",
    "WorldIdVerificationError",
    "WorldIdVerificationResult",
    "compute_rp_signature_message",
    "eip191_digest",
    "hash_to_field",
    "hash_to_field_hex",
    "load_world_id_config",
    "normalize_idkit_response",
    "normalize_world_id_idkit_response",
    "normalize_world_id_verification_response",
    "redact_world_id_payload",
    "sign_world_id_request",
    "sign_world_id_request_from_config",
    "verify_world_id_proof",
    "verify_world_id_proof_from_config",
    "world_id_keccak256",
]
