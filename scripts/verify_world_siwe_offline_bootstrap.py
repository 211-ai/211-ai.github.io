#!/usr/bin/env python3
"""Verify the unapproved G037 SIWE packet, or a signed Gate 0B selection.

The preparation path is deliberately read-only and dependency-free: it does
not invoke npm, Node, a registry, a cache, a socket, or a package.  It validates
the exact npm lockfile-v3 closure and all executable contract digests.  The
approved path additionally delegates signature, expiry, repository-state, and
artifact verification to the canonical Gate 0B verifier before cross-binding
the SIWE-specific selection.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("wallet_interface/services/world_siwe_verifier/package.json")
LOCK = Path("wallet_interface/services/world_siwe_verifier/package-lock.json")
PROPOSAL = Path("data/worldcoin_human_aid/bootstrap/world-siwe-dependency-proposal.json")
ADAPTER = Path("wallet_interface/services/world_siwe_verifier/index.mjs")
VERIFIER = Path("scripts/verify_world_siwe_offline_bootstrap.py")
STATIC_TEST = Path("tests/world_aid/test_siwe_dependency_lock.py")
RUNTIME_TEST = Path("tests/world_aid/test_siwe_offline_bootstrap.py")
GATE_VERIFIER = Path("scripts/verify_world_aid_gate_0b.py")
CANONICAL_APPROVAL = Path("data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json")

ARTIFACT_PATHS = {
    "manifest": MANIFEST,
    "lockfile": LOCK,
    "adapter": ADAPTER,
    "verifier": VERIFIER,
    "static_contract": STATIC_TEST,
    "runtime_contract": RUNTIME_TEST,
    "gate_verifier": GATE_VERIFIER,
}
EXPECTED_DEPENDENCIES = {
    "@worldcoin/minikit-js": "2.0.3",
    "abitype": "1.2.3",
    "react": "18.3.1",
    "viem": "2.45.3",
}
EXPECTED_LOCK_METADATA = {
    "approval_status": "NOT APPROVED",
    "generated_by": "npm 10.9.8 package-lock-only with isolated ephemeral cache",
    "node": "22.23.1",
    "platform": "linux",
    "architecture": "x64",
    "registry_metadata_observed_at": "2026-07-24",
    "selection_owner": "human Gate 0B reviewers",
}
EXPECTED_EVIDENCE_PATHS = {
    "licenses": "data/worldcoin_human_aid/bootstrap/siwe-licenses.json",
    "provenance": "data/worldcoin_human_aid/bootstrap/siwe-provenance.json",
    "sbom": "data/worldcoin_human_aid/bootstrap/siwe-sbom.json",
    "vulnerability_review": "data/worldcoin_human_aid/bootstrap/siwe-vulnerability-review.json",
}
EXPECTED_CACHE_PATH = "data/worldcoin_human_aid/offline/npm"
EXPECTED_TOOLCHAIN = {
    "platform": "linux",
    "architecture": "x86_64",
    "archive_format": "tar.xz",
    "archive_path": (
        "data/worldcoin_human_aid/offline/node/"
        "node-v22.23.1-linux-x64.tar.xz"
    ),
    "root": "node-v22.23.1-linux-x64",
    "node_path": "node-v22.23.1-linux-x64/bin/node",
    "node_version": "22.23.1",
    "npm_cli_path": (
        "node-v22.23.1-linux-x64/lib/node_modules/npm/bin/npm-cli.js"
    ),
    "npm_version": "10.9.8",
}

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXACT_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PACKAGE_NAME_RE = re.compile(r"^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")
REGISTRY_TARBALL_RE = re.compile(
    r"^https://registry\.npmjs\.org/[A-Za-z0-9@._~%+/-]+\.tgz$"
)


class SiweBootstrapError(ValueError):
    """Raised when the preparation packet or signed selection fails closed."""


@dataclass(frozen=True)
class Verification:
    status: str
    manifest_sha256: str
    lock_sha256: str
    adapter_sha256: str
    verifier_sha256: str
    static_contract_sha256: str
    runtime_contract_sha256: str
    package_count: int
    closure: tuple[str, ...]
    approval_sha256: str | None = None


def _fail(message: str) -> None:
    raise SiweBootstrapError(message)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json_bytes(raw: bytes, context: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except UnicodeDecodeError as exc:
        _fail(f"{context} is not UTF-8: {exc}")
    except json.JSONDecodeError as exc:
        _fail(f"{context} is not strict JSON: {exc}")
    if not isinstance(value, dict):
        _fail(f"{context} root must be an object")
    return value


def _load_json(path: Path, context: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read {context}: {exc}")
    return _load_json_bytes(raw, context), raw


def _read_bytes(path: Path, context: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read {context}: {exc}")


def _expect_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    return value


def _expect_array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    return value


def _expect_string(value: Any, context: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        _fail(f"{context} must be a non-empty bounded string")
    return value


def _exact_keys(value: Mapping[str, Any], expected: Iterable[str], context: str) -> None:
    expected_set = set(expected)
    observed = set(value)
    if observed != expected_set:
        _fail(
            f"{context} keys differ; "
            f"missing={sorted(expected_set - observed)}, unknown={sorted(observed - expected_set)}"
        )


def _root_path(root: Path) -> Path:
    if root.is_symlink():
        _fail("repository root cannot be a symlink")
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail(f"repository root cannot be resolved: {exc}")
    if not resolved.is_dir():
        _fail("repository root must be a directory")
    return resolved


def _relative_path(value: Any, context: str) -> str:
    text = _expect_string(value, context, maximum=512)
    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or text != pure.as_posix()
        or "\\" in text
        or "//" in text
        or any(part in {"", ".", ".."} for part in pure.parts)
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        _fail(f"{context} must be a normalized repository-relative POSIX path")
    return text


def _safe_file(root: Path, relative: Path | str, context: str) -> Path:
    text = _relative_path(Path(relative).as_posix(), context)
    candidate = root.joinpath(*PurePosixPath(text).parts)
    current = root
    for part in PurePosixPath(text).parts:
        current /= part
        if current.is_symlink():
            _fail(f"{context} traverses a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        mode = resolved.stat().st_mode
    except (OSError, RuntimeError, ValueError) as exc:
        _fail(f"{context} escapes the repository or is unavailable: {exc}")
    if not stat.S_ISREG(mode):
        _fail(f"{context} must be a regular non-symlink file")
    return resolved


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        _fail(f"cannot hash {path}: {exc}")
    return f"sha256:{digest.hexdigest()}"


def _digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _tarball_snapshot_digests(path: Path, context: str) -> tuple[str, str]:
    """Calculate approval SHA-256 and lock SRI from one open-file snapshot."""

    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            _fail(f"{context} must be a regular file")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            before = os.fstat(handle.fileno())
            while chunk := handle.read(1024 * 1024):
                sha256.update(chunk)
                sha512.update(chunk)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        _fail(f"cannot hash {context}: {exc}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    def snapshot(value: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    if snapshot(before) != snapshot(after):
        _fail(f"{context} changed while it was being hashed")
    return (
        f"sha256:{sha256.hexdigest()}",
        "sha512-" + base64.b64encode(sha512.digest()).decode("ascii"),
    )


def _numeric_version(
    value: str,
    context: str,
    *,
    allowed_component_counts: frozenset[int],
) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) not in allowed_component_counts or any(
        not part or not part.isascii() or not part.isdigit() for part in parts
    ):
        _fail(f"{context} contains an unsupported narrow semver component: {value}")
    if any(len(part) > 1 and part.startswith("0") for part in parts):
        _fail(f"{context} contains a leading-zero semver component: {value}")
    return tuple(int(part) for part in (*parts, *(["0"] * (3 - len(parts)))))  # type: ignore[return-value]


def _parse_constraint(
    constraint: str,
    context: str,
) -> tuple[tuple[str, tuple[int, int, int]], ...]:
    parsed: list[tuple[str, tuple[int, int, int]]] = []
    for alternative in (part.strip() for part in constraint.split("||")):
        if not alternative:
            _fail(f"{context} contains an empty semver alternative")
        if alternative == "*":
            parsed.append(("*", (0, 0, 0)))
            continue
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", alternative):
            parsed.append(
                (
                    "exact",
                    _numeric_version(
                        alternative,
                        context,
                        allowed_component_counts=frozenset({3}),
                    ),
                )
            )
            continue
        if alternative.startswith(">="):
            parsed.append(
                (
                    "minimum",
                    _numeric_version(
                        alternative[2:],
                        context,
                        allowed_component_counts=frozenset({3}),
                    ),
                )
            )
            continue
        if alternative.startswith("~"):
            parsed.append(
                (
                    "tilde",
                    _numeric_version(
                        alternative[1:],
                        context,
                        allowed_component_counts=frozenset({3}),
                    ),
                )
            )
            continue
        if alternative.startswith("^"):
            body = alternative[1:]
            wanted = _numeric_version(
                body,
                context,
                allowed_component_counts=frozenset({1, 3}),
            )
            if wanted[0] == 0:
                _fail(f"{context} contains unsupported zero-major caret syntax")
            parsed.append(("caret", wanted))
            continue
        _fail(f"{context} contains unsupported semver syntax: {alternative}")
    return tuple(parsed)


def _satisfies_constraint(version: str, constraint: str, context: str) -> bool:
    selected = _numeric_version(
        version,
        context,
        allowed_component_counts=frozenset({3}),
    )
    parsed = _parse_constraint(constraint, context)
    return any(
        kind == "*"
        or kind == "exact"
        and selected == wanted
        or kind == "minimum"
        and selected >= wanted
        or kind == "tilde"
        and wanted <= selected < (wanted[0], wanted[1] + 1, 0)
        or kind == "caret"
        and wanted <= selected < (wanted[0] + 1, 0, 0)
        for kind, wanted in parsed
    )


def _package_name(location: str) -> str:
    marker = "node_modules/"
    if not location.startswith(marker) or location.endswith("/"):
        _fail(f"invalid lock package location: {location}")
    tail = location[len(marker) :]
    if "/node_modules/" in tail:
        tail = tail.rsplit("/node_modules/", 1)[-1]
    if tail.startswith("@"):
        parts = tail.split("/")
        if len(parts) != 2:
            _fail(f"invalid scoped lock package location: {location}")
        name = "/".join(parts)
    else:
        if "/" in tail:
            _fail(f"invalid unscoped lock package location: {location}")
        name = tail
    if not PACKAGE_NAME_RE.fullmatch(name):
        _fail(f"invalid package name at {location}")
    return name


def _tarball_path(name: str, version: str) -> str:
    slug = name.removeprefix("@").replace("/", "--")
    return f"{EXPECTED_CACHE_PATH}/tarballs/{slug}-{version}.tgz"


def _validate_sri(value: Any, context: str) -> str:
    integrity = _expect_string(value, context, maximum=128)
    if not integrity.startswith("sha512-"):
        _fail(f"{context} must use sha512 SRI")
    try:
        decoded = base64.b64decode(integrity[7:].encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        _fail(f"{context} is not valid base64 SRI: {exc}")
    if len(decoded) != hashlib.sha512().digest_size or decoded == bytes(len(decoded)):
        _fail(f"{context} is missing a real 512-bit digest")
    return integrity


def _validate_manifest(manifest: dict[str, Any]) -> None:
    _exact_keys(
        manifest,
        {
            "name",
            "version",
            "private",
            "x-world-aid-approval-status",
            "type",
            "description",
            "engines",
            "dependencies",
        },
        "manifest",
    )
    if manifest["name"] != "@211-ai/world-siwe-verifier" or manifest["version"] != "0.1.0":
        _fail("manifest identity drifted")
    if manifest["private"] is not True or manifest["type"] != "module":
        _fail("manifest must remain a private ESM package")
    if "NOT APPROVED" not in _expect_string(
        manifest["x-world-aid-approval-status"], "manifest approval status"
    ):
        _fail("manifest is not prominently marked NOT APPROVED")
    if "NOT APPROVED" not in _expect_string(manifest["description"], "manifest description"):
        _fail("manifest description is not prominently marked NOT APPROVED")
    if manifest["engines"] != {"node": ">=18.20.0 <23"}:
        _fail("manifest Node engine drifted")
    if manifest["dependencies"] != EXPECTED_DEPENDENCIES:
        _fail("manifest dependency proposal drifted from the exact human-owned candidate set")


def _resolve_dependency(
    owner_location: str,
    dependency_name: str,
    constraint: str,
    packages: Mapping[str, Any],
    *,
    required: bool,
) -> str | None:
    name_parts = tuple(dependency_name.split("/"))
    owner_parts = PurePosixPath(owner_location).parts if owner_location else ()
    candidates: list[str] = []
    if owner_parts:
        candidates.append(PurePosixPath(*owner_parts, "node_modules", *name_parts).as_posix())
        node_indexes = [index for index, part in enumerate(owner_parts) if part == "node_modules"]
        for index in reversed(node_indexes):
            candidates.append(
                PurePosixPath(*owner_parts[:index], "node_modules", *name_parts).as_posix()
            )
    else:
        candidates.append(PurePosixPath("node_modules", *name_parts).as_posix())
    for candidate in dict.fromkeys(candidates):
        if candidate in packages:
            selected = _expect_string(
                _expect_object(packages[candidate], f"lock package {candidate}").get("version"),
                f"{candidate}.version",
                maximum=128,
            )
            if not _satisfies_constraint(
                selected,
                constraint,
                f"constraint {dependency_name}={constraint!r} from {owner_location or '<root>'}",
            ):
                _fail(
                    f"lock resolves {dependency_name}={selected} outside constraint "
                    f"{constraint!r} from {owner_location or '<root>'}"
                )
            return candidate
    if required:
        _fail(f"lock closure cannot resolve {dependency_name!r} from {owner_location or '<root>'}")
    return None


def _validate_dependency_map(value: Any, context: str) -> dict[str, str]:
    if value is None:
        return {}
    mapping = _expect_object(value, context)
    result: dict[str, str] = {}
    for name, constraint in mapping.items():
        if not isinstance(name, str) or not PACKAGE_NAME_RE.fullmatch(name):
            _fail(f"{context} contains an invalid package name")
        constraint_text = _expect_string(constraint, f"{context}.{name}", maximum=128)
        _parse_constraint(constraint_text, f"{context}.{name}")
        result[name] = constraint_text
    return result


def _validate_lock_entry(location: str, value: Any) -> dict[str, Any]:
    item = _expect_object(value, f"lock.packages[{location!r}]")
    for unsafe_flag in ("dev", "optional", "peer", "link", "inBundle", "hasInstallScript"):
        if item.get(unsafe_flag):
            _fail(f"lock entry {location} has unsupported {unsafe_flag}=true")
    if "scripts" in item or "bundleDependencies" in item or "bundledDependencies" in item:
        _fail(f"lock entry {location} contains unreviewed scripts or bundled dependencies")
    if item.get("optionalDependencies"):
        _fail(f"lock entry {location} contains unreviewed optional dependencies")
    version = _expect_string(item.get("version"), f"{location}.version", maximum=128)
    if not EXACT_VERSION_RE.fullmatch(version):
        _fail(f"{location}.version is not exact")
    resolved = _expect_string(item.get("resolved"), f"{location}.resolved", maximum=512)
    package_name = _package_name(location)
    expected_resolved = (
        f"https://registry.npmjs.org/{package_name}/-/"
        f"{package_name.rsplit('/', 1)[-1]}-{version}.tgz"
    )
    if (
        not REGISTRY_TARBALL_RE.fullmatch(resolved)
        or ".." in resolved
        or "?" in resolved
        or "#" in resolved
        or resolved != expected_resolved
    ):
        _fail(
            f"{location}.resolved is not the exact official-registry URL for "
            f"{package_name}@{version}"
        )
    _validate_sri(item.get("integrity"), f"{location}.integrity")
    _expect_string(item.get("license"), f"{location}.license", maximum=128)
    engines = _expect_object(item.get("engines"), f"{location}.engines")
    node_engine = _expect_string(engines.get("node"), f"{location}.engines.node", maximum=128)
    source = item.get("x-world-aid-engine-source")
    if source not in {"registry-declared", "registry-not-declared"}:
        _fail(f"{location} lacks an engine-source inventory marker")
    if source == "registry-not-declared" and node_engine != "*":
        _fail(f"{location} invents a registry-undeclared Node constraint")
    _validate_dependency_map(item.get("dependencies"), f"{location}.dependencies")
    peers = _validate_dependency_map(item.get("peerDependencies"), f"{location}.peerDependencies")
    peer_meta = _expect_object(item.get("peerDependenciesMeta", {}), f"{location}.peerDependenciesMeta")
    if not set(peer_meta) <= set(peers):
        _fail(f"{location}.peerDependenciesMeta names an undeclared peer")
    for name, metadata in peer_meta.items():
        if metadata != {"optional": True}:
            _fail(f"{location}.peerDependenciesMeta.{name} is not the exact optional marker")
    return item


def _validate_lock(manifest: dict[str, Any], lock: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    _exact_keys(
        lock,
        {
            "name",
            "version",
            "lockfileVersion",
            "requires",
            "packages",
            "x-world-aid-approval-status",
            "x-world-aid-lock-proposal",
        },
        "lock",
    )
    if lock["name"] != manifest["name"] or lock["version"] != manifest["version"]:
        _fail("lock identity differs from manifest")
    if lock["lockfileVersion"] != 3 or lock["requires"] is not True:
        _fail("SIWE lock must be npm lockfile v3 with requires=true")
    if "NOT APPROVED" not in _expect_string(
        lock["x-world-aid-approval-status"],
        "lock.x-world-aid-approval-status",
    ):
        _fail("lock is not prominently marked NOT APPROVED")
    if lock["x-world-aid-lock-proposal"] != EXPECTED_LOCK_METADATA:
        _fail("lock generation metadata drifted")
    packages_raw = _expect_object(lock["packages"], "lock.packages")
    root = _expect_object(packages_raw.get(""), "lock root package")
    _exact_keys(root, {"name", "version", "dependencies", "engines"}, "lock root package")
    if (
        root["name"] != manifest["name"]
        or root["version"] != manifest["version"]
        or root["dependencies"] != manifest["dependencies"]
        or root["engines"] != manifest["engines"]
    ):
        _fail("lock root package differs from manifest")

    packages: dict[str, dict[str, Any]] = {}
    for location, item in packages_raw.items():
        if location == "":
            continue
        normalized = _relative_path(location, f"lock package location {location!r}")
        if normalized != location or "/node_modules/" in location and location.startswith("/"):
            _fail(f"lock package location is not normalized: {location}")
        _package_name(location)
        packages[location] = _validate_lock_entry(location, item)
    if not packages:
        _fail("lock has no resolved dependency closure")

    queue: list[str] = []
    for dependency_name, constraint in sorted(EXPECTED_DEPENDENCIES.items()):
        resolved = _resolve_dependency(
            "", dependency_name, constraint, packages, required=True
        )
        assert resolved is not None
        queue.append(resolved)
    reachable: set[str] = set()
    while queue:
        location = queue.pop()
        if location in reachable:
            continue
        reachable.add(location)
        item = packages[location]
        dependencies = _validate_dependency_map(item.get("dependencies"), f"{location}.dependencies")
        for name, constraint in sorted(dependencies.items()):
            resolved = _resolve_dependency(
                location, name, constraint, packages, required=True
            )
            assert resolved is not None
            queue.append(resolved)
        peers = _validate_dependency_map(item.get("peerDependencies"), f"{location}.peerDependencies")
        peer_meta = _expect_object(item.get("peerDependenciesMeta", {}), f"{location}.peerDependenciesMeta")
        for name, constraint in sorted(peers.items()):
            optional = peer_meta.get(name) == {"optional": True}
            resolved = _resolve_dependency(
                location,
                name,
                constraint,
                packages,
                required=not optional,
            )
            if resolved is not None:
                queue.append(resolved)
    if reachable != set(packages):
        _fail(
            "lock contains unreachable or omits reachable packages; "
            f"unreachable={sorted(set(packages) - reachable)}"
        )
    return packages, tuple(sorted(reachable))


def _closure_record(location: str, item: Mapping[str, Any]) -> dict[str, str]:
    name = _package_name(location)
    return {
        "location": location,
        "name": name,
        "version": item["version"],
        "integrity": item["integrity"],
        "resolved": item["resolved"],
        "license": item["license"],
        "engine_node": item["engines"]["node"],
        "engine_source": item["x-world-aid-engine-source"],
        "proposed_tarball_path": _tarball_path(name, item["version"]),
    }


def _validate_artifact_binding(
    value: Any,
    context: str,
    expected_path: Path,
    expected_digest: str,
) -> None:
    artifact = _expect_object(value, context)
    _exact_keys(artifact, {"path", "sha256"}, context)
    if artifact["path"] != expected_path.as_posix():
        _fail(f"{context}.path must be {expected_path.as_posix()}")
    digest = _expect_string(artifact["sha256"], f"{context}.sha256", maximum=71)
    if not SHA256_RE.fullmatch(digest) or digest != expected_digest:
        _fail(f"{context}.sha256 does not bind the current repository artifact")


def _validate_proposal(
    proposal: dict[str, Any],
    packages: Mapping[str, Mapping[str, Any]],
    digests: Mapping[str, str],
) -> tuple[str, ...]:
    _exact_keys(
        proposal,
        {
            "schema_version",
            "status",
            "goal_id",
            "authority_statement",
            "approval",
            "artifacts",
            "selection_proposal",
            "lock_generation",
            "supply_chain_review",
            "constraints",
            "non_execution_boundary",
        },
        "proposal",
    )
    if proposal["schema_version"] != "world-aid-siwe-dependency-proposal/v2":
        _fail("proposal schema version drifted")
    if proposal["status"] != "NOT APPROVED":
        _fail("proposal status must be exactly NOT APPROVED")
    if proposal["goal_id"] != "WORLDCOIN-G037":
        _fail("proposal goal ID drifted")
    if "NOT APPROVED" not in _expect_string(
        proposal["authority_statement"], "proposal.authority_statement"
    ):
        _fail("proposal lacks the prominent non-approval authority statement")

    approval = _expect_object(proposal["approval"], "proposal.approval")
    _exact_keys(
        approval,
        {
            "required",
            "binding",
            "canonical_path",
            "selection_owner",
            "cache_presence_is_not_trust",
        },
        "proposal.approval",
    )
    if (
        approval["required"] is not True
        or approval["binding"] != "canonical signed Gate 0B-selection"
        or approval["canonical_path"] != CANONICAL_APPROVAL.as_posix()
        or approval["selection_owner"] != "human Gate 0B reviewers"
        or approval["cache_presence_is_not_trust"] is not True
    ):
        _fail("proposal approval boundary drifted")

    artifacts = _expect_object(proposal["artifacts"], "proposal.artifacts")
    _exact_keys(artifacts, ARTIFACT_PATHS, "proposal.artifacts")
    for name, path in ARTIFACT_PATHS.items():
        _validate_artifact_binding(
            artifacts[name],
            f"proposal.artifacts.{name}",
            path,
            digests[name],
        )

    selection = _expect_object(proposal["selection_proposal"], "proposal.selection_proposal")
    _exact_keys(
        selection,
        {"direct", "closure", "minimum_runtime", "human_decisions"},
        "proposal.selection_proposal",
    )
    direct = _expect_array(selection["direct"], "proposal.selection_proposal.direct")
    expected_direct = [
        {"name": name, "version": version, "selection_status": "human-owned-unapproved"}
        for name, version in sorted(EXPECTED_DEPENDENCIES.items())
    ]
    if direct != expected_direct:
        _fail("proposal direct dependency set differs from the exact manifest proposal")
    expected_closure = [_closure_record(location, packages[location]) for location in sorted(packages)]
    if selection["closure"] != expected_closure:
        _fail("proposal closure does not exactly mirror the validated lock closure")
    if selection["minimum_runtime"] is not True:
        _fail("proposal must explain its minimum-runtime boundary")
    decisions = _expect_object(selection["human_decisions"], "proposal.selection_proposal.human_decisions")
    _exact_keys(
        decisions,
        {"minikit", "viem", "react_peer", "closure", "runtime_toolchain"},
        "proposal.selection_proposal.human_decisions",
    )
    if set(decisions.values()) != {"unapproved; human Gate 0B decision required"}:
        _fail("proposal improperly claims an agent-owned dependency decision")

    generation = _expect_object(proposal["lock_generation"], "proposal.lock_generation")
    _exact_keys(
        generation,
        {
            "status",
            "performed_at",
            "tool",
            "node",
            "platform",
            "architecture",
            "operation",
            "registry",
            "network_use",
            "cache",
            "package_execution",
            "node_modules_created",
            "tarballs_downloaded",
            "failed_draft_observation",
            "validation_replay",
        },
        "proposal.lock_generation",
    )
    expected_generation = {
        "status": "controlled-unapproved-proposal-generation",
        "performed_at": "2026-07-24",
        "tool": "npm 10.9.8",
        "node": "22.23.1",
        "platform": "linux",
        "architecture": "x64",
        "operation": "npm install --package-lock-only --ignore-scripts --audit=false --fund=false",
        "registry": "https://registry.npmjs.org",
        "network_use": "official registry metadata was read to construct the unapproved lock proposal",
        "cache": "isolated ephemeral mktemp caches; the user cache was not used for lock generation",
        "package_execution": False,
        "node_modules_created": False,
        "tarballs_downloaded": False,
        "failed_draft_observation": (
            "a rejected agent draft ran read-only npm cache ls, found no MiniKit basis, "
            "and was fenced before validation, commit, or enqueue"
        ),
        "validation_replay": (
            "the G037 verifier and static tests perform no npm or Node invocation, "
            "network access, cache access, installation, package execution, or lock regeneration"
        ),
    }
    if generation != expected_generation:
        _fail("proposal lock-generation receipt is incomplete or inaccurate")

    review = _expect_object(proposal["supply_chain_review"], "proposal.supply_chain_review")
    _exact_keys(
        review,
        {
            "lifecycle_scripts",
            "licenses",
            "provenance",
            "sbom",
            "vulnerability_review",
            "cache",
            "tarballs",
            "runtime_toolchain",
        },
        "proposal.supply_chain_review",
    )
    if review["lifecycle_scripts"] != {
        "proposed": [],
        "status": "human tarball review required before Gate 0B",
        "install_policy": "npm ci --offline --ignore-scripts",
    }:
        _fail("proposal lifecycle-script review boundary drifted")
    for key, path in EXPECTED_EVIDENCE_PATHS.items():
        if review[key] != {"path": path, "status": "human evidence required before Gate 0B"}:
            _fail(f"proposal {key} evidence boundary drifted")
    if review["cache"] != {
        "path": EXPECTED_CACHE_PATH,
        "read_only": True,
        "tree_sha256": None,
        "status": "human staging and review required before Gate 0B",
        "is_trust": False,
    }:
        _fail("proposal cache review boundary drifted")
    if review["runtime_toolchain"] != {
        **EXPECTED_TOOLCHAIN,
        "status": (
            "not staged; exact symlink-free archive, member digests, provenance, "
            "and licenses require human Gate 0B review"
        ),
    }:
        _fail("proposal runtime-toolchain review boundary drifted")
    proposed_tarballs = tuple(record["proposed_tarball_path"] for record in expected_closure)
    if review["tarballs"] != {
        "paths": list(proposed_tarballs),
        "status": "not staged; exact tarballs and sha256 digests require human Gate 0B review",
    }:
        _fail("proposal tarball review boundary drifted")

    if proposal["constraints"] != {
        "node": ">=18.20.0 <23",
        "lockfile": "npm lockfileVersion 3",
        "runtime_network": (
            "G038 requires signed OS-level egress denial and a local mock; the receipt proves "
            "no successful external egress and boundary stability while attempt count remains unobserved"
        ),
        "g038_install": "isolated npm ci --offline --ignore-scripts after signed selection only",
        "g038_launcher": (
            "blocked until an operator-controlled Gate-first supervisor launcher authenticates "
            "the canonical Gate, SIWE verifier, and runtime entrypoint before repository code runs"
        ),
    }:
        _fail("proposal runtime constraints drifted")
    if proposal["non_execution_boundary"] != {
        "static_validation_performed": True,
        "package_installation": False,
        "package_execution": False,
        "live_world_api_calls": False,
        "world_chain_calls": False,
        "token_transfers": False,
        "approval_created": False,
    }:
        _fail("proposal non-execution boundary drifted")
    return proposed_tarballs


def _validate_adapter(source: str) -> None:
    required_fragments = {
        'from "@worldcoin/minikit-js/siwe"',
        "parseSiweMessage",
        "verifySiweMessage",
        'exactKeys(runtime, ["client", "now"], "SIWE runtime")',
        '"expirationTime"',
        '"issuedAt"',
        '"maxAgeSeconds"',
        '"notBefore"',
        '"version"',
        '["address", "message", "signature"]',
        "parsed.address.toLowerCase() !== address.toLowerCase()",
        "expected.nonce",
        "expected.statement",
        "expected.request_id",
        "expected.issued_at",
        "expected.expiration_time",
        "expected.not_before",
        "runtime.now",
        "policy.version must be exactly 1",
        "policy.maxAgeSeconds cannot exceed 900",
        "client.chain.id !== chainId",
        'typeof client.readContract !== "function"',
        "expirationMilliseconds - issuedMilliseconds > maxAgeSeconds * 1000",
        "client,",
        "NOT APPROVED",
    }
    missing = sorted(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        _fail(f"SIWE adapter contract is incomplete: {missing}")
    lowered = source.lower()
    for forbidden in (
        "createpublicclient",
        "http(",
        "websocket(",
        "fetch(",
        "https://",
        "wss://",
        "process.env",
        "child_process",
    ):
        if forbidden in lowered:
            _fail(f"SIWE adapter contains a forbidden implicit transport primitive: {forbidden}")


def _external_allowed_signers(root: Path, path: Path | None) -> Path:
    if path is None:
        _fail("an external --allowed-signers trust file is required for approved verification")
    if not path.is_absolute():
        _fail("--allowed-signers must be an absolute operator-controlled path")
    if path.is_symlink():
        _fail("--allowed-signers cannot be a symlink")
    try:
        resolved = path.resolve(strict=True)
        mode = resolved.stat().st_mode
    except (OSError, RuntimeError) as exc:
        _fail(f"--allowed-signers cannot be resolved: {exc}")
    if not stat.S_ISREG(mode):
        _fail("--allowed-signers must be a regular file")
    try:
        resolved.relative_to(root)
    except ValueError:
        return resolved
    _fail("--allowed-signers must be external to the repository")


def _canonical_approval(root: Path, supplied: Path | None) -> Path:
    if supplied is None:
        _fail("the canonical signed Gate 0B-selection approval is required")
    expected = root / CANONICAL_APPROVAL
    candidate = supplied if supplied.is_absolute() else root / supplied
    try:
        if candidate.absolute() != expected.absolute():
            _fail(f"approval must use canonical path {CANONICAL_APPROVAL.as_posix()}")
    except OSError as exc:
        _fail(f"approval path cannot be resolved: {exc}")
    return _safe_file(root, CANONICAL_APPROVAL, "canonical approval")


def _load_pinned_gate_verifier(
    path: Path,
    raw: bytes,
    expected_digest: str | None,
) -> tuple[type[Exception], str, Any]:
    """Execute only the exact canonical verifier bytes pinned by the operator."""

    if expected_digest is None:
        _fail(
            "an external --gate-verifier-sha256 trust anchor is required "
            "for approved verification"
        )
    if not isinstance(expected_digest, str) or not SHA256_RE.fullmatch(expected_digest):
        _fail("--gate-verifier-sha256 must be a lowercase sha256 digest")
    observed = _digest_bytes(raw)
    if observed != expected_digest:
        _fail("canonical Gate verifier differs from the external trust anchor")
    if path != path.parent.parent / GATE_VERIFIER:
        _fail("canonical Gate verifier path drifted")

    module = ModuleType("_world_aid_pinned_gate_0b")
    module.__file__ = str(path)
    module.__package__ = ""
    try:
        code = compile(raw, str(path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except Exception as exc:
        _fail(f"cannot execute the externally pinned canonical Gate verifier: {exc}")

    approval_error = module.__dict__.get("ApprovalVerificationError")
    selection = module.__dict__.get("SELECTION")
    verify_approval = module.__dict__.get("verify_approval")
    if (
        not isinstance(approval_error, type)
        or not issubclass(approval_error, Exception)
        or selection != "selection"
        or not callable(verify_approval)
    ):
        _fail("externally pinned canonical Gate verifier exports are invalid")
    return approval_error, selection, verify_approval


def _cross_bind_approved_selection(
    repo_root: Path,
    record: dict[str, Any],
    packages: Mapping[str, Mapping[str, Any]],
    digests: Mapping[str, str],
    proposed_tarballs: Sequence[str],
) -> None:
    dependencies = _expect_object(record.get("dependency_sets"), "approval.dependency_sets")
    siwe = _expect_object(dependencies.get("siwe"), "approval.dependency_sets.siwe")
    toolchain = _expect_object(
        siwe.get("runtime_toolchain"),
        "approval.dependency_sets.siwe.runtime_toolchain",
    )
    _exact_keys(
        toolchain,
        {
            "platform",
            "architecture",
            "archive_format",
            "archive",
            "root",
            "node",
            "npm_cli",
        },
        "approval.dependency_sets.siwe.runtime_toolchain",
    )
    for key in ("platform", "architecture", "archive_format", "root"):
        if toolchain.get(key) != EXPECTED_TOOLCHAIN[key]:
            _fail(f"signed SIWE runtime toolchain {key} differs from the proposal")
    archive = _expect_object(
        toolchain["archive"],
        "approval.dependency_sets.siwe.runtime_toolchain.archive",
    )
    _exact_keys(
        archive,
        {"path", "sha256"},
        "approval.dependency_sets.siwe.runtime_toolchain.archive",
    )
    if archive.get("path") != EXPECTED_TOOLCHAIN["archive_path"]:
        _fail("signed SIWE runtime toolchain archive path differs from the proposal")
    archive_digest = _expect_string(
        archive.get("sha256"),
        "approval.dependency_sets.siwe.runtime_toolchain.archive.sha256",
        maximum=71,
    )
    if not SHA256_RE.fullmatch(archive_digest):
        _fail("signed SIWE runtime toolchain archive digest is invalid")
    archive_path = _safe_file(
        repo_root,
        archive["path"],
        "approved SIWE runtime toolchain archive",
    )
    if _digest(archive_path) != archive_digest:
        _fail("signed SIWE runtime toolchain archive digest drifted")
    for key, path_key, version_key in (
        ("node", "node_path", "node_version"),
        ("npm_cli", "npm_cli_path", "npm_version"),
    ):
        context = f"approval.dependency_sets.siwe.runtime_toolchain.{key}"
        member = _expect_object(toolchain[key], context)
        _exact_keys(member, {"path", "sha256", "version"}, context)
        if (
            member.get("path") != EXPECTED_TOOLCHAIN[path_key]
            or member.get("version") != EXPECTED_TOOLCHAIN[version_key]
        ):
            _fail(f"signed SIWE runtime toolchain {key} differs from the proposal")
        member_digest = _expect_string(
            member.get("sha256"),
            f"{context}.sha256",
            maximum=71,
        )
        if not SHA256_RE.fullmatch(member_digest):
            _fail(f"{context}.sha256 is invalid")
    for name, path in (("manifest", MANIFEST), ("lockfile", LOCK)):
        _validate_artifact_binding(
            siwe.get(name),
            f"approval.dependency_sets.siwe.{name}",
            path,
            digests[name],
        )
    tarballs = _expect_array(siwe.get("tarballs"), "approval.dependency_sets.siwe.tarballs")
    observed_tarballs: list[tuple[str, str]] = []
    for index, value in enumerate(tarballs):
        artifact = _expect_object(value, f"approval.dependency_sets.siwe.tarballs[{index}]")
        _exact_keys(
            artifact,
            {"path", "sha256"},
            f"approval.dependency_sets.siwe.tarballs[{index}]",
        )
        path_text = _relative_path(
            artifact["path"],
            f"approval.dependency_sets.siwe.tarballs[{index}].path",
        )
        digest = _expect_string(
            artifact["sha256"],
            f"approval.dependency_sets.siwe.tarballs[{index}].sha256",
            maximum=71,
        )
        if not SHA256_RE.fullmatch(digest):
            _fail(f"approval.dependency_sets.siwe.tarballs[{index}].sha256 is invalid")
        observed_tarballs.append((path_text, digest))
    observed_paths = [path for path, _ in observed_tarballs]
    if observed_paths != list(proposed_tarballs):
        _fail("signed selection tarballs differ from the exact proposed closure")
    for location, (path_text, expected_sha256) in zip(
        sorted(packages),
        observed_tarballs,
        strict=True,
    ):
        expected_sri = packages[location]["integrity"]
        tarball_path = _safe_file(
            repo_root,
            path_text,
            f"approved tarball for {location}",
        )
        observed_sha256, observed_sri = _tarball_snapshot_digests(
            tarball_path,
            f"approved tarball for {location}",
        )
        if observed_sha256 != expected_sha256:
            _fail(f"signed tarball sha256 drifted: {path_text}")
        if observed_sri != expected_sri:
            _fail(f"approved tarball does not match lock SHA-512 SRI for {location}")
    cache = _expect_object(siwe.get("cache"), "approval.dependency_sets.siwe.cache")
    _exact_keys(
        cache,
        {"path", "read_only", "tree_sha256"},
        "approval.dependency_sets.siwe.cache",
    )
    if (
        cache.get("path") != EXPECTED_CACHE_PATH
        or cache.get("read_only") is not True
        or not isinstance(cache.get("tree_sha256"), str)
        or not SHA256_RE.fullmatch(cache["tree_sha256"])
    ):
        _fail("signed selection does not bind the proposed read-only cache")
    if siwe.get("lifecycle_scripts") != []:
        _fail("signed selection authorizes unexpected SIWE lifecycle scripts")
    for key, path in EXPECTED_EVIDENCE_PATHS.items():
        artifact = _expect_object(siwe.get(key), f"approval.dependency_sets.siwe.{key}")
        _exact_keys(artifact, {"path", "sha256"}, f"approval.dependency_sets.siwe.{key}")
        if artifact.get("path") != path:
            _fail(f"approval.dependency_sets.siwe.{key}.path must be {path}")
        digest = _expect_string(
            artifact.get("sha256"),
            f"approval.dependency_sets.siwe.{key}.sha256",
            maximum=71,
        )
        if not SHA256_RE.fullmatch(digest):
            _fail(f"approval.dependency_sets.siwe.{key}.sha256 is invalid")
        evidence_path = _safe_file(repo_root, path, f"approval.dependency_sets.siwe.{key}")
        if _digest(evidence_path) != digest:
            _fail(f"signed {key} evidence digest drifted")
    reviewed = _expect_object(record.get("reviewed_state"), "approval.reviewed_state")
    for name, artifact_name, expected_path in (
        ("siwe_adapter", "adapter", ADAPTER),
        ("siwe_proposal", "proposal", PROPOSAL),
        ("siwe_static_test", "static_contract", STATIC_TEST),
        ("siwe_verifier", "verifier", VERIFIER),
        ("siwe_runtime_test", "runtime_contract", RUNTIME_TEST),
    ):
        _validate_artifact_binding(
            reviewed.get(name),
            f"approval.reviewed_state.{name}",
            expected_path,
            digests[artifact_name],
        )


def verify_world_siwe_offline_bootstrap(
    root: Path = ROOT,
    *,
    approval: Path | None = None,
    allowed_signers: Path | None = None,
    gate_verifier_sha256: str | None = None,
    require_approval: bool = False,
) -> Verification:
    """Verify the static packet; optionally require a canonical signed selection."""

    repo_root = _root_path(root)
    paths = {
        name: _safe_file(repo_root, relative, f"{name} artifact")
        for name, relative in ARTIFACT_PATHS.items()
    }
    manifest, manifest_raw = _load_json(paths["manifest"], "manifest")
    lock, lock_raw = _load_json(paths["lockfile"], "lockfile")
    proposal_path = _safe_file(repo_root, PROPOSAL, "proposal artifact")
    proposal, proposal_raw = _load_json(proposal_path, "proposal")
    raw_artifacts = {
        "manifest": manifest_raw,
        "lockfile": lock_raw,
        "adapter": _read_bytes(paths["adapter"], "adapter artifact"),
        "verifier": _read_bytes(paths["verifier"], "verifier artifact"),
        "static_contract": _read_bytes(paths["static_contract"], "static contract"),
        "runtime_contract": _read_bytes(paths["runtime_contract"], "runtime contract"),
        "gate_verifier": _read_bytes(paths["gate_verifier"], "canonical Gate verifier"),
    }
    _validate_manifest(manifest)
    packages, closure = _validate_lock(manifest, lock)
    digests = {name: _digest_bytes(raw) for name, raw in raw_artifacts.items()}
    digests["proposal"] = _digest_bytes(proposal_raw)
    proposed_tarballs = _validate_proposal(proposal, packages, digests)
    try:
        adapter_source = raw_artifacts["adapter"].decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"cannot read SIWE adapter: {exc}")
    _validate_adapter(adapter_source)

    approved = require_approval or approval is not None
    status = "NOT APPROVED"
    approval_sha256: str | None = None
    if approved:
        approval_path = _canonical_approval(repo_root, approval)
        trust_path = _external_allowed_signers(repo_root, allowed_signers)
        try:
            before = approval_path.read_bytes()
        except OSError as exc:
            _fail(f"cannot read canonical approval: {exc}")
        record = _load_json_bytes(before, "canonical approval")
        approval_error, selection, canonical_verify_approval = _load_pinned_gate_verifier(
            paths["gate_verifier"],
            raw_artifacts["gate_verifier"],
            gate_verifier_sha256,
        )
        try:
            gate_summary = canonical_verify_approval(
                repo_root=repo_root,
                phase=selection,
                approval_path=approval_path,
                allowed_signers_path=trust_path,
                expected_approval_bytes=before,
            )
        except approval_error as exc:
            _fail(f"canonical Gate 0B verification rejected the selection: {exc}")
        approval_sha256 = _digest_bytes(before)
        if gate_summary.get("verified_approval_sha256") != approval_sha256:
            _fail("canonical Gate verifier did not attest the caller-captured approval")
        try:
            after = approval_path.read_bytes()
        except OSError as exc:
            _fail(f"cannot reread canonical approval: {exc}")
        if before != after:
            _fail("canonical approval changed during verification")
        _cross_bind_approved_selection(
            repo_root,
            record,
            packages,
            digests,
            proposed_tarballs,
        )
        status = "approved-selection-bound"

    for name, path in paths.items():
        if _digest(path) != digests[name]:
            _fail(f"{name} artifact changed during verification")
    if _read_bytes(proposal_path, "proposal artifact") != proposal_raw:
        _fail("proposal artifact changed during verification")
    if approved:
        try:
            final_approval = approval_path.read_bytes()
        except OSError as exc:
            _fail(f"cannot perform the final canonical approval reread: {exc}")
        if before != final_approval:
            _fail("canonical approval changed before verification completed")

    return Verification(
        status=status,
        manifest_sha256=digests["manifest"],
        lock_sha256=digests["lockfile"],
        adapter_sha256=digests["adapter"],
        verifier_sha256=digests["verifier"],
        static_contract_sha256=digests["static_contract"],
        runtime_contract_sha256=digests["runtime_contract"],
        package_count=len(packages),
        closure=closure,
        approval_sha256=approval_sha256,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--approval", type=Path)
    parser.add_argument(
        "--allowed-signers",
        type=Path,
        default=Path(os.environ["WORLD_AID_ALLOWED_SIGNERS"])
        if os.environ.get("WORLD_AID_ALLOWED_SIGNERS")
        else None,
    )
    parser.add_argument(
        "--gate-verifier-sha256",
        default=os.environ.get("WORLD_AID_GATE_VERIFIER_SHA256"),
        help="External sha256 trust anchor for scripts/verify_world_aid_gate_0b.py.",
    )
    parser.add_argument("--require-approval", action="store_true")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Required acknowledgement that external access is denied.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.offline:
        print("SIWE verification rejected: --offline is required", file=sys.stderr)
        return 2
    try:
        result = verify_world_siwe_offline_bootstrap(
            args.root,
            approval=args.approval,
            allowed_signers=args.allowed_signers,
            gate_verifier_sha256=args.gate_verifier_sha256,
            require_approval=args.require_approval,
        )
    except SiweBootstrapError as exc:
        print(f"SIWE verification rejected: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": result.status,
                "manifest_sha256": result.manifest_sha256,
                "lock_sha256": result.lock_sha256,
                "adapter_sha256": result.adapter_sha256,
                "verifier_sha256": result.verifier_sha256,
                "static_contract_sha256": result.static_contract_sha256,
                "runtime_contract_sha256": result.runtime_contract_sha256,
                "package_count": result.package_count,
                "closure": list(result.closure),
                "offline": True,
                "package_execution": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
