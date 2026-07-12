"""Route factory for ai router endpoints."""

from __future__ import annotations

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
    HTTPException = None  # type: ignore[assignment]
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
from ..schemas import (
    AddTextDocumentRequest,
    WalletEmbeddingsRouterRequest,
    WalletLlmRouterRequest,
    WalletMultimodalRouterRequest,
)


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
    ) -> dict[str, Any]:
        try:
            reference_audio = await audio.read() if audio is not None else None
            reference_name = getattr(audio, "filename", None) if audio is not None else None
            reference_type = getattr(audio, "content_type", None) if audio is not None else None
            reply_text, generation_latency = _run_indextts_with_endpoint_retry(
                "infer-generate",
                lambda: _generate_indextts_voice_reply_text(
                    mode=mode,
                    text=text,
                    system_prompt=system_prompt or systemPrompt,
                    user_prompt=user_prompt or userPrompt,
                    fallback_text=fallback_text or fallbackText,
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
