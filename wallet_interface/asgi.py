"""ASGI entrypoint for deployed 211-AI wallet API instances."""

from __future__ import annotations

from .api import create_app

app = create_app()

