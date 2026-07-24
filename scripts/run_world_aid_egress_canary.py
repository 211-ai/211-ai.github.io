#!/usr/bin/env python3
"""Produce a redacted receipt for the reviewed Gate 0B egress boundary.

The canary is useful only when the current process is demonstrably confined by
the expected enforcing AppArmor profile and reviewed network namespace.  That
namespace must expose only loopback and no route outside loopback.  DNS failure,
NXDOMAIN, timeout, connection refusal, and successful connection are never
accepted as policy evidence.
"""

from __future__ import annotations

import argparse
import errno
import ipaddress
import json
import os
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

POLICY_ERRNOS = {
    errno.EACCES,
    errno.EPERM,
    errno.ENETUNREACH,
}
NETWORK_NAMESPACE_RE = re.compile(r"^net:\[[1-9][0-9]*\]$")

_PROC_ROOT = Path("/proc")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _parse_apparmor_label(label: str) -> tuple[str, str]:
    match = re.fullmatch(r"(.+) \(([^()]+)\)", label)
    if match is None:
        return label, "unknown"
    return match.group(1), match.group(2).lower()


def _parse_interfaces(text: str) -> list[str]:
    interfaces: list[str] = []
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, _ = line.split(":", 1)
        normalized = name.strip()
        if normalized:
            interfaces.append(normalized)
    return sorted(set(interfaces))


def _decode_ipv4_proc_hex(value: str) -> ipaddress.IPv4Address:
    raw = bytes.fromhex(value)
    if len(raw) != 4:
        raise ValueError("IPv4 route value must contain four bytes")
    return ipaddress.IPv4Address(int.from_bytes(raw, byteorder="little"))


def _parse_ipv4_routes(text: str) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0] or lines[0][0] != "Iface":
        raise ValueError("missing /proc/net/route header")
    for fields in lines[1:]:
        if len(fields) < 8:
            raise ValueError("malformed /proc/net/route entry")
        destination = _decode_ipv4_proc_hex(fields[1])
        gateway = _decode_ipv4_proc_hex(fields[2])
        mask = _decode_ipv4_proc_hex(fields[7])
        network = ipaddress.IPv4Network((destination, str(mask)), strict=False)
        is_loopback = (
            fields[0] == "lo"
            and network.subnet_of(ipaddress.IPv4Network("127.0.0.0/8"))
            and (gateway.is_unspecified or gateway.is_loopback)
        )
        routes.append(
            {
                "interface": fields[0],
                "destination": str(network),
                "gateway": str(gateway),
                "loopback_only": is_loopback,
            }
        )
    return routes


def _parse_ipv6_routes(text: str) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 10:
            raise ValueError("malformed /proc/net/ipv6_route entry")
        destination = ipaddress.IPv6Address(int(fields[0], 16))
        prefix_length = int(fields[1], 16)
        network = ipaddress.IPv6Network((destination, prefix_length), strict=False)
        next_hop = ipaddress.IPv6Address(int(fields[4], 16))
        is_loopback = (
            fields[-1] == "lo"
            and network == ipaddress.IPv6Network("::1/128")
            and (next_hop.is_unspecified or next_hop.is_loopback)
        )
        routes.append(
            {
                "interface": fields[-1],
                "destination": str(network),
                "next_hop": str(next_hop),
                "loopback_only": is_loopback,
            }
        )
    return routes


def collect_boundary_evidence(
    *,
    expected_apparmor_profile: str,
    expected_network_namespace: str,
    host_network_namespace: str,
    proc_root: Path = _PROC_ROOT,
) -> dict[str, Any]:
    """Read the current Linux confinement state without invoking a subprocess."""

    errors: list[str] = []
    apparmor_label = ""
    apparmor_profile = ""
    apparmor_mode = "unknown"
    namespace_identity = ""
    interfaces: list[str] = []
    ipv4_routes: list[dict[str, Any]] = []
    ipv6_routes: list[dict[str, Any]] = []

    try:
        apparmor_label = _read_text(proc_root / "self/attr/current")
        apparmor_profile, apparmor_mode = _parse_apparmor_label(apparmor_label)
    except (OSError, UnicodeError) as exc:
        errors.append(f"apparmor-label-unavailable:{type(exc).__name__}")

    try:
        namespace_identity = os.readlink(proc_root / "self/ns/net")
    except OSError as exc:
        errors.append(f"network-namespace-unavailable:{type(exc).__name__}")

    try:
        interfaces = _parse_interfaces(_read_text(proc_root / "net/dev"))
        if not interfaces:
            errors.append("interface-inventory-empty")
    except (OSError, UnicodeError) as exc:
        errors.append(f"interface-inventory-unavailable:{type(exc).__name__}")

    try:
        ipv4_routes = _parse_ipv4_routes(_read_text(proc_root / "net/route"))
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"ipv4-routes-unavailable-or-invalid:{type(exc).__name__}")

    try:
        ipv6_routes = _parse_ipv6_routes(_read_text(proc_root / "net/ipv6_route"))
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"ipv6-routes-unavailable-or-invalid:{type(exc).__name__}")

    expected_profile_valid = bool(
        expected_apparmor_profile
        and expected_apparmor_profile != "unconfined"
        and "\n" not in expected_apparmor_profile
        and "\r" not in expected_apparmor_profile
    )
    expected_namespace_valid = bool(NETWORK_NAMESPACE_RE.fullmatch(expected_network_namespace))
    host_namespace_valid = bool(NETWORK_NAMESPACE_RE.fullmatch(host_network_namespace))
    apparmor_matches = (
        expected_profile_valid and apparmor_profile == expected_apparmor_profile and apparmor_mode == "enforce"
    )
    namespace_matches = (
        expected_namespace_valid
        and namespace_identity == expected_network_namespace
        and bool(NETWORK_NAMESPACE_RE.fullmatch(namespace_identity))
    )
    namespace_separated_from_host = (
        host_namespace_valid
        and bool(NETWORK_NAMESPACE_RE.fullmatch(namespace_identity))
        and namespace_identity != host_network_namespace
    )
    loopback_only = interfaces == ["lo"]
    no_external_route = all(route["loopback_only"] for route in [*ipv4_routes, *ipv6_routes])
    passed = (
        not errors
        and apparmor_matches
        and namespace_matches
        and namespace_separated_from_host
        and loopback_only
        and no_external_route
    )

    return {
        "apparmor": {
            "label": apparmor_label,
            "profile": apparmor_profile,
            "mode": apparmor_mode,
            "expected_profile": expected_apparmor_profile,
            "matches_reviewed_profile": apparmor_matches,
        },
        "network_namespace": {
            "identity": namespace_identity,
            "expected_identity": expected_network_namespace,
            "host_identity": host_network_namespace,
            "matches_reviewed_namespace": namespace_matches,
            "host_identity_valid": host_namespace_valid,
            "separated_from_host": namespace_separated_from_host,
        },
        "interfaces": interfaces,
        "loopback_only": loopback_only,
        "ipv4_routes": ipv4_routes,
        "ipv6_routes": ipv6_routes,
        "no_external_route": no_external_route,
        "errors": errors,
        "passed": passed,
    }


def _attempt_ipv4() -> dict[str, Any]:
    target = ("198.51.100.1", 9)  # RFC 5737 TEST-NET-2.
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(0.5)
    try:
        client.connect(target)
    except OSError as exc:
        policy_denied = exc.errno in POLICY_ERRNOS
        return {
            "surface": "ipv4_tcp_connect",
            "target_class": "RFC5737_TEST_NET",
            "outcome": "policy_denied" if policy_denied else "ambiguous_or_not_policy_denied",
            "errno": exc.errno,
            "errno_name": errno.errorcode.get(exc.errno, "UNKNOWN"),
            "error_type": type(exc).__name__,
        }
    finally:
        client.close()
    return {
        "surface": "ipv4_tcp_connect",
        "target_class": "RFC5737_TEST_NET",
        "outcome": "connection_succeeded",
        "errno": None,
        "errno_name": None,
        "error_type": None,
    }


def build_receipt(
    *,
    expected_apparmor_profile: str,
    expected_network_namespace: str,
    host_network_namespace: str,
) -> dict[str, Any]:
    boundary = collect_boundary_evidence(
        expected_apparmor_profile=expected_apparmor_profile,
        expected_network_namespace=expected_network_namespace,
        host_network_namespace=host_network_namespace,
    )
    if boundary.get("passed") is True:
        ipv4_result = _attempt_ipv4()
    else:
        ipv4_result = {
            "surface": "ipv4_tcp_connect",
            "target_class": "RFC5737_TEST_NET",
            "outcome": "not_attempted_boundary_invalid",
            "errno": None,
            "errno_name": None,
            "error_type": None,
        }
    policy_errno = ipv4_result.get("errno") in POLICY_ERRNOS
    passed = boundary.get("passed") is True and ipv4_result.get("outcome") == "policy_denied" and policy_errno
    dns_policy = {
        "surface": "dns_resolution",
        "outcome": "not_used_as_policy_evidence",
        "attempted": False,
        "accepted_as_policy_evidence": False,
        "reason": (
            "DNS failure and NXDOMAIN can occur without an enforced egress "
            "boundary, so this canary neither attempts nor accepts them."
        ),
    }
    return {
        "schema": "world-human-aid-egress-canary/v2",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "synthetic_fixture": True,
        "human_approval": False,
        "contains_secrets": False,
        "offline": True,
        "passed": passed,
        "boundary": boundary,
        "results": [ipv4_result, dns_policy],
        "interpretation": (
            "Passing proves only that this process matched the named enforcing "
            "AppArmor profile and reviewed network namespace, that the namespace "
            "identity differed from the host identity captured before unshare, "
            "that it exposed only loopback routes/interfaces, and that the "
            "bounded synthetic connect received a policy-consistent errno. It "
            "is not Gate 0B approval and does not authorize secrets or live "
            "network activity."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--inside-reviewed-deny-sandbox",
        action="store_true",
        help="Required acknowledgement; the script refuses an unconfined run.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Required acknowledgement that external egress is expected to be denied.",
    )
    parser.add_argument(
        "--expected-apparmor-profile",
        required=True,
        help="Exact reviewed AppArmor profile name expected in /proc/self/attr/current.",
    )
    parser.add_argument(
        "--expected-network-namespace",
        required=True,
        help="Exact reviewed network namespace identity, for example net:[4026533000].",
    )
    parser.add_argument(
        "--host-network-namespace",
        required=True,
        help=(
            "Host network namespace identity captured before unshare; it must "
            "differ from the current reviewed namespace."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.inside_reviewed_deny_sandbox or not args.offline:
        raise SystemExit("--inside-reviewed-deny-sandbox and --offline are both required")

    receipt_path = args.receipt.resolve()
    if receipt_path.exists():
        raise SystemExit(f"refusing to overwrite existing receipt: {receipt_path}")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    receipt = build_receipt(
        expected_apparmor_profile=args.expected_apparmor_profile,
        expected_network_namespace=args.expected_network_namespace,
        host_network_namespace=args.host_network_namespace,
    )
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": receipt["passed"], "receipt": str(receipt_path)}))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
