"""FastAPI surface for 211-AI wallet workflows."""
# ruff: noqa: E501

from __future__ import annotations

from .app_service import WalletInterfaceService
from .helpers._app import _cors_origins_from_env, _wallet_interface_service_from_env

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
        create_auth_router,
        create_wallets_router,
        create_dead_drops_router,
        create_notifications_router,
        create_proofs_router,
        create_ai_router,
        create_storage_router,
        create_records_router,
        create_hmis_router,
        create_grants_router,
        create_exports_router,
        create_analytics_router,
        create_ops_router,
    ):
        app.include_router(create_router(app_service))
    return app
