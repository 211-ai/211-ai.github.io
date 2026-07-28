# Wallet Processor Migration Ownership Map

- Goal: `WALPROC-G010`
- Task: `WALPROC-002`
- Generated: `2026-07-28T22:15:21Z`
- Freeze attempt: `2`
- Freeze status: `frozen`
- Schema: `wallet_processor_migration/ownership-map@1`

This map freezes **move / retain / deprecate / create** decisions and **one owner per symbol** before production code moves. Unresolved ownership is recorded as a **blocker**, not guessed.

Companion artifacts:

- [`source-inventory.json`](./source-inventory.json)
- [`import-map.json`](./import-map.json)

## 1. Domain ownership summary

| Domain | Current home | Decision | Target owner |
| --- | --- | --- | --- |
| World ID protocol/crypto/HTTP/redaction | `wallet_interface/world_id.py` (955 lines, 128 symbols) | **move** | `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin` |
| World ID application orchestration | `wallet_interface/app_service.py` | **retain** (thin after cutover) | `wallet_interface (thin 211-AI wrapper after cutover)` |
| World ID production readiness/signoff | `wallet_interface/ops.py` | **retain** | `wallet_interface/ops.py` |
| World ID HTTP routes/DTOs | `wallet_interface/routes/world_id.py` | **retain** | `wallet_interface/routes (application HTTP; not reusable processor)` |
| World ID UI / IDKit client | `wallet_interface/ui/**` | **retain** | `wallet_interface/ui (application UI; not reusable processor)` |
| WorldIdBinding + UCAN wallet service | `ipfs_datasets_py/.../wallet` | **retain** (+ delegate protocol) | `ipfs_datasets_py/ipfs_datasets_py/wallet` |
| Xaman formal assurance / IR | `logic/security_ir/xaman`, `logic/security_models/crypto_exchange` | **retain** | `ipfs_datasets_py/ipfs_datasets_py/logic/security_ir/xaman + logic/security_models/crypto_exchange` |
| Xaman/XRPL runtime ledger processor | *(missing)* | **create** | `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman` / XRPL package |
| Generic `can_process` protocol | `processors/protocol.py` | **retain** (not for wallets) | existing processors |
| Generic `can_handle` protocol + registry | `processors/core/protocol.py` + `registry.py` | **retain** (not for wallets) | processors/core |
| Wallet-domain protocols | *(missing)* | **create** | `ipfs_datasets_py/ipfs_datasets_py/processors/wallets (shared contracts)` (WALPROC-G030) |

## 2. Processor protocol ambiguity

Two incompatible generic processor surfaces exist today:

| Surface | Path | Dispatch | Decision |
| --- | --- | --- | --- |
| `legacy-processor-protocol` | `ipfs_datasets_py/ipfs_datasets_py/processors/protocol.py` | `can_process` | retain_generic_do_not_use_for_wallets |
| `core-processor-protocol` | `ipfs_datasets_py/ipfs_datasets_py/processors/core/protocol.py` | `can_handle` | retain_generic_do_not_use_for_wallets_directly |
| `wallet-domain-protocol-planned` | `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/protocols.py` | `n/a (domain methods: validate_address, ingest_wallet, ingest_ledger, export_wallet)` | create |

**Blocker:** which single compatibility adapter wallets may use later is **unresolved** until WALPROC-G030 ADR. Do not implement an opportunistic adapter in chain lanes.

## 3. `wallet_interface/world_id.py` symbol ownership (complete)

Every inventoried symbol in the 955-line module is listed. Default decision is **move** to `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin`.

| Symbol | Kind | Line | Decision | Owner |
| --- | --- | ---: | --- | --- |
| `DEFAULT_WORLD_ID_ACTION` | constant | 40 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `DEFAULT_WORLD_ID_CREDENTIAL_POLICY` | constant | 41 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `DEFAULT_WORLD_ID_VERIFY_BASE_URL` | constant | 42 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `DEFAULT_WORLD_ID_SIGNATURE_TTL_SECONDS` | constant | 43 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `DEFAULT_WORLD_ID_HTTP_TIMEOUT_SECONDS` | constant | 44 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `SUPPORTED_WORLD_ID_ENVIRONMENTS` | constant | 45 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_PUBLIC_SECRET_ENV_NAMES` | constant | 47 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfigError` | class | 55 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdSignatureError` | class | 59 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationError` | class | 63 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdPayloadError` | class | 67 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature` | class | 75 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.signature` | class_attr | 78 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.nonce` | class_attr | 79 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.created_at` | class_attr | 80 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.expires_at` | class_attr | 81 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.action` | class_attr | 82 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.to_protocol_dict` | method | 84 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdRpSignature.to_rp_context` | method | 94 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult` | class | 104 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.success` | class_attr | 107 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.action` | class_attr | 108 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.nullifier` | class_attr | 109 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.created_at` | class_attr | 110 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.environment` | class_attr | 111 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.session_id` | class_attr | 112 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.message` | class_attr | 113 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.results` | class_attr | 114 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.raw_response` | class_attr | 115 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.successful_results` | method | 118 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdVerificationResult.public_dict` | method | 121 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse` | class | 135 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.identifier` | class_attr | 138 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.proof_type` | class_attr | 139 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.signal_hash` | class_attr | 140 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.nullifier` | class_attr | 141 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.session_nullifier` | class_attr | 142 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.session_action` | class_attr | 143 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.issuer_schema_id` | class_attr | 144 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.expires_at_min` | class_attr | 145 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.credential_identifier` | method | 148 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.nullifier_value` | method | 152 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdCredentialResponse.public_dict` | method | 155 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult` | class | 168 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.protocol_version` | class_attr | 171 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.nonce` | class_attr | 172 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.environment` | class_attr | 173 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.proof_type` | class_attr | 174 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.responses` | class_attr | 175 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.action` | class_attr | 176 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.action_description` | class_attr | 177 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.session_id` | class_attr | 178 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.user_presence_completed` | class_attr | 179 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.identity_attested` | class_attr | 180 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.integrity_bundle_present` | class_attr | 181 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.raw_response` | class_attr | 182 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.credential_identifiers` | method | 185 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.signal_hashes` | method | 189 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.nullifiers` | method | 193 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.session_actions` | method | 197 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.verification_timestamps` | method | 201 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.expires_at_min_values` | method | 207 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdIdkitResult.public_dict` | method | 210 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdSecretConfig` | class | 231 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdSecretConfig.value` | class_attr | 234 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdSecretConfig.secret_ref` | class_attr | 235 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdSecretConfig.configured` | method | 238 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdSecretConfig.public_dict` | method | 241 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig` | class | 249 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.enabled` | class_attr | 252 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.environment` | class_attr | 253 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.app_id` | class_attr | 254 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.rp_id` | class_attr | 255 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.allowed_actions` | class_attr | 256 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.default_action` | class_attr | 257 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.credential_policy` | class_attr | 258 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.allow_legacy_proofs` | class_attr | 259 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.require_user_presence` | class_attr | 260 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.rp_signature_ttl_seconds` | class_attr | 261 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.verify_base_url` | class_attr | 262 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.http_timeout_seconds` | class_attr | 263 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.rp_signing_key` | class_attr | 264 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.nullifier_hmac_key` | class_attr | 265 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.public_actions` | method | 268 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `WorldIdConfig.public_dict` | method | 271 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `load_world_id_config` | function | 290 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `world_id_keccak256` | function | 339 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `hash_to_field` | function | 348 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `hash_to_field_hex` | function | 356 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `compute_rp_signature_message` | function | 360 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `eip191_digest` | function | 382 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `sign_world_id_request` | function | 389 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `sign_world_id_request_from_config` | function | 425 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `normalize_idkit_response` | function | 450 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `normalize_world_id_idkit_response` | function | 528 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `verify_world_id_proof` | function | 534 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `verify_world_id_proof_from_config` | function | 568 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `normalize_world_id_verification_response` | function | 587 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `redact_world_id_payload` | function | 619 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_normalize_v3_response` | function | 652 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_normalize_v4_response` | function | 664 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_normalize_v4_session_response` | function | 679 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_response_items` | function | 702 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_proof_list` | function | 714 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_required_string_field` | function | 721 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_optional_string_field` | function | 727 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_non_empty_string` | function | 733 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_optional_bool_field` | function | 739 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_positive_int_field` | function | 748 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_integrity_bundle_present` | function | 757 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_validate_enabled_config` | function | 765 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_actions_from_env` | function | 783 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_reject_public_secret_leaks` | function | 799 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_str_env` | function | 809 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_secret_env` | function | 814 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_bool_env` | function | 820 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_positive_int_env` | function | 832 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_positive_float_env` | function | 843 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_url_env` | function | 854 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_require_signing_dependencies` | function | 861 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_require_keccak_dependency` | function | 866 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_parse_private_key` | function | 871 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_parse_bytes32` | function | 884 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_uint64` | function | 900 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_validate_base_url` | function | 907 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_default_world_id_request_json` | function | 915 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_safe_error_message` | function | 946 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |
| `_redact_text` | function | 950 | **move** | ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin |

## 4. Application World ID orchestration (`app_service.py` / `ops.py`)

| Symbol | Source | Decision | Owner |
| --- | --- | --- | --- |
| `PROVIDER_STAFF_WORLD_ID_ACTION` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `_allow_simulated_proofs_from_env` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `_proof_backend_from_env` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.verify_wallet_snapshot` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.get_world_id_config` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.get_world_id_status` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.create_world_id_rp_signature` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.create_provider_staff_world_id_rp_signature` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.register_world_id_verification` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.revoke_world_id_binding` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.create_location_region_proof_grant` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.create_location_region_proof` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.create_location_distance_proof_grant` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `WalletInterfaceService.create_location_distance_proof` | `wallet_interface/app_service.py` | **retain** | wallet_interface (thin 211-AI wrapper after cutover) |
| `_TARGET_SIGNOFF_PACKET_TEMPLATE` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_SIGNOFF_REQUIRED_ENVIRONMENT_FIELDS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_SIGNOFF_REQUIRED_SECRET_REFS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_SIGNOFF_REQUIRED_ARTIFACT_REFS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_SIGNOFF_REQUIRED_RETENTION_FIELDS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_SIGNOFF_REQUIRED_REVIEW_AREAS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_SIGNOFF_ALLOWED_APPROVAL_DECISIONS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_READINESS_TARGET_ENV_VARS` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_WORLD_ID_REACHABILITY_EVIDENCE_ENV` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_WORLD_ID_SANITIZATION_EVIDENCE_ENV` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_WORLD_ID_SIGNATURE_VECTOR_CREATED_AT` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_WORLD_ID_SIGNATURE_VECTOR_ENTROPY` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_world_id_production_readiness_checks` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_signoff_review_status` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `validate_target_signoff_packet` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `validate_target_signoff_packet_template` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `validate_proof_contract` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `validate_distance_proof_contract` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `validate_production_readiness` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `_has_target_readiness_environment` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |
| `validate_local_production_readiness_self_check` | `wallet_interface/ops.py` | **retain** | wallet_interface/ops.py (211-AI ops) |

## 5. `ipfs_datasets_py.wallet` World ID binding / snapshot / proof paths

| Symbol | Source | Decision | Owner |
| --- | --- | --- | --- |
| `DataVersion.proof_receipt_ids` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataRecord` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `Wallet` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.binding_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.wallet_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.actor_did` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.rp_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.action` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.protocol_version` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.environment` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.nullifier_ref` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.app_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.credential_identifiers` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.issuer_schema_ids` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.proof_receipt_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.session_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.signal_hash_ref` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.verification_status` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.status` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.verified_at` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.expires_at_min` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.created_at` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.updated_at` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.metadata` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WorldIdBinding.to_dict` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `Grant` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `Grant.proof_chain` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.proof_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.wallet_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.proof_type` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.statement` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.verifier_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.public_inputs` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.proof_hash` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.witness_record_ids` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.is_simulated` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.proof_system` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.circuit_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.verifier_digest` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.proof_artifact_ref` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.verification_status` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.created_at` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.expires_at` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.metadata` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `ProofReceipt.to_dict` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `AnalyticsContribution.nullifier` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `AnalyticsContribution.proof_id` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `AuditEvent` | `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` | **retain** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WORLD_ID_PROOF_TYPE` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WORLD_ID_PROOF_SYSTEM` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WORLD_ID_VERIFIER_ID` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `PUBLIC_EXPORT_PROOF_KEYS` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `PUBLIC_EXPORT_PROOF_PRIVATE_KEYS` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `PUBLIC_EXPORT_PROOF_PRIVATE_KEY_PATTERN` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `WORLD_ID_NULLIFIER_REF_PREFIX` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._world_id_binding_resource` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.add_world_id_binding` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.get_world_id_binding` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.list_world_id_bindings` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.find_world_id_binding_by_nullifier` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.create_location_region_proof` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.create_location_distance_proof` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.create_document_profile_proof` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._assert_no_simulated_proof_overclaim` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.export_wallet_snapshot` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.export_analytics_ledger` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.create_export_bundle` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.export_bundle_hash` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._verify_export_bundle_hash` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.verify_export_bundle` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.validate_export_bundle_schema` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.import_export_bundle` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.verify_export_bundle_storage` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._validate_export_bundle_shape` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._public_export_proof_receipt` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._public_export_proof_receipt_from_mapping` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._sanitize_public_export_proof_public_inputs` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._sanitize_public_export_proof_mapping` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._sanitize_public_export_proof_value` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._assert_public_export_proof_is_sanitized` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._private_public_export_proof_key` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._private_public_export_proof_string` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._export_wallet_descriptor` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.create_export_bundle_with_invocation` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService.import_wallet_snapshot` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._store_world_id_binding` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._store_world_id_private_nullifier` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._ensure_world_id_proof_receipt` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._create_world_id_proof_receipt` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._world_id_proof_public_inputs` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._world_id_public_nullifier_commitment` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._world_id_nullifier_ref` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._world_id_raw_nullifier_commitment` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._required_world_id_string` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._normalize_world_id_schema_ids` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._normalize_world_id_expires_at_min` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |
| `DataWalletService._assert_export_grant_allows` | `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` | **retain_with_delegation** | ipfs_datasets_py/ipfs_datasets_py/wallet |

## 6. Callers (Python and TypeScript)

### Python callers of `wallet_interface.world_id`

- `wallet_interface/app_service.py`
- `wallet_interface/ops.py`
- `tests/test_world_id_wallet.py`
- `tests/test_world_id_wallet_api.py`
- `tests/contract/test_wallet_api_contract.py`
- `tests/test_wallet_interface.py`
- `tests/test_wallet_interface_api.py`
- `tests/test_wallet_interface_ops.py`
- `tests/test_wallet_interface_hmis_api.py`
- `tests/test_hmis_end_to_end.py`
- `tests/test_hmis_reconciliation.py`
- `scripts/hmis_reconciliation_job.py`
- `tests/world_aid/test_integration_audit_contract.py`

### TypeScript / UI callers

- `wallet_interface/ui/src/features/wallet/lib/walletApi.ts`
- `wallet_interface/ui/src/features/wallet/lib/walletProofReview.ts`
- `wallet_interface/ui/src/shared/components/WorldIdVerificationPanel.tsx`
- `wallet_interface/ui/src/components/world-id/WorldIdVerificationPanel.tsx`
- `wallet_interface/ui/src/app/components/WorldIdSurfaceStatus.tsx`
- `wallet_interface/ui/src/shared/lib/runtimeConfig.ts`
- `wallet_interface/ui/src/features/wallet/components/ProofCenterScreen.tsx`
- `wallet_interface/ui/src/features/wallet/components/RegistrationScreen.tsx`
- `wallet_interface/ui/src/features/wallet/components/SettingsScreen.tsx`
- `wallet_interface/ui/src/features/wallet/components/UploadsScreen.tsx`
- `wallet_interface/ui/tests/fixtures/world-id-fixtures.ts`
- `wallet_interface/ui/tests/world-id.spec.ts`
- `wallet_interface/ui/tests/world-id-ux.spec.ts`
- `wallet_interface/ui/tests/world-id-fullstack.spec.ts`
- `wallet_interface/services/world_siwe_verifier/index.mjs`

## 7. Xaman / XRPL formal assets (retain)

Counted **34** Xaman-related formal/security assets under logic. Runtime processor package is **missing** and must be created under `processors/wallets/xaman` without importing assurance report internals.

<details><summary>Asset path list</summary>

- `ipfs_datasets_py/ipfs_datasets_py/logic/security_ir/xaman/adapter.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_ir/xaman/config.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/extractors/xaman_runtime_trace_ingestor.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/extractors/xaman_source_extractor.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_assurance_packet.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_counterexample_triage.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_disproof_suite.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_gap_remediation_status.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_gap_remediation_workflow.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_native_vault_android_preflight.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_native_vault_assessment.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_native_vault_fault_injection.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_native_vault_ios_preflight.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_native_vault_state_fuzz.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_production_blocker_bridge.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_proof_consumer.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_protocol_projection.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_public_source_testnet_assurance_verdict.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_self_hosted_resolution_protocol.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_self_hosted_review.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_self_hosted_runtime_trace.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_apalache.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_assurance_verdict.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_fuzzing.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_kernel_proofs.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_leanstral.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_protocol.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_public_build_reproduction.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_runtime_conformance.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_smt_results.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_smt_worker.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_testnet_solver_portfolio.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_tla_workflow.py`
- `ipfs_datasets_py/ipfs_datasets_py/logic/security_models/crypto_exchange/reports/xaman_vendor_evidence.py`

</details>

## 8. Network endpoints, config keys, secrets

### Network endpoints

- **world-developer-portal-verify-v4**: `{WORLD_ID_VERIFY_BASE_URL}/api/v4/verify/{rp_id}` (source: `wallet_interface/world_id.py`)
- **ops-local-self-check-verifier**: `http://127.0.0.1/local-self-check-verifier` (source: `wallet_interface/ops.py`)
- **ops-staging-alert-webhook-example**: `https://ops.staging.211.local/hooks/wallet` (source: `wallet_interface/ops.py`)

### Config keys (scanned)

`ABBY_RUNTIME_WORLD_ID_NULLIFIER_HMAC_KEY`, `ABBY_RUNTIME_WORLD_ID_RP_SIGNING_KEY`, `VITE_WORLD_ID_NULLIFIER_HMAC_KEY`, `VITE_WORLD_ID_RP_SIGNING_KEY`, `WALLET_ALLOW_SIMULATED_PROOFS`, `WALLET_OPS_ALERT_BEARER_TOKEN`, `WALLET_OPS_ALERT_HEADER_NAME`, `WALLET_OPS_ALERT_HEADER_VALUE`, `WALLET_OPS_ALERT_ON`, `WALLET_OPS_ALERT_SECRET_REF`, `WALLET_OPS_ALERT_WEBHOOK_URL`, `WALLET_OPS_HEALTH_SECRET_REF`, `WALLET_OPS_HEALTH_SHARED_SECRET`, `WALLET_PROOF_BACKEND`, `WALLET_PROOF_BEARER_TOKEN`, `WALLET_PROOF_CIRCUIT_ID`, `WALLET_PROOF_CREDENTIAL_SECRET_REF`, `WALLET_PROOF_DISTANCE_PROVE_PATH`, `WALLET_PROOF_HTTP_HEADER_NAME`, `WALLET_PROOF_HTTP_HEADER_VALUE`, `WALLET_PROOF_MODE`, `WALLET_PROOF_PROVE_PATH`, `WALLET_PROOF_SERVICE_URL`, `WALLET_PROOF_SYSTEM`, `WALLET_PROOF_TIMEOUT_SECONDS`, `WALLET_PROOF_VERIFIER_ID`, `WALLET_PROOF_VERIFY_PATH`, `WALLET_REPOSITORY_ROOT`, `WALLET_STORAGE_BUCKET`, `WALLET_STORAGE_CONFIG`, `WALLET_STORAGE_CREDENTIAL_SECRET_REF`, `WALLET_STORAGE_MIRRORS`, `WALLET_STORAGE_PIN`, `WALLET_STORAGE_PREFIX`, `WALLET_STORAGE_ROOT`, `WALLET_STORAGE_TYPE`, `WORLD_ID_ALLOWED_ACTIONS`, `WORLD_ID_ALLOW_LEGACY_PROOFS`, `WORLD_ID_APP_ID`, `WORLD_ID_CREDENTIAL_POLICY`, `WORLD_ID_DEFAULT_ACTION`, `WORLD_ID_ENABLED`, `WORLD_ID_ENVIRONMENT`, `WORLD_ID_HTTP_TIMEOUT_SECONDS`, `WORLD_ID_NULLIFIER_HMAC_KEY`, `WORLD_ID_NULLIFIER_HMAC_KEY_SECRET_REF`, `WORLD_ID_PROOF_SANITIZATION_EVIDENCE`, `WORLD_ID_RAW_DEVELOPER_RESPONSE_READINESS_SENTINEL`, `WORLD_ID_RAW_MERKLE_ROOT_READINESS_SENTINEL`, `WORLD_ID_RAW_NULLIFIER_READINESS_SENTINEL`, `WORLD_ID_RAW_PROOF_READINESS_SENTINEL`, `WORLD_ID_RAW_RP_SIGNATURE_READINESS_SENTINEL`, `WORLD_ID_REQUIRE_USER_PRESENCE`, `WORLD_ID_RP_ID`, `WORLD_ID_RP_SIGNATURE_TTL_SECONDS`, `WORLD_ID_RP_SIGNING_KEY`, `WORLD_ID_RP_SIGNING_KEY_SECRET_REF`, `WORLD_ID_VERIFY_BASE_URL`, `WORLD_ID_VERIFY_ENDPOINT_REACHABILITY_EVIDENCE`

### Secret references

| Name | Kind | Disposition | Role |
| --- | --- | --- | --- |
| `WORLD_ID_RP_SIGNING_KEY` | raw_secret_env | **retain_as_secret_ref_only** | RP request signing private key (hex) |
| `WORLD_ID_NULLIFIER_HMAC_KEY` | raw_secret_env | **retain_as_secret_ref_only** | Nullifier HMAC key |
| `WORLD_ID_RP_SIGNING_KEY_SECRET_REF` | secret_ref | **retain** | Indirection to RP signing key via resolve_secret |
| `WORLD_ID_NULLIFIER_HMAC_KEY_SECRET_REF` | secret_ref | **retain** | Indirection to nullifier HMAC key via resolve_secret |
| `VITE_WORLD_ID_RP_SIGNING_KEY` | forbidden_public_env | **deprecate_reject** | Must never hold signing secrets in frontend env |
| `VITE_WORLD_ID_NULLIFIER_HMAC_KEY` | forbidden_public_env | **deprecate_reject** | Must never hold nullifier secrets in frontend env |
| `ABBY_RUNTIME_WORLD_ID_RP_SIGNING_KEY` | forbidden_public_env | **deprecate_reject** | Runtime public surface secret leak check |
| `ABBY_RUNTIME_WORLD_ID_NULLIFIER_HMAC_KEY` | forbidden_public_env | **deprecate_reject** | Runtime public surface secret leak check |
| `WALLET_PROOF_BEARER_TOKEN` | raw_secret_env | **retain_as_secret_ref_only** | Optional proof service bearer token |
| `WALLET_OPS_HEALTH_SHARED_SECRET` | raw_secret_env | **retain_as_secret_ref_only** | Ops health shared secret |

## 9. Optional dependencies

- `ipfs_datasets_py` extras: `ipld`, `knowledge_graphs`, `logic`, `theorem-provers`, `file_conversion`, `multimedia`, `ocr`, `vectors`, `groth16`, `profile-f-zk`, `provekit`, `api`, `symai_router`, `lazy`, `legal_netherlands`, `scraping`, `test`, `all`
- **Wallet processor chain extras: not declared** (blocker → WALPROC-G050).
- World ID soft optional imports: `Crypto.Hash.keccak` (pycryptodome), `coincurve`.
- `211-ai` optional extra `[wallet]`: FastAPI/runtime only.

## 10. Blockers (unresolved ownership — do not guess)

### BLOCKER-WALPROC-G010-001: No single owner yet for which generic ProcessorProtocol adapter wallets will bind to

- Severity: **high**
- Resolving goal: `WALPROC-G030`
- Detail: Both processors/protocol.py (can_process) and processors/core/protocol.py (can_handle) exist and are incompatible. WALPROC-G030 must produce an ADR permitting exactly one later compatibility adapter. Until then, ownership of the adapter symbol is unresolved; do not implement an opportunistic adapter.
- Guessed: `False`

### BLOCKER-WALPROC-G010-002: World ID binding nullifier storage ownership boundary between wallet.service and worldcoin processor

- Severity: **medium**
- Resolving goal: `WALPROC-G090`
- Detail: DataWalletService owns private nullifier storage, public nullifier commitment, and proof receipts today. Reusable verification/signing moves to processors.wallets.worldcoin. Exact split of _store_world_id_private_nullifier / _world_id_public_nullifier_commitment vs processor projections is deferred to WALPROC-G090/G100 extraction tasks. Recorded as blocker rather than guessing which helper moves first.
- Guessed: `False`

### BLOCKER-WALPROC-G010-003: Wallet processor optional dependency extras are not declared

- Severity: **medium**
- Resolving goal: `WALPROC-G050`
- Detail: ipfs_datasets_py optional extras have no worldcoin/xaman/ethereum/bitcoin/solana groups yet. Signing currently soft-depends on pycryptodome and coincurve inside wallet_interface/world_id.py. Package owner for extras declaration is WALPROC-G050/WALPROC-010; not invented here.
- Guessed: `False`

### BLOCKER-WALPROC-G010-004: Duplicate WorldIdVerificationPanel paths in UI

- Severity: **low**
- Resolving goal: `WALPROC-G710`
- Detail: Both wallet_interface/ui/src/shared/components/WorldIdVerificationPanel.tsx and wallet_interface/ui/src/components/world-id/WorldIdVerificationPanel.tsx exist. Which is canonical for post-cutover UI is an application cleanup decision; both retained for now.
- Guessed: `False`

## 11. Freeze gate

Phase 0 gate from the migration plan: **no production move begins** until this inventory identifies every current import and the protocol decision (WALPROC-G030) is accepted.

This document satisfies the inventory half of that gate for WALPROC-G010.
