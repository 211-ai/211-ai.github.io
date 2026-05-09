import type {
  Bm25Payload,
  CorpusArtifactManifest,
  CorpusDocument,
  CorpusDocumentIndex,
  DocumentCommunity,
  EmbeddingIndex,
  GeneratedCorpusManifest,
  GraphCommunity,
  GraphEdge,
  GraphNeighborhoodIndex,
  GraphNeighborhoodShard,
  GraphNode,
  ServiceGeoIndex,
} from "./types";

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
const graphShardPromises = new Map<string, Promise<GraphNeighborhoodShard>>();

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
    documentsPromise = fetch211CorpusJson<CorpusDocument[]>("generated/documents.json").then((documents) => ({
      documents,
      documentById: new Map(documents.map((document) => [document.doc_id, document])),
      documentByContentCid: new Map(
        documents
          .filter((document) => document.source_content_cid)
          .map((document) => [document.source_content_cid, document]),
      ),
    }));
  }
  return documentsPromise;
}

export async function load211DocumentIndex(): Promise<CorpusDocumentIndex> {
  if (!documentIndexPromise) {
    documentIndexPromise = fetch211CorpusJson<CorpusDocumentIndex>("generated/document-index.json");
  }
  return documentIndexPromise;
}

export async function load211Bm25(): Promise<Bm25Payload> {
  if (!bm25Promise) {
    bm25Promise = fetch211CorpusJson<Bm25Payload>("generated/bm25-documents.json");
  }
  return bm25Promise;
}

export async function load211Embeddings(): Promise<{ index: EmbeddingIndex; vectors: Float32Array }> {
  if (!embeddingsPromise) {
    embeddingsPromise = Promise.all([
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
  }
  return embeddingsPromise;
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
    communitiesPromise = fetch211CorpusJson<{ communities: GraphCommunity[] }>("generated/graph-communities.json").then(
      (payload) => payload.communities,
    );
  }
  return communitiesPromise;
}

export async function load211DocumentCommunities(): Promise<DocumentCommunity[]> {
  if (!documentCommunitiesPromise) {
    documentCommunitiesPromise = fetch211CorpusJson<{ documents: DocumentCommunity[] }>(
      "generated/document-communities.json",
    ).then((payload) => payload.documents);
  }
  return documentCommunitiesPromise;
}

export async function load211ServiceGeoIndex(): Promise<ServiceGeoIndex> {
  if (!serviceGeoIndexPromise) {
    serviceGeoIndexPromise = fetch211CorpusJson<ServiceGeoIndex>("generated/service-geo-index.json");
  }
  return serviceGeoIndexPromise;
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
