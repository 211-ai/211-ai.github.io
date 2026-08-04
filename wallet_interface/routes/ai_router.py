"""Route factory for ai router endpoints."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any
from urllib import error as urllib_error

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]
    Body = None  # type: ignore[assignment]
    File = None  # type: ignore[assignment]
    Form = None  # type: ignore[assignment]
    class HTTPException(Exception):  # type: ignore[assignment]
        def __init__(self, status_code: int = 500, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    UploadFile = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..helpers import (
    _check_wallet_router_rate_limit,
    _generate_indextts_voice_reply_text,
    _indextts_degraded_error_payload,
    _key_from_optional_hex,
    _prepare_hf_router_environment,
    _require_wallet_router_actor,
    _run_hf_whisper_stt,
    _run_indextts_gradio_batch_tts,
    _run_indextts_tts_with_batch_fallback,
    _run_indextts_with_endpoint_retry,
    _silent_wav_bytes,
    _wallet_router_subject,
)
from ..helpers._voice_router_adapter import (
    is_unified_voice_router_enabled,
    process_wallet_voice_turn,
)
from ..schemas import (
    AddTextDocumentRequest,
    WalletEmbeddingsRouterRequest,
    WalletLlmRouterRequest,
    WalletMultimodalRouterRequest,
)


def _text_form_value(value: object | None) -> str | None:
    """Normalize optional form text; empty strings become ``None``."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_mapping_form_field(value: object | None) -> dict[str, Any] | None:
    """Parse optional JSON object form fields (GraphRAG / template metadata)."""

    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, Mapping):
        return None
    return dict(parsed)


def _route_from_template_metadata(metadata: Mapping[str, Any] | None) -> str | None:
    """Extract a slotted-DAG route from GraphRAG / template metadata."""

    if not isinstance(metadata, Mapping):
        return None
    for key in ("route", "response_route"):
        route = _text_form_value(metadata.get(key))
        if route is not None:
            return route
    nested = metadata.get("template_metadata") or metadata.get("response_template")
    if isinstance(nested, Mapping):
        for key in ("route", "response_route"):
            route = _text_form_value(nested.get(key))
            if route is not None:
                return route
    return None


def _resolve_infer_route(
    *,
    route: object | None = None,
    response_route: object | None = None,
    template_metadata: Mapping[str, Any] | None = None,
) -> str | None:
    """Resolve the response-DAG route for the unified voice infer path.

    Prefer explicit form fields (``route`` / ``response_route``), then fall back
    to GraphRAG / template metadata so browser and proxy clients can pass the
    slotted-DAG route without inventing executable authority.
    """

    direct = _text_form_value(route) or _text_form_value(response_route)
    if direct is not None:
        return direct
    return _route_from_template_metadata(template_metadata)


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/wallets/{wallet_id}/ai-router/embeddings")
    def proxy_wallet_embeddings_router(
        wallet_id: str,
        request: WalletEmbeddingsRouterRequest,
    ) -> dict[str, Any]:
        try:
            _require_wallet_router_actor(app_service, wallet_id, request.actor_did)
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid, cost=max(1, len(request.texts) or 1))
            texts = list(request.texts or [])
            if request.text:
                texts.insert(0, request.text)
            if not texts:
                raise ValueError("text or texts is required")
            kwargs = _prepare_hf_router_environment(request.kwargs)
            from ipfs_datasets_py import embeddings_router  # noqa: WPS433

            embeddings = [
                embeddings_router.embed_text(
                    text,
                    model_name=request.model_name,
                    provider=request.provider,
                    **kwargs,
                )
                for text in texts
            ]
            return {
                "router": "embeddings_router",
                "wallet_id": wallet_id,
                "wallet_cid": wallet_cid,
                "provider": request.provider,
                "model_name": request.model_name,
                "rate_limit": limit,
                "embeddings": embeddings,
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/ai-router/llm")
    def proxy_wallet_llm_router(
        wallet_id: str,
        request: WalletLlmRouterRequest,
    ) -> dict[str, Any]:
        try:
            _require_wallet_router_actor(app_service, wallet_id, request.actor_did)
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid)
            prompt = request.prompt
            if request.system_prompt:
                prompt = f"system: {request.system_prompt}\nuser: {request.prompt}"
            kwargs = _prepare_hf_router_environment(request.kwargs)
            from ipfs_datasets_py import llm_router  # noqa: WPS433

            if request.max_new_tokens is not None:
                kwargs.setdefault("max_new_tokens", request.max_new_tokens)
            model_name = request.model_name or os.getenv("WALLET_AI_ROUTER_LLM_MODEL", "Qwen/Qwen3.5-2B")
            text = llm_router.generate_text(
                prompt,
                model_name=model_name,
                provider=request.provider,
                **kwargs,
            )
            return {
                "router": "llm_router",
                "wallet_id": wallet_id,
                "wallet_cid": wallet_cid,
                "provider": request.provider,
                "model_name": model_name,
                "rate_limit": limit,
                "text": text,
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/ai-router/multimodal")
    def proxy_wallet_multimodal_router(
        wallet_id: str,
        request: WalletMultimodalRouterRequest,
    ) -> dict[str, Any]:
        try:
            _require_wallet_router_actor(app_service, wallet_id, request.actor_did)
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid)
            kwargs = _prepare_hf_router_environment(request.kwargs)
            from ipfs_datasets_py import multimodal_router  # noqa: WPS433

            if request.max_new_tokens is not None:
                kwargs.setdefault("max_new_tokens", request.max_new_tokens)
            model_name = request.model_name or os.getenv("WALLET_AI_ROUTER_MULTIMODAL_MODEL")
            text = multimodal_router.generate_multimodal_text(
                request.prompt,
                model_name=model_name,
                provider=request.provider,
                image_urls=request.image_urls,
                system_prompt=None,
                additional_text_blocks=request.additional_text_blocks,
                messages=request.messages or None,
                image_detail=request.image_detail,
                **kwargs,
            )
            return {
                "router": "multimodal_router",
                "wallet_id": wallet_id,
                "wallet_cid": wallet_cid,
                "provider": request.provider,
                "model_name": model_name,
                "rate_limit": limit,
                "text": text,
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


    @router.post("/voice/indextts/tts")
    def indextts_voice_tts(
        text: str = Form(default=""),
        voice_description: str | None = Form(default=None),
    ) -> dict[str, Any]:
        try:
            audio = _run_indextts_with_endpoint_retry(
                "tts",
                lambda: _run_indextts_tts_with_batch_fallback(
                    text=text,
                    voice_description=voice_description,
                ),
            )
            return audio
        except Exception as exc:
            raise HTTPException(status_code=503, detail=_indextts_degraded_error_payload(exc, "tts")) from exc


    @router.post("/voice/indextts/batch")
    def indextts_voice_batch(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            raw_texts = payload.get("texts") if isinstance(payload, Mapping) else None
            if isinstance(raw_texts, str):
                texts = [raw_texts]
            elif isinstance(raw_texts, Sequence):
                texts = [str(item) for item in raw_texts if str(item or "").strip()]
            else:
                texts = []
            audio = _run_indextts_with_endpoint_retry(
                "batch",
                lambda: _run_indextts_gradio_batch_tts(
                    texts=texts,
                    voice_description=str(payload.get("voice_description") or payload.get("voiceDescription") or "")
                    if isinstance(payload, Mapping)
                    else "",
                ),
            )
            return audio
        except Exception as exc:
            raise HTTPException(status_code=503, detail=_indextts_degraded_error_payload(exc, "batch")) from exc


    @router.post("/voice/indextts/infer")
    async def indextts_voice_infer(
        audio: UploadFile | None = File(default=None),
        mode: str = Form(default=""),
        text: str = Form(default=""),
        systemPrompt: str | None = Form(default=None),
        system_prompt: str | None = Form(default=None),
        userPrompt: str | None = Form(default=None),
        user_prompt: str | None = Form(default=None),
        fallbackText: str | None = Form(default=None),
        fallback_text: str | None = Form(default=None),
        voice_description: str | None = Form(default=None),
        # Slotted response-DAG route (from GraphRAG / template metadata or UI).
        route: str | None = Form(default=None),
        response_route: str | None = Form(default=None),
        # Optional JSON object carrying GraphRAG / template metadata with a route.
        template_metadata: str | None = Form(default=None),
        templateMetadata: str | None = Form(default=None),
        # Dual-gate confirm: explicit per-request flag; execute still requires operator flag.
        confirm_action: str | None = Form(default=None),
        action_confirm: str | None = Form(default=None),
        request_id: str | None = Form(default=None),
        requestId: str | None = Form(default=None),
    ) -> dict[str, Any]:
        try:
            reference_audio = await audio.read() if audio is not None else None
            reference_name = getattr(audio, "filename", None) if audio is not None else None
            reference_type = getattr(audio, "content_type", None) if audio is not None else None
            resolved_user_prompt = user_prompt or userPrompt
            resolved_fallback = fallback_text or fallbackText
            resolved_confirm = confirm_action or action_confirm
            parsed_template_metadata = _parse_mapping_form_field(
                template_metadata or templateMetadata
            )
            resolved_route = _resolve_infer_route(
                route=route,
                response_route=response_route,
                template_metadata=parsed_template_metadata,
            )

            # Staged unified router: when enabled, return the canonical voice
            # receipt (including fail-closed action proposal/decision/receipt).
            # When the flag is off, form route/confirm fields are ignored and the
            # legacy IndexTTS proxy path below remains unchanged.
            if is_unified_voice_router_enabled():
                envelope: dict[str, Any] = {
                    "mode": mode or "voice-reply",
                    "text": text or resolved_fallback or "",
                    "user_prompt": resolved_user_prompt or text or "",
                    "fallback_text": resolved_fallback or text or "",
                    "voice": voice_description,
                    "request_id": request_id or requestId,
                    "channel": "voice",
                }
                if resolved_route is not None:
                    envelope["route"] = resolved_route
                    envelope["response_route"] = resolved_route
                if parsed_template_metadata is not None:
                    # Preserve GraphRAG metadata for downstream extractors; route
                    # authority still comes only from resolved_route / provenance.
                    envelope["template_metadata"] = parsed_template_metadata
                    envelope["context"] = {
                        **dict(envelope.get("context") or {}),
                        "template_metadata": parsed_template_metadata,
                        **(
                            {"route": resolved_route}
                            if resolved_route is not None
                            else {}
                        ),
                    }
                if resolved_confirm is not None:
                    # Pass confirm only when the client set it so dual-gate
                    # evaluation matches attach_action_surface expectations.
                    envelope["confirm_action"] = resolved_confirm
                    envelope["action_confirm"] = resolved_confirm
                if reference_audio:
                    envelope["audio_bytes"] = reference_audio
                unified = process_wallet_voice_turn(envelope, enabled=True)
                if unified is not None:
                    # Preserve legacy text field for older proxy clients.
                    if "text" not in unified and unified.get("response_text"):
                        unified = dict(unified)
                        unified["text"] = unified.get("response_text")
                    return unified

            reply_text, generation_latency = _run_indextts_with_endpoint_retry(
                "infer-generate",
                lambda: _generate_indextts_voice_reply_text(
                    mode=mode,
                    text=text,
                    system_prompt=system_prompt or systemPrompt,
                    user_prompt=resolved_user_prompt,
                    fallback_text=resolved_fallback,
                ),
            )
            audio_payload = _run_indextts_with_endpoint_retry(
                "infer",
                lambda: _run_indextts_tts_with_batch_fallback(
                    text=reply_text,
                    voice_description=voice_description,
                    reference_audio=reference_audio,
                    reference_audio_name=reference_name,
                    reference_audio_mime_type=reference_type,
                ),
            )
            audio_payload["text"] = reply_text
            latency = dict(audio_payload.get("latency") or {})
            latency.update(generation_latency)
            audio_payload["latency"] = latency
            return audio_payload
        except Exception as exc:
            raise HTTPException(status_code=503, detail=_indextts_degraded_error_payload(exc, "infer")) from exc


    @router.post("/voice/hf-whisper/stt")
    async def hf_whisper_voice_stt(
        audio: UploadFile | None = File(default=None),
        model_name: str | None = Form(default=None),
        language: str | None = Form(default=None),
    ) -> dict[str, Any]:
        try:
            audio_bytes = await audio.read() if audio is not None else _silent_wav_bytes()
            audio_name = getattr(audio, "filename", None) if audio is not None else "preflight.wav"
            audio_type = getattr(audio, "content_type", None) if audio is not None else "audio/wav"
            return _run_hf_whisper_stt(
                audio_bytes,
                audio_name=audio_name,
                audio_type=audio_type,
                language=language,
                model_name=model_name,
            )
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip() or str(exc)
            raise HTTPException(status_code=502, detail=detail) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/documents/text")
    def add_text_document(wallet_id: str, request: AddTextDocumentRequest) -> dict[str, Any]:
        try:
            metadata = {"title": request.title} if request.title else {}
            record = app_service.add_text_document(
                wallet_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.key_hex),
                text=request.text,
                filename=request.filename,
                metadata=metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/documents")
    async def add_binary_document(
        wallet_id: str,
        actor_did: str = Form(...),
        key_hex: str | None = Form(default=None),
        title: str | None = Form(default=None),
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        try:
            metadata = {"title": title} if title else {}
            data = await file.read()
            record = app_service.add_binary_document(
                wallet_id,
                actor_did=actor_did,
                actor_secret=_key_from_optional_hex(key_hex),
                data=data,
                filename=file.filename or "document.bin",
                content_type=file.content_type,
                metadata=metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    return router
