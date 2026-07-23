"""Pytest bootstrap for local 211-AI development."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
VENDORED_IPFS_DATASETS = REPO_ROOT / "ipfs_datasets_py"
LOCAL_IPFS_ACCELERATE = REPO_ROOT / "ipfs_accelerate_py"

# insert(0) means the final candidate has highest precedence. Keep the local
# voice-router checkout ahead of editable sibling installations.
for candidate in (REPO_ROOT, VENDORED_IPFS_DATASETS, LOCAL_IPFS_ACCELERATE):
    if candidate.exists():
        candidate_str = str(candidate)
        if candidate_str in sys.path:
            sys.path.remove(candidate_str)
        sys.path.insert(0, candidate_str)
