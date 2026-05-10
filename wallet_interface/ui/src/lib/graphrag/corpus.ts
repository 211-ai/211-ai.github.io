import type {
  Bm25Payload,
  CorpusArtifactManifest,
  CorpusDocument,
  CorpusDocumentIndex,
  DocumentGeoClusterManifest,
  DocumentCommunity,
  EmbeddingIndex,
  GeneratedCorpusManifest,
  GraphGeoClusterManifest,
  GraphCommunity,
  GraphEdge,
  GraphNeighborhoodIndex,
  GraphNeighborhoodShard,
  GraphNode,
  RetrievalGeoShardManifest,
  ServiceLocationIndex,
  ServiceLocationRecord,
  ServiceGeoIndex,
} from "./types";
import { loadDocumentsFromParquet, queryParquetRows, type DuckDbDocumentQuery } from "./duckdbDocuments";

const DEFAULT_CORPUS_BASE_URL = resolveDefaultCorpusBaseUrl();
const configuredCorpusBaseUrl = import.meta.env?.VITE_211_CORPUS_BASE_URL as string | undefined;
const CORPUS_BASE_URL = stripTrailingSlash(configuredCorpusBaseUrl || DEFAULT_CORPUS_BASE_URL);

interface CorpusState {
  documents: CorpusDocument[];
  documentById: Map<string, CorpusDocument>;
  documentByContentCid: Map<string, CorpusDocument>;
}

let artifactManifestPromise: Promise<CorpusArtifactManifest> | null = null;
let generatedManifestPromise: Promise<GeneratedCorpusManifest> | null = null;
let documentsPromise: Promise<CorpusState> | null = null;
let documentIndexPromise: Promise<CorpusDocumentIndex> | null = null;
let bm25Promise: Promise<Bm25Payload> | null = null;
let embeddingsPromise: Promise<{ index: EmbeddingIndex; vectors: Float32Array }> | null = null;
let graphIndexPromise: Promise<GraphNeighborhoodIndex> | null = null;
let communitiesPromise: Promise<GraphCommunity[]> | null = null;
let documentCommunitiesPromise: Promise<DocumentCommunity[]> | null = null;
let serviceGeoIndexPromise: Promise<ServiceGeoIndex> | null = null;
let serviceLocationIndexPromise: Promise<ServiceLocationIndex> | null = null;
let documentGeoClusterPromise: Promise<DocumentGeoClusterManifest> | null = null;
let retrievalGeoShardManifestPromise: Promise<RetrievalGeoShardManifest> | null = null;
let graphGeoClusterManifestPromise: Promise<GraphGeoClusterManifest> | null = null;
const serviceLocationSlicePromises = new Map<string, Promise<ServiceLocationRecord[]>>();
const graphShardPromises = new Map<string, Promise<GraphNeighborhoodShard>>();
const documentSlicePromises = new Map<string, Promise<CorpusState>>();
const bm25GeoShardPromises = new Map<string, Promise<Bm25Payload>>();
const embeddingGeoShardPromises = new Map<string, Promise<{ index: EmbeddingIndex; vectors: Float32Array }>>();

export function get211CorpusBaseUrl(): string {
  return CORPUS_BASE_URL;
}

export async function load211ArtifactManifest(): Promise<CorpusArtifactManifest> {
  if (!artifactManifestPromise) {
    artifactManifestPromise = fetch(`${CORPUS_BASE_URL}/artifacts.manifest.json`, { cache: "no-store" }).then(
      async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load 211 corpus manifest: ${response.status}`);
        }
        return response.json() as Promise<CorpusArtifactManifest>;
      },
    );
  }
  return artifactManifestPromise;
}

export async function load211GeneratedManifest(): Promise<GeneratedCorpusManifest> {
  if (!generatedManifestPromise) {
    generatedManifestPromise = fetch211CorpusJson<GeneratedCorpusManifest>("generated/generated-manifest.json");
  }
  return generatedManifestPromise;
}

export async function load211Documents(): Promise<CorpusState> {
  if (!documentsPromise) {
    documentsPromise = load211ArtifactManifest()
      .then(async (manifest) => {
        const parquetArtifact = manifest.artifacts.find(
          (artifact) => artifact.role === "documents" && artifact.path.endsWith(".parquet"),
        );
        if (parquetArtifact) {
          try {
            return await loadDocumentsFromParquet(get211CorpusAssetUrl(parquetArtifact.path));
          } catch (error) {
            console.warn("211 corpus parquet load failed; falling back to JSON documents.", error);
          }
        }
        return fetch211CorpusJson<CorpusDocument[]>("generated/documents.json");
      })
      .then(buildCorpusState);
  }
  return documentsPromise;
}

export async function load211DocumentsSlice(query: DuckDbDocumentQuery = {}): Promise<CorpusState> {
  const manifest = await load211ArtifactManifest();
  const parquetArtifact = manifest.artifacts.find(
    (artifact) => artifact.role === "documents" && artifact.path.endsWith(".parquet"),
  );
  if (!parquetArtifact) {
    return load211Documents();
  }
  const cacheKey = JSON.stringify({
    clusterIds: query.clusterIds || [],
    includeUnclusteredServices: Boolean(query.includeUnclusteredServices),
    docTypes: query.docTypes || [],
    docIds: query.docIds || [],
    limit: query.limit || 0,
  });
  if (!documentSlicePromises.has(cacheKey)) {
    documentSlicePromises.set(
      cacheKey,
      loadDocumentsFromParquet(get211CorpusAssetUrl(parquetArtifact.path), query).then(buildCorpusState),
    );
  }
  return documentSlicePromises.get(cacheKey)!;
}

export async function load211DocumentIndex(): Promise<CorpusDocumentIndex> {
  if (!documentIndexPromise) {
    documentIndexPromise = fetch211CorpusJson<CorpusDocumentIndex>("generated/document-index.json");
  }
  return documentIndexPromise;
}

export async function load211Bm25(): Promise<Bm25Payload> {
  if (!bm25Promise) {
    bm25Promise = load211ArtifactManifest().then(async (manifest) => {
      const parquetArtifact = findArtifactBySuffix(manifest, "generated/bm25-documents.parquet");
      if (parquetArtifact) {
        try {
          return buildBm25PayloadFromRows(await queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
            orderBy: ["doc_type ASC", "doc_id ASC"],
          }));
        } catch (error) {
          console.warn("211 BM25 parquet load failed; falling back to JSON BM25.", error);
        }
      }
      return fetch211CorpusJson<Bm25Payload>("generated/bm25-documents.json");
    });
  }
  return bm25Promise;
}

export async function load211Embeddings(): Promise<{ index: EmbeddingIndex; vectors: Float32Array }> {
  if (!embeddingsPromise) {
    embeddingsPromise = load211ArtifactManifest().then(async (manifest) => {
      const parquetArtifact = findArtifactBySuffix(manifest, "generated/embeddings.parquet");
      if (parquetArtifact) {
        try {
          return buildEmbeddingBundleFromRows(
            await queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
              orderBy: ["doc_type ASC", "doc_id ASC"],
            }),
            parquetArtifact.path,
          );
        } catch (error) {
          console.warn("211 embedding parquet load failed; falling back to binary embedding bundle.", error);
        }
      }
      return Promise.all([
        fetch211CorpusJson<EmbeddingIndex>("generated/embedding-index.json"),
        fetch211CorpusArrayBuffer("generated/embeddings.f32"),
      ]).then(([index, buffer]) => {
        const vectors = new Float32Array(buffer);
        const expectedLength = index.count * index.dimension;
        if (vectors.length !== expectedLength) {
          throw new Error(`211 embedding vector length ${vectors.length} did not match ${expectedLength}`);
        }
        return { index, vectors };
      });
    });
  }
  return embeddingsPromise;
}

export async function load211Bm25GeoShard(shardPath: string): Promise<Bm25Payload> {
  if (!bm25GeoShardPromises.has(shardPath)) {
    bm25GeoShardPromises.set(shardPath, fetch211CorpusJson<Bm25Payload>(shardPath));
  }
  return bm25GeoShardPromises.get(shardPath)!;
}

export async function load211EmbeddingGeoShard(
  indexPath: string,
  binaryPath: string,
): Promise<{ index: EmbeddingIndex; vectors: Float32Array }> {
  const cacheKey = `${indexPath}::${binaryPath}`;
  if (!embeddingGeoShardPromises.has(cacheKey)) {
    embeddingGeoShardPromises.set(
      cacheKey,
      Promise.all([fetch211CorpusJson<EmbeddingIndex>(indexPath), fetch211CorpusArrayBuffer(binaryPath)]).then(
        ([index, buffer]) => {
          const vectors = new Float32Array(buffer);
          const expectedLength = index.count * index.dimension;
          if (vectors.length !== expectedLength) {
            throw new Error(`211 embedding shard vector length ${vectors.length} did not match ${expectedLength}`);
          }
          return { index, vectors };
        },
      ),
    );
  }
  return embeddingGeoShardPromises.get(cacheKey)!;
}

export async function load211GraphNeighborhoodIndex(): Promise<GraphNeighborhoodIndex> {
  if (!graphIndexPromise) {
    graphIndexPromise = fetch211CorpusJson<GraphNeighborhoodIndex>("generated/graph-neighborhood-index.json");
  }
  return graphIndexPromise;
}

export async function load211GraphNeighborhoodShard(path: string): Promise<GraphNeighborhoodShard> {
  if (!graphShardPromises.has(path)) {
    graphShardPromises.set(path, fetch211CorpusJson<GraphNeighborhoodShard>(path));
  }
  return graphShardPromises.get(path)!;
}

export async function get211RelatedGraph(
  docIds: string[],
): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const graphIndex = await load211GraphNeighborhoodIndex();
  const shardPaths = new Set<string>();
  for (const docId of docIds) {
    const shardPath = graphIndex.docIdToShard[docId];
    if (shardPath) {
      shardPaths.add(shardPath);
    }
  }

  const nodeById = new Map<string, GraphNode>();
  const edgeById = new Map<string, GraphEdge>();
  const shards = await Promise.all([...shardPaths].map((path) => load211GraphNeighborhoodShard(path)));

  for (const shard of shards) {
    for (const docId of docIds) {
      const neighborhood = shard.neighborhoods[docId];
      if (!neighborhood) {
        continue;
      }
      for (const nodeId of neighborhood.node_ids) {
        const node = shard.nodes[nodeId];
        if (node) {
          nodeById.set(nodeId, node);
        }
      }
      for (const edgeId of neighborhood.edge_ids) {
        const edge = shard.edges[edgeId];
        if (edge) {
          edgeById.set(edgeId, edge);
        }
      }
    }
  }

  return { nodes: [...nodeById.values()], edges: [...edgeById.values()] };
}

export async function load211GraphCommunities(): Promise<GraphCommunity[]> {
  if (!communitiesPromise) {
    communitiesPromise = load211ArtifactManifest().then(async (manifest) => {
      const parquetArtifact = findArtifactBySuffix(manifest, "generated/graph-communities.parquet");
      if (parquetArtifact) {
        try {
          return buildGraphCommunitiesFromRows(
            await queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
              orderBy: ["coalesce(geo_cluster_id, 999999) ASC", "community_id ASC"],
            }),
          );
        } catch (error) {
          console.warn("211 graph community parquet load failed; falling back to JSON graph communities.", error);
        }
      }
      return fetch211CorpusJson<{ communities: GraphCommunity[] }>("generated/graph-communities.json").then(
        (payload) => payload.communities,
      );
    });
  }
  return communitiesPromise;
}

export async function load211DocumentCommunities(): Promise<DocumentCommunity[]> {
  if (!documentCommunitiesPromise) {
    documentCommunitiesPromise = load211ArtifactManifest().then(async (manifest) => {
      const parquetArtifact = findArtifactBySuffix(manifest, "generated/document-communities.parquet");
      if (parquetArtifact) {
        try {
          return buildDocumentCommunitiesFromRows(
            await queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
              orderBy: ["coalesce(geo_cluster_id, 999999) ASC", "doc_id ASC", "community_id ASC"],
            }),
          );
        } catch (error) {
          console.warn("211 document community parquet load failed; falling back to JSON document communities.", error);
        }
      }
      return fetch211CorpusJson<{ documents: DocumentCommunity[] }>("generated/document-communities.json").then(
        (payload) => payload.documents,
      );
    });
  }
  return documentCommunitiesPromise;
}

export async function load211ServiceGeoIndex(): Promise<ServiceGeoIndex> {
  if (!serviceGeoIndexPromise) {
    serviceGeoIndexPromise = fetch211CorpusJson<ServiceGeoIndex>("generated/service-geo-index.json");
  }
  return serviceGeoIndexPromise;
}

export async function load211ServiceLocationIndex(): Promise<ServiceLocationIndex> {
  if (!serviceLocationIndexPromise) {
    serviceLocationIndexPromise = fetch211CorpusJson<ServiceLocationIndex>("generated/service-location-index.json");
  }
  return serviceLocationIndexPromise;
}

export async function load211ServiceLocationsSlice(options: {
  clusterIds?: number[];
  includeUnclusteredLocations?: boolean;
  serviceDocIds?: string[];
  limit?: number;
} = {}): Promise<ServiceLocationRecord[]> {
  const manifest = await load211ArtifactManifest();
  const parquetArtifact = findArtifactBySuffix(manifest, "generated/service-locations.parquet");
  if (!parquetArtifact) {
    return [];
  }
  const cacheKey = JSON.stringify({
    clusterIds: options.clusterIds || [],
    includeUnclusteredLocations: Boolean(options.includeUnclusteredLocations),
    serviceDocIds: options.serviceDocIds || [],
    limit: options.limit || 0,
  });
  if (!serviceLocationSlicePromises.has(cacheKey)) {
    serviceLocationSlicePromises.set(
      cacheKey,
      queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
        clusterIds: options.clusterIds,
        includeNullCluster: Boolean(options.includeUnclusteredLocations),
        serviceDocIds: options.serviceDocIds,
        clusterColumn: "geo_cluster_id",
        orderBy: options.clusterIds?.length
          ? [
              "coalesce(geo_cluster_id, 999999) ASC",
              "service_doc_id ASC",
              "location_id ASC",
            ]
          : ["service_doc_id ASC", "location_id ASC"],
        limit: options.limit,
      }).then((rows) => rows.map((row) => buildServiceLocationRecord(row))),
    );
  }
  return serviceLocationSlicePromises.get(cacheKey)!;
}

export async function load211DocumentGeoClusters(): Promise<DocumentGeoClusterManifest> {
  if (!documentGeoClusterPromise) {
    documentGeoClusterPromise = fetch211CorpusJson<DocumentGeoClusterManifest>("generated/document-geo-clusters.json");
  }
  return documentGeoClusterPromise;
}

export async function load211RetrievalGeoShards(): Promise<RetrievalGeoShardManifest> {
  if (!retrievalGeoShardManifestPromise) {
    retrievalGeoShardManifestPromise = fetch211CorpusJson<RetrievalGeoShardManifest>("generated/retrieval-geo-shards.json");
  }
  return retrievalGeoShardManifestPromise;
}

export async function load211GraphGeoClusters(): Promise<GraphGeoClusterManifest> {
  if (!graphGeoClusterManifestPromise) {
    graphGeoClusterManifestPromise = fetch211CorpusJson<GraphGeoClusterManifest>("generated/graph-geo-clusters.json");
  }
  return graphGeoClusterManifestPromise;
}

export async function load211Bm25Slice(options: {
  clusterIds: number[];
  includeUnclusteredServices?: boolean;
}): Promise<Bm25Payload | null> {
  const manifest = await load211ArtifactManifest();
  const parquetArtifact = findArtifactBySuffix(manifest, "generated/bm25-documents.parquet");
  if (!parquetArtifact) {
    return null;
  }
  const rows = await queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
    clusterIds: options.clusterIds,
    includeNullCluster: Boolean(options.includeUnclusteredServices),
    clusterColumn: "geo_cluster_id",
    clusterFilterDocTypes: ["service"],
    orderBy: ["doc_id ASC"],
  });
  return buildBm25PayloadFromRows(rows);
}

export async function load211EmbeddingSlice(options: {
  clusterIds: number[];
  includeUnclusteredServices?: boolean;
}): Promise<{ index: EmbeddingIndex; vectors: Float32Array } | null> {
  const manifest = await load211ArtifactManifest();
  const parquetArtifact = findArtifactBySuffix(manifest, "generated/embeddings.parquet");
  if (!parquetArtifact) {
    return null;
  }
  const rows = await queryParquetRows(get211CorpusAssetUrl(parquetArtifact.path), {
    clusterIds: options.clusterIds,
    includeNullCluster: Boolean(options.includeUnclusteredServices),
    clusterColumn: "geo_cluster_id",
    clusterFilterDocTypes: ["service"],
    orderBy: ["doc_id ASC"],
  });
  return buildEmbeddingBundleFromRows(rows, parquetArtifact.path);
}

export async function fetch211CorpusJson<T>(relativePath: string): Promise<T> {
  const response = await fetch(get211CorpusAssetUrl(relativePath));
  if (!response.ok) {
    throw new Error(`Failed to load 211 corpus asset ${relativePath}: ${response.status}`);
  }
  const text = await response.text();
  const trimmed = text.trimStart();
  if (trimmed.startsWith("version https://git-lfs.github.com/spec/v1")) {
    throw new Error(
      `211 corpus asset ${relativePath} resolved to a Git LFS pointer instead of JSON. Refresh the service worker cache or serve a non-LFS JSON artifact.`,
    );
  }
  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new Error(
      `Failed to parse 211 corpus asset ${relativePath} as JSON: ${error instanceof Error ? error.message : "unknown parse error"}`,
    );
  }
}

export async function fetch211CorpusArrayBuffer(relativePath: string): Promise<ArrayBuffer> {
  const response = await fetch(get211CorpusAssetUrl(relativePath));
  if (!response.ok) {
    throw new Error(`Failed to load 211 corpus asset ${relativePath}: ${response.status}`);
  }
  return response.arrayBuffer();
}

export function get211CorpusAssetUrl(relativePath: string): string {
  const cleanPath = relativePath.replace(/^\/+/, "");
  return `${CORPUS_BASE_URL}/${cleanPath}`;
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function buildCorpusState(documents: CorpusDocument[]): CorpusState {
  return {
    documents,
    documentById: new Map(documents.map((document) => [document.doc_id, document])),
    documentByContentCid: new Map(
      documents
        .filter((document) => document.source_content_cid)
        .map((document) => [document.source_content_cid, document]),
    ),
  };
}

function findArtifactBySuffix(manifest: CorpusArtifactManifest, suffix: string) {
  return manifest.artifacts.find((artifact) => artifact.path.endsWith(suffix));
}

function buildBm25PayloadFromRows(rows: Record<string, unknown>[]): Bm25Payload {
  const documents = rows.map((row) => ({
    doc_id: stringValue(row.doc_id),
    doc_type: stringValue(row.doc_type),
    source_url: stringValue(row.source_url),
    source_content_cid: stringValue(row.source_content_cid),
    source_page_cid: stringValue(row.source_page_cid),
    document_length: numberValue(row.document_length),
    terms: jsonRecordValue(row.terms_json),
    term_idf: jsonRecordValue(row.term_idf_json),
  }));
  const firstRow = rows[0] || {};
  return {
    schemaVersion: 1,
    documents,
    documentFrequency: {},
    k1: numberValue(firstRow.k1),
    b: numberValue(firstRow.b),
    avgdl: numberValue(firstRow.avgdl),
    documentCount: numberValue(firstRow.document_count),
    maxTermsPerDocument: numberValue(firstRow.max_terms_per_document),
    sourceContentCidToDocIds: buildContentCidToDocIds(documents),
  };
}

function buildEmbeddingBundleFromRows(
  rows: Record<string, unknown>[],
  parquetPath: string,
): { index: EmbeddingIndex; vectors: Float32Array } {
  const vectorsByRow = rows.map((row) => arrayNumberValue(row.embedding));
  const dimension = vectorsByRow[0]?.length || 0;
  const flatValues = new Float32Array(rows.length * dimension);
  vectorsByRow.forEach((vector, rowIndex) => {
    vector.forEach((value, columnIndex) => {
      flatValues[rowIndex * dimension + columnIndex] = value;
    });
  });
  const firstRow = rows[0] || {};
  return {
    index: {
      schemaVersion: 1,
      count: rows.length,
      dimension,
      embeddingModel: stringValue(firstRow.embedding_model),
      browserEmbeddingModel: stringValue(firstRow.browser_embedding_model),
      binary: "",
      parquet: parquetPath,
      doc_ids: rows.map((row) => stringValue(row.doc_id)),
      source_content_cids: rows.map((row) => stringValue(row.source_content_cid)),
      source_page_cids: rows.map((row) => stringValue(row.source_page_cid)),
      source_urls: rows.map((row) => stringValue(row.source_url)),
      sourceContentCidToDocIds: buildContentCidToDocIds(
        rows.map((row) => ({
          doc_id: stringValue(row.doc_id),
          source_content_cid: stringValue(row.source_content_cid),
        })),
      ),
    },
    vectors: flatValues,
  };
}

function buildGraphCommunitiesFromRows(rows: Record<string, unknown>[]): GraphCommunity[] {
  return rows.map((row) => ({
    community_id: stringValue(row.community_id),
    community_cid: stringValue(row.community_cid),
    label: stringValue(row.label),
    node_count: numberValue(row.node_count),
    document_count: numberValue(row.document_count),
    page_count: numberValue(row.page_count),
    service_count: numberValue(row.service_count),
    keyterm_count: numberValue(row.keyterm_count),
    provider_count: numberValue(row.provider_count),
    category_count: numberValue(row.category_count),
    top_terms: tuplePairsValue(row.top_terms ?? jsonArrayValue(row.top_terms_json)),
    top_categories: tuplePairsValue(row.top_categories ?? jsonArrayValue(row.top_categories_json)),
    top_hosts: tuplePairsValue(row.top_hosts ?? jsonArrayValue(row.top_hosts_json)),
  }));
}

function buildDocumentCommunitiesFromRows(rows: Record<string, unknown>[]): DocumentCommunity[] {
  return rows.map((row) => ({
    doc_id: stringValue(row.doc_id),
    doc_type: stringValue(row.doc_type),
    source_url: stringValue(row.source_url),
    source_content_cid: stringValue(row.source_content_cid),
    source_page_cid: stringValue(row.source_page_cid),
    community_id: stringValue(row.community_id),
    community_label: stringValue(row.community_label),
    geo_cluster_id: numberOrNull(row.geo_cluster_id),
    geo_cluster_ids_json: stringValue(row.geo_cluster_ids_json),
    cluster_count: numberValue(row.cluster_count),
  }));
}

function buildServiceLocationRecord(row: Record<string, unknown>): ServiceLocationRecord {
  return {
    service_doc_id: stringValue(row.service_doc_id),
    location_id: stringValue(row.location_id),
    label: stringValue(row.label),
    address: stringValue(row.address),
    street: stringValue(row.street),
    city: stringValue(row.city),
    state: stringValue(row.state),
    postal_code: stringValue(row.postal_code),
    source_url: stringValue(row.source_url),
    source_content_cid: stringValue(row.source_content_cid),
    source_page_cid: stringValue(row.source_page_cid),
    maps_query: stringValue(row.maps_query),
    apple_maps_url: stringValue(row.apple_maps_url),
    google_maps_url: stringValue(row.google_maps_url),
    geo_url: stringValue(row.geo_url),
    geo_lat: numberOrNull(row.geo_lat),
    geo_lon: numberOrNull(row.geo_lon),
    geo_precision: stringValue(row.geo_precision),
    geo_cluster_id: numberOrNull(row.geo_cluster_id),
    service_geo_cluster_id: numberOrNull(row.service_geo_cluster_id),
  };
}

function buildContentCidToDocIds(
  rows: Array<{ doc_id: string; source_content_cid: string }>,
): Record<string, string[]> {
  const contentCidToDocIds = new Map<string, Set<string>>();
  for (const row of rows) {
    if (!row.source_content_cid || !row.doc_id) {
      continue;
    }
    const entry = contentCidToDocIds.get(row.source_content_cid) || new Set<string>();
    entry.add(row.doc_id);
    contentCidToDocIds.set(row.source_content_cid, entry);
  }
  return Object.fromEntries(
    [...contentCidToDocIds.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([contentCid, docIds]) => [contentCid, [...docIds].sort()]),
  );
}

function jsonRecordValue(value: unknown): Record<string, number> {
  if (typeof value !== "string" || !value) {
    return {};
  }
  try {
    return JSON.parse(value) as Record<string, number>;
  } catch {
    return {};
  }
}

function jsonArrayValue(value: unknown): unknown[] {
  if (typeof value !== "string" || !value) {
    return [];
  }
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function arrayNumberValue(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((entry) => numberValue(entry));
}

function tuplePairsValue(value: unknown): Array<[string, number]> {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) =>
      Array.isArray(entry) && entry.length >= 2 ? [stringValue(entry[0]), numberValue(entry[1])] : null,
    )
    .filter((entry): entry is [string, number] => Boolean(entry));
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

function numberValue(value: unknown): number {
  const numeric = typeof value === "number" ? value : Number(value || 0);
  return Number.isFinite(numeric) ? numeric : 0;
}

function numberOrNull(value: unknown): number | null {
  if (value == null || value === "") {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function resolveDefaultCorpusBaseUrl(): string {
  const baseUrl = String(import.meta.env?.BASE_URL || "/");
  if (/^https?:\/\//i.test(baseUrl)) {
    return `${stripTrailingSlash(baseUrl)}/corpus/211-info/current`;
  }
  if (baseUrl === "." || baseUrl === "./") {
    return "/corpus/211-info/current";
  }
  if (baseUrl.startsWith("/")) {
    return `${stripTrailingSlash(baseUrl)}/corpus/211-info/current`;
  }
  return `/${stripTrailingSlash(baseUrl)}/corpus/211-info/current`;
}
