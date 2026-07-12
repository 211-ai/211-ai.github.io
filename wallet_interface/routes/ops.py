"""Route factory for ops endpoints."""

from __future__ import annotations

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..api import *  # noqa: F401,F403
from ..schemas import *  # noqa: F401,F403

def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.get("/ops/health")
    def ops_health(
        verify_storage: bool = False,
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        expected_secret = _ops_health_shared_secret()
        if expected_secret:
            supplied_secret = _extract_bearer_token(authorization) or str(x_wallet_ops_shared_secret or "").strip()
            if supplied_secret != expected_secret:
                raise HTTPException(status_code=401, detail="ops health authorization required")
        try:
            report = app_service.ops_health(verify_storage=verify_storage)
            voice_warning = _publicus_indextts_credential_warning()
            if voice_warning:
                checks = list(report.get("checks") or [])
                checks.append(
                    {
                        "name": "voice_proxy_credentials",
                        "status": "warning",
                        "summary": voice_warning["message"],
                        "details": voice_warning,
                    }
                )
                report["checks"] = checks
                report["check_count"] = len(checks)
                if report.get("status") == "ok":
                    report["status"] = "warning"
            return report
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


    @router.get("/ops/voice-proxy/status")
    def ops_voice_proxy_status(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        expected_secret = _ops_health_shared_secret()
        if expected_secret:
            supplied_secret = _extract_bearer_token(authorization) or str(x_wallet_ops_shared_secret or "").strip()
            if supplied_secret != expected_secret:
                raise HTTPException(status_code=401, detail="ops voice proxy authorization required")

        warnings = _voice_proxy_runtime_warnings()
        status = "warning" if warnings else "ok"
        return {
            "status": status,
            "spaceUrl": _indextts_space_base_url(),
            "apiName": _indextts_api_name(),
            "batchApiName": _indextts_batch_api_name(),
            "modelName": os.getenv("WALLET_INDEXTTS_MODEL_NAME", "Publicus/IndexTTS-2-Demo"),
            "billTo": (
                os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
                or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
                or "publicus"
            ).strip() or "publicus",
            "tokenConfigured": bool(_configured_hf_token()),
            "warnings": warnings,
        }


    @router.get("/wallets/snapshots")
    def list_wallet_snapshots() -> Dict[str, Any]:
        return {"wallet_ids": app_service.list_wallet_snapshots()}


    @router.post("/wallets/snapshots/save-all")
    def save_all_wallet_snapshots() -> Dict[str, Any]:
        try:
            paths = app_service.save_all_wallet_snapshots()
            return {"paths": [str(path) for path in paths], "count": len(paths)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/snapshots/load-all")
    def load_all_wallet_snapshots() -> Dict[str, Any]:
        try:
            wallet_ids = app_service.load_all_wallet_snapshots()
            return {"wallet_ids": wallet_ids, "count": len(wallet_ids)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    return router
