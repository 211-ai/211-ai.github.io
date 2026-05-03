from __future__ import annotations

import json
import types

from scraper.archive_ingest import (
    append_external_seed_urls,
    bootstrap_cloudflare_keyring,
    cdx_record_matches,
    filter_and_rank_records,
    load_shared_secrets,
    normalize_cdx_record,
    record_url,
    unique_warc_filenames,
)


def test_record_url_prefers_live_url():
    record = {
        "url": "https://www.211info.org/get-help/food",
        "archive_url": "https://web.archive.org/web/20240101000000/https://www.211info.org/get-help/food",
    }

    assert record_url(record) == "https://www.211info.org/get-help/food"


def test_record_url_can_prefer_archive_url():
    record = {
        "url": "https://www.211info.org/get-help/food",
        "archive_url": "https://web.archive.org/web/20240101000000/https://www.211info.org/get-help/food",
    }

    assert record_url(record, prefer_archive_url=True).startswith("https://web.archive.org/")


def test_append_external_seed_urls_deduplicates(tmp_path):
    state_dir = tmp_path / "state"
    count1 = append_external_seed_urls(
        state_dir,
        ["https://www.211info.org/a", "https://www.211info.org/a"],
        source="test",
    )
    count2 = append_external_seed_urls(
        state_dir,
        ["https://www.211info.org/a", "https://www.211info.org/b"],
        source="test",
    )

    lines = [
        json.loads(line)
        for line in (state_dir / "external_seed_urls.jsonl").read_text().splitlines()
    ]
    assert count1 == 1
    assert count2 == 1
    assert [line["url"] for line in lines] == [
        "https://www.211info.org/a",
        "https://www.211info.org/b",
    ]


def test_unique_warc_filenames():
    records = [
        {"warc_filename": "a.warc.gz"},
        {"warc_filename": "a.warc.gz"},
        {"warc_filename": "b.warc.gz"},
        {"warc_filename": ""},
    ]

    assert unique_warc_filenames(records) == ["a.warc.gz", "b.warc.gz"]


def test_normalize_cdx_record_maps_warc_fields():
    record = normalize_cdx_record(
        {
            "url": "https://www.211info.org/",
            "timestamp": "20260101000000",
            "filename": "crawl-data/example.warc.gz",
            "offset": "10",
            "length": "20",
        }
    )

    assert record["warc_filename"] == "crawl-data/example.warc.gz"
    assert record["warc_offset"] == "10"
    assert record["warc_length"] == "20"
    assert record["archive_url"].startswith("https://web.archive.org/web/20260101000000/")


def test_cdx_record_matches_filters_status_and_mime():
    record = {"status": "200", "mime": "text/html", "mime-detected": ""}

    assert cdx_record_matches(record, statuses={"200"}, mime_contains="html")
    assert not cdx_record_matches(record, statuses={"403"}, mime_contains="html")
    assert not cdx_record_matches(record, statuses={"200"}, mime_contains="pdf")


def test_load_shared_secrets_from_config_file(tmp_path, monkeypatch):
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps(
            {
                "CLOUDFLARE_ACCOUNT_ID": "acct-123",
                "CLOUDFLARE_API_TOKEN": "token-123",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("IPFS_DATASETS_SECRETS_FILE", str(secrets_path))

    secrets = load_shared_secrets()

    assert secrets["CLOUDFLARE_ACCOUNT_ID"] == "acct-123"
    assert secrets["CLOUDFLARE_API_TOKEN"] == "token-123"


def test_bootstrap_cloudflare_keyring_syncs_expected_aliases(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, name: str):
        return store.get((service, name))

    def set_password(service: str, name: str, value: str):
        store[(service, name)] = value

    fake_keyring = types.SimpleNamespace(
        get_password=get_password,
        set_password=set_password,
    )
    monkeypatch.setitem(__import__("sys").modules, "keyring", fake_keyring)

    result = bootstrap_cloudflare_keyring(
        secrets={
            "IPFS_DATASETS_CLOUDFLARE_ACCOUNT_ID": "acct-xyz",
            "IPFS_DATASETS_CLOUDFLARE_API_TOKEN": "token-xyz",
        }
    )

    assert result["keyring_available"] is True
    assert result["synced"] == 8
    assert store[("ipfs_datasets_py", "CLOUDFLARE_ACCOUNT_ID")] == "acct-xyz"
    assert store[("ipfs_datasets_py", "CLOUDFLARE_API_TOKEN")] == "token-xyz"
    assert store[("ipfs_datasets_py", "CLOUDFLARE_AGENT_API_KEY")] == "token-xyz"


def test_filter_and_rank_records_prefers_service_detail_urls():
    records = [
        {"url": "https://www.211info.org/", "status": "403", "mime": "text/html", "mime-detected": "", "timestamp": "20260101"},
        {"url": "https://gethelp.211info.org/get-help/food/community-meals-at-risk-youth/", "status": "200", "mime": "text/html", "mime-detected": "", "timestamp": "20250101"},
        {"url": "https://gethelp.211info.org/get-help/food/", "status": "200", "mime": "text/html", "mime-detected": "", "timestamp": "20250102"},
    ]

    ranked = filter_and_rank_records(
        records,
        url_contains=["/get-help/"],
        url_excludes=[],
        statuses={"200"},
        mime_contains="html",
        prefer_service_paths=True,
    )

    assert len(ranked) == 2
    assert "community-meals-at-risk-youth" in ranked[0]["url"]
    assert ranked[1]["url"].endswith("/get-help/food/")
