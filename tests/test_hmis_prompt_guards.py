from __future__ import annotations

from pathlib import Path



def test_hmis_prompt_guards_exports_hmis_specific_redaction_helpers() -> None:
    source = Path("wallet_interface/ui/src/agent/promptGuards.ts").read_text(encoding="utf-8")
    implementation = Path("wallet_interface/ui/src/features/agent/lib/promptGuards.ts").read_text(encoding="utf-8")

    assert 'export * from "../features/agent/lib/promptGuards";' in source
    assert "hmis_linked_record" in implementation
    assert "redactHmisPromptContext" in implementation
    assert "isHmisPromptExposureAllowed" in implementation
