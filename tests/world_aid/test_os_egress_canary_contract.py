from __future__ import annotations

import errno
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/run_world_aid_egress_canary.py"
HOST_NAMESPACE = "net:[4026532000]"


def _load_module():
    spec = importlib.util.spec_from_file_location("world_aid_egress_canary", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proc_fixture(
    tmp_path: Path,
    *,
    apparmor_label: str = "linux-sandbox (enforce)",
    namespace_identity: str = "net:[4026533000]",
    interfaces: tuple[str, ...] = ("lo",),
    ipv4_route_lines: tuple[str, ...] = (),
    ipv6_route_lines: tuple[str, ...] = (),
) -> Path:
    proc_root = tmp_path / "proc"
    (proc_root / "self/attr").mkdir(parents=True)
    (proc_root / "self/ns").mkdir(parents=True)
    (proc_root / "net").mkdir(parents=True)
    (proc_root / "self/attr/current").write_text(
        apparmor_label + "\n",
        encoding="utf-8",
    )
    (proc_root / "self/ns/net").symlink_to(namespace_identity)
    interface_rows = "\n".join(f"{name}: 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0" for name in interfaces)
    (proc_root / "net/dev").write_text(
        "Inter-| Receive | Transmit\n"
        " face |bytes packets errs drop fifo frame compressed multicast|"
        "bytes packets errs drop fifo colls carrier compressed\n"
        f"{interface_rows}\n",
        encoding="utf-8",
    )
    (proc_root / "net/route").write_text(
        "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"
        + "".join(f"{line}\n" for line in ipv4_route_lines),
        encoding="utf-8",
    )
    (proc_root / "net/ipv6_route").write_text(
        "".join(f"{line}\n" for line in ipv6_route_lines),
        encoding="utf-8",
    )
    return proc_root


def test_canary_requires_reviewed_boundary_and_uses_no_dns_result() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "198.51.100.1" in text
    assert "POLICY_ERRNOS" in text
    assert "getaddrinfo" not in text
    assert "RESERVED_INVALID_TLD" not in text
    assert "--inside-reviewed-deny-sandbox" in text
    assert "--offline" in text
    assert "--expected-apparmor-profile" in text
    assert "--expected-network-namespace" in text
    assert "--host-network-namespace" in text
    assert "/proc" in text
    assert "refusing to overwrite existing receipt" in text


def test_boundary_requires_enforcing_profile_exact_namespace_and_loopback_only(
    tmp_path: Path,
) -> None:
    module = _load_module()
    namespace_identity = "net:[4026533000]"
    proc_root = _proc_fixture(
        tmp_path,
        ipv4_route_lines=("lo 0000007F 00000000 0001 0 0 0 000000FF 0 0 0",),
        ipv6_route_lines=(
            "00000000000000000000000000000001 80 "
            "00000000000000000000000000000000 00 "
            "00000000000000000000000000000000 "
            "00000000 00000000 00000000 00000001 lo",
        ),
    )

    evidence = module.collect_boundary_evidence(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace=namespace_identity,
        host_network_namespace=HOST_NAMESPACE,
        proc_root=proc_root,
    )

    assert evidence["passed"] is True
    assert evidence["apparmor"]["mode"] == "enforce"
    assert evidence["network_namespace"]["identity"] == namespace_identity
    assert evidence["network_namespace"]["host_identity"] == HOST_NAMESPACE
    assert evidence["network_namespace"]["host_identity_valid"] is True
    assert evidence["network_namespace"]["separated_from_host"] is True
    assert evidence["interfaces"] == ["lo"]
    assert evidence["loopback_only"] is True
    assert evidence["no_external_route"] is True
    assert evidence["errors"] == []
    assert evidence["ipv4_routes"][0]["destination"] == "127.0.0.0/8"
    assert evidence["ipv6_routes"][0]["destination"] == "::1/128"


@pytest.mark.parametrize(
    ("fixture_kwargs", "expected_failed_check"),
    [
        ({"interfaces": ("lo", "eth0")}, "loopback_only"),
        (
            {"ipv4_route_lines": ("lo 00000000 00000000 0001 0 0 0 00000000 0 0 0",)},
            "no_external_route",
        ),
        ({"apparmor_label": "unconfined"}, "apparmor"),
        ({"namespace_identity": "net:[4026533001]"}, "network_namespace"),
    ],
)
def test_boundary_rejects_unreviewed_or_externally_routable_state(
    tmp_path: Path,
    fixture_kwargs: dict[str, object],
    expected_failed_check: str,
) -> None:
    module = _load_module()
    proc_root = _proc_fixture(tmp_path, **fixture_kwargs)

    evidence = module.collect_boundary_evidence(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace="net:[4026533000]",
        host_network_namespace=HOST_NAMESPACE,
        proc_root=proc_root,
    )

    assert evidence["passed"] is False
    if expected_failed_check == "loopback_only":
        assert evidence["loopback_only"] is False
    elif expected_failed_check == "no_external_route":
        assert evidence["no_external_route"] is False
    elif expected_failed_check == "apparmor":
        assert evidence["apparmor"]["matches_reviewed_profile"] is False
    else:
        assert evidence["network_namespace"]["matches_reviewed_namespace"] is False


@pytest.mark.parametrize(
    ("host_namespace", "host_identity_valid"),
    [
        ("net:[4026533000]", True),
        ("not-a-network-namespace", False),
        ("net:[0]", False),
    ],
)
def test_boundary_rejects_same_or_malformed_host_namespace(
    tmp_path: Path,
    host_namespace: str,
    host_identity_valid: bool,
) -> None:
    module = _load_module()
    proc_root = _proc_fixture(tmp_path)

    evidence = module.collect_boundary_evidence(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace="net:[4026533000]",
        host_network_namespace=host_namespace,
        proc_root=proc_root,
    )

    assert evidence["passed"] is False
    assert evidence["network_namespace"]["host_identity"] == host_namespace
    assert evidence["network_namespace"]["host_identity_valid"] is host_identity_valid
    assert evidence["network_namespace"]["separated_from_host"] is False


def test_cli_requires_host_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    base_arguments = [
        str(SCRIPT_PATH),
        "--receipt",
        "receipt.json",
        "--inside-reviewed-deny-sandbox",
        "--offline",
        "--expected-apparmor-profile",
        "linux-sandbox",
        "--expected-network-namespace",
        "net:[4026533000]",
    ]
    monkeypatch.setattr(sys, "argv", base_arguments)
    with pytest.raises(SystemExit):
        module._parse_args()

    monkeypatch.setattr(
        sys,
        "argv",
        [*base_arguments, "--host-network-namespace", HOST_NAMESPACE],
    )
    parsed = module._parse_args()
    assert parsed.host_network_namespace == HOST_NAMESPACE


def test_receipt_passes_only_for_exact_boundary_and_policy_consistent_errno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    boundary = {
        "passed": True,
        "apparmor": {"profile": "linux-sandbox", "mode": "enforce"},
        "network_namespace": {"identity": "net:[4026533000]"},
        "interfaces": ["lo"],
        "ipv4_routes": [],
        "ipv6_routes": [],
    }
    monkeypatch.setattr(
        module,
        "collect_boundary_evidence",
        lambda **_kwargs: boundary,
    )
    monkeypatch.setattr(
        module,
        "_attempt_ipv4",
        lambda: {
            "outcome": "policy_denied",
            "errno": errno.ENETUNREACH,
            "errno_name": "ENETUNREACH",
        },
    )

    receipt = module.build_receipt(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace="net:[4026533000]",
        host_network_namespace=HOST_NAMESPACE,
    )

    assert receipt["passed"] is True
    assert receipt["human_approval"] is False
    assert receipt["synthetic_fixture"] is True
    assert receipt["contains_secrets"] is False
    assert receipt["offline"] is True
    assert receipt["schema"] == "world-human-aid-egress-canary/v2"
    assert receipt["results"][1]["attempted"] is False
    assert receipt["results"][1]["accepted_as_policy_evidence"] is False
    assert "NXDOMAIN" in receipt["results"][1]["reason"]


@pytest.mark.parametrize(
    ("outcome", "error_number"),
    [
        ("ambiguous_or_not_policy_denied", errno.ECONNREFUSED),
        ("ambiguous_or_not_policy_denied", errno.ETIMEDOUT),
        ("connection_succeeded", None),
        ("policy_denied", errno.ECONNREFUSED),
    ],
)
def test_receipt_rejects_refused_timeout_success_and_inconsistent_errno(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    error_number: int | None,
) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "collect_boundary_evidence",
        lambda **_kwargs: {"passed": True},
    )
    monkeypatch.setattr(
        module,
        "_attempt_ipv4",
        lambda: {"outcome": outcome, "errno": error_number},
    )

    receipt = module.build_receipt(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace="net:[4026533000]",
        host_network_namespace=HOST_NAMESPACE,
    )

    assert receipt["passed"] is False


def test_receipt_rejects_policy_errno_when_boundary_does_not_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "collect_boundary_evidence",
        lambda **_kwargs: {"passed": False},
    )
    monkeypatch.setattr(
        module,
        "_attempt_ipv4",
        lambda: pytest.fail("an invalid boundary must prevent the socket attempt"),
    )

    receipt = module.build_receipt(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace="net:[4026533000]",
        host_network_namespace=HOST_NAMESPACE,
    )

    assert receipt["passed"] is False
    assert receipt["results"][0]["outcome"] == "not_attempted_boundary_invalid"


def test_boundary_rejects_missing_ipv4_route_inventory_header(tmp_path: Path) -> None:
    module = _load_module()
    proc_root = _proc_fixture(tmp_path)
    (proc_root / "net/route").write_text("", encoding="utf-8")

    evidence = module.collect_boundary_evidence(
        expected_apparmor_profile="linux-sandbox",
        expected_network_namespace="net:[4026533000]",
        host_network_namespace=HOST_NAMESPACE,
        proc_root=proc_root,
    )

    assert evidence["passed"] is False
    assert any(error.startswith("ipv4-routes-unavailable-or-invalid") for error in evidence["errors"])


@pytest.mark.parametrize(
    ("raised", "expected_outcome"),
    [
        (OSError(errno.EPERM, os.strerror(errno.EPERM)), "policy_denied"),
        (
            OSError(errno.ENETUNREACH, os.strerror(errno.ENETUNREACH)),
            "policy_denied",
        ),
        (
            ConnectionRefusedError(
                errno.ECONNREFUSED,
                os.strerror(errno.ECONNREFUSED),
            ),
            "ambiguous_or_not_policy_denied",
        ),
        (TimeoutError("timed out"), "ambiguous_or_not_policy_denied"),
    ],
)
def test_ipv4_canary_classifies_only_policy_consistent_errno_as_denial(
    monkeypatch: pytest.MonkeyPatch,
    raised: OSError,
    expected_outcome: str,
) -> None:
    module = _load_module()

    class FakeSocket:
        def settimeout(self, _seconds: float) -> None:
            return None

        def connect(self, _target: tuple[str, int]) -> None:
            raise raised

        def close(self) -> None:
            return None

    monkeypatch.setattr(module.socket, "socket", lambda *_args: FakeSocket())

    result = module._attempt_ipv4()

    assert result["outcome"] == expected_outcome
