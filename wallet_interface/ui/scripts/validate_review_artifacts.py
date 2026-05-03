#!/usr/bin/env python3
"""Validate generated Abby UI visual-review artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


UI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCREENSHOT_ROOT = "artifacts/ui-screenshots/latest"
DEFAULT_REVIEW_RESULTS = "artifacts/ui-review/latest/review-results.json"
DEFAULT_BACKLOG = "artifacts/ui-review/latest/refinement-backlog.json"
DEFAULT_PROMPT_DIR = "artifacts/ui-review/latest/agent-prompts"
DEFAULT_HEALTH_RESULTS = "artifacts/ui-review/latest/accelerate-health.json"
CURRENT_VIEWPORTS = ("desktop", "mobile")
EXPECTED_HEALTH_PROVIDERS = (
    "codex_cli",
    "copilot_cli",
    "copilot_sdk",
    "gemini_cli",
    "gemini_py",
    "claude_code",
    "claude_py",
    "hf_inference_api",
    "openai",
    "openrouter",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--screenshot-root",
        default=DEFAULT_SCREENSHOT_ROOT,
        help=f"Screenshot root relative to wallet_interface/ui. Default: {DEFAULT_SCREENSHOT_ROOT}",
    )
    parser.add_argument(
        "--review-results",
        default=DEFAULT_REVIEW_RESULTS,
        help=f"Review results JSON relative to wallet_interface/ui. Default: {DEFAULT_REVIEW_RESULTS}",
    )
    parser.add_argument(
        "--backlog",
        default=DEFAULT_BACKLOG,
        help=f"Backlog JSON relative to wallet_interface/ui. Default: {DEFAULT_BACKLOG}",
    )
    parser.add_argument(
        "--prompt-dir",
        default=DEFAULT_PROMPT_DIR,
        help=f"Prompt directory relative to wallet_interface/ui. Default: {DEFAULT_PROMPT_DIR}",
    )
    parser.add_argument(
        "--health-results",
        default=DEFAULT_HEALTH_RESULTS,
        help=f"AccelerateManager health JSON relative to wallet_interface/ui. Default: {DEFAULT_HEALTH_RESULTS}",
    )
    parser.add_argument(
        "--require-health",
        action="store_true",
        help="Require and validate AccelerateManager health results.",
    )
    return parser.parse_args()


def resolve_ui_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else UI_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON artifact: {path}")
    return json.loads(path.read_text())


def slugify(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_manifest_entries(screenshot_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for viewport in CURRENT_VIEWPORTS:
        manifest_path = screenshot_root / viewport / "manifest.json"
        manifest = read_json(manifest_path)
        screenshots = manifest.get("screenshots")
        if not isinstance(screenshots, list):
            raise ValueError(f"{manifest_path} does not contain a screenshots list")

        for entry in screenshots:
            if str(entry.get("viewport")) != viewport:
                raise ValueError(
                    f"{manifest_path} contains viewport {entry.get('viewport')!r}; expected {viewport!r}"
                )
            screenshot_path = resolve_ui_path(str(entry.get("screenshotPath", "")))
            if not screenshot_path.exists():
                raise FileNotFoundError(f"Manifest screenshot missing: {screenshot_path}")
            entries.append(entry)
    return entries


def manifest_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("viewport")),
        str(entry.get("id")),
        str(entry.get("state", "default")),
        str(entry.get("screenshotPath")),
    )


def review_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("viewport")),
        str(entry.get("routeId")),
        str(entry.get("state", "default")),
        str(entry.get("screenshotPath")),
    )


def backlog_key(task: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(task.get("viewport")),
        str(task.get("route_id")),
        str(task.get("state", "default")),
        str(task.get("screenshot_path")),
    )


def assert_unique_keys(keys: list[tuple[str, str, str, str]], label: str) -> None:
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        formatted = ", ".join(" / ".join(key) for key in duplicates)
        raise ValueError(f"Duplicate {label} entries: {formatted}")


def validate_review_results(
    review_results_path: Path, expected_entries: list[dict[str, Any]]
) -> dict[str, Any]:
    review_results = read_json(review_results_path)
    entries = review_results.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{review_results_path} does not contain an entries list")
    if len(entries) != len(expected_entries):
        raise ValueError(f"Review result count {len(entries)} does not match manifest count {len(expected_entries)}")

    expected_keys = [manifest_key(entry) for entry in expected_entries]
    actual_keys = [review_key(entry) for entry in entries]
    assert_unique_keys(expected_keys, "manifest")
    assert_unique_keys(actual_keys, "review result")

    missing = sorted(set(expected_keys) - set(actual_keys))
    if missing:
        formatted = ", ".join(" / ".join(key) for key in missing)
        raise ValueError(f"Review results missing manifest entries: {formatted}")

    stale = sorted(set(actual_keys) - set(expected_keys))
    if stale:
        formatted = ", ".join(" / ".join(key) for key in stale)
        raise ValueError(f"Review results contain stale entries: {formatted}")

    for entry in entries:
        screenshot_path = resolve_ui_path(str(entry.get("screenshotPath", "")))
        if not screenshot_path.exists():
            raise FileNotFoundError(f"Review result screenshot missing: {screenshot_path}")
    return review_results


def validate_backlog(backlog_path: Path, review_entries: list[dict[str, Any]]) -> dict[str, Any]:
    backlog = read_json(backlog_path)
    tasks = backlog.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError(f"{backlog_path} does not contain a tasks list")
    if len(tasks) != len(review_entries):
        raise ValueError(f"Backlog task count {len(tasks)} does not match review count {len(review_entries)}")

    expected_keys = [review_key(entry) for entry in review_entries]
    actual_keys = [backlog_key(task) for task in tasks]
    assert_unique_keys(actual_keys, "backlog task")

    missing = sorted(set(expected_keys) - set(actual_keys))
    if missing:
        formatted = ", ".join(" / ".join(key) for key in missing)
        raise ValueError(f"Backlog missing review entries: {formatted}")

    stale = sorted(set(actual_keys) - set(expected_keys))
    if stale:
        formatted = ", ".join(" / ".join(key) for key in stale)
        raise ValueError(f"Backlog contains stale entries: {formatted}")

    for task in tasks:
        screenshot_path = resolve_ui_path(str(task.get("screenshot_path", "")))
        if not screenshot_path.exists():
            raise FileNotFoundError(f"Backlog task screenshot missing: {screenshot_path}")
    return backlog


def validate_prompts(prompt_dir: Path, backlog: dict[str, Any]) -> None:
    if not prompt_dir.exists():
        raise FileNotFoundError(f"Missing prompt directory: {prompt_dir}")
    index_path = prompt_dir / "index.md"
    if not index_path.exists():
        raise FileNotFoundError(f"Missing prompt index: {index_path}")

    tasks = backlog.get("tasks", [])
    expected_files = {f"{slugify(str(task['task_id']))}.md" for task in tasks}
    actual_files = {path.name for path in prompt_dir.glob("*.md") if path.name != "index.md"}

    missing = sorted(expected_files - actual_files)
    if missing:
        raise FileNotFoundError(f"Missing prompt files: {', '.join(missing)}")

    stale = sorted(actual_files - expected_files)
    if stale:
        raise ValueError(f"Stale prompt files: {', '.join(stale)}")


def validate_health_results(health_results_path: Path) -> dict[str, Any]:
    health = read_json(health_results_path)
    providers = health.get("llm_router_providers")
    if not isinstance(providers, dict):
        raise ValueError(f"{health_results_path} does not contain llm_router_providers")

    missing_providers = [provider for provider in EXPECTED_HEALTH_PROVIDERS if provider not in providers]
    if missing_providers:
        raise ValueError(f"Health results missing providers: {', '.join(missing_providers)}")

    for provider_name, provider_status in providers.items():
        if not isinstance(provider_status, dict):
            raise ValueError(f"Health provider {provider_name!r} is not an object")
        status = str(provider_status.get("status", ""))
        if status not in {"ok", "unavailable", "error"}:
            raise ValueError(f"Health provider {provider_name!r} has invalid status {status!r}")

    if not bool(health.get("any_available")):
        raise ValueError("AccelerateManager health results report no available backend")

    summary = str(health.get("summary", "")).strip()
    if not summary:
        raise ValueError("AccelerateManager health results missing summary")
    return health


def main() -> int:
    args = parse_args()
    screenshot_root = resolve_ui_path(args.screenshot_root)
    review_results_path = resolve_ui_path(args.review_results)
    backlog_path = resolve_ui_path(args.backlog)
    prompt_dir = resolve_ui_path(args.prompt_dir)
    health_results_path = resolve_ui_path(args.health_results)

    manifest_entries = load_manifest_entries(screenshot_root)
    review_results = validate_review_results(review_results_path, expected_entries=manifest_entries)
    backlog = validate_backlog(backlog_path, review_entries=review_results["entries"])
    validate_prompts(prompt_dir, backlog)
    if args.require_health:
        health = validate_health_results(health_results_path)
        print(f"Validated AccelerateManager health: {health['summary']}")

    print(f"Validated {len(manifest_entries)} screenshots")
    print(f"Validated {review_results['entryCount']} review entries")
    print(f"Validated {backlog['taskCount']} backlog tasks")
    print(f"Validated {len(backlog['tasks'])} prompt files plus index.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
