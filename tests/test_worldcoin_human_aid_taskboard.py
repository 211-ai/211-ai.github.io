from __future__ import annotations

import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_IMPLEMENTATION_PLAN.md"
HEAP_PATH = REPO_ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
RUNBOOK_PATH = REPO_ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_AGENT_SUPERVISOR_RUNBOOK.md"

REQUIRED_GOAL_FIELDS = {
    "status",
    "fib_priority",
    "priority",
    "track",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "bundle",
    "parallel_lane",
    "embedding_query",
    "ast_query",
    "interfaces",
    "submodules",
    "predicted_files",
    "conflict_policy",
    "gap_task",
    "acceptance_criteria",
    "refinement",
    "acceptance_gate",
}


def _objective_graph_api():
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_KIT_DISABLE", "1")
    package_root = str(REPO_ROOT / "ipfs_accelerate_py")
    if package_root not in sys.path:
        sys.path.insert(0, package_root)
    from ipfs_accelerate_py.agent_supervisor.objective_graph import (  # noqa: PLC0415
        ObjectiveFinding,
        objective_heap_schedule,
        parse_goal_heap,
        render_task_block,
    )

    return parse_goal_heap, objective_heap_schedule, ObjectiveFinding, render_task_block


def test_worldcoin_human_aid_heap_uses_the_supervisor_contract() -> None:
    parse_goal_heap, objective_heap_schedule, _, _ = _objective_graph_api()
    goals = parse_goal_heap(HEAP_PATH.read_text(encoding="utf-8"))

    assert len(goals) == 40
    goal_ids = [goal.goal_id for goal in goals]
    assert len(goal_ids) == len(set(goal_ids))
    assert all(re.fullmatch(r"WORLDCOIN-G\d{3}", goal_id) for goal_id in goal_ids)

    for goal in goals:
        assert REQUIRED_GOAL_FIELDS <= set(goal.fields), (
            goal.goal_id,
            sorted(REQUIRED_GOAL_FIELDS - set(goal.fields)),
        )
        assert goal.status in {
            "active",
            "provisionally_complete",
            "verified_complete",
            "analysis_inconclusive",
            "blocked",
            "reopened",
        }
        assert int(goal.fields["fib_priority"]) > 0
        assert goal.fields["validation"].strip()
        assert goal.fields["outputs"].strip()
        assert goal.fields["predicted_files"].strip()
        assert goal.fields["acceptance_criteria"].strip()
        assert goal.fields["refinement"].strip()
        assert goal.fields["acceptance_criteria"].lower() in goal.fields["refinement"].lower()
        validation = goal.fields["validation"]
        assert ";" not in validation
        assert "|| true" not in validation
        test_outputs = [
            output.strip()
            for output in goal.fields["outputs"].split(",")
            if (
                output.strip().endswith((".py", ".js", ".jsx", ".ts", ".tsx"))
                and (
                    Path(output.strip()).name.startswith("test_")
                    or ".spec." in Path(output.strip()).name
                )
            )
        ]
        assert all(Path(output).name in validation for output in test_outputs), (
            goal.goal_id,
            test_outputs,
            validation,
        )

    scheduled_ids = {record.goal_id for record in objective_heap_schedule(goals)}
    assert scheduled_ids == {goal.goal_id for goal in goals if goal.is_schedulable}
    assert len(scheduled_ids) == 38

    blocked = {goal.goal_id for goal in goals if goal.status == "blocked"}
    assert blocked == {"WORLDCOIN-G035", "WORLDCOIN-G036"}
    assert all(goal.is_terminal and not goal.is_schedulable for goal in goals if goal.goal_id in blocked)


def test_worldcoin_human_aid_goal_dependencies_exist_and_are_acyclic() -> None:
    parse_goal_heap, _, _, _ = _objective_graph_api()
    goals = parse_goal_heap(HEAP_PATH.read_text(encoding="utf-8"))
    by_id = {goal.goal_id: goal for goal in goals}

    for goal in goals:
        assert "none" not in {parent.lower() for parent in goal.parent_goal_ids}
        assert goal.goal_id not in goal.parent_goal_ids
        assert set(goal.parent_goal_ids) <= set(by_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(goal_id: str) -> None:
        if goal_id in visited:
            return
        assert goal_id not in visiting, f"parent cycle reaches {goal_id}"
        visiting.add(goal_id)
        for parent_id in by_id[goal_id].parent_goal_ids:
            visit(parent_id)
        visiting.remove(goal_id)
        visited.add(goal_id)

    for goal_id in by_id:
        visit(goal_id)

    assert "WORLDCOIN-G038" in by_id["WORLDCOIN-G006"].parent_goal_ids
    assert "WORLDCOIN-G039" in by_id["WORLDCOIN-G012"].parent_goal_ids
    assert "WORLDCOIN-G040" in by_id["WORLDCOIN-G033"].parent_goal_ids


def test_generated_worldcoin_tasks_preserve_goal_specific_acceptance() -> None:
    parse_goal_heap, _, ObjectiveFinding, render_task_block = _objective_graph_api()
    goals = parse_goal_heap(HEAP_PATH.read_text(encoding="utf-8"))

    for index, goal in enumerate(goals, start=1):
        finding = ObjectiveFinding(
            fingerprint=f"worldcoin-acceptance-{index}",
            goal_id=goal.goal_id,
            title=goal.title,
            summary=f"Implement {goal.goal_id}",
            priority=goal.fields["priority"],
            track=goal.fields["track"],
            missing_evidence=["goal-specific acceptance evidence"],
            present_evidence={},
            evidence_methods=[],
            objective_path=HEAP_PATH.relative_to(REPO_ROOT).as_posix(),
            outputs=[],
            validation=goal.fields["validation"],
            refinement=goal.fields["refinement"],
        )
        rendered = render_task_block(
            task_id=f"WORLDCOIN-AUTO-{index:03d}",
            finding=finding,
            discovery_path=Path(f"data/worldcoin_human_aid/discovery/{index:03d}.json"),
        )
        acceptance_lines = [
            line for line in rendered.splitlines() if line.startswith("- Acceptance:")
        ]

        assert len(acceptance_lines) == 1
        assert acceptance_lines[0].removeprefix("- Acceptance:").strip()
        assert goal.goal_id in acceptance_lines[0]
        assert goal.fields["acceptance_criteria"].lower() in acceptance_lines[0].lower()


def test_runbook_forces_only_schedulable_worldcoin_goals() -> None:
    parse_goal_heap, _, _, _ = _objective_graph_api()
    goals = parse_goal_heap(HEAP_PATH.read_text(encoding="utf-8"))
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    forced = set(re.findall(r"--force-goal-id (WORLDCOIN-G\d{3})", runbook))
    schedulable = {goal.goal_id for goal in goals if goal.is_schedulable}
    blocked = {goal.goal_id for goal in goals if goal.status == "blocked"}

    assert forced == schedulable
    assert not forced & blocked


def test_worldcoin_human_aid_plan_preserves_proof_and_privacy_boundaries() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8").lower()

    required_terms = (
        "optional proof-of-human",
        "siwe",
        "eip-1271",
        "simulated",
        "homelessness status",
        "manual review",
        "appeal",
        "reorg",
        "submission_ambiguous",
        "do not advertise the direct erc-20 path as anonymous",
        "postgresql",
        "localwalletrepository",
        "0x2cfc85d8e48f8eab294be644d9e25c3030863003",
        "world_aid_external_calls_enabled",
        "world_aid_wld_transfers_enabled",
    )
    for term in required_terms:
        assert term in plan

    assert "world id is optional anti-abuse evidence" in plan
    assert "it is not authentication" in plan
    assert "not the eligibility engine" in plan
    assert "must not authorize money" in plan
    assert "world chain mainnet" in plan and "`480`" in plan
    assert "raw documents" in plan and "on-chain" in plan


def test_worldcoin_human_aid_runbook_defaults_to_offline_dry_run() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    lowered = runbook.lower()

    assert "ipfs_accelerate_py.agent_supervisor.objective_daemon" in runbook
    assert "ipfs_accelerate_py.agent_supervisor.bundle_supervisor" in runbook
    assert "--task-prefix WORLDCOIN-AUTO-" in runbook
    assert "--no-reconcile-goal-completion" in runbook
    assert "--no-implement" in runbook
    assert "--once" in runbook
    assert "invalid_task_cids" in runbook
    assert "IPFS_ACCEL_SKIP_CORE=1" in runbook
    assert "IPFS_KIT_DISABLE=1" in runbook
    assert "WORLD_AID_EXTERNAL_CALLS_ENABLED=0" in runbook
    assert "WORLD_AID_WLD_TRANSFERS_ENABLED=0" in runbook
    assert "expected_blocked_goal_ids" in runbook
    assert "todo_task_cids != canonical_nodes" in runbook
    assert "bundle_task_cids != canonical_nodes" in runbook
    assert "normalized_acceptance" in runbook
    assert "excluded_bundle_keys" in runbook
    assert "g002-only.index.json" in runbook
    assert "--max-restarts 0" in runbook
    assert "--implementation-command 'codex exec --ephemeral --sandbox workspace-write" in runbook
    assert "human approval" in lowered
    assert "production" in lowered and "transfer" in lowered
