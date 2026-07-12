from __future__ import annotations

import builtins
import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

CLI_PATH = Path(__file__).resolve().parents[1] / "wallet_interface" / "cli.py"
CLI_SPEC = importlib.util.spec_from_file_location("wallet_interface_cli_module", CLI_PATH)
assert CLI_SPEC is not None and CLI_SPEC.loader is not None
cli = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(cli)
EXPECTED_ASGI_MODULE = "wallet_interface.asgi"


def test_wallet_cli_reports_missing_uvicorn_dependency(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "uvicorn":
            raise ImportError("missing uvicorn")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match=re.escape('python3 -m pip install -e ".[wallet]"')):
        cli.main()


def test_wallet_cli_rejects_invalid_port(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=Mock()))
    monkeypatch.setenv("WALLET_API_PORT", "not-a-port")

    with pytest.raises(RuntimeError, match="WALLET_API_PORT must be an integer"):
        cli.main()


def test_wallet_cli_reports_missing_asgi_app(monkeypatch) -> None:
    uvicorn_run = Mock()

    def import_asgi_module(module_name: str) -> SimpleNamespace:
        assert module_name == EXPECTED_ASGI_MODULE
        return SimpleNamespace()

    monkeypatch.setattr(cli, "importlib", SimpleNamespace(import_module=import_asgi_module))
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=uvicorn_run))

    with pytest.raises(RuntimeError, match="wallet_interface.asgi:app not found"):
        cli.main()

    uvicorn_run.assert_not_called()


def test_wallet_cli_reports_missing_asgi_module(monkeypatch) -> None:
    uvicorn_run = Mock()

    def import_asgi_module(module_name: str) -> SimpleNamespace:
        assert module_name == EXPECTED_ASGI_MODULE
        raise ImportError("missing asgi module")

    monkeypatch.setattr(cli, "importlib", SimpleNamespace(import_module=import_asgi_module))
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=uvicorn_run))

    with pytest.raises(RuntimeError, match="wallet_interface.asgi:app not found"):
        cli.main()

    uvicorn_run.assert_not_called()


def test_wallet_cli_runs_uvicorn_with_env_config(monkeypatch) -> None:
    uvicorn_run = Mock()

    def import_asgi_module(module_name: str) -> SimpleNamespace:
        assert module_name == EXPECTED_ASGI_MODULE
        return SimpleNamespace(app=object())

    monkeypatch.setenv("WALLET_API_HOST", "0.0.0.0")
    monkeypatch.setenv("WALLET_API_PORT", "9001")
    monkeypatch.setenv("WALLET_API_RELOAD", "yes")
    monkeypatch.setattr(cli, "importlib", SimpleNamespace(import_module=import_asgi_module))
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=uvicorn_run))

    cli.main()

    uvicorn_run.assert_called_once_with("wallet_interface.asgi:app", host="0.0.0.0", port=9001, reload=True)
