#!/usr/bin/env python3
"""Build deterministic canonical Abby voice v2 JSONL configs.

This command is intentionally offline and never reads or writes a remote
bucket.  Rejected rows are copied to ``quarantine.jsonl`` with stable evidence;
the source manifests are opened read-only and are never modified.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "ipfs_datasets_py"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from ipfs_datasets_py.voice.normalize import (  # noqa: E402
    AbbyVoiceDatasetNormalizer,
    NormalizationConfig,
    NormalizationResult,
    canonical_json,
)
from ipfs_datasets_py.voice.schema import validate_bundle  # noqa: E402

DEFAULT_INPUT = REPO_ROOT / "docs" / "pregenerated_text_response_manifest.json"


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _discover_inputs(paths: list[Path]) -> list[Path]:
    discovered: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved.is_dir():
            discovered.update(
                candidate.resolve()
                for candidate in resolved.rglob("*")
                if candidate.is_file()
                and candidate.suffix.casefold() in {".json", ".jsonl"}
            )
        elif resolved.is_file():
            discovered.add(resolved)
        else:
            raise FileNotFoundError(f"input does not exist: {path}")
    return sorted(discovered, key=_display_path)


def _load_input(path: Path) -> Any:
    if path.suffix.casefold() == ".jsonl":
        rows = []
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        return rows
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def normalize_paths(
    paths: list[Path], *, config: NormalizationConfig
) -> NormalizationResult:
    """Load and normalize paths in stable path order."""

    sources = []
    for path in _discover_inputs(paths):
        raw_bytes = path.read_bytes()
        sources.append(
            (
                _load_input(path),
                _display_path(path),
                sha256(raw_bytes).hexdigest(),
                path.parent,
            )
        )
    if not sources:
        raise ValueError("no JSON or JSONL input files were discovered")
    return AbbyVoiceDatasetNormalizer(config).normalize_sources(sources)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    return (
        "\n".join(canonical_json(row) for row in rows) + "\n"
    ).encode("utf-8")


def render_artifacts(result: NormalizationResult) -> dict[str, bytes]:
    """Render every output except the checksummed manifest."""

    artifacts = {
        "responses.jsonl": _jsonl_bytes(
            [row.to_dict() for row in result.responses]
        ),
        "templates.jsonl": _jsonl_bytes(
            [row.to_dict() for row in result.templates]
        ),
        "audio.jsonl": _jsonl_bytes([row.to_dict() for row in result.audio]),
        "provenance.jsonl": _jsonl_bytes(
            [row.to_dict() for row in result.provenance]
        ),
        "quarantine.jsonl": _jsonl_bytes(
            [row.to_dict() for row in result.quarantine]
        ),
        "warnings.jsonl": _jsonl_bytes(
            [row.to_dict() for row in result.warnings]
        ),
        "duplicate-ledger.jsonl": _jsonl_bytes(
            [row.to_dict() for row in result.duplicates]
        ),
        "splits.json": _json_bytes(dict(sorted(result.splits.items()))),
        "quality-report.json": _json_bytes(result.quality_summary()),
    }
    return dict(sorted(artifacts.items()))


def _manifest_for(
    result: NormalizationResult, artifacts: dict[str, bytes]
) -> dict[str, Any]:
    row_counts = {
        "responses.jsonl": len(result.responses),
        "templates.jsonl": len(result.templates),
        "audio.jsonl": len(result.audio),
        "provenance.jsonl": len(result.provenance),
        "quarantine.jsonl": len(result.quarantine),
        "warnings.jsonl": len(result.warnings),
        "duplicate-ledger.jsonl": len(result.duplicates),
    }
    return {
        "schema_version": "abby_voice_dataset_build_v2",
        "normalization_version": result.quality_summary()["normalization_version"],
        "deterministic": True,
        "source_manifest_count": result.source_manifest_count,
        "input_record_count": result.input_record_count,
        "files": [
            {
                "path": name,
                "sha256": sha256(content).hexdigest(),
                "byte_length": len(content),
                **(
                    {"row_count": row_counts[name]}
                    if name in row_counts
                    else {}
                ),
            }
            for name, content in artifacts.items()
        ],
    }


def write_dataset(result: NormalizationResult, output_dir: Path) -> dict[str, Any]:
    """Atomically write one complete deterministic local build."""

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = render_artifacts(result)
    manifest = _manifest_for(result, artifacts)
    artifacts["manifest.json"] = _json_bytes(manifest)
    for name, content in sorted(artifacts.items()):
        target = output_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", dir=target.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o644)
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()
    return manifest


def validate_build(
    result: NormalizationResult, output_dir: Path, manifest: dict[str, Any]
) -> None:
    """Verify schema relationships and all on-disk checksums."""

    validate_bundle(
        responses=result.responses,
        templates=result.templates,
        audio=result.audio,
        provenance=result.provenance,
        require_references=True,
    )
    for item in manifest["files"]:
        path = output_dir / item["path"]
        if not path.is_file():
            raise RuntimeError(f"build output is missing: {path}")
        data = path.read_bytes()
        if len(data) != item["byte_length"]:
            raise RuntimeError(f"byte length mismatch: {path}")
        if sha256(data).hexdigest() != item["sha256"]:
            raise RuntimeError(f"checksum mismatch: {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Input JSON/JSONL manifests or directories.",
    )
    parser.add_argument(
        "--input",
        dest="inputs",
        action="append",
        type=Path,
        default=[],
        help="Additional input manifest (repeatable).",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        type=Path,
        default=[],
        help="Fixture manifest or directory; equivalent to an input.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Local output directory. No remote state is changed.",
    )
    parser.add_argument("--locale", default="en-US")
    parser.add_argument("--license-id", default="NOASSERTION")
    parser.add_argument(
        "--consent-status",
        choices=("granted", "not_required", "unknown", "denied", "withdrawn"),
        default="unknown",
    )
    parser.add_argument(
        "--require-audio",
        action="store_true",
        help="Quarantine response rows whose audio is absent or unverifiable.",
    )
    parser.add_argument(
        "--allow-ungrounded-claims",
        action="store_true",
        help="Disable the factual-claim grounding gate (not recommended).",
    )
    parser.add_argument(
        "--fail-on-quarantine",
        action="store_true",
        help="Exit nonzero after writing evidence if any source row is quarantined.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate canonical relationships and output checksums.",
    )
    parser.add_argument(
        "--check-idempotence",
        action="store_true",
        help="Normalize a second time and require byte-identical rendered output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_paths = [*args.paths, *args.inputs, *args.fixture]
    if not input_paths:
        input_paths = [DEFAULT_INPUT]
    config = NormalizationConfig(
        locale=args.locale,
        license_id=args.license_id,
        consent_status=args.consent_status,
        require_audio=args.require_audio,
        require_grounding_for_claims=not args.allow_ungrounded_claims,
    )
    result = normalize_paths(input_paths, config=config)
    manifest = write_dataset(result, args.output_dir)
    if args.check or args.check_idempotence:
        validate_build(result, args.output_dir, manifest)
    if args.check_idempotence:
        rerun = normalize_paths(input_paths, config=config)
        if render_artifacts(result) != render_artifacts(rerun):
            raise RuntimeError("normalization is not byte-identical on rerun")
        if _manifest_for(result, render_artifacts(result)) != _manifest_for(
            rerun, render_artifacts(rerun)
        ):
            raise RuntimeError("manifest is not byte-identical on rerun")

    summary = {
        "output_dir": str(args.output_dir),
        "manifest_sha256": sha256(
            (args.output_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "quality": result.quality_summary(),
        "check": bool(args.check),
        "check_idempotence": bool(args.check_idempotence),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 2 if args.fail_on_quarantine and result.quarantine else 0


if __name__ == "__main__":
    raise SystemExit(main())
