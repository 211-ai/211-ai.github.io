from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "data/abby_voice/huggingface/migration-plan.json"
README_PATH = ROOT / "data/abby_voice/huggingface/README.template.md"
DOC_PATH = ROOT / "docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md"
HEAP_PATH = ROOT / "docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md"


def _plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_plan_is_explicitly_offline_and_has_no_destructive_operations() -> None:
    plan = _plan()
    policy = plan["remote_mutation"]
    assert policy["allowed"] is False
    assert policy["policy"] == "plan_only_no_remote_writes_moves_rewrites_or_deletes"
    delete = plan["dry_run_migration"]["delete_plan"]
    assert delete["operations"] == []
    assert delete["policy"] == "prohibited"
    assert delete["legacy_sources_retained"] is True
    assert any(
        step["operation"] == "delete" and step["approval"] == "prohibited"
        for step in plan["dry_run_migration"]["steps"]
    )


def test_plan_declares_five_isolated_configs_and_data_files() -> None:
    plan = _plan()
    configs = plan["dataset_yaml"]["configs"]
    names = [config["config_name"] for config in configs]
    assert names == [
        "abby_voice_response_v2",
        "abby_voice_template_v2",
        "abby_voice_audio_v2",
        "abby_voice_provenance_v2",
        "abby_voice_evaluation_v2",
    ]
    paths: list[str] = []
    for config in configs:
        assert config["schema_version"] == config["config_name"]
        assert config["data_files"]
        for data_file in config["data_files"]:
            assert data_file["path"].endswith(".parquet")
            assert config["config_name"].split("abby_voice_")[1].split("_v2")[0] in data_file["path"]
            paths.append(data_file["path"])
    assert len(paths) == len(set(paths))
    assert all(not any(token in path for token in ("manifest", "index", "batch", "run-output")) for path in paths)


def test_plan_has_reproducible_local_evidence_but_defers_remote_counts_and_costs() -> None:
    plan = _plan()
    evidence = plan["local_build_evidence"]
    assert evidence["input_record_count"] == 13809
    assert evidence["accepted_counts"]["responses"] == 13779
    assert evidence["quarantined_source_count"] == 30
    remote = plan["checksums_counts_costs"]["remote_estimates"]
    assert remote["object_count"] is None
    assert remote["total_bytes"] is None
    assert remote["estimated_storage_cost_usd"] is None
    assert remote["estimated_transfer_cost_usd"] is None
    assert "cost_formula" in remote
    assert "source_inventory_sha256" in plan["checksums_counts_costs"]["release_receipt_fields"]


def test_template_and_docs_prove_dataset_viewer_and_dry_run_safety_contract() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    docs = DOC_PATH.read_text(encoding="utf-8")
    heap = HEAP_PATH.read_text(encoding="utf-8")
    for text in (readme, docs):
        assert "configs:" in text or "five isolated Parquet configurations" in text
        assert "Dataset Viewer" in text
        assert "delete" in text.lower()
        assert "SHA-256" in text
    assert "objective-validation repair" in heap
    assert "tests/voice/test_abby_voice_hf_migration.py" in heap
    assert "list_bucket_tree" in docs
    assert "sync_bucket" in docs
    assert "upload_hf_abby_tts_dataset" in docs
