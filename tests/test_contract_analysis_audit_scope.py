from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "contract_analysis"
    / "audit_scope.py"
)


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("contract_analysis_audit_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit_scope = _load_module()


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _new_repository(path: Path, filename: str) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "audit-scope@example.invalid")
    _git(path, "config", "user.name", "Audit Scope Test")
    (path / filename).write_text(f"{path.name}\n", encoding="utf-8")
    _git(path, "add", filename)
    _git(path, "commit", "-q", "-m", "initial")
    return path


def _package_repository(path: Path, package_name: str) -> Path:
    repository = _new_repository(path, "package.py")
    nested_path = f"{package_name}/mirror"
    _git(
        repository,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{'1' * 40},{nested_path}",
    )
    _git(repository, "commit", "-q", "-m", "record nested mirror gitlink")
    return repository


@pytest.fixture()
def frozen_scope(tmp_path: Path) -> tuple[Path, Path, dict]:
    packages = {
        name: _package_repository(tmp_path / f"{name}-origin", name)
        for name in audit_scope.SELECTED_PACKAGE_ROOTS
    }
    swissknife = _new_repository(tmp_path / "swissknife", "swiss.ts")
    hallucinate = _new_repository(tmp_path / "hallucinate", "runtime.py")
    home_datasets = _new_repository(tmp_path / "home-datasets", "home.py")
    root = _new_repository(tmp_path / "superproject", "README.md")

    for name, origin in packages.items():
        _git(
            root,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "-q",
            str(origin),
            name,
        )
    _git(root, "commit", "-q", "-am", "pin selected package roots")

    frozen = audit_scope.collect_source_roots(
        root,
        swissknife_path=swissknife,
        hallucinate_path=hallucinate,
        home_datasets_path=home_datasets,
    )
    assert frozen["freeze_ok"] is True
    assert frozen["mirror_cycles"]

    manifest = (
        root
        / "data"
        / "datasets_contract_analysis"
        / "audit"
        / "source-roots.json"
    )
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(frozen), encoding="utf-8")

    # Advance ambient HEAD after the freeze while retaining all historical
    # objects. Snapshot integrity should remain valid; freshness should not.
    (root / "post-freeze.txt").write_text("new ambient revision\n", encoding="utf-8")
    _git(root, "add", "post-freeze.txt")
    _git(root, "commit", "-q", "-m", "advance ambient head")
    return root, manifest, frozen


def test_snapshot_check_uses_pinned_objects_after_ambient_head_moves(
    frozen_scope: tuple[Path, Path, dict],
) -> None:
    root, manifest, frozen = frozen_scope
    errors: list[str] = []
    warnings: list[str] = []

    checked = audit_scope._check_source_roots(
        root,
        manifest,
        errors,
        warnings,
    )

    assert checked == frozen
    assert errors == []
    assert not any("drift" in message for message in errors)


def test_current_comparison_reports_the_ambient_move(
    frozen_scope: tuple[Path, Path, dict],
) -> None:
    root, _manifest, frozen = frozen_scope
    candidates = {
        candidate["role"]: candidate
        for candidate in frozen["authority_candidates"]
    }

    divergences = audit_scope._collect_current_divergences(
        root,
        frozen,
        swissknife_path=Path(frozen["swissknife"]["configured_path"]),
        hallucinate_path=Path(frozen["hallucinate_datasets"]["configured_path"]),
        home_datasets_path=Path(candidates["standalone_home_checkout"]["path"]),
    )

    assert any(item.startswith("superproject.commit:") for item in divergences)
    assert any(item.startswith("superproject.tree:") for item in divergences)


def test_snapshot_check_fails_closed_when_pinned_commit_is_missing(
    frozen_scope: tuple[Path, Path, dict],
) -> None:
    root, manifest, frozen = frozen_scope
    corrupted = copy.deepcopy(frozen)
    corrupted["superproject"]["commit"] = "f" * 40
    manifest.write_text(json.dumps(corrupted), encoding="utf-8")
    errors: list[str] = []

    audit_scope._check_source_roots(root, manifest, errors, [])

    assert any(
        "superproject pinned commit" in message and "unavailable" in message
        for message in errors
    )


def test_snapshot_check_fails_closed_on_commit_tree_mismatch(
    frozen_scope: tuple[Path, Path, dict],
) -> None:
    root, manifest, frozen = frozen_scope
    corrupted = copy.deepcopy(frozen)
    corrupted["superproject"]["tree"] = _git(root, "rev-parse", "HEAD^{tree}")
    manifest.write_text(json.dumps(corrupted), encoding="utf-8")
    errors: list[str] = []

    audit_scope._check_source_roots(root, manifest, errors, [])

    assert any("superproject pinned commit/tree mismatch" in message for message in errors)
