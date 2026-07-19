from __future__ import annotations

import json

from wallet_interface.hmis.adapters.file_exchange import FileExchangeHmisAdapter


def test_file_exchange_adapter_writes_deterministic_batch(tmp_path) -> None:
    adapter = FileExchangeHmisAdapter(staging_dir=tmp_path)
    payload = {"local_ref": "ref-1", "client_id": "client-1", "program_id": "program-1"}

    result = adapter.execute(action_type="submit_referral", payload=payload)
    batch_id = result.external_refs["batch_id"]
    batch_path = tmp_path / "outbound" / f"{batch_id}.json"

    assert result.ok is True
    assert batch_path.exists()
    assert json.loads(batch_path.read_text(encoding="utf-8"))["batch_id"] == batch_id
    assert adapter.staged_metadata(batch_id)["record_count"] == 1



def test_file_exchange_adapter_reconciles_fixture_imports(tmp_path) -> None:
    adapter = FileExchangeHmisAdapter(
        staging_dir=tmp_path,
        fixture_imports=[{"local_ref": "ref-1", "status": "accepted", "external_referral_id": "hmis-1"}],
    )

    result = adapter.execute(action_type="sync_referral_status", payload={"local_ref": "ref-1"})

    assert result.ok is True
    assert result.external_refs["referral_id"] == "hmis-1"
