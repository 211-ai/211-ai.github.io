# ruff: noqa: E501
"""Helpers package — re-exports from all domain submodules.

Import hierarchy (acyclic):
  _tts_normalization  →  (stdlib only, always importable)
  _tts_gradio         →  (stdlib only, always importable)
  _tts_config         →  (stdlib only, always importable)
  _auth               →  (stdlib only after guards, always importable)
  _app  →  (vendor only)
  _ai_routing  →  _app
  _records  →  _ai_routing
  _tts_http  →  _tts_config, _tts_gradio, resolve_secret (optional dep)
  _tts  →  _tts_normalization, _tts_gradio, _tts_config, _tts_http, (vendor)
  _storage  →  _app, _auth
"""

from __future__ import annotations

from ._tts_config import (  # noqa: F401
    _INDEXTTS_ACTIVE_SPACE_URL,
    _INDEXTTS_ACTIVE_TIMEOUT_SECONDS,
    _INDEXTTS_FAST_FAIL_MODE,
    _INDEXTTS_FORCE_REQUIRE_BATCH,
    _clean_voice_reply_text,
    _hf_whisper_model_name,
    _hf_whisper_timeout_seconds,
    _indextts_allow_direct_predict_fallback,
    _indextts_api_name,
    _indextts_attempt_timeout_seconds,
    _indextts_batch_api_name,
    _indextts_cache_ttl_seconds,
    _indextts_degraded_error_payload,
    _indextts_degraded_fast_fail_enabled,
    _indextts_endpoint_retry_count,
    _indextts_endpoint_timeout_seconds,
    _indextts_fallback_space_base_url,
    _indextts_fast_fail_mode,
    _indextts_force_require_batch,
    _indextts_is_fast_fail_mode,
    _indextts_model_name,
    _indextts_require_batch_mode,
    _indextts_single_batch_fallback_enabled,
    _indextts_space_base_url,
    _indextts_space_base_urls,
    _indextts_timeout_seconds,
    _indextts_use_space_base_url,
    _indextts_use_timeout_seconds,
    _is_opaque_indextts_queue_failure,
    _run_indextts_with_endpoint_retry,
    _run_indextts_with_endpoint_timeout,
    _silent_wav_bytes,
    _voice_llm_timeout_seconds,
)

# ── stdlib-only, always importable ──────────────────────────────────────────
from ._tts_gradio import (  # noqa: F401
    _dedupe_gradio_references,
    _default_indextts_reference_wav,
    _extract_audio_files_from_zip,
    _extract_hf_whisper_text,
    _find_gradio_audio_reference,
    _find_gradio_audio_references,
    _find_gradio_file_reference,
    _first_upload_path,
    _gradio_file_key,
    _gradio_output_values,
    _gradio_update_value,
    _indextts_batch_request_data,
    _indextts_request_data,
    _normalize_indextts_queue_failure,
)
from ._tts_normalization import *  # noqa: F401,F403
from ._tts_normalization import (  # noqa: F401
    _normalize_indextts_spoken_text,
    _normalize_phone_numbers,
    _normalize_zip_codes,
    _number_to_words,
    _ordinal_to_words,
    _strip_coordinates,
    _strip_scraped_page_chrome,
    _strip_unspoken_fields,
    _title_case_program_name,
)

# ── _auth is importable without optional deps (guards its own ipfs import) ──
try:
    from ._auth import *  # noqa: F401,F403
    from ._auth import (  # noqa: F401
        _build_magic_login_link,
        _extract_bearer_token,
        _is_email_contact,
        _issue_magic_ucan,
        _magic_login_base_url,
        _magic_login_payload_from_request,
        _normalize_phone_number,
        _require_internal_webhook_auth,
        _require_magic_ucan,
        _require_portland_police_missing_email,
        _send_auth_email_notification,
        _send_phone_call_notification,
        _send_sms_notification,
        _sign_magic_login_token,
        _sms_inbound_actor_did,
        _verify_magic_login_token,
        _wallet_config_from_magic_payload,
    )
except ImportError:
    pass

# ── optional-dependency modules ──────────────────────────────────────────────
try:
    from ._ai_routing import *  # noqa: F401,F403
    from ._ai_routing import (  # noqa: F401
        _analysis_result_to_dict,
        _check_wallet_router_rate_limit,
        _match_to_dict,
        _require_wallet_router_actor,
        _wallet_router_subject,
    )
    from ._app import *  # noqa: F401,F403
    from ._app import (  # noqa: F401
        _fetch_ipfs_cid_via_gateway,
        _ipfs_proxy_allows_cid,
        _ipfs_proxy_media_type,
        _normalize_ipfs_cid,
        _ops_health_shared_secret,
        _prepare_hf_router_environment,
        _valid_ipfs_cid,
    )
    from ._records import *  # noqa: F401,F403
    from ._records import (  # noqa: F401
        _build_document_profile_public_inputs,
        _build_privacy_search_text,
        _build_privacy_vector_terms,
        _classify_document_profile,
        _default_labels_for_mime_type,
        _derived_artifact_id,
        _derived_output,
        _fallback_document_profile_output,
        _generate_wallet_organizer_profile,
        _read_string_list,
        _record_metadata_value,
        _summarize_document_profile,
    )
    from ._storage import *  # noqa: F401,F403
    from ._storage import (  # noqa: F401
        _fetch_filecoin_pin_status,
        _filecoin_upload_status_url,
        _key_from_optional_hex,
        _parse_upload_metadata,
        _publish_bytes_to_ipfs,
        _publish_encrypted_record_graph_to_ipfs,
        _publish_record_metadata_ipld,
        _send_dead_drop_email,
        _should_publish_record_metadata_ipld,
    )
    from ._tts import *  # noqa: F401,F403
    from ._tts import (  # noqa: F401
        _indextts_api_name,
        _indextts_batch_api_name,
        _indextts_space_base_url,
        _run_indextts_gradio_batch_tts,
        _run_indextts_tts_with_batch_fallback,
        _silent_wav_bytes,
    )
    from ._tts_http import *  # noqa: F401,F403
    from ._tts_http import (  # noqa: F401
        _configured_hf_token,
        _generate_indextts_voice_reply_text,
        _gradio_upload_file,
        _http_bytes,
        _http_json,
        _indextts_headers,
        _publicus_indextts_credential_warning,
        _run_hf_whisper_stt,
        _voice_proxy_runtime_warnings,
    )
except ImportError:
    pass
