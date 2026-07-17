from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
for import_root in (IPFS_DATASETS_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_DATASETS_PY_MINIMAL_IMPORTS", "1")

from scraper.utils import setup_logging
from wallet_interface import WalletInterfaceService

logger = logging.getLogger("wallet_interface.hmis.reconciliation")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HMIS reconciliation job")
    parser.add_argument("--once", action="store_true", help="Run one reconciliation pass and exit")
    parser.add_argument("--dry-run", action="store_true", help="Summarize work without mutating state")
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=REPO_ROOT / "data" / "hmis" / "runtime_repository",
        help="Repository root used for HMIS state persistence",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    service = WalletInterfaceService(repository_root=args.repository_root)
    result = service.run_hmis_reconciliation_job(dry_run=args.dry_run)
    logger.info("HMIS reconciliation job complete: %s", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
