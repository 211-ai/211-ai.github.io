"""Pytest bootstrap for local 211-AI development."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
VENDORED_IPFS_DATASETS = REPO_ROOT / "ipfs_datasets_py"

for candidate in (REPO_ROOT, VENDORED_IPFS_DATASETS):
    if candidate.exists():
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
