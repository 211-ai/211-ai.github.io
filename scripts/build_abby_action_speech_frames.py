#!/usr/bin/env python3
"""Author Abby confirmation and outcome speech frames for pilot actions.

VOICE-ACTION-024 / VOICE-ACTION-G120

Builds a deterministic JSONL corpus of content-plane speech frames for every
211-AI pilot logical action.  Each action receives confirm / success / deny /
fail spoken texts that are:

- slot-safe (no placeholders, or only simple named slots without format specs);
- free of executable / locator content (INV-CONTENT-001);
- marked ``generate_required`` until VOICE-ACTION-025 stages audio rows.

Frame IDs align with the action-link projection:

- ``frame.action.confirm.<logical_action>.v1``
- ``frame.action.outcome.<logical_action>.success.v1``
- ``frame.action.outcome.<logical_action>.denied.v1``  (role ``deny``)
- ``frame.action.outcome.<logical_action>.failed.v1``   (role ``fail``)

Usage:
  python scripts/build_abby_action_speech_frames.py
  python scripts/build_abby_action_speech_frames.py --check
  python scripts/build_abby_action_speech_frames.py --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from string import Formatter
from typing import Any, Final

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "ipfs_accelerate_py"
for _import_root in (REPO_ROOT, IPFS_ACCELERATE_ROOT):
    _path = str(_import_root)
    if _import_root.is_dir() and _path not in sys.path:
        sys.path.insert(0, _path)

TASK_ID: Final = "VOICE-ACTION-024"
SOURCE_LABEL: Final = "voice-action-024/abby-action-speech-frames"
SCHEMA: Final = "voice-action/action-speech-frame@1"
SCHEMA_VERSION: Final = "abby_action_speech_frame_v1"

DEFAULT_OUTPUT_REL: Final = "docs/phone_dialog_generation/action_speech_frames.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / DEFAULT_OUTPUT_REL
CATALOG_JSON_REL: Final = "data/voice_action_dag/catalog/211ai-pilot-v1.json"
DEFAULT_CATALOG_JSON = REPO_ROOT / CATALOG_JSON_REL

# Required spoken roles for acceptance (confirm + three outcome roles).
REQUIRED_ROLES: Final[tuple[str, ...]] = ("confirm", "success", "deny", "fail")

# Role → outcome suffix used in frame.action.outcome.* frame ids.
# confirm uses the separate confirmation frame id namespace.
_OUTCOME_ROLE_SUFFIX: Final[Mapping[str, str]] = {
    "success": "success",
    "deny": "denied",
    "fail": "failed",
}

# Content-plane ban list aligned with INV-CONTENT-001 / action-link schema.
FORBIDDEN_CONTENT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "command",
        "argv",
        "executable",
        "shell",
        "cwd",
        "env",
        "import",
        "import_path",
        "url",
        "credentials",
        "secret",
        "webhook",
        "host",
        "port",
        "binary",
        "module",
        "entrypoint",
    }
)

# Optional: only these simple slot names are allowed if a template needs one.
# Pilot frames intentionally use zero slots so precomputed audio can exact-match.
ALLOWED_SLOT_NAMES: Final[frozenset[str]] = frozenset(
    {
        "surface_name",
        "service_name",
        "provider_name",
    }
)

_LOGICAL_ACTION_RE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_FRAME_ID_RE = re.compile(r"^frame\.action\.(confirm|outcome)\.[a-z0-9_.]+$")
_PATH_SUFFIX = "_path"

# Fallback pilot set when the catalog module / JSON cannot be imported (still
# matches catalog_211ai.PILOT_LOGICAL_ACTIONS / supervisor pilot_logical_actions).
_FALLBACK_PILOT_LOGICAL_ACTIONS: Final[tuple[str, ...]] = (
    "handoff_live_agent",
    "open_app_surface",
    "open_wallet_documents",
    "read_calendar",
    "create_calendar_reminder",
    "read_provider_messages",
    "leave_provider_message",
    "open_service_detail",
    "schedule_service_callback",
    "escalate_safety",
)

# Authored spoken texts: fixed (slot-free) for exact-match audio readiness.
# Handoff / safety success texts never claim unverified transfer completion.
_SPEECH_TEXTS: Final[Mapping[str, Mapping[str, str]]] = {
    "handoff_live_agent": {
        "confirm": (
            "I can request a live specialist for you. "
            "Say yes to submit the handoff request, or no to cancel."
        ),
        "success": (
            "Your request to speak with a live specialist has been submitted. "
            "I will not treat the transfer as complete until a provider confirms it."
        ),
        "deny": (
            "Okay, I will not request a live specialist right now. "
            "We can continue here, or you can ask again later."
        ),
        "fail": (
            "I could not complete the live specialist request just now. "
            "Please try again, or stay on the line for more options."
        ),
    },
    "open_app_surface": {
        "confirm": (
            "I can open that app screen for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I opened the requested app screen.",
        "deny": "Okay, I will not open that app screen.",
        "fail": (
            "I could not open that app screen right now. "
            "Please try again in a moment."
        ),
    },
    "open_wallet_documents": {
        "confirm": (
            "I can open your wallet documents for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I opened your wallet documents.",
        "deny": "Okay, I will not open your wallet documents.",
        "fail": (
            "I could not open your wallet documents right now. "
            "Please try again in a moment."
        ),
    },
    "read_calendar": {
        "confirm": (
            "I can read your calendar for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I finished reading your calendar.",
        "deny": "Okay, I will not read your calendar.",
        "fail": (
            "I could not read your calendar right now. "
            "Please try again in a moment."
        ),
    },
    "create_calendar_reminder": {
        "confirm": (
            "I can create a calendar reminder for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I created the calendar reminder.",
        "deny": "Okay, I will not create that calendar reminder.",
        "fail": (
            "I could not create that calendar reminder right now. "
            "Please try again in a moment."
        ),
    },
    "read_provider_messages": {
        "confirm": (
            "I can read your provider messages for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I finished reading your provider messages.",
        "deny": "Okay, I will not read your provider messages.",
        "fail": (
            "I could not read your provider messages right now. "
            "Please try again in a moment."
        ),
    },
    "leave_provider_message": {
        "confirm": (
            "I can leave a message for the provider. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I left the message for the provider.",
        "deny": "Okay, I will not leave a message for the provider.",
        "fail": (
            "I could not leave a message for the provider right now. "
            "Please try again in a moment."
        ),
    },
    "open_service_detail": {
        "confirm": (
            "I can open the service details for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I opened the service details.",
        "deny": "Okay, I will not open the service details.",
        "fail": (
            "I could not open the service details right now. "
            "Please try again in a moment."
        ),
    },
    "schedule_service_callback": {
        "confirm": (
            "I can schedule a service callback for you. "
            "Say yes to continue, or no to cancel."
        ),
        "success": "I scheduled the service callback request.",
        "deny": "Okay, I will not schedule a service callback.",
        "fail": (
            "I could not schedule the service callback right now. "
            "Please try again in a moment."
        ),
    },
    "escalate_safety": {
        "confirm": (
            "For your safety, I can escalate this to emergency or specialist support. "
            "Say yes if you want me to start that escalation now."
        ),
        "success": (
            "I started the safety escalation request. "
            "If you are in immediate danger, call nine one one now."
        ),
        "deny": (
            "Okay, I will not start a safety escalation from here. "
            "If you are in immediate danger, call nine one one now."
        ),
        "fail": (
            "I could not complete the safety escalation request just now. "
            "If you are in immediate danger, call nine one one now."
        ),
    },
}


class BuildError(RuntimeError):
    """Fail-closed rebuild / check error."""


def load_pilot_logical_actions(
    catalog_path: Path | None = None,
) -> tuple[str, ...]:
    """Return the stable pilot logical-action set (catalog first, then fallback)."""

    try:
        from ipfs_accelerate_py.action_runtime.catalog_211ai import (  # type: ignore
            PILOT_LOGICAL_ACTIONS,
        )

        actions = tuple(str(item) for item in PILOT_LOGICAL_ACTIONS)
        if actions:
            return actions
    except Exception:
        pass

    path = catalog_path or DEFAULT_CATALOG_JSON
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BuildError(f"failed to read pilot catalog: {exc}") from exc
        if isinstance(payload, Mapping):
            raw = payload.get("logical_actions")
            if isinstance(raw, list) and raw:
                actions = tuple(str(item) for item in raw if str(item).strip())
                if actions:
                    return actions
            descriptors = payload.get("descriptors")
            if isinstance(descriptors, list) and descriptors:
                names = sorted(
                    {
                        str(row.get("logical_action") or "").strip()
                        for row in descriptors
                        if isinstance(row, Mapping)
                        and str(row.get("logical_action") or "").strip()
                    }
                )
                if names:
                    return tuple(names)

    return _FALLBACK_PILOT_LOGICAL_ACTIONS


def confirmation_frame_id(logical_action: str) -> str:
    return f"frame.action.confirm.{logical_action}.v1"


def outcome_frame_id(logical_action: str, role: str) -> str:
    suffix = _OUTCOME_ROLE_SUFFIX.get(role)
    if suffix is None:
        raise BuildError(f"role {role!r} has no outcome frame suffix")
    return f"frame.action.outcome.{logical_action}.{suffix}.v1"


def frame_id_for(logical_action: str, role: str) -> str:
    if role == "confirm":
        return confirmation_frame_id(logical_action)
    return outcome_frame_id(logical_action, role)


def extract_slot_names(spoken_text: str) -> tuple[str, ...]:
    """Parse ``{slot}`` placeholders; reject unsafe format-string features."""

    names: list[str] = []
    try:
        for _, name, format_spec, conversion in Formatter().parse(spoken_text):
            if name is None:
                continue
            if not name or format_spec or conversion or "." in name or "[" in name:
                raise BuildError(
                    f"unsafe placeholder {name!r} in spoken text "
                    f"(format_spec={format_spec!r}, conversion={conversion!r})"
                )
            names.append(name)
    except ValueError as exc:
        raise BuildError(f"invalid braces in spoken text: {exc}") from exc
    return tuple(sorted(set(names)))


def assert_slot_safe(spoken_text: str, *, frame_id: str) -> tuple[str, ...]:
    slots = extract_slot_names(spoken_text)
    illegal = [name for name in slots if name not in ALLOWED_SLOT_NAMES]
    if illegal:
        raise BuildError(
            f"frame {frame_id} uses disallowed slot names: {', '.join(illegal)}"
        )
    return slots


def _reject_forbidden_key(key: str, *, path: str) -> None:
    lowered = key.casefold()
    if lowered in FORBIDDEN_CONTENT_FIELDS:
        raise BuildError(f"forbidden content field {key!r} at {path}")
    if lowered.endswith(_PATH_SUFFIX):
        raise BuildError(f"path-smuggling key {key!r} at {path}")


def reject_forbidden_content_fields(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key)
            child = f"{path}.{name}"
            _reject_forbidden_key(name, path=child)
            reject_forbidden_content_fields(item, path=child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_forbidden_content_fields(item, path=f"{path}[{index}]")


def normalize_spoken_text(text: str) -> str:
    return " ".join(str(text).split()).strip()


def build_frame_record(
    *,
    logical_action: str,
    role: str,
    spoken_text: str,
    source: str = SOURCE_LABEL,
) -> dict[str, Any]:
    if not _LOGICAL_ACTION_RE.match(logical_action):
        raise BuildError(f"invalid logical_action: {logical_action!r}")
    if role not in REQUIRED_ROLES:
        raise BuildError(f"invalid role: {role!r}")
    text = normalize_spoken_text(spoken_text)
    if not text:
        raise BuildError(f"empty spoken_text for {logical_action}/{role}")
    frame_id = frame_id_for(logical_action, role)
    if not _FRAME_ID_RE.match(frame_id):
        raise BuildError(f"invalid frame_id: {frame_id!r}")
    slots = assert_slot_safe(text, frame_id=frame_id)
    record: dict[str, Any] = {
        "audio_status": "generate_required",
        "frame_id": frame_id,
        "logical_action": logical_action,
        "role": role,
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "slot_names": list(slots),
        "source": source,
        "spoken_text": text,
        "task_id": TASK_ID,
    }
    reject_forbidden_content_fields(record)
    return record


def authored_speech_table() -> Mapping[str, Mapping[str, str]]:
    return _SPEECH_TEXTS


def build_frame_records(
    *,
    logical_actions: Sequence[str] | None = None,
    speech_table: Mapping[str, Mapping[str, str]] | None = None,
    source: str = SOURCE_LABEL,
) -> list[dict[str, Any]]:
    """Build sorted frame records for every pilot action × required role."""

    actions = tuple(logical_actions) if logical_actions is not None else load_pilot_logical_actions()
    table = speech_table if speech_table is not None else authored_speech_table()

    missing_actions = [name for name in actions if name not in table]
    if missing_actions:
        raise BuildError(
            "missing speech texts for logical action(s): "
            + ", ".join(sorted(missing_actions))
        )

    extra = sorted(set(table) - set(actions))
    if extra:
        raise BuildError(
            "speech table has non-pilot logical action(s): " + ", ".join(extra)
        )

    records: list[dict[str, Any]] = []
    for action in sorted(actions):
        role_map = table[action]
        missing_roles = [role for role in REQUIRED_ROLES if role not in role_map]
        if missing_roles:
            raise BuildError(
                f"logical action {action!r} missing role(s): "
                + ", ".join(missing_roles)
            )
        for role in REQUIRED_ROLES:
            records.append(
                build_frame_record(
                    logical_action=action,
                    role=role,
                    spoken_text=role_map[role],
                    source=source,
                )
            )

    # Stable order: logical_action, then role order in REQUIRED_ROLES.
    role_rank = {role: index for index, role in enumerate(REQUIRED_ROLES)}
    records.sort(key=lambda row: (row["logical_action"], role_rank[row["role"]]))
    return records


def serialize_frames(records: Sequence[Mapping[str, Any]]) -> str:
    """Return byte-stable JSONL text (one object per line, trailing newline)."""

    lines: list[str] = []
    for record in records:
        reject_forbidden_content_fields(record)
        lines.append(
            json.dumps(
                dict(record),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


def build_corpus_text(
    *,
    logical_actions: Sequence[str] | None = None,
    speech_table: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    records = build_frame_records(
        logical_actions=logical_actions,
        speech_table=speech_table,
    )
    return serialize_frames(records)


def parse_corpus_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BuildError(f"malformed JSONL at line {line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise BuildError(f"JSONL row must be an object at line {line_number}")
        rows.append(payload)
    return rows


def validate_corpus_records(
    records: Sequence[Mapping[str, Any]],
    *,
    logical_actions: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Fail-closed validation; returns a coverage report dict."""

    actions = (
        tuple(logical_actions)
        if logical_actions is not None
        else load_pilot_logical_actions()
    )
    action_set = set(actions)
    seen: dict[tuple[str, str], str] = {}
    generate_required = 0
    slot_counts: dict[str, int] = {}

    if not records:
        raise BuildError("corpus is empty")

    for index, row in enumerate(records):
        reject_forbidden_content_fields(row, path=f"$[{index}]")
        schema = str(row.get("schema") or "")
        if schema != SCHEMA:
            raise BuildError(f"row {index}: unexpected schema {schema!r}")
        schema_version = str(row.get("schema_version") or "")
        if schema_version != SCHEMA_VERSION:
            raise BuildError(
                f"row {index}: unexpected schema_version {schema_version!r}"
            )
        logical_action = str(row.get("logical_action") or "")
        role = str(row.get("role") or "")
        frame_id = str(row.get("frame_id") or "")
        spoken_text = str(row.get("spoken_text") or "")
        audio_status = str(row.get("audio_status") or "")
        if logical_action not in action_set:
            raise BuildError(f"row {index}: non-pilot logical_action {logical_action!r}")
        if role not in REQUIRED_ROLES:
            raise BuildError(f"row {index}: invalid role {role!r}")
        expected_id = frame_id_for(logical_action, role)
        if frame_id != expected_id:
            raise BuildError(
                f"row {index}: frame_id {frame_id!r} != expected {expected_id!r}"
            )
        slots = assert_slot_safe(spoken_text, frame_id=frame_id)
        declared = row.get("slot_names")
        if not isinstance(declared, list):
            raise BuildError(f"row {index}: slot_names must be a list")
        if tuple(str(item) for item in declared) != slots:
            raise BuildError(
                f"row {index}: slot_names {declared!r} do not match text slots {list(slots)!r}"
            )
        if audio_status not in {"generate_required", "ready", "staged"}:
            raise BuildError(f"row {index}: invalid audio_status {audio_status!r}")
        if audio_status == "generate_required":
            generate_required += 1
        key = (logical_action, role)
        if key in seen:
            raise BuildError(
                f"duplicate frame for {logical_action}/{role}: "
                f"{seen[key]} and {frame_id}"
            )
        seen[key] = frame_id
        for slot in slots:
            slot_counts[slot] = slot_counts.get(slot, 0) + 1

    missing: list[str] = []
    complete_actions = 0
    for action in sorted(action_set):
        roles_present = {role for (la, role) in seen if la == action}
        if roles_present >= set(REQUIRED_ROLES):
            complete_actions += 1
        else:
            absent = sorted(set(REQUIRED_ROLES) - roles_present)
            missing.append(f"{action}: missing {', '.join(absent)}")

    if missing:
        raise BuildError(
            "incomplete pilot coverage: " + "; ".join(missing)
        )

    report = {
        "schema": "voice-action/action-speech-coverage@1",
        "task_id": TASK_ID,
        "pilot_action_count": len(action_set),
        "complete_action_count": complete_actions,
        "frame_count": len(records),
        "required_roles": list(REQUIRED_ROLES),
        "roles_per_action": len(REQUIRED_ROLES),
        "generate_required_count": generate_required,
        "slot_name_counts": dict(sorted(slot_counts.items())),
        "slot_free_frame_count": sum(
            1 for row in records if not list(row.get("slot_names") or [])
        ),
        "logical_actions": sorted(action_set),
        "complete": complete_actions == len(action_set)
        and len(records) == len(action_set) * len(REQUIRED_ROLES),
    }
    if not report["complete"]:
        raise BuildError(f"coverage incomplete: {report}")
    return report


def coverage_report_text(report: Mapping[str, Any]) -> str:
    return (
        f"{TASK_ID} coverage: "
        f"{report['complete_action_count']}/{report['pilot_action_count']} actions complete; "
        f"{report['frame_count']} frames; "
        f"roles={','.join(report['required_roles'])}; "
        f"generate_required={report['generate_required_count']}; "
        f"slot_free={report['slot_free_frame_count']}"
    )


def write_corpus(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check_corpus(path: Path, text: str) -> None:
    if not path.is_file():
        raise BuildError(f"missing speech-frame corpus: {path}")
    existing = path.read_text(encoding="utf-8")
    if existing != text:
        raise BuildError(
            f"corpus drift detected for {path}: rebuild is not byte-identical "
            f"(disk={len(existing)} bytes, rebuild={len(text)} bytes; "
            f"disk_digest={_sha_prefix(existing)}, rebuild_digest={_sha_prefix(text)})"
        )
    validate_corpus_records(parse_corpus_text(existing))


def _sha_prefix(text: str, n: int = 12) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:n]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or check Abby confirmation/outcome speech frames for pilot "
            f"actions ({TASK_ID})."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT_REL})",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_JSON,
        help=f"Pilot catalog JSON (default: {CATALOG_JSON_REL})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Rebuild and require the on-disk corpus to match byte-for-byte",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the rebuilt corpus (default when --check is not set)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.check and not args.write:
        args.write = True

    try:
        actions = load_pilot_logical_actions(args.catalog)
        text = build_corpus_text(logical_actions=actions)
        records = parse_corpus_text(text)
        report = validate_corpus_records(records, logical_actions=actions)
        print(coverage_report_text(report))
        if args.check:
            check_corpus(args.output, text)
            print(
                f"{TASK_ID} --check OK "
                f"({report['frame_count']} frames, {len(text)} bytes, "
                f"digest={_sha_prefix(text)})"
            )
        if args.write:
            write_corpus(args.output, text)
            print(
                f"{TASK_ID} wrote {args.output} "
                f"({report['frame_count']} frames, {len(text)} bytes)"
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
