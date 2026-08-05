#!/usr/bin/env python3
"""Audit 211-AI app surfaces, tools, and voice bindings (VAS-004 / VAS-005)."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "voice_app_surface_coverage" / "baseline"
SURFACE_INV = OUT_DIR / "app-surface-inventory.json"
TOOL_INV = OUT_DIR / "tool-inventory.json"
BINDING_INV = OUT_DIR / "binding-inventory.json"
DOC_OUT = REPO_ROOT / "docs" / "voice_app_surface_coverage" / "APP_SURFACE_INVENTORY.md"
SCHEMA_SURFACE = "voice-app-surface-coverage/app-surface-inventory@1"
SCHEMA_TOOL = "voice-app-surface-coverage/tool-inventory@1"
SCHEMA_BINDING = "voice-app-surface-coverage/binding-inventory@1"
PROGRAM_ID = "voice-app-surface-coverage-v1"

APP_STATE = REPO_ROOT / "wallet_interface" / "ui" / "src" / "app" / "appState.ts"
NAV_CONFIG = REPO_ROOT / "wallet_interface" / "ui" / "src" / "app" / "config" / "navigation.ts"
ROUTE_TYPE = REPO_ROOT / "wallet_interface" / "ui" / "src" / "models" / "abby.ts"
BINDING_PY = (
    REPO_ROOT / "wallet_interface" / "helpers" / "_voice_app_action_binding.py"
)
TOOLS_DIR = (
    REPO_ROOT / "wallet_interface" / "ui" / "src" / "features" / "agent" / "lib" / "tools"
)
CATALOG_JSON = REPO_ROOT / "data" / "voice_action_dag" / "catalog" / "211ai-pilot-v1.json"
ADAPTER_DIR = (
    REPO_ROOT
    / "ipfs_accelerate_py"
    / "ipfs_accelerate_py"
    / "action_runtime"
    / "adapters"
)

PROVIDER_PREFIXES = ("provider-",)
DEFAULT_PROVIDER_IDS = frozenset(
    {
        "shelter",
        "provider-clients",
        "provider-cases",
        "provider-messages",
        "provider-analytics",
        "provider-proofs",
        "provider-operations",
    }
)
REMOVED_STANDALONE_DEFAULT = frozenset(
    {
        "sharing-rules",
        "recipient-access",
        "benefits-protection",
        "exports",
        "security",
    }
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_route_union(text: str) -> list[str]:
    """Parse `export type RouteId = "a" | "b"` style unions."""
    match = re.search(
        r"export\s+type\s+RouteId\s*=\s*([\s\S]*?);",
        text,
    )
    if not match:
        return []
    body = match.group(1)
    return re.findall(r'"([^"]+)"', body)


def _parse_route_array(text: str, const_name: str) -> list[dict[str, str]]:
    """Parse `export const primaryRoutes: Array<{ id: RouteId; label: string }> = [...]`."""
    pattern = re.compile(
        rf"export\s+const\s+{re.escape(const_name)}\s*[^=]*=\s*\[([\s\S]*?)\];",
    )
    match = pattern.search(text)
    if not match:
        return []
    body = match.group(1)
    rows: list[dict[str, str]] = []
    for id_, label in re.findall(
        r'\{\s*id:\s*"([^"]+)"\s*,\s*label:\s*"([^"]+)"\s*\}',
        body,
    ):
        rows.append({"id": id_, "label": label})
    return rows


def _parse_string_set(text: str, const_name: str) -> set[str]:
    pattern = re.compile(
        rf"(?:export\s+)?const\s+{re.escape(const_name)}\s*=\s*new\s+Set[^(]*\(\[([\s\S]*?)\]\)",
    )
    match = pattern.search(text)
    if not match:
        # frozenset({...}) or set literal assignment
        pattern2 = re.compile(
            rf"{re.escape(const_name)}\s*[:=][^\[]*\[([\s\S]*?)\]",
        )
        match = pattern2.search(text)
    if not match:
        return set()
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _parse_python_frozenset_strings(path: Path, name: str) -> set[str]:
    tree = ast.parse(_read(path), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign | ast.Assign):
            continue
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id != name:
                continue
            value = node.value
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    targets.append(t)
            if not targets:
                continue
            value = node.value
        else:
            continue
        if value is None:
            continue
        # frozenset({...}) or frozenset([...])
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            if value.func.id != "frozenset" or not value.args:
                continue
            arg = value.args[0]
            if isinstance(arg, (ast.Set, ast.List, ast.Tuple)):
                out: set[str] = set()
                for elt in arg.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        out.add(elt.value)
                return out
    return set()


def _parse_python_dict_string_keys(path: Path, name: str) -> dict[str, str]:
    tree = ast.parse(_read(path), filename=str(path))
    for node in tree.body:
        target_name = None
        value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    target_name = t.id
                    value = node.value
                    break
        if target_name != name or value is None:
            continue
        # MappingProxyType({...}) or dict literal
        if isinstance(value, ast.Call) and value.args:
            value = value.args[0]
        if not isinstance(value, ast.Dict):
            continue
        out: dict[str, str] = {}
        for k, v in zip(value.keys, value.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out[k.value] = v.value
        return out
    return {}


def build_surface_inventory() -> dict[str, Any]:
    route_type_ids = _parse_route_union(_read(ROUTE_TYPE))
    app_state = _read(APP_STATE)
    primary = _parse_route_array(app_state, "primaryRoutes")
    secondary = _parse_route_array(app_state, "secondaryRoutes")
    nav = _read(NAV_CONFIG)
    provider_ids = _parse_string_set(nav, "providerRouteIds") or set(DEFAULT_PROVIDER_IDS)
    removed = _parse_string_set(nav, "removedStandaloneRoutes") or set(
        REMOVED_STANDALONE_DEFAULT
    )
    binding_ids = _parse_python_frozenset_strings(BINDING_PY, "NAVIGATION_SURFACE_IDS")
    labels = _parse_python_dict_string_keys(BINDING_PY, "NAVIGATION_SURFACE_LABELS")

    by_id: dict[str, dict[str, Any]] = {}
    for row in primary:
        by_id[row["id"]] = {
            "id": row["id"],
            "label": row["label"],
            "family": "primary",
            "source": "wallet_interface/ui/src/app/appState.ts#primaryRoutes",
        }
    for row in secondary:
        by_id[row["id"]] = {
            "id": row["id"],
            "label": row["label"],
            "family": "secondary",
            "source": "wallet_interface/ui/src/app/appState.ts#secondaryRoutes",
        }
    # audit is in appRouteIds but may not be in primary/secondary lists
    for rid in route_type_ids:
        if rid not in by_id:
            by_id[rid] = {
                "id": rid,
                "label": labels.get(rid, rid),
                "family": "extra",
                "source": "wallet_interface/ui/src/models/abby.ts#RouteId",
            }

    surfaces = []
    for rid in sorted(by_id):
        row = dict(by_id[rid])
        row["is_provider"] = rid in provider_ids or rid.startswith(PROVIDER_PREFIXES)
        row["removed_standalone"] = rid in removed
        row["in_navigation_allowlist"] = rid in binding_ids
        row["binding_label"] = labels.get(rid)
        row["hash_route"] = f"#/{rid}"
        surfaces.append(row)

    ui_ids = set(by_id)
    type_ids = set(route_type_ids)
    allow_ids = set(binding_ids)
    mismatches = {
        "in_route_type_not_ui_tables": sorted(type_ids - ui_ids),
        "in_ui_tables_not_route_type": sorted(ui_ids - type_ids),
        "in_allowlist_not_ui": sorted(allow_ids - ui_ids - type_ids),
        "in_ui_not_allowlist": sorted((ui_ids | type_ids) - allow_ids),
    }

    return {
        "schema": SCHEMA_SURFACE,
        "program_id": PROGRAM_ID,
        "task_ids": ["VAS-004"],
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {
            "route_type": str(ROUTE_TYPE.relative_to(REPO_ROOT)),
            "app_state": str(APP_STATE.relative_to(REPO_ROOT)),
            "navigation_config": str(NAV_CONFIG.relative_to(REPO_ROOT)),
            "voice_binding": str(BINDING_PY.relative_to(REPO_ROOT)),
        },
        "counts": {
            "surfaces": len(surfaces),
            "primary": len(primary),
            "secondary": len(secondary),
            "provider": sum(1 for s in surfaces if s["is_provider"]),
            "allowlist": len(allow_ids),
        },
        "surfaces": surfaces,
        "mismatches": mismatches,
    }


def build_tool_inventory() -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    if TOOLS_DIR.is_dir():
        for path in sorted(TOOLS_DIR.glob("*.ts")):
            text = _read(path)
            exports = re.findall(
                r"export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)",
                text,
            )
            exports += re.findall(
                r"export\s+const\s+([A-Za-z0-9_]+)\s*=",
                text,
            )
            tools.append(
                {
                    "module": path.name,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "exports": sorted(set(exports)),
                    "export_count": len(set(exports)),
                }
            )

    adapters: list[dict[str, Any]] = []
    if ADAPTER_DIR.is_dir():
        for path in sorted(ADAPTER_DIR.glob("*.py")):
            if path.name.startswith("_"):
                continue
            adapters.append(
                {
                    "module": path.stem,
                    "path": str(path.relative_to(REPO_ROOT)),
                }
            )

    return {
        "schema": SCHEMA_TOOL,
        "program_id": PROGRAM_ID,
        "task_ids": ["VAS-005"],
        "generated_at": datetime.now(UTC).isoformat(),
        "agent_tools": tools,
        "action_runtime_adapters": adapters,
        "counts": {
            "agent_tool_modules": len(tools),
            "adapter_modules": len(adapters),
        },
    }


def build_binding_inventory() -> dict[str, Any]:
    logical_actions: list[str] = []
    descriptors: list[dict[str, Any]] = []
    if CATALOG_JSON.is_file():
        catalog = json.loads(_read(CATALOG_JSON))
        for row in catalog.get("descriptors") or []:
            if not isinstance(row, dict):
                continue
            la = str(row.get("logical_action") or "")
            if la:
                logical_actions.append(la)
            descriptors.append(
                {
                    "logical_action": la,
                    "descriptor_id": row.get("descriptor_id"),
                    "adapter": row.get("adapter"),
                    "risk_class": row.get("risk_class"),
                    "requires_confirmation": row.get("requires_confirmation"),
                }
            )

    allowlist = sorted(
        _parse_python_frozenset_strings(BINDING_PY, "NAVIGATION_SURFACE_IDS")
    )
    return {
        "schema": SCHEMA_BINDING,
        "program_id": PROGRAM_ID,
        "task_ids": ["VAS-005"],
        "generated_at": datetime.now(UTC).isoformat(),
        "catalog_path": str(CATALOG_JSON.relative_to(REPO_ROOT)),
        "catalog_logical_actions": sorted(set(logical_actions)),
        "descriptors": descriptors,
        "navigation_allowlist": allowlist,
        "voice_binding_module": str(BINDING_PY.relative_to(REPO_ROOT)),
        "counts": {
            "logical_actions": len(set(logical_actions)),
            "descriptors": len(descriptors),
            "allowlist_surfaces": len(allowlist),
        },
        "unbound_notes": [
            "Most allowlisted surfaces only open via open_app_surface; "
            "refined read/write actions remain calendar/messages/service/handoff pilot set."
        ],
    }


def write_doc(
    surface: dict[str, Any],
    tools: dict[str, Any],
    binding: dict[str, Any],
) -> None:
    lines = [
        "# 211-AI App Surface Inventory",
        "",
        f"Program: `{PROGRAM_ID}`  ",
        "Tasks: `VAS-004`, `VAS-005`  ",
        f"Generated: `{surface.get('generated_at')}`",
        "",
        "## Counts",
        "",
        f"- Surfaces: **{surface['counts']['surfaces']}** "
        f"(primary {surface['counts']['primary']}, "
        f"secondary {surface['counts']['secondary']}, "
        f"provider {surface['counts']['provider']})",
        f"- Navigation allowlist: **{surface['counts']['allowlist']}**",
        f"- Agent tool modules: **{tools['counts']['agent_tool_modules']}**",
        f"- Action adapters: **{tools['counts']['adapter_modules']}**",
        f"- Pilot logical actions: **{binding['counts']['logical_actions']}**",
        "",
        "## Surfaces",
        "",
        "| id | label | family | provider | allowlist | removed standalone |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in surface["surfaces"]:
        lines.append(
            f"| `{row['id']}` | {row['label']} | {row['family']} | "
            f"{'yes' if row['is_provider'] else 'no'} | "
            f"{'yes' if row['in_navigation_allowlist'] else 'NO'} | "
            f"{'yes' if row['removed_standalone'] else 'no'} |"
        )
    mm = surface.get("mismatches") or {}
    lines += [
        "",
        "## Allowlist vs UI mismatches",
        "",
        "```json",
        json.dumps(mm, indent=2, sort_keys=True),
        "```",
        "",
        "## Pilot logical actions",
        "",
    ]
    for la in binding.get("catalog_logical_actions") or []:
        lines.append(f"- `{la}`")
    lines += [
        "",
        "## Agent tool modules",
        "",
    ]
    for tool in tools.get("agent_tools") or []:
        lines.append(
            f"- `{tool['module']}` ({tool['export_count']} exports) — `{tool['path']}`"
        )
    lines.append("")
    DOC_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOC_OUT.write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check() -> list[str]:
    errors: list[str] = []
    for path, schema in (
        (SURFACE_INV, SCHEMA_SURFACE),
        (TOOL_INV, SCHEMA_TOOL),
        (BINDING_INV, SCHEMA_BINDING),
    ):
        if not path.is_file():
            errors.append(f"missing {path}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"unreadable {path}: {exc}")
            continue
        if payload.get("schema") != schema:
            errors.append(f"{path.name} schema mismatch")
        if payload.get("program_id") != PROGRAM_ID:
            errors.append(f"{path.name} program_id mismatch")
    if SURFACE_INV.is_file():
        payload = json.loads(SURFACE_INV.read_text(encoding="utf-8"))
        surfaces = payload.get("surfaces") or []
        if len(surfaces) < 20:
            errors.append(f"expected ≥20 surfaces, got {len(surfaces)}")
        ids = [row.get("id") for row in surfaces if isinstance(row, dict)]
        for required in ("home", "calendar", "messages", "uploads", "audit"):
            if required not in ids:
                errors.append(f"surface inventory missing {required}")
    if not DOC_OUT.is_file():
        errors.append(f"missing inventory doc {DOC_OUT}")
    return errors


def check_tools() -> list[str]:
    errors = check()
    if TOOL_INV.is_file():
        payload = json.loads(TOOL_INV.read_text(encoding="utf-8"))
        if payload.get("counts", {}).get("agent_tool_modules", 0) < 10:
            errors.append("expected ≥10 agent tool modules")
    if BINDING_INV.is_file():
        payload = json.loads(BINDING_INV.read_text(encoding="utf-8"))
        actions = set(payload.get("catalog_logical_actions") or [])
        for required in (
            "open_app_surface",
            "read_calendar",
            "handoff_live_agent",
        ):
            if required not in actions:
                errors.append(f"binding inventory missing logical action {required}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write inventory artifacts")
    parser.add_argument("--check", action="store_true", help="Validate surface inventory")
    parser.add_argument(
        "--check-tools",
        action="store_true",
        help="Validate tool + binding inventories",
    )
    args = parser.parse_args()

    if args.write or not (args.check or args.check_tools):
        surface = build_surface_inventory()
        tools = build_tool_inventory()
        binding = build_binding_inventory()
        if args.write or not (args.check or args.check_tools):
            # default: write when neither check-only
            if args.write or not (args.check or args.check_tools):
                pass
        if args.write:
            _write_json(SURFACE_INV, surface)
            _write_json(TOOL_INV, tools)
            _write_json(BINDING_INV, binding)
            write_doc(surface, tools, binding)
            print(f"wrote {SURFACE_INV}")
            print(f"wrote {TOOL_INV}")
            print(f"wrote {BINDING_INV}")
            print(f"wrote {DOC_OUT}")
        elif not args.check and not args.check_tools:
            _write_json(SURFACE_INV, surface)
            _write_json(TOOL_INV, tools)
            _write_json(BINDING_INV, binding)
            write_doc(surface, tools, binding)
            print(f"wrote {SURFACE_INV}")
            print(f"wrote {TOOL_INV}")
            print(f"wrote {BINDING_INV}")
            print(f"wrote {DOC_OUT}")

    errors: list[str] = []
    if args.check:
        errors.extend(check())
    if args.check_tools:
        errors.extend(check_tools())
    if errors:
        print("app surface audit FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    if args.check or args.check_tools:
        print("app surface audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
