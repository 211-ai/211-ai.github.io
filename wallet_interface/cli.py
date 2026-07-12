"""Console entry points for the wallet API."""

from __future__ import annotations

import importlib
import os


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            'uvicorn is required to run the wallet API CLI. Install it with: python3 -m pip install -e ".[wallet]"'
        ) from exc

    host = os.getenv("WALLET_API_HOST", "127.0.0.1")
    port_raw = os.getenv("WALLET_API_PORT", "8000")
    try:
        port = int(port_raw)
    except ValueError as exc:  # pragma: no cover - configuration guard
        raise RuntimeError(f"WALLET_API_PORT must be an integer, got: {port_raw!r}") from exc
    reload = os.getenv("WALLET_API_RELOAD", "false").lower() in {"1", "true", "yes", "on"}
    try:
        asgi_module = importlib.import_module("wallet_interface.asgi")
        getattr(asgi_module, "app")
    except (ImportError, AttributeError) as exc:  # pragma: no cover - configuration guard
        raise RuntimeError(
            "wallet_interface.asgi:app not found. Ensure the wallet API module is properly configured."
        ) from exc
    uvicorn.run("wallet_interface.asgi:app", host=host, port=port, reload=reload)
