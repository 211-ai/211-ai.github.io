"""FastAPI surface for 211-AI wallet workflows."""
# ruff: noqa: E501

from __future__ import annotations

from .app_service import WalletInterfaceService
from .helpers._app import _cors_origins_from_env, _wallet_interface_service_from_env

# ---------------------------------------------------------------------------
# Backward-compatible re-exports
# Tests and scripts that were written against the old monolithic api.py access
# these helpers as `wallet_interface.api.<name>`.  Importing them here keeps
# those call-sites (and monkeypatches) working without requiring test changes.
# ---------------------------------------------------------------------------
from .helpers._auth import _send_sms_notification  # noqa: F401
from .helpers._tts import (  # noqa: F401
    _run_indextts_gradio_batch_tts,
    _run_indextts_gradio_tts,
    _run_indextts_tts_with_batch_fallback,
)
from .helpers._tts_client import (  # noqa: F401
    _INDEXTTS_CONFIG_CACHE,
    _INDEXTTS_FN_INDEX_CACHE,
    _INDEXTTS_REFERENCE_CACHE,
    _fetch_gradio_file,
    _indextts_batch_audio_references,
    _indextts_space_client,
    _indextts_wait_for_result,
)
from .helpers._tts_http import _run_hf_whisper_stt  # noqa: F401
from .helpers._tts_normalization import _normalize_indextts_spoken_text  # noqa: F401
from .helpers._voice_router_adapter import (  # noqa: F401
    WalletVoiceRouterAdapter,
    build_voice_turn_request,
    is_unified_voice_router_enabled,
    process_wallet_voice_turn,
    route_wallet_voice_turn,
    serialize_voice_turn_result,
)
from .helpers._voice_action_surface import (  # noqa: F401
    VOICE_ACTION_EXECUTE_FLAG,
    attach_action_surface,
    extract_voice_route,
    is_voice_action_execute_enabled,
)

try:  # resolve_secret is an optional dep; guard it the same way the helpers do.
    from ipfs_datasets_py.utils.secrets import resolve_secret  # noqa: F401
except Exception:  # pragma: no cover
    resolve_secret = None  # type: ignore[assignment]

# urllib_request re-exported so legacy patches on wallet_interface.api.urllib_request work.
from urllib import request as urllib_request  # noqa: F401

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    CORSMiddleware = None  # type: ignore[assignment]


def create_app(*, service: WalletInterfaceService | None = None):
    """Create the wallet API app.

    The API stays deliberately thin: all authorization, crypto, proofs,
    analytics privacy, and audit behavior remains in `ipfs_datasets_py.wallet`.
    """

    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")

    from .routes.ai_router import create_router as create_ai_router
    from .routes.analytics import create_router as create_analytics_router
    from .routes.auth import create_router as create_auth_router
    from .routes.dead_drops import create_router as create_dead_drops_router
    from .routes.exports import create_router as create_exports_router
    from .routes.grants import create_router as create_grants_router
    from .routes.hmis import create_router as create_hmis_router
    from .routes.notifications import create_router as create_notifications_router
    from .routes.ops import create_router as create_ops_router
    from .routes.proofs import create_router as create_proofs_router
    from .routes.records import create_router as create_records_router
    from .routes.storage import create_router as create_storage_router
    from .routes.wallets import create_router as create_wallets_router
    from .routes.world_id import create_router as create_world_id_router

    app_service = service or _wallet_interface_service_from_env()
    app = FastAPI(title="211-AI Wallet Interface", version="0.1.0")
    cors_origins = _cors_origins_from_env()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["authorization", "content-type", "x-wallet-ops-shared-secret"],
        )

    for create_router in (
        # ops first: its literal /wallets/snapshots paths must not be shadowed
        # by create_wallets_router's /wallets/{wallet_id} wildcard.
        create_ops_router,
        create_auth_router,
        create_wallets_router,
        create_dead_drops_router,
        create_notifications_router,
        create_proofs_router,
        create_ai_router,
        create_storage_router,
        create_records_router,
        create_world_id_router,
        create_hmis_router,
        create_grants_router,
        create_exports_router,
        create_analytics_router,
    ):
        app.include_router(create_router(app_service))
    return app
