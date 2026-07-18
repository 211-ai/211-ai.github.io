from __future__ import annotations

import json
from pathlib import Path


def test_hmis_program_links_registry_has_expected_domains() -> None:
    path = Path("state/hmis/program_links.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"]
    assert {item["entity_type"] for item in payload["program_links"]} == {"program"}
    sample = payload["program_links"][0]
    assert sample["local_program_ref"]
    assert sample["external_project_id"]
    assert sample["confidence"] >= 0.5
