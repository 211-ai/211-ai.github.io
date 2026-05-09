import * as duckdb from "@duckdb/duckdb-wasm";
import type { Table } from "apache-arrow";
import type { CorpusDocument } from "./types";

let duckDbPromise: Promise<duckdb.AsyncDuckDB> | null = null;
let duckDbBundlesPromise: Promise<duckdb.DuckDBBundles> | null = null;

export interface DuckDbDocumentQuery {
  clusterIds?: number[];
  includeUnclusteredServices?: boolean;
  docTypes?: string[];
  docIds?: string[];
  limit?: number;
}

export async function loadDocumentsFromParquet(
  parquetUrl: string,
  query: DuckDbDocumentQuery = {},
): Promise<CorpusDocument[]> {
  const database = await getDuckDb();
  const connection = await database.connect();
  try {
    const table = await connection.query(buildReadParquetQuery(parquetUrl, query));
    return tableToDocuments(table);
  } finally {
    await connection.close();
  }
}

async function getDuckDb(): Promise<duckdb.AsyncDuckDB> {
  if (!duckDbPromise) {
    duckDbPromise = instantiateDuckDb();
  }
  return duckDbPromise;
}

async function instantiateDuckDb(): Promise<duckdb.AsyncDuckDB> {
  const bundle = await duckdb.selectBundle(await loadDuckDbBundles());
  const worker = new Worker(bundle.mainWorker!);
  const logger = new duckdb.VoidLogger();
  const database = new duckdb.AsyncDuckDB(logger, worker);
  await database.instantiate(bundle.mainModule, bundle.pthreadWorker);
  return database;
}

async function loadDuckDbBundles(): Promise<duckdb.DuckDBBundles> {
  if (!duckDbBundlesPromise) {
    duckDbBundlesPromise = Promise.all([
      import("@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url"),
      import("@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url"),
      import("@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url"),
      import("@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url"),
    ]).then(([duckdbWasmMvp, duckdbWorkerMvp, duckdbWasmEh, duckdbWorkerEh]) => ({
      mvp: {
        mainModule: duckdbWasmMvp.default,
        mainWorker: duckdbWorkerMvp.default,
      },
      eh: {
        mainModule: duckdbWasmEh.default,
        mainWorker: duckdbWorkerEh.default,
      },
    }));
  }
  return duckDbBundlesPromise;
}

function tableToDocuments(table: Table<any>): CorpusDocument[] {
  return table
    .toArray()
    .map((row) => normalizeDuckDbValue(row))
    .map((row) => coerceCorpusDocument(row));
}

function coerceCorpusDocument(value: unknown): CorpusDocument {
  const row = isRecord(value) ? value : {};
  return {
    doc_id: stringValue(row.doc_id),
    doc_type: stringValue(row.doc_type),
    title: stringValue(row.title),
    text: stringValue(row.text),
    text_truncated: Boolean(row.text_truncated),
    source_url: stringValue(row.source_url),
    source_content_cid: stringValue(row.source_content_cid),
    source_page_cid: stringValue(row.source_page_cid),
    provider_name: stringValue(row.provider_name),
    program_name: stringValue(row.program_name),
    categories: stringValue(row.categories),
    host: stringValue(row.host),
    city: stringValue(row.city),
    state: stringValue(row.state),
    geo_lat: numberOrNull(row.geo_lat),
    geo_lon: numberOrNull(row.geo_lon),
    geo_precision: stringValue(row.geo_precision),
    geo_cluster_id: integerOrNull(row.geo_cluster_id),
    phones: arrayValue(row.phones),
    emails: arrayValue(row.emails),
    websites: arrayValue(row.websites),
    addresses: arrayValue(row.addresses),
    hours: arrayValue(row.hours),
    eligibility: arrayValue(row.eligibility),
    intake_steps: arrayValue(row.intake_steps),
    required_documents: arrayValue(row.required_documents),
    fees: arrayValue(row.fees),
    languages: arrayValue(row.languages),
    accessibility: arrayValue(row.accessibility),
    travel_info: arrayValue(row.travel_info),
    area_served: arrayValue(row.area_served),
    geo: recordOrNull(row.geo),
  };
}

function normalizeDuckDbValue(value: unknown): unknown {
  if (value == null) {
    return value;
  }
  if (typeof value === "bigint") {
    return Number.isSafeInteger(Number(value)) ? Number(value) : String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizeDuckDbValue(item));
  }
  if (ArrayBuffer.isView(value) && !(value instanceof DataView)) {
    return Array.from(value as unknown as ArrayLike<unknown>, (item) => normalizeDuckDbValue(item));
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (typeof value === "object") {
    const withJson = value as { toJSON?: () => unknown };
    if (typeof withJson.toJSON === "function") {
      const jsonValue = withJson.toJSON();
      if (jsonValue !== value) {
        return normalizeDuckDbValue(jsonValue);
      }
    }
    const entries = Object.entries(value as Record<string, unknown>);
    return Object.fromEntries(entries.map(([key, child]) => [key, normalizeDuckDbValue(child)]));
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

function numberOrNull(value: unknown): number | null | undefined {
  if (value == null || value === "") {
    return undefined;
  }
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function integerOrNull(value: unknown): number | null | undefined {
  const numeric = numberOrNull(value);
  return numeric == null ? numeric : Math.trunc(numeric);
}

function arrayValue(value: unknown): any[] | undefined {
  return Array.isArray(value) ? value : undefined;
}

function recordOrNull(value: unknown): Record<string, unknown> | null | undefined {
  if (value == null) {
    return undefined;
  }
  return isRecord(value) ? value : null;
}

function buildReadParquetQuery(parquetUrl: string, query: DuckDbDocumentQuery): string {
  const whereClauses: string[] = [];
  if (query.docTypes?.length) {
    whereClauses.push(`doc_type IN (${query.docTypes.map(sqlStringLiteral).join(", ")})`);
  }
  if (query.clusterIds?.length) {
    const clusterClauses = [`geo_cluster_id IN (${query.clusterIds.map((value) => String(Math.trunc(value))).join(", ")})`];
    if (query.includeUnclusteredServices) {
      clusterClauses.push("(doc_type = 'service' AND geo_cluster_id IS NULL)");
    }
    whereClauses.push(`(doc_type = 'service' AND (${clusterClauses.join(" OR ")}))`);
  } else if (query.includeUnclusteredServices) {
    whereClauses.push("(doc_type = 'service' AND geo_cluster_id IS NULL)");
  }
  if (query.docIds?.length) {
    whereClauses.push(`doc_id IN (${query.docIds.map(sqlStringLiteral).join(", ")})`);
  }

  const clauses = [`SELECT * FROM read_parquet(${sqlStringLiteral(parquetUrl)})`];
  if (whereClauses.length) {
    clauses.push(`WHERE ${whereClauses.join(" AND ")}`);
  }
  clauses.push("ORDER BY");
  if (query.clusterIds?.length) {
    clauses.push(
      `CASE ${query.clusterIds
        .map((clusterId, index) => `WHEN geo_cluster_id = ${String(Math.trunc(clusterId))} THEN ${index}`)
        .join(" ")} ELSE ${query.clusterIds.length + (query.includeUnclusteredServices ? 1 : 0)} END,`,
    );
  }
  clauses.push("doc_type ASC, city ASC, state ASC, doc_id ASC");
  if (query.limit && query.limit > 0) {
    clauses.push(`LIMIT ${Math.trunc(query.limit)}`);
  }
  return clauses.join(" ");
}

function sqlStringLiteral(value: string): string {
  return `'${value.replace(/'/g, "''")}'`;
}
