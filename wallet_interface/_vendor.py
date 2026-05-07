"""Import helpers for the vendored `ipfs_datasets_py` checkout."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_ipfs_datasets_py_path() -> None:
    """Make the local vendored package importable when not installed.

    Production deployments should install `ipfs_datasets_py` normally. This
    helper keeps the in-repo 211-AI interface usable during development.
    """

    root = Path(__file__).resolve().parents[1]
    vendored = root / "ipfs_datasets_py"
    if (vendored / "ipfs_datasets_py").is_dir():
        path = str(vendored)
        if path not in sys.path:
            sys.path.insert(0, path)
