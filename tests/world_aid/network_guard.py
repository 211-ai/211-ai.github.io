"""Deterministic Python-level network deny/spy for World human-aid tests.

The guard permits loopback and Unix-domain fixtures.  Every other DNS, socket,
HTTP, or asyncio connection attempt is recorded and denied.  This is a test
boundary, not a replacement for the Gate 0B OS/container egress policy.
"""

from __future__ import annotations

import asyncio
import http.client
import ipaddress
import socket
import urllib.request
from dataclasses import dataclass
from typing import Any


class UnexpectedWorldAidNetworkAccess(RuntimeError):
    """Raised when a World human-aid test attempts non-local network access."""


@dataclass(frozen=True)
class NetworkAttempt:
    surface: str
    target: str


def _host_is_local(host: object) -> bool:
    if not isinstance(host, str):
        return False
    normalized = host.strip().lower().rstrip(".")
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _address_is_local(address: object) -> bool:
    if isinstance(address, str):
        return True  # Unix-domain socket path.
    if isinstance(address, tuple) and address:
        return _host_is_local(address[0])
    return False


def install_network_guard(monkeypatch: Any, attempts: list[NetworkAttempt]) -> None:
    """Install the deny/spy using a pytest-compatible monkeypatch object."""

    original_socket = socket.socket
    original_getaddrinfo = socket.getaddrinfo
    original_create_connection = socket.create_connection
    original_asyncio_open_connection = asyncio.open_connection
    original_http_connect = http.client.HTTPConnection.connect
    original_https_connect = http.client.HTTPSConnection.connect
    original_urlopen = urllib.request.urlopen

    def deny(surface: str, target: object) -> None:
        attempt = NetworkAttempt(surface=surface, target=repr(target))
        attempts.append(attempt)
        raise UnexpectedWorldAidNetworkAccess(f"unexpected World human-aid network access: {surface} {attempt.target}")

    class GuardedSocket(original_socket):
        def connect(self, address: object) -> None:
            if self.family == socket.AF_UNIX or _address_is_local(address):
                return super().connect(address)  # type: ignore[arg-type]
            deny("socket.connect", address)

        def connect_ex(self, address: object) -> int:
            if self.family == socket.AF_UNIX or _address_is_local(address):
                return super().connect_ex(address)  # type: ignore[arg-type]
            deny("socket.connect_ex", address)
            raise AssertionError("unreachable")

        def sendto(self, data: bytes, *args: object) -> int:
            address = args[-1] if args else None
            if self.family == socket.AF_UNIX or _address_is_local(address):
                return super().sendto(data, *args)  # type: ignore[arg-type]
            deny("socket.sendto", address)
            raise AssertionError("unreachable")

    def guarded_getaddrinfo(host: object, *args: object, **kwargs: object) -> object:
        if host is None or _host_is_local(host):
            return original_getaddrinfo(host, *args, **kwargs)
        deny("dns.getaddrinfo", host)
        raise AssertionError("unreachable")

    def guarded_create_connection(address: object, *args: object, **kwargs: object) -> socket.socket:
        if _address_is_local(address):
            return original_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]
        deny("socket.create_connection", address)
        raise AssertionError("unreachable")

    async def guarded_asyncio_open_connection(
        host: object = None, port: object = None, *args: object, **kwargs: object
    ) -> object:
        if host is None or _host_is_local(host):
            return await original_asyncio_open_connection(host, port, *args, **kwargs)
        deny("asyncio.open_connection", (host, port))
        raise AssertionError("unreachable")

    def guarded_http_connect(connection: object) -> None:
        host = getattr(connection, "host", None)
        if _host_is_local(host):
            return original_http_connect(connection)  # type: ignore[arg-type]
        deny("http.connect", (host, getattr(connection, "port", None)))

    def guarded_https_connect(connection: object) -> None:
        host = getattr(connection, "host", None)
        if _host_is_local(host):
            return original_https_connect(connection)  # type: ignore[arg-type]
        deny("https.connect", (host, getattr(connection, "port", None)))

    def guarded_urlopen(url: object, *args: object, **kwargs: object) -> object:
        rendered = getattr(url, "full_url", url)
        text = str(rendered)
        if text.startswith(("http://localhost", "https://localhost")):
            return original_urlopen(url, *args, **kwargs)
        deny("urllib.request.urlopen", text)
        raise AssertionError("unreachable")

    monkeypatch.setattr(socket, "socket", GuardedSocket)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(asyncio, "open_connection", guarded_asyncio_open_connection)
    monkeypatch.setattr(http.client.HTTPConnection, "connect", guarded_http_connect)
    monkeypatch.setattr(http.client.HTTPSConnection, "connect", guarded_https_connect)
    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)
