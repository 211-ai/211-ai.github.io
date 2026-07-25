"""Offline contract tests for the generated World aid board verifier."""

from __future__ import annotations

import ast
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts.verify_world_aid_generated_board import (
    BLOCKED_REVIEW_CONTRACT,
    GATE0B_REOPENED_CONTRACT,
    BoardVerificationError,
    main,
    verify_generated_board,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = REPOSITORY_ROOT / "scripts/verify_world_aid_generated_board.py"


def _goal(
    goal_id: str,
    *,
    status: str,
    parents: str,
    output: str,
    validation: str,
) -> str:
    return f"""## {goal_id} Example goal

- Status: {status}
- Fib priority: {int(goal_id.removeprefix("WORLDCOIN-G")) + 1}
- Track: fixture
- Parents: {parents}
- Outputs: {output}
- Validation: {validation}
- Bundle: world-aid/{goal_id.lower()}
- Acceptance criteria: Deterministic fixture acceptance.
- Refinement: Generated TODO acceptance must preserve deterministic fixture acceptance.
"""


def _task(
    task_id: str,
    *,
    goal_id: str,
    cid: str,
    bundle: str,
    shard_path: str,
    parents: str,
    output: str,
    validation: str,
    status: str = "todo",
) -> str:
    review_only = status == "blocked"
    return f"""## {task_id} Implement {goal_id}

- Status: {status}
- Completion: manual
- Is schedulable: {str(not review_only).lower()}
- Review only: {str(review_only).lower()}
- Outputs: generated/discovery, objective.md, {output}
- Validation: {validation}
- Bundle: {bundle}
- Bundle shard: {shard_path}
- Graph parents: {parents}
- Goal id: {goal_id}
- Canonical task CID: {cid}
- Acceptance: Deterministic fixture acceptance.
"""


def _write_fixture(
    tmp_path: Path,
    *,
    board_contract: str = BLOCKED_REVIEW_CONTRACT,
) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repo"
    generated_root = repo_root / "data/worldcoin_human_aid/agent_supervisor/regenerations/test-review"
    bundle_dir = generated_root / "objective_bundles"
    bundle_dir.mkdir(parents=True)
    objective_path = repo_root / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
    objective_path.parent.mkdir(parents=True)
    generated_relative = generated_root.relative_to(repo_root).as_posix()

    goal_specs: list[dict[str, str]] = []
    for number in range(1, 43):
        goal_id = f"WORLDCOIN-G{number:03d}"
        if number in {35, 36}:
            status = "blocked"
        elif number in {38, 39, 40}:
            status = (
                "reopened"
                if board_contract == GATE0B_REOPENED_CONTRACT
                else "blocked"
            )
        else:
            status = "active"
        if number == 1:
            parents = ""
        elif number == 36:
            parents = "WORLDCOIN-G035"
        elif number == 37:
            parents = "WORLDCOIN-G034"
        else:
            parents = f"WORLDCOIN-G{number - 1:03d}"
        goal_specs.append(
            {
                "goal_id": goal_id,
                "status": status,
                "parents": parents,
                "output": f"out/g{number:03d}.py",
                "validation": f"python -m pytest -q tests/g{number:03d}.py",
            }
        )
    objective_path.write_text(
        "# Objective heap\n\n" + "\n".join(_goal(**spec) for spec in goal_specs),
        encoding="utf-8",
    )

    task_blocks: list[str] = []
    task_by_goal: dict[str, dict[str, object]] = {}
    bundles: dict[str, dict[str, object]] = {}
    for task_number, spec in enumerate(
        (
            item
            for item in goal_specs
            if item["status"] in {"active", "reopened"}
            or item["goal_id"] in {
                "WORLDCOIN-G038",
                "WORLDCOIN-G039",
                "WORLDCOIN-G040",
            }
        ),
        start=1,
    ):
        goal_id = spec["goal_id"]
        task_id = f"WORLDCOIN-AUTO-{task_number:03d}"
        cid = f"cid-{goal_id.lower()}"
        bundle = f"world-aid/{goal_id.lower()}"
        shard_relative = f"{generated_relative}/objective_bundles/{goal_id.lower()}.todo.md"
        task_block = _task(
            task_id,
            goal_id=goal_id,
            cid=cid,
            bundle=bundle,
            shard_path=shard_relative,
            parents=spec["parents"] or "none",
            output=spec["output"],
            validation=spec["validation"],
            status="blocked" if spec["status"] == "blocked" else "todo",
        )
        task_blocks.append(task_block)
        task_by_goal[goal_id] = {
            "task_id": task_id,
            "cid": cid,
            "bundle": bundle,
            "shard": shard_relative,
            "body": task_block,
            "status": "blocked" if spec["status"] == "blocked" else "todo",
            "is_schedulable": spec["status"] != "blocked",
            "review_only": spec["status"] == "blocked",
        }
        bundles[bundle] = {
            "bundle_key": bundle,
            "shard_path": shard_relative,
            "is_schedulable": spec["status"] != "blocked",
            "review_only": spec["status"] == "blocked",
            "tasks": [
                {
                    "task_id": task_id,
                    "canonical_task_cid": cid,
                    "task_cid": cid,
                    "goal_id": goal_id,
                    "status": "blocked" if spec["status"] == "blocked" else "todo",
                    "is_schedulable": spec["status"] != "blocked",
                    "review_only": spec["status"] == "blocked",
                    "parent_goal_ids": [item.strip() for item in spec["parents"].split(",") if item.strip()],
                    "outputs": [spec["output"]],
                    "acceptance_criteria": ["Deterministic fixture acceptance."],
                }
            ],
        }

    todo_path = generated_root / "WORLDCOIN_HUMAN_AID_TODO.md"
    todo_path.write_text(
        "# Objective Todo\n\n" + "\n".join(task_blocks),
        encoding="utf-8",
    )
    for goal_id, task in task_by_goal.items():
        shard_path = repo_root / task["shard"]
        shard_path.write_text(
            f"# Objective Bundle: {task['bundle']}\n\n"
            f"Source todo: {generated_relative}/WORLDCOIN_HUMAN_AID_TODO.md\n\n" + task["body"],
            encoding="utf-8",
        )

    nodes = {
        task["cid"]: {
            "task_id": task["task_id"],
            "goal_id": goal_id,
            "status": task["status"],
            "metadata": {
                "is_schedulable": task["is_schedulable"],
                "review_only": task["review_only"],
            },
        }
        for goal_id, task in task_by_goal.items()
    }
    edges = []
    for spec in goal_specs:
        child = task_by_goal.get(spec["goal_id"])
        if child is None:
            continue
        for parent_goal_id in (item.strip() for item in spec["parents"].split(",") if item.strip()):
            parent = task_by_goal.get(parent_goal_id)
            if parent is not None:
                edges.append(
                    {
                        "source_task_cid": parent["cid"],
                        "target_task_cid": child["cid"],
                    }
                )
    incoming = {cid: 0 for cid in nodes}
    for edge in edges:
        incoming[edge["target_task_cid"]] += 1
    dag = {
        "nodes": nodes,
        "edges": edges,
        "invalid_task_cids": [],
        "claimable_task_cids": sorted(
            cid
            for cid, count in incoming.items()
            if count == 0 and nodes[cid]["status"] != "blocked"
        ),
    }
    index = {
        "source_todo": f"{generated_relative}/WORLDCOIN_HUMAN_AID_TODO.md",
        "bundles": bundles,
        "query_store": {
            "artifact_kind": "bundle_planning_index",
            "catalog_table": "artifact_catalog",
            "duckdb_path": "index.duckdb",
            "schema": "ipfs_accelerate_py.agent_supervisor.queryable_artifact@2",
        },
        "dependency_dag": dag,
        "task_dependency_graph": dag,
    }
    (bundle_dir / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "index.duckdb").write_bytes(b"fixture-duckdb")

    graph_edges = [
        {"from": parent.strip(), "to": spec["goal_id"], "kind": "refines"}
        for spec in goal_specs
        for parent in spec["parents"].split(",")
        if parent.strip()
    ]
    graph_payload = {
        "schema": "ipfs_accelerate_py.agent_supervisor.objective_graph",
        "objective_path": objective_path.relative_to(repo_root).as_posix(),
        "goal_count": len(goal_specs),
        "active_goal_count": sum(
            spec["status"] in {"active", "reopened"}
            for spec in goal_specs
        ),
        "completed_goal_count": 0,
        "goals": [
            {
                "goal_id": spec["goal_id"],
                "title": "Example goal",
                "status": spec["status"],
                "parents": [item.strip() for item in spec["parents"].split(",") if item.strip()],
                "bundle": f"world-aid/{spec['goal_id'].lower()}",
                "track": "fixture",
                "fib_priority": int(spec["goal_id"].removeprefix("WORLDCOIN-G")) + 1,
            }
            for spec in goal_specs
        ],
        "graph": {
            "nodes": [spec["goal_id"] for spec in goal_specs],
            "edges": graph_edges,
            "roots": ["WORLDCOIN-G001"],
            "schedulable_goal_ids": sorted(
                spec["goal_id"]
                for spec in goal_specs
                if spec["status"] in {"active", "reopened"}
            ),
            "terminal_goal_ids": [
                spec["goal_id"]
                for spec in goal_specs
                if spec["status"] == "blocked"
            ],
        },
        "heap_schedule": [
            {"goal_id": spec["goal_id"]}
            for spec in goal_specs
            if spec["status"] in {"active", "reopened"}
        ],
    }
    (generated_root / "objective_graph.json").write_text(
        json.dumps(graph_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    records = []
    for spec in goal_specs:
        task = task_by_goal.get(spec["goal_id"])
        if task is None:
            continue
        records.append(
            {
                "task_id": task["task_id"],
                "task_cid": task["cid"],
                "goal_id": spec["goal_id"],
                "title": f"Implement {spec['goal_id']}",
                "status": task["status"],
                "acceptance": "Deterministic fixture acceptance.",
                "bundle_key": task["bundle"],
                "bundle_shard": task["shard"],
                "graph_parents": [item.strip() for item in spec["parents"].split(",") if item.strip()],
                "outputs": [
                    "generated/discovery",
                    "objective.md",
                    spec["output"],
                ],
                "validation": [spec["validation"]],
            }
        )
    vector_payload = {
        "schema": "ipfs_accelerate_py.agent_supervisor.todo_vector_index",
        "todo_path": f"{generated_relative}/WORLDCOIN_HUMAN_AID_TODO.md",
        "objective_path": objective_path.relative_to(repo_root).as_posix(),
        "bundle_index_path": f"{generated_relative}/objective_bundles/index.json",
        "task_count": len(records),
        "active_task_count": sum(record["status"] != "blocked" for record in records),
        "records": records,
        "query_artifact": {
            "path": f"{generated_relative}/objective_bundles/index.json",
            "duckdb_path": f"{generated_relative}/objective_bundles/index.duckdb",
        },
    }
    (bundle_dir / "todo_vector_index.json").write_text(
        json.dumps(vector_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return repo_root, objective_path, generated_root


def _verify(
    paths: tuple[Path, Path, Path],
    *,
    board_contract: str = BLOCKED_REVIEW_CONTRACT,
):
    repo_root, objective_path, generated_root = paths
    return verify_generated_board(
        repo_root=repo_root,
        objective_path=objective_path,
        generated_root=generated_root,
        board_contract=board_contract,
    )


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _rewrite_index(
    generated_root: Path,
    mutate: Callable[[dict[str, object]], None],
) -> None:
    path = generated_root / "objective_bundles" / "index.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_valid_board_passes_and_cli_writes_no_generated_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _write_fixture(tmp_path)
    repo_root, objective_path, generated_root = paths
    before = {
        path.relative_to(generated_root).as_posix(): path.read_bytes()
        for path in generated_root.rglob("*")
        if path.is_file()
    }

    summary = _verify(paths)
    exit_code = main(
        [
            "--repo-root",
            str(repo_root),
            "--objective-path",
            str(objective_path.relative_to(repo_root)),
            "--generated-root",
            str(generated_root.relative_to(repo_root)),
        ]
    )

    assert summary.to_dict() == {
        "bundle_count": 40,
        "dag_count": 2,
        "schedulable_goal_count": 37,
        "source_goal_count": 42,
        "status": "passed",
        "task_count": 40,
    }
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "passed"
    after = {
        path.relative_to(generated_root).as_posix(): path.read_bytes()
        for path in generated_root.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_reopened_gate0b_board_requires_explicit_contract_and_exact_status(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _write_fixture(
        tmp_path,
        board_contract=GATE0B_REOPENED_CONTRACT,
    )
    repo_root, objective_path, generated_root = paths

    with pytest.raises(BoardVerificationError, match="blocked-goal set differs"):
        _verify(paths)

    summary = _verify(paths, board_contract=GATE0B_REOPENED_CONTRACT)
    exit_code = main(
        [
            "--repo-root",
            str(repo_root),
            "--objective-path",
            str(objective_path.relative_to(repo_root)),
            "--generated-root",
            str(generated_root.relative_to(repo_root)),
            "--board-contract",
            GATE0B_REOPENED_CONTRACT,
        ]
    )
    assert summary.schedulable_goal_count == 40
    assert summary.task_count == 40
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "passed"

    _replace(
        objective_path,
        "## WORLDCOIN-G038 Example goal\n\n- Status: reopened",
        "## WORLDCOIN-G038 Example goal\n\n- Status: active",
    )
    with pytest.raises(
        BoardVerificationError,
        match=(
            "gate0b-selection-reopened-v1 requires WORLDCOIN-G038 "
            "status to be exactly 'reopened'"
        ),
    ):
        _verify(paths, board_contract=GATE0B_REOPENED_CONTRACT)


def test_reopened_gate0b_board_rejects_review_only_flags(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(
        tmp_path,
        board_contract=GATE0B_REOPENED_CONTRACT,
    )
    _replace(
        paths[2] / "WORLDCOIN_HUMAN_AID_TODO.md",
        (
            "## WORLDCOIN-AUTO-036 Implement WORLDCOIN-G038\n\n"
            "- Status: todo\n"
            "- Completion: manual\n"
            "- Is schedulable: true"
        ),
        (
            "## WORLDCOIN-AUTO-036 Implement WORLDCOIN-G038\n\n"
            "- Status: todo\n"
            "- Completion: manual\n"
            "- Is schedulable: false"
        ),
    )
    with pytest.raises(
        BoardVerificationError,
        match=(
            "reopened scheduling flag 'is_schedulable' must be "
            "literal 'true'"
        ),
    ):
        _verify(paths, board_contract=GATE0B_REOPENED_CONTRACT)


def test_reopened_contract_rejects_current_blocked_review_projection(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths, board_contract=GATE0B_REOPENED_CONTRACT)
    rendered = "\n".join(raised.value.problems)
    assert "blocked-goal set differs" in rendered
    assert (
        "requires WORLDCOIN-G038 status to be exactly 'reopened'; "
        "found 'blocked'"
    ) in rendered


@pytest.mark.parametrize(
    ("layer", "expected"),
    [
        (
            "todo",
            "review-only goal WORLDCOIN-G038 must remain status 'blocked'",
        ),
        (
            "index",
            "bundle index task WORLDCOIN-AUTO-036 for review-only goal "
            "WORLDCOIN-G038 must remain status 'blocked'",
        ),
        (
            "dag",
            "dependency_dag node 'cid-worldcoin-g038' for review-only goal "
            "WORLDCOIN-G038 must remain status 'blocked'",
        ),
    ],
)
def test_review_only_goal_status_must_remain_blocked_in_every_task_projection(
    tmp_path: Path,
    layer: str,
    expected: str,
) -> None:
    paths = _write_fixture(tmp_path)
    if layer == "todo":
        _replace(
            paths[2] / "WORLDCOIN_HUMAN_AID_TODO.md",
            "Status: blocked",
            "Status: todo",
        )
    elif layer == "index":
        def mutate_index(payload: dict[str, object]) -> None:
            bundles = payload["bundles"]
            assert isinstance(bundles, dict)
            bundle = bundles["world-aid/worldcoin-g038"]
            assert isinstance(bundle, dict)
            tasks = bundle["tasks"]
            assert isinstance(tasks, list)
            task = tasks[0]
            assert isinstance(task, dict)
            task["status"] = "todo"

        _rewrite_index(paths[2], mutate_index)
    else:
        def mutate_dag(payload: dict[str, object]) -> None:
            dag = payload["dependency_dag"]
            assert isinstance(dag, dict)
            nodes = dag["nodes"]
            assert isinstance(nodes, dict)
            node = nodes["cid-worldcoin-g038"]
            assert isinstance(node, dict)
            node["status"] = "todo"

        _rewrite_index(paths[2], mutate_dag)

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    assert expected in "\n".join(raised.value.problems)


@pytest.mark.parametrize(
    ("layer", "field", "mutation", "expected"),
    [
        (
            "todo",
            "is_schedulable",
            "wrong",
            "review-only scheduling flag 'is_schedulable' must be literal 'false'",
        ),
        (
            "todo",
            "review_only",
            "missing",
            "is missing review-only scheduling flag 'review_only'",
        ),
        (
            "index_task",
            "is_schedulable",
            "missing",
            "is missing review-only scheduling flag 'is_schedulable'",
        ),
        (
            "index_task",
            "review_only",
            "wrong",
            "review-only scheduling flag 'review_only' must be JSON boolean true",
        ),
        (
            "bundle",
            "is_schedulable",
            "wrong",
            "review-only scheduling flag 'is_schedulable' must be JSON boolean false",
        ),
        (
            "bundle",
            "review_only",
            "missing",
            "is missing review-only scheduling flag 'review_only'",
        ),
        (
            "dag",
            "is_schedulable",
            "missing",
            "is missing review-only scheduling flag 'is_schedulable'",
        ),
        (
            "dag",
            "review_only",
            "wrong",
            "review-only scheduling flag 'review_only' must be JSON boolean true",
        ),
    ],
)
def test_review_only_scheduling_flags_are_required_in_generated_projections(
    tmp_path: Path,
    layer: str,
    field: str,
    mutation: str,
    expected: str,
) -> None:
    paths = _write_fixture(tmp_path)
    if layer == "todo":
        labels = {
            "is_schedulable": "Is schedulable",
            "review_only": "Review only",
        }
        current = "false" if field == "is_schedulable" else "true"
        replacement = (
            ""
            if mutation == "missing"
            else f"- {labels[field]}: {'true' if current == 'false' else 'false'}\n"
        )
        _replace(
            paths[2] / "WORLDCOIN_HUMAN_AID_TODO.md",
            f"- {labels[field]}: {current}\n",
            replacement,
        )
    else:
        def mutate_index(payload: dict[str, object]) -> None:
            bundles = payload["bundles"]
            assert isinstance(bundles, dict)
            bundle = bundles["world-aid/worldcoin-g038"]
            assert isinstance(bundle, dict)
            if layer == "bundle":
                target = bundle
            elif layer == "index_task":
                tasks = bundle["tasks"]
                assert isinstance(tasks, list)
                target = tasks[0]
                assert isinstance(target, dict)
            else:
                dag = payload["dependency_dag"]
                assert isinstance(dag, dict)
                nodes = dag["nodes"]
                assert isinstance(nodes, dict)
                node = nodes["cid-worldcoin-g038"]
                assert isinstance(node, dict)
                target = node["metadata"]
                assert isinstance(target, dict)
            if mutation == "missing":
                target.pop(field)
            else:
                target[field] = not bool(target[field])

        _rewrite_index(paths[2], mutate_index)

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    assert expected in "\n".join(raised.value.problems)


@pytest.mark.parametrize(
    ("old_goal", "new_goal", "expected"),
    [
        (
            "WORLDCOIN-G038",
            "WORLDCOIN-G035",
            "review-only blocked goal WORLDCOIN-G038 must have exactly one "
            "generated task; found 0",
        ),
        (
            "WORLDCOIN-G039",
            "WORLDCOIN-G038",
            "review-only blocked goal WORLDCOIN-G038 must have exactly one "
            "generated task; found 2",
        ),
    ],
)
def test_review_only_goals_must_materialize_exactly_once(
    tmp_path: Path,
    old_goal: str,
    new_goal: str,
    expected: str,
) -> None:
    paths = _write_fixture(tmp_path)
    _replace(
        paths[2] / "WORLDCOIN_HUMAN_AID_TODO.md",
        f"Goal id: {old_goal}",
        f"Goal id: {new_goal}",
    )

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    assert expected in "\n".join(raised.value.problems)


def test_review_only_blocked_task_is_never_dag_claimable(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)

    def mutate(payload: dict[str, object]) -> None:
        dag = payload["dependency_dag"]
        assert isinstance(dag, dict)
        claimable = dag["claimable_task_cids"]
        assert isinstance(claimable, list)
        claimable.append("cid-worldcoin-g038")

    _rewrite_index(paths[2], mutate)

    with pytest.raises(
        BoardVerificationError,
        match="dependency_dag claimable roots differ",
    ):
        _verify(paths)


def test_other_verified_goal_remains_non_materializable(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    _replace(
        paths[1],
        "## WORLDCOIN-G001 Example goal\n\n- Status: active",
        "## WORLDCOIN-G001 Example goal\n\n- Status: verified",
    )

    with pytest.raises(
        BoardVerificationError,
        match=(
            "materializes non-schedulable goal WORLDCOIN-G001 "
            "with status 'verified'"
        ),
    ):
        _verify(paths)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing", "WORLDCOIN-G002 must have exactly one generated task; found 0"),
        ("duplicate_goal", "WORLDCOIN-G001 must have exactly one generated task; found 2"),
        ("blocked", "materializes non-schedulable goal WORLDCOIN-G035"),
    ],
)
def test_rejects_missing_duplicate_and_non_schedulable_goal_tasks(
    tmp_path: Path,
    mutation: str,
    expected: str,
) -> None:
    paths = _write_fixture(tmp_path)
    todo_path = paths[2] / "WORLDCOIN_HUMAN_AID_TODO.md"
    text = todo_path.read_text(encoding="utf-8")
    marker = "\n## WORLDCOIN-AUTO-002 "
    first, second = text.split(marker, 1)
    task_two = "## WORLDCOIN-AUTO-002 " + second
    if mutation == "missing":
        todo_path.write_text(first.rstrip() + "\n", encoding="utf-8")
    elif mutation == "duplicate_goal":
        duplicate = (
            task_two.replace("WORLDCOIN-AUTO-002", "WORLDCOIN-AUTO-099")
            .replace("WORLDCOIN-G002", "WORLDCOIN-G001")
            .replace("cid-two", "cid-extra")
        )
        todo_path.write_text(text.rstrip() + "\n\n" + duplicate, encoding="utf-8")
    else:
        todo_path.write_text(
            text.replace("Goal id: WORLDCOIN-G002", "Goal id: WORLDCOIN-G035", 1),
            encoding="utf-8",
        )

    with pytest.raises(BoardVerificationError, match=expected):
        _verify(paths)


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (
            "Validation: python -m pytest -q tests/g002.py",
            "Validation: python -m pytest -q tests/other.py",
            "validation differs",
        ),
        (
            "Graph parents: WORLDCOIN-G001",
            "Graph parents: none",
            "graph parents differ",
        ),
        (
            "generated/discovery, objective.md, out/g002.py",
            "generated/discovery, objective.md",
            "omits source outputs",
        ),
    ],
)
def test_rejects_source_validation_parent_and_output_drift(
    tmp_path: Path,
    old: str,
    new: str,
    expected: str,
) -> None:
    paths = _write_fixture(tmp_path)
    _replace(paths[2] / "WORLDCOIN_HUMAN_AID_TODO.md", old, new)

    with pytest.raises(BoardVerificationError, match=expected):
        _verify(paths)


def test_rejects_index_dag_and_invalid_cid_drift(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)

    def mutate(payload: dict[str, object]) -> None:
        bundles = payload["bundles"]
        assert isinstance(bundles, dict)
        bundle = bundles["world-aid/worldcoin-g002"]
        assert isinstance(bundle, dict)
        tasks = bundle["tasks"]
        assert isinstance(tasks, list)
        task = tasks[0]
        assert isinstance(task, dict)
        task["canonical_task_cid"] = "cid-index-drift"
        dag = payload["dependency_dag"]
        assert isinstance(dag, dict)
        nodes = dag["nodes"]
        assert isinstance(nodes, dict)
        nodes.pop("cid-worldcoin-g002")
        dag["invalid_task_cids"] = ["cid-rejected"]

    _rewrite_index(paths[2], mutate)

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    rendered = "\n".join(raised.value.problems)
    assert "bundle index task ID/CID set differs" in rendered
    assert "dependency_dag contains invalid task CIDs" in rendered
    assert "dependency_dag task ID/CID set differs" in rendered


def test_rejects_bundle_shard_body_and_task_set_drift(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    shard = paths[2] / "objective_bundles" / "worldcoin-g002.todo.md"
    _replace(shard, "Status: todo", "Status: completed")
    extra = _task(
        "WORLDCOIN-AUTO-099",
        goal_id="WORLDCOIN-G002",
        cid="cid-extra",
        bundle="world-aid/worldcoin-g002",
        shard_path=(
            "data/worldcoin_human_aid/agent_supervisor/regenerations/"
            "test-review/objective_bundles/worldcoin-g002.todo.md"
        ),
        parents="WORLDCOIN-G001",
        output="out/two.py",
        validation="python -m pytest -q tests/two.py",
    )
    shard.write_text(shard.read_text(encoding="utf-8").rstrip() + "\n\n" + extra, encoding="utf-8")

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    rendered = "\n".join(raised.value.problems)
    assert "shard body differs from source TODO task WORLDCOIN-AUTO-002" in rendered
    assert "shard task IDs differ from index" in rendered
    assert "shard contains task absent from TODO: WORLDCOIN-AUTO-099" in rendered


def test_rejects_missing_or_reversed_heap_parent_edge(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)

    def mutate(payload: dict[str, object]) -> None:
        dag = payload["dependency_dag"]
        assert isinstance(dag, dict)
        edges = dag["edges"]
        assert isinstance(edges, list)
        edge = next(
            item
            for item in edges
            if isinstance(item, dict)
            and item.get("source_task_cid") == "cid-worldcoin-g001"
            and item.get("target_task_cid") == "cid-worldcoin-g002"
        )
        edge["source_task_cid"], edge["target_task_cid"] = (
            edge["target_task_cid"],
            edge["source_task_cid"],
        )

    _rewrite_index(paths[2], mutate)

    with pytest.raises(BoardVerificationError, match="parent-to-child edges differ"):
        _verify(paths)


def test_rejects_acceptance_refinement_graph_and_vector_drift(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    repo_root, objective_path, generated_root = paths
    _replace(
        objective_path,
        "Refinement: Generated TODO acceptance must preserve deterministic fixture acceptance.",
        "Refinement: unrelated text",
    )

    graph_path = generated_root / "objective_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["graph"]["edges"] = graph["graph"]["edges"][1:]
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    vector_path = generated_root / "objective_bundles/todo_vector_index.json"
    vector = json.loads(vector_path.read_text(encoding="utf-8"))
    vector["records"][0]["goal_id"] = "WORLDCOIN-G002"
    vector_path.write_text(json.dumps(vector, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(BoardVerificationError) as raised:
        _verify((repo_root, objective_path, generated_root))
    rendered = "\n".join(raised.value.problems)
    assert "refinement does not preserve" in rendered
    assert "objective graph parent-to-child edges differ" in rendered
    assert "TODO vector WORLDCOIN-AUTO-001 goal_id differs" in rendered


def test_rejects_orphan_shards_and_unparsed_shard_prose(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    bundle_dir = paths[2] / "objective_bundles"
    orphan = bundle_dir / "orphan.todo.md"
    orphan.write_text("# Objective Bundle: orphan\n", encoding="utf-8")
    shard = bundle_dir / "worldcoin-g002.todo.md"
    shard.write_text(
        shard.read_text(encoding="utf-8") + "\nUnreviewed instruction outside parsed fields.\n",
        encoding="utf-8",
    )

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    rendered = "\n".join(raised.value.problems)
    assert "shard body differs from source TODO task WORLDCOIN-AUTO-002" in rendered
    assert "orphan.todo.md" in rendered


def test_rejects_goal_count_blocked_set_and_missing_duckdb_sidecar(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    objective_path = paths[1]
    _replace(objective_path, "Status: blocked", "Status: active")
    (paths[2] / "objective_bundles/index.duckdb").unlink()

    with pytest.raises(BoardVerificationError) as raised:
        _verify(paths)
    rendered = "\n".join(raised.value.problems)
    assert "blocked-goal set differs" in rendered
    assert "schedulable-goal set differs" in rendered
    assert "no regular, non-symlink DuckDB sidecar" in rendered


def test_verifier_source_has_no_network_or_write_capability() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert not imported_roots & {
        "aiohttp",
        "httpx",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    assert not re_search_write_calls(source)


def re_search_write_calls(source: str) -> list[str]:
    """Return forbidden filesystem mutation spellings in verifier source."""

    forbidden = (
        ".chmod(",
        ".mkdir(",
        ".rename(",
        ".replace(",
        ".rmdir(",
        ".touch(",
        ".unlink(",
        ".write_bytes(",
        ".write_text(",
        "open(",
    )
    return [spelling for spelling in forbidden if spelling in source]
