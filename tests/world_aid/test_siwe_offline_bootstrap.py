"""G038 future hermetic SIWE runtime contract.

G037 only collects this test. Real execution remains deliberately fenced until
an operator-controlled Gate-first supervisor launcher authenticates this
entrypoint and the SIWE verifier before any repository Python runs. Human Gate
0B approval and staged inputs remain necessary, but are not by themselves a
trusted execution boundary.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from scripts.verify_world_siwe_offline_bootstrap import (
    ADAPTER,
    CANONICAL_APPROVAL,
    EXPECTED_CACHE_PATH,
    EXPECTED_TOOLCHAIN,
    LOCK,
    MANIFEST,
    ROOT,
    _load_json_bytes,
    verify_world_siwe_offline_bootstrap,
)

RECEIPT = ROOT / "data/worldcoin_human_aid/bootstrap/world-siwe-offline-smoke.fixture.json"
MAX_BOUND_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 100_000
MAX_CACHE_ENTRIES = 100_000
MAX_CACHE_BYTES = 2 * 1024 * 1024 * 1024
TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED = False

NODE_SMOKE = r"""
import { hashMessage } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { verifyWorldSiwe } from "./index.mjs";

const privateKey =
  "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const account = privateKeyToAccount(privateKey);
const domain = "synthetic.invalid";
const uri = "https://synthetic.invalid/world-aid";
const chainId = 480;
const nonce = "G038NONCE123";
const statement = "Synthetic offline World Aid SIWE smoke";
const requestId = "g038-synthetic-request";
const nowMilliseconds = Date.now();
const now = new Date(nowMilliseconds).toISOString();
const issuedAt = new Date(nowMilliseconds - 2000).toISOString();
const notBefore = new Date(nowMilliseconds - 1000).toISOString();
const expirationTime = new Date(nowMilliseconds + 298000).toISOString();

const messageFor = (address) =>
  `${domain} wants you to sign in with your Ethereum account:\n` +
  `${address}\n\n${statement}\n\nURI: ${uri}\nVersion: 1\n` +
  `Chain ID: ${chainId}\nNonce: ${nonce}\nIssued At: ${issuedAt}\n` +
  `Expiration Time: ${expirationTime}\nNot Before: ${notBefore}\n` +
  `Request ID: ${requestId}\n`;
const policy = {
  chainId,
  domain,
  expirationTime,
  issuedAt,
  maxAgeSeconds: 300,
  nonce,
  notBefore,
  requestId,
  statement,
  uri,
  version: "1",
};

const contractAddress = "0x0000000000000000000000000000000000001271";
const contractMessage = messageFor(contractAddress);
let contractReads = 0;
const injectedClient = {
  chain: { id: chainId },
  readContract: async ({ address, abi, functionName, args }) => {
    if (
      address.toLowerCase() !== contractAddress.toLowerCase() ||
      functionName !== "isValidSignature" ||
      !Array.isArray(abi) ||
      !abi.some((item) => item?.name === "isValidSignature") ||
      !Array.isArray(args) ||
      args.length !== 2 ||
      args[0] !== hashMessage(contractMessage) ||
      args[1] !== "0x00"
    ) {
      throw new Error("unexpected EIP-1271 readContract request");
    }
    contractReads += 1;
    return "0x1626ba7e";
  },
};

const eoaMessage = messageFor(account.address);
const eoaSignature = await account.signMessage({ message: eoaMessage });
const eoa = await verifyWorldSiwe(
  { address: account.address, message: eoaMessage, signature: eoaSignature },
  policy,
  { client: injectedClient, now },
);
if (eoa.isValid !== true || contractReads !== 0) {
  throw new Error("EOA verification did not stay on the local recovery path");
}

const eip1271 = await verifyWorldSiwe(
  { address: contractAddress, message: contractMessage, signature: "0x00" },
  policy,
  { client: injectedClient, now },
);
if (eip1271.isValid !== true || contractReads !== 1) {
  throw new Error("EIP-1271 verification did not use exactly the injected client");
}
console.log(JSON.stringify({ eoa: eoa.isValid, eip1271: eip1271.isValid, contractReads }));
"""


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(f"{name} is required before any G038 package action")
    return value


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _normalized_relative(value: Any, context: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        pytest.fail(f"{context} must be a non-empty normalized POSIX path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or pure.as_posix() != value or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        pytest.fail(f"{context} must be a normalized relative POSIX path")
    return value


def _bound_repo_bytes(
    artifact: dict[str, Any],
    context: str,
    *,
    maximum: int = MAX_BOUND_ARTIFACT_BYTES,
) -> bytes:
    if set(artifact) != {"path", "sha256"}:
        pytest.fail(f"{context} is not an exact signed artifact")
    relative = _normalized_relative(artifact["path"], f"{context}.path")
    path = ROOT.joinpath(*PurePosixPath(relative).parts)
    current = ROOT
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            pytest.fail(f"{context} traverses a symlink")
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            pytest.fail(f"{context} must be a bounded regular file")
        chunks: list[bytes] = []
        remaining = maximum
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining == 0 and os.read(descriptor, 1):
            pytest.fail(f"{context} exceeds its size limit")
        after = os.fstat(descriptor)
    except OSError as exc:
        pytest.fail(f"{context} cannot be read safely: {exc}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    snapshot = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    if snapshot != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        pytest.fail(f"{context} changed while being read")
    raw = b"".join(chunks)
    if _sha256(raw) != artifact["sha256"]:
        pytest.fail(f"{context} digest differs from the signed selection")
    return raw


def _tree_digest(root: Path, *, require_read_only: bool) -> str:
    def file_digest(path: Path) -> bytes:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                pytest.fail(f"cache entry is not a regular file: {path}")
            observed = hashlib.sha256()
            while chunk := os.read(descriptor, 1024 * 1024):
                observed.update(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            pytest.fail(f"cache entry changed while being hashed: {path}")
        return observed.digest()

    digest = hashlib.sha256()
    entries = (root, *sorted(root.rglob("*")))
    if len(entries) > MAX_CACHE_ENTRIES:
        pytest.fail("cache tree exceeds the entry limit")
    total_bytes = 0
    for path in entries:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            pytest.fail(f"cache tree contains a symlink: {path}")
        if not (stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode)):
            pytest.fail(f"cache tree contains an unsupported entry: {path}")
        if require_read_only and metadata.st_mode & (
            stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        ):
            pytest.fail(f"approved cache entry is mode-writable: {path}")
        relative = b"." if path == root else path.relative_to(root).as_posix().encode()
        digest.update(b"D" if stat.S_ISDIR(metadata.st_mode) else b"F")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        if stat.S_ISREG(metadata.st_mode):
            total_bytes += metadata.st_size
            if total_bytes > MAX_CACHE_BYTES:
                pytest.fail("cache tree exceeds the byte limit")
            digest.update(file_digest(path))
    return "sha256:" + digest.hexdigest()


def _security_snapshot(approval: dict[str, Any]) -> dict[str, Any]:
    security = approval["security_evidence"]
    canary_artifact = security["network_deny_canary"]
    policy_artifact = security["egress_policy"]
    canary_raw = _bound_repo_bytes(canary_artifact, "signed network deny canary")
    policy_raw = _bound_repo_bytes(policy_artifact, "signed egress policy")
    canary = _load_json_bytes(canary_raw, "signed network deny canary")
    policy = _load_json_bytes(policy_raw, "signed egress policy")

    if (
        policy.get("external_enforcement") is not True
        or policy.get("default_deny") is not True
        or policy.get("registry_access") is not False
        or policy.get("allowed_destinations") != []
    ):
        pytest.fail("signed egress policy is not an externally enforced default deny")
    boundary = canary["boundary"]
    expected_namespace = boundary["network_namespace"]["identity"]
    observed_namespace = os.readlink("/proc/self/ns/net")
    if observed_namespace != expected_namespace:
        pytest.fail("current process is outside the signed reviewed network namespace")
    expected_profile = boundary["apparmor"]["profile"]
    observed_profile = Path("/proc/self/attr/current").read_text(encoding="utf-8").strip()
    if observed_profile != f"{expected_profile} (enforce)":
        pytest.fail("current process is outside the signed enforcing AppArmor profile")
    interfaces = sorted(path.name for path in Path("/sys/class/net").iterdir())
    if interfaces != ["lo"]:
        pytest.fail("current network namespace exposes a non-loopback interface")
    route_interfaces: list[str] = []
    route_lines = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()[1:]
    route_interfaces.extend(line.split()[0] for line in route_lines if line.split())
    ipv6_lines = Path("/proc/net/ipv6_route").read_text(encoding="utf-8").splitlines()
    route_interfaces.extend(line.split()[-1] for line in ipv6_lines if line.split())
    if any(interface != "lo" for interface in route_interfaces):
        pytest.fail("current network namespace exposes an external route")
    return {
        "namespace": observed_namespace,
        "apparmor_profile": observed_profile,
        "interfaces": interfaces,
        "no_external_route": True,
        "network_deny_canary_sha256": canary_artifact["sha256"],
        "egress_policy_sha256": policy_artifact["sha256"],
    }


def _safe_extract_toolchain(
    archive_raw: bytes,
    destination: Path,
    toolchain: dict[str, Any],
) -> tuple[Path, Path]:
    root_name = _normalized_relative(toolchain["root"], "runtime toolchain root")
    seen: set[str] = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive_raw), mode="r:xz") as archive:
        members = archive.getmembers()
        if not members or len(members) > MAX_ARCHIVE_MEMBERS:
            pytest.fail("runtime toolchain archive has an invalid member count")
        for member in members:
            name = member.name.rstrip("/") if member.isdir() else member.name
            normalized = _normalized_relative(name, "runtime toolchain archive member")
            member_path = PurePosixPath(normalized)
            if member_path != PurePosixPath(root_name) and PurePosixPath(root_name) not in member_path.parents:
                pytest.fail("runtime toolchain archive member escapes its signed root")
            if normalized in seen or not (member.isdir() or member.isfile()):
                pytest.fail("runtime toolchain archive has a duplicate or unsafe member")
            seen.add(normalized)
            target = destination.joinpath(*member_path.parts)
            try:
                target.relative_to(destination)
            except ValueError:
                pytest.fail("runtime toolchain archive member escapes the sandbox")
            if member.isdir():
                if target.exists():
                    if target.is_symlink() or not target.is_dir():
                        pytest.fail("runtime toolchain archive directory conflicts with a file")
                else:
                    target.mkdir(mode=0o700, parents=True)
                continue
            total += member.size
            if member.size < 0 or total > MAX_EXTRACTED_BYTES:
                pytest.fail("runtime toolchain archive exceeds the extraction limit")
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                pytest.fail("runtime toolchain regular member has no payload")
            with target.open("xb") as output:
                remaining = member.size
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        pytest.fail("runtime toolchain archive member is truncated")
                    output.write(chunk)
                    remaining -= len(chunk)
                if source.read(1):
                    pytest.fail("runtime toolchain archive member exceeds its declared size")
            target.chmod(0o400)

    def member_path(key: str) -> Path:
        member = toolchain[key]
        relative = _normalized_relative(member["path"], f"runtime toolchain {key}")
        path = destination.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_file():
            pytest.fail(f"runtime toolchain {key} member is absent or unsafe")
        if _sha256(path.read_bytes()) != member["sha256"]:
            pytest.fail(f"runtime toolchain {key} member digest drifted")
        return path

    node = member_path("node")
    npm_cli = member_path("npm_cli")
    node.chmod(0o500)
    return node, npm_cli


def _verify_open_descriptor(
    descriptor: int,
    expected_digest: str,
    context: str,
) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        pytest.fail(f"{context} is not a regular file")
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, 1024 * 1024):
        digest.update(chunk)
    after = os.fstat(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        pytest.fail(f"{context} changed while being hashed")
    if "sha256:" + digest.hexdigest() != expected_digest:
        pytest.fail(f"{context} digest differs from the signed selection")


def _open_pinned_member(
    path: Path,
    expected_digest: str,
    context: str,
    *,
    executable: bool,
) -> int:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or (
        executable and not metadata.st_mode & stat.S_IXUSR
    ):
        os.close(descriptor)
        pytest.fail(f"{context} does not have the required regular-file mode")
    try:
        _verify_open_descriptor(descriptor, expected_digest, context)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _validate_sandbox_parent(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute() or path.is_symlink():
        pytest.fail("WORLD_AID_G038_SANDBOX_PARENT must be an absolute non-symlink directory")
    path = path.resolve(strict=True)
    metadata = path.stat()
    if (
        not path.is_dir()
        or metadata.st_uid != os.geteuid()
        or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        pytest.fail("G038 sandbox parent must be owned by this user and not group/other writable")
    try:
        path.relative_to(ROOT)
    except ValueError:
        return path
    pytest.fail("G038 sandbox parent must be outside the repository")


def test_g038_approved_offline_siwe_runtime() -> None:
    """Install and exercise EOA/EIP-1271 only after exact human approval."""

    if TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED is not True:
        pytest.fail(
            "G038 remains blocked: an operator-controlled Gate-first supervisor "
            "launcher has not been implemented"
        )
    if os.environ.get("WORLD_AID_G038_REAL_EXECUTION") != "1":
        pytest.fail("WORLD_AID_G038_REAL_EXECUTION=1 is required; G037 may only collect this test")

    approval_path = ROOT / CANONICAL_APPROVAL
    verification = verify_world_siwe_offline_bootstrap(
        ROOT,
        approval=approval_path,
        allowed_signers=Path(_required_env("WORLD_AID_ALLOWED_SIGNERS")),
        gate_verifier_sha256=_required_env("WORLD_AID_GATE_VERIFIER_SHA256"),
        require_approval=True,
    )
    assert verification.status == "approved-selection-bound"
    approval_raw = approval_path.read_bytes()
    if _sha256(approval_raw) != verification.approval_sha256:
        pytest.fail("canonical approval changed after exact-byte verification")
    approval = _load_json_bytes(approval_raw, "verified canonical selection")

    # All imports and operations capable of extraction, copying, or launching
    # package tooling remain below exact Gate verification.
    import shutil
    import subprocess

    selection = approval["dependency_sets"]["siwe"]
    toolchain = selection["runtime_toolchain"]
    if {
        "platform": toolchain["platform"],
        "architecture": toolchain["architecture"],
        "archive_format": toolchain["archive_format"],
        "archive_path": toolchain["archive"]["path"],
        "root": toolchain["root"],
        "node_path": toolchain["node"]["path"],
        "node_version": toolchain["node"]["version"],
        "npm_cli_path": toolchain["npm_cli"]["path"],
        "npm_version": toolchain["npm_cli"]["version"],
    } != EXPECTED_TOOLCHAIN:
        pytest.fail("signed runtime toolchain differs from the G037 proposal")

    manifest_raw = _bound_repo_bytes(selection["manifest"], "signed SIWE manifest")
    lock_raw = _bound_repo_bytes(selection["lockfile"], "signed SIWE lock")
    adapter_raw = _bound_repo_bytes(approval["reviewed_state"]["siwe_adapter"], "signed SIWE adapter")
    if (
        _sha256(manifest_raw) != verification.manifest_sha256
        or _sha256(lock_raw) != verification.lock_sha256
        or _sha256(adapter_raw) != verification.adapter_sha256
    ):
        pytest.fail("verified SIWE input digests differ from the signed selection")
    archive_raw = _bound_repo_bytes(toolchain["archive"], "signed Node distribution")

    cache = selection["cache"]
    if (
        set(cache) != {"path", "read_only", "tree_sha256"}
        or cache["path"] != EXPECTED_CACHE_PATH
        or cache["read_only"] is not True
    ):
        pytest.fail("signed SIWE cache contract drifted")
    approved_cache = ROOT.joinpath(*PurePosixPath(cache["path"]).parts)
    if approved_cache.is_symlink() or not approved_cache.is_dir():
        pytest.fail("signed SIWE cache is absent or unsafe")
    cache_before = _tree_digest(approved_cache, require_read_only=True)
    if cache_before != cache["tree_sha256"]:
        pytest.fail("reviewed cache tree differs from the signed selection")
    boundary_before = _security_snapshot(approval)
    sandbox_parent = _validate_sandbox_parent(_required_env("WORLD_AID_G038_SANDBOX_PARENT"))

    sandbox = Path(tempfile.mkdtemp(prefix="world-aid-g038-", dir=sandbox_parent))
    node_descriptor = -1
    npm_cli_descriptor = -1
    boundary_after: dict[str, Any] | None = None
    cache_local_before_digest: str | None = None
    cache_local_after_digest: str | None = None
    smoke_result: dict[str, Any] | None = None
    try:
        if sandbox.parent != sandbox_parent or sandbox.is_symlink():
            pytest.fail("G038 did not create an owned child sandbox")
        toolchain_root = sandbox / "toolchain"
        toolchain_root.mkdir(mode=0o700)
        node, npm_cli = _safe_extract_toolchain(archive_raw, toolchain_root, toolchain)
        node_descriptor = _open_pinned_member(
            node,
            toolchain["node"]["sha256"],
            "signed Node member",
            executable=True,
        )
        npm_cli_descriptor = _open_pinned_member(
            npm_cli,
            toolchain["npm_cli"]["sha256"],
            "signed npm CLI member",
            executable=False,
        )
        node_fd_path = f"/proc/self/fd/{node_descriptor}"
        npm_cli_fd_path = f"/proc/self/fd/{npm_cli_descriptor}"

        service_root = sandbox / "service"
        service_root.mkdir(mode=0o700)
        service_inputs = {
            service_root / "package.json": manifest_raw,
            service_root / "package-lock.json": lock_raw,
            service_root / "index.mjs": adapter_raw,
        }
        for path, raw in service_inputs.items():
            path.write_bytes(raw)
            path.chmod(0o400)

        local_cache = sandbox / "npm-cache"
        shutil.copytree(approved_cache, local_cache, symlinks=False)
        if _tree_digest(approved_cache, require_read_only=True) != cache_before:
            pytest.fail("approved cache changed while being copied")
        cache_local_before_digest = _tree_digest(local_cache, require_read_only=True)
        if cache_local_before_digest != cache_before:
            pytest.fail("local cache copy differs from the reviewed cache")
        for path in (local_cache, *local_cache.rglob("*")):
            path.chmod(0o700 if path.is_dir() else 0o600)

        home = sandbox / "home"
        temporary = sandbox / "tmp"
        home.mkdir(mode=0o700)
        temporary.mkdir(mode=0o700)
        command_env = {
            "HOME": str(home),
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": str(node.parent),
            "TMPDIR": str(temporary),
            "TZ": "UTC",
            "npm_config_audit": "false",
            "npm_config_cache": str(local_cache),
            "npm_config_fund": "false",
            "npm_config_ignore_scripts": "true",
            "npm_config_offline": "true",
            "npm_config_update_notifier": "false",
        }

        def run_node(arguments: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [node_fd_path, *arguments],
                cwd=service_root,
                env=command_env,
                pass_fds=(node_descriptor, npm_cli_descriptor),
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            _verify_open_descriptor(
                node_descriptor,
                toolchain["node"]["sha256"],
                "signed Node member",
            )
            _verify_open_descriptor(
                npm_cli_descriptor,
                toolchain["npm_cli"]["sha256"],
                "signed npm CLI member",
            )
            for path, raw in service_inputs.items():
                if path.read_bytes() != raw:
                    pytest.fail(f"selection-bound input changed during execution: {path.name}")
            return result

        npm_version = run_node([npm_cli_fd_path, "--version"], timeout=15).stdout.strip()
        if npm_version != toolchain["npm_cli"]["version"]:
            pytest.fail(f"signed npm version differs from observed {npm_version!r}")
        node_version = run_node(["--version"], timeout=15).stdout.strip()
        if node_version != f"v{toolchain['node']['version']}":
            pytest.fail(f"signed Node version differs from observed {node_version!r}")

        run_node(
            [
                npm_cli_fd_path,
                "ci",
                "--offline",
                "--ignore-scripts",
                "--audit=false",
                "--fund=false",
                "--cache",
                str(local_cache),
            ],
            timeout=180,
        )
        smoke_path = service_root / "g038-smoke.mjs"
        smoke_path.write_text(NODE_SMOKE, encoding="utf-8")
        smoke = run_node([str(smoke_path)], timeout=30)
        smoke_result = json.loads(smoke.stdout)
        if smoke_result != {"eoa": True, "eip1271": True, "contractReads": 1}:
            pytest.fail("SIWE runtime smoke result drifted")

        if _tree_digest(approved_cache, require_read_only=True) != cache_before:
            pytest.fail("approved cache changed during G038")
        cache_local_after_digest = _tree_digest(local_cache, require_read_only=False)
        boundary_after = _security_snapshot(approval)
        if boundary_after != boundary_before:
            pytest.fail("signed egress boundary changed during G038")
    finally:
        if node_descriptor >= 0:
            os.close(node_descriptor)
        if npm_cli_descriptor >= 0:
            os.close(npm_cli_descriptor)
        if (
            sandbox.parent != sandbox_parent
            or not sandbox.name.startswith("world-aid-g038-")
            or sandbox.is_symlink()
        ):
            pytest.fail("refusing unsafe G038 sandbox cleanup target")
        shutil.rmtree(sandbox)

    if sandbox.exists():
        pytest.fail("owned G038 child sandbox was not removed")
    assert boundary_after is not None
    assert cache_local_before_digest is not None
    assert cache_local_after_digest is not None
    assert smoke_result is not None
    receipt = {
        "schema_version": "world-human-aid-siwe-bootstrap-verification-receipt/v2",
        "goal_id": "WORLDCOIN-G038",
        "status": "passed",
        "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valid_until": approval["expires_at"],
        "offline": True,
        "live_actions_authorized": False,
        "selection_record_id": approval["record_id"],
        "selection_approval_sha256": verification.approval_sha256,
        "real_execution": True,
        "cache_mutated": False,
        "toolchain": {
            "platform": toolchain["platform"],
            "architecture": toolchain["architecture"],
            "archive_sha256": toolchain["archive"]["sha256"],
            "node_sha256": toolchain["node"]["sha256"],
            "node_version": toolchain["node"]["version"],
            "npm_cli_sha256": toolchain["npm_cli"]["sha256"],
            "npm_version": toolchain["npm_cli"]["version"],
        },
        "inputs": {
            "manifest_sha256": verification.manifest_sha256,
            "lock_sha256": verification.lock_sha256,
            "adapter_sha256": verification.adapter_sha256,
        },
        "cache": {
            "reviewed_before_sha256": cache_before,
            "reviewed_after_sha256": cache_before,
            "local_before_sha256": cache_local_before_digest,
            "local_after_sha256": cache_local_after_digest,
        },
        "network": {
            "enforcement": "signed-namespace-plus-apparmor",
            "attempt_monitor": "not-configured",
            "attempt_count": None,
            "external_network_succeeded": False,
            "boundary_before": boundary_before,
            "boundary_after": boundary_after,
        },
        "smoke_result": smoke_result,
    }
    RECEIPT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
