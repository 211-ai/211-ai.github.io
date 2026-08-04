#!/usr/bin/env python3
"""Build deterministic slotted-DAG → action-link projection (VOICE-ACTION-005).

Projects the 12 Abby slotted-response-DAG routes into a content-plane
``ActionLinkDocument`` (schema ``voice-action/action-link@1``).  The mapping is
a fixed deployment table: tool-adjacent / proposal-eligible routes name pilot
logical actions; content-only routes emit ``no_action`` with no frames.

The rebuild is pure and offline.  Given fixed inputs it is byte-stable.

Usage:
  python scripts/build_slotted_response_action_links.py
  python scripts/build_slotted_response_action_links.py --check
  python scripts/build_slotted_response_action_links.py --write
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
for _import_root in (REPO_ROOT, IPFS_DATASETS_ROOT):
    _path = str(_import_root)
    if _import_root.is_dir() and _path not in sys.path:
        sys.path.insert(0, _path)

from ipfs_datasets_py.voice.action_links import (  # noqa: E402
    NO_ACTION,
    ActionLink,
    ActionLinkDocument,
    parse_action_link_document,
)

TASK_ID: Final = "VOICE-ACTION-005"
SOURCE_LABEL: Final = "voice-action-005/slotted-response-action-links"

SLOTTED_DAG_REL: Final = "docs/phone_dialog_generation/slotted_response_dag.json"
DEFAULT_OUTPUT_REL: Final = (
    "docs/phone_dialog_generation/slotted_response_action_links.json"
)
DEFAULT_OUTPUT = REPO_ROOT / DEFAULT_OUTPUT_REL
DEFAULT_SLOTTED_DAG = REPO_ROOT / SLOTTED_DAG_REL

# Outcome roles emitted for proposal-eligible and safety-overlay links.
_OUTCOME_ROLES: Final = (
    "success",
    "denied",
    "failed",
    "cancelled",
    "unknown",
)

# Fixed route → (classification, logical_action) deployment map.
# Matches docs/voice_action_dag/BASELINE_INVENTORY.md and route-gap-matrix.
# content-only → no_action; others → pilot logical actions.
ROUTE_ACTION_PROJECTION: Final[dict[str, dict[str, str]]] = {
    "app_surface_navigation": {
        "classification": "proposal-eligible",
        "logical_action": "open_app_surface",
        "notes": "Pilot app/UI surface navigation proposal",
    },
    "calendar_event_support": {
        "classification": "proposal-eligible",
        "logical_action": "open_calendar_support",
        "notes": "Pilot calendar support proposal",
    },
    "clarifying_prompt": {
        "classification": "content-only",
        "logical_action": NO_ACTION,
        "notes": "Slot collection has no side-effect proposal",
    },
    "grounded_211_answer": {
        "classification": "proposal-eligible",
        "logical_action": "open_service_detail",
        "notes": "Optional service-detail open from grounded answer",
    },
    "live_agent": {
        "classification": "proposal-eligible",
        "logical_action": "handoff_live_agent",
        "notes": "Never claim transfer success without provider receipt",
    },
    "provider_contact_support": {
        "classification": "proposal-eligible",
        "logical_action": "provide_provider_contact",
        "notes": "Pilot provider contact / messaging proposal",
    },
    "repeat_or_restate": {
        "classification": "content-only",
        "logical_action": NO_ACTION,
        "notes": "Repeat/restate is speech-only",
    },
    "safety_guardrail_support": {
        "classification": "safety-overlay",
        "logical_action": "escalate_safety",
        "notes": "Safety overlay may propose escalate_safety under policy",
    },
    "service_interaction_support": {
        "classification": "proposal-eligible",
        "logical_action": "review_service_interaction",
        "notes": "Pilot service-interaction review proposal",
    },
    "speech_unclear_clarification": {
        "classification": "content-only",
        "logical_action": NO_ACTION,
        "notes": "Speech clarification is content-only",
    },
    "template_guided_fallback": {
        "classification": "content-only",
        "logical_action": NO_ACTION,
        "notes": "Safe template fallback is content-only",
    },
    "wallet_document_support": {
        "classification": "proposal-eligible",
        "logical_action": "open_wallet_documents",
        "notes": "Pilot wallet document surface proposal",
    },
}

# Routes that already have a voice_bridge tool-adjacent mapping (5 pilot tools).
TOOL_ADJACENT_ROUTES: Final = frozenset(
    {
        "app_surface_navigation",
        "wallet_document_support",
        "calendar_event_support",
        "service_interaction_support",
        "provider_contact_support",
    }
)

CONTENT_ONLY_ROUTES: Final = frozenset(
    route
    for route, spec in ROUTE_ACTION_PROJECTION.items()
    if spec["classification"] == "content-only"
)

EXPECTED_ROUTE_COUNT: Final = 12


class BuildError(RuntimeError):
    """Fail-closed rebuild / check error."""


def _confirmation_frame_id(logical_action: str) -> str:
    return f"frame.action.confirm.{logical_action}.v1"


def _outcome_frame_ids(logical_action: str) -> dict[str, str]:
    return {
        role: f"frame.action.outcome.{logical_action}.{role}.v1"
        for role in _OUTCOME_ROLES
    }


def build_action_link(route: str, spec: Mapping[str, str]) -> ActionLink:
    """Build one normalized ActionLink for *route* from the fixed projection."""

    classification = spec["classification"]
    logical_action = spec["logical_action"]
    notes = spec.get("notes")
    if classification == "content-only":
        return ActionLink(
            route=route,
            logical_action=NO_ACTION,
            classification="content-only",
            notes=notes,
        )
    return ActionLink(
        route=route,
        logical_action=logical_action,
        classification=classification,
        confirmation_frame_id=_confirmation_frame_id(logical_action),
        outcome_frame_ids=_outcome_frame_ids(logical_action),
        notes=notes,
    )


def load_slotted_route_names(dag_path: Path) -> tuple[str, ...]:
    """Return sorted route names from the slotted DAG summary (fail closed)."""

    if not dag_path.is_file():
        raise BuildError(f"missing slotted DAG: {dag_path}")
    try:
        payload = json.loads(dag_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"failed to read slotted DAG: {exc}") from exc
    if not isinstance(payload, dict):
        raise BuildError("slotted DAG root must be an object")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise BuildError("slotted DAG summary missing")
    route_counts = summary.get("routeCounts")
    if not isinstance(route_counts, dict) or not route_counts:
        raise BuildError("slotted DAG summary.routeCounts missing or empty")
    names = sorted(str(name) for name in route_counts if str(name))
    if not names:
        raise BuildError("slotted DAG has no route names")
    return tuple(names)


def build_action_link_document(
    *,
    routes: Sequence[str] | None = None,
    source: str = SOURCE_LABEL,
) -> ActionLinkDocument:
    """Project routes into a sorted, content-addressed ActionLinkDocument."""

    route_list = list(routes) if routes is not None else sorted(ROUTE_ACTION_PROJECTION)
    missing_map = [route for route in route_list if route not in ROUTE_ACTION_PROJECTION]
    if missing_map:
        raise BuildError(
            "no projection for route(s): " + ", ".join(sorted(missing_map))
        )
    # Always emit the full fixed table so the artifact is self-contained even if
    # the live DAG gains/loses routes; callers may pass DAG routes to assert set
    # equality separately.
    projected_routes = sorted(ROUTE_ACTION_PROJECTION)
    links = tuple(
        build_action_link(route, ROUTE_ACTION_PROJECTION[route])
        for route in projected_routes
    )
    return ActionLinkDocument(links=links, source=source)


def link_export_dict(link: ActionLink) -> dict[str, Any]:
    """Export one link for the on-disk projection (semantic fields only).

    ``link_id`` is omitted from the committed artifact so the file is a pure
    deployment map; parsers recompute the content-addressed id on load.  This
    keeps the rebuild recipe free of derived digests while remaining schema-
    compatible (``link_id`` is optional and verified when present).
    """

    payload: dict[str, Any] = {
        "classification": link.classification,
        "logical_action": link.logical_action,
        "route": link.route,
        "schema": link.schema,
        "schema_version": link.schema_version,
    }
    if link.confirmation_frame_id is not None:
        payload["confirmation_frame_id"] = link.confirmation_frame_id
    if link.outcome_frame_ids:
        payload["outcome_frame_ids"] = dict(link.outcome_frame_ids)
    if link.evidence_cids:
        payload["evidence_cids"] = list(link.evidence_cids)
    if link.notes is not None:
        payload["notes"] = link.notes
    return payload


def document_payload(document: ActionLinkDocument) -> dict[str, Any]:
    """JSON-serializable projection document (byte-stable export shape)."""

    payload: dict[str, Any] = {
        "links": [link_export_dict(link) for link in document.links],
        "schema": document.schema,
        "schema_version": document.schema_version,
        "source": document.source,
    }
    return payload


def serialize_document(document: ActionLinkDocument) -> str:
    """Return the byte-stable UTF-8 text written to disk (trailing newline)."""

    # Pretty-printed, key-sorted JSON is stable across runs and readable in docs/.
    text = json.dumps(
        document_payload(document),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    )
    return text + "\n"


def build_projection_text(
    *,
    dag_path: Path | None = None,
    require_dag_routes: bool = True,
) -> str:
    """Rebuild the projection artifact text from fixed inputs."""

    if require_dag_routes:
        path = dag_path or DEFAULT_SLOTTED_DAG
        dag_routes = load_slotted_route_names(path)
        projected = frozenset(ROUTE_ACTION_PROJECTION)
        dag_set = frozenset(dag_routes)
        if projected != dag_set:
            only_map = sorted(projected - dag_set)
            only_dag = sorted(dag_set - projected)
            parts: list[str] = []
            if only_map:
                parts.append("projection-only: " + ", ".join(only_map))
            if only_dag:
                parts.append("dag-only: " + ", ".join(only_dag))
            raise BuildError(
                "route set mismatch between projection table and slotted DAG ("
                + "; ".join(parts)
                + ")"
            )
        if len(dag_routes) != EXPECTED_ROUTE_COUNT:
            raise BuildError(
                f"expected {EXPECTED_ROUTE_COUNT} routes, found {len(dag_routes)}"
            )
    document = build_action_link_document()
    # Fail closed: re-parse the serialized form before emitting.
    parse_action_link_document(document_payload(document))
    return serialize_document(document)


def write_projection(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check_projection(path: Path, text: str) -> None:
    if not path.is_file():
        raise BuildError(f"missing projection artifact: {path}")
    existing = path.read_text(encoding="utf-8")
    if existing != text:
        raise BuildError(
            f"projection drift detected for {path}: rebuild is not byte-identical "
            f"(disk={len(existing)} bytes, rebuild={len(text)} bytes; "
            f"disk_digest={_sha_prefix(existing)}, rebuild_digest={_sha_prefix(text)})"
        )
    # Validate on-disk document still parses under the schema.
    parse_action_link_document(json.loads(existing))


def _sha_prefix(text: str, n: int = 12) -> str:
    from hashlib import sha256

    return sha256(text.encode("utf-8")).hexdigest()[:n]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or check the deterministic slotted DAG action-link projection "
            f"({TASK_ID})."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT_REL})",
    )
    parser.add_argument(
        "--slotted-dag",
        type=Path,
        default=DEFAULT_SLOTTED_DAG,
        help=f"Slotted response DAG path (default: {SLOTTED_DAG_REL})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Rebuild and require the on-disk artifact to match byte-for-byte",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the rebuilt artifact (default when --check is not set)",
    )
    parser.add_argument(
        "--skip-dag-route-check",
        action="store_true",
        help="Do not require the projection route set to match the slotted DAG",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.check and not args.write:
        # Default mode: write the artifact.
        args.write = True

    try:
        text = build_projection_text(
            dag_path=args.slotted_dag,
            require_dag_routes=not args.skip_dag_route_check,
        )
        if args.check:
            check_projection(args.output, text)
            print(
                f"{TASK_ID} --check OK "
                f"({EXPECTED_ROUTE_COUNT} routes, {len(text)} bytes, "
                f"digest={_sha_prefix(text)})"
            )
        if args.write:
            write_projection(args.output, text)
            print(
                f"{TASK_ID} wrote {args.output} "
                f"({EXPECTED_ROUTE_COUNT} routes, {len(text)} bytes)"
            )
    except BuildError as exc:
        print(f"{TASK_ID} FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"{TASK_ID} FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
