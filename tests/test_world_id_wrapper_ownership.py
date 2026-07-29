"""Static ownership gate for the 211-AI World ID thin wrapper (WALPROC-G130).

Proves that ``wallet_interface/world_id.py`` is a compatibility re-export of the
reusable ``ipfs_datasets_py.processors.wallets.worldcoin`` package and that
application policy remains in 211-AI (``app_service`` / ``ops``).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from wallet_interface import world_id as world_id_module
from wallet_interface.app_service import WalletInterfaceService
from wallet_interface.world_id import (
    DEFAULT_WORLD_ID_ACTION,
    DEFAULT_WORLD_ID_VERIFY_BASE_URL,
    WorldIdConfig,
    WorldIdConfigError,
    WorldIdPayloadError,
    WorldIdSignatureError,
    WorldIdVerificationError,
    load_world_id_config,
    normalize_idkit_response,
    redact_world_id_payload,
    sign_world_id_request_from_config,
    verify_world_id_proof_from_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORLD_ID_PATH = REPO_ROOT / "wallet_interface" / "world_id.py"
APP_SERVICE_PATH = REPO_ROOT / "wallet_interface" / "app_service.py"
OPS_PATH = REPO_ROOT / "wallet_interface" / "ops.py"

# Reviewed thin-wrapper budget (deprecation-window compatibility module only).
MAX_WRAPPER_LINES = 120
MAX_WRAPPER_TOP_LEVEL_STATEMENTS = 12

# Documented public World ID API that must remain importable from 211-AI.
REQUIRED_PUBLIC_NAMES = (
    "DEFAULT_WORLD_ID_ACTION",
    "DEFAULT_WORLD_ID_CREDENTIAL_POLICY",
    "DEFAULT_WORLD_ID_HTTP_TIMEOUT_SECONDS",
    "DEFAULT_WORLD_ID_SIGNATURE_TTL_SECONDS",
    "DEFAULT_WORLD_ID_VERIFY_BASE_URL",
    "SUPPORTED_WORLD_ID_ENVIRONMENTS",
    "WorldIdConfig",
    "WorldIdConfigError",
    "WorldIdCredentialResponse",
    "WorldIdIdkitResult",
    "WorldIdPayloadError",
    "WorldIdRequestJson",
    "WorldIdRpSignature",
    "WorldIdSecretConfig",
    "WorldIdSignatureError",
    "WorldIdVerificationError",
    "WorldIdVerificationResult",
    "compute_rp_signature_message",
    "eip191_digest",
    "hash_to_field",
    "hash_to_field_hex",
    "load_world_id_config",
    "normalize_idkit_response",
    "normalize_world_id_idkit_response",
    "normalize_world_id_verification_response",
    "redact_world_id_payload",
    "sign_world_id_request",
    "sign_world_id_request_from_config",
    "verify_world_id_proof",
    "verify_world_id_proof_from_config",
    "world_id_keccak256",
)

FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "urllib",
        "urllib.request",
        "urllib.error",
        "urllib.parse",
        "requests",
        "httpx",
        "http",
        "http.client",
        "Crypto",
        "Crypto.Hash",
        "coincurve",
        "hashlib",
        "hmac",
        "secrets",
        "socket",
        "ssl",
    }
)

# Implementation spellings that must not appear outside the module docstring.
# Avoid bare symbol names that also appear as re-export identifiers.
FORBIDDEN_SOURCE_MARKERS = (
    "import urllib",
    "from urllib",
    "import requests",
    "import httpx",
    "from Crypto",
    "import Crypto",
    "import coincurve",
    "from coincurve",
    "PrivateKey",
    "urlopen",
    "import hashlib",
    "from hashlib",
    "hmac.new",
    "json.loads",
    "json.dumps",
    "developer.world.org",
    "resolve_secret",
    "def world_id_keccak256",
    "def hash_to_field",
    "def sign_world_id_request",
    "def verify_world_id_proof",
    "def normalize_idkit_response",
    "def redact_world_id_payload",
    "def load_world_id_config",
    "class WorldIdConfig",
    "class WorldIdConfigError",
    "class WorldIdSignatureError",
    "class WorldIdVerificationError",
    "class WorldIdPayloadError",
)

ALLOWED_IMPORT_MODULES = frozenset(
    {
        "_vendor",
        "wallet_interface._vendor",
        "ipfs_datasets_py.processors.wallets.worldcoin",
    }
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _function_names(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def test_world_id_wrapper_has_explicit_all_and_required_public_api() -> None:
    assert hasattr(world_id_module, "__all__")
    public = list(world_id_module.__all__)
    assert public, "wrapper must declare an explicit non-empty __all__"
    assert public == sorted(public), "wrapper __all__ should be sorted for reviewability"
    for name in REQUIRED_PUBLIC_NAMES:
        assert name in public, f"missing from __all__: {name}"
        assert hasattr(world_id_module, name), f"missing attribute: {name}"


def test_world_id_wrapper_exception_and_symbol_identities_match_package() -> None:
    from ipfs_datasets_py.processors.wallets import worldcoin as package

    assert world_id_module.WorldIdConfigError is package.WorldIdConfigError
    assert world_id_module.WorldIdSignatureError is package.WorldIdSignatureError
    assert world_id_module.WorldIdVerificationError is package.WorldIdVerificationError
    assert world_id_module.WorldIdPayloadError is package.WorldIdPayloadError
    assert world_id_module.WorldIdConfig is package.WorldIdConfig
    assert world_id_module.load_world_id_config is package.load_world_id_config
    assert world_id_module.sign_world_id_request_from_config is package.sign_world_id_request_from_config
    assert world_id_module.verify_world_id_proof_from_config is package.verify_world_id_proof_from_config
    assert world_id_module.normalize_idkit_response is package.normalize_idkit_response
    assert world_id_module.redact_world_id_payload is package.redact_world_id_payload
    assert world_id_module.DEFAULT_WORLD_ID_ACTION is package.DEFAULT_WORLD_ID_ACTION
    assert world_id_module.DEFAULT_WORLD_ID_VERIFY_BASE_URL is package.DEFAULT_WORLD_ID_VERIFY_BASE_URL

    # Exception MRO / bases stay compatible with documented caller expectations.
    assert issubclass(WorldIdConfigError, ValueError)
    assert issubclass(WorldIdSignatureError, ValueError)
    assert issubclass(WorldIdPayloadError, ValueError)
    assert issubclass(WorldIdVerificationError, RuntimeError)


def test_world_id_wrapper_is_reexport_only_no_protocol_implementation() -> None:
    source = _read(WORLD_ID_PATH)
    tree = ast.parse(source)

    line_count = len(source.splitlines())
    assert line_count <= MAX_WRAPPER_LINES, f"wrapper line budget exceeded: {line_count}"

    top_level = [node for node in tree.body if not isinstance(node, ast.Expr)]
    assert len(top_level) <= MAX_WRAPPER_TOP_LEVEL_STATEMENTS, (
        f"wrapper top-level statement budget exceeded: {len(top_level)}"
    )

    defined = _function_names(tree)
    assert not defined, f"wrapper must not define classes/functions; found {sorted(defined)}"

    imported = _imported_modules(tree)
    forbidden = {
        name
        for name in imported
        if name in FORBIDDEN_IMPORT_ROOTS or name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS
    }
    assert not forbidden, f"wrapper imports forbidden modules: {sorted(forbidden)}"

    for name in imported:
        root = name.split(".")[0]
        if name.startswith("ipfs_datasets_py"):
            assert name == "ipfs_datasets_py.processors.wallets.worldcoin", name
        elif root in {"__future__"}:
            continue
        else:
            # Relative vendor bootstrap only.
            assert name in ALLOWED_IMPORT_MODULES or name.endswith("_vendor"), name

    for marker in FORBIDDEN_SOURCE_MARKERS:
        # Docstring may mention ownership terms; skip the module docstring.
        body_without_doc = source
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
            doc_end = tree.body[0].end_lineno or 1
            body_without_doc = "\n".join(source.splitlines()[doc_end:])
        assert marker not in body_without_doc, f"wrapper body must not contain {marker!r}"


def test_world_id_wrapper_has_no_network_endpoint_literal() -> None:
    source = _read(WORLD_ID_PATH)
    tree = ast.parse(source)
    # Skip module docstring which may document the default URL for reviewers.
    body_start = 0
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        body_start = tree.body[0].end_lineno or 0
    body = "\n".join(source.splitlines()[body_start:])
    assert "https://" not in body
    assert "http://" not in body
    assert "developer.world.org" not in body


def test_wallet_interface_service_retains_world_id_application_policy_methods() -> None:
    for name in (
        "get_world_id_config",
        "get_world_id_status",
        "create_world_id_rp_signature",
        "create_provider_staff_world_id_rp_signature",
        "register_world_id_verification",
        "revoke_world_id_binding",
    ):
        assert hasattr(WalletInterfaceService, name), name

    source = _read(APP_SERVICE_PATH)
    tree = ast.parse(source)

    methods: dict[str, ast.AST] = {}
    for cls in tree.body:
        if isinstance(cls, ast.ClassDef) and cls.name == "WalletInterfaceService":
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods[item.name] = item
            break

    create_sig = methods["create_world_id_rp_signature"]
    register = methods["register_world_id_verification"]
    status = methods["get_world_id_status"]
    staff = methods["create_provider_staff_world_id_rp_signature"]

    create_src = ast.get_source_segment(source, create_sig) or ""
    register_src = ast.get_source_segment(source, register) or ""
    status_src = ast.get_source_segment(source, status) or ""
    staff_src = ast.get_source_segment(source, staff) or ""

    # Actor authorization stays in 211-AI.
    assert "_require_portal_actor" in create_src
    assert "_require_portal_actor" in register_src
    assert "_require_portal_actor" in status_src

    # Protocol work is delegated through the thin wrapper imports / DTO adapter.
    assert "sign_world_id_request_from_config" in create_src
    assert "verify_world_id_proof_from_config" in register_src
    assert "normalize_world_id_idkit_response" in register_src
    assert "_world_id_verification_response_dto" in register_src or "redact_world_id_payload" in register_src
    assert "add_world_id_binding" in register_src

    # Response adapter must still redact via the package helper (not re-implement it).
    adapter = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_world_id_verification_response_dto"
        ),
        None,
    )
    if adapter is not None:
        adapter_src = ast.get_source_segment(source, adapter) or ""
        assert "redact_world_id_payload" in adapter_src
        assert "urlopen" not in adapter_src

    # Provider-staff policy remains application-owned.
    assert "provider_id" in staff_src
    assert "provider_staff_id" in staff_src
    assert "PROVIDER_STAFF_WORLD_ID_ACTION" in staff_src

    # No crypto/HTTP implementation inside the cutover-owner methods.
    for body in (create_src, register_src, status_src, staff_src):
        assert "urlopen" not in body
        assert "PrivateKey" not in body
        assert "urllib" not in body
        assert "coincurve" not in body
        assert "from Crypto" not in body
        assert "import hashlib" not in body


def test_ops_world_id_readiness_probes_delegate_to_wrapper() -> None:
    source = _read(OPS_PATH)
    tree = ast.parse(source)
    readiness = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_world_id_production_readiness_checks"
        ),
        None,
    )
    assert readiness is not None, "ops must keep World ID readiness probe composition"
    readiness_src = ast.get_source_segment(source, readiness) or ""

    assert "from .world_id import" in readiness_src or "from wallet_interface.world_id import" in readiness_src
    assert "load_world_id_config" in readiness_src
    assert "sign_world_id_request_from_config" in readiness_src
    assert "redact_world_id_payload" in readiness_src
    # Probes compose checks; they must not re-implement HTTP verification.
    assert "urlopen" not in readiness_src
    assert "verify_world_id_proof" not in readiness_src


def test_wrapper_reexports_are_callables_or_types() -> None:
    assert callable(load_world_id_config)
    assert callable(sign_world_id_request_from_config)
    assert callable(verify_world_id_proof_from_config)
    assert callable(normalize_idkit_response)
    assert callable(redact_world_id_payload)
    assert inspect.isclass(WorldIdConfig)
    assert DEFAULT_WORLD_ID_ACTION == "wallet-attach-world-id-v1"
    assert DEFAULT_WORLD_ID_VERIFY_BASE_URL == "https://developer.world.org"


def test_wrapper_module_source_mentions_ownership_boundary() -> None:
    source = _read(WORLD_ID_PATH)
    lowered = source.lower()
    assert "compatibility" in lowered or "re-export" in lowered or "reexport" in lowered
    assert "ipfs_datasets_py" in source
    assert "walproc-g130" in lowered or "walproc_g130" in lowered or "thin" in lowered
