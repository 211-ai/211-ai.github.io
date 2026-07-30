#!/usr/bin/env python3
"""Build a deterministic, package-only AST coverage baseline.

This runner reads the exact committed ``ipfs_datasets_py`` Git objects.  It
does not import or execute analyzed source and it does not claim contract or
proof authority.  Its purpose is to prove frontend enumeration/termination
before resolver, obligation, solver, and finding stages are allowed to run.
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Iterable, Mapping, Sequence


REPOSITORY_ID: Final[str] = "repository:ipfs_datasets_py"
LOGICAL_ROOT: Final[str] = "ipfs_datasets_py"
RECEIPT_SCHEMA: Final[str] = (
    "ipfs-datasets.software-contracts.ast-baseline-receipt@1"
)
RESULT_SCHEMA: Final[str] = (
    "ipfs-datasets.software-contracts.ast-baseline-result@1"
)
ERROR_SCHEMA: Final[str] = (
    "ipfs-datasets.software-contracts.ast-baseline-error@1"
)
INDEX_SCHEMA: Final[str] = (
    "ipfs-datasets.software-contracts.ast-baseline-index@1"
)
STATUS_COMPLETE: Final[str] = "complete"
STATUS_INCOMPLETE: Final[str] = "INCOMPLETE_SCAN"
DEFAULT_SHARD_SIZE: Final[int] = 250


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _install_import_path(repo_root: Path) -> None:
    package_root = str(repo_root / "ipfs_datasets_py")
    if package_root not in sys.path:
        sys.path.insert(0, package_root)


@dataclass(frozen=True)
class ScanDocuments:
    repository_root: dict[str, Any]
    coverage: dict[str, Any]
    result_index: dict[str, Any]
    receipt: dict[str, Any]


def _git_text(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _superproject_gitlink(repo_root: Path) -> str:
    line = _git_text(repo_root, "ls-tree", "HEAD", LOGICAL_ROOT)
    fields = line.split()
    if len(fields) < 3 or fields[0] != "160000" or fields[1] != "commit":
        raise RuntimeError("ipfs_datasets_py is not a pinned superproject gitlink")
    return fields[2]


def _pinned_package_snapshot(repo_root: Path, *, shard_size: int) -> Any:
    """Inventory one immutable package commit and reject checkout races."""

    from ipfs_datasets_py.logic.software_contracts.repository import (
        RepositorySnapshot,
        STATUS_INCOMPLETE_SCAN,
        build_tracked_blobs_for_root,
        checkout_identity,
    )

    package_checkout = repo_root / LOGICAL_ROOT
    superproject_head_before = _git_text(repo_root, "rev-parse", "HEAD")
    gitlink_before = _superproject_gitlink(repo_root)
    identity = checkout_identity(
        package_checkout,
        label=LOGICAL_ROOT,
        relative_path=LOGICAL_ROOT,
    )
    if identity is None:
        raise RuntimeError("ipfs_datasets_py checkout identity is unavailable")
    pinned_commit = str(identity["commit"])
    if pinned_commit != gitlink_before:
        raise RuntimeError(
            "ipfs_datasets_py checkout does not match the superproject gitlink"
        )

    blobs, gitlinks, blockers = build_tracked_blobs_for_root(
        package_checkout,
        logical_root=LOGICAL_ROOT,
        treeish=pinned_commit,
        hash_content=True,
    )
    disposition_counts: collections.Counter[str] = collections.Counter(
        blob.parser_disposition for blob in blobs
    )
    identity = dict(identity)
    identity.update(
        {
            "blob_count": len(blobs),
            "object_count": len(blobs),
            "gitlink_count": len(gitlinks),
            "disposition_counts": dict(sorted(disposition_counts.items())),
        }
    )
    mirror_cycles = [
        gitlink.to_dict()
        for gitlink in gitlinks
        if gitlink.disposition == "mirror_cycle_recorded_without_rescan"
    ]
    snapshot = RepositorySnapshot(
        logical_roots=[identity],
        blobs=blobs,
        gitlinks=gitlinks,
        mirror_cycles=mirror_cycles,
        blockers=list(blockers),
        shard_size=shard_size,
    )
    if blockers:
        snapshot.status = STATUS_INCOMPLETE_SCAN
    if bool(identity.get("dirty")):
        snapshot.status = STATUS_INCOMPLETE_SCAN
        snapshot.blockers.append(
            "dirty selected root yields INCOMPLETE_SCAN: ipfs_datasets_py"
        )

    superproject_head_after = _git_text(repo_root, "rev-parse", "HEAD")
    gitlink_after = _superproject_gitlink(repo_root)
    package_head_after = _git_text(package_checkout, "rev-parse", "HEAD")
    if (
        superproject_head_before != superproject_head_after
        or gitlink_before != gitlink_after
        or pinned_commit != package_head_after
    ):
        snapshot.status = STATUS_INCOMPLETE_SCAN
        snapshot.blockers.append(
            "repository identity changed during immutable snapshot construction"
        )
    return snapshot


def _count_codes(records: Iterable[Any]) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter(
        str(record.code) for record in records
    )
    return dict(sorted(counts.items()))


def _bounded_error_message(error: BaseException, repo_root: Path) -> str:
    message = str(error).strip() or type(error).__name__
    message = message.replace(str(repo_root), "<repo>")
    return message[:2_048]


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    from ipfs_datasets_py.logic.software_contracts.content import (
        canonical_dag_json_bytes,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(canonical_dag_json_bytes(dict(document)) + b"\n")
    temporary.replace(path)


def _leaf_counts(leaves: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter(
        str(leaf["disposition"]) for leaf in leaves
    )
    return {
        "parsed_count": counts["parsed"],
        "explicit_unsupported_count": counts["explicit_unsupported"],
        "frontend_exception_count": counts["frontend_exception"],
        "resource_exhausted_count": counts["resource_exhausted"],
        "source_unavailable_count": counts["source_unavailable"],
    }


def _build_shards(
    leaves: Sequence[Mapping[str, Any]],
    leaf_cids: Sequence[str],
    *,
    shard_size: int,
) -> list[dict[str, Any]]:
    from ipfs_datasets_py.logic.software_contracts.content import (
        cid_for_structured,
    )

    shards: list[dict[str, Any]] = []
    for offset in range(0, len(leaves), shard_size):
        chunk = leaves[offset : offset + shard_size]
        chunk_cids = leaf_cids[offset : offset + shard_size]
        counts = _leaf_counts(chunk)
        shards.append(
            {
                "index": len(shards),
                "count": len(chunk),
                "first_path": str(chunk[0]["path"]),
                "last_path": str(chunk[-1]["path"]),
                **counts,
                "shard_cid": cid_for_structured(list(chunk_cids)),
            }
        )
    return shards


def build_documents(
    repo_root: Path,
    *,
    shard_size: int = DEFAULT_SHARD_SIZE,
) -> ScanDocuments:
    _install_import_path(repo_root)

    from ipfs_datasets_py.logic.software_contracts.content import (
        cid_for_bytes,
        cid_for_structured,
    )
    from ipfs_datasets_py.logic.software_contracts.coverage import (
        build_coverage_receipt,
        validate_coverage_receipt,
    )
    from ipfs_datasets_py.logic.software_contracts.python_frontend import (
        PythonASTExtractor,
    )
    from ipfs_datasets_py.logic.software_contracts.repository import (
        batch_blob_bytes,
        validate_repository_root_manifest,
    )

    if shard_size < 1:
        raise ValueError("shard_size must be at least one")

    runner_source = Path(__file__).read_bytes()
    snapshot = _pinned_package_snapshot(repo_root, shard_size=shard_size)
    repository_root = snapshot.to_repository_root_manifest()
    repository_errors = validate_repository_root_manifest(repository_root)
    coverage_record = build_coverage_receipt(
        snapshot,
        repository_root=repository_root,
    )
    coverage_errors = validate_coverage_receipt(
        coverage_record,
        repository_root=repository_root,
    )
    coverage = coverage_record.to_dict()

    identities = [
        root
        for root in snapshot.logical_roots
        if root.get("label") == LOGICAL_ROOT
    ]
    if len(identities) != 1:
        raise RuntimeError("package snapshot has no unique ipfs_datasets_py root")
    identity = identities[0]
    commit = str(identity["commit"])
    tree = str(identity["tree"])
    repository_root_cid = str(repository_root["root_cid"])

    eligible = [
        blob
        for blob in snapshot.sorted_blobs()
        if blob.language == "python"
        and blob.parser_disposition == "parseable"
    ]
    package_checkout = repo_root / LOGICAL_ROOT
    source_by_oid = batch_blob_bytes(
        package_checkout,
        [blob.git_oid for blob in eligible],
    )
    extractor = PythonASTExtractor()

    fact_counts: collections.Counter[str] = collections.Counter()
    severity_counts: collections.Counter[str] = collections.Counter()
    diagnostic_counts: collections.Counter[str] = collections.Counter()
    unsupported_counts: collections.Counter[str] = collections.Counter()
    errors_by_fingerprint: dict[str, dict[str, Any]] = {}
    error_objects: list[dict[str, Any]] = []
    leaves: list[dict[str, Any]] = []
    ast_cids: list[str] = []

    for blob in eligible:
        raw_source = source_by_oid.get(blob.git_oid)
        fact = {
            "modules": 0,
            "scopes": 0,
            "symbols": 0,
            "imports": 0,
            "references": 0,
            "calls": 0,
            "effects": 0,
            "diagnostics": 0,
            "unsupported": 0,
        }
        disposition = "source_unavailable"
        ast_cid: str | None = None
        diagnostic_codes: list[str] = []
        unsupported_codes: list[str] = []
        error_cid: str | None = None

        if raw_source is not None:
            try:
                record = extractor.extract(
                    raw_source,
                    path=blob.path,
                    repository_id=REPOSITORY_ID,
                    revision=commit,
                    repository_tree_cid=repository_root_cid,
                )
                ast_cid = record.cid
                ast_cids.append(ast_cid)
                fact = {
                    "modules": 1,
                    "scopes": len(record.scopes),
                    "symbols": len(record.symbols),
                    "imports": len(record.imports),
                    "references": len(record.references),
                    "calls": len(record.calls),
                    "effects": len(record.effects),
                    "diagnostics": len(record.diagnostics),
                    "unsupported": len(record.unsupported),
                }
                diagnostic_codes = sorted(
                    {str(item.code) for item in record.diagnostics}
                )
                unsupported_codes = sorted(
                    {str(item.code) for item in record.unsupported}
                )
                diagnostic_counts.update(
                    str(item.code) for item in record.diagnostics
                )
                unsupported_counts.update(
                    str(item.code) for item in record.unsupported
                )
                severity_counts.update(
                    str(item.severity) for item in record.diagnostics
                )
                if "python.resource_limit" in unsupported_codes:
                    disposition = "resource_exhausted"
                elif unsupported_codes:
                    disposition = "explicit_unsupported"
                else:
                    disposition = "parsed"
            except Exception as error:  # fail-closed corpus boundary
                message = _bounded_error_message(error, repo_root)
                error_identity = {
                    "schema": ERROR_SCHEMA,
                    "error_code": "python.frontend_exception",
                    "exception_type": type(error).__name__,
                    "message": message,
                    "message_cid": cid_for_structured({"message": message}),
                }
                error_cid = cid_for_structured(error_identity)
                error_object = dict(error_identity)
                error_object["error_cid"] = error_cid
                error_objects.append(error_object)
                fingerprint = cid_for_structured(
                    {
                        "error_code": error_identity["error_code"],
                        "exception_type": error_identity["exception_type"],
                        "message_cid": error_identity["message_cid"],
                    }
                )
                aggregate = errors_by_fingerprint.setdefault(
                    fingerprint,
                    {
                        "fingerprint": fingerprint,
                        "error_code": error_identity["error_code"],
                        "exception_type": error_identity["exception_type"],
                        "message_cid": error_identity["message_cid"],
                        "count": 0,
                    },
                )
                aggregate["count"] += 1
                disposition = "frontend_exception"

        fact_counts.update(fact)
        leaf = {
            "schema": RESULT_SCHEMA,
            "path": blob.path,
            "mode": blob.mode,
            "git_oid": blob.git_oid,
            "size_bytes": blob.size_bytes,
            "source_cid": blob.cid,
            "frontend_capability_cid": extractor.capability.cid,
            "disposition": disposition,
            "ast_cid": ast_cid,
            "fact_counts": fact,
            "diagnostic_codes": diagnostic_codes,
            "unsupported_codes": unsupported_codes,
            "error_cid": error_cid,
        }
        leaves.append(leaf)
        if len(leaves) % 500 == 0:
            print(
                f"AST baseline: processed {len(leaves)}/{len(eligible)} blobs",
                file=sys.stderr,
                flush=True,
            )

    leaf_cids = [cid_for_structured(leaf) for leaf in leaves]
    shards = _build_shards(leaves, leaf_cids, shard_size=shard_size)
    disposition_counts = _leaf_counts(leaves)
    attempted_count = (
        disposition_counts["parsed_count"]
        + disposition_counts["explicit_unsupported_count"]
        + disposition_counts["frontend_exception_count"]
        + disposition_counts["resource_exhausted_count"]
    )
    source_unavailable_count = disposition_counts["source_unavailable_count"]
    unattempted_count = len(eligible) - attempted_count - source_unavailable_count
    terminal_count = len(eligible) - unattempted_count
    enumeration_complete = terminal_count == len(eligible)
    identity_changed_during_analysis = (
        _superproject_gitlink(repo_root) != commit
        or _git_text(package_checkout, "rev-parse", "HEAD") != commit
    )
    runner_changed_during_analysis = Path(__file__).read_bytes() != runner_source
    analysis_complete = (
        enumeration_complete
        and disposition_counts["frontend_exception_count"] == 0
        and disposition_counts["resource_exhausted_count"] == 0
        and source_unavailable_count == 0
        and not repository_errors
        and not coverage_errors
        and coverage_record.complete
        and not identity_changed_during_analysis
        and not runner_changed_during_analysis
    )

    blockers: set[str] = set()
    if repository_errors or not coverage_record.complete:
        blockers.add("repository_coverage_incomplete")
    if coverage_errors:
        blockers.add("coverage_receipt_invalid")
    if disposition_counts["frontend_exception_count"]:
        blockers.add("frontend_exception")
    if disposition_counts["resource_exhausted_count"]:
        blockers.add("frontend_resource_exhausted")
    if source_unavailable_count:
        blockers.add("source_unavailable")
    if unattempted_count:
        blockers.add("eligible_source_unattempted")
    if identity_changed_during_analysis:
        blockers.add("repository_identity_changed_during_analysis")
    if runner_changed_during_analysis:
        blockers.add("analyzer_source_changed_during_analysis")

    source_set = [
        {
            "path": blob.path,
            "mode": blob.mode,
            "git_oid": blob.git_oid,
            "size_bytes": blob.size_bytes,
            "source_cid": blob.cid,
        }
        for blob in eligible
    ]
    configuration_identity = {
        "shard_size": shard_size,
        "max_source_bytes": extractor.max_source_bytes,
        "max_ast_nodes": extractor.max_ast_nodes,
        "ordering": "utf8_posix_path_then_git_oid",
        "network": "deny",
    }
    result_index_identity = {
        "schema": INDEX_SCHEMA,
        "repository_root_cid": repository_root_cid,
        "frontend_capability_cid": extractor.capability.cid,
        "result_leaves": leaves,
        "error_objects": sorted(
            error_objects,
            key=lambda item: str(item["error_cid"]),
        ),
    }
    result_index = dict(result_index_identity)
    result_index["index_cid"] = cid_for_structured(result_index_identity)

    receipt_identity = {
        "schema": RECEIPT_SCHEMA,
        "authority": "STATIC_AST_BASELINE_ONLY",
        "status": STATUS_COMPLETE if analysis_complete else STATUS_INCOMPLETE,
        "repository": {
            "repository_id": REPOSITORY_ID,
            "commit": commit,
            "tree": tree,
            "repository_root_cid": repository_root_cid,
            "source_selection": "git_objects_at_commit",
            "eligible_source_set_cid": cid_for_structured(source_set),
        },
        "frontend": {
            "name": extractor.capability.frontend_name,
            "version": extractor.capability.frontend_version,
            "ast_schema": extractor.capability.ast_schema.identifier,
            "capability_cid": extractor.capability.cid,
            "toolchain_cid": extractor.capability.toolchain_cid,
            "runner_source_cid": cid_for_bytes(runner_source),
        },
        "configuration": {
            **configuration_identity,
            "configuration_cid": cid_for_structured(configuration_identity),
        },
        "coverage": {
            "tracked_blob_count": len(snapshot.blobs),
            "eligible_blob_count": len(eligible),
            "attempted_count": attempted_count,
            "terminal_count": terminal_count,
            "unattempted_count": unattempted_count,
            **disposition_counts,
            "enumeration_complete": enumeration_complete,
            "analysis_complete": analysis_complete,
        },
        "facts": {
            **dict(sorted(fact_counts.items())),
            "diagnostics_by_severity": dict(sorted(severity_counts.items())),
        },
        "failures": {
            "diagnostics_by_code": dict(sorted(diagnostic_counts.items())),
            "unsupported_by_code": dict(sorted(unsupported_counts.items())),
            "exceptions_by_fingerprint": sorted(
                errors_by_fingerprint.values(),
                key=lambda item: str(item["fingerprint"]),
            ),
            "sample_failure_leaf_cids": [
                cid
                for cid, leaf in zip(leaf_cids, leaves)
                if leaf["disposition"]
                in {
                    "frontend_exception",
                    "resource_exhausted",
                    "source_unavailable",
                }
            ][:32],
        },
        "artifacts": {
            "result_leaf_set_cid": cid_for_structured(leaf_cids),
            "ast_record_set_cid": cid_for_structured(ast_cids),
            "exception_set_cid": cid_for_structured(
                sorted(
                    str(item["error_cid"]) for item in error_objects
                )
            ),
            "result_index_cid": result_index["index_cid"],
            "shards": shards,
        },
        "blockers": sorted(blockers),
    }
    receipt = dict(receipt_identity)
    receipt["receipt_cid"] = cid_for_structured(receipt_identity)
    return ScanDocuments(
        repository_root=repository_root,
        coverage=coverage,
        result_index=result_index,
        receipt=receipt,
    )


def _output_documents(
    documents: ScanDocuments,
    output_dir: Path,
) -> dict[Path, Mapping[str, Any]]:
    return {
        output_dir / "repository-root.json": documents.repository_root,
        output_dir / "coverage.json": documents.coverage,
        output_dir / "ast-result-index.json": documents.result_index,
        output_dir / "ast-baseline.json": documents.receipt,
    }


def _canonical_bytes(document: Mapping[str, Any]) -> bytes:
    from ipfs_datasets_py.logic.software_contracts.content import (
        canonical_dag_json_bytes,
    )

    return canonical_dag_json_bytes(dict(document)) + b"\n"


def _check_outputs(
    outputs: Mapping[Path, Mapping[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for path, document in outputs.items():
        if not path.is_file():
            errors.append(f"missing output: {path}")
            continue
        if path.read_bytes() != _canonical_bytes(document):
            errors.append(f"stale or noncanonical output: {path}")
    receipt = next(
        document
        for path, document in outputs.items()
        if path.name == "ast-baseline.json"
    )
    if receipt.get("status") != STATUS_COMPLETE:
        errors.append(
            "AST baseline is incomplete: "
            + ",".join(str(item) for item in receipt.get("blockers", []))
        )
    return errors


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root(),
        help="211-AI integration worktree containing ipfs_datasets_py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "data/datasets_contract_analysis/scans/"
            "ipfs_datasets_py/baseline"
        ),
    )
    parser.add_argument(
        "--shard-size",
        type=int,
        default=DEFAULT_SHARD_SIZE,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Require checked-in outputs to be current and complete",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    documents = build_documents(repo_root, shard_size=args.shard_size)
    outputs = _output_documents(documents, output_dir)
    if args.check:
        errors = _check_outputs(outputs)
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    for path, document in outputs.items():
        _write_json(path, document)
    print(
        json.dumps(
            {
                "authority": documents.receipt["authority"],
                "status": documents.receipt["status"],
                "receipt_cid": documents.receipt["receipt_cid"],
                "repository": documents.receipt["repository"],
                "coverage": documents.receipt["coverage"],
                "blockers": documents.receipt["blockers"],
                "output_dir": output_dir.relative_to(repo_root).as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
