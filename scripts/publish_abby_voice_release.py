#!/usr/bin/env python3
"""Plan (and only with explicit approval, publish) an Abby voice HF release.

Default mode is ``--dry-run``: produce a deterministic dry-run diff and cost
receipt and write ``data/abby_voice/releases/publication-receipt.json``.
Autonomous workers stop after the dry run.  Remote writes require both
``--execute`` and a reviewed approval JSON matching the plan digest and cost
bound.  Tokens are never written into receipts or logs.

Goal: ABBY-VOICE-G021
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "ipfs_datasets_py"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from ipfs_datasets_py.huggingface.publisher import (  # noqa: E402
    HuggingFacePublicationError,
    PublicationApproval,
    publish_abby_voice_release,
)

DEFAULT_MANIFEST = (
    REPO_ROOT / "data" / "abby_voice" / "releases" / "release-manifest.json"
)
DEFAULT_RECEIPT = (
    REPO_ROOT / "data" / "abby_voice" / "releases" / "publication-receipt.json"
)


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SystemExit(f"JSON root must be an object: {path}")
    return payload


def _approval_from_mapping(value: Mapping[str, Any]) -> PublicationApproval:
    return PublicationApproval(
        approver=str(value.get("approver") or ""),
        plan_digest=str(value.get("plan_digest") or ""),
        max_cost_usd=float(value.get("max_cost_usd", -1)),
        max_upload_bytes=int(value.get("max_upload_bytes", -1)),
        credentials_scope=str(value.get("credentials_scope") or ""),
        approval_id=str(value.get("approval_id") or ""),
        notes=str(value.get("notes") or ""),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Publish and promote an immutable Abby voice Hugging Face release "
            "(default: dry-run only)."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the signed/reviewed local release manifest",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=DEFAULT_RECEIPT,
        help="Where to write the publication receipt (dry-run or post-commit)",
    )
    parser.add_argument(
        "--local-root",
        type=Path,
        default=None,
        help="Directory containing local release files (defaults to manifest parent)",
    )
    parser.add_argument(
        "--repository-id",
        default="Publicus/211-abby-tts",
        help="Target Hugging Face dataset repository",
    )
    parser.add_argument(
        "--audited-parent-commit",
        default="",
        help=(
            "Exact 40-64 hex commit SHA audited before this plan. It is included "
            "in plan_digest and required by --execute."
        ),
    )
    parser.add_argument(
        "--target-revision",
        default="main",
        help="Branch protected by the parent-commit race guard (currently: main)",
    )
    parser.add_argument(
        "--verified-cache-root",
        type=Path,
        default=None,
        help=(
            "Empty directory for the real pinned redownload. If omitted during "
            "--execute, a new persistent temporary directory is created."
        ),
    )
    parser.add_argument(
        "--pinned-download-workers",
        type=int,
        default=8,
        help="Bounded concurrent pinned downloads during verification (1-32; default: 8)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Produce dry-run diff and cost receipt only (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Execute the approved append-only create_commit. Requires "
            "--approval-json and HF credentials in the environment (never logged)."
        ),
    )
    parser.add_argument(
        "--approval-json",
        type=Path,
        default=None,
        help="Human approval JSON binding plan_digest, cost bound, and credentials scope",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="Print the dry-run plan digest and cost summary to stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = args.manifest.expanduser().resolve()
    if not manifest_path.is_file():
        print(f"error: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    dry_run = not bool(args.execute)
    if args.execute and args.approval_json is None:
        print(
            "error: --execute requires --approval-json; "
            "autonomous work stops after a dry run",
            file=sys.stderr,
        )
        return 2
    if args.execute and not str(args.audited_parent_commit).strip():
        print(
            "error: --execute requires --audited-parent-commit; "
            "rerun the dry-run with that same commit before approval",
            file=sys.stderr,
        )
        return 2

    approval = None
    if args.approval_json is not None:
        approval = _approval_from_mapping(_load_json(args.approval_json.expanduser()))

    api = None
    if not dry_run:
        # Import only when executing so dry-run needs no network stack or token.
        try:
            from huggingface_hub import HfApi
        except ImportError as exc:
            print(
                f"error: huggingface_hub is required for --execute: {exc}",
                file=sys.stderr,
            )
            return 2
        # Token is read from the environment by HfApi; never serialize it.
        api = HfApi()

    try:
        receipt = publish_abby_voice_release(
            manifest=manifest_path,
            dry_run=dry_run,
            local_root=args.local_root,
            repository_id=str(args.repository_id),
            audited_parent_commit=str(args.audited_parent_commit),
            target_revision=str(args.target_revision),
            approval=approval,
            api=api,
            verified_cache_root=(
                args.verified_cache_root.expanduser().resolve()
                if args.verified_cache_root is not None
                else None
            ),
            pinned_download_workers=int(args.pinned_download_workers),
            receipt_path=args.receipt.expanduser().resolve(),
        )
    except HuggingFacePublicationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.print_plan or dry_run:
        plan = receipt.get("dry_run_diff_and_cost_receipt") or {}
        cost = plan.get("cost_receipt") or {}
        summary = {
            "status": receipt.get("status"),
            "dry_run": receipt.get("dry_run"),
            "remote_write_performed": receipt.get("remote_write_performed"),
            "repository_id": receipt.get("repository_id"),
            "release_id": plan.get("release_id"),
            "release_prefix": plan.get("release_prefix"),
            "audited_parent_commit": plan.get("audited_parent_commit"),
            "target_revision": plan.get("target_revision"),
            "plan_digest": plan.get("plan_digest"),
            "upload_file_count": plan.get("upload_file_count"),
            "upload_bytes": plan.get("upload_bytes"),
            "estimated_cost_usd": cost.get("estimated_cost_usd"),
            "receipt_path": str(args.receipt.expanduser().resolve()),
            "evidence": receipt.get("evidence"),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
