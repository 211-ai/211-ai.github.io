#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download


DEFAULT_REPO_ID = "endomorphosis/211-info"
DEFAULT_SOURCE_DIR = Path("data/portal")
DEFAULT_REMOTE_PREFIX = "portal/211-info/current/data"
DEFAULT_AUDIT_FILENAME = "upload_audit.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hf_token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_portal_files(source_dir: Path, *, audit_filename: str = DEFAULT_AUDIT_FILENAME) -> list[Path]:
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.name != audit_filename
    )


def remote_size_map(api: HfApi, repo_id: str) -> tuple[str, dict[str, int]]:
    info = api.repo_info(repo_id, repo_type="dataset", files_metadata=True)
    sizes: dict[str, int] = {}
    for sibling in info.siblings:
        size = getattr(sibling, "size", None)
        if size is not None:
            sizes[sibling.rfilename] = int(size)
    return str(info.sha), sizes


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False}
    return {"available": True, "content": json.loads(path.read_text(encoding="utf-8"))}


def portal_manifest_summary(source_dir: Path) -> dict[str, Any]:
    service_manifest = load_json_file(source_dir / "service_portal_manifest.json")
    extraction_manifest = load_json_file(source_dir / "extraction_manifest.json")
    coverage_report = load_json_file(source_dir / "extraction_coverage_report.json")

    summary: dict[str, Any] = {
        "service_portal_manifest_available": bool(service_manifest["available"]),
        "extraction_manifest_available": bool(extraction_manifest["available"]),
        "extraction_coverage_report_available": bool(coverage_report["available"]),
    }
    if service_manifest["available"]:
        manifest = service_manifest["content"]
        summary["schema_version"] = manifest.get("schemaVersion")
        summary["generated_at"] = manifest.get("generated_at")
        summary["portal_manifest_cid"] = manifest.get("portal_manifest_cid")
        summary["source_package"] = manifest.get("source_package") or {}
        summary["service_count"] = int(manifest.get("service_count") or 0)
        summary["contact_count"] = int(manifest.get("contact_count") or 0)
        summary["location_count"] = int(manifest.get("location_count") or 0)
        summary["hours_count"] = int(manifest.get("hours_count") or 0)
        summary["requirement_count"] = int(manifest.get("requirement_count") or 0)
        summary["action_count"] = int(manifest.get("action_count") or 0)
        summary["artifact_count"] = len(manifest.get("artifacts") or [])
    if coverage_report["available"]:
        coverage = coverage_report["content"]
        summary["coverage_service_count"] = int(coverage.get("service_count") or 0)
        summary["coverage_fields"] = sorted((coverage.get("coverage") or {}).keys())
    return summary


def audit_portal_package(
    *,
    source_dir: Path,
    repo_id: str,
    remote_prefix: str,
    verify_hashes: bool,
    audit_filename: str = DEFAULT_AUDIT_FILENAME,
    api: HfApi | None = None,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Portal source directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Portal source path is not a directory: {source_dir}")

    api = api or HfApi(token=hf_token())
    commit_sha, remote_sizes = remote_size_map(api, repo_id)
    local_files = iter_portal_files(source_dir, audit_filename=audit_filename)

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    hash_mismatches: list[dict[str, Any]] = []
    hash_verified_count = 0

    for local_path in local_files:
        relative_path = local_path.relative_to(source_dir).as_posix()
        remote_path = f"{remote_prefix}/{relative_path}".strip("/")
        local_size = int(local_path.stat().st_size)
        remote_size = remote_sizes.get(remote_path)
        status = "ok" if remote_size == local_size else "missing" if remote_size is None else "size_mismatch"
        record: dict[str, Any] = {
            "relative_path": relative_path,
            "remote_path": remote_path,
            "local_size": local_size,
            "remote_size": remote_size,
            "local_sha256": sha256_file(local_path),
            "status": status,
        }
        if verify_hashes and status == "ok":
            downloaded_path = Path(
                hf_hub_download(
                    repo_id=repo_id,
                    filename=remote_path,
                    repo_type="dataset",
                    token=hf_token(),
                )
            )
            remote_sha = sha256_file(downloaded_path)
            record["remote_sha256"] = remote_sha
            record["sha256_match"] = record["local_sha256"] == remote_sha
            hash_verified_count += 1
            if record["local_sha256"] != remote_sha:
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
        "source_dir": str(source_dir),
        "remote_prefix": remote_prefix,
        "local_file_count": len(local_files),
        "remote_file_count": len(remote_sizes),
        "matched_file_count": len(matched_records),
        "hash_verified_file_count": hash_verified_count,
        "missing_remote_files": missing,
        "size_mismatches": size_mismatches,
        "hash_mismatches": hash_mismatches,
        "local_total_size": sum(record["local_size"] for record in records),
        "matched_total_size": sum(record["local_size"] for record in matched_records),
        "manifest": portal_manifest_summary(source_dir),
        "files": records,
    }


def package_is_fully_matched(audit: dict[str, Any], *, require_hashes: bool) -> bool:
    if audit["missing_remote_files"] or audit["size_mismatches"] or audit["hash_mismatches"]:
        return False
    if audit["matched_file_count"] != audit["local_file_count"]:
        return False
    if require_hashes and audit["hash_verified_file_count"] != audit["local_file_count"]:
        return False
    return True


def write_audit(source_dir: Path, audit_filename: str, payload: dict[str, Any]) -> Path:
    audit_path = source_dir / audit_filename
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit_path


def local_artifact_audit(source_dir: Path, *, remote_prefix: str, audit_filename: str) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    local_files = iter_portal_files(source_dir, audit_filename=audit_filename) if source_dir.exists() else []
    records: list[dict[str, Any]] = []
    for local_path in local_files:
        relative_path = local_path.relative_to(source_dir).as_posix()
        records.append(
            {
                "relative_path": relative_path,
                "remote_path": f"{remote_prefix}/{relative_path}".strip("/"),
                "local_size": int(local_path.stat().st_size),
                "remote_size": None,
                "local_sha256": sha256_file(local_path),
                "status": "remote_not_checked",
            }
        )
    return {
        "source_dir": str(source_dir),
        "remote_prefix": remote_prefix,
        "local_file_count": len(records),
        "local_total_size": sum(record["local_size"] for record in records),
        "manifest": portal_manifest_summary(source_dir) if source_dir.exists() else {},
        "files": records,
    }


def write_failure_audit(
    *,
    source_dir: Path,
    repo_id: str,
    remote_prefix: str,
    audit_filename: str,
    upload_enabled: bool,
    exc: BaseException,
) -> None:
    if not source_dir.exists():
        return
    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "repo_id": repo_id,
        "source_dir": str(source_dir.resolve()),
        "remote_prefix": remote_prefix,
        "audit_path": str((source_dir / audit_filename).resolve()),
        "upload_enabled": upload_enabled,
        "upload_performed": False,
        "verified_hashes": False,
        "package_match": False,
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
        "local_artifact_audit": local_artifact_audit(
            source_dir,
            remote_prefix=remote_prefix,
            audit_filename=audit_filename,
        ),
    }
    write_audit(source_dir, audit_filename, payload)


def upload_portal_package(
    *,
    source_dir: Path,
    repo_id: str,
    remote_prefix: str,
    audit_filename: str = DEFAULT_AUDIT_FILENAME,
    private: bool = False,
    force_upload: bool = False,
    verify_hashes: bool = True,
    upload: bool = True,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Portal source directory does not exist: {source_dir}")
    if not iter_portal_files(source_dir, audit_filename=audit_filename):
        raise FileNotFoundError(f"No portal package artifacts found in {source_dir}")

    api = HfApi(token=hf_token())
    if upload:
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)

    pre_upload_audit = audit_portal_package(
        source_dir=source_dir,
        repo_id=repo_id,
        remote_prefix=remote_prefix,
        verify_hashes=False,
        audit_filename=audit_filename,
        api=api,
    )
    needs_upload = bool(force_upload or not package_is_fully_matched(pre_upload_audit, require_hashes=False))

    upload_performed = False
    if upload and needs_upload:
        delete_patterns = [f"{remote_prefix}/**"] if force_upload else None
        api.upload_folder(
            repo_id=repo_id,
            repo_type="dataset",
            folder_path=str(source_dir),
            path_in_repo=remote_prefix,
            delete_patterns=delete_patterns,
            ignore_patterns=[audit_filename],
            commit_message="Upload 211 service portal package artifacts",
        )
        upload_performed = True

    post_upload_audit = audit_portal_package(
        source_dir=source_dir,
        repo_id=repo_id,
        remote_prefix=remote_prefix,
        verify_hashes=verify_hashes,
        audit_filename=audit_filename,
        api=api,
    )
    result = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "repo_id": repo_id,
        "source_dir": str(source_dir),
        "remote_prefix": remote_prefix,
        "audit_path": str((source_dir / audit_filename).resolve()),
        "upload_enabled": upload,
        "upload_performed": upload_performed,
        "force_upload": force_upload,
        "verified_hashes": verify_hashes,
        "package_match": package_is_fully_matched(post_upload_audit, require_hashes=verify_hashes),
        "pre_upload_audit": pre_upload_audit,
        "post_upload_audit": post_upload_audit,
    }
    write_audit(source_dir, audit_filename, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload and audit the structured 211 portal package on Hugging Face")
    parser.add_argument("--repo", "--repo-id", dest="repo_id", default=DEFAULT_REPO_ID)
    parser.add_argument("--source", "--source-dir", dest="source_dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--remote-prefix", default=DEFAULT_REMOTE_PREFIX)
    parser.add_argument("--audit-filename", default=DEFAULT_AUDIT_FILENAME)
    parser.add_argument("--private", action="store_true", help="Create the dataset repo as private if it does not exist.")
    parser.add_argument("--force-upload", action="store_true", help="Delete and reupload the remote portal prefix.")
    parser.add_argument("--audit-only", action="store_true", help="Do not upload; only compare local artifacts to the remote repo.")
    parser.add_argument("--no-verify-hashes", action="store_true", help="Skip remote downloads and verify by size only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = upload_portal_package(
            source_dir=args.source_dir,
            repo_id=args.repo_id,
            remote_prefix=args.remote_prefix,
            audit_filename=args.audit_filename,
            private=bool(args.private),
            force_upload=bool(args.force_upload),
            verify_hashes=not bool(args.no_verify_hashes),
            upload=not bool(args.audit_only),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if not result["package_match"]:
            raise SystemExit("Portal package audit failed: remote artifacts do not match local package")
    except Exception as exc:
        write_failure_audit(
            source_dir=args.source_dir,
            repo_id=args.repo_id,
            remote_prefix=args.remote_prefix,
            audit_filename=args.audit_filename,
            upload_enabled=not bool(args.audit_only),
            exc=exc,
        )
        print(f"Portal package upload/audit failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
