from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scraper.build_service_portal_package import (
    build_service_portal_package,
    labeled_sections,
    parse_address_parts,
)


def test_labeled_sections_extracts_portal_fields():
    text = (
        "Eligibility: Ages 7-16 Hours: Varies Email (503) 661-8972 "
        "INTAKE PROCEDURE: Call or visit website for more information "
        "FEES: None DOCUMENTS: Application required LANGUAGES: English, Spanish"
    )

    sections = labeled_sections(text)
    by_field = {item["field"]: item["value"] for item in sections}

    assert by_field["eligibility"] == "Ages 7-16"
    assert by_field["hours"] == "Varies"
    assert by_field["intake_steps"] == "Call or visit website for more information"
    assert by_field["fees"] == "None"
    assert by_field["required_documents"] == "Application required"
    assert by_field["languages"] == "English, Spanish"


def test_parse_address_parts_splits_city_state_and_zip():
    parts = parse_address_parts("473 SE 194th Avenue Portland, OR 97233")

    assert parts["street"] == "473 SE 194th Avenue"
    assert parts["city"] == "Portland"
    assert parts["state"] == "OR"
    assert parts["postal_code"] == "97233"


def test_build_service_portal_package_writes_expected_outputs(tmp_path):
    package_dir = tmp_path / "retrieval_package"
    output_dir = tmp_path / "portal"
    (package_dir / "content").mkdir(parents=True)
    (package_dir / "manifest").mkdir(parents=True)

    page_doc = {
        "doc_id": "page:bafk-page",
        "doc_type": "page",
        "title": "SUMMER OVERNIGHT CAMP - 211info",
        "text": (
            "SUMMER OVERNIGHT CAMP - 211info SALVATION ARMY GRESHAM CORPS SUMMER OVERNIGHT CAMP "
            "473 SE 194th Avenue Portland, OR 97233 Eligibility: Ages 7-16 Hours: Varies "
            "Email (503) 661-8972 Phone/FAX Numbers (503) 661-8972 Main phone "
            "Email Address: camp@example.org INTAKE PROCEDURE: Call or visit website for more information "
            "FEES: $325-$425 DOCUMENTS: Application required LANGUAGES: English, Spanish "
            "TRAVEL/LOCATION INFORMATION: Located near downtown Gresham"
        ),
        "source_url": "https://gethelp.211info.org/agency/10000/15919/",
        "source_content_cid": "bafk-page",
        "source_page_cid": "bafk-page",
        "provider_name": "",
        "program_name": "",
        "categories": "",
        "host": "gethelp.211info.org",
        "city": "",
        "state": "",
        "metadata_json": json.dumps({"kind": "page"}),
    }
    service_doc = {
        "doc_id": "service:svc-1",
        "doc_type": "service",
        "title": "SUMMER OVERNIGHT CAMP",
        "text": (
            "SUMMER OVERNIGHT CAMP SALVATION ARMY GRESHAM CORPS 473 SE 194th Avenue Portland, OR 97233 "
            "Eligibility: Ages 7-16 Hours: Varies (503) 661-8972"
        ),
        "source_url": "https://gethelp.211info.org/agency/10000/15919/",
        "source_content_cid": "bafk-service",
        "source_page_cid": "bafk-page",
        "provider_name": "SALVATION ARMY GRESHAM CORPS",
        "program_name": "SUMMER OVERNIGHT CAMP",
        "categories": "camps | youth",
        "host": "gethelp.211info.org",
        "city": "Portland",
        "state": "OR",
        "metadata_json": json.dumps(
            {
                "provider_name": "SALVATION ARMY GRESHAM CORPS",
                "program_name": "SUMMER OVERNIGHT CAMP",
                "description": "Operates the Christian faith-based overnight camp.",
                "address": "473 SE 194th Avenue Portland, OR 97233",
                "phone": "(503) 661-8972",
                "email": "",
                "website": "https://provider.example.org/camp",
                "hours": "",
                "eligibility": "",
                "languages": "",
                "categories": "camps, youth",
            }
        ),
    }
    pd.DataFrame([page_doc, service_doc]).to_parquet(package_dir / "content" / "documents.parquet", index=False)
    (package_dir / "manifest" / "build_manifest.json").write_text(
        json.dumps(
            {
                "build_manifest_cid": "bafk-manifest",
                "document_count": 2,
                "service_document_count": 1,
                "page_document_count": 1,
            }
        ),
        encoding="utf-8",
    )

    manifest = build_service_portal_package(
        package_dir=package_dir,
        output_dir=output_dir,
        warehouse_path=tmp_path / "missing.duckdb",
    )

    services = pd.read_parquet(output_dir / "services.parquet")
    contacts = pd.read_parquet(output_dir / "service_contacts.parquet")
    requirements = pd.read_parquet(output_dir / "service_requirements.parquet")
    hours = pd.read_parquet(output_dir / "service_hours.parquet")

    assert manifest["service_count"] == 1
    assert (output_dir / "documents.portal.parquet").exists()
    assert (output_dir / "service_portal_manifest.json").exists()
    assert (output_dir / "extraction_manifest.json").exists()
    assert services.iloc[0]["provider_name"] == "SALVATION ARMY GRESHAM CORPS"
    assert services.iloc[0]["city"] == "Portland"
    assert contacts["contact_type"].tolist().count("phone") >= 1
    assert contacts["contact_type"].tolist().count("email") >= 1
    assert "intake_steps" in set(requirements["requirement_type"].tolist())
    assert hours.iloc[0]["hours_text"].startswith("Varies")
