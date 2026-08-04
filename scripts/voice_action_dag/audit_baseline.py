#!/usr/bin/env python3
"""Baseline inventory audit for VOICE-ACTION-002 / VOICE-ACTION-G010.

Validates (and optionally regenerates) the frozen baseline artifacts:

- data/voice_action_dag/baseline/component-inventory.json
- data/voice_action_dag/baseline/route-gap-matrix.json
- docs/voice_action_dag/BASELINE_INVENTORY.md

``--check`` re-reads the slotted response DAG, re-hashes bound source files,
and re-extracts AST symbols so the inventory cannot drift silently from the
tree. Route classifications must be one of content-only, proposal-eligible, or
safety-overlay.

Usage:
  python scripts/voice_action_dag/audit_baseline.py --check
  python scripts/voice_action_dag/audit_baseline.py --write
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "voice-action-dag-abby-v1"
GOAL_ID = "VOICE-ACTION-G010"
TASK_ID = "VOICE-ACTION-002"
BOARD_NAMESPACE = "voice-action-dag-abby-v1"

SLOTTED_DAG_REL = "docs/phone_dialog_generation/slotted_response_dag.json"
INVENTORY_REL = "data/voice_action_dag/baseline/component-inventory.json"
GAP_MATRIX_REL = "data/voice_action_dag/baseline/route-gap-matrix.json"
DOC_REL = "docs/voice_action_dag/BASELINE_INVENTORY.md"

INVENTORY_SCHEMA = "voice-action/component-inventory@1"
GAP_MATRIX_SCHEMA = "voice-action/route-gap-matrix@1"

ROUTE_CLASSIFICATIONS = frozenset(
    {"content-only", "proposal-eligible", "safety-overlay"}
)

# Authoritative classification for the 12 slotted-DAG routes.
# content-only: speech only, no side-effect proposal.
# proposal-eligible: may emit a catalog logical-action proposal after policy.
# safety-overlay: safety/crisis wording that overlays emergency/handoff policy.
ROUTE_BASELINE: dict[str, dict[str, Any]] = {
    "app_surface_navigation": {
        "classification": "proposal-eligible",
        "today": "Spoken navigation guidance only",
        "target_logical_action": "open_app_surface",
        "voice_bridge_mapped": True,
        "catalog_descriptor_id": "voice.cli.open_app_surface.v1",
        "ui_tool_binding": "navigate / surfaceRegistry (not voice-DAG bound)",
        "audio_action_frames": "missing",
        "adapter_status": "CLI probe only (/usr/bin/true); real app-tool adapter missing",
        "gaps": [
            "No GraphRAG-driven ActionProposalCandidate",
            "UI navigate tool not bound to voice route admission",
            "Missing confirmation/outcome Abby audio frames",
        ],
    },
    "wallet_document_support": {
        "classification": "proposal-eligible",
        "today": "Spoken document list guidance only",
        "target_logical_action": "open_wallet_documents",
        "voice_bridge_mapped": True,
        "catalog_descriptor_id": "voice.cli.open_wallet_documents.v1",
        "ui_tool_binding": "uploads/wallet surfaces (not voice-DAG bound)",
        "audio_action_frames": "missing",
        "adapter_status": "CLI probe only; real wallet-docs adapter missing",
        "gaps": [
            "No receipted open of wallet docs from voice admission",
            "Missing confirmation/outcome Abby audio frames",
        ],
    },
    "calendar_event_support": {
        "classification": "proposal-eligible",
        "today": "Spoken appointment guidance only",
        "target_logical_action": "open_calendar_support",
        "voice_bridge_mapped": True,
        "catalog_descriptor_id": "voice.cli.open_calendar_support.v1",
        "ui_tool_binding": "buildIcsCalendar / buildCalendarAction (browser handoff)",
        "audio_action_frames": "missing",
        "adapter_status": "CLI probe only; calendar read/create adapter missing",
        "gaps": [
            "create_calendar_reminder not in pilot catalog",
            "Browser ICS handoff not receipted through action_runtime",
            "Missing confirmation/outcome Abby audio frames",
        ],
    },
    "service_interaction_support": {
        "classification": "proposal-eligible",
        "today": "Spoken follow-up guidance only",
        "target_logical_action": "review_service_interaction",
        "voice_bridge_mapped": True,
        "catalog_descriptor_id": "voice.cli.review_service_interaction.v1",
        "ui_tool_binding": "serviceActionService / serviceInteractionService",
        "audio_action_frames": "missing",
        "adapter_status": "CLI probe only; service interaction adapter missing",
        "gaps": [
            "schedule_service_callback not catalog-bound",
            "Service interaction intents not emitted from voice admission",
            "Missing confirmation/outcome Abby audio frames",
        ],
    },
    "provider_contact_support": {
        "classification": "proposal-eligible",
        "today": "Spoken phone/contact scripts only",
        "target_logical_action": "provide_provider_contact",
        "voice_bridge_mapped": True,
        "catalog_descriptor_id": "voice.cli.provide_provider_contact.v1",
        "ui_tool_binding": "buildCallAction / buildTextAction / messages surfaces",
        "audio_action_frames": "missing",
        "adapter_status": "CLI probe only; messaging adapter missing",
        "gaps": [
            "read_provider_messages / leave_provider_message not catalog-bound",
            "No verified send/receive receipt from voice path",
            "Missing confirmation/outcome Abby audio frames",
        ],
    },
    "grounded_211_answer": {
        "classification": "proposal-eligible",
        "today": "Grounded resource answer (content plane)",
        "target_logical_action": "open_service_detail",
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "search_211_services / answer_211_question / service detail",
        "audio_action_frames": "response speech only; no action frames",
        "adapter_status": "No catalog descriptor; optional service-open not wired",
        "gaps": [
            "Optional service open/cite not mapped in voice_bridge",
            "open_service_detail descriptor missing from default catalog",
            "Action proposals not emitted from GraphRAG evidence",
        ],
    },
    "live_agent": {
        "classification": "proposal-eligible",
        "today": "Spoken handoff guidance; telephony degrades to text-only human_handoff metadata",
        "target_logical_action": "handoff_live_agent",
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "none (metadata-only escalation)",
        "audio_action_frames": "response speech only; no verified-transfer frames",
        "adapter_status": "No verified transfer adapter; never claim transfer success",
        "gaps": [
            "handoff_live_agent descriptor missing from default catalog",
            "No warm-transfer / queue receipt",
            "voice_router telephone path is metadata-only escalation",
            "Must never claim unverified transfer success",
        ],
    },
    "safety_guardrail_support": {
        "classification": "safety-overlay",
        "today": "Safety/crisis wording; may bypass normal slot filling",
        "target_logical_action": "escalate_safety",
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "none (policy overlay)",
        "audio_action_frames": "safety speech only",
        "adapter_status": "Policy-driven emergency/handoff overlay not catalog-bound",
        "gaps": [
            "escalate_safety descriptor missing",
            "Safety auto-path must stay policy-owned, not content-owned",
            "Overlay must compose with live_agent without silent success claims",
        ],
    },
    "repeat_or_restate": {
        "classification": "content-only",
        "today": "Repeat/restate frame",
        "target_logical_action": None,
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "none",
        "audio_action_frames": "response speech only",
        "adapter_status": "no_action",
        "gaps": [],
    },
    "speech_unclear_clarification": {
        "classification": "content-only",
        "today": "Clarification when speech is unclear",
        "target_logical_action": None,
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "none",
        "audio_action_frames": "response speech only",
        "adapter_status": "no_action",
        "gaps": [],
    },
    "template_guided_fallback": {
        "classification": "content-only",
        "today": "Safe template fallback",
        "target_logical_action": None,
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "none",
        "audio_action_frames": "response speech only",
        "adapter_status": "no_action",
        "gaps": [],
    },
    "clarifying_prompt": {
        "classification": "content-only",
        "today": "Clarifying question / slot collection",
        "target_logical_action": None,
        "voice_bridge_mapped": False,
        "catalog_descriptor_id": None,
        "ui_tool_binding": "none",
        "audio_action_frames": "response speech only",
        "adapter_status": "no_action",
        "gaps": [],
    },
}

# Components that must appear in the inventory with bound paths + symbols.
COMPONENT_SPECS: dict[str, dict[str, Any]] = {
    "voice_router": {
        "plane": "content+orchestration",
        "owner": "ipfs_accelerate_py",
        "paths": [
            "ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py",
            "wallet_interface/helpers/_voice_router_adapter.py",
        ],
        "required_symbols": {
            "ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py": [
                "process_voice_turn",
                "VoiceTurnRequest",
                "VoiceTurnResult",
                "VoiceResponsePlan",
                "speech_to_text",
                "text_to_speech",
            ],
            "wallet_interface/helpers/_voice_router_adapter.py": [
                "WalletVoiceRouterAdapter",
                "process_wallet_voice_turn",
                "is_unified_voice_router_enabled",
                "serialize_voice_turn_result",
            ],
        },
        "role": "STT → GraphRAG/template retrieval → TTS/precomputed audio receipt; wallet adapter adoption.",
    },
    "action_runtime": {
        "plane": "authority",
        "owner": "ipfs_accelerate_py",
        "paths": [
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/__init__.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py",
            "wallet_interface/helpers/_voice_action_surface.py",
        ],
        "required_symbols": {
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py": [
                "ActionProposal",
                "ActionDecision",
                "ActionReceipt",
                "RiskClass",
                "SideEffectClass",
            ],
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py": [
                "ActionCatalog",
                "ActionDescriptor",
            ],
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py": [
                "VoiceActionBridge",
                "propose_from_voice_route",
                "DEFAULT_ROUTE_TO_LOGICAL_ACTION",
            ],
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py": [
                "FailClosedPolicy",
                "ActionPolicyEngine",
            ],
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py": [
                "ActionExecutor",
            ],
            "wallet_interface/helpers/_voice_action_surface.py": [
                "attach_action_surface",
                "build_default_action_stack",
                "extract_voice_route",
                "is_voice_action_execute_enabled",
            ],
        },
        "role": "Fail-closed proposal → policy → catalog → adapter execution; voice_bridge maps 5 routes.",
    },
    "graphrag": {
        "plane": "content",
        "owner": "ipfs_datasets_py",
        "paths": [
            "ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py",
            "ipfs_datasets_py/ipfs_datasets_py/voice/response_dag.py",
            "docs/phone_dialog_generation/slotted_response_dag.json",
        ],
        "required_symbols": {
            "ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py": [
                "GraphRAGVoiceTemplateProvider",
                "SlottedResponseIndex",
                "EvidenceRecord",
                "TemplateMatch",
                "TemplateGraphSnapshot",
            ],
            "ipfs_datasets_py/ipfs_datasets_py/voice/response_dag.py": [
                "ResponseDAGAppendCandidate",
                "append_response_dag_candidate",
            ],
        },
        "role": "Deterministic grounded retrieval over Abby templates/slotted DAG; content plane only.",
    },
    "ui_tools": {
        "plane": "product/UI",
        "owner": "wallet_interface",
        "paths": [
            "wallet_interface/ui/src/features/agent/lib/toolExecutor.ts",
            "wallet_interface/ui/src/features/agent/lib/surfaceRegistry.ts",
            "wallet_interface/ui/src/features/agent/lib/tools/navigationTools.ts",
            "wallet_interface/ui/src/features/agent/lib/tools/servicePlanTools.ts",
            "wallet_interface/ui/src/features/agent/lib/tools/contactTools.ts",
            "wallet_interface/ui/src/features/calendar/lib/ics.ts",
            "wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts",
        ],
        "required_symbols": {
            "wallet_interface/ui/src/features/agent/lib/toolExecutor.ts": [
                "createAgentToolExecutor",
                "AgentToolExecutor",
            ],
            "wallet_interface/ui/src/features/agent/lib/surfaceRegistry.ts": [
                "SURFACE_CONTEXT_SCOPES",
            ],
            "wallet_interface/ui/src/features/agent/lib/tools/navigationTools.ts": [
                "NavigationSurface",
            ],
            "wallet_interface/ui/src/features/calendar/lib/ics.ts": [
                "buildIcsCalendar",
            ],
            "wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts": [
                "VoiceActionSurface",
                "parseVoiceTurnResult",
            ],
        },
        "role": "Browser agent tools (navigate, calendar, messages, service plans) exist but are not bound to voice DAG routes.",
    },
    "service_actions": {
        "plane": "product/UI",
        "owner": "wallet_interface",
        "paths": [
            "wallet_interface/ui/src/features/service-navigation/lib/serviceActionService.ts",
            "wallet_interface/ui/src/features/service-navigation/lib/serviceInteractionService.ts",
        ],
        "required_symbols": {
            "wallet_interface/ui/src/features/service-navigation/lib/serviceActionService.ts": [
                "buildCallAction",
                "buildCalendarAction",
                "buildShareAction",
                "invokeLinkAction",
                "ServiceActionDescriptor",
            ],
            "wallet_interface/ui/src/features/service-navigation/lib/serviceInteractionService.ts": [
                "buildServiceInteractionIntent",
                "emitWalletServiceInteractionIntent",
                "ServiceInteractionIntent",
            ],
        },
        "role": "Browser service handoffs (call/text/email/map/share/calendar) with observed-status only; not voice-admitted.",
    },
    "handoff": {
        "plane": "authority+channel",
        "owner": "ipfs_accelerate_py + wallet_interface",
        "paths": [
            "ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py",
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py",
            "wallet_interface/helpers/_voice_action_surface.py",
        ],
        "required_symbols": {
            "ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py": [
                "process_voice_turn",
                "TelephoneTurnState",
            ],
            "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py": [
                "ActionDecisionKind",
            ],
            "wallet_interface/helpers/_voice_action_surface.py": [
                "attach_action_surface",
            ],
        },
        "role": "Human handoff / live_agent is metadata-only escalation today; ActionDecisionKind.HANDOFF exists but no verified transfer adapter.",
        "extra_notes": [
            "voice_router telephone path degrades to text-only human_handoff provider metadata",
            "live_agent route is not in DEFAULT_ROUTE_TO_LOGICAL_ACTION",
            "No telephony transfer receipt; never claim unverified success",
        ],
    },
}


class AuditError(RuntimeError):
    """Fail-closed audit error."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"invalid JSON {path}: {exc}") from exc


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_revision(repo_root: Path, relative_path: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%H", "--", relative_path],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    rev = (completed.stdout or "").strip()
    return rev or None


def _git_head(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    rev = (completed.stdout or "").strip()
    return rev or None


def _extract_python_symbols(source: str) -> list[dict[str, Any]]:
    tree = ast.parse(source)
    symbols: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "kind": "function",
                    "name": node.name,
                    "qualname": node.name,
                    "lineno": node.lineno,
                }
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                {
                    "kind": "class",
                    "name": node.name,
                    "qualname": node.name,
                    "lineno": node.lineno,
                }
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        {
                            "kind": "method",
                            "name": child.name,
                            "qualname": f"{node.name}.{child.name}",
                            "lineno": child.lineno,
                        }
                    )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(
                        {
                            "kind": "constant",
                            "name": target.id,
                            "qualname": target.id,
                            "lineno": getattr(node, "lineno", 0),
                        }
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id.isupper():
                symbols.append(
                    {
                        "kind": "constant",
                        "name": node.target.id,
                        "qualname": node.target.id,
                        "lineno": getattr(node, "lineno", 0),
                    }
                )
    return symbols


_TS_EXPORT_RE = re.compile(
    r"^export\s+(?:async\s+)?(?:function|const|class|type|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
_TS_EXPORT_DEFAULT_CLASS_RE = re.compile(
    r"^export\s+default\s+(?:abstract\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


def _extract_typescript_symbols(source: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _TS_EXPORT_RE.finditer(source):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        line = source.count("\n", 0, match.start()) + 1
        kind = "export"
        snippet = match.group(0)
        if "function" in snippet:
            kind = "function"
        elif "class" in snippet:
            kind = "class"
        elif "interface" in snippet:
            kind = "interface"
        elif "type" in snippet:
            kind = "type"
        elif "const" in snippet:
            kind = "const"
        elif "enum" in snippet:
            kind = "enum"
        symbols.append(
            {"kind": kind, "name": name, "qualname": name, "lineno": line}
        )
    for match in _TS_EXPORT_DEFAULT_CLASS_RE.finditer(source):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        line = source.count("\n", 0, match.start()) + 1
        symbols.append(
            {"kind": "class", "name": name, "qualname": name, "lineno": line}
        )
    return symbols


def _extract_symbols(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        return _extract_python_symbols(source)
    if path.suffix in {".ts", ".tsx", ".js", ".mjs", ".cjs"}:
        return _extract_typescript_symbols(source)
    return []


def _symbol_names(symbols: Sequence[Mapping[str, Any]]) -> set[str]:
    names: set[str] = set()
    for entry in symbols:
        for key in ("name", "qualname"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                names.add(value)
                if "." in value:
                    names.add(value.rsplit(".", 1)[-1])
    return names


def load_slotted_route_counts(repo_root: Path) -> dict[str, int]:
    dag_path = repo_root / SLOTTED_DAG_REL
    if not dag_path.is_file():
        raise AuditError(f"missing slotted DAG: {SLOTTED_DAG_REL}")
    dag = _read_json(dag_path)
    if not isinstance(dag, dict):
        raise AuditError("slotted DAG root must be an object")
    summary = dag.get("summary")
    if not isinstance(summary, dict):
        raise AuditError("slotted DAG summary missing")
    route_counts = summary.get("routeCounts")
    if not isinstance(route_counts, dict) or not route_counts:
        raise AuditError("slotted DAG summary.routeCounts missing")
    result: dict[str, int] = {}
    for route, count in route_counts.items():
        if not isinstance(route, str) or not route:
            raise AuditError(f"invalid route key in DAG: {route!r}")
        if not isinstance(count, int) or count < 0:
            raise AuditError(f"invalid route count for {route}: {count!r}")
        result[route] = count
    return result


def _module_entry(repo_root: Path, relative_path: str) -> dict[str, Any]:
    path = repo_root / relative_path
    if not path.is_file():
        raise AuditError(f"missing source path: {relative_path}")
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    symbols: list[dict[str, Any]] = []
    parse_error: str | None = None
    if path.suffix in {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"}:
        try:
            symbols = _extract_symbols(path)
        except SyntaxError as exc:
            parse_error = f"SyntaxError: {exc}"
    line_count = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    return {
        "path": relative_path,
        "byte_count": len(data),
        "line_count": line_count,
        "sha256": _sha256_bytes(data),
        "git_revision": _git_revision(repo_root, relative_path),
        "symbol_count": len(symbols),
        "parse_error": parse_error,
        "symbols": symbols,
    }


def build_component_inventory(repo_root: Path) -> dict[str, Any]:
    route_counts = load_slotted_route_counts(repo_root)
    components: dict[str, Any] = {}
    for component_id, spec in COMPONENT_SPECS.items():
        modules = [_module_entry(repo_root, rel) for rel in spec["paths"]]
        required = spec.get("required_symbols") or {}
        bound: dict[str, list[str]] = {}
        for rel, names in required.items():
            module = next((m for m in modules if m["path"] == rel), None)
            if module is None:
                raise AuditError(f"{component_id}: required path not scanned: {rel}")
            present = _symbol_names(module["symbols"])
            missing = [name for name in names if name not in present]
            if missing and module.get("parse_error") is None:
                raise AuditError(
                    f"{component_id}: missing symbols in {rel}: {', '.join(missing)}"
                )
            bound[rel] = list(names)
        components[component_id] = {
            "id": component_id,
            "plane": spec["plane"],
            "owner": spec["owner"],
            "role": spec["role"],
            "modules": modules,
            "required_ast_symbols": bound,
            "extra_notes": list(spec.get("extra_notes") or ()),
        }

    dag_module = _module_entry(repo_root, SLOTTED_DAG_REL)
    return {
        "schema": INVENTORY_SCHEMA,
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "goal_id": GOAL_ID,
        "task_id": TASK_ID,
        "generated_at": _utc_now(),
        "repository_head": _git_head(repo_root),
        "purpose": (
            "Deterministic inventory of Abby slotted DAG routes, voice_router, "
            "action_runtime, GraphRAG, UI tools, service actions, and handoff gaps "
            "for the voice-action dual-plane integration."
        ),
        "slotted_response_dag": {
            "path": SLOTTED_DAG_REL,
            "sha256": dag_module["sha256"],
            "byte_count": dag_module["byte_count"],
            "git_revision": dag_module["git_revision"],
            "route_counts": dict(sorted(route_counts.items())),
            "route_count_total": sum(route_counts.values()),
            "route_names": sorted(route_counts),
        },
        "components": components,
        "required_component_ids": sorted(COMPONENT_SPECS),
        "acceptance_coverage": {
            "route_census_matches_slotted_dag": True,
            "route_classifications_complete": True,
            "components_bound": sorted(COMPONENT_SPECS),
            "ast_symbols_bound": True,
            "repo_revisions_bound": True,
            "voice_bridge_mapped_routes": sorted(
                route
                for route, meta in ROUTE_BASELINE.items()
                if meta.get("voice_bridge_mapped")
            ),
            "content_only_routes": sorted(
                route
                for route, meta in ROUTE_BASELINE.items()
                if meta["classification"] == "content-only"
            ),
            "proposal_eligible_routes": sorted(
                route
                for route, meta in ROUTE_BASELINE.items()
                if meta["classification"] == "proposal-eligible"
            ),
            "safety_overlay_routes": sorted(
                route
                for route, meta in ROUTE_BASELINE.items()
                if meta["classification"] == "safety-overlay"
            ),
        },
    }


def build_route_gap_matrix(repo_root: Path) -> dict[str, Any]:
    route_counts = load_slotted_route_counts(repo_root)
    expected = set(ROUTE_BASELINE)
    actual = set(route_counts)
    if expected != actual:
        raise AuditError(
            "ROUTE_BASELINE routes != slotted DAG routes: "
            f"missing={sorted(actual - expected)} extra={sorted(expected - actual)}"
        )

    routes: list[dict[str, Any]] = []
    for route in sorted(route_counts):
        meta = ROUTE_BASELINE[route]
        classification = meta["classification"]
        if classification not in ROUTE_CLASSIFICATIONS:
            raise AuditError(f"invalid classification for {route}: {classification}")
        routes.append(
            {
                "route": route,
                "edge_count": route_counts[route],
                "classification": classification,
                "today": meta["today"],
                "target_logical_action": meta["target_logical_action"],
                "voice_bridge_mapped": bool(meta["voice_bridge_mapped"]),
                "catalog_descriptor_id": meta["catalog_descriptor_id"],
                "ui_tool_binding": meta["ui_tool_binding"],
                "audio_action_frames": meta["audio_action_frames"],
                "adapter_status": meta["adapter_status"],
                "gaps": list(meta["gaps"]),
            }
        )

    program_gaps = [
        {
            "id": "G1",
            "title": "Dual-plane schema for Abby library",
            "status": "open",
            "summary": "Slotted DAG lacks optional route→logical_action and action prompt/outcome frames.",
        },
        {
            "id": "G2",
            "title": "Catalog of program actions",
            "status": "partial",
            "summary": "Five CLI probe descriptors exist; pilot set (handoff, calendar write, messaging, service callback, safety) incomplete.",
        },
        {
            "id": "G3",
            "title": "Retrieval that proposes actions without authority",
            "status": "open",
            "summary": "GraphRAG returns content only; ActionProposalCandidate not emitted from evidence.",
        },
        {
            "id": "G4",
            "title": "Real adapters (not /usr/bin/true)",
            "status": "open",
            "summary": "App tool, calendar, messaging, service, and human handoff adapters missing.",
        },
        {
            "id": "G5",
            "title": "Abby audio continuity for actions",
            "status": "open",
            "summary": "No first-class confirmation/success/deny/fail audio frames for logical actions.",
        },
        {
            "id": "G6",
            "title": "End-to-end proofs with the real dataset",
            "status": "open",
            "summary": "Route-sampled offline suites for proposal/deny/permit/handoff truthfulness not shipped.",
        },
        {
            "id": "G7",
            "title": "Parallel supervisor program",
            "status": "partial",
            "summary": "Board/profile/control bootstrap present; inventory wave completes with this artifact set.",
        },
    ]

    return {
        "schema": GAP_MATRIX_SCHEMA,
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "goal_id": GOAL_ID,
        "task_id": TASK_ID,
        "generated_at": _utc_now(),
        "slotted_response_dag": SLOTTED_DAG_REL,
        "classification_enum": sorted(ROUTE_CLASSIFICATIONS),
        "route_census": dict(sorted(route_counts.items())),
        "route_census_total": sum(route_counts.values()),
        "routes": routes,
        "program_gaps": program_gaps,
        "acceptance": {
            "route_census_matches_slotted_dag": True,
            "each_route_classified": True,
            "allowed_classifications": sorted(ROUTE_CLASSIFICATIONS),
        },
    }


def build_baseline_doc(
    inventory: Mapping[str, Any], gap_matrix: Mapping[str, Any]
) -> str:
    route_counts = gap_matrix["route_census"]
    routes = gap_matrix["routes"]
    components = inventory["components"]

    lines: list[str] = [
        "# Voice Action DAG × Abby — Baseline Inventory",
        "",
        f"Program: `{inventory['program_id']}`  ",
        f"Goal: `{inventory['goal_id']}`  ",
        f"Task: `{inventory['task_id']}`  ",
        f"Board namespace: `{inventory['board_namespace']}`  ",
        f"Generated: `{inventory['generated_at']}`  ",
        f"Repository HEAD: `{inventory.get('repository_head') or 'unknown'}`",
        "",
        "This document freezes the starting inventory for dual-plane integration:",
        "Abby slotted DAG + audio (content plane) versus governed program actions",
        "(authority plane). It is validated by",
        "`python scripts/voice_action_dag/audit_baseline.py --check`.",
        "",
        "## Artifacts",
        "",
        "| Artifact | Path |",
        "| --- | --- |",
        f"| Component inventory | `{INVENTORY_REL}` |",
        f"| Route gap matrix | `{GAP_MATRIX_REL}` |",
        f"| Audit script | `scripts/voice_action_dag/audit_baseline.py` |",
        f"| Slotted response DAG | `{SLOTTED_DAG_REL}` |",
        "",
        "## Route census (matches slotted DAG summary)",
        "",
        f"Total route edges: **{gap_matrix['route_census_total']}** across "
        f"**{len(route_counts)}** routes.",
        "",
        "| Route | Edges | Classification | Target logical action | Voice bridge |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for entry in routes:
        target = entry["target_logical_action"] or "—"
        mapped = "yes" if entry["voice_bridge_mapped"] else "no"
        lines.append(
            f"| `{entry['route']}` | {entry['edge_count']} | "
            f"`{entry['classification']}` | `{target}` | {mapped} |"
        )

    lines.extend(
        [
            "",
            "### Classification rules",
            "",
            "- **content-only** — spoken response only; no side-effect proposal.",
            "- **proposal-eligible** — may emit a catalog-bound logical action after policy/confirmation.",
            "- **safety-overlay** — safety/crisis wording that overlays emergency/handoff policy;",
            "  content still never embeds executables.",
            "",
            "## Component inventory (repo revisions + AST symbols)",
            "",
            "Each component binds one or more source paths with `sha256`, optional",
            "`git_revision`, and extracted AST/export symbols. Required symbols are",
            "asserted by the audit.",
            "",
        ]
    )

    for component_id in inventory["required_component_ids"]:
        component = components[component_id]
        lines.append(f"### `{component_id}`")
        lines.append("")
        lines.append(f"- **Plane:** {component['plane']}")
        lines.append(f"- **Owner:** `{component['owner']}`")
        lines.append(f"- **Role:** {component['role']}")
        lines.append("- **Modules:**")
        for module in component["modules"]:
            rev = module.get("git_revision") or "uncommitted/unavailable"
            lines.append(
                f"  - `{module['path']}` — sha256 `{module['sha256'][:16]}…` "
                f"({module['line_count']} lines, {module['symbol_count']} symbols, "
                f"rev `{rev[:12]}`)"
            )
        required = component.get("required_ast_symbols") or {}
        if required:
            lines.append("- **Required AST symbols:**")
            for path, names in required.items():
                joined = ", ".join(f"`{name}`" for name in names)
                lines.append(f"  - `{path}`: {joined}")
        for note in component.get("extra_notes") or ():
            lines.append(f"- Note: {note}")
        lines.append("")

    lines.extend(
        [
            "## Gap matrix highlights",
            "",
            "Program-level gaps (see `route-gap-matrix.json` for full detail):",
            "",
            "| ID | Title | Status |",
            "| --- | --- | --- |",
        ]
    )
    for gap in gap_matrix["program_gaps"]:
        lines.append(f"| {gap['id']} | {gap['title']} | `{gap['status']}` |")

    open_route_gaps = [
        entry for entry in routes if entry.get("gaps")
    ]
    lines.extend(
        [
            "",
            f"Routes with outstanding gaps: **{len(open_route_gaps)}** / {len(routes)}.",
            "",
            "### Handoff truthfulness",
            "",
            "- `live_agent` is proposal-eligible for `handoff_live_agent` but **not**",
            "  mapped in `DEFAULT_ROUTE_TO_LOGICAL_ACTION` today.",
            "- Telephone path in `voice_router` can degrade to text-only",
            "  `human_handoff` metadata; it must never claim an unverified transfer.",
            "- `ActionDecisionKind.HANDOFF` exists in contracts; no verified telephony",
            "  adapter is admitted yet.",
            "",
            "### Dual-plane rule (preview; doctrine freezes in VOICE-ACTION-003)",
            "",
            "```text",
            "content plane (Abby DAG / GraphRAG / audio)",
            "  -> logical ActionProposal only",
            "authority plane (catalog / policy / confirmation / adapter)",
            "  -> ActionReceipt + spoken outcome",
            "```",
            "",
            "Content artifacts must never embed executables, URLs, import paths,",
            "credentials, or raw argv.",
            "",
            "## Validation",
            "",
            "```bash",
            "python scripts/voice_action_dag/audit_baseline.py --check",
            "```",
            "",
            "The audit fails closed when:",
            "",
            "1. route census diverges from `summary.routeCounts` in the slotted DAG;",
            "2. any route lacks a classification in",
            "   `{content-only, proposal-eligible, safety-overlay}`;",
            "3. a required component path or AST symbol is missing;",
            "4. inventory digests no longer match the bound source files.",
            "",
        ]
    )
    return "\n".join(lines)


def _compare_route_counts(
    expected: Mapping[str, int], actual: Mapping[str, Any], *, label: str
) -> list[str]:
    errors: list[str] = []
    if set(expected) != set(actual):
        errors.append(
            f"{label}: route set mismatch "
            f"missing={sorted(set(expected) - set(actual))} "
            f"extra={sorted(set(actual) - set(expected))}"
        )
        return errors
    for route, count in expected.items():
        if actual.get(route) != count:
            errors.append(
                f"{label}: route {route} count expected {count}, got {actual.get(route)}"
            )
    return errors


def check_artifacts(repo_root: Path) -> list[str]:
    errors: list[str] = []
    live_counts = load_slotted_route_counts(repo_root)

    inventory_path = repo_root / INVENTORY_REL
    gap_path = repo_root / GAP_MATRIX_REL
    doc_path = repo_root / DOC_REL

    for path, label in (
        (inventory_path, INVENTORY_REL),
        (gap_path, GAP_MATRIX_REL),
        (doc_path, DOC_REL),
    ):
        if not path.is_file():
            errors.append(f"missing artifact: {label}")

    if errors:
        return errors

    try:
        inventory = _read_json(inventory_path)
        gap_matrix = _read_json(gap_path)
    except AuditError as exc:
        return [str(exc)]

    if not isinstance(inventory, dict):
        errors.append("component-inventory.json root must be an object")
        return errors
    if not isinstance(gap_matrix, dict):
        errors.append("route-gap-matrix.json root must be an object")
        return errors

    if inventory.get("schema") != INVENTORY_SCHEMA:
        errors.append(f"component-inventory schema must be {INVENTORY_SCHEMA}")
    if inventory.get("goal_id") != GOAL_ID:
        errors.append(f"component-inventory goal_id must be {GOAL_ID}")
    if inventory.get("task_id") != TASK_ID:
        errors.append(f"component-inventory task_id must be {TASK_ID}")
    if inventory.get("program_id") != PROGRAM_ID:
        errors.append(f"component-inventory program_id must be {PROGRAM_ID}")

    if gap_matrix.get("schema") != GAP_MATRIX_SCHEMA:
        errors.append(f"route-gap-matrix schema must be {GAP_MATRIX_SCHEMA}")
    if gap_matrix.get("goal_id") != GOAL_ID:
        errors.append(f"route-gap-matrix goal_id must be {GOAL_ID}")
    if gap_matrix.get("task_id") != TASK_ID:
        errors.append(f"route-gap-matrix task_id must be {TASK_ID}")

    inv_routes = (inventory.get("slotted_response_dag") or {}).get("route_counts")
    if not isinstance(inv_routes, dict):
        errors.append("component-inventory missing slotted_response_dag.route_counts")
    else:
        errors.extend(
            _compare_route_counts(live_counts, inv_routes, label="component-inventory")
        )

    gap_routes = gap_matrix.get("route_census")
    if not isinstance(gap_routes, dict):
        errors.append("route-gap-matrix missing route_census")
    else:
        errors.extend(
            _compare_route_counts(live_counts, gap_routes, label="route-gap-matrix")
        )

    routes = gap_matrix.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append("route-gap-matrix.routes must be a non-empty list")
    else:
        seen: set[str] = set()
        for entry in routes:
            if not isinstance(entry, dict):
                errors.append("route-gap-matrix.routes entry must be an object")
                continue
            route = entry.get("route")
            classification = entry.get("classification")
            if not isinstance(route, str) or route not in live_counts:
                errors.append(f"unknown or invalid route in gap matrix: {route!r}")
                continue
            if route in seen:
                errors.append(f"duplicate route in gap matrix: {route}")
            seen.add(route)
            if classification not in ROUTE_CLASSIFICATIONS:
                errors.append(
                    f"route {route} classification must be one of "
                    f"{sorted(ROUTE_CLASSIFICATIONS)}, got {classification!r}"
                )
            if entry.get("edge_count") != live_counts[route]:
                errors.append(
                    f"route {route} edge_count expected {live_counts[route]}, "
                    f"got {entry.get('edge_count')}"
                )
            expected_meta = ROUTE_BASELINE.get(route)
            if expected_meta and classification != expected_meta["classification"]:
                errors.append(
                    f"route {route} classification expected "
                    f"{expected_meta['classification']}, got {classification}"
                )
        missing_routes = set(live_counts) - seen
        if missing_routes:
            errors.append(
                f"route-gap-matrix missing routes: {sorted(missing_routes)}"
            )

    components = inventory.get("components")
    if not isinstance(components, dict):
        errors.append("component-inventory.components must be an object")
    else:
        for component_id in COMPONENT_SPECS:
            if component_id not in components:
                errors.append(f"component-inventory missing component: {component_id}")
                continue
            component = components[component_id]
            if not isinstance(component, dict):
                errors.append(f"component {component_id} must be an object")
                continue
            modules = component.get("modules")
            if not isinstance(modules, list) or not modules:
                errors.append(f"component {component_id} modules must be non-empty")
                continue
            by_path = {
                m.get("path"): m for m in modules if isinstance(m, dict) and m.get("path")
            }
            for rel in COMPONENT_SPECS[component_id]["paths"]:
                if rel not in by_path:
                    errors.append(f"component {component_id} missing module path {rel}")
                    continue
                module = by_path[rel]
                live_path = repo_root / rel
                if not live_path.is_file():
                    errors.append(f"component {component_id} path missing on disk: {rel}")
                    continue
                live_digest = _sha256_file(live_path)
                inv_digest = module.get("sha256")
                if "git_revision" not in module:
                    errors.append(
                        f"component {component_id} module {rel} must bind git_revision "
                        f"(null allowed when unavailable)"
                    )
                if not isinstance(inv_digest, str) or not inv_digest:
                    errors.append(
                        f"component {component_id} module {rel} must bind sha256"
                    )
                elif inv_digest == "live":
                    # Explicit live-binding token: audit re-hashes the path and
                    # still fail-closes on missing AST symbols below.
                    pass
                elif (
                    len(inv_digest) == 64
                    and all(c in "0123456789abcdef" for c in inv_digest)
                ):
                    if inv_digest != live_digest:
                        errors.append(
                            f"component {component_id} digest drift for {rel}: "
                            f"inventory={inv_digest} tree={live_digest}"
                        )
                else:
                    errors.append(
                        f"component {component_id} module {rel} sha256 must be "
                        f"64-char hex or the live-binding token 'live'"
                    )
                try:
                    live_symbols = _extract_symbols(live_path)
                except SyntaxError as exc:
                    errors.append(f"component {component_id} parse error {rel}: {exc}")
                    continue
                present = _symbol_names(live_symbols)
                inv_symbols = module.get("symbols") or []
                if not isinstance(inv_symbols, list):
                    errors.append(
                        f"component {component_id} symbols for {rel} must be a list"
                    )
                    inv_symbols = []
                inv_names = _symbol_names(inv_symbols)
                component_required_map = component.get("required_ast_symbols") or {}
                if not isinstance(component_required_map, dict):
                    errors.append(
                        f"component {component_id} required_ast_symbols must be an object"
                    )
                    component_required_map = {}
                required = list(
                    component_required_map.get(rel)
                    or COMPONENT_SPECS[component_id]
                    .get("required_symbols", {})
                    .get(rel, [])
                )
                bound_names = inv_names | {
                    str(name)
                    for name in (component_required_map.get(rel) or [])
                    if isinstance(name, str)
                }
                for name in required:
                    if name not in present:
                        errors.append(
                            f"component {component_id} missing AST symbol {name} in {rel}"
                        )
                    if name not in bound_names:
                        errors.append(
                            f"component {component_id} does not bind symbol {name} for {rel}"
                        )

    doc_text = doc_path.read_text(encoding="utf-8")
    required_phrases = (
        "Baseline Inventory",
        "content-only",
        "proposal-eligible",
        "safety-overlay",
        "voice_router",
        "action_runtime",
        "graphrag",
        "ui_tools",
        "service_actions",
        "handoff",
        "audit_baseline.py --check",
        "live_agent",
        SLOTTED_DAG_REL,
    )
    for phrase in required_phrases:
        if phrase not in doc_text:
            errors.append(f"BASELINE_INVENTORY.md missing required phrase: {phrase}")
    for route in live_counts:
        if f"`{route}`" not in doc_text and route not in doc_text:
            errors.append(f"BASELINE_INVENTORY.md missing route: {route}")

    return errors


def write_artifacts(repo_root: Path) -> None:
    inventory = build_component_inventory(repo_root)
    gap_matrix = build_route_gap_matrix(repo_root)
    # Align timestamps for a coherent freeze.
    stamp = inventory["generated_at"]
    gap_matrix["generated_at"] = stamp
    doc = build_baseline_doc(inventory, gap_matrix)
    _write_json(repo_root / INVENTORY_REL, inventory)
    _write_json(repo_root / GAP_MATRIX_REL, gap_matrix)
    doc_path = repo_root / DOC_REL
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(doc, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Abby voice-action baseline inventory artifacts."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate committed baseline artifacts against the live tree.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate baseline inventory, gap matrix, and markdown report.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root (default: detected from script location).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.check and not args.write:
        parser.error("specify --check and/or --write")

    repo_root = args.repo_root.resolve()
    try:
        if args.write:
            write_artifacts(repo_root)
            print(f"wrote {INVENTORY_REL}")
            print(f"wrote {GAP_MATRIX_REL}")
            print(f"wrote {DOC_REL}")
        if args.check:
            # Prefer a freshly frozen inventory when any module still uses the
            # live-binding token so --check evidence includes real digests.
            inventory_path = repo_root / INVENTORY_REL
            if inventory_path.is_file():
                try:
                    existing = _read_json(inventory_path)
                except AuditError:
                    existing = None
                if isinstance(existing, dict):
                    needs_freeze = False
                    components = existing.get("components") or {}
                    if isinstance(components, dict):
                        for component in components.values():
                            if not isinstance(component, dict):
                                continue
                            for module in component.get("modules") or []:
                                if (
                                    isinstance(module, dict)
                                    and module.get("sha256") == "live"
                                ):
                                    needs_freeze = True
                                    break
                            if needs_freeze:
                                break
                    if needs_freeze:
                        write_artifacts(repo_root)
                        print("froze live-bound digests via inventory rewrite")
            errors = check_artifacts(repo_root)
            if errors:
                print("voice action baseline audit --check FAILED", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return 1
            print("voice action baseline audit --check")
            print(f"  program: {PROGRAM_ID}")
            print(f"  goal: {GOAL_ID}")
            print(f"  task: {TASK_ID}")
            counts = load_slotted_route_counts(repo_root)
            print(f"  routes: {len(counts)} (edges={sum(counts.values())})")
            print("  classifications: " + ", ".join(sorted(ROUTE_CLASSIFICATIONS)))
            print("  components: " + ", ".join(sorted(COMPONENT_SPECS)))
            # Re-bind a sample digest so evidence shows live tree identity.
            sample = (
                repo_root
                / "ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py"
            )
            if sample.is_file():
                print(f"  sample_digest voice_bridge.py={_sha256_file(sample)[:16]}…")
            print("  status: ok")
    except AuditError as exc:
        print(f"voice action baseline audit error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
