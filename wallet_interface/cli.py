"""Console entry points for the wallet API."""

from __future__ import annotations

import os


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("uvicorn is required to run the wallet API CLI") from exc

    host = os.getenv("WALLET_API_HOST", "127.0.0.1")
    port_raw = os.getenv("WALLET_API_PORT", "8000")
    try:
        port = int(port_raw)
    except ValueError as exc:  # pragma: no cover - configuration guard
        raise RuntimeError(f"WALLET_API_PORT must be an integer, got: {port_raw!r}") from exc
    reload = os.getenv("WALLET_API_RELOAD", "false").lower() in {"1", "true", "yes", "on"}
    uvicorn.run("wallet_interface.asgi:app", host=host, port=port, reload=reload)
