#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download


DEFAULT_PACKAGE_DIR = Path("data/retrieval_package")
DEFAULT_REPO_ID = "endomorphosis/211-info"
DEFAULT_REMOTE_PREFIX = "data"


def iter_local_files(package_dir: Path) -> list[Path]:
    return sorted(path for path in package_dir.rglob("*") if path.is_file())


def remote_size_map(repo_id: str) -> tuple[str, dict[str, int]]:
    info = HfApi().repo_info(repo_id, repo_type="dataset", files_metadata=True)
    sizes: dict[str, int] = {}
    for sibling in info.siblings:
        size = getattr(sibling, "size", None)
        if size is not None:
            sizes[sibling.rfilename] = int(size)
    return str(info.sha), sizes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def documents_stats(package_dir: Path) -> dict[str, Any]:
    documents_path = package_dir / "content" / "documents.parquet"
    if not documents_path.exists():
        return {"available": False}

    frame = pd.read_parquet(documents_path)
    text_lengths = frame["text"].fillna("").str.len()
    metadata_lengths = frame["metadata_json"].fillna("").str.len()
    return {
        "available": True,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "doc_type_counts": {str(key): int(value) for key, value in frame["doc_type"].value_counts().items()},
        "nonempty_text_rows": int((text_lengths > 0).sum()),
        "nonempty_source_content_cid_rows": int((frame["source_content_cid"].fillna("").str.len() > 0).sum()),
        "text_length": {
            "min": int(text_lengths.min()),
            "median": int(text_lengths.median()),
            "mean": int(text_lengths.mean()),
            "p95": int(text_lengths.quantile(0.95)),
            "p99": int(text_lengths.quantile(0.99)),
            "max": int(text_lengths.max()),
            "sum": int(text_lengths.sum()),
        },
        "metadata_json_length": {
            "min": int(metadata_lengths.min()),
            "median": int(metadata_lengths.median()),
            "mean": int(metadata_lengths.mean()),
            "max": int(metadata_lengths.max()),
            "sum": int(metadata_lengths.sum()),
        },
    }


def compare_remote_documents_hash(repo_id: str, package_dir: Path, remote_prefix: str) -> dict[str, Any]:
    local_path = package_dir / "content" / "documents.parquet"
    remote_path = f"{remote_prefix}/content/documents.parquet"
    downloaded_path = Path(hf_hub_download(repo_id, remote_path, repo_type="dataset"))
    local_sha = sha256_file(local_path)
    remote_sha = sha256_file(downloaded_path)
    return {
        "remote_path": remote_path,
        "local_size": int(local_path.stat().st_size),
        "remote_size": int(downloaded_path.stat().st_size),
        "local_sha256": local_sha,
        "remote_sha256": remote_sha,
        "sha256_match": local_sha == remote_sha,
    }


def audit_upload(
    *,
    package_dir: Path,
    repo_id: str,
    remote_prefix: str,
    verify_documents_hash: bool,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    commit_sha, remote_sizes = remote_size_map(repo_id)
    local_files = iter_local_files(package_dir)

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    for local_path in local_files:
        relative_path = local_path.relative_to(package_dir).as_posix()
        remote_path = f"{remote_prefix}/{relative_path}".strip("/")
        local_size = int(local_path.stat().st_size)
        remote_size = remote_sizes.get(remote_path)
        status = "ok" if remote_size == local_size else "missing" if remote_size is None else "size_mismatch"
        record = {
            "relative_path": relative_path,
            "remote_path": remote_path,
            "local_size": local_size,
            "remote_size": remote_size,
            "status": status,
        }
        records.append(record)
        if status == "missing":
            missing.append(remote_path)
        elif status == "size_mismatch":
            size_mismatches.append(record)

    result: dict[str, Any] = {
        "repo_id": repo_id,
        "repo_commit_sha": commit_sha,
        "package_dir": str(package_dir),
        "remote_prefix": remote_prefix,
        "local_file_count": len(local_files),
        "remote_file_count": len(remote_sizes),
        "matched_file_count": sum(1 for record in records if record["status"] == "ok"),
        "missing_remote_files": missing,
        "size_mismatches": size_mismatches,
        "local_total_size": sum(record["local_size"] for record in records),
        "matched_total_size": sum(record["local_size"] for record in records if record["status"] == "ok"),
        "documents_stats": documents_stats(package_dir),
    }
    if verify_documents_hash:
        result["documents_hash_check"] = compare_remote_documents_hash(repo_id, package_dir, remote_prefix)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit local 211 retrieval package files against Hugging Face")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--remote-prefix", default=DEFAULT_REMOTE_PREFIX)
    parser.add_argument(
        "--verify-documents-hash",
        action="store_true",
        help="Download remote documents.parquet and compare SHA-256 with the local file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            audit_upload(
                package_dir=args.package_dir,
                repo_id=args.repo_id,
                remote_prefix=args.remote_prefix,
                verify_documents_hash=args.verify_documents_hash,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
