# ruff: noqa: E501
"""Record and document-profile helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from ._ai_routing import _check_wallet_router_rate_limit


def _derived_output(result: Mapping[str, Any]) -> dict[str, Any]:
    output = result.get("output")
    return dict(output) if isinstance(output, Mapping) else {}


def _derived_artifact_id(result: Mapping[str, Any]) -> str:
    artifact = result.get("artifact")
    if hasattr(artifact, "artifact_id"):
        return str(getattr(artifact, "artifact_id") or "")
    if hasattr(artifact, "id"):
        return str(getattr(artifact, "id") or "")
    if isinstance(artifact, Mapping):
        return str(artifact.get("artifact_id") or artifact.get("id") or "")
    return ""


def _record_metadata_value(record: Mapping[str, Any], key: str) -> str:
    metadata = record.get("metadata")
    if isinstance(metadata, Mapping):
        value = metadata.get(key)
        if isinstance(value, str):
            return value
    return ""


def _safe_short_text(value: Any, *, limit: int = 240) -> str:
    text = str(value or "")
    text = re.sub(r"[^\s@]+@(?:[A-Z0-9\-]{1,63}\.){1,10}[A-Z]{2,10}", "[email]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b", "[phone]", text)
    text = re.sub(r"\b\d{4,}\b", "[number]", text)
    return text.strip()[:limit]


def _safe_organizer_signal(output: Mapping[str, Any]) -> dict[str, Any]:
    signal: dict[str, Any] = {
        "output_policy": _safe_short_text(output.get("output_policy")),
        "summary": _safe_short_text(output.get("summary")),
        "text": _safe_short_text(output.get("text")),
    }
    profile = output.get("profile")
    if isinstance(profile, Mapping):
        signal["profile"] = {
            key: profile.get(key)
            for key in ("profile_type", "chunk_count")
            if profile.get(key) is not None
        }
    graph = output.get("graph")
    if isinstance(graph, Mapping):
        signal["graph"] = {
            key: graph.get(key)
            for key in ("graph_type", "node_count", "edge_count")
            if graph.get(key) is not None
        }
    return {key: value for key, value in signal.items() if value not in ("", None, {})}


def _redacted_file_name(file_name: str) -> str:
    _, dot, extension = str(file_name or "").rpartition(".")
    return f"document.{extension.lower()}" if dot and extension else "document"


def _generate_wallet_organizer_profile(
    *,
    wallet_id: str,
    wallet_cid: str,
    file_name: str,
    mime_type: str,
    outputs: Sequence[Mapping[str, Any]],
    provider: str | None,
    model_name: str | None,
    kwargs: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    safe_signals = [_safe_organizer_signal(output) for output in outputs]
    safe_signals = [signal for signal in safe_signals if signal]
    if not safe_signals:
        return None
    try:
        _check_wallet_router_rate_limit(wallet_cid or wallet_id)
        from ipfs_datasets_py import llm_router  # noqa: WPS433

        prompt = "\n".join(
            [
                "Create privacy-preserving organizer metadata from redacted wallet document signals.",
                "Return only one JSON object with keys: summary, labels, browseHints, riskSignals.",
                "Use generic non-identifying language only.",
                json.dumps(
                    {
                        "fileName": _redacted_file_name(file_name),
                        "mimeType": mime_type,
                        "redactedSignals": safe_signals[:8],
                    },
                    sort_keys=True,
                ),
            ]
        )
        text = llm_router.generate_text(
            prompt,
            model_name=model_name,
            provider=provider or "hf_inference_api",
            **dict(kwargs or {}),
        )
        parsed = _parse_first_json_object(text)
        if not parsed:
            return None
        return {
            "summary": _safe_short_text(parsed.get("summary")),
            "labels": _read_string_list(parsed.get("labels"), limit=8),
            "browseHints": _read_string_list(parsed.get("browseHints"), limit=8),
            "riskSignals": _read_string_list(parsed.get("riskSignals"), limit=8),
            "model": model_name or provider or "wallet-router",
        }
    except Exception:
        return None


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    trimmed = str(text or "").strip()
    start = trimmed.find("{")
    end = trimmed.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(trimmed[start : end + 1])
    except Exception:
        return None
    return dict(parsed) if isinstance(parsed, Mapping) else None


def _read_string_list(value: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_short_text(item, limit=80) for item in value if _safe_short_text(item, limit=80)][:limit]


def _read_number(record: Mapping[str, Any] | None, key: str) -> int | float | None:
    if not isinstance(record, Mapping):
        return None
    value = record.get(key)
    return value if isinstance(value, int | float) else None


def _read_string(record: Mapping[str, Any] | None, key: str) -> str:
    if not isinstance(record, Mapping):
        return ""
    value = record.get(key)
    return str(value).strip() if isinstance(value, str) else ""


def _default_labels_for_mime_type(mime_type: str) -> list[str]:
    normalized = str(mime_type or "").lower()
    if normalized == "application/pdf":
        return ["pdf", "document"]
    if normalized.startswith("image/"):
        return ["image", "visual file"]
    if normalized.startswith("text/"):
        return ["text", "document"]
    if "json" in normalized:
        return ["json", "structured data"]
    if "spreadsheet" in normalized or "excel" in normalized or "csv" in normalized:
        return ["spreadsheet", "tabular data"]
    if "wordprocessing" in normalized or "msword" in normalized:
        return ["word document", "document"]
    if normalized.startswith("audio/"):
        return ["audio"]
    if normalized.startswith("video/"):
        return ["video"]
    return ["wallet file"]


def _display_mime_type(mime_type: str) -> str:
    normalized = str(mime_type or "").strip().lower()
    if not normalized:
        return "Unknown file"
    if normalized == "application/pdf":
        return "PDF document"
    if normalized.startswith("image/"):
        return f"{normalized.split('/', 1)[1].upper()} image"
    if normalized.startswith("text/"):
        return "Text document"
    if "json" in normalized:
        return "JSON data"
    if "spreadsheet" in normalized or "excel" in normalized or "csv" in normalized:
        return "Spreadsheet"
    if "wordprocessing" in normalized or "msword" in normalized:
        return "Word document"
    if normalized.startswith("audio/"):
        return "Audio file"
    if normalized.startswith("video/"):
        return "Video file"
    if normalized == "application/octet-stream":
        return "Encrypted/binary file"
    return normalized


def _fallback_document_profile_output(*, file_name: str, mime_type: str) -> dict[str, Any]:
    return {
        "output_policy": "local_metadata_only",
        "profile": {"chunk_count": 0, "profile_type": "metadata fallback"},
        "summary": f"{_display_mime_type(mime_type)} wallet file queued for redacted profiling.",
        "upload_state": {"fileName": _redacted_file_name(file_name), "mimeType": mime_type},
    }


def _build_document_profile_public_inputs(
    *,
    artifact_ids: Sequence[str],
    file_name: str,
    mime_type: str,
    outputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    graphs = [output.get("graph") for output in outputs]
    graph = next((item for item in graphs if isinstance(item, Mapping)), {})
    profiles = [output.get("profile") for output in outputs]
    profile = next((item for item in profiles if isinstance(item, Mapping)), {})
    organizer_profiles = [output.get("openrouter_organizer_profile") for output in outputs]
    organizer = next((item for item in organizer_profiles if isinstance(item, Mapping)), {})
    redaction_count = 0
    for output in outputs:
        counts = output.get("redaction_counts")
        if isinstance(counts, Mapping):
            redaction_count += sum(value for value in counts.values() if isinstance(value, int | float))
    public_mime_type = mime_type or "application/octet-stream"
    labels = _read_string_list(organizer.get("labels")) or _default_labels_for_mime_type(public_mime_type)
    return {
        "artifact_ids": list(artifact_ids),
        "chunk_count": _read_number(profile, "chunk_count"),
        "edge_count": _read_number(graph, "edge_count"),
        "file_name_profile": _redacted_file_name(file_name),
        "graph_type": _read_string(graph, "graph_type"),
        "mime_family": public_mime_type.split("/", 1)[0] or "application",
        "mime_type": public_mime_type,
        "node_count": _read_number(graph, "node_count"),
        "openrouter_model": _read_string(organizer, "model"),
        "organizer_labels": labels,
        "organizer_summary": _read_string(organizer, "summary") or _display_mime_type(public_mime_type),
        "output_policies": sorted({str(output.get("output_policy")) for output in outputs if output.get("output_policy")}),
        "privacy_policy": "no_plaintext_public_inputs",
        "profile_methods": sorted({str(output.get("output_policy")) for output in outputs if output.get("output_policy")}),
        "redaction_count": redaction_count,
        "size_bucket": "server-side",
        "summary": "Redacted GraphRAG, vector metadata, and derived descriptors created inside the wallet boundary.",
    }


def _classify_document_profile(public_inputs: Mapping[str, Any]) -> str:
    summary = _read_string(public_inputs, "organizer_summary")
    if summary:
        return summary
    labels = _read_string_list(public_inputs.get("organizer_labels"), limit=3)
    if labels:
        return ", ".join(labels[:3])
    return _display_mime_type(str(public_inputs.get("mime_type") or ""))


def _summarize_document_profile(public_inputs: Mapping[str, Any]) -> str:
    mime_type = str(public_inputs.get("mime_type") or "document")
    graph_type = str(public_inputs.get("graph_type") or "redacted graph")
    nodes = public_inputs.get("node_count")
    chunks = public_inputs.get("chunk_count")
    nodes_text = f"{nodes} nodes" if isinstance(nodes, int | float) else "safe graph"
    chunks_text = f"{chunks} chunks" if isinstance(chunks, int | float) else "vector metadata"
    return f"{mime_type} · {graph_type} · {nodes_text} · {chunks_text}"


def _build_privacy_search_text(outputs: Sequence[Mapping[str, Any]], public_inputs: Mapping[str, Any]) -> str:
    parts: list[str] = [
        _classify_document_profile(public_inputs),
        _summarize_document_profile(public_inputs),
        " ".join(_read_string_list(public_inputs.get("organizer_labels"), limit=12)),
        " ".join(str(policy) for policy in public_inputs.get("output_policies", []) if isinstance(policy, str)),
    ]
    for output in outputs:
        parts.append(_safe_short_text(output.get("summary")))
        parts.append(_safe_short_text(output.get("text")))
    return " ".join(part for part in parts if part).strip()


def _build_privacy_vector_terms(outputs: Sequence[Mapping[str, Any]], public_inputs: Mapping[str, Any]) -> list[str]:
    terms: list[str] = []
    terms.extend(_read_string_list(public_inputs.get("organizer_labels"), limit=12))
    for key in ("mime_type", "mime_family", "graph_type", "organizer_summary"):
        value = public_inputs.get(key)
        if isinstance(value, str) and value.strip():
            terms.append(value.strip())
    for output in outputs:
        policy = output.get("output_policy")
        if isinstance(policy, str) and policy.strip():
            terms.append(policy.strip())
    normalized: list[str] = []
    seen = set()
    for term in terms:
        safe = _safe_short_text(term, limit=80).lower()
        if safe and safe not in seen:
            normalized.append(safe)
            seen.add(safe)
    return normalized[:24]


