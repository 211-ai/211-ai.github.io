# ruff: noqa: E501
"""IPFS publish, Filecoin pin, encryption-key, and dead-drop email helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import smtplib
from collections.abc import Mapping
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from ._app import FilecoinPinHandoffError

try:
    from .._vendor import ensure_ipfs_datasets_py_path

    ensure_ipfs_datasets_py_path()

    from ipfs_datasets_py.ipfs_backend_router import get_ipfs_backend  # noqa: E402

    _IPFS_BACKEND_AVAILABLE = True
except ImportError:
    get_ipfs_backend = None  # type: ignore[assignment]
    _IPFS_BACKEND_AVAILABLE = False

try:
    from ._auth import _send_webhook_notification  # noqa: E402

    _AUTH_AVAILABLE = True
except ImportError:
    _send_webhook_notification = None  # type: ignore[assignment]
    _AUTH_AVAILABLE = False


def _parse_upload_metadata(metadata: str | None) -> dict[str, Any]:
    if not metadata:
        return {}
    parsed = json.loads(metadata)
    if not isinstance(parsed, dict):
        raise ValueError("upload metadata must decode to an object")
    return parsed


def _publish_bytes_to_ipfs(
    data: bytes,
    *,
    file_name: str | None = None,
    mime_type: str | None = None,
    source_record_id: str | None = None,
    wallet_id: str | None = None,
) -> dict[str, Any]:
    cid = _publish_bytes_via_ipfs_backend(data)
    gateway_base_url = os.environ.get("WALLET_IPFS_PUBLIC_GATEWAY_BASE_URL", "/ipfs-proxy").rstrip("/")
    payload: dict[str, Any] = {
        "cid": cid,
        "gatewayUrl": f"{gateway_base_url}/{cid}",
        "ipfsCid": cid,
        "message": "Pinned to IPFS through the wallet upload bridge.",
        "provider": "ipfs-filecoin",
        "status": "stored",
    }
    sidecar_result = _submit_ipfs_cid_to_filecoin_pin(
        cid,
        file_name=file_name,
        mime_type=mime_type,
        source_record_id=source_record_id,
        wallet_id=wallet_id,
    )
    if sidecar_result is not None:
        payload["message"] = "Pinned to IPFS and queued for Filecoin persistence through the wallet upload bridge."
        request_id = str(sidecar_result.get("requestid") or sidecar_result.get("requestId") or "").strip()
        handoff_status = str(sidecar_result.get("status") or "").strip()
        if request_id:
            payload["requestId"] = request_id
            payload["filecoinPinRequestId"] = request_id
            payload["statusUrl"] = _filecoin_upload_status_url(request_id)
        if handoff_status:
            payload["filecoinPinStatus"] = handoff_status
        if isinstance(sidecar_result.get("info"), dict):
            payload["filecoinPinInfo"] = sidecar_result["info"]
    if file_name:
        payload["fileName"] = file_name
    if mime_type:
        payload["mimeType"] = mime_type
    if source_record_id:
        payload["recordId"] = source_record_id
    if wallet_id:
        payload["walletId"] = wallet_id
    return payload


def _publish_encrypted_record_graph_to_ipfs(
    encrypted_record: Mapping[str, Any],
    *,
    file_name: str | None = None,
) -> dict[str, Any]:
    record = dict(encrypted_record["record"])
    version = dict(encrypted_record["version"])
    wallet_id = str(record.get("wallet_id") or "")
    record_id = str(record.get("record_id") or "")
    version_id = str(version.get("version_id") or record.get("current_version_id") or "")
    payload_result = _publish_bytes_to_ipfs(
        encrypted_record["encrypted_payload"],
        file_name=f"{file_name or record_id}.encrypted-payload.json",
        mime_type="application/vnd.211-ai.wallet.encrypted-payload+json",
        source_record_id=record_id,
        wallet_id=wallet_id,
    )
    payload_cid = str(payload_result.get("ipfsCid") or payload_result.get("cid") or "")
    metadata_result = None
    metadata_cid = ""
    if encrypted_record.get("encrypted_metadata") is not None:
        metadata_result = _publish_bytes_to_ipfs(
            encrypted_record["encrypted_metadata"],
            file_name=f"{file_name or record_id}.encrypted-metadata.json",
            mime_type="application/vnd.211-ai.wallet.encrypted-metadata+json",
            source_record_id=record_id,
            wallet_id=wallet_id,
        )
        metadata_cid = str(metadata_result.get("ipfsCid") or metadata_result.get("cid") or "")
    encrypted_payload_ref = dict(version.get("encrypted_payload_ref") or {})
    encrypted_metadata_ref = dict(version.get("encrypted_metadata_ref") or {}) if version.get("encrypted_metadata_ref") else None
    graph = {
        "schemaVersion": "211-ai-wallet-encrypted-record-ipld-v1",
        "walletId": wallet_id,
        "recordId": record_id,
        "versionId": version_id,
        "dataType": record.get("data_type"),
        "sensitivity": record.get("sensitivity"),
        "publicDescriptor": record.get("public_descriptor"),
        "ciphertextHash": version.get("ciphertext_hash"),
        "encryptionSuite": version.get("encryption_suite"),
        "encryptedPayload": {
            "/": payload_cid,
            "storageRef": encrypted_payload_ref,
            "filecoin": payload_result,
        },
        "encryptedMetadata": (
            {
                "/": metadata_cid,
                "storageRef": encrypted_metadata_ref,
                "filecoin": metadata_result,
            }
            if metadata_result is not None
            else None
        ),
        "walletMetadata": None,
        "links": [
            {"name": "encrypted_payload", "/": payload_cid, "mediaType": "application/vnd.211-ai.wallet.encrypted-payload+json"},
            *(
                [{"name": "encrypted_metadata", "/": metadata_cid, "mediaType": "application/vnd.211-ai.wallet.encrypted-metadata+json"}]
                if metadata_result is not None
                else []
            ),
        ],
    }
    wallet_metadata_cid = _record_metadata_cid(encrypted_record)
    if wallet_metadata_cid:
        graph["walletMetadata"] = {
            "/": wallet_metadata_cid,
            "mediaType": "application/vnd.211-ai.wallet.record-metadata+json",
        }
        graph["links"].append(
            {
                "name": "wallet_metadata",
                "/": wallet_metadata_cid,
                "mediaType": "application/vnd.211-ai.wallet.record-metadata+json",
            }
        )
    graph_result = _publish_bytes_to_ipfs(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        file_name=f"{file_name or record_id}.ipld-wallet-record.json",
        mime_type="application/vnd.ipld.dag-json",
        source_record_id=record_id,
        wallet_id=wallet_id,
    )
    graph_cid = str(graph_result.get("ipfsCid") or graph_result.get("cid") or "")
    return {
        **graph_result,
        "message": "Pinned encrypted wallet record graph to IPFS/Filecoin.",
        "encryptedPayloadCid": payload_cid,
        "encryptedMetadataCid": metadata_cid or None,
        "metadataCid": wallet_metadata_cid or None,
        "metadataIpldCid": wallet_metadata_cid or None,
        "ipldLinks": graph["links"],
        "recordId": record_id,
        "versionId": version_id,
        "root": {"/": graph_cid},
        "walletId": wallet_id,
    }


def _record_metadata_cid(encrypted_record: Mapping[str, Any]) -> str:
    metadata = encrypted_record.get("metadata")
    if isinstance(metadata, Mapping):
        for key in ("metadataCid", "metadataIpldCid"):
            value = str(metadata.get(key) or "").strip()
            if value:
                return value
    record = encrypted_record.get("record")
    if isinstance(record, Mapping):
        metadata = record.get("metadata")
        if isinstance(metadata, Mapping):
            for key in ("metadataCid", "metadataIpldCid"):
                value = str(metadata.get(key) or "").strip()
                if value:
                    return value
    return ""


def _should_publish_record_metadata_ipld(metadata: Mapping[str, Any]) -> bool:
    generated_keys = {
        "decryptedClassification",
        "decryptedLabels",
        "decryptedMimeType",
        "privacyProfileArtifactIds",
        "privacyProfileClassification",
        "privacyProfileLabels",
        "privacyProfileMimeType",
        "privacyProfileProofId",
        "privacyProfilePublicInputs",
        "privacyProfileSearchText",
        "privacyProfileStatus",
        "privacyProfileSummary",
        "privacyProfileVectorTerms",
    }
    return any(key in metadata for key in generated_keys)


def _publish_record_metadata_ipld(record: Mapping[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    generated_metadata = _generated_wallet_metadata(metadata)
    if not generated_metadata:
        return {}
    record_id = str(record.get("record_id") or "")
    wallet_id = str(record.get("wallet_id") or metadata.get("walletId") or "")
    graph = {
        "schemaVersion": "211-ai-wallet-record-metadata-ipld-v1",
        "walletId": wallet_id,
        "recordId": record_id,
        "dataType": record.get("data_type"),
        "sensitivity": record.get("sensitivity"),
        "metadata": generated_metadata,
        "privacyPolicy": "proof_backed_metadata_no_plaintext_payload",
        "links": [
            *(
                [
                    {
                        "name": "document_privacy_profile_proof",
                        "proofId": str(generated_metadata["privacyProfileProofId"]),
                        "mediaType": "application/vnd.211-ai.wallet.proof-receipt+json",
                    }
                ]
                if generated_metadata.get("privacyProfileProofId")
                else []
            ),
            *(
                [
                    {
                        "name": "derived_artifact",
                        "artifactId": artifact_id,
                        "mediaType": "application/vnd.211-ai.wallet.derived-artifact+json",
                    }
                    for artifact_id in generated_metadata.get("privacyProfileArtifactIds", [])
                    if isinstance(artifact_id, str) and artifact_id.strip()
                ]
            ),
        ],
    }
    result = _publish_bytes_to_ipfs(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        file_name=f"{record_id or 'wallet-record'}.wallet-metadata.ipld.json",
        mime_type="application/vnd.211-ai.wallet.record-metadata+json",
        source_record_id=record_id or None,
        wallet_id=wallet_id or None,
    )
    cid = str(result.get("ipfsCid") or result.get("cid") or "")
    if not cid:
        return {}
    existing_links = metadata.get("ipldLinks") if isinstance(metadata.get("ipldLinks"), list) else []
    metadata_link = {
        "name": "wallet_metadata",
        "/": cid,
        "mediaType": "application/vnd.211-ai.wallet.record-metadata+json",
    }
    links = [
        link
        for link in existing_links
        if not (isinstance(link, Mapping) and str(link.get("name") or "") == "wallet_metadata")
    ]
    links.append(metadata_link)
    patch: dict[str, Any] = {
        "metadataCid": cid,
        "metadataGatewayUrl": result.get("gatewayUrl") or result.get("url"),
        "metadataIpldCid": cid,
        "metadataIpldLink": metadata_link,
        "metadataStorageMessage": result.get("message") or "Pinned wallet metadata IPLD to IPFS/Filecoin.",
        "ipldLinks": links,
    }
    for key in ("filecoinPinRequestId", "filecoinPinStatus", "filecoinPinStatusUrl"):
        value = result.get(key)
        if value:
            patch[f"metadata{key[0].upper()}{key[1:]}"] = value
    return patch


def _generated_wallet_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "decryptedClassification",
        "decryptedLabels",
        "decryptedMimeType",
        "fileName",
        "privacyProfileArtifactIds",
        "privacyProfileClassification",
        "privacyProfileLabels",
        "privacyProfileMimeType",
        "privacyProfileProofId",
        "privacyProfilePublicInputs",
        "privacyProfileSearchText",
        "privacyProfileStatus",
        "privacyProfileSummary",
        "privacyProfileVectorTerms",
    }
    generated = {key: metadata[key] for key in sorted(allowed) if key in metadata}
    return _json_safe_metadata(generated)


def _json_safe_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe_metadata(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_json_safe_metadata(item) for item in value if item is not None]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _publish_bytes_via_ipfs_backend(data: bytes) -> str:
    backend_mode = str(os.getenv("WALLET_IPFS_UPLOAD_BACKEND") or "").strip().lower()
    if backend_mode == "mock":
        return _mock_ipfs_cid_for_bytes(data)
    if not _IPFS_BACKEND_AVAILABLE or get_ipfs_backend is None:
        raise RuntimeError("ipfs_datasets_py is required for IPFS upload")
    backend = get_ipfs_backend()
    return backend.add_bytes(data, pin=True)


def _mock_ipfs_cid_for_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return f"bafybeimock{digest[:24]}"


def _submit_ipfs_cid_to_filecoin_pin(
    cid: str,
    *,
    file_name: str | None = None,
    mime_type: str | None = None,
    source_record_id: str | None = None,
    wallet_id: str | None = None,
) -> dict[str, Any] | None:
    if not _filecoin_pin_service_url():
        return None

    origins = [
        origin.strip()
        for origin in str(os.getenv("WALLET_FILECOIN_PIN_ORIGINS") or "").split(",")
        if origin.strip()
    ]
    metadata: dict[str, str] = {"source": "211-ai-wallet"}
    if wallet_id:
        metadata["walletId"] = wallet_id
    if source_record_id:
        metadata["recordId"] = source_record_id
    if file_name:
        metadata["fileName"] = file_name
    if mime_type:
        metadata["mimeType"] = mime_type

    payload: dict[str, Any] = {
        "cid": cid,
        "meta": metadata,
    }
    if file_name:
        payload["name"] = file_name
    if origins:
        payload["origins"] = origins
    return _filecoin_pin_request("POST", "/pins", payload=payload)


def _fetch_filecoin_pin_status(request_id: str) -> dict[str, Any]:
    if not request_id.strip():
        raise ValueError("request ID is required")
    return _filecoin_pin_request("GET", f"/pins/{request_id}")


def _filecoin_pin_request(method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    service_url = _filecoin_pin_service_url()
    if not service_url:
        raise FilecoinPinHandoffError("WALLET_FILECOIN_PIN_SERVICE_URL is not configured")
    if service_url == "mock":
        return _mock_filecoin_pin_request(method, path, payload=payload)

    endpoint = f"{service_url}{path}"
    body = json.dumps(payload, sort_keys=True).encode("utf-8") if payload is not None else None
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers=_filecoin_pin_request_headers(include_json_content_type=payload is not None),
        method=method,
    )
    try:
        with urllib_request.urlopen(req, timeout=_filecoin_pin_timeout_seconds()) as response:
            raw = response.read().decode("utf-8")
            content_type = str(getattr(response, "headers", {}).get("content-type", ""))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        detail = _response_message_from_raw_json(error_body) or f"Filecoin Pin sidecar rejected the request with HTTP {exc.code}"
        raise FilecoinPinHandoffError(detail) from exc
    except urllib_error.URLError as exc:
        raise FilecoinPinHandoffError(f"Unable to reach Filecoin Pin sidecar at {endpoint}: {exc.reason}") from exc

    if not raw:
        return {}
    if "json" not in content_type.lower() and not raw.lstrip().startswith("{"):
        raise FilecoinPinHandoffError("Filecoin Pin sidecar returned a non-JSON response")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise FilecoinPinHandoffError("Filecoin Pin sidecar returned a non-object response")
    return parsed


def _filecoin_pin_service_url() -> str:
    return str(os.getenv("WALLET_FILECOIN_PIN_SERVICE_URL") or "").strip().rstrip("/")


def _filecoin_pin_mock_status() -> str:
    return str(os.getenv("WALLET_FILECOIN_PIN_MOCK_STATUS") or "pinned").strip() or "pinned"


def _mock_filecoin_pin_request(method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_method = str(method or "").strip().upper()
    normalized_path = str(path or "").strip()

    if normalized_method == "POST" and normalized_path == "/pins":
        cid = str((payload or {}).get("cid") or "").strip()
        if not cid:
            raise FilecoinPinHandoffError("mock Filecoin Pin request requires a cid")
        request_id = f"mock-pin-{hashlib.sha256(cid.encode('utf-8')).hexdigest()[:12]}"
        return {
            "requestid": request_id,
            "status": "queued",
            "info": {
                "provider": "mock-filecoin-pin",
                "cid": cid,
                "mock": True,
            },
        }

    if normalized_method == "GET" and normalized_path.startswith("/pins/"):
        request_id = normalized_path.rsplit("/", 1)[-1].strip()
        if not request_id:
            raise FilecoinPinHandoffError("mock Filecoin Pin status requires a request ID")
        return {
            "requestid": request_id,
            "status": _filecoin_pin_mock_status(),
            "info": {
                "provider": "mock-filecoin-pin",
                "mock": True,
                "pieceCid": f"baga6ea4seaq{hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:16]}",
            },
        }

    raise FilecoinPinHandoffError(f"mock Filecoin Pin does not support {normalized_method} {normalized_path}")


def _filecoin_pin_timeout_seconds() -> float:
    timeout_seconds = float(str(os.getenv("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS") or "30").strip())
    if timeout_seconds <= 0:
        raise FilecoinPinHandoffError("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS must be positive")
    return timeout_seconds


def _filecoin_pin_request_headers(*, include_json_content_type: bool) -> dict[str, str]:
    request_headers: dict[str, str] = {}
    if include_json_content_type:
        request_headers["content-type"] = "application/json"
    if bearer_token := str(os.getenv("WALLET_FILECOIN_PIN_BEARER_TOKEN") or "").strip():
        request_headers["authorization"] = f"Bearer {bearer_token}"
    if header_name := str(os.getenv("WALLET_FILECOIN_PIN_HTTP_HEADER_NAME") or "").strip():
        header_value = str(os.getenv("WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE") or "").strip()
        if not header_value:
            raise FilecoinPinHandoffError(
                "WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE is required when WALLET_FILECOIN_PIN_HTTP_HEADER_NAME is set"
            )
        request_headers[header_name] = header_value
    return request_headers


def _response_message_from_raw_json(raw: str) -> str:
    if not raw.strip():
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()
    if not isinstance(parsed, dict):
        return raw.strip()
    return str(parsed.get("error") or parsed.get("message") or "").strip()


def _filecoin_pin_status_url(request_id: str) -> str:
    service_url = _filecoin_pin_service_url()
    return f"{service_url}/pins/{request_id}" if service_url else ""


def _filecoin_upload_status_url(request_id: str) -> str:
    return f"/filecoin-upload/status/{request_id}"


def _key_from_optional_hex(value: str | None) -> bytes | None:
    if value is None:
        return None
    key = bytes.fromhex(value)
    if len(key) != 32:
        raise ValueError("wallet key must decode to 32 bytes")
    return key


def _send_dead_drop_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    bundle: dict[str, Any],
    bundle_filename: str,
) -> dict[str, Any]:
    normalized_to_email = str(to_email or "").strip()
    normalized_subject = str(subject or "").strip()
    normalized_body = str(body or "")
    bundle_json = json.dumps(bundle, indent=2, sort_keys=True)
    sender = str(os.getenv("WALLET_DEAD_DROP_FROM_EMAIL") or "no-reply@211-ai.org").strip()

    webhook_url = str(os.getenv("WALLET_DEAD_DROP_WEBHOOK_URL") or "").strip()
    backend = str(os.getenv("WALLET_DEAD_DROP_BACKEND") or ("http" if webhook_url else "")).strip().lower()
    if backend or webhook_url:
        if backend != "http" or not webhook_url:
            raise RuntimeError(
                "WALLET_DEAD_DROP_WEBHOOK_URL environment variable is required for dead-drop delivery when WALLET_DEAD_DROP_BACKEND is enabled"
            )
        delivery = _send_webhook_notification(
            env_prefix="WALLET_DEAD_DROP",
            required_key="to_email",
            required_value=normalized_to_email,
            extra_payload={
                "subject": normalized_subject,
                "body": normalized_body,
                "from_email": sender,
                "attachment_base64": base64.b64encode(bundle_json.encode("utf-8")).decode("ascii"),
                "attachment_filename": str(bundle_filename or "abby-missing-person-wallet-dead-drop.json"),
                "attachment_mime_type": "application/json",
            },
        )
        return {"message_id": str(delivery.get("provider_message_id") or "")}

    smtp_host = str(os.getenv("WALLET_DEAD_DROP_SMTP_HOST") or "").strip()
    if not smtp_host:
        raise RuntimeError(
            "WALLET_DEAD_DROP_SMTP_HOST environment variable is required for dead-drop email delivery but is not configured"
        )
    smtp_port = int(str(os.getenv("WALLET_DEAD_DROP_SMTP_PORT") or "587").strip())
    smtp_use_ssl = str(os.getenv("WALLET_DEAD_DROP_SMTP_USE_SSL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    smtp_starttls = str(os.getenv("WALLET_DEAD_DROP_SMTP_STARTTLS") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    smtp_username = str(os.getenv("WALLET_DEAD_DROP_SMTP_USERNAME") or "").strip()
    smtp_password = str(os.getenv("WALLET_DEAD_DROP_SMTP_PASSWORD") or "")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = normalized_to_email
    message["Subject"] = normalized_subject
    sender_domain = sender.rsplit("@", 1)[-1].strip() if "@" in sender else ""
    message["Message-Id"] = make_msgid(domain=sender_domain or None)
    message.set_content(normalized_body)
    message.add_attachment(
        bundle_json.encode("utf-8"),
        maintype="application",
        subtype="json",
        filename=bundle_filename,
    )

    smtp_factory = smtplib.SMTP_SSL if smtp_use_ssl else smtplib.SMTP
    with smtp_factory(smtp_host, smtp_port, timeout=20) as smtp:
        if not smtp_use_ssl and smtp_starttls:
            smtp.starttls()
        if smtp_username:
            smtp.login(smtp_username, smtp_password)
        rejected = smtp.send_message(message)
    if rejected:
        raise RuntimeError(f"Dead-drop email delivery rejected recipients: {sorted(rejected)}")
    return {"message_id": str(message.get("Message-Id") or "")}
