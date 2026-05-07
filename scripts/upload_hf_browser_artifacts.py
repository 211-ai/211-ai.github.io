#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download


DEFAULT_BROWSER_DIR = Path("wallet_interface/ui/public/corpus/211-info/current")
DEFAULT_REPO_ID = "endomorphosis/211-info"
DEFAULT_REMOTE_PREFIX = "browser/211-info/current"


def iter_local_files(browser_dir: Path) -> list[Path]:
    return sorted(path for path in browser_dir.rglob("*") if path.is_file())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remote_size_map(api: HfApi, repo_id: str) -> tuple[str, dict[str, int]]:
    info = api.repo_info(repo_id, repo_type="dataset", files_metadata=True)
    sizes: dict[str, int] = {}
    for sibling in info.siblings:
        size = getattr(sibling, "size", None)
        if size is not None:
            sizes[sibling.rfilename] = int(size)
    return str(info.sha), sizes


def manifest_summary(browser_dir: Path) -> dict[str, Any]:
    manifest_path = browser_dir / "artifacts.manifest.json"
    generated_manifest_path = browser_dir / "generated" / "generated-manifest.json"
    result: dict[str, Any] = {
        "artifacts_manifest_available": manifest_path.exists(),
        "generated_manifest_available": generated_manifest_path.exists(),
    }
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        result["dataset_id"] = manifest.get("datasetId")
        result["dataset_path"] = manifest.get("datasetPath")
        result["artifact_count"] = len(manifest.get("artifacts") or [])
        result["corpus"] = manifest.get("corpus") or {}
        result["source_package"] = manifest.get("sourcePackage") or {}
    if generated_manifest_path.exists():
        generated = json.loads(generated_manifest_path.read_text())
        result["generated"] = {
            "document_count": generated.get("documentCount"),
            "embedding_count": generated.get("embeddingCount"),
            "embedding_dimension": generated.get("embeddingDimension"),
            "embedding_model": generated.get("embeddingModel"),
            "bm25_document_count": generated.get("bm25DocumentCount"),
            "graph_neighborhood_count": generated.get("graphNeighborhoodCount"),
            "graph_neighborhood_shard_count": generated.get("graphNeighborhoodShardCount"),
            "graph_community_count": generated.get("graphCommunityCount"),
            "document_community_count": generated.get("documentCommunityCount"),
        }
    return result


def audit_browser_artifacts(
    *,
    browser_dir: Path,
    repo_id: str,
    remote_prefix: str,
    verify_hashes: bool = False,
    api: HfApi | None = None,
) -> dict[str, Any]:
    browser_dir = browser_dir.resolve()
    api = api or HfApi()
    commit_sha, remote_sizes = remote_size_map(api, repo_id)
    local_files = iter_local_files(browser_dir)

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    hash_mismatches: list[dict[str, Any]] = []
    for local_path in local_files:
        relative_path = local_path.relative_to(browser_dir).as_posix()
        remote_path = f"{remote_prefix}/{relative_path}".strip("/")
        local_size = int(local_path.stat().st_size)
        remote_size = remote_sizes.get(remote_path)
        status = "ok" if remote_size == local_size else "missing" if remote_size is None else "size_mismatch"
        record: dict[str, Any] = {
            "relative_path": relative_path,
            "remote_path": remote_path,
            "local_size": local_size,
            "remote_size": remote_size,
            "status": status,
        }
        if verify_hashes and status == "ok":
            downloaded_path = Path(
                hf_hub_download(
                    repo_id=repo_id,
                    filename=remote_path,
                    repo_type="dataset",
                )
            )
            local_sha = sha256_file(local_path)
            remote_sha = sha256_file(downloaded_path)
            record["local_sha256"] = local_sha
            record["remote_sha256"] = remote_sha
            record["sha256_match"] = local_sha == remote_sha
            if local_sha != remote_sha:
                record["status"] = "hash_mismatch"
                hash_mismatches.append(record)

        records.append(record)
        if status == "missing":
            missing.append(remote_path)
        elif status == "size_mismatch":
            size_mismatches.append(record)

    matched_records = [record for record in records if record["status"] == "ok"]
    return {
        "repo_id": repo_id,
        "repo_commit_sha": commit_sha,
        "browser_dir": str(browser_dir),
        "remote_prefix": remote_prefix,
        "local_file_count": len(local_files),
        "remote_file_count": len(remote_sizes),
        "matched_file_count": len(matched_records),
        "missing_remote_files": missing,
        "size_mismatches": size_mismatches,
        "hash_mismatches": hash_mismatches,
        "local_total_size": sum(record["local_size"] for record in records),
        "matched_total_size": sum(record["local_size"] for record in matched_records),
        "manifest": manifest_summary(browser_dir),
    }


def upload_browser_artifacts(
    *,
    browser_dir: Path,
    repo_id: str,
    remote_prefix: str,
    private: bool = False,
    force_upload: bool = False,
    verify_hashes: bool = False,
) -> dict[str, Any]:
    browser_dir = browser_dir.resolve()
    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)

    pre_upload_audit = audit_browser_artifacts(
        browser_dir=browser_dir,
        repo_id=repo_id,
        remote_prefix=remote_prefix,
        verify_hashes=False,
        api=api,
    )
    needs_upload = bool(
        force_upload
        or pre_upload_audit["missing_remote_files"]
        or pre_upload_audit["size_mismatches"]
        or pre_upload_audit["matched_file_count"] != pre_upload_audit["local_file_count"]
    )
    if needs_upload:
        delete_patterns = [f"{remote_prefix}/**"] if force_upload else None
        api.upload_folder(
            repo_id=repo_id,
            repo_type="dataset",
            folder_path=str(browser_dir),
            path_in_repo=remote_prefix,
            delete_patterns=delete_patterns,
            commit_message="Upload browser-ready 211 GraphRAG artifacts",
        )

    post_upload_audit = audit_browser_artifacts(
        browser_dir=browser_dir,
        repo_id=repo_id,
        remote_prefix=remote_prefix,
        verify_hashes=verify_hashes,
        api=api,
    )
    return {
        "repo_id": repo_id,
        "browser_dir": str(browser_dir),
        "remote_prefix": remote_prefix,
        "upload_performed": needs_upload,
        "force_upload": force_upload,
        "verified_hashes": verify_hashes,
        "pre_upload_audit": pre_upload_audit,
        "post_upload_audit": post_upload_audit,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload/audit browser-ready 211 GraphRAG artifacts on Hugging Face")
    parser.add_argument("--browser-dir", type=Path, default=DEFAULT_BROWSER_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--remote-prefix", default=DEFAULT_REMOTE_PREFIX)
    parser.add_argument("--private", action="store_true", help="Create the dataset repo as private if it does not exist.")
    parser.add_argument("--upload", action="store_true", help="Upload missing or mismatched browser artifact files.")
    parser.add_argument("--force-upload", action="store_true", help="Delete and reupload the remote browser prefix.")
    parser.add_argument("--verify-hashes", action="store_true", help="Download matching remote files and compare SHA-256.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.upload or args.force_upload:
        result = upload_browser_artifacts(
            browser_dir=args.browser_dir,
            repo_id=args.repo_id,
            remote_prefix=args.remote_prefix,
            private=bool(args.private),
            force_upload=bool(args.force_upload),
            verify_hashes=bool(args.verify_hashes),
        )
    else:
        result = audit_browser_artifacts(
            browser_dir=args.browser_dir,
            repo_id=args.repo_id,
            remote_prefix=args.remote_prefix,
            verify_hashes=bool(args.verify_hashes),
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
