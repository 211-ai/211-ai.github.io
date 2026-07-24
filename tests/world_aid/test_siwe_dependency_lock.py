"""Static, repository-only WORLDCOIN-G037 acceptance contract."""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import urllib.request
from pathlib import Path

import pytest

import scripts.verify_world_siwe_offline_bootstrap as siwe_bootstrap
from scripts.verify_world_aid_gate_0b import PROTECTED_WRITABLE_PATHS
from scripts.verify_world_siwe_offline_bootstrap import (
    ADAPTER,
    ARTIFACT_PATHS,
    CANONICAL_APPROVAL,
    EXPECTED_DEPENDENCIES,
    EXPECTED_LOCK_METADATA,
    GATE_VERIFIER,
    LOCK,
    MANIFEST,
    PROPOSAL,
    ROOT,
    RUNTIME_TEST,
    STATIC_TEST,
    SiweBootstrapError,
    _load_pinned_gate_verifier,
    _tarball_snapshot_digests,
    main,
    verify_world_siwe_offline_bootstrap,
)

SCRIPT = ROOT / "scripts/verify_world_siwe_offline_bootstrap.py"
HEAP = ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
EXPECTED_PACKAGE_COUNT = 17


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _packet_copy(tmp_path: Path) -> Path:
    copied_root = tmp_path / "repo"
    for relative in (*ARTIFACT_PATHS.values(), PROPOSAL):
        destination = copied_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    return copied_root


def _forbidden(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("static G037 verification crossed its read-only boundary")


def test_static_verifier_passes_without_process_network_cache_or_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subprocess, "run", _forbidden)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    monkeypatch.setattr(socket, "socket", _forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)
    monkeypatch.setattr(os, "system", _forbidden)
    monkeypatch.setattr(Path, "write_text", _forbidden)
    monkeypatch.setattr(Path, "write_bytes", _forbidden)
    result = verify_world_siwe_offline_bootstrap()
    assert result.status == "NOT APPROVED"
    assert result.package_count == EXPECTED_PACKAGE_COUNT
    assert len(result.closure) == EXPECTED_PACKAGE_COUNT


def test_manifest_and_complete_lock_closure_are_exact() -> None:
    manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["dependencies"] == EXPECTED_DEPENDENCIES
    assert "scripts" not in manifest
    assert "NOT APPROVED" in manifest["description"]

    lock = json.loads((ROOT / LOCK).read_text(encoding="utf-8"))
    assert lock["lockfileVersion"] == 3
    assert lock["requires"] is True
    assert lock["x-world-aid-lock-proposal"] == EXPECTED_LOCK_METADATA
    assert lock["packages"][""]["dependencies"] == EXPECTED_DEPENDENCIES
    packages = {location: value for location, value in lock["packages"].items() if location}
    assert len(packages) == EXPECTED_PACKAGE_COUNT
    assert {
        packages["node_modules/@worldcoin/minikit-js"]["version"],
        packages["node_modules/viem"]["version"],
        packages["node_modules/react"]["version"],
        packages["node_modules/abitype"]["version"],
    } == {"2.0.3", "2.45.3", "18.3.1", "1.2.3"}
    for location, entry in packages.items():
        assert entry["resolved"].startswith("https://registry.npmjs.org/")
        assert len(base64.b64decode(entry["integrity"].removeprefix("sha512-"), validate=True)) == 64
        assert entry["license"]
        assert entry["engines"]["node"]
        assert entry["x-world-aid-engine-source"] in {
            "registry-declared",
            "registry-not-declared",
        }
        assert not {
            key for key in ("dev", "optional", "peer", "link", "hasInstallScript") if entry.get(key)
        }, location


def test_proposal_binds_every_executable_contract_and_human_decision() -> None:
    proposal = json.loads((ROOT / PROPOSAL).read_text(encoding="utf-8"))
    assert proposal["status"] == "NOT APPROVED"
    assert "NOT APPROVED" in proposal["authority_statement"]
    assert proposal["approval"]["selection_owner"] == "human Gate 0B reviewers"
    for name, relative in ARTIFACT_PATHS.items():
        assert proposal["artifacts"][name] == {
            "path": relative.as_posix(),
            "sha256": _sha256(ROOT / relative),
        }
    decisions = proposal["selection_proposal"]["human_decisions"]
    assert set(decisions.values()) == {"unapproved; human Gate 0B decision required"}
    assert len(proposal["selection_proposal"]["closure"]) == EXPECTED_PACKAGE_COUNT
    assert proposal["supply_chain_review"]["cache"]["is_trust"] is False
    assert proposal["supply_chain_review"]["runtime_toolchain"]["status"].startswith("not staged")
    assert proposal["lock_generation"]["network_use"].startswith("official registry metadata")
    assert proposal["lock_generation"]["package_execution"] is False
    assert proposal["lock_generation"]["tarballs_downloaded"] is False
    assert proposal["non_execution_boundary"]["approval_created"] is False


def test_duplicate_json_and_placeholder_integrity_fail_closed(tmp_path: Path) -> None:
    copied_root = _packet_copy(tmp_path)
    lock_path = copied_root / LOCK
    raw = lock_path.read_text(encoding="utf-8")
    lock_path.write_text(
        raw.replace(
            '{\n  "name": "@211-ai/world-siwe-verifier",',
            '{\n  "name": "@211-ai/world-siwe-verifier",\n'
            '  "name": "@211-ai/world-siwe-verifier",',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(SiweBootstrapError, match="duplicate JSON key"):
        verify_world_siwe_offline_bootstrap(copied_root)

    shutil.copy2(ROOT / LOCK, lock_path)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"]["node_modules/viem"]["integrity"] = (
        "sha512-" + base64.b64encode(bytes(64)).decode("ascii")
    )
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SiweBootstrapError, match="real 512-bit digest"):
        verify_world_siwe_offline_bootstrap(copied_root)


def test_unreachable_package_and_engine_drift_fail_before_proposal_digest(
    tmp_path: Path,
) -> None:
    copied_root = _packet_copy(tmp_path)
    lock_path = copied_root / LOCK
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"]["node_modules/unreachable"] = {
        "version": "1.0.0",
        "resolved": "https://registry.npmjs.org/unreachable/-/unreachable-1.0.0.tgz",
        "integrity": "sha512-" + base64.b64encode(hashlib.sha512(b"unreachable").digest()).decode(),
        "license": "MIT",
        "engines": {"node": "*"},
        "x-world-aid-engine-source": "registry-not-declared",
    }
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SiweBootstrapError, match="unreachable"):
        verify_world_siwe_offline_bootstrap(copied_root)

    shutil.copy2(ROOT / LOCK, lock_path)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    del lock["packages"]["node_modules/viem"]["engines"]
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SiweBootstrapError, match="engines"):
        verify_world_siwe_offline_bootstrap(copied_root)

    shutil.copy2(ROOT / LOCK, lock_path)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"]["node_modules/viem"]["version"] = "2.45.3-beta.1"
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SiweBootstrapError, match="version is not exact"):
        verify_world_siwe_offline_bootstrap(copied_root)

    shutil.copy2(ROOT / LOCK, lock_path)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"]["node_modules/viem"]["resolved"] = (
        "https://registry.npmjs.org/react/-/react-2.45.3.tgz"
    )
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(SiweBootstrapError, match="exact official-registry URL"):
        verify_world_siwe_offline_bootstrap(copied_root)


@pytest.mark.parametrize(
    ("peer_name", "constraint"),
    [
        ("react", "^17 || ^18 || ^19 || NOT-A-RANGE"),
        ("wagmi", "* || NOT-A-RANGE"),
    ],
)
def test_every_semver_alternative_is_validated_even_after_a_match(
    tmp_path: Path,
    peer_name: str,
    constraint: str,
) -> None:
    copied_root = _packet_copy(tmp_path)
    lock_path = copied_root / LOCK
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"]["node_modules/@worldcoin/minikit-js"]["peerDependencies"][
        peer_name
    ] = constraint
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SiweBootstrapError, match="unsupported semver syntax"):
        verify_world_siwe_offline_bootstrap(copied_root)


def test_semver_components_with_leading_zeroes_fail_closed(tmp_path: Path) -> None:
    copied_root = _packet_copy(tmp_path)
    lock_path = copied_root / LOCK
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"]["node_modules/@worldcoin/minikit-js"]["peerDependencies"]["wagmi"] = (
        "* || 01.2.3"
    )
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SiweBootstrapError, match="leading-zero semver"):
        verify_world_siwe_offline_bootstrap(copied_root)


def test_tarball_approval_hash_and_sri_share_one_nofollow_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tarball = tmp_path / "package.tgz"
    payload = b"one reviewed tarball snapshot"
    tarball.write_bytes(payload)
    real_open = os.open
    opens: list[Path] = []

    def tracked_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        opens.append(Path(path))  # type: ignore[arg-type]
        assert flags & getattr(os, "O_NOFOLLOW", 0)
        return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", tracked_open)
    sha256, sri = _tarball_snapshot_digests(tarball, "synthetic tarball")
    assert opens == [tarball]
    assert sha256 == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert sri == "sha512-" + base64.b64encode(hashlib.sha512(payload).digest()).decode()

    link = tmp_path / "package-link.tgz"
    link.symlink_to(tarball)
    with pytest.raises(SiweBootstrapError, match="cannot hash"):
        _tarball_snapshot_digests(link, "symlink tarball")


def test_gate_loader_executes_captured_pinned_bytes_not_later_path_contents(
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / GATE_VERIFIER
    gate_path.parent.mkdir(parents=True)
    captured = b"""\
class ApprovalVerificationError(ValueError):
    pass
SELECTION = "selection"
def verify_approval(**kwargs):
    return {"verified_approval_sha256": "captured"}
"""
    gate_path.write_bytes(captured)
    digest = "sha256:" + hashlib.sha256(captured).hexdigest()
    gate_path.write_text("raise RuntimeError('replacement executed')\n", encoding="utf-8")

    _, selection, verifier = _load_pinned_gate_verifier(gate_path, captured, digest)
    assert selection == "selection"
    assert verifier()["verified_approval_sha256"] == "captured"


def test_fake_signed_boolean_cannot_replace_canonical_gate_verification(
    tmp_path: Path,
) -> None:
    copied_root = _packet_copy(tmp_path)
    approval_path = copied_root / CANONICAL_APPROVAL
    approval_path.parent.mkdir(parents=True)
    approval_path.write_text('{"signed":true}\n', encoding="utf-8")
    allowed_signers = tmp_path / "operator.allowed_signers"
    allowed_signers.write_text("synthetic invalid trust file\n", encoding="utf-8")
    gate_digest = _sha256(copied_root / GATE_VERIFIER)
    with pytest.raises(SiweBootstrapError, match="canonical Gate 0B verification rejected"):
        verify_world_siwe_offline_bootstrap(
            copied_root,
            approval=CANONICAL_APPROVAL,
            allowed_signers=allowed_signers.resolve(),
            gate_verifier_sha256=gate_digest,
            require_approval=True,
        )
    assert 'record.get("signed")' not in SCRIPT.read_text(encoding="utf-8")
    assert 'record["signed"]' not in SCRIPT.read_text(encoding="utf-8")


def test_approved_path_requires_an_external_gate_verifier_digest(
    tmp_path: Path,
) -> None:
    copied_root = _packet_copy(tmp_path)
    approval_path = copied_root / CANONICAL_APPROVAL
    approval_path.parent.mkdir(parents=True)
    approval_path.write_text("{}\n", encoding="utf-8")
    allowed_signers = tmp_path / "operator.allowed_signers"
    allowed_signers.write_text("synthetic invalid trust file\n", encoding="utf-8")

    with pytest.raises(SiweBootstrapError, match="gate-verifier-sha256 trust anchor"):
        verify_world_siwe_offline_bootstrap(
            copied_root,
            approval=CANONICAL_APPROVAL,
            allowed_signers=allowed_signers.resolve(),
            require_approval=True,
        )
    with pytest.raises(SiweBootstrapError, match="external trust anchor"):
        verify_world_siwe_offline_bootstrap(
            copied_root,
            approval=CANONICAL_APPROVAL,
            allowed_signers=allowed_signers.resolve(),
            gate_verifier_sha256="sha256:" + "0" * 64,
            require_approval=True,
        )


def test_approved_cross_binding_rechecks_the_canonical_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied_root = _packet_copy(tmp_path)
    approval_path = copied_root / CANONICAL_APPROVAL
    approval_path.parent.mkdir(parents=True)
    approval_path.write_text("{}\n", encoding="utf-8")
    allowed_signers = tmp_path / "operator.allowed_signers"
    allowed_signers.write_text("synthetic trust snapshot\n", encoding="utf-8")
    captured = approval_path.read_bytes()
    captured_digest = "sha256:" + hashlib.sha256(captured).hexdigest()

    def fake_gate_loader(*_args: object, **_kwargs: object):
        def fake_verify(**_verify_kwargs: object) -> dict[str, str]:
            return {"verified_approval_sha256": captured_digest}

        return ValueError, "selection", fake_verify

    def mutate_during_cross_bind(*_args: object, **_kwargs: object) -> None:
        approval_path.write_text('{"replacement":true}\n', encoding="utf-8")

    monkeypatch.setattr(siwe_bootstrap, "_load_pinned_gate_verifier", fake_gate_loader)
    monkeypatch.setattr(siwe_bootstrap, "_cross_bind_approved_selection", mutate_during_cross_bind)

    with pytest.raises(SiweBootstrapError, match="changed before verification completed"):
        verify_world_siwe_offline_bootstrap(
            copied_root,
            approval=CANONICAL_APPROVAL,
            allowed_signers=allowed_signers.resolve(),
            gate_verifier_sha256="sha256:" + "0" * 64,
            require_approval=True,
        )


def test_final_artifact_checks_precede_the_final_approval_reread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied_root = _packet_copy(tmp_path)
    approval_path = copied_root / CANONICAL_APPROVAL
    approval_path.parent.mkdir(parents=True)
    approval_path.write_text("{}\n", encoding="utf-8")
    allowed_signers = tmp_path / "operator.allowed_signers"
    allowed_signers.write_text("synthetic trust snapshot\n", encoding="utf-8")
    captured_digest = "sha256:" + hashlib.sha256(approval_path.read_bytes()).hexdigest()
    gate_completed = False
    mutated = False
    original_digest = siwe_bootstrap._digest

    def fake_gate_loader(*_args: object, **_kwargs: object):
        def fake_verify(**_verify_kwargs: object) -> dict[str, str]:
            nonlocal gate_completed
            gate_completed = True
            return {"verified_approval_sha256": captured_digest}

        return ValueError, "selection", fake_verify

    def mutate_during_final_digest(path: Path) -> str:
        nonlocal mutated
        if gate_completed and not mutated and path == copied_root / MANIFEST:
            mutated = True
            approval_path.write_text('{"replacement":true}\n', encoding="utf-8")
        return original_digest(path)

    monkeypatch.setattr(siwe_bootstrap, "_load_pinned_gate_verifier", fake_gate_loader)
    monkeypatch.setattr(siwe_bootstrap, "_cross_bind_approved_selection", lambda *_args: None)
    monkeypatch.setattr(siwe_bootstrap, "_digest", mutate_during_final_digest)

    with pytest.raises(SiweBootstrapError, match="changed before verification completed"):
        verify_world_siwe_offline_bootstrap(
            copied_root,
            approval=CANONICAL_APPROVAL,
            allowed_signers=allowed_signers.resolve(),
            gate_verifier_sha256="sha256:" + "0" * 64,
            require_approval=True,
        )
    assert mutated is True


def test_verifier_ast_has_no_install_network_or_process_primitive() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    forbidden_modules = {"subprocess", "socket", "urllib", "requests", "http", "npm", "node"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert not imported & forbidden_modules
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {
        "run",
        "Popen",
        "system",
        "urlopen",
        "connect",
        "write_text",
        "write_bytes",
        "mkdir",
        "unlink",
    }
    assert "verify_approval(" in SCRIPT.read_text(encoding="utf-8")
    assert "from scripts.verify_world_aid_gate_0b import" not in SCRIPT.read_text(encoding="utf-8")


def test_adapter_requires_exact_policy_and_injected_client_without_transport() -> None:
    source = (ROOT / ADAPTER).read_text(encoding="utf-8")
    assert 'from "@worldcoin/minikit-js/siwe"' in source
    assert 'exactKeys(runtime, ["client", "now"], "SIWE runtime")' in source
    for term in (
        "expiration_time",
        "issued_at",
        "maxAgeSeconds",
        "not_before",
        "policy.version must be exactly 1",
        "runtime.now",
        "client.chain.id !== chainId",
        'typeof client.readContract !== "function"',
        "expirationMilliseconds - issuedMilliseconds",
    ):
        assert term in source
    for forbidden in ("createPublicClient", "http(", "fetch(", "process.env", "https://"):
        assert forbidden not in source


def test_runtime_contract_verifies_gate_before_any_process_and_is_collectible() -> None:
    source = (ROOT / RUNTIME_TEST).read_text(encoding="utf-8")
    fence_offset = source.index("    if TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED is not True:")
    execution_flag_offset = source.index('    if os.environ.get("WORLD_AID_G038_REAL_EXECUTION")')
    gate_offset = source.index("verification = verify_world_siwe_offline_bootstrap(")
    subprocess_import_offset = source.index("    import subprocess")
    first_process_offset = source.index("subprocess.run(")
    assert fence_offset < execution_flag_offset < gate_offset < subprocess_import_offset < first_process_offset
    assert "TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED = False" in source
    assert "operator-controlled Gate-first supervisor launcher" in source
    assert '"ci",' in source
    assert '"--offline",' in source
    assert '"--ignore-scripts",' in source
    assert "EOA" in source
    assert "EIP-1271" in source
    assert "WORLD_AID_G038_REAL_EXECUTION" in source
    assert "runtime_toolchain" in source
    assert "WORLD_AID_G038_SANDBOX_PARENT" in source
    assert "world-human-aid-siwe-bootstrap-verification-receipt/v2" in source
    assert '"attempt_count": None' in source
    for forbidden in (
        "WORLD_AID_G038_NETWORK_DENIED",
        "WORLD_AID_G038_NODE",
        "WORLD_AID_G038_NPM",
        "WORLD_AID_G038_ISOLATED_ROOT",
        "shutil.rmtree(isolated_root)",
    ):
        assert forbidden not in source


def test_cli_requires_explicit_offline_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(subprocess, "run", _forbidden)
    assert main([]) == 2
    assert "--offline is required" in capsys.readouterr().err


def test_g038_cannot_rewrite_the_selection_bound_siwe_packet() -> None:
    assert {
        ADAPTER.as_posix(),
        MANIFEST.as_posix(),
        LOCK.as_posix(),
        PROPOSAL.as_posix(),
        STATIC_TEST.as_posix(),
        RUNTIME_TEST.as_posix(),
        GATE_VERIFIER.as_posix(),
        "scripts/verify_world_siwe_offline_bootstrap.py",
    } <= PROTECTED_WRITABLE_PATHS


def test_heap_records_truthful_controlled_generation_and_static_boundary() -> None:
    heap = HEAP.read_text(encoding="utf-8")
    section = heap[heap.index("## WORLDCOIN-G037") : heap.index("## WORLDCOIN-G038")]
    for term in (
        "NOT APPROVED",
        "human Gate 0B",
        "official registry metadata",
        "isolated ephemeral cache",
        "no package execution",
        "static validation",
        "no npm",
        "canonical",
    ):
        assert term.lower() in section.lower()
