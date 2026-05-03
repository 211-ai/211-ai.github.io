from __future__ import annotations

from io import BytesIO

import duckdb
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter

from scraper.warc_etl import etl_warc_paths, iter_warc_documents


def write_test_warc(path):
    html = b"""
    <html>
      <head><title>Archived Food Service</title></head>
      <body>
        <main>
          <h1>Archived Food Service</h1>
          <p>Service provides food resources. Hours: Monday 9-5.</p>
          <p>123 Main St, Portland, OR 97201. Call 503-555-1212.</p>
          <a href="/get-help/food">Food</a>
        </main>
      </body>
    </html>
    """
    stream = BytesIO()
    writer = WARCWriter(stream, gzip=True)
    http_headers = StatusAndHeaders(
        "200 OK",
        [("Content-Type", "text/html; charset=UTF-8")],
        protocol="HTTP/1.1",
    )
    record = writer.create_warc_record(
        "https://www.211info.org/archive-test",
        "response",
        payload=BytesIO(html),
        http_headers=http_headers,
    )
    writer.write_record(record)
    path.write_bytes(stream.getvalue())


def test_iter_warc_documents_reads_html(tmp_path):
    warc_path = tmp_path / "sample.warc.gz"
    write_test_warc(warc_path)

    docs = list(iter_warc_documents([warc_path]))

    assert len(docs) == 1
    assert docs[0].url == "https://www.211info.org/archive-test"
    assert docs[0].status_code == 200
    assert "Archived Food Service" in docs[0].title


def test_etl_warc_paths_exports_services(tmp_path):
    warc_path = tmp_path / "sample.warc.gz"
    output_dir = tmp_path / "out"
    write_test_warc(warc_path)

    result = etl_warc_paths([warc_path], output_dir=output_dir, basename="test_warc")

    assert result["warc_documents"] == 1
    assert result["processed_services"] == 1
    assert (output_dir / "raw" / "warc_pages_raw.jsonl").exists()
    assert (output_dir / "processed" / "test_warc.csv").exists()
    con = duckdb.connect(str(output_dir / "state" / "etl_warehouse.duckdb"), read_only=True)
    assert con.execute("select count(*) from warc_documents").fetchone()[0] == 1
    assert con.execute("select count(*) from processed_services where source = 'warc_etl'").fetchone()[0] == 1
