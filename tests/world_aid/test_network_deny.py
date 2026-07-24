from __future__ import annotations

import asyncio
import socket
import urllib.request

import pytest

from .network_guard import UnexpectedWorldAidNetworkAccess

pytestmark = pytest.mark.world_aid_egress_canary


def test_dns_canary_is_blocked_and_reported(world_aid_network_deny) -> None:
    with pytest.raises(UnexpectedWorldAidNetworkAccess):
        socket.getaddrinfo("world-aid-egress-canary.invalid", 443)
    assert [attempt.surface for attempt in world_aid_network_deny] == ["dns.getaddrinfo"]


def test_socket_canary_is_blocked_and_reported(world_aid_network_deny) -> None:
    with socket.socket() as client:
        with pytest.raises(UnexpectedWorldAidNetworkAccess):
            client.connect(("198.51.100.1", 443))
    assert [attempt.surface for attempt in world_aid_network_deny] == ["socket.connect"]


def test_http_canary_is_blocked_and_reported(world_aid_network_deny) -> None:
    with pytest.raises(UnexpectedWorldAidNetworkAccess):
        urllib.request.urlopen("https://world-aid-egress-canary.invalid")
    assert [attempt.surface for attempt in world_aid_network_deny] == ["urllib.request.urlopen"]


def test_asyncio_canary_is_blocked_and_reported(world_aid_network_deny) -> None:
    async def exercise() -> None:
        with pytest.raises(UnexpectedWorldAidNetworkAccess):
            await asyncio.open_connection("198.51.100.1", 443)

    asyncio.run(exercise())
    assert [attempt.surface for attempt in world_aid_network_deny] == ["asyncio.open_connection"]


def test_loopback_dns_remains_available(world_aid_network_deny) -> None:
    assert socket.getaddrinfo("localhost", 80)
    assert not world_aid_network_deny
