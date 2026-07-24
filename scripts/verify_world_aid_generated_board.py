#!/usr/bin/env python3
"""Verify a generated World human-aid supervisor board without side effects.

The verifier intentionally uses only the Python standard library and performs
only filesystem reads.  It does not import the application, supervisor,
database, package-manager, or network stacks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GOAL_HEADER = re.compile(r"^## (?P<goal_id>WORLDCOIN-G[0-9]{3})(?:\s+(?P<title>.*))?$")
TASK_HEADER = re.compile(r"^## (?P<task_id>WORLDCOIN-AUTO-[A-Za-z0-9._-]+)(?:\s+(?P<title>.*))?$")
FIELD_LINE = re.compile(r"^- (?P<name>[A-Za-z][A-Za-z0-9 _-]*):(?: ?)(?P<value>.*)$")
SCHEDULABLE_STATES = frozenset(
    {
        "active",
        "todo",
        "open",
        "in_progress",
        "provisional",
        "provisionally_complete",
        "provisionally_completed",
        "analysis_inconclusive",
        "inconclusive",
        "reopened",
    }
)
NON_SCHEDULABLE_STATES = frozenset(
    {
        "blocked",
        "verified",
        "verified_complete",
        "complete",
        "completed",
        "done",
    }
)
EXPECTED_GOAL_IDS = frozenset(f"WORLDCOIN-G{index:03d}" for index in range(1, 43))
EXPECTED_BLOCKED_GOAL_IDS = frozenset(
    {
        "WORLDCOIN-G035",
        "WORLDCOIN-G036",
        "WORLDCOIN-G038",
        "WORLDCOIN-G039",
        "WORLDCOIN-G040",
    }
)
EXPECTED_NON_MATERIALIZED_GOAL_IDS = frozenset(
    {"WORLDCOIN-G035", "WORLDCOIN-G036"}
)
EXPECTED_REVIEW_ONLY_GOAL_IDS = frozenset(
    {"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"}
)
EXPECTED_SCHEDULABLE_GOAL_IDS = EXPECTED_GOAL_IDS - EXPECTED_BLOCKED_GOAL_IDS
EXPECTED_MATERIALIZED_GOAL_IDS = (
    EXPECTED_SCHEDULABLE_GOAL_IDS | EXPECTED_REVIEW_ONLY_GOAL_IDS
)
OBJECTIVE_GRAPH_SCHEMA = "ipfs_accelerate_py.agent_supervisor.objective_graph"
TODO_VECTOR_INDEX_SCHEMA = "ipfs_accelerate_py.agent_supervisor.todo_vector_index"
BUNDLE_QUERY_SCHEMA = "ipfs_accelerate_py.agent_supervisor.queryable_artifact@2"
BUNDLE_QUERY_KIND = "bundle_planning_index"


class BoardVerificationError(ValueError):
    """Raised when a generated board does not match its source objective heap."""

    def __init__(self, problems: Iterable[str]):
        self.problems = tuple(dict.fromkeys(str(problem) for problem in problems if str(problem)))
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class GoalRecord:
    """Source objective fields needed to verify generated task coverage."""

    goal_id: str
    title: str
    fields: Mapping[str, str]
    source_line: int

    @property
    def status(self) -> str:
        return _normalize_state(self.fields.get("status", ""))

    @property
    def is_schedulable(self) -> bool:
        return self.status in SCHEDULABLE_STATES


@dataclass(frozen=True)
class TaskRecord:
    """One parsed generated task block."""

    task_id: str
    title: str
    fields: Mapping[str, str]
    source_line: int
    body: str

    @property
    def goal_id(self) -> str:
        return str(self.fields.get("goal_id") or "").strip()

    @property
    def task_cid(self) -> str:
        return str(self.fields.get("canonical_task_cid") or self.fields.get("task_cid") or "").strip()

    @property
    def status(self) -> str:
        return _normalize_state(self.fields.get("status", ""))


@dataclass(frozen=True)
class VerificationSummary:
    """Counts from a successful generated-board verification."""

    source_goal_count: int
    schedulable_goal_count: int
    task_count: int
    bundle_count: int
    dag_count: int

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible summary."""

        return {
            "bundle_count": self.bundle_count,
            "dag_count": self.dag_count,
            "schedulable_goal_count": self.schedulable_goal_count,
            "source_goal_count": self.source_goal_count,
            "status": "passed",
            "task_count": self.task_count,
        }


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _normalize_state(value: str) -> str:
    return re.sub(r"[-\s]+", "_", str(value or "").strip().lower())


def _verify_review_only_scheduling_flags(
    record: Mapping[str, Any],
    *,
    location: str,
    json_booleans: bool,
    problems: list[str],
) -> None:
    """Require the durable scheduling-deny flags on a review-only record."""

    expected = {
        "is_schedulable": False,
        "review_only": True,
    }
    for field, expected_value in expected.items():
        if field not in record:
            problems.append(
                f"{location} is missing review-only scheduling flag {field!r}"
            )
            continue
        value = record[field]
        if json_booleans:
            valid = isinstance(value, bool) and value is expected_value
            expected_text = f"JSON boolean {str(expected_value).lower()}"
        else:
            valid = (
                isinstance(value, str)
                and value.strip().casefold() == str(expected_value).lower()
            )
            expected_text = f"literal {str(expected_value).lower()!r}"
        if not valid:
            problems.append(
                f"{location} review-only scheduling flag {field!r} must be "
                f"{expected_text}; found {value!r}"
            )


def _split_csv(value: str, *, omit_none: bool = False) -> tuple[str, ...]:
    parts = tuple(item.strip() for item in str(value or "").split(",") if item.strip())
    if omit_none:
        return tuple(item for item in parts if item.casefold() != "none")
    return parts


def _normalize_prose(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def _parse_fields(lines: Sequence[str], *, location: str, problems: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = FIELD_LINE.match(line)
        if match is None:
            continue
        name = _normalize_field_name(match.group("name"))
        if name in fields:
            problems.append(f"{location} has duplicate field {name!r}")
            continue
        fields[name] = match.group("value").strip()
    return fields


def parse_goal_heap(text: str, *, source: str, problems: list[str]) -> list[GoalRecord]:
    """Parse World goal records from the canonical Markdown heap."""

    lines = text.splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for offset, line in enumerate(lines):
        match = GOAL_HEADER.match(line)
        if match is not None:
            headers.append((offset, match))

    goals: list[GoalRecord] = []
    for position, (offset, match) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        goal_id = match.group("goal_id")
        fields = _parse_fields(
            lines[offset + 1 : end],
            location=f"{goal_id} at {source}:{offset + 1}",
            problems=problems,
        )
        goals.append(
            GoalRecord(
                goal_id=goal_id,
                title=(match.group("title") or "").strip(),
                fields=fields,
                source_line=offset + 1,
            )
        )
    if not goals:
        problems.append(f"{source} contains no parseable WORLDCOIN goals")
    return goals


def parse_task_board(text: str, *, source: str, problems: list[str]) -> list[TaskRecord]:
    """Parse generated World task records from a TODO or bundle shard."""

    lines = text.splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for offset, line in enumerate(lines):
        match = TASK_HEADER.match(line)
        if match is not None:
            headers.append((offset, match))

    tasks: list[TaskRecord] = []
    for position, (offset, match) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        task_id = match.group("task_id")
        fields = _parse_fields(
            lines[offset + 1 : end],
            location=f"{task_id} at {source}:{offset + 1}",
            problems=problems,
        )
        tasks.append(
            TaskRecord(
                task_id=task_id,
                title=(match.group("title") or "").strip(),
                fields=fields,
                source_line=offset + 1,
                body="\n".join(lines[offset:end]).strip(),
            )
        )
    if not tasks:
        problems.append(f"{source} contains no parseable WORLDCOIN-AUTO tasks")
    return tasks


def _read_text(path: Path, *, label: str, problems: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        problems.append(f"cannot read {label} {path}: {exc}")
        return ""


def _read_json(path: Path, *, label: str, problems: list[str]) -> dict[str, Any]:
    text = _read_text(path, label=label, problems=problems)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        problems.append(f"invalid JSON in {label} {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        problems.append(f"{label} {path} must contain a JSON object")
        return {}
    return payload


def _duplicates(values: Iterable[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if value and count > 1)


def _resolve_reference(repo_root: Path, value: str) -> Path:
    path = Path(str(value or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _verify_source_task_coverage(
    goals: Sequence[GoalRecord],
    tasks: Sequence[TaskRecord],
    *,
    problems: list[str],
) -> None:
    required_goal_fields = {
        "acceptance_criteria",
        "outputs",
        "parents",
        "refinement",
        "status",
        "validation",
    }
    recognized_states = SCHEDULABLE_STATES | NON_SCHEDULABLE_STATES
    observed_goal_ids = {goal.goal_id for goal in goals}
    if observed_goal_ids != EXPECTED_GOAL_IDS:
        problems.append(
            "objective heap goal IDs differ from the reviewed 42-goal contract: "
            f"missing={sorted(EXPECTED_GOAL_IDS - observed_goal_ids)}, "
            f"unexpected={sorted(observed_goal_ids - EXPECTED_GOAL_IDS)}"
        )
    blocked_goal_ids = {goal.goal_id for goal in goals if goal.status == "blocked"}
    if blocked_goal_ids != EXPECTED_BLOCKED_GOAL_IDS:
        problems.append(
            "objective heap blocked-goal set differs from the reviewed human gates: "
            f"expected={sorted(EXPECTED_BLOCKED_GOAL_IDS)}, "
            f"actual={sorted(blocked_goal_ids)}"
        )
    schedulable_goal_ids = {goal.goal_id for goal in goals if goal.is_schedulable}
    if schedulable_goal_ids != EXPECTED_SCHEDULABLE_GOAL_IDS:
        problems.append(
            "objective heap schedulable-goal set differs from the reviewed contract: "
            f"missing={sorted(EXPECTED_SCHEDULABLE_GOAL_IDS - schedulable_goal_ids)}, "
            f"unexpected={sorted(schedulable_goal_ids - EXPECTED_SCHEDULABLE_GOAL_IDS)}"
        )

    for goal in goals:
        location = f"{goal.goal_id} at objective heap line {goal.source_line}"
        missing_fields = sorted(required_goal_fields - set(goal.fields))
        if missing_fields:
            problems.append(f"{location} is missing required fields: {missing_fields}")
        if goal.status not in recognized_states:
            problems.append(f"{location} has unknown status {goal.status!r}")
        acceptance = str(goal.fields.get("acceptance_criteria") or "").strip()
        refinement = str(goal.fields.get("refinement") or "").strip()
        if not acceptance:
            problems.append(f"{location} has empty acceptance criteria")
        if not refinement:
            problems.append(f"{location} has empty refinement")
        elif acceptance and _normalize_prose(acceptance) not in _normalize_prose(refinement):
            problems.append(f"{location} refinement does not preserve its complete acceptance criteria")

    goal_duplicates = _duplicates(goal.goal_id for goal in goals)
    if goal_duplicates:
        problems.append(f"objective heap has duplicate goal IDs: {goal_duplicates}")
    task_duplicates = _duplicates(task.task_id for task in tasks)
    if task_duplicates:
        problems.append(f"generated TODO has duplicate task IDs: {task_duplicates}")
    cid_duplicates = _duplicates(task.task_cid for task in tasks)
    if cid_duplicates:
        problems.append(f"generated TODO has duplicate task CIDs: {cid_duplicates}")

    goals_by_id = {goal.goal_id: goal for goal in goals}
    tasks_by_goal: dict[str, list[TaskRecord]] = defaultdict(list)
    required_task_fields = {
        "bundle",
        "bundle_shard",
        "canonical_task_cid",
        "goal_id",
        "graph_parents",
        "outputs",
        "status",
        "acceptance",
        "validation",
    }

    for task in tasks:
        location = f"{task.task_id} at generated TODO line {task.source_line}"
        missing_fields = sorted(required_task_fields - set(task.fields))
        if missing_fields:
            problems.append(f"{location} is missing required fields: {missing_fields}")
        if not task.task_cid:
            problems.append(f"{location} has no canonical task CID")
        if not str(task.fields.get("acceptance") or "").strip():
            problems.append(f"{location} has empty acceptance")
        if not task.goal_id:
            problems.append(f"{location} has no goal ID")
            continue
        goal = goals_by_id.get(task.goal_id)
        if goal is None:
            problems.append(f"{location} references unknown goal {task.goal_id!r}")
            continue
        tasks_by_goal[task.goal_id].append(task)
        if task.goal_id in EXPECTED_REVIEW_ONLY_GOAL_IDS:
            if task.status != "blocked":
                problems.append(
                    f"{location} review-only goal {task.goal_id} must remain "
                    f"status 'blocked'; found {task.status!r}"
                )
            _verify_review_only_scheduling_flags(
                task.fields,
                location=f"{location} for review-only goal {task.goal_id}",
                json_booleans=False,
                problems=problems,
            )
        elif not goal.is_schedulable:
            problems.append(f"{location} materializes non-schedulable goal {goal.goal_id} with status {goal.status!r}")

    schedulable = {goal.goal_id for goal in goals if goal.is_schedulable}
    for goal_id in sorted(schedulable):
        count = len(tasks_by_goal.get(goal_id, ()))
        if count != 1:
            problems.append(f"schedulable goal {goal_id} must have exactly one generated task; found {count}")

    for goal_id in sorted(EXPECTED_REVIEW_ONLY_GOAL_IDS):
        count = len(tasks_by_goal.get(goal_id, ()))
        if count != 1:
            problems.append(
                f"review-only blocked goal {goal_id} must have exactly one "
                f"generated task; found {count}"
            )

    for goal_id in sorted(EXPECTED_NON_MATERIALIZED_GOAL_IDS):
        count = len(tasks_by_goal.get(goal_id, ()))
        if count:
            problems.append(
                f"terminal blocked goal {goal_id} must never materialize; "
                f"found {count} generated task(s)"
            )

    if len(tasks) != len(EXPECTED_MATERIALIZED_GOAL_IDS):
        problems.append(
            "generated review TODO must contain exactly "
            f"{len(EXPECTED_MATERIALIZED_GOAL_IDS)} tasks; found {len(tasks)}"
        )

    for goal in goals:
        if goal.goal_id not in EXPECTED_MATERIALIZED_GOAL_IDS:
            continue
        matching = tasks_by_goal.get(goal.goal_id, ())
        if len(matching) != 1:
            continue
        task = matching[0]
        source_validation = str(goal.fields.get("validation") or "").strip()
        generated_validation = str(task.fields.get("validation") or "").strip()
        if source_validation != generated_validation:
            problems.append(
                f"{task.task_id} validation differs from {goal.goal_id}: "
                f"source={source_validation!r}, generated={generated_validation!r}"
            )

        source_parents = _split_csv(goal.fields.get("parents", ""), omit_none=True)
        generated_parents = _split_csv(task.fields.get("graph_parents", ""), omit_none=True)
        if source_parents != generated_parents:
            problems.append(
                f"{task.task_id} graph parents differ from {goal.goal_id}: "
                f"source={list(source_parents)!r}, generated={list(generated_parents)!r}"
            )

        source_outputs = _split_csv(goal.fields.get("outputs", ""))
        generated_outputs = set(_split_csv(task.fields.get("outputs", "")))
        missing_outputs = [output for output in source_outputs if output not in generated_outputs]
        if missing_outputs:
            problems.append(f"{task.task_id} omits source outputs from {goal.goal_id}: {missing_outputs}")

        source_acceptance = str(goal.fields.get("acceptance_criteria") or "").strip()
        generated_acceptance = str(task.fields.get("acceptance") or "").strip()
        if source_acceptance and _normalize_prose(source_acceptance) not in _normalize_prose(generated_acceptance):
            problems.append(
                f"{task.task_id} acceptance does not preserve the complete {goal.goal_id} source acceptance criteria"
            )


def _task_pairs(tasks: Iterable[TaskRecord]) -> set[tuple[str, str]]:
    return {(task.task_id, task.task_cid) for task in tasks if task.task_id and task.task_cid}


def _index_task_pairs(
    bundles: Mapping[str, Any],
    *,
    problems: list[str],
) -> tuple[set[tuple[str, str]], dict[str, tuple[str, Mapping[str, Any]]]]:
    pairs: set[tuple[str, str]] = set()
    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    seen_ids: list[str] = []
    seen_cids: list[str] = []
    for bundle_key, raw_bundle in sorted(bundles.items()):
        if not isinstance(raw_bundle, Mapping):
            problems.append(f"bundle {bundle_key!r} is not an object")
            continue
        raw_tasks = raw_bundle.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            problems.append(f"bundle {bundle_key!r} contains no indexed tasks")
            continue
        for position, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, Mapping):
                problems.append(f"bundle {bundle_key!r} task {position} is not an object")
                continue
            task_id = str(raw_task.get("task_id") or "").strip()
            task_cid = str(raw_task.get("canonical_task_cid") or raw_task.get("task_cid") or "").strip()
            if not task_id or not task_cid:
                problems.append(f"bundle {bundle_key!r} task {position} lacks task ID or canonical CID")
                continue
            seen_ids.append(task_id)
            seen_cids.append(task_cid)
            pairs.add((task_id, task_cid))
            indexed[task_id] = (str(bundle_key), raw_task)
    duplicate_ids = _duplicates(seen_ids)
    if duplicate_ids:
        problems.append(f"bundle index has duplicate task IDs: {duplicate_ids}")
    duplicate_cids = _duplicates(seen_cids)
    if duplicate_cids:
        problems.append(f"bundle index has duplicate task CIDs: {duplicate_cids}")
    return pairs, indexed


def _string_sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return _split_csv(value, omit_none=True)
    if isinstance(value, Sequence) and not isinstance(
        value,
        str | bytes | bytearray,
    ):
        return tuple(
            str(item).strip() for item in value if str(item).strip() and str(item).strip().casefold() != "none"
        )
    return ()


def _verify_index_task_identity(
    *,
    goals: Sequence[GoalRecord],
    todo_tasks: Sequence[TaskRecord],
    bundles: Mapping[str, Any],
    indexed_tasks: Mapping[str, tuple[str, Mapping[str, Any]]],
    repo_root: Path,
    problems: list[str],
) -> None:
    goals_by_id = {goal.goal_id: goal for goal in goals}
    for task in todo_tasks:
        indexed = indexed_tasks.get(task.task_id)
        if indexed is None:
            continue
        bundle_key, indexed_task = indexed
        location = f"bundle index task {task.task_id}"
        todo_bundle = str(task.fields.get("bundle") or "").strip()
        if bundle_key != todo_bundle:
            problems.append(f"{location} bundle differs from TODO: index={bundle_key!r}, todo={todo_bundle!r}")
        raw_bundle = bundles.get(bundle_key)
        if isinstance(raw_bundle, Mapping):
            indexed_bundle_key = str(raw_bundle.get("bundle_key") or "").strip()
            if indexed_bundle_key != bundle_key:
                problems.append(f"bundle {bundle_key!r} embeds a different bundle_key {indexed_bundle_key!r}")
            shard_reference = str(raw_bundle.get("shard_path") or "").strip()
            todo_shard = str(task.fields.get("bundle_shard") or "").strip()
            if not shard_reference or _resolve_reference(repo_root, shard_reference) != _resolve_reference(
                repo_root, todo_shard
            ):
                problems.append(f"{location} shard differs from TODO: index={shard_reference!r}, todo={todo_shard!r}")

        indexed_parents = _string_sequence(indexed_task.get("parent_goal_ids"))
        todo_parents = _split_csv(task.fields.get("graph_parents", ""), omit_none=True)
        if indexed_parents != todo_parents:
            problems.append(
                f"{location} parents differ from TODO: index={list(indexed_parents)!r}, todo={list(todo_parents)!r}"
            )

        if task.goal_id in EXPECTED_REVIEW_ONLY_GOAL_IDS:
            indexed_status = _normalize_state(indexed_task.get("status", ""))
            if indexed_status != "blocked":
                problems.append(
                    f"{location} for review-only goal {task.goal_id} must "
                    f"remain status 'blocked'; found {indexed_status!r}"
                )
            _verify_review_only_scheduling_flags(
                indexed_task,
                location=f"{location} for review-only goal {task.goal_id}",
                json_booleans=True,
                problems=problems,
            )
            if isinstance(raw_bundle, Mapping):
                _verify_review_only_scheduling_flags(
                    raw_bundle,
                    location=f"bundle {bundle_key!r} for review-only goal {task.goal_id}",
                    json_booleans=True,
                    problems=problems,
                )

        goal = goals_by_id.get(task.goal_id)
        if goal is not None:
            source_outputs = _split_csv(goal.fields.get("outputs", ""))
            indexed_outputs = _string_sequence(indexed_task.get("outputs"))
            if indexed_outputs != source_outputs:
                problems.append(
                    f"{location} outputs differ from {goal.goal_id}: "
                    f"index={list(indexed_outputs)!r}, source={list(source_outputs)!r}"
                )
            criteria = indexed_task.get("acceptance_criteria")
            rendered_criteria = "; ".join(_string_sequence(criteria)) if not isinstance(criteria, str) else criteria
            source_acceptance = str(goal.fields.get("acceptance_criteria") or "")
            if _normalize_prose(source_acceptance) not in _normalize_prose(rendered_criteria):
                problems.append(
                    f"{location} acceptance criteria do not preserve the complete "
                    f"{goal.goal_id} source acceptance criteria"
                )


def _expected_task_parent_edges(
    goals: Sequence[GoalRecord],
    tasks: Sequence[TaskRecord],
    *,
    problems: list[str],
) -> set[tuple[str, str]]:
    goals_by_id = {goal.goal_id: goal for goal in goals}
    task_by_goal = {task.goal_id: task for task in tasks if task.goal_id}
    expected: set[tuple[str, str]] = set()
    for goal in goals:
        for parent_goal_id in _split_csv(goal.fields.get("parents", ""), omit_none=True):
            if parent_goal_id not in goals_by_id:
                problems.append(f"{goal.goal_id} references unknown parent goal {parent_goal_id!r}")
                continue
            if (
                goal.goal_id not in EXPECTED_MATERIALIZED_GOAL_IDS
                or parent_goal_id not in EXPECTED_MATERIALIZED_GOAL_IDS
            ):
                continue
            child_task = task_by_goal.get(goal.goal_id)
            parent_task = task_by_goal.get(parent_goal_id)
            if child_task is None or parent_task is None:
                continue
            expected.add((parent_task.task_cid, child_task.task_cid))
    return expected


def _verify_dag(
    name: str,
    dag: Mapping[str, Any],
    *,
    todo_pairs: set[tuple[str, str]],
    todo_tasks: Sequence[TaskRecord],
    expected_parent_edges: set[tuple[str, str]],
    problems: list[str],
) -> None:
    invalid = dag.get("invalid_task_cids") or []
    if invalid:
        problems.append(f"{name} contains invalid task CIDs: {sorted(str(item) for item in invalid)}")

    raw_nodes = dag.get("nodes")
    if not isinstance(raw_nodes, Mapping) or not raw_nodes:
        problems.append(f"{name} contains no node map")
        return

    dag_pairs: set[tuple[str, str]] = set()
    todo_by_cid = {task.task_cid: task for task in todo_tasks if task.task_cid}
    review_only_cids = {
        task.task_cid
        for task in todo_tasks
        if task.task_cid and task.goal_id in EXPECTED_REVIEW_ONLY_GOAL_IDS
    }
    node_cids = {str(cid) for cid in raw_nodes}
    for raw_cid, raw_node in raw_nodes.items():
        cid = str(raw_cid)
        if not isinstance(raw_node, Mapping):
            problems.append(f"{name} node {cid!r} is not an object")
            continue
        task_id = str(raw_node.get("task_id") or "").strip()
        if not task_id:
            problems.append(f"{name} node {cid!r} has no task ID")
            continue
        dag_pairs.add((task_id, cid))
        todo_task = todo_by_cid.get(cid)
        if todo_task is not None:
            node_goal_id = str(raw_node.get("goal_id") or "").strip()
            if task_id != todo_task.task_id or node_goal_id != todo_task.goal_id:
                problems.append(
                    f"{name} node {cid!r} identity differs from TODO: "
                    f"node_task={task_id!r}, todo_task={todo_task.task_id!r}, "
                    f"node_goal={node_goal_id!r}, todo_goal={todo_task.goal_id!r}"
                )
            if todo_task.goal_id in EXPECTED_REVIEW_ONLY_GOAL_IDS:
                node_status = _normalize_state(raw_node.get("status", ""))
                if node_status != "blocked":
                    problems.append(
                        f"{name} node {cid!r} for review-only goal "
                        f"{todo_task.goal_id} must remain status 'blocked'; "
                        f"found {node_status!r}"
                    )
                metadata = raw_node.get("metadata")
                if not isinstance(metadata, Mapping):
                    problems.append(
                        f"{name} node {cid!r} for review-only goal "
                        f"{todo_task.goal_id} has no metadata object"
                    )
                else:
                    _verify_review_only_scheduling_flags(
                        metadata,
                        location=(
                            f"{name} node {cid!r} metadata for review-only "
                            f"goal {todo_task.goal_id}"
                        ),
                        json_booleans=True,
                        problems=problems,
                    )
    if dag_pairs != todo_pairs:
        problems.append(
            f"{name} task ID/CID set differs from generated TODO: "
            f"dag_only={sorted(dag_pairs - todo_pairs)}, "
            f"todo_only={sorted(todo_pairs - dag_pairs)}"
        )

    adjacency: dict[str, set[str]] = {cid: set() for cid in node_cids}
    indegree = {cid: 0 for cid in node_cids}
    raw_edges = dag.get("edges") or []
    if not isinstance(raw_edges, list):
        problems.append(f"{name} edges must be a list")
        raw_edges = []
    observed_edges: set[tuple[str, str]] = set()
    for position, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, Mapping):
            problems.append(f"{name} edge {position} is not an object")
            continue
        source = str(raw_edge.get("source_task_cid") or "").strip()
        target = str(raw_edge.get("target_task_cid") or "").strip()
        if source not in node_cids:
            problems.append(f"{name} edge {position} has dangling source CID {source!r}")
        if target not in node_cids:
            problems.append(f"{name} edge {position} has dangling target CID {target!r}")
        if source and source == target:
            problems.append(f"{name} edge {position} is a self-dependency for {source!r}")
        if source in node_cids and target in node_cids and source != target and target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1
            observed_edges.add((source, target))

    if observed_edges != expected_parent_edges:
        problems.append(
            f"{name} parent-to-child edges differ from the objective heap: "
            f"missing={sorted(expected_parent_edges - observed_edges)}, "
            f"unexpected={sorted(observed_edges - expected_parent_edges)}"
        )

    topological_roots = {cid for cid, degree in indegree.items() if degree == 0}
    expected_claimable = topological_roots - review_only_cids
    ready = deque(sorted(topological_roots))
    visited = 0
    while ready:
        cid = ready.popleft()
        visited += 1
        for target in sorted(adjacency[cid]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if visited != len(node_cids):
        cyclic = sorted(cid for cid, degree in indegree.items() if degree > 0)
        problems.append(f"{name} contains a dependency cycle involving {cyclic}")

    raw_claimable = dag.get("claimable_task_cids") or []
    unknown_claimable = sorted(str(cid) for cid in raw_claimable if str(cid) not in node_cids)
    if unknown_claimable:
        problems.append(f"{name} has unknown claimable task CIDs: {unknown_claimable}")
    observed_claimable = {str(cid) for cid in raw_claimable}
    if observed_claimable != expected_claimable:
        problems.append(
            f"{name} claimable roots differ from zero-indegree tasks: "
            f"missing={sorted(expected_claimable - observed_claimable)}, "
            f"unexpected={sorted(observed_claimable - expected_claimable)}"
        )


def _verify_shards(
    *,
    repo_root: Path,
    generated_root: Path,
    todo_path: Path,
    todo_tasks: Sequence[TaskRecord],
    bundles: Mapping[str, Any],
    problems: list[str],
) -> None:
    todo_by_id = {task.task_id: task for task in todo_tasks}
    bundle_dir = generated_root / "objective_bundles"
    referenced_shards: dict[Path, str] = {}
    for bundle_key, raw_bundle in sorted(bundles.items()):
        if not isinstance(raw_bundle, Mapping):
            continue
        shard_reference = str(raw_bundle.get("shard_path") or "").strip()
        if not shard_reference:
            problems.append(f"bundle {bundle_key!r} has no shard path")
            continue
        shard_path = _resolve_reference(repo_root, shard_reference)
        if not _is_within(shard_path, generated_root):
            problems.append(f"bundle {bundle_key!r} shard escapes generated root: {shard_path}")
            continue
        if shard_path.parent != bundle_dir or not shard_path.name.endswith(".todo.md"):
            problems.append(
                f"bundle {bundle_key!r} shard is not a direct objective_bundles/*.todo.md file: {shard_path}"
            )
            continue
        if shard_path.is_symlink():
            problems.append(f"bundle {bundle_key!r} shard must not be a symlink: {shard_path}")
            continue
        previous_bundle = referenced_shards.setdefault(shard_path, str(bundle_key))
        if previous_bundle != bundle_key:
            problems.append(f"bundle shard {shard_path} is shared by {previous_bundle!r} and {bundle_key!r}")
        shard_text = _read_text(
            shard_path,
            label=f"bundle {bundle_key!r} shard",
            problems=problems,
        )
        if not shard_text:
            continue
        source_match = re.search(r"^Source todo:\s*(?P<path>.+?)\s*$", shard_text, re.MULTILINE)
        if source_match is None:
            problems.append(f"bundle {bundle_key!r} shard has no Source todo reference")
        else:
            shard_source = _resolve_reference(repo_root, source_match.group("path"))
            if shard_source != todo_path:
                problems.append(
                    f"bundle {bundle_key!r} shard source TODO differs: expected={todo_path}, actual={shard_source}"
                )

        shard_tasks = parse_task_board(
            shard_text,
            source=str(shard_path),
            problems=problems,
        )
        shard_ids = [task.task_id for task in shard_tasks]
        duplicate_ids = _duplicates(shard_ids)
        if duplicate_ids:
            problems.append(f"bundle {bundle_key!r} shard has duplicate task IDs: {duplicate_ids}")

        raw_index_tasks = raw_bundle.get("tasks")
        if isinstance(raw_index_tasks, list):
            expected_ids = {
                str(raw_task.get("task_id") or "").strip()
                for raw_task in raw_index_tasks
                if isinstance(raw_task, Mapping)
            }
        else:
            expected_ids = set()
        actual_ids = set(shard_ids)
        if actual_ids != expected_ids:
            problems.append(
                f"bundle {bundle_key!r} shard task IDs differ from index: "
                f"shard_only={sorted(actual_ids - expected_ids)}, "
                f"index_only={sorted(expected_ids - actual_ids)}"
            )

        for shard_task in shard_tasks:
            source_task = todo_by_id.get(shard_task.task_id)
            if source_task is None:
                problems.append(f"bundle {bundle_key!r} shard contains task absent from TODO: {shard_task.task_id}")
                continue
            if shard_task.body != source_task.body:
                problems.append(f"bundle {bundle_key!r} shard body differs from source TODO task {shard_task.task_id}")
            todo_bundle = str(source_task.fields.get("bundle") or "").strip()
            if todo_bundle != bundle_key:
                problems.append(
                    f"{source_task.task_id} names bundle {todo_bundle!r}, but index places it in {bundle_key!r}"
                )
            todo_shard_reference = str(source_task.fields.get("bundle_shard") or "").strip()
            if not todo_shard_reference:
                problems.append(f"{source_task.task_id} has no bundle shard reference")
            elif _resolve_reference(repo_root, todo_shard_reference) != shard_path:
                problems.append(
                    f"{source_task.task_id} bundle shard reference differs from index: {todo_shard_reference!r}"
                )

    actual_shards = {path.resolve() for path in bundle_dir.rglob("*.todo.md") if path.is_file() or path.is_symlink()}
    expected_shards = set(referenced_shards)
    if actual_shards != expected_shards:
        problems.append(
            "objective bundle shard files differ from the index: "
            f"orphan={sorted(str(path) for path in actual_shards - expected_shards)}, "
            f"missing={sorted(str(path) for path in expected_shards - actual_shards)}"
        )


def _verify_objective_graph(
    *,
    payload: Mapping[str, Any],
    goals: Sequence[GoalRecord],
    objective_path: Path,
    repo_root: Path,
    problems: list[str],
) -> None:
    if payload.get("schema") != OBJECTIVE_GRAPH_SCHEMA:
        problems.append(f"objective graph has unexpected schema {payload.get('schema')!r}")

    objective_reference = str(payload.get("objective_path") or "").strip()
    if not objective_reference or _resolve_reference(repo_root, objective_reference) != objective_path:
        problems.append(
            f"objective graph source path differs from the canonical objective heap: {objective_reference!r}"
        )

    goals_by_id = {goal.goal_id: goal for goal in goals}
    raw_goals = payload.get("goals")
    if not isinstance(raw_goals, list):
        problems.append("objective graph goals must be a list")
        raw_goals = []
    graph_goal_ids = [str(item.get("goal_id") or "").strip() for item in raw_goals if isinstance(item, Mapping)]
    duplicate_goal_ids = _duplicates(graph_goal_ids)
    if duplicate_goal_ids:
        problems.append(f"objective graph has duplicate goal IDs: {duplicate_goal_ids}")
    if set(graph_goal_ids) != set(goals_by_id):
        problems.append(
            "objective graph goal IDs differ from the objective heap: "
            f"graph_only={sorted(set(graph_goal_ids) - set(goals_by_id))}, "
            f"heap_only={sorted(set(goals_by_id) - set(graph_goal_ids))}"
        )
    for item in raw_goals:
        if not isinstance(item, Mapping):
            problems.append("objective graph contains a malformed goal record")
            continue
        goal_id = str(item.get("goal_id") or "").strip()
        goal = goals_by_id.get(goal_id)
        if goal is None:
            continue
        checks = {
            "bundle": str(goal.fields.get("bundle") or "").strip(),
            "status": goal.status,
            "title": goal.title,
            "track": str(goal.fields.get("track") or "").strip(),
        }
        for field, expected in checks.items():
            actual = _normalize_state(item.get(field, "")) if field == "status" else str(item.get(field) or "").strip()
            if actual != expected:
                problems.append(
                    f"objective graph {goal_id} {field} differs from the objective heap: "
                    f"graph={actual!r}, heap={expected!r}"
                )
        if _string_sequence(item.get("parents")) != _split_csv(goal.fields.get("parents", ""), omit_none=True):
            problems.append(f"objective graph {goal_id} parents differ from the objective heap")
        try:
            graph_priority = int(item.get("fib_priority"))
            source_priority = int(goal.fields.get("fib_priority", ""))
        except (TypeError, ValueError):
            problems.append(f"objective graph {goal_id} has an invalid Fibonacci priority")
        else:
            if graph_priority != source_priority:
                problems.append(f"objective graph {goal_id} Fibonacci priority differs from the objective heap")

    if int(payload.get("goal_count") or -1) != len(goals):
        problems.append("objective graph goal_count differs from the objective heap")
    schedulable = {goal.goal_id for goal in goals if goal.is_schedulable}
    if int(payload.get("active_goal_count") or -1) != len(schedulable):
        problems.append("objective graph active_goal_count differs from the schedulable goal count")

    graph = payload.get("graph")
    if not isinstance(graph, Mapping):
        problems.append("objective graph graph field must be an object")
        return
    graph_nodes = {str(item) for item in (graph.get("nodes") or [])}
    if graph_nodes != set(goals_by_id):
        problems.append(
            "objective graph node set differs from the objective heap: "
            f"graph_only={sorted(graph_nodes - set(goals_by_id))}, "
            f"heap_only={sorted(set(goals_by_id) - graph_nodes)}"
        )

    expected_edges = {
        (parent, goal.goal_id)
        for goal in goals
        for parent in _split_csv(goal.fields.get("parents", ""), omit_none=True)
        if parent in goals_by_id
    }
    raw_edges = graph.get("edges")
    if not isinstance(raw_edges, list):
        problems.append("objective graph edges must be a list")
        raw_edges = []
    observed_edges: set[tuple[str, str]] = set()
    for position, edge in enumerate(raw_edges):
        if not isinstance(edge, Mapping):
            problems.append(f"objective graph edge {position} is not an object")
            continue
        source = str(edge.get("from") or "").strip()
        target = str(edge.get("to") or "").strip()
        kind = str(edge.get("kind") or "").strip()
        if kind != "refines":
            problems.append(f"objective graph edge {position} has unexpected kind {kind!r}")
        observed_edges.add((source, target))
    if observed_edges != expected_edges:
        problems.append(
            "objective graph parent-to-child edges differ from the objective heap: "
            f"missing={sorted(expected_edges - observed_edges)}, "
            f"unexpected={sorted(observed_edges - expected_edges)}"
        )

    expected_roots = {goal.goal_id for goal in goals if not _split_csv(goal.fields.get("parents", ""), omit_none=True)}
    if {str(item) for item in (graph.get("roots") or [])} != expected_roots:
        problems.append("objective graph roots differ from the objective heap")
    if {str(item) for item in (graph.get("schedulable_goal_ids") or [])} != schedulable:
        problems.append("objective graph schedulable goals differ from the objective heap")
    terminal = {goal.goal_id for goal in goals if not goal.is_schedulable}
    if {str(item) for item in (graph.get("terminal_goal_ids") or [])} != terminal:
        problems.append("objective graph terminal goals differ from the objective heap")

    raw_schedule = payload.get("heap_schedule")
    if not isinstance(raw_schedule, list):
        problems.append("objective graph heap_schedule must be a list")
        raw_schedule = []
    scheduled_ids = [str(item.get("goal_id") or "").strip() for item in raw_schedule if isinstance(item, Mapping)]
    if _duplicates(scheduled_ids) or set(scheduled_ids) != schedulable:
        problems.append(
            "objective graph heap schedule differs from schedulable goals: "
            f"missing={sorted(schedulable - set(scheduled_ids))}, "
            f"unexpected={sorted(set(scheduled_ids) - schedulable)}"
        )


def _verify_todo_vector_index(
    *,
    payload: Mapping[str, Any],
    todo_tasks: Sequence[TaskRecord],
    todo_path: Path,
    objective_path: Path,
    bundle_index_path: Path,
    repo_root: Path,
    problems: list[str],
) -> None:
    if payload.get("schema") != TODO_VECTOR_INDEX_SCHEMA:
        problems.append(f"TODO vector index has unexpected schema {payload.get('schema')!r}")
    path_references = {
        "todo_path": todo_path,
        "objective_path": objective_path,
        "bundle_index_path": bundle_index_path,
    }
    for field, expected in path_references.items():
        reference = str(payload.get(field) or "").strip()
        if not reference or _resolve_reference(repo_root, reference) != expected:
            problems.append(f"TODO vector index {field} differs: expected={expected}, actual={reference!r}")

    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        problems.append("TODO vector index records must be a list")
        raw_records = []
    records_by_id: dict[str, Mapping[str, Any]] = {}
    record_ids: list[str] = []
    record_cids: list[str] = []
    for position, raw_record in enumerate(raw_records):
        if not isinstance(raw_record, Mapping):
            problems.append(f"TODO vector index record {position} is not an object")
            continue
        task_id = str(raw_record.get("task_id") or "").strip()
        task_cid = str(raw_record.get("canonical_task_cid") or raw_record.get("task_cid") or "").strip()
        record_ids.append(task_id)
        record_cids.append(task_cid)
        records_by_id[task_id] = raw_record
    if _duplicates(record_ids):
        problems.append(f"TODO vector index has duplicate task IDs: {_duplicates(record_ids)}")
    if _duplicates(record_cids):
        problems.append(f"TODO vector index has duplicate task CIDs: {_duplicates(record_cids)}")

    todo_pairs = _task_pairs(todo_tasks)
    vector_pairs = {
        (
            str(record.get("task_id") or "").strip(),
            str(record.get("canonical_task_cid") or record.get("task_cid") or "").strip(),
        )
        for record in raw_records
        if isinstance(record, Mapping)
    }
    if vector_pairs != todo_pairs:
        problems.append(
            "TODO vector task ID/CID set differs from generated TODO: "
            f"vector_only={sorted(vector_pairs - todo_pairs)}, "
            f"todo_only={sorted(todo_pairs - vector_pairs)}"
        )

    for task in todo_tasks:
        record = records_by_id.get(task.task_id)
        if record is None:
            continue
        scalar_checks = {
            "acceptance": str(task.fields.get("acceptance") or "").strip(),
            "bundle_key": str(task.fields.get("bundle") or "").strip(),
            "goal_id": task.goal_id,
            "status": str(task.fields.get("status") or "").strip(),
            "title": task.title,
        }
        for field, expected in scalar_checks.items():
            actual = str(record.get(field) or "").strip()
            if actual != expected:
                problems.append(
                    f"TODO vector {task.task_id} {field} differs from TODO: vector={actual!r}, todo={expected!r}"
                )
        sequence_checks = {
            "graph_parents": _split_csv(task.fields.get("graph_parents", ""), omit_none=True),
            "outputs": _split_csv(task.fields.get("outputs", "")),
            "validation": (str(task.fields.get("validation") or "").strip(),),
        }
        for field, expected in sequence_checks.items():
            actual = _string_sequence(record.get(field))
            if actual != expected:
                problems.append(
                    f"TODO vector {task.task_id} {field} differs from TODO: "
                    f"vector={list(actual)!r}, todo={list(expected)!r}"
                )
        vector_shard = str(record.get("bundle_shard") or "").strip()
        todo_shard = str(task.fields.get("bundle_shard") or "").strip()
        if not vector_shard or _resolve_reference(repo_root, vector_shard) != _resolve_reference(repo_root, todo_shard):
            problems.append(f"TODO vector {task.task_id} bundle shard differs from TODO")

    expected_count = len(todo_tasks)
    if int(payload.get("task_count") or -1) != expected_count:
        problems.append("TODO vector task_count differs from generated TODO")
    expected_active_count = sum(
        task.goal_id not in EXPECTED_REVIEW_ONLY_GOAL_IDS
        for task in todo_tasks
    )
    if int(payload.get("active_task_count") or -1) != expected_active_count:
        problems.append(
            "TODO vector active_task_count differs from the non-blocked "
            "generated task count"
        )

    query_artifact = payload.get("query_artifact")
    if not isinstance(query_artifact, Mapping):
        problems.append("TODO vector index has no query_artifact reference")
    else:
        json_reference = str(query_artifact.get("path") or "").strip()
        duckdb_reference = str(query_artifact.get("duckdb_path") or "").strip()
        if not json_reference or _resolve_reference(repo_root, json_reference) != bundle_index_path:
            problems.append("TODO vector query_artifact JSON path differs from bundle index")
        if not duckdb_reference or _resolve_reference(repo_root, duckdb_reference) != bundle_index_path.with_suffix(
            ".duckdb"
        ):
            problems.append("TODO vector query_artifact DuckDB path differs from bundle index")


def _verify_bundle_query_store(
    *,
    index: Mapping[str, Any],
    bundle_index_path: Path,
    problems: list[str],
) -> None:
    query_store = index.get("query_store")
    if not isinstance(query_store, Mapping):
        problems.append("bundle index has no query_store descriptor")
        return
    expected = {
        "artifact_kind": BUNDLE_QUERY_KIND,
        "catalog_table": "artifact_catalog",
        "duckdb_path": bundle_index_path.with_suffix(".duckdb").name,
        "schema": BUNDLE_QUERY_SCHEMA,
    }
    observed = {key: query_store.get(key) for key in expected}
    if observed != expected:
        problems.append(f"bundle index query_store descriptor differs: expected={expected!r}, actual={observed!r}")
    duckdb_path = bundle_index_path.with_suffix(".duckdb")
    if not duckdb_path.is_file() or duckdb_path.is_symlink():
        problems.append(f"bundle index has no regular, non-symlink DuckDB sidecar: {duckdb_path}")


def verify_generated_board(
    *,
    repo_root: Path,
    objective_path: Path,
    generated_root: Path,
) -> VerificationSummary:
    """Verify generated board identity and source alignment.

    Raises:
        BoardVerificationError: If any source, task, index, DAG, or shard
            invariant is violated.
    """

    root = repo_root.resolve()
    objective = objective_path if objective_path.is_absolute() else root / objective_path
    objective = objective.resolve()
    generated_input = generated_root if generated_root.is_absolute() else root / generated_root
    generated_is_symlink = generated_input.is_symlink()
    generated = generated_input.resolve()
    approved_parent = (root / "data/worldcoin_human_aid/agent_supervisor/regenerations").resolve()
    todo_path = generated / "WORLDCOIN_HUMAN_AID_TODO.md"
    index_path = generated / "objective_bundles" / "index.json"
    graph_path = generated / "objective_graph.json"
    vector_path = generated / "objective_bundles" / "todo_vector_index.json"

    problems: list[str] = []
    if generated.parent != approved_parent:
        problems.append(
            f"generated root must be one direct immutable review directory below {approved_parent}: {generated}"
        )
    if generated_is_symlink:
        problems.append(f"generated root must not be a symlink: {generated}")
    for label, path in {
        "generated TODO": todo_path,
        "bundle index": index_path,
        "objective graph": graph_path,
        "TODO vector index": vector_path,
    }.items():
        if path.is_symlink():
            problems.append(f"{label} must not be a symlink: {path}")

    goal_text = _read_text(objective, label="objective heap", problems=problems)
    todo_text = _read_text(todo_path, label="generated TODO", problems=problems)
    index = _read_json(index_path, label="bundle index", problems=problems)
    objective_graph = _read_json(graph_path, label="objective graph", problems=problems)
    todo_vector_index = _read_json(vector_path, label="TODO vector index", problems=problems)

    goals = parse_goal_heap(goal_text, source=str(objective), problems=problems) if goal_text else []
    tasks = parse_task_board(todo_text, source=str(todo_path), problems=problems) if todo_text else []
    _verify_source_task_coverage(goals, tasks, problems=problems)

    source_todo_reference = str(index.get("source_todo") or "").strip()
    if not source_todo_reference:
        problems.append("bundle index has no source_todo reference")
    elif _resolve_reference(root, source_todo_reference) != todo_path:
        problems.append(
            "bundle index source_todo differs from generated TODO: "
            f"expected={todo_path}, actual={_resolve_reference(root, source_todo_reference)}"
        )

    raw_bundles = index.get("bundles")
    if not isinstance(raw_bundles, Mapping) or not raw_bundles:
        problems.append("bundle index contains no bundles")
        bundles: Mapping[str, Any] = {}
    else:
        bundles = raw_bundles

    todo_pairs = _task_pairs(tasks)
    index_pairs, indexed_tasks = _index_task_pairs(bundles, problems=problems)
    if index_pairs != todo_pairs:
        problems.append(
            "bundle index task ID/CID set differs from generated TODO: "
            f"index_only={sorted(index_pairs - todo_pairs)}, "
            f"todo_only={sorted(todo_pairs - index_pairs)}"
        )

    todo_by_id = {task.task_id: task for task in tasks}
    for task_id, (_bundle_key, indexed_task) in indexed_tasks.items():
        todo_task = todo_by_id.get(task_id)
        if todo_task is None:
            continue
        indexed_goal_id = str(indexed_task.get("goal_id") or "").strip()
        if indexed_goal_id != todo_task.goal_id:
            problems.append(
                f"bundle index goal ID for {task_id} differs from TODO: "
                f"index={indexed_goal_id!r}, todo={todo_task.goal_id!r}"
            )

    _verify_index_task_identity(
        goals=goals,
        todo_tasks=tasks,
        bundles=bundles,
        indexed_tasks=indexed_tasks,
        repo_root=root,
        problems=problems,
    )
    _verify_bundle_query_store(
        index=index,
        bundle_index_path=index_path,
        problems=problems,
    )
    expected_parent_edges = _expected_task_parent_edges(goals, tasks, problems=problems)

    planning = index.get("task_planning_graph")
    dag_candidates: dict[str, Any] = {
        "dependency_dag": index.get("dependency_dag"),
        "task_dependency_graph": index.get("task_dependency_graph"),
    }
    if isinstance(planning, Mapping):
        dag_candidates["task_planning_graph.task_dependency_graph"] = planning.get("task_dependency_graph")
    for name, candidate in dag_candidates.items():
        if candidate is not None and not isinstance(candidate, Mapping):
            problems.append(f"{name} must be a dependency-DAG object")
    dags = {name: dag for name, dag in dag_candidates.items() if isinstance(dag, Mapping)}
    if not dags:
        problems.append("bundle index contains no dependency DAG")
    for name, dag in sorted(dags.items()):
        _verify_dag(
            name,
            dag,
            todo_pairs=todo_pairs,
            todo_tasks=tasks,
            expected_parent_edges=expected_parent_edges,
            problems=problems,
        )

    _verify_shards(
        repo_root=root,
        generated_root=generated,
        todo_path=todo_path,
        todo_tasks=tasks,
        bundles=bundles,
        problems=problems,
    )
    _verify_objective_graph(
        payload=objective_graph,
        goals=goals,
        objective_path=objective,
        repo_root=root,
        problems=problems,
    )
    _verify_todo_vector_index(
        payload=todo_vector_index,
        todo_tasks=tasks,
        todo_path=todo_path,
        objective_path=objective,
        bundle_index_path=index_path,
        repo_root=root,
        problems=problems,
    )

    if problems:
        raise BoardVerificationError(problems)
    return VerificationSummary(
        source_goal_count=len(goals),
        schedulable_goal_count=sum(goal.is_schedulable for goal in goals),
        task_count=len(tasks),
        bundle_count=len(bundles),
        dag_count=len(dags),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Verify a generated World human-aid board without network calls or writes."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--objective-path", type=Path, required=True)
    parser.add_argument("--generated-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline generated-board verifier."""

    args = build_arg_parser().parse_args(argv)
    try:
        summary = verify_generated_board(
            repo_root=args.repo_root,
            objective_path=args.objective_path,
            generated_root=args.generated_root,
        )
    except BoardVerificationError as exc:
        print("World aid generated-board verification FAILED:", file=sys.stderr)
        for problem in exc.problems:
            print(f" - {problem}", file=sys.stderr)
        return 1
    print(json.dumps(summary.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
