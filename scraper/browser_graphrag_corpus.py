from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.cluster import KMeans


DEFAULT_PACKAGE_DIR = Path("data/retrieval_package")
DEFAULT_OUTPUT_DIR = Path("wallet_interface/ui/public/corpus/211-info/current")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORTAL_PARQUET = REPO_ROOT / "data" / "portal" / "documents.portal.parquet"
DEFAULT_PORTAL_LOCATION_PARQUET = REPO_ROOT / "data" / "portal" / "service_locations.parquet"
DEFAULT_GEO_REFERENCE_DIR = REPO_ROOT / "data" / "reference" / "geo"
DEFAULT_BROWSER_EMBEDDING_MODEL_BY_PYTHON_MODEL = {
    "BAAI/bge-small-en-v1.5": "Xenova/bge-small-en-v1.5",
}
DEFAULT_GEO_CLUSTER_TARGET_SIZE = 256
DEFAULT_GEO_CLUSTER_MIN_COUNT = 8
DEFAULT_GEO_CLUSTER_MAX_COUNT = 64
DEFAULT_NON_SERVICE_ROW_GROUP_SIZE = 1024
CENSUS_PLACE_GAZETTEER_YEAR = 2025
CENSUS_PLACE_GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    f"{CENSUS_PLACE_GAZETTEER_YEAR}_Gazetteer/{CENSUS_PLACE_GAZETTEER_YEAR}_Gaz_place_national.zip"
)
CENSUS_PLACE_GAZETTEER_FILENAME = f"{CENSUS_PLACE_GAZETTEER_YEAR}_Gaz_place_national.txt"
PLACE_SUFFIX_PATTERN = re.compile(
    r"\b(?:city|town|village|borough|municipality|metro township|cdp|balance|urban county|consolidated government)\b$"
)
GEO_STOP_WORDS = {
    "and",
    "ave",
    "avenue",
    "blvd",
    "boulevard",
    "box",
    "center",
    "county",
    "court",
    "ct",
    "drive",
    "dr",
    "hwy",
    "highway",
    "lane",
    "ln",
    "loop",
    "main",
    "north",
    "northeast",
    "northwest",
    "or",
    "parkway",
    "pkwy",
    "place",
    "pl",
    "po",
    "rd",
    "road",
    "south",
    "southeast",
    "southwest",
    "st",
    "state",
    "street",
    "suite",
    "the",
    "unit",
    "west",
}
_CID_FOR_BYTES_IMPL: Any | None = None


def _bootstrap_local_ipfs_datasets() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    local_ipfs = repo_root / "ipfs_datasets_py"
    if local_ipfs.exists() and str(local_ipfs) not in sys.path:
        sys.path.insert(0, str(local_ipfs))


def _load_cid_for_bytes_impl() -> Any | None:
    global _CID_FOR_BYTES_IMPL
    if _CID_FOR_BYTES_IMPL is not None:
        return _CID_FOR_BYTES_IMPL

    local_cid_utils = REPO_ROOT / "ipfs_datasets_py" / "ipfs_datasets_py" / "utils" / "cid_utils.py"
    try:
        if local_cid_utils.exists():
            spec = importlib.util.spec_from_file_location("_ipfs_datasets_cid_utils_local", local_cid_utils)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                cid_for_bytes = getattr(module, "cid_for_bytes", None)
                if callable(cid_for_bytes):
                    _CID_FOR_BYTES_IMPL = cid_for_bytes
                    return _CID_FOR_BYTES_IMPL
        _bootstrap_local_ipfs_datasets()
        from ipfs_datasets_py.utils.cid_utils import cid_for_bytes

        _CID_FOR_BYTES_IMPL = cid_for_bytes
        return _CID_FOR_BYTES_IMPL
    except Exception:
        _CID_FOR_BYTES_IMPL = False
        return None


def cid_for_file(path: Path) -> str:
    data = path.read_bytes()
    try:
        cid_for_bytes = _load_cid_for_bytes_impl()
        if cid_for_bytes:
            return str(cid_for_bytes(data))
    except Exception:
        pass
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return file_record(path)


def write_parquet(path: Path, rows: list[dict[str, Any]], *, compression: str = "zstd") -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False, compression=compression)
    return file_record(path)


def write_clustered_documents_parquet(
    path: Path,
    documents: list[dict[str, Any]],
    *,
    service_cluster_metadata: dict[str, Any],
    non_service_row_group_size: int = DEFAULT_NON_SERVICE_ROW_GROUP_SIZE,
    compression: str = "zstd",
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not documents:
        pd.DataFrame(documents).to_parquet(path, index=False, compression=compression)
        return file_record(path)

    grouped_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    service_docs_by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    service_docs_unclustered: list[dict[str, Any]] = []
    non_service_documents: list[dict[str, Any]] = []

    for document in documents:
        if document.get("doc_type") != "service":
            non_service_documents.append(document)
            continue
        cluster_id = document.get("geo_cluster_id")
        if isinstance(cluster_id, int) and cluster_id >= 0:
            service_docs_by_cluster[cluster_id].append(document)
        else:
            service_docs_unclustered.append(document)

    cluster_rows = {
        int(cluster["clusterId"]): cluster
        for cluster in service_cluster_metadata.get("clusters", [])
        if cluster.get("kind") == "service_cluster"
    }
    cluster_order = sorted(cluster_rows)

    def sort_document_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda document: (
                str(document.get("city", "")),
                str(document.get("state", "")),
                str(document.get("provider_name", "")),
                str(document.get("program_name", "")),
                str(document.get("title", "")),
                str(document.get("doc_id", "")),
            ),
        )

    row_group_records: list[dict[str, Any]] = []
    row_group_index = 0

    for cluster_id in cluster_order:
        rows = sort_document_rows(service_docs_by_cluster.get(cluster_id, []))
        if not rows:
            continue
        grouped_rows.append(({"kind": "service_cluster", "clusterId": cluster_id}, rows))
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "service_cluster",
                "clusterId": cluster_id,
                "documentCount": len(rows),
                "serviceDocumentCount": len(rows),
            }
        )
        row_group_index += 1

    if service_docs_unclustered:
        rows = sort_document_rows(service_docs_unclustered)
        grouped_rows.append(({"kind": "service_unclustered", "clusterId": -1}, rows))
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "service_unclustered",
                "clusterId": -1,
                "documentCount": len(rows),
                "serviceDocumentCount": len(rows),
            }
        )
        row_group_index += 1

    non_service_sorted = sorted(
        non_service_documents,
        key=lambda document: (
            str(document.get("doc_type", "")),
            str(document.get("city", "")),
            str(document.get("state", "")),
            str(document.get("title", "")),
            str(document.get("doc_id", "")),
        ),
    )
    for offset in range(0, len(non_service_sorted), max(1, non_service_row_group_size)):
        rows = non_service_sorted[offset : offset + max(1, non_service_row_group_size)]
        grouped_rows.append(({"kind": "non_service", "clusterId": None}, rows))
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "non_service",
                "clusterId": None,
                "documentCount": len(rows),
                "serviceDocumentCount": 0,
            }
        )
        row_group_index += 1

    ordered_rows = [row for _, group in grouped_rows for row in group]
    schema = pa.Table.from_pandas(pd.DataFrame(ordered_rows), preserve_index=False).schema
    writer = pq.ParquetWriter(path, schema, compression=compression, use_dictionary=True)
    try:
        for _, rows in grouped_rows:
            table = pa.Table.from_pandas(pd.DataFrame(rows), schema=schema, preserve_index=False)
            writer.write_table(table)
    finally:
        writer.close()

    service_cluster_metadata["rowGroups"] = row_group_records
    service_cluster_metadata["rowGroupCount"] = len(row_group_records)
    service_cluster_metadata["nonServiceRowGroupCount"] = sum(
        1 for record in row_group_records if record["kind"] == "non_service"
    )
    service_cluster_metadata["serviceRowGroupCount"] = sum(
        1 for record in row_group_records if record["kind"] != "non_service"
    )
    return file_record(path)


def write_service_clustered_parquet(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    non_service_row_group_size: int = DEFAULT_NON_SERVICE_ROW_GROUP_SIZE,
    compression: str = "zstd",
    sort_key: Callable[[dict[str, Any]], Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not rows:
        return write_parquet(path, rows, compression=compression), []

    service_rows_by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    service_rows_unclustered: list[dict[str, Any]] = []
    non_service_rows: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("doc_type", "")) != "service":
            non_service_rows.append(row)
            continue
        cluster_id = row.get("geo_cluster_id")
        if isinstance(cluster_id, int) and cluster_id >= 0:
            service_rows_by_cluster[cluster_id].append(row)
        else:
            service_rows_unclustered.append(row)

    if sort_key is None:
        sort_key = lambda row: (str(row.get("doc_id", "")), str(row.get("source_content_cid", "")))

    grouped_rows: list[list[dict[str, Any]]] = []
    row_group_records: list[dict[str, Any]] = []
    row_group_index = 0

    for cluster_id in sorted(service_rows_by_cluster):
        cluster_rows = sorted(service_rows_by_cluster[cluster_id], key=sort_key)
        grouped_rows.append(cluster_rows)
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "service_cluster",
                "clusterId": cluster_id,
                "documentCount": len(cluster_rows),
                "serviceDocumentCount": len(cluster_rows),
            }
        )
        row_group_index += 1

    if service_rows_unclustered:
        cluster_rows = sorted(service_rows_unclustered, key=sort_key)
        grouped_rows.append(cluster_rows)
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "service_unclustered",
                "clusterId": -1,
                "documentCount": len(cluster_rows),
                "serviceDocumentCount": len(cluster_rows),
            }
        )
        row_group_index += 1

    non_service_rows = sorted(non_service_rows, key=sort_key)
    for offset in range(0, len(non_service_rows), max(1, non_service_row_group_size)):
        chunk = non_service_rows[offset : offset + max(1, non_service_row_group_size)]
        grouped_rows.append(chunk)
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "non_service",
                "clusterId": None,
                "documentCount": len(chunk),
                "serviceDocumentCount": 0,
            }
        )
        row_group_index += 1

    return write_grouped_parquet(path, grouped_rows, compression=compression), row_group_records


def write_cluster_field_grouped_parquet(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    cluster_field: str,
    unclustered_row_group_size: int = DEFAULT_NON_SERVICE_ROW_GROUP_SIZE,
    compression: str = "zstd",
    sort_key: Callable[[dict[str, Any]], Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not rows:
        return write_parquet(path, rows, compression=compression), []

    clustered_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unclustered_rows: list[dict[str, Any]] = []
    for row in rows:
        cluster_id = row.get(cluster_field)
        if isinstance(cluster_id, int) and cluster_id >= 0:
            clustered_rows[cluster_id].append(row)
        else:
            unclustered_rows.append(row)

    if sort_key is None:
        sort_key = lambda row: (
            str(row.get("community_id", "")),
            str(row.get("doc_id", "")),
            str(row.get("label", "")),
        )

    grouped_rows: list[list[dict[str, Any]]] = []
    row_group_records: list[dict[str, Any]] = []
    row_group_index = 0
    for cluster_id in sorted(clustered_rows):
        cluster_rows = sorted(clustered_rows[cluster_id], key=sort_key)
        grouped_rows.append(cluster_rows)
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "clustered",
                "clusterId": cluster_id,
                "documentCount": len(cluster_rows),
            }
        )
        row_group_index += 1

    unclustered_rows = sorted(unclustered_rows, key=sort_key)
    for offset in range(0, len(unclustered_rows), max(1, unclustered_row_group_size)):
        chunk = unclustered_rows[offset : offset + max(1, unclustered_row_group_size)]
        grouped_rows.append(chunk)
        row_group_records.append(
            {
                "rowGroupIndex": row_group_index,
                "kind": "unclustered",
                "clusterId": None,
                "documentCount": len(chunk),
            }
        )
        row_group_index += 1

    return write_grouped_parquet(path, grouped_rows, compression=compression), row_group_records


def write_grouped_parquet(
    path: Path,
    grouped_rows: list[list[dict[str, Any]]],
    *,
    compression: str = "zstd",
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = [row for group in grouped_rows for row in group]
    schema = pa.Table.from_pandas(pd.DataFrame(all_rows), preserve_index=False).schema
    writer = pq.ParquetWriter(path, schema, compression=compression, use_dictionary=True)
    try:
        for rows in grouped_rows:
            table = pa.Table.from_pandas(pd.DataFrame(rows), schema=schema, preserve_index=False)
            writer.write_table(table)
    finally:
        writer.close()
    return file_record(path)


def build_cluster_row_group_indexes(row_group_records: list[dict[str, Any]]) -> dict[str, list[int]]:
    cluster_to_row_groups: dict[str, list[int]] = defaultdict(list)
    for row_group in row_group_records:
        cluster_id = row_group.get("clusterId")
        if cluster_id in ("", None):
            continue
        cluster_to_row_groups[str(cluster_id)].append(int(row_group["rowGroupIndex"]))
    return {cluster_id: values for cluster_id, values in sorted(cluster_to_row_groups.items())}


def resolve_portal_location_parquet_path(
    portal_parquet_path: Path,
    portal_location_parquet_path: Path | None,
) -> Path:
    if portal_location_parquet_path is not None:
        return portal_location_parquet_path
    sibling_path = portal_parquet_path.with_name("service_locations.parquet")
    if sibling_path.exists():
        return sibling_path
    return DEFAULT_PORTAL_LOCATION_PARQUET


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "bytes": int(path.stat().st_size),
        "cid": cid_for_file(path),
    }


def build_content_cid_to_doc_ids(rows: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    cid_to_doc_ids: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        content_cid = str(row.get("source_content_cid", "") or "")
        doc_id = str(row.get("doc_id", "") or "")
        if not content_cid or not doc_id:
            continue
        cid_to_doc_ids[content_cid].append(doc_id)
    return {cid: sorted(set(doc_ids)) for cid, doc_ids in sorted(cid_to_doc_ids.items())}


def build_geo_cluster_centroids(geo_cluster_manifest: dict[str, Any]) -> dict[int, tuple[float, float]]:
    centroids: dict[int, tuple[float, float]] = {}
    for cluster in geo_cluster_manifest.get("clusters", []):
        cluster_id = cluster.get("clusterId")
        centroid = cluster.get("centroid") if isinstance(cluster.get("centroid"), dict) else {}
        lat = centroid.get("lat") if isinstance(centroid, dict) else None
        lon = centroid.get("lon") if isinstance(centroid, dict) else None
        if not isinstance(cluster_id, int) or cluster_id < 0 or lat is None or lon is None:
            continue
        centroids[cluster_id] = (float(lat), float(lon))
    return centroids


def nearest_geo_cluster_id(
    *,
    lat: float | None,
    lon: float | None,
    service_cluster_id: int | None,
    cluster_centroids: dict[int, tuple[float, float]],
) -> int | None:
    if lat is None or lon is None:
        return service_cluster_id if isinstance(service_cluster_id, int) and service_cluster_id >= 0 else None
    if not cluster_centroids:
        return service_cluster_id if isinstance(service_cluster_id, int) and service_cluster_id >= 0 else None

    mean_lat_radians = math.radians(sum(point[0] for point in cluster_centroids.values()) / len(cluster_centroids))
    projected_lon = lon * math.cos(mean_lat_radians)
    best_cluster_id: int | None = None
    best_distance: float | None = None
    for cluster_id, (cluster_lat, cluster_lon) in cluster_centroids.items():
        distance = ((cluster_lon * math.cos(mean_lat_radians)) - projected_lon) ** 2 + (cluster_lat - lat) ** 2
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_cluster_id = cluster_id
    return best_cluster_id


def build_service_location_artifacts(
    *,
    output_dir: Path,
    generated_dir: Path,
    portal_location_rows: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    geo_cluster_manifest: dict[str, Any],
    non_service_row_group_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    service_cluster_by_doc_id = {
        str(document.get("doc_id", "")): int(document["geo_cluster_id"])
        for document in documents
        if document.get("doc_type") == "service" and isinstance(document.get("geo_cluster_id"), int)
    }
    cluster_centroids = build_geo_cluster_centroids(geo_cluster_manifest)
    rows: list[dict[str, Any]] = []
    cluster_id_to_location_ids: dict[str, set[str]] = defaultdict(set)
    content_cid_to_location_ids: dict[str, set[str]] = defaultdict(set)
    content_cid_to_cluster_ids: dict[str, set[int]] = defaultdict(set)
    doc_id_to_location_ids: dict[str, set[str]] = defaultdict(set)
    doc_id_to_cluster_ids: dict[str, set[int]] = defaultdict(set)
    location_id_to_cluster_id: dict[str, int | None] = {}

    for row in portal_location_rows:
        service_doc_id = str(row.get("service_doc_id", "") or "")
        location_id = str(row.get("location_id", "") or "")
        source_content_cid = str(row.get("source_content_cid", "") or "")
        service_cluster_id = service_cluster_by_doc_id.get(service_doc_id)
        geo_cluster_id = nearest_geo_cluster_id(
            lat=row.get("geo_lat"),
            lon=row.get("geo_lon"),
            service_cluster_id=service_cluster_id,
            cluster_centroids=cluster_centroids,
        )
        rows.append(
            {
                **row,
                "geo_cluster_id": geo_cluster_id,
                "service_geo_cluster_id": service_cluster_id,
            }
        )
        if location_id:
            location_id_to_cluster_id[location_id] = geo_cluster_id
        if service_doc_id and location_id:
            doc_id_to_location_ids[service_doc_id].add(location_id)
        if source_content_cid and location_id:
            content_cid_to_location_ids[source_content_cid].add(location_id)
        if isinstance(geo_cluster_id, int) and geo_cluster_id >= 0:
            if location_id:
                cluster_id_to_location_ids[str(geo_cluster_id)].add(location_id)
            if source_content_cid:
                content_cid_to_cluster_ids[source_content_cid].add(geo_cluster_id)
            if service_doc_id:
                doc_id_to_cluster_ids[service_doc_id].add(geo_cluster_id)

    parquet_record, row_group_records = write_cluster_field_grouped_parquet(
        generated_dir / "service-locations.parquet",
        rows,
        cluster_field="geo_cluster_id",
        unclustered_row_group_size=non_service_row_group_size,
        sort_key=lambda row: (
            str(row.get("service_doc_id", "")),
            str(row.get("location_id", "")),
            str(row.get("source_content_cid", "")),
        ),
    )
    index_payload = {
        "schemaVersion": 1,
        "locationCount": len(rows),
        "clusteredLocationCount": sum(
            1 for row in rows if isinstance(row.get("geo_cluster_id"), int) and row["geo_cluster_id"] >= 0
        ),
        "unclusteredLocationCount": sum(
            1 for row in rows if not isinstance(row.get("geo_cluster_id"), int) or row["geo_cluster_id"] < 0
        ),
        "parquetPath": Path(parquet_record["path"]).relative_to(output_dir).as_posix(),
        "rowGroupCount": len(row_group_records),
        "clusterIdToLocationRowGroupIndexes": build_cluster_row_group_indexes(row_group_records),
        "clusterIdToLocationIds": {
            cluster_id: sorted(location_ids)
            for cluster_id, location_ids in sorted(cluster_id_to_location_ids.items())
        },
        "contentCidToLocationIds": {
            content_cid: sorted(location_ids)
            for content_cid, location_ids in sorted(content_cid_to_location_ids.items())
        },
        "contentCidToClusterIds": {
            content_cid: sorted(cluster_ids)
            for content_cid, cluster_ids in sorted(content_cid_to_cluster_ids.items())
        },
        "docIdToLocationIds": {
            doc_id: sorted(location_ids)
            for doc_id, location_ids in sorted(doc_id_to_location_ids.items())
        },
        "docIdToClusterIds": {
            doc_id: sorted(cluster_ids)
            for doc_id, cluster_ids in sorted(doc_id_to_cluster_ids.items())
        },
        "locationIdToClusterId": location_id_to_cluster_id,
    }
    index_record = write_json(generated_dir / "service-location-index.json", index_payload)
    artifact_records = [
        relative_manifest_record(output_dir, parquet_record, "geo"),
        relative_manifest_record(output_dir, index_record, "geo"),
    ]
    return index_payload, artifact_records


def compact_text(value: Any, max_chars: int) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip(), True
    return text, False


def read_manifest(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "manifest" / "build_manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def json_value(value: Any, default: Any) -> Any:
    if value in ("", None):
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(str(value))
    except Exception:
        return default
    return parsed if parsed is not None else default


def load_portal_service_details(portal_parquet_path: Path) -> dict[str, dict[str, Any]]:
    if not portal_parquet_path.exists():
        return {}

    frame = pd.read_parquet(
        portal_parquet_path,
        columns=[
            "service_doc_id",
            "phones",
            "emails",
            "websites",
            "addresses",
            "hours",
            "eligibility",
            "intake_steps",
            "required_documents",
            "fees",
            "languages",
            "accessibility",
            "travel_info",
            "area_served",
            "geo",
        ],
    ).fillna("")

    details: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        doc_id = str(row.get("service_doc_id", ""))
        if not doc_id:
            continue
        details[doc_id] = {
            "phones": json_value(row.get("phones"), []),
            "emails": json_value(row.get("emails"), []),
            "websites": json_value(row.get("websites"), []),
            "addresses": json_value(row.get("addresses"), []),
            "hours": json_value(row.get("hours"), []),
            "eligibility": json_value(row.get("eligibility"), []),
            "intake_steps": json_value(row.get("intake_steps"), []),
            "required_documents": json_value(row.get("required_documents"), []),
            "fees": json_value(row.get("fees"), []),
            "languages": json_value(row.get("languages"), []),
            "accessibility": json_value(row.get("accessibility"), []),
            "travel_info": json_value(row.get("travel_info"), []),
            "area_served": json_value(row.get("area_served"), []),
            "geo": json_value(row.get("geo"), {"lat": None, "lon": None, "precision": "none"}),
        }
    return details


def load_portal_service_locations(portal_location_parquet_path: Path) -> list[dict[str, Any]]:
    if not portal_location_parquet_path.exists():
        return []

    frame = pd.read_parquet(
        portal_location_parquet_path,
        columns=[
            "service_doc_id",
            "location_id",
            "label",
            "address",
            "street",
            "city",
            "state",
            "postal_code",
            "source_url",
            "source_content_cid",
            "source_page_cid",
            "maps_query",
            "apple_maps_url",
            "google_maps_url",
            "geo_url",
            "geo_json",
        ],
    ).fillna("")

    locations: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        geo_payload = json_value(row.get("geo_json"), {"lat": None, "lon": None, "precision": "none"})
        lat = geo_payload.get("lat") if isinstance(geo_payload, dict) else None
        lon = geo_payload.get("lon") if isinstance(geo_payload, dict) else None
        try:
            geo_lat = float(lat) if lat not in ("", None) else None
        except (TypeError, ValueError):
            geo_lat = None
        try:
            geo_lon = float(lon) if lon not in ("", None) else None
        except (TypeError, ValueError):
            geo_lon = None
        locations.append(
            {
                "service_doc_id": str(row.get("service_doc_id", "") or ""),
                "location_id": str(row.get("location_id", "") or ""),
                "label": str(row.get("label", "") or ""),
                "address": str(row.get("address", "") or ""),
                "street": str(row.get("street", "") or ""),
                "city": str(row.get("city", "") or ""),
                "state": str(row.get("state", "") or ""),
                "postal_code": str(row.get("postal_code", "") or ""),
                "source_url": str(row.get("source_url", "") or ""),
                "source_content_cid": str(row.get("source_content_cid", "") or ""),
                "source_page_cid": str(row.get("source_page_cid", "") or ""),
                "maps_query": str(row.get("maps_query", "") or ""),
                "apple_maps_url": str(row.get("apple_maps_url", "") or ""),
                "google_maps_url": str(row.get("google_maps_url", "") or ""),
                "geo_url": str(row.get("geo_url", "") or ""),
                "geo_lat": geo_lat,
                "geo_lon": geo_lon,
                "geo_precision": str(geo_payload.get("precision") or "none") if isinstance(geo_payload, dict) else "none",
            }
        )
    return locations


def load_documents(
    package_dir: Path,
    *,
    portal_service_details: dict[str, dict[str, Any]],
    max_documents: int,
    text_max_chars: int,
) -> list[dict[str, Any]]:
    frame = pd.read_parquet(package_dir / "content" / "documents.parquet")
    if max_documents > 0:
        frame = frame.head(max_documents)

    documents: list[dict[str, Any]] = []
    for row in frame.fillna("").to_dict(orient="records"):
        text, text_truncated = compact_text(row.get("text", ""), text_max_chars)
        doc_id = str(row.get("doc_id", ""))
        document = {
            "doc_id": doc_id,
            "doc_type": str(row.get("doc_type", "")),
            "title": str(row.get("title", "")),
            "text": text,
            "text_truncated": text_truncated,
            "source_url": str(row.get("source_url", "")),
            "source_content_cid": str(row.get("source_content_cid", "")),
            "source_page_cid": str(row.get("source_page_cid", "")),
            "provider_name": str(row.get("provider_name", "")),
            "program_name": str(row.get("program_name", "")),
            "categories": str(row.get("categories", "")),
            "host": str(row.get("host", "")),
            "city": str(row.get("city", "")),
            "state": str(row.get("state", "")),
            "phones": [],
            "emails": [],
            "websites": [],
            "addresses": [],
            "hours": [],
            "eligibility": [],
            "intake_steps": [],
            "required_documents": [],
            "fees": [],
            "languages": [],
            "accessibility": [],
            "travel_info": [],
            "area_served": [],
            "geo": {"lat": None, "lon": None, "precision": "none"},
        }
        if document["doc_type"] == "service":
            document.update(portal_service_details.get(doc_id, {}))
        documents.append(document)
    return documents


def normalize_geo_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def normalize_place_name(value: Any) -> str:
    normalized = normalize_geo_key(value)
    if not normalized:
        return ""
    normalized = PLACE_SUFFIX_PATTERN.sub("", normalized).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def tokenize_geo_text(value: str) -> set[str]:
    tokens = set()
    for token in normalize_geo_key(value).split():
        if len(token) < 2:
            continue
        if token in GEO_STOP_WORDS:
            continue
        if token.isdigit() and len(token) < 5:
            continue
        tokens.add(token)
    return tokens


def add_geo_term(index: dict[str, set[str]], key: Any, doc_id: str) -> None:
    normalized = normalize_geo_key(key)
    if not normalized:
        return
    index.setdefault(normalized, set()).add(doc_id)


def build_service_geo_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    docs_by_city: dict[str, set[str]] = {}
    docs_by_state: dict[str, set[str]] = {}
    docs_by_place_term: dict[str, set[str]] = {}
    geo_precision_counts: dict[str, int] = defaultdict(int)
    docs_with_address = 0
    docs_with_map_query = 0
    docs_with_coordinates = 0
    docs_with_area_served = 0
    service_count = 0

    for document in documents:
        if document.get("doc_type") != "service":
            continue
        service_count += 1
        doc_id = str(document.get("doc_id", ""))
        geo = document.get("geo") if isinstance(document.get("geo"), dict) else {}
        precision = str((geo or {}).get("precision") or "none")
        geo_precision_counts[precision] += 1
        if (geo or {}).get("lat") is not None and (geo or {}).get("lon") is not None:
            docs_with_coordinates += 1

        place_text_parts = [
            str(document.get("city", "")),
            str(document.get("state", "")),
            str(document.get("categories", "")),
        ]
        add_geo_term(docs_by_city, document.get("city"), doc_id)
        add_geo_term(docs_by_state, document.get("state"), doc_id)

        addresses = document.get("addresses") if isinstance(document.get("addresses"), list) else []
        if addresses:
            docs_with_address += 1
        seen_map_query = False
        for address in addresses:
            if not isinstance(address, dict):
                continue
            add_geo_term(docs_by_city, address.get("city"), doc_id)
            add_geo_term(docs_by_state, address.get("state"), doc_id)
            place_text_parts.extend(
                [
                    str(address.get("city", "")),
                    str(address.get("state", "")),
                    str(address.get("maps_query", "")),
                ]
            )
            if address.get("maps_query"):
                seen_map_query = True
        if seen_map_query:
            docs_with_map_query += 1

        area_served = document.get("area_served") if isinstance(document.get("area_served"), list) else []
        if area_served:
            docs_with_area_served += 1
        for item in area_served:
            if isinstance(item, dict):
                place_text_parts.append(str(item.get("value", "")))

        travel_info = document.get("travel_info") if isinstance(document.get("travel_info"), list) else []
        for item in travel_info:
            if isinstance(item, dict):
                place_text_parts.append(str(item.get("value", "")))

        for term in tokenize_geo_text(" ".join(part for part in place_text_parts if part)):
            docs_by_place_term.setdefault(term, set()).add(doc_id)

    return {
        "schemaVersion": 1,
        "serviceCount": service_count,
        "docsWithAddress": docs_with_address,
        "docsWithMapQuery": docs_with_map_query,
        "docsWithCoordinates": docs_with_coordinates,
        "docsWithAreaServed": docs_with_area_served,
        "geoPrecisionCounts": dict(sorted(geo_precision_counts.items())),
        "docsByCity": {key: sorted(value) for key, value in sorted(docs_by_city.items())},
        "docsByState": {key: sorted(value) for key, value in sorted(docs_by_state.items())},
        "docsByPlaceTerm": {key: sorted(value) for key, value in sorted(docs_by_place_term.items())},
    }


def load_place_centroids(
    *,
    reference_dir: Path = DEFAULT_GEO_REFERENCE_DIR,
    place_centroid_path: Path | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    if place_centroid_path is None:
        place_centroid_path = ensure_census_place_gazetteer(reference_dir)
    centroid_records: dict[tuple[str, str], dict[str, Any]] = {}
    for line in place_centroid_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("USPS|"):
            continue
        parts = line.split("|")
        if len(parts) < 13:
            continue
        state = normalize_geo_key(parts[0])
        name = normalize_place_name(parts[4])
        if not state or not name:
            continue
        try:
            lat = float(parts[11])
            lon = float(parts[12])
        except ValueError:
            continue
        land_area = float(parts[8] or 0.0)
        funcstat = parts[6]
        priority = (1 if funcstat == "A" else 0, land_area)
        key = (state, name)
        current = centroid_records.get(key)
        if current is None or priority > current["priority"]:
            centroid_records[key] = {
                "state": parts[0],
                "name": parts[4],
                "lat": lat,
                "lon": lon,
                "priority": priority,
            }
    return centroid_records


def ensure_census_place_gazetteer(reference_dir: Path) -> Path:
    reference_dir.mkdir(parents=True, exist_ok=True)
    txt_path = reference_dir / CENSUS_PLACE_GAZETTEER_FILENAME
    if txt_path.exists():
        return txt_path
    zip_path = reference_dir / f"{CENSUS_PLACE_GAZETTEER_YEAR}_Gaz_place_national.zip"
    if not zip_path.exists():
        urlretrieve(CENSUS_PLACE_GAZETTEER_URL, zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        member = next((name for name in archive.namelist() if name.endswith(".txt")), "")
        if not member:
            raise FileNotFoundError(f"no gazetteer text file found in {zip_path}")
        archive.extract(member, reference_dir)
        extracted = reference_dir / member
        if extracted != txt_path:
            extracted.replace(txt_path)
    return txt_path


def first_non_empty_text(values: Iterable[Any]) -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def iter_service_locality_candidates(document: dict[str, Any]) -> Iterable[tuple[str, str]]:
    addresses = document.get("addresses") if isinstance(document.get("addresses"), list) else []
    for address in addresses:
        if not isinstance(address, dict):
            continue
        city = first_non_empty_text([address.get("city")])
        state = first_non_empty_text([address.get("state")])
        if city and state:
            yield (city, state)

    document_city = first_non_empty_text([document.get("city")])
    document_state = first_non_empty_text([document.get("state")])
    if document_city and document_state:
        yield (document_city, document_state)

    area_served = document.get("area_served") if isinstance(document.get("area_served"), list) else []
    for value in area_served:
        if not isinstance(value, dict):
            continue
        text = str(value.get("value", "")).strip()
        match = re.match(r"^\s*([^,]+),\s*([A-Z]{2})\s*$", text)
        if match:
            yield (match.group(1), match.group(2))


def coerce_service_geo_point(document: dict[str, Any], place_centroids: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    existing_geo = document.get("geo") if isinstance(document.get("geo"), dict) else {}
    existing_lat = existing_geo.get("lat")
    existing_lon = existing_geo.get("lon")
    if existing_lat is not None and existing_lon is not None:
        return {
            "lat": float(existing_lat),
            "lon": float(existing_lon),
            "precision": str(existing_geo.get("precision") or "service"),
            "source": str(existing_geo.get("source") or "service"),
            "place": str(existing_geo.get("place") or ""),
            "state": str(existing_geo.get("state") or ""),
        }

    addresses = document.get("addresses") if isinstance(document.get("addresses"), list) else []
    for address in addresses:
        if not isinstance(address, dict):
            continue
        address_geo = address.get("geo") if isinstance(address.get("geo"), dict) else {}
        address_lat = address_geo.get("lat")
        address_lon = address_geo.get("lon")
        if address_lat is None or address_lon is None:
            continue
        return {
            "lat": float(address_lat),
            "lon": float(address_lon),
            "precision": str(address_geo.get("precision") or "address_geocode"),
            "source": str(address_geo.get("source") or "address"),
            "place": first_non_empty_text([address.get("city"), document.get("city")]),
            "state": first_non_empty_text([address.get("state"), document.get("state")]),
        }

    for city, state in iter_service_locality_candidates(document):
        key = (normalize_geo_key(state), normalize_place_name(city))
        match = place_centroids.get(key)
        if not match:
            continue
        return {
            "lat": float(match["lat"]),
            "lon": float(match["lon"]),
            "precision": "place_centroid",
            "source": "census_gazetteer",
            "place": city,
            "state": state,
        }

    return {
        "lat": None,
        "lon": None,
        "precision": str(existing_geo.get("precision") or "none"),
        "source": str(existing_geo.get("source") or ""),
        "place": "",
        "state": "",
    }


def choose_geo_cluster_count(
    point_count: int,
    *,
    requested_cluster_count: int = 0,
    target_cluster_size: int = DEFAULT_GEO_CLUSTER_TARGET_SIZE,
) -> int:
    if point_count <= 1:
        return point_count
    if requested_cluster_count > 0:
        return max(1, min(requested_cluster_count, point_count))
    auto_count = int(math.ceil(point_count / max(1, target_cluster_size)))
    return max(DEFAULT_GEO_CLUSTER_MIN_COUNT, min(DEFAULT_GEO_CLUSTER_MAX_COUNT, auto_count, point_count))


def cluster_service_documents(
    documents: list[dict[str, Any]],
    *,
    reference_dir: Path = DEFAULT_GEO_REFERENCE_DIR,
    place_centroid_path: Path | None = None,
    target_cluster_size: int = DEFAULT_GEO_CLUSTER_TARGET_SIZE,
    cluster_count: int = 0,
) -> dict[str, Any]:
    place_centroids = load_place_centroids(reference_dir=reference_dir, place_centroid_path=place_centroid_path)
    service_documents = [document for document in documents if document.get("doc_type") == "service"]
    located_documents: list[dict[str, Any]] = []
    feature_rows: list[tuple[float, float]] = []

    for document in service_documents:
        geo_point = coerce_service_geo_point(document, place_centroids)
        document["geo"] = geo_point
        lat = geo_point.get("lat")
        lon = geo_point.get("lon")
        document["geo_lat"] = float(lat) if lat is not None else None
        document["geo_lon"] = float(lon) if lon is not None else None
        document["geo_precision"] = str(geo_point.get("precision") or "none")
        document["geo_cluster_id"] = None
        if lat is None or lon is None:
            continue
        located_documents.append(document)
        feature_rows.append((float(lat), float(lon)))

    for document in documents:
        if document.get("doc_type") != "service":
            document["geo_lat"] = None
            document["geo_lon"] = None
            document["geo_precision"] = ""
            document["geo_cluster_id"] = None

    if not located_documents:
        return {
            "schemaVersion": 1,
            "centroidSource": {
                "kind": "census_place_gazetteer",
                "year": CENSUS_PLACE_GAZETTEER_YEAR,
                "url": CENSUS_PLACE_GAZETTEER_URL,
                "path": str(place_centroid_path or ensure_census_place_gazetteer(reference_dir)),
            },
            "serviceDocumentCount": len(service_documents),
            "clusteredServiceCount": 0,
            "unclusteredServiceCount": len(service_documents),
            "clusterCount": 0,
            "clusters": [],
            "serviceDocIdToClusterId": {},
        }

    points = np.array(feature_rows, dtype=np.float64)
    mean_lat_radians = math.radians(float(points[:, 0].mean()))
    projected = np.column_stack((points[:, 1] * math.cos(mean_lat_radians), points[:, 0]))
    effective_cluster_count = choose_geo_cluster_count(
        len(located_documents),
        requested_cluster_count=cluster_count,
        target_cluster_size=target_cluster_size,
    )
    kmeans = KMeans(n_clusters=effective_cluster_count, n_init=10, random_state=42)
    labels = kmeans.fit_predict(projected)

    clusters: list[dict[str, Any]] = []
    doc_id_to_cluster: dict[str, int] = {}
    cluster_member_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for label, document in zip(labels.tolist(), located_documents):
        cluster_id = int(label)
        document["geo_cluster_id"] = cluster_id
        doc_id_to_cluster[str(document.get("doc_id", ""))] = cluster_id
        cluster_member_rows[cluster_id].append(document)

    for cluster_id in sorted(cluster_member_rows):
        rows = cluster_member_rows[cluster_id]
        latitudes = [float(row["geo_lat"]) for row in rows if row.get("geo_lat") is not None]
        longitudes = [float(row["geo_lon"]) for row in rows if row.get("geo_lon") is not None]
        city_counts: dict[str, int] = defaultdict(int)
        state_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            address_cities = [
                address.get("city")
                for address in row.get("addresses", [])
                if isinstance(address, dict)
            ]
            address_states = [
                address.get("state")
                for address in row.get("addresses", [])
                if isinstance(address, dict)
            ]
            city = first_non_empty_text(
                [
                    row.get("city"),
                    *address_cities,
                ]
            )
            state = first_non_empty_text(
                [
                    row.get("state"),
                    *address_states,
                ]
            )
            if city:
                city_counts[city] += 1
            if state:
                state_counts[state] += 1
        clusters.append(
            {
                "clusterId": cluster_id,
                "kind": "service_cluster",
                "serviceDocumentCount": len(rows),
                "documentCount": len(rows),
                "centroid": {
                    "lat": round(float(sum(latitudes) / len(latitudes)), 6) if latitudes else None,
                    "lon": round(float(sum(longitudes) / len(longitudes)), 6) if longitudes else None,
                },
                "bounds": {
                    "minLat": round(float(min(latitudes)), 6) if latitudes else None,
                    "maxLat": round(float(max(latitudes)), 6) if latitudes else None,
                    "minLon": round(float(min(longitudes)), 6) if longitudes else None,
                    "maxLon": round(float(max(longitudes)), 6) if longitudes else None,
                },
                "topCities": [
                    {"name": name, "count": count}
                    for name, count in sorted(city_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
                ],
                "topStates": [
                    {"name": name, "count": count}
                    for name, count in sorted(state_counts.items(), key=lambda item: (-item[1], item[0]))[:4]
                ],
            }
        )

    unclustered_service_count = len(service_documents) - len(located_documents)
    if unclustered_service_count > 0:
        clusters.append(
            {
                "clusterId": -1,
                "kind": "service_unclustered",
                "serviceDocumentCount": unclustered_service_count,
                "documentCount": unclustered_service_count,
                "centroid": {"lat": None, "lon": None},
                "bounds": {"minLat": None, "maxLat": None, "minLon": None, "maxLon": None},
                "topCities": [],
                "topStates": [],
            }
        )

    return {
        "schemaVersion": 1,
        "centroidSource": {
            "kind": "census_place_gazetteer",
            "year": CENSUS_PLACE_GAZETTEER_YEAR,
            "url": CENSUS_PLACE_GAZETTEER_URL,
            "path": str(place_centroid_path or ensure_census_place_gazetteer(reference_dir)),
        },
        "serviceDocumentCount": len(service_documents),
        "clusteredServiceCount": len(located_documents),
        "unclusteredServiceCount": unclustered_service_count,
        "clusterCount": effective_cluster_count,
        "clusters": clusters,
        "serviceDocIdToClusterId": doc_id_to_cluster,
    }


def build_document_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "count": len(documents),
        "docIdToIndex": {document["doc_id"]: index for index, document in enumerate(documents)},
        "contentCidToIndex": {
            document["source_content_cid"]: index
            for index, document in enumerate(documents)
            if document.get("source_content_cid")
        },
        "contentCidToDocIds": build_content_cid_to_doc_ids(documents),
    }


def build_bm25_payload(
    package_dir: Path,
    *,
    selected_doc_ids: set[str],
    max_terms_per_document: int,
    doc_frame: pd.DataFrame | None = None,
    term_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    doc_frame = (doc_frame.copy() if doc_frame is not None else pd.read_parquet(package_dir / "retrieval" / "bm25_documents.parquet")).fillna("")
    if selected_doc_ids:
        doc_frame = doc_frame[doc_frame["doc_id"].isin(selected_doc_ids)]

    term_frame = (term_frame.copy() if term_frame is not None else pd.read_parquet(package_dir / "retrieval" / "bm25_terms.parquet")).fillna("")
    if selected_doc_ids:
        term_frame = term_frame[term_frame["doc_id"].isin(selected_doc_ids)]

    if term_frame.empty:
        document_frequency: dict[str, int] = {}
        documents = [
            {
                "doc_id": str(row["doc_id"]),
                "doc_type": str(row.get("doc_type", "")),
                "source_content_cid": str(row.get("source_content_cid", "")),
                "source_page_cid": str(row.get("source_page_cid", "")),
                "document_length": int(row.get("doc_length") or 0),
                "terms": {},
            }
            for row in doc_frame.to_dict(orient="records")
        ]
        avgdl = 0.0
        document_count = len(documents)
    else:
        term_frame = term_frame.assign(score=term_frame["tf"].astype(float) * term_frame["idf"].astype(float))
        term_frame = term_frame.sort_values(["doc_id", "score", "idf", "tf", "term"], ascending=[True, False, False, False, True])
        if max_terms_per_document > 0:
            term_frame = term_frame.groupby("doc_id", sort=False).head(max_terms_per_document)

        term_rows_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        document_frequency: dict[str, int] = {}
        for row in term_frame.to_dict(orient="records"):
            term = str(row.get("term", ""))
            if not term:
                continue
            document_frequency[term] = max(document_frequency.get(term, 0), int(row.get("df") or 0))
            term_rows_by_doc[str(row.get("doc_id", ""))].append(
                {
                    "term": term,
                    "tf": float(row.get("tf") or 0.0),
                    "idf": float(row.get("idf") or 0.0),
                }
            )

        documents = []
        for row in doc_frame.to_dict(orient="records"):
            doc_id = str(row.get("doc_id", ""))
            documents.append(
                {
                    "doc_id": doc_id,
                    "doc_type": str(row.get("doc_type", "")),
                    "source_url": str(row.get("source_url", "")),
                    "source_content_cid": str(row.get("source_content_cid", "")),
                    "source_page_cid": str(row.get("source_page_cid", "")),
                    "document_length": int(row.get("doc_length") or 0),
                    "terms": {
                        term_row["term"]: term_row["tf"]
                        for term_row in term_rows_by_doc.get(doc_id, [])
                    },
                    "term_idf": {
                        term_row["term"]: term_row["idf"]
                        for term_row in term_rows_by_doc.get(doc_id, [])
                    },
                }
            )
        avgdl = float(term_frame["avg_doc_length"].iloc[0]) if "avg_doc_length" in term_frame and len(term_frame) else 0.0
        document_count = int(term_frame["document_count"].iloc[0]) if "document_count" in term_frame and len(term_frame) else len(documents)

    return {
        "schemaVersion": 1,
        "documents": documents,
        "documentFrequency": document_frequency,
        "k1": 1.5,
        "b": 0.75,
        "avgdl": avgdl,
        "documentCount": document_count,
        "maxTermsPerDocument": max_terms_per_document,
        "sourceContentCidToDocIds": build_content_cid_to_doc_ids(documents),
    }


def write_embeddings(
    package_dir: Path,
    output_path: Path,
    *,
    selected_doc_ids: set[str],
    frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    frame = (frame.copy() if frame is not None else pd.read_parquet(package_dir / "retrieval" / "vector_embeddings.parquet")).fillna("")
    if selected_doc_ids:
        frame = frame[frame["doc_id"].isin(selected_doc_ids)]

    vectors: list[list[float]] = []
    doc_ids: list[str] = []
    content_cids: list[str] = []
    page_cids: list[str] = []
    source_urls: list[str] = []
    model_name = ""
    dimension = 0

    for row in frame.to_dict(orient="records"):
        embedding = row.get("embedding")
        if embedding is None:
            values = []
        else:
            values = [float(value) for value in embedding]
        if not values:
            continue
        if dimension and len(values) != dimension:
            raise ValueError(f"embedding dimension mismatch for {row.get('doc_id')}")
        dimension = len(values)
        vectors.append(values)
        doc_ids.append(str(row.get("doc_id", "")))
        content_cids.append(str(row.get("source_content_cid", "")))
        page_cids.append(str(row.get("source_page_cid", "")))
        source_urls.append(str(row.get("source_url", "")))
        model_name = model_name or str(row.get("embedding_model", ""))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        for vector in vectors:
            handle.write(struct.pack(f"<{dimension}f", *vector))

    index = {
        "schemaVersion": 1,
        "count": len(vectors),
        "dimension": dimension,
        "embeddingModel": model_name,
        "browserEmbeddingModel": DEFAULT_BROWSER_EMBEDDING_MODEL_BY_PYTHON_MODEL.get(model_name, ""),
        "binary": output_path.name,
        "doc_ids": doc_ids,
        "source_content_cids": content_cids,
        "source_page_cids": page_cids,
        "source_urls": source_urls,
        "sourceContentCidToDocIds": build_content_cid_to_doc_ids(
            [
                {
                    "doc_id": doc_id,
                    "source_content_cid": content_cid,
                }
                for doc_id, content_cid in zip(doc_ids, content_cids)
            ]
        ),
    }
    return index


def build_retrieval_geo_shard_artifacts(
    *,
    package_dir: Path,
    output_dir: Path,
    generated_dir: Path,
    documents: list[dict[str, Any]],
    geo_cluster_manifest: dict[str, Any],
    max_terms_per_document: int,
    bm25_doc_frame: pd.DataFrame,
    bm25_term_frame: pd.DataFrame,
    embedding_frame: pd.DataFrame,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    shard_dir = generated_dir / "retrieval-geo-shards"
    shard_dir.mkdir(parents=True, exist_ok=True)
    for stale_path in shard_dir.glob("*"):
        if stale_path.is_file():
            stale_path.unlink()

    service_documents = [document for document in documents if document.get("doc_type") == "service"]
    service_docs_by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    service_docs_unclustered: list[dict[str, Any]] = []
    for document in service_documents:
        cluster_id = document.get("geo_cluster_id")
        if isinstance(cluster_id, int) and cluster_id >= 0:
            service_docs_by_cluster[cluster_id].append(document)
        else:
            service_docs_unclustered.append(document)

    shard_records: list[dict[str, Any]] = []
    artifact_records: list[dict[str, Any]] = []
    doc_id_to_shard_id: dict[str, str] = {}
    content_cid_to_shard_ids: dict[str, set[str]] = defaultdict(set)
    cluster_id_to_shard_id: dict[str, str] = {}
    embedding_model = ""
    embedding_dimension = 0
    selected_doc_ids = {str(document.get("doc_id", "")) for document in documents if document.get("doc_id")}
    documents_by_id = {
        str(document.get("doc_id", "")): document
        for document in documents
        if document.get("doc_id")
    }

    full_bm25_payload = build_bm25_payload(
        package_dir,
        selected_doc_ids=selected_doc_ids,
        max_terms_per_document=max_terms_per_document,
        doc_frame=bm25_doc_frame,
        term_frame=bm25_term_frame,
    )
    bm25_rows = build_bm25_parquet_rows(full_bm25_payload, documents_by_id)
    bm25_parquet_record, bm25_row_groups = write_service_clustered_parquet(
        generated_dir / "bm25-documents.parquet",
        bm25_rows,
        sort_key=lambda row: (str(row.get("doc_id", "")), str(row.get("source_content_cid", ""))),
    )
    artifact_records.append(relative_manifest_record(output_dir, bm25_parquet_record, "retrieval"))
    cluster_id_to_bm25_row_groups = build_cluster_row_group_indexes(bm25_row_groups)

    embedding_rows = build_embedding_parquet_rows(
        frame=embedding_frame,
        selected_doc_ids=selected_doc_ids,
        documents_by_id=documents_by_id,
    )
    embedding_parquet_record, embedding_row_groups = write_service_clustered_parquet(
        generated_dir / "embeddings.parquet",
        embedding_rows,
        sort_key=lambda row: (str(row.get("doc_id", "")), str(row.get("source_content_cid", ""))),
    )
    artifact_records.append(relative_manifest_record(output_dir, embedding_parquet_record, "retrieval"))
    cluster_id_to_embedding_row_groups = build_cluster_row_group_indexes(embedding_row_groups)

    for cluster in geo_cluster_manifest.get("clusters", []):
        kind = str(cluster.get("kind") or "")
        raw_cluster_id = cluster.get("clusterId")
        cluster_id = int(raw_cluster_id) if raw_cluster_id not in ("", None) else -1
        if kind not in {"service_cluster", "service_unclustered"}:
            continue
        shard_documents = (
            sorted(service_docs_by_cluster.get(cluster_id, []), key=lambda document: str(document.get("doc_id", "")))
            if kind == "service_cluster"
            else sorted(service_docs_unclustered, key=lambda document: str(document.get("doc_id", "")))
        )
        if not shard_documents:
            continue

        shard_id = f"cluster-{cluster_id:04d}" if cluster_id >= 0 else "cluster-unclustered"
        cluster_id_to_shard_id[str(cluster_id)] = shard_id
        selected_doc_ids = {str(document.get("doc_id", "")) for document in shard_documents}
        bm25_payload = build_bm25_payload(
            package_dir,
            selected_doc_ids=selected_doc_ids,
            max_terms_per_document=max_terms_per_document,
            doc_frame=bm25_doc_frame,
            term_frame=bm25_term_frame,
        )
        bm25_record = write_json(shard_dir / f"bm25-{shard_id}.json", bm25_payload)
        artifact_records.append(relative_manifest_record(output_dir, bm25_record, "retrieval"))

        embedding_binary_path = shard_dir / f"embeddings-{shard_id}.f32"
        embedding_index = write_embeddings(
            package_dir,
            embedding_binary_path,
            selected_doc_ids=selected_doc_ids,
            frame=embedding_frame,
        )
        embedding_model = embedding_model or str(embedding_index.get("embeddingModel") or "")
        embedding_dimension = embedding_dimension or int(embedding_index.get("dimension") or 0)
        embedding_binary_record = file_record(embedding_binary_path)
        artifact_records.append(relative_manifest_record(output_dir, embedding_binary_record, "retrieval"))
        embedding_index_record = write_json(shard_dir / f"embedding-index-{shard_id}.json", embedding_index)
        artifact_records.append(relative_manifest_record(output_dir, embedding_index_record, "retrieval"))

        for document in shard_documents:
            doc_id = str(document.get("doc_id", ""))
            if doc_id:
                doc_id_to_shard_id[doc_id] = shard_id
            content_cid = str(document.get("source_content_cid", "") or "")
            if content_cid:
                content_cid_to_shard_ids[content_cid].add(shard_id)

        shard_records.append(
            {
                "shardId": shard_id,
                "clusterId": cluster_id,
                "kind": kind,
                "documentCount": len(shard_documents),
                "serviceDocumentCount": len(shard_documents),
                "contentCidCount": len(
                    {
                        str(document.get("source_content_cid", ""))
                        for document in shard_documents
                        if document.get("source_content_cid")
                    }
                ),
                "firstDocId": str(shard_documents[0].get("doc_id", "")),
                "lastDocId": str(shard_documents[-1].get("doc_id", "")),
                "bm25Path": Path(bm25_record["path"]).relative_to(output_dir).as_posix(),
                "embeddingIndexPath": Path(embedding_index_record["path"]).relative_to(output_dir).as_posix(),
                "embeddingBinaryPath": Path(embedding_binary_record["path"]).relative_to(output_dir).as_posix(),
                "bm25ParquetPath": Path(bm25_parquet_record["path"]).relative_to(output_dir).as_posix(),
                "embeddingParquetPath": Path(embedding_parquet_record["path"]).relative_to(output_dir).as_posix(),
                "bm25RowGroupIndexes": cluster_id_to_bm25_row_groups.get(str(cluster_id), []),
                "embeddingRowGroupIndexes": cluster_id_to_embedding_row_groups.get(str(cluster_id), []),
                "sourceContentCidToDocIds": build_content_cid_to_doc_ids(shard_documents),
            }
        )

    manifest = {
        "schemaVersion": 1,
        "serviceDocumentCount": len(service_documents),
        "clusteredServiceCount": int(geo_cluster_manifest.get("clusteredServiceCount") or 0),
        "unclusteredServiceCount": int(geo_cluster_manifest.get("unclusteredServiceCount") or 0),
        "embeddingModel": embedding_model,
        "embeddingDimension": embedding_dimension,
        "bm25ParquetPath": Path(bm25_parquet_record["path"]).relative_to(output_dir).as_posix(),
        "embeddingParquetPath": Path(embedding_parquet_record["path"]).relative_to(output_dir).as_posix(),
        "bm25RowGroupCount": len(bm25_row_groups),
        "embeddingRowGroupCount": len(embedding_row_groups),
        "clusterIdToBm25RowGroupIndexes": cluster_id_to_bm25_row_groups,
        "clusterIdToEmbeddingRowGroupIndexes": cluster_id_to_embedding_row_groups,
        "shardCount": len(shard_records),
        "shards": shard_records,
        "clusterIdToShardId": cluster_id_to_shard_id,
        "docIdToShardId": dict(sorted(doc_id_to_shard_id.items())),
        "contentCidToShardIds": {
            content_cid: sorted(shard_ids)
            for content_cid, shard_ids in sorted(content_cid_to_shard_ids.items())
        },
    }
    manifest_record = write_json(generated_dir / "retrieval-geo-shards.json", manifest)
    artifact_records.insert(0, relative_manifest_record(output_dir, manifest_record, "retrieval"))
    return manifest, artifact_records


def build_bm25_parquet_rows(
    bm25_payload: dict[str, Any],
    documents_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for document in bm25_payload.get("documents", []):
        doc_id = str(document.get("doc_id", ""))
        source_document = documents_by_id.get(doc_id, {})
        geo_cluster_id = source_document.get("geo_cluster_id")
        rows.append(
            {
                "doc_id": doc_id,
                "doc_type": str(document.get("doc_type", "")),
                "source_url": str(document.get("source_url", "")),
                "source_content_cid": str(document.get("source_content_cid", "")),
                "source_page_cid": str(document.get("source_page_cid", "")),
                "document_length": int(document.get("document_length") or 0),
                "terms_json": json.dumps(document.get("terms") or {}, separators=(",", ":")),
                "term_idf_json": json.dumps(document.get("term_idf") or {}, separators=(",", ":")),
                "geo_cluster_id": int(geo_cluster_id) if isinstance(geo_cluster_id, int) else None,
                "k1": float(bm25_payload.get("k1") or 0.0),
                "b": float(bm25_payload.get("b") or 0.0),
                "avgdl": float(bm25_payload.get("avgdl") or 0.0),
                "document_count": int(bm25_payload.get("documentCount") or 0),
                "max_terms_per_document": int(bm25_payload.get("maxTermsPerDocument") or 0),
            }
        )
    return rows


def build_embedding_parquet_rows(
    *,
    frame: pd.DataFrame,
    selected_doc_ids: set[str],
    documents_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    filtered_frame = frame.fillna("")
    if selected_doc_ids:
        filtered_frame = filtered_frame[filtered_frame["doc_id"].isin(selected_doc_ids)]

    for row in filtered_frame.to_dict(orient="records"):
        doc_id = str(row.get("doc_id", ""))
        embedding = row.get("embedding")
        values = [float(value) for value in embedding] if embedding is not None and len(embedding) else []
        if not values:
            continue
        source_document = documents_by_id.get(doc_id, {})
        geo_cluster_id = source_document.get("geo_cluster_id")
        embedding_model = str(row.get("embedding_model", ""))
        rows.append(
            {
                "doc_id": doc_id,
                "doc_type": str(row.get("doc_type", "")),
                "source_url": str(row.get("source_url", "")),
                "source_content_cid": str(row.get("source_content_cid", "")),
                "source_page_cid": str(row.get("source_page_cid", "")),
                "embedding_model": embedding_model,
                "browser_embedding_model": DEFAULT_BROWSER_EMBEDDING_MODEL_BY_PYTHON_MODEL.get(embedding_model, ""),
                "dimension": len(values),
                "embedding": values,
                "geo_cluster_id": int(geo_cluster_id) if isinstance(geo_cluster_id, int) else None,
            }
        )
    return rows


def compact_node(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key, "")
        for key in [
            "node_id",
            "node_type",
            "label",
            "node_cid",
            "source_url",
            "source_content_cid",
            "source_page_cid",
            "provider_name",
            "program_name",
            "categories",
            "city",
            "state",
            "category",
            "term",
        ]
        if row.get(key, "") not in ("", None) or key in {"node_id", "node_type", "label"}
    }


def compact_edge(row: dict[str, Any]) -> dict[str, Any]:
    edge = {
        "source": str(row.get("source", "")),
        "target": str(row.get("target", "")),
        "relation": str(row.get("relation", "")),
        "edge_cid": str(row.get("edge_cid", "")),
    }
    for key in ["bm25_score", "tf", "idf", "shared_document_count", "cooccurrence_score"]:
        value = row.get(key)
        if value not in ("", None) and not (isinstance(value, float) and math.isnan(value)):
            edge[key] = float(value)
    if row.get("source_content_cid"):
        edge["source_content_cid"] = str(row["source_content_cid"])
    return edge


def edge_priority(edge: dict[str, Any]) -> tuple[int, float]:
    relation = str(edge.get("relation", ""))
    priority = {
        "HAS_KEYTERM": 100,
        "IN_CATEGORY": 90,
        "LOCATED_IN": 85,
        "PROVIDES_SERVICE": 80,
        "HAS_PROGRAM": 75,
        "DERIVED_FROM_PAGE": 70,
        "HAS_DOCUMENT": 60,
        "LINKS_TO": 40,
        "CO_OCCURS_WITH": 30,
    }.get(relation, 10)
    score = max(
        float(edge.get("bm25_score") or 0.0),
        float(edge.get("cooccurrence_score") or 0.0),
        float(edge.get("shared_document_count") or 0.0),
    )
    return priority, score


def build_graph_neighborhoods(
    package_dir: Path,
    *,
    selected_doc_ids: set[str],
    max_edges_per_document: int,
) -> dict[str, Any]:
    nodes = pd.read_parquet(package_dir / "graph" / "knowledge_graph_nodes.parquet").fillna("")
    edges = pd.read_parquet(package_dir / "graph" / "knowledge_graph_edges.parquet").fillna("")

    node_by_id = {
        str(row.get("node_id", "")): compact_node(row)
        for row in nodes.to_dict(orient="records")
        if row.get("node_id")
    }

    selected = selected_doc_ids or {
        node_id
        for node_id, node in node_by_id.items()
        if node.get("node_type") in {"page", "service"}
    }

    incident: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edges.to_dict(orient="records"):
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        if source in selected:
            incident[source].append(compact_edge(row))
        if target in selected and target != source:
            incident[target].append(compact_edge(row))

    neighborhoods: dict[str, dict[str, Any]] = {}
    exported_nodes: dict[str, dict[str, Any]] = {}
    exported_edges: dict[str, dict[str, Any]] = {}
    for doc_id in sorted(selected):
        ranked_edges = sorted(
            incident.get(doc_id, []),
            key=lambda edge: edge_priority(edge),
            reverse=True,
        )
        if max_edges_per_document > 0:
            ranked_edges = ranked_edges[:max_edges_per_document]
        node_ids = [doc_id]
        exported_nodes[doc_id] = node_by_id.get(doc_id, {"node_id": doc_id})
        edge_ids: list[str] = []
        for edge in ranked_edges:
            edge_id = str(edge.get("edge_cid") or f"{edge.get('source')}->{edge.get('relation')}->{edge.get('target')}")
            exported_edges[edge_id] = edge
            edge_ids.append(edge_id)
            for node_id in [edge.get("source", ""), edge.get("target", "")]:
                if node_id and node_id in node_by_id:
                    exported_nodes[node_id] = node_by_id[node_id]
                    if node_id not in node_ids:
                        node_ids.append(node_id)
        neighborhoods[doc_id] = {
            "node_ids": node_ids,
            "edge_ids": edge_ids,
        }

    return {
        "schemaVersion": 1,
        "maxEdgesPerDocument": max_edges_per_document,
        "nodes": exported_nodes,
        "edges": exported_edges,
        "neighborhoods": neighborhoods,
    }


def write_graph_neighborhood_artifacts(
    *,
    output_dir: Path,
    generated_dir: Path,
    graph_payload: dict[str, Any],
    shard_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    legacy_graph_path = generated_dir / "graph-neighborhoods.json"
    if legacy_graph_path.exists():
        legacy_graph_path.unlink()

    shard_dir = generated_dir / "graph-neighborhoods"
    shard_dir.mkdir(parents=True, exist_ok=True)
    for stale_path in shard_dir.glob("*.json"):
        stale_path.unlink()

    neighborhoods: dict[str, dict[str, Any]] = graph_payload["neighborhoods"]
    nodes: dict[str, dict[str, Any]] = graph_payload["nodes"]
    edges: dict[str, dict[str, Any]] = graph_payload["edges"]
    doc_ids = sorted(neighborhoods)
    shard_size = max(1, shard_size)

    shard_records: list[dict[str, Any]] = []
    doc_id_to_shard: dict[str, str] = {}
    artifact_records: list[dict[str, Any]] = []

    for shard_number, start_index in enumerate(range(0, len(doc_ids), shard_size)):
        shard_doc_ids = doc_ids[start_index : start_index + shard_size]
        shard_neighborhoods = {
            doc_id: neighborhoods[doc_id]
            for doc_id in shard_doc_ids
        }
        shard_node_ids = sorted(
            {
                node_id
                for neighborhood in shard_neighborhoods.values()
                for node_id in neighborhood.get("node_ids", [])
            }
        )
        shard_edge_ids = sorted(
            {
                edge_id
                for neighborhood in shard_neighborhoods.values()
                for edge_id in neighborhood.get("edge_ids", [])
            }
        )
        shard_payload = {
            "schemaVersion": 1,
            "shardId": f"shard-{shard_number:04d}",
            "maxEdgesPerDocument": graph_payload["maxEdgesPerDocument"],
            "doc_ids": shard_doc_ids,
            "nodes": {
                node_id: nodes[node_id]
                for node_id in shard_node_ids
                if node_id in nodes
            },
            "edges": {
                edge_id: edges[edge_id]
                for edge_id in shard_edge_ids
                if edge_id in edges
            },
            "neighborhoods": shard_neighborhoods,
        }
        shard_path = shard_dir / f"shard-{shard_number:04d}.json"
        shard_record = write_json(shard_path, shard_payload)
        relative_path = Path(shard_record["path"]).relative_to(output_dir).as_posix()
        for doc_id in shard_doc_ids:
            doc_id_to_shard[doc_id] = relative_path
        shard_records.append(
            {
                "id": f"shard-{shard_number:04d}",
                "path": relative_path,
                "bytes": shard_record["bytes"],
                "cid": shard_record["cid"],
                "documentCount": len(shard_doc_ids),
                "nodeCount": len(shard_payload["nodes"]),
                "edgeCount": len(shard_payload["edges"]),
                "firstDocId": shard_doc_ids[0] if shard_doc_ids else "",
                "lastDocId": shard_doc_ids[-1] if shard_doc_ids else "",
            }
        )
        artifact_records.append(relative_manifest_record(output_dir, shard_record, "graph"))

    graph_index = {
        "schemaVersion": 1,
        "maxEdgesPerDocument": graph_payload["maxEdgesPerDocument"],
        "neighborhoodCount": len(neighborhoods),
        "shardSize": shard_size,
        "shardCount": len(shard_records),
        "shards": shard_records,
        "docIdToShard": doc_id_to_shard,
    }
    graph_index_record = write_json(generated_dir / "graph-neighborhood-index.json", graph_index)
    artifact_records.insert(0, relative_manifest_record(output_dir, graph_index_record, "graph"))
    return graph_index, artifact_records


def build_community_payloads(package_dir: Path, *, selected_doc_ids: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    communities_frame = pd.read_parquet(package_dir / "graph" / "graph_communities.parquet").fillna("")
    document_frame = pd.read_parquet(package_dir / "graph" / "document_communities.parquet").fillna("")
    if selected_doc_ids:
        document_frame = document_frame[document_frame["doc_id"].isin(selected_doc_ids)]

    used_community_ids = set(str(value) for value in document_frame["community_id"].tolist()) if len(document_frame) else set()
    community_rows = [
        {
            "community_id": str(row.get("community_id", "")),
            "community_cid": str(row.get("community_cid", "")),
            "label": str(row.get("label", "")),
            "node_count": int(row.get("node_count") or 0),
            "document_count": int(row.get("document_count") or 0),
            "page_count": int(row.get("page_count") or 0),
            "service_count": int(row.get("service_count") or 0),
            "keyterm_count": int(row.get("keyterm_count") or 0),
            "provider_count": int(row.get("provider_count") or 0),
            "category_count": int(row.get("category_count") or 0),
            "top_terms": json.loads(row.get("top_terms_json") or "[]"),
            "top_categories": json.loads(row.get("top_categories_json") or "[]"),
            "top_hosts": json.loads(row.get("top_hosts_json") or "[]"),
        }
        for row in communities_frame.to_dict(orient="records")
        if not used_community_ids or str(row.get("community_id", "")) in used_community_ids
    ]
    document_rows = [
        {
            "doc_id": str(row.get("doc_id", "")),
            "doc_type": str(row.get("doc_type", "")),
            "source_url": str(row.get("source_url", "")),
            "source_content_cid": str(row.get("source_content_cid", "")),
            "source_page_cid": str(row.get("source_page_cid", "")),
            "community_id": str(row.get("community_id", "")),
            "community_label": str(row.get("community_label", "")),
        }
        for row in document_frame.to_dict(orient="records")
    ]
    return (
        {"schemaVersion": 1, "communities": community_rows},
        {"schemaVersion": 1, "documents": document_rows},
    )


def build_document_community_parquet_rows(
    document_communities: dict[str, Any],
    documents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    service_cluster_by_doc_id: dict[str, list[int]] = {}
    page_cluster_ids_by_page_cid: dict[str, set[int]] = defaultdict(set)
    for document in documents:
        if str(document.get("doc_type", "")) != "service":
            continue
        doc_id = str(document.get("doc_id", "") or "")
        if not doc_id:
            continue
        cluster_id = document.get("geo_cluster_id")
        normalized_cluster_id = int(cluster_id) if isinstance(cluster_id, int) and cluster_id >= 0 else -1
        service_cluster_by_doc_id[doc_id] = [normalized_cluster_id]
        page_cid = str(document.get("source_page_cid", "") or "")
        if page_cid:
            page_cluster_ids_by_page_cid[page_cid].add(normalized_cluster_id)

    rows: list[dict[str, Any]] = []
    doc_id_to_cluster_ids: dict[str, list[int]] = {}
    for row in document_communities.get("documents", []):
        doc_id = str(row.get("doc_id", "") or "")
        doc_type = str(row.get("doc_type", "") or "")
        source_page_cid = str(row.get("source_page_cid", "") or "")
        cluster_ids = service_cluster_by_doc_id.get(doc_id)
        if cluster_ids is None and source_page_cid:
            cluster_ids = sorted(page_cluster_ids_by_page_cid.get(source_page_cid, set()))
        cluster_ids = cluster_ids or []
        primary_cluster_id = next((cluster_id for cluster_id in cluster_ids if cluster_id >= 0), None)
        rows.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "source_url": str(row.get("source_url", "")),
                "source_content_cid": str(row.get("source_content_cid", "")),
                "source_page_cid": source_page_cid,
                "community_id": str(row.get("community_id", "")),
                "community_label": str(row.get("community_label", "")),
                "geo_cluster_id": primary_cluster_id,
                "geo_cluster_ids_json": json.dumps(cluster_ids, separators=(",", ":")),
                "cluster_count": len(cluster_ids),
            }
        )
        doc_id_to_cluster_ids[doc_id] = cluster_ids
    return rows, doc_id_to_cluster_ids


def build_graph_community_parquet_rows(
    graph_communities: dict[str, Any],
    document_community_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    community_cluster_counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for row in document_community_rows:
        community_id = str(row.get("community_id", "") or "")
        if not community_id:
            continue
        for cluster_id in json.loads(row.get("geo_cluster_ids_json") or "[]"):
            if isinstance(cluster_id, int):
                community_cluster_counts[community_id][cluster_id] += 1

    rows: list[dict[str, Any]] = []
    for row in graph_communities.get("communities", []):
        community_id = str(row.get("community_id", "") or "")
        cluster_counts = community_cluster_counts.get(community_id, {})
        primary_cluster_id = None
        positive_cluster_counts = {
            cluster_id: count
            for cluster_id, count in cluster_counts.items()
            if cluster_id >= 0
        }
        if positive_cluster_counts:
            primary_cluster_id = sorted(
                positive_cluster_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]
        rows.append(
            {
                "community_id": community_id,
                "community_cid": str(row.get("community_cid", "")),
                "label": str(row.get("label", "")),
                "node_count": int(row.get("node_count") or 0),
                "document_count": int(row.get("document_count") or 0),
                "page_count": int(row.get("page_count") or 0),
                "service_count": int(row.get("service_count") or 0),
                "keyterm_count": int(row.get("keyterm_count") or 0),
                "provider_count": int(row.get("provider_count") or 0),
                "category_count": int(row.get("category_count") or 0),
                "top_terms_json": json.dumps(row.get("top_terms") or [], separators=(",", ":")),
                "top_categories_json": json.dumps(row.get("top_categories") or [], separators=(",", ":")),
                "top_hosts_json": json.dumps(row.get("top_hosts") or [], separators=(",", ":")),
                "geo_cluster_id": primary_cluster_id,
                "geo_cluster_ids_json": json.dumps(sorted(cluster_counts), separators=(",", ":")),
                "geo_cluster_counts_json": json.dumps(
                    {str(cluster_id): count for cluster_id, count in sorted(cluster_counts.items())},
                    separators=(",", ":"),
                ),
            }
        )
    return rows


def build_graph_geo_cluster_manifest(
    *,
    geo_cluster_manifest: dict[str, Any],
    graph_index: dict[str, Any],
    graph_communities: dict[str, Any],
    document_community_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    cluster_metadata = {
        int(cluster.get("clusterId")): cluster
        for cluster in geo_cluster_manifest.get("clusters", [])
        if cluster.get("clusterId") not in ("", None)
    }
    community_by_id = {
        str(community.get("community_id", "")): community
        for community in graph_communities.get("communities", [])
        if community.get("community_id")
    }
    graph_cluster_records: dict[int, dict[str, Any]] = {}
    community_id_to_cluster_ids: dict[str, set[int]] = defaultdict(set)

    for row in document_community_rows:
        doc_id = str(row.get("doc_id", "") or "")
        community_id = str(row.get("community_id", "") or "")
        doc_type = str(row.get("doc_type", "") or "")
        source_page_cid = str(row.get("source_page_cid", "") or "")
        shard_path = str(graph_index.get("docIdToShard", {}).get(doc_id, "") or "")
        cluster_ids = json.loads(row.get("geo_cluster_ids_json") or "[]")
        for cluster_id in cluster_ids:
            if not isinstance(cluster_id, int):
                continue
            record = graph_cluster_records.setdefault(
                cluster_id,
                {
                    "clusterId": cluster_id,
                    "kind": cluster_metadata.get(cluster_id, {}).get(
                        "kind",
                        "service_unclustered" if cluster_id < 0 else "service_cluster",
                    ),
                    "serviceDocumentCount": int(cluster_metadata.get(cluster_id, {}).get("serviceDocumentCount") or 0),
                    "graphDocIds": set(),
                    "graphNeighborhoodShardPaths": set(),
                    "communityCounts": defaultdict(int),
                    "pageDocCount": 0,
                    "serviceDocCount": 0,
                    "sourcePageCids": set(),
                },
            )
            if doc_id:
                record["graphDocIds"].add(doc_id)
            if shard_path:
                record["graphNeighborhoodShardPaths"].add(shard_path)
            if community_id:
                record["communityCounts"][community_id] += 1
                community_id_to_cluster_ids[community_id].add(cluster_id)
            if source_page_cid:
                record["sourcePageCids"].add(source_page_cid)
            if doc_type == "service":
                record["serviceDocCount"] += 1
            elif doc_type == "page":
                record["pageDocCount"] += 1

    clusters: list[dict[str, Any]] = []
    for cluster_id, record in sorted(graph_cluster_records.items()):
        top_communities = []
        for community_id, count in sorted(
            record["communityCounts"].items(),
            key=lambda item: (-item[1], item[0]),
        )[:8]:
            community = community_by_id.get(community_id, {})
            top_communities.append(
                {
                    "community_id": community_id,
                    "label": str(community.get("label", "")),
                    "document_count": int(community.get("document_count") or 0),
                    "service_count": int(community.get("service_count") or 0),
                    "matched_documents": count,
                }
            )
        clusters.append(
            {
                "clusterId": cluster_id,
                "kind": record["kind"],
                "serviceDocumentCount": record["serviceDocumentCount"],
                "graphDocumentCount": len(record["graphDocIds"]),
                "serviceGraphDocumentCount": int(record["serviceDocCount"]),
                "pageGraphDocumentCount": int(record["pageDocCount"]),
                "graphNeighborhoodShardCount": len(record["graphNeighborhoodShardPaths"]),
                "graphNeighborhoodShardPaths": sorted(record["graphNeighborhoodShardPaths"]),
                "communityCount": len(record["communityCounts"]),
                "communityIds": sorted(record["communityCounts"]),
                "sourcePageCidCount": len(record["sourcePageCids"]),
                "topCommunities": top_communities,
            }
        )

    return {
        "schemaVersion": 1,
        "clusterCount": len(clusters),
        "clusters": clusters,
        "communityIdToClusterIds": {
            community_id: sorted(cluster_ids)
            for community_id, cluster_ids in sorted(community_id_to_cluster_ids.items())
        },
    }


def relative_manifest_record(root: Path, record: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "path": Path(record["path"]).relative_to(root).as_posix(),
        "bytes": record["bytes"],
        "cid": record["cid"],
        "role": role,
    }


def build_browser_graphrag_corpus(
    *,
    package_dir: Path = DEFAULT_PACKAGE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    portal_parquet_path: Path = DEFAULT_PORTAL_PARQUET,
    portal_location_parquet_path: Path | None = None,
    geo_reference_dir: Path = DEFAULT_GEO_REFERENCE_DIR,
    place_centroid_path: Path | None = None,
    max_documents: int = 0,
    text_max_chars: int = 6000,
    max_terms_per_document: int = 48,
    max_edges_per_document: int = 8,
    graph_shard_size: int = 500,
    geo_cluster_target_size: int = DEFAULT_GEO_CLUSTER_TARGET_SIZE,
    geo_cluster_count: int = 0,
    non_service_row_group_size: int = DEFAULT_NON_SERVICE_ROW_GROUP_SIZE,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    output_dir = output_dir.resolve()
    generated_dir = output_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = read_manifest(package_dir)
    portal_parquet_path = portal_parquet_path.resolve()
    portal_location_parquet_path = resolve_portal_location_parquet_path(
        portal_parquet_path,
        portal_location_parquet_path.resolve() if portal_location_parquet_path else None,
    )
    portal_service_details = load_portal_service_details(portal_parquet_path)
    documents = load_documents(
        package_dir,
        portal_service_details=portal_service_details,
        max_documents=max_documents,
        text_max_chars=text_max_chars,
    )
    geo_cluster_manifest = cluster_service_documents(
        documents,
        reference_dir=geo_reference_dir.resolve(),
        place_centroid_path=place_centroid_path.resolve() if place_centroid_path else None,
        target_cluster_size=geo_cluster_target_size,
        cluster_count=geo_cluster_count,
    )
    selected_doc_ids = {document["doc_id"] for document in documents}
    service_documents = [document for document in documents if document.get("doc_type") == "service"]
    service_count = len(service_documents)
    service_phone_count = sum(1 for document in service_documents if document.get("phones"))
    service_address_count = sum(1 for document in service_documents if document.get("addresses"))
    service_intake_step_count = sum(1 for document in service_documents if document.get("intake_steps"))
    service_required_document_count = sum(1 for document in service_documents if document.get("required_documents"))

    artifact_records: list[dict[str, Any]] = []
    stale_documents_json = generated_dir / "documents.json"
    if stale_documents_json.exists():
        stale_documents_json.unlink()
    documents_record = write_clustered_documents_parquet(
        generated_dir / "documents.parquet",
        documents,
        service_cluster_metadata=geo_cluster_manifest,
        non_service_row_group_size=non_service_row_group_size,
    )
    artifact_records.append(relative_manifest_record(output_dir, documents_record, "documents"))

    document_index_record = write_json(generated_dir / "document-index.json", build_document_index(documents))
    artifact_records.append(relative_manifest_record(output_dir, document_index_record, "index"))

    bm25_doc_frame = pd.read_parquet(package_dir / "retrieval" / "bm25_documents.parquet")
    bm25_term_frame = pd.read_parquet(package_dir / "retrieval" / "bm25_terms.parquet")
    embedding_frame = pd.read_parquet(package_dir / "retrieval" / "vector_embeddings.parquet")

    bm25_payload = build_bm25_payload(
        package_dir,
        selected_doc_ids=selected_doc_ids,
        max_terms_per_document=max_terms_per_document,
        doc_frame=bm25_doc_frame,
        term_frame=bm25_term_frame,
    )
    bm25_record = write_json(generated_dir / "bm25-documents.json", bm25_payload)
    artifact_records.append(relative_manifest_record(output_dir, bm25_record, "retrieval"))

    embedding_index = write_embeddings(
        package_dir,
        generated_dir / "embeddings.f32",
        selected_doc_ids=selected_doc_ids,
        frame=embedding_frame,
    )
    embedding_binary_record = file_record(generated_dir / "embeddings.f32")
    artifact_records.append(relative_manifest_record(output_dir, embedding_binary_record, "retrieval"))
    embedding_index_record = write_json(generated_dir / "embedding-index.json", embedding_index)
    artifact_records.append(relative_manifest_record(output_dir, embedding_index_record, "retrieval"))

    retrieval_geo_shards, retrieval_geo_shard_records = build_retrieval_geo_shard_artifacts(
        package_dir=package_dir,
        output_dir=output_dir,
        generated_dir=generated_dir,
        documents=documents,
        geo_cluster_manifest=geo_cluster_manifest,
        max_terms_per_document=max_terms_per_document,
        bm25_doc_frame=bm25_doc_frame,
        bm25_term_frame=bm25_term_frame,
        embedding_frame=embedding_frame,
    )
    artifact_records.extend(retrieval_geo_shard_records)

    graph_payload = build_graph_neighborhoods(
        package_dir,
        selected_doc_ids=selected_doc_ids,
        max_edges_per_document=max_edges_per_document,
    )
    graph_index, graph_records = write_graph_neighborhood_artifacts(
        output_dir=output_dir,
        generated_dir=generated_dir,
        graph_payload=graph_payload,
        shard_size=graph_shard_size,
    )
    artifact_records.extend(graph_records)

    graph_communities, document_communities = build_community_payloads(
        package_dir,
        selected_doc_ids=selected_doc_ids,
    )
    communities_record = write_json(generated_dir / "graph-communities.json", graph_communities)
    artifact_records.append(relative_manifest_record(output_dir, communities_record, "graph"))
    document_communities_record = write_json(generated_dir / "document-communities.json", document_communities)
    artifact_records.append(relative_manifest_record(output_dir, document_communities_record, "graph"))

    document_community_parquet_rows, doc_id_to_cluster_ids = build_document_community_parquet_rows(
        document_communities,
        documents,
    )
    document_communities_parquet_record, document_communities_row_groups = write_cluster_field_grouped_parquet(
        generated_dir / "document-communities.parquet",
        document_community_parquet_rows,
        cluster_field="geo_cluster_id",
        sort_key=lambda row: (str(row.get("doc_id", "")), str(row.get("community_id", ""))),
    )
    artifact_records.append(relative_manifest_record(output_dir, document_communities_parquet_record, "graph"))

    graph_community_parquet_rows = build_graph_community_parquet_rows(
        graph_communities,
        document_community_parquet_rows,
    )
    graph_communities_parquet_record, graph_communities_row_groups = write_cluster_field_grouped_parquet(
        generated_dir / "graph-communities.parquet",
        graph_community_parquet_rows,
        cluster_field="geo_cluster_id",
        sort_key=lambda row: (str(row.get("community_id", "")), str(row.get("label", ""))),
    )
    artifact_records.append(relative_manifest_record(output_dir, graph_communities_parquet_record, "graph"))

    graph_geo_clusters = build_graph_geo_cluster_manifest(
        geo_cluster_manifest=geo_cluster_manifest,
        graph_index=graph_index,
        graph_communities=graph_communities,
        document_community_rows=document_community_parquet_rows,
    )
    graph_geo_clusters["docIdToClusterIds"] = doc_id_to_cluster_ids
    graph_geo_clusters_record = write_json(generated_dir / "graph-geo-clusters.json", graph_geo_clusters)
    artifact_records.append(relative_manifest_record(output_dir, graph_geo_clusters_record, "graph"))

    service_geo_index = build_service_geo_index(documents)
    service_geo_record = write_json(generated_dir / "service-geo-index.json", service_geo_index)
    artifact_records.append(relative_manifest_record(output_dir, service_geo_record, "geo"))
    location_index, location_records = build_service_location_artifacts(
        output_dir=output_dir,
        generated_dir=generated_dir,
        portal_location_rows=load_portal_service_locations(portal_location_parquet_path),
        documents=documents,
        geo_cluster_manifest=geo_cluster_manifest,
        non_service_row_group_size=non_service_row_group_size,
    )
    artifact_records.extend(location_records)
    document_geo_cluster_record = write_json(generated_dir / "document-geo-clusters.json", geo_cluster_manifest)
    artifact_records.append(relative_manifest_record(output_dir, document_geo_cluster_record, "geo"))

    generated_manifest = {
        "schemaVersion": 1,
        "documentCount": len(documents),
        "serviceDocumentCount": service_count,
        "servicePhoneCount": service_phone_count,
        "serviceAddressCount": service_address_count,
        "serviceIntakeStepCount": service_intake_step_count,
        "serviceRequiredDocumentCount": service_required_document_count,
        "serviceLocationCount": int(location_index.get("locationCount") or 0),
        "clusteredServiceLocationCount": int(location_index.get("clusteredLocationCount") or 0),
        "serviceLocationParquetRowGroupCount": int(location_index.get("rowGroupCount") or 0),
        "embeddingCount": int(embedding_index["count"]),
        "embeddingDimension": int(embedding_index["dimension"]),
        "embeddingModel": embedding_index["embeddingModel"],
        "bm25DocumentCount": len(bm25_payload["documents"]),
        "graphNeighborhoodCount": len(graph_payload["neighborhoods"]),
        "graphNeighborhoodShardCount": int(graph_index["shardCount"]),
        "graphCommunityCount": len(graph_communities["communities"]),
        "documentCommunityCount": len(document_communities["documents"]),
        "geoSearchIndexedServiceCount": int(service_geo_index["serviceCount"]),
        "geoSearchPlaceTermCount": len(service_geo_index["docsByPlaceTerm"]),
        "geoClusterCount": int(geo_cluster_manifest["clusterCount"]),
        "geoClusteredServiceCount": int(geo_cluster_manifest["clusteredServiceCount"]),
        "geoUnclusteredServiceCount": int(geo_cluster_manifest["unclusteredServiceCount"]),
        "documentParquetRowGroupCount": int(geo_cluster_manifest.get("rowGroupCount", 0)),
        "geoRetrievalShardCount": int(retrieval_geo_shards["shardCount"]),
        "geoRetrievalShardContentCidCount": len(retrieval_geo_shards["contentCidToShardIds"]),
        "bm25ParquetRowGroupCount": int(retrieval_geo_shards.get("bm25RowGroupCount") or 0),
        "embeddingParquetRowGroupCount": int(retrieval_geo_shards.get("embeddingRowGroupCount") or 0),
        "graphGeoClusterCount": int(graph_geo_clusters["clusterCount"]),
        "graphCommunityParquetRowGroupCount": len(graph_communities_row_groups),
        "documentCommunityParquetRowGroupCount": len(document_communities_row_groups),
        "sourcePackage": {
            "path": str(package_dir),
            "build_manifest_cid": source_manifest.get("build_manifest_cid", ""),
            "document_count": source_manifest.get("document_count", 0),
            "graph_node_count": source_manifest.get("graph_node_count", 0),
            "graph_edge_count": source_manifest.get("graph_edge_count", 0),
        },
        "files": artifact_records,
    }
    generated_manifest_record = write_json(generated_dir / "generated-manifest.json", generated_manifest)
    artifact_records.append(relative_manifest_record(output_dir, generated_manifest_record, "metadata"))

    artifacts_manifest = {
        "schemaVersion": 1,
        "datasetId": "endomorphosis/211-info",
        "datasetPath": "browser/211-info/current",
        "corpus": {
            "name": "211info retrieval package",
            "source": "https://huggingface.co/datasets/endomorphosis/211-info",
            "documentCount": len(documents),
            "embeddingModel": embedding_index["embeddingModel"],
            "embeddingDimension": int(embedding_index["dimension"]),
        },
        "sourcePackage": generated_manifest["sourcePackage"],
        "artifacts": artifact_records,
    }
    artifacts_manifest_record = write_json(output_dir / "artifacts.manifest.json", artifacts_manifest)

    return {
        "output_dir": str(output_dir),
        "document_count": len(documents),
        "service_document_count": service_count,
        "service_phone_count": service_phone_count,
        "service_address_count": service_address_count,
        "service_intake_step_count": service_intake_step_count,
        "service_required_document_count": service_required_document_count,
        "embedding_count": int(embedding_index["count"]),
        "embedding_dimension": int(embedding_index["dimension"]),
        "bm25_document_count": len(bm25_payload["documents"]),
        "graph_neighborhood_count": len(graph_payload["neighborhoods"]),
        "graph_neighborhood_shard_count": int(graph_index["shardCount"]),
        "graph_community_count": len(graph_communities["communities"]),
        "document_community_count": len(document_communities["documents"]),
        "geo_indexed_service_count": int(service_geo_index["serviceCount"]),
        "geo_place_term_count": len(service_geo_index["docsByPlaceTerm"]),
        "geo_cluster_count": int(geo_cluster_manifest["clusterCount"]),
        "geo_clustered_service_count": int(geo_cluster_manifest["clusteredServiceCount"]),
        "geo_unclustered_service_count": int(geo_cluster_manifest["unclusteredServiceCount"]),
        "service_location_count": int(location_index.get("locationCount") or 0),
        "clustered_service_location_count": int(location_index.get("clusteredLocationCount") or 0),
        "service_location_parquet_row_group_count": int(location_index.get("rowGroupCount") or 0),
        "document_parquet_row_group_count": int(geo_cluster_manifest.get("rowGroupCount", 0)),
        "geo_retrieval_shard_count": int(retrieval_geo_shards["shardCount"]),
        "geo_retrieval_shard_content_cid_count": len(retrieval_geo_shards["contentCidToShardIds"]),
        "bm25_parquet_row_group_count": int(retrieval_geo_shards.get("bm25RowGroupCount") or 0),
        "embedding_parquet_row_group_count": int(retrieval_geo_shards.get("embeddingRowGroupCount") or 0),
        "graph_geo_cluster_count": int(graph_geo_clusters["clusterCount"]),
        "graph_community_parquet_row_group_count": len(graph_communities_row_groups),
        "document_community_parquet_row_group_count": len(document_communities_row_groups),
        "artifact_count": len(artifact_records) + 1,
        "artifacts_manifest_cid": artifacts_manifest_record["cid"],
        "generated_manifest_cid": generated_manifest_record["cid"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build browser-ready static GraphRAG assets from the 211 retrieval package")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--portal-parquet-path", type=Path, default=DEFAULT_PORTAL_PARQUET)
    parser.add_argument("--portal-location-parquet-path", type=Path, default=None)
    parser.add_argument("--geo-reference-dir", type=Path, default=DEFAULT_GEO_REFERENCE_DIR)
    parser.add_argument("--place-centroid-path", type=Path, default=None)
    parser.add_argument("--max-documents", type=int, default=0, help="Optional cap for smoke builds")
    parser.add_argument("--text-max-chars", type=int, default=6000, help="Per-document text cap; 0 keeps full text")
    parser.add_argument("--max-terms-per-document", type=int, default=48)
    parser.add_argument("--max-edges-per-document", type=int, default=8)
    parser.add_argument("--graph-shard-size", type=int, default=500)
    parser.add_argument("--geo-cluster-target-size", type=int, default=DEFAULT_GEO_CLUSTER_TARGET_SIZE)
    parser.add_argument("--geo-cluster-count", type=int, default=0)
    parser.add_argument("--non-service-row-group-size", type=int, default=DEFAULT_NON_SERVICE_ROW_GROUP_SIZE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = build_browser_graphrag_corpus(
        package_dir=args.package_dir,
        output_dir=args.output_dir,
        portal_parquet_path=args.portal_parquet_path,
        portal_location_parquet_path=args.portal_location_parquet_path,
        geo_reference_dir=args.geo_reference_dir,
        place_centroid_path=args.place_centroid_path,
        max_documents=args.max_documents,
        text_max_chars=args.text_max_chars,
        max_terms_per_document=args.max_terms_per_document,
        max_edges_per_document=args.max_edges_per_document,
        graph_shard_size=args.graph_shard_size,
        geo_cluster_target_size=args.geo_cluster_target_size,
        geo_cluster_count=args.geo_cluster_count,
        non_service_row_group_size=args.non_service_row_group_size,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
