"""Route factory for storage endpoints."""

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

    @router.post("/filecoin-upload")
    async def upload_to_ipfs_bridge(
        request: Request,
        file: UploadFile | None = File(default=None),
        metadata: str | None = Form(default=None),
    ) -> Dict[str, Any]:
        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                payload = FilecoinRecordUploadRequest(**(await request.json()))
                encrypted_record = app_service.export_record_encrypted_blobs(
                    payload.walletId,
                    payload.recordId,
                    actor_did=payload.actorDid,
                )
                return _publish_encrypted_record_graph_to_ipfs(
                    encrypted_record,
                    file_name=payload.fileName,
                )

            if file is None:
                raise ValueError("multipart uploads require a file field")
            upload_metadata = _parse_upload_metadata(metadata)
            data = await file.read()
            expected_sha256 = str(upload_metadata.get("sha256") or "").strip()
            if expected_sha256:
                actual_sha256 = hashlib.sha256(data).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ValueError("uploaded file SHA-256 does not match metadata")
            return _publish_bytes_to_ipfs(
                data,
                file_name=str(upload_metadata.get("fileName") or file.filename or "").strip() or None,
                mime_type=str(upload_metadata.get("mimeType") or file.content_type or "").strip() or None,
                source_record_id=str(upload_metadata.get("recordId") or "").strip() or None,
                wallet_id=str(upload_metadata.get("walletId") or "").strip() or None,
            )
        except FilecoinPinHandoffError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/ipfs-proxy/{cid}")
    def proxy_ipfs_cid(cid: str) -> Response:
        normalized_cid = _normalize_ipfs_cid(cid)
        if not _valid_ipfs_cid(normalized_cid):
            raise HTTPException(status_code=400, detail="invalid IPFS CID")
        if not _ipfs_proxy_allows_cid(normalized_cid):
            raise HTTPException(status_code=403, detail="CID is not allowed by WALLET_IPFS_PROXY_ALLOWED_CIDS")
        try:
            payload = get_ipfs_backend().cat(normalized_cid)
        except Exception as local_exc:
            try:
                payload = _fetch_ipfs_cid_via_gateway(normalized_cid)
            except Exception as fallback_exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Unable to fetch CID from local IPFS or fallback gateways: {local_exc}; {fallback_exc}",
                ) from fallback_exc
        return Response(
            content=payload,
            media_type=_ipfs_proxy_media_type(payload),
            headers={"Cache-Control": "public, max-age=300"},
        )


    @router.get("/filecoin-upload/status/{request_id}")
    def get_filecoin_upload_status(request_id: str) -> Dict[str, Any]:
        try:
            payload = _fetch_filecoin_pin_status(request_id)
            normalized_request_id = str(
                payload.get("requestId") or payload.get("requestid") or request_id
            ).strip()
            if normalized_request_id:
                payload["requestId"] = normalized_request_id
            if isinstance(payload.get("info"), dict) and not isinstance(payload.get("filecoinPinInfo"), dict):
                payload["filecoinPinInfo"] = payload["info"]
            status_url = _filecoin_upload_status_url(request_id)
            if status_url:
                payload["statusUrl"] = status_url
            return payload
        except FilecoinPinHandoffError as exc:
            status_code = 503 if "not configured" in str(exc).lower() else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/records/{record_id}/storage")
    def verify_record_storage(wallet_id: str, record_id: str) -> Dict[str, Any]:
        try:
            report = app_service.verify_record_storage(wallet_id, record_id)
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/storage")
    def verify_wallet_storage(wallet_id: str) -> Dict[str, Any]:
        try:
            report = app_service.verify_wallet_storage(wallet_id)
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/storage/repair")
    def repair_wallet_storage(wallet_id: str, request: RepairStorageRequest) -> Dict[str, Any]:
        try:
            report = app_service.repair_wallet_storage(wallet_id, actor_did=request.actor_did)
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/records/{record_id}/storage/repair")
    def repair_record_storage(
        wallet_id: str,
        record_id: str,
        request: RepairStorageRequest,
    ) -> Dict[str, Any]:
        try:
            report = app_service.repair_record_storage(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
            )
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    return router
