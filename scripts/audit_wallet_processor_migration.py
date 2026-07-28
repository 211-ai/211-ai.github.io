#!/usr/bin/env python3
"""Read-only audit checks for wallet processor migration Phase 0 inventory.

Validates the frozen WALPROC-G010 evidence artifacts:

- data/wallet_processor_migration/audit/source-inventory.json
- data/wallet_processor_migration/audit/import-map.json
- data/wallet_processor_migration/audit/ownership-map.md

Usage:
  python scripts/audit_wallet_processor_migration.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO_ROOT / "data" / "wallet_processor_migration" / "audit"
SOURCE_INVENTORY = AUDIT_DIR / "source-inventory.json"
IMPORT_MAP = AUDIT_DIR / "import-map.json"
OWNERSHIP_MAP = AUDIT_DIR / "ownership-map.md"

REQUIRED_WORLD_ID_SYMBOLS = (
    "WorldIdConfig",
    "load_world_id_config",
    "normalize_world_id_idkit_response",
    "normalize_idkit_response",
    "sign_world_id_request",
    "verify_world_id_proof",
    "redact_world_id_payload",
    "hash_to_field",
    "WorldIdRpSignature",
    "WorldIdIdkitResult",
    "WorldIdVerificationResult",
)

REQUIRED_WALLET_SYMBOLS = (
    "WorldIdBinding",
    "DataWalletService",
)

REQUIRED_INVENTORY_KEYS = (
    "schema",
    "goal_id",
    "modules",
    "world_id_symbols_complete",
    "app_service_world_id_related_symbols",
    "ops_world_id_related_symbols",
    "data_wallet_service_world_snapshot_proof_symbols",
    "python_callers",
    "typescript_and_ui_callers",
    "xaman_formal_and_security_assets",
    "processor_protocols",
    "optional_dependencies",
    "network_endpoints",
    "config_keys",
    "secret_references",
    "blockers",
    "acceptance_coverage",
)

REQUIRED_IMPORT_KEYS = (
    "schema",
    "goal_id",
    "edges",
    "python_direct_world_id_callers",
    "typescript_ui_callers",
    "incompatible_generic_processor_surfaces",
)

REQUIRED_OWNERSHIP_PHRASES = (
    "WALPROC-G010",
    "wallet_interface/world_id.py",
    "WorldIdBinding",
    "DataWalletService",
    "can_process",
    "can_handle",
    "move",
    "retain",
    "Blocker",
    "processors/wallets/worldcoin",
    "xaman",
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return data


def _symbol_names(entries: list[Any]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for key in ("name", "qualname", "symbol"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                names.add(value)
                if "." in value:
                    names.add(value.rsplit(".", 1)[-1])
    return names


def check_source_inventory(errors: list[str], warnings: list[str]) -> dict[str, Any] | None:
    if not SOURCE_INVENTORY.is_file():
        errors.append(f"missing inventory: {SOURCE_INVENTORY.relative_to(REPO_ROOT)}")
        return None

    try:
        inventory = _load_json(SOURCE_INVENTORY)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid source-inventory.json: {exc}")
        return None

    for key in REQUIRED_INVENTORY_KEYS:
        if key not in inventory:
            errors.append(f"source-inventory.json missing key: {key}")

    if inventory.get("goal_id") != "WALPROC-G010":
        errors.append("source-inventory.json goal_id must be WALPROC-G010")

    coverage = inventory.get("acceptance_coverage") or {}
    if not isinstance(coverage, dict):
        errors.append("acceptance_coverage must be an object")
        coverage = {}

    line_count = coverage.get("world_id_py_line_count")
    world_id_path = REPO_ROOT / "wallet_interface" / "world_id.py"
    if world_id_path.is_file():
        text = world_id_path.read_text(encoding="utf-8", errors="replace")
        actual_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        if isinstance(line_count, int) and abs(line_count - actual_lines) > 5:
            warnings.append(
                f"world_id.py line_count inventory={line_count} filesystem={actual_lines}"
            )
        if isinstance(line_count, int) and line_count < 900:
            errors.append(f"world_id.py inventory line_count too small: {line_count}")
    else:
        errors.append("wallet_interface/world_id.py missing from repository")
    world_symbols = inventory.get("world_id_symbols_complete") or []
    if not isinstance(world_symbols, list) or len(world_symbols) < 50:
        errors.append(
            "world_id_symbols_complete must list the full world_id.py symbol set "
            f"(got {0 if not isinstance(world_symbols, list) else len(world_symbols)})"
        )
    names = _symbol_names(world_symbols if isinstance(world_symbols, list) else [])
    for required in REQUIRED_WORLD_ID_SYMBOLS:
        if required not in names:
            errors.append(f"world_id inventory missing symbol: {required}")

    models_and_service = []
    for key in (
        "world_id_binding_and_related_models",
        "data_wallet_service_world_snapshot_proof_symbols",
    ):
        value = inventory.get(key) or []
        if isinstance(value, list):
            models_and_service.extend(value)
    service_names = _symbol_names(models_and_service)
    # Also scan serialized JSON for binding/service names
    blob = json.dumps(inventory)
    for required in REQUIRED_WALLET_SYMBOLS:
        if required not in service_names and required not in blob:
            errors.append(f"inventory missing wallet-domain symbol coverage: {required}")

    protocols = inventory.get("processor_protocols") or []
    if not isinstance(protocols, list) or len(protocols) < 2:
        errors.append("processor_protocols must document both incompatible generic surfaces")
    else:
        dispatch = {str(p.get("dispatch_method")) for p in protocols if isinstance(p, dict)}
        if "can_process" not in dispatch or "can_handle" not in dispatch:
            errors.append("processor_protocols must include can_process and can_handle")

    xaman = inventory.get("xaman_formal_and_security_assets") or []
    if not isinstance(xaman, list) or len(xaman) < 1:
        errors.append("xaman_formal_and_security_assets must list current formal assets")

    callers = inventory.get("python_callers") or {}
    if not isinstance(callers, dict) or not callers:
        errors.append("python_callers must be present")
    ts_callers = inventory.get("typescript_and_ui_callers") or []
    if not isinstance(ts_callers, list) or len(ts_callers) < 1:
        errors.append("typescript_and_ui_callers must list UI/TS callers")

    if not inventory.get("network_endpoints"):
        errors.append("network_endpoints must be documented")
    if not inventory.get("config_keys"):
        errors.append("config_keys must be documented")
    if not inventory.get("secret_references"):
        errors.append("secret_references must be documented")
    if not inventory.get("optional_dependencies"):
        errors.append("optional_dependencies must be documented")

    blockers = inventory.get("blockers") or []
    if not isinstance(blockers, list) or not blockers:
        errors.append(
            "blockers must record unresolved ownership rather than guessing "
            "(at least the generic processor adapter decision)"
        )
    else:
        guessed = [b for b in blockers if isinstance(b, dict) and b.get("guessed") is True]
        if guessed:
            errors.append("blockers must not mark unresolved ownership as guessed=true")

    app_syms = inventory.get("app_service_world_id_related_symbols") or []
    ops_syms = inventory.get("ops_world_id_related_symbols") or []
    if not isinstance(app_syms, list) or not app_syms:
        errors.append("app_service_world_id_related_symbols must be non-empty")
    if not isinstance(ops_syms, list) or not ops_syms:
        errors.append("ops_world_id_related_symbols must be non-empty")
    else:
        ops_blob = json.dumps(ops_syms)
        if "_world_id_production_readiness_checks" not in ops_blob and "production_readiness" not in ops_blob:
            errors.append("ops inventory must cover World ID production readiness checks")

    return inventory


def check_import_map(errors: list[str], warnings: list[str]) -> dict[str, Any] | None:
    if not IMPORT_MAP.is_file():
        errors.append(f"missing import map: {IMPORT_MAP.relative_to(REPO_ROOT)}")
        return None

    try:
        import_map = _load_json(IMPORT_MAP)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid import-map.json: {exc}")
        return None

    for key in REQUIRED_IMPORT_KEYS:
        if key not in import_map:
            errors.append(f"import-map.json missing key: {key}")

    if import_map.get("goal_id") != "WALPROC-G010":
        errors.append("import-map.json goal_id must be WALPROC-G010")

    edges = import_map.get("edges") or []
    if not isinstance(edges, list) or len(edges) < 10:
        errors.append(f"import-map edges too sparse: {0 if not isinstance(edges, list) else len(edges)}")

    py_callers = import_map.get("python_direct_world_id_callers") or []
    if not isinstance(py_callers, list) or "wallet_interface/app_service.py" not in py_callers:
        errors.append("import-map must list wallet_interface/app_service.py as a world_id caller")

    surfaces = import_map.get("incompatible_generic_processor_surfaces") or []
    if not isinstance(surfaces, list) or len(surfaces) < 2:
        errors.append("import-map must document both incompatible generic processor surfaces")

    return import_map


def check_ownership_map(errors: list[str], warnings: list[str], inventory: dict[str, Any] | None) -> None:
    if not OWNERSHIP_MAP.is_file():
        errors.append(f"missing ownership map: {OWNERSHIP_MAP.relative_to(REPO_ROOT)}")
        return

    try:
        text = OWNERSHIP_MAP.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read ownership-map.md: {exc}")
        return

    if len(text) < 2000:
        errors.append("ownership-map.md is too short to be a complete freeze document")

    lowered = text.lower()
    for phrase in REQUIRED_OWNERSHIP_PHRASES:
        if phrase.lower() not in lowered and phrase not in text:
            errors.append(f"ownership-map.md missing required phrase: {phrase}")

    for decision in ("move", "retain", "create"):
        if f"**{decision}**" not in text and f"| **{decision}**" not in text and decision not in lowered:
            warnings.append(f"ownership-map.md may be missing decision emphasis for: {decision}")

    # Every top-level world_id symbol from inventory should appear in the ownership map.
    if inventory is not None:
        world_symbols = inventory.get("world_id_symbols_complete") or []
        if isinstance(world_symbols, list):
            missing = []
            for entry in world_symbols:
                if not isinstance(entry, dict):
                    continue
                qual = entry.get("qualname") or entry.get("name")
                if not qual:
                    continue
                # Methods are listed with qualname in the ownership table.
                if f"`{qual}`" not in text and f"`{entry.get('name')}`" not in text:
                    missing.append(str(qual))
            if missing:
                sample = ", ".join(missing[:8])
                errors.append(
                    f"ownership-map.md missing {len(missing)} world_id symbols "
                    f"(sample: {sample})"
                )

    if "blocker" not in lowered:
        errors.append("ownership-map.md must record unresolved ownership as blockers")


def run_check() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    inventory = check_source_inventory(errors, warnings)
    import_map = check_import_map(errors, warnings)
    check_ownership_map(errors, warnings, inventory)

    # Cross-artifact consistency
    if inventory is not None and import_map is not None:
        inv_callers = set(inventory.get("typescript_and_ui_callers") or [])
        map_callers = set(import_map.get("typescript_ui_callers") or [])
        if inv_callers and map_callers and inv_callers != map_callers:
            warnings.append("typescript caller lists differ between inventory and import-map")

    print("wallet processor migration audit --check")
    print(f"  inventory: {SOURCE_INVENTORY.relative_to(REPO_ROOT)} ({'ok' if inventory else 'MISSING'})")
    print(f"  import-map: {IMPORT_MAP.relative_to(REPO_ROOT)} ({'ok' if import_map else 'MISSING'})")
    print(f"  ownership: {OWNERSHIP_MAP.relative_to(REPO_ROOT)} ({'ok' if OWNERSHIP_MAP.is_file() else 'MISSING'})")

    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        return 1

    print(f"PASS ({len(warnings)} warning(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate frozen inventory / import-map / ownership-map artifacts",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    global REPO_ROOT, AUDIT_DIR, SOURCE_INVENTORY, IMPORT_MAP, OWNERSHIP_MAP
    if args.root is not None:
        REPO_ROOT = args.root.resolve()
        AUDIT_DIR = REPO_ROOT / "data" / "wallet_processor_migration" / "audit"
        SOURCE_INVENTORY = AUDIT_DIR / "source-inventory.json"
        IMPORT_MAP = AUDIT_DIR / "import-map.json"
        OWNERSHIP_MAP = AUDIT_DIR / "ownership-map.md"

    if args.check:
        return run_check()

    parser.error("specify --check (this script is validation-only; artifacts are checked in)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
