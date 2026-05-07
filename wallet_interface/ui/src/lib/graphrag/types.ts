export type SearchMode = "keyword" | "vector" | "hybrid";

export interface CorpusArtifact {
  path: string;
  bytes: number;
  cid: string;
  role: string;
}

export interface CorpusArtifactManifest {
  schemaVersion: number;
  datasetId: string;
  datasetPath: string;
  corpus: {
    name: string;
    source: string;
    documentCount: number;
    embeddingModel: string;
    embeddingDimension: number;
  };
  sourcePackage: {
    path: string;
    build_manifest_cid: string;
    document_count: number;
    graph_node_count: number;
    graph_edge_count: number;
  };
  artifacts: CorpusArtifact[];
}

export interface GeneratedCorpusManifest {
  schemaVersion: number;
  documentCount: number;
  embeddingCount: number;
  embeddingDimension: number;
  embeddingModel: string;
  bm25DocumentCount: number;
  graphNeighborhoodCount: number;
  graphNeighborhoodShardCount: number;
  graphCommunityCount: number;
  documentCommunityCount: number;
  files: CorpusArtifact[];
}

export interface CorpusDocument {
  doc_id: string;
  doc_type: string;
  title: string;
  text: string;
  text_truncated: boolean;
  source_url: string;
  source_content_cid: string;
  source_page_cid: string;
  provider_name: string;
  program_name: string;
  categories: string;
  host: string;
  city: string;
  state: string;
}

export interface CorpusDocumentIndex {
  schemaVersion: number;
  count: number;
  docIdToIndex: Record<string, number>;
  contentCidToIndex: Record<string, number>;
}

export interface Bm25Document {
  doc_id: string;
  doc_type: string;
  source_url: string;
  source_content_cid: string;
  source_page_cid: string;
  document_length: number;
  terms: Record<string, number>;
  term_idf?: Record<string, number>;
}

export interface Bm25Payload {
  schemaVersion: number;
  documents: Bm25Document[];
  documentFrequency: Record<string, number>;
  k1: number;
  b: number;
  avgdl: number;
  documentCount: number;
  maxTermsPerDocument: number;
}

export interface EmbeddingIndex {
  schemaVersion: number;
  count: number;
  dimension: number;
  embeddingModel: string;
  browserEmbeddingModel: string;
  binary: string;
  doc_ids: string[];
  source_content_cids: string[];
  source_page_cids: string[];
  source_urls: string[];
}

export interface GraphNode {
  node_id: string;
  node_type: string;
  label: string;
  [key: string]: string | number | boolean | null | undefined;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  edge_cid: string;
  bm25_score?: number;
  tf?: number;
  idf?: number;
  shared_document_count?: number;
  cooccurrence_score?: number;
  source_content_cid?: string;
}

export interface GraphNeighborhood {
  node_ids: string[];
  edge_ids: string[];
}

export interface GraphNeighborhoodShardRecord {
  id: string;
  path: string;
  bytes: number;
  cid: string;
  documentCount: number;
  nodeCount: number;
  edgeCount: number;
  firstDocId: string;
  lastDocId: string;
}

export interface GraphNeighborhoodIndex {
  schemaVersion: number;
  maxEdgesPerDocument: number;
  neighborhoodCount: number;
  shardSize: number;
  shardCount: number;
  shards: GraphNeighborhoodShardRecord[];
  docIdToShard: Record<string, string>;
}

export interface GraphNeighborhoodShard {
  schemaVersion: number;
  shardId: string;
  maxEdgesPerDocument: number;
  doc_ids: string[];
  nodes: Record<string, GraphNode>;
  edges: Record<string, GraphEdge>;
  neighborhoods: Record<string, GraphNeighborhood>;
}

export interface GraphCommunity {
  community_id: string;
  community_cid: string;
  label: string;
  node_count: number;
  document_count: number;
  page_count: number;
  service_count: number;
  keyterm_count: number;
  provider_count: number;
  category_count: number;
  top_terms: Array<[string, number]>;
  top_categories: Array<[string, number]>;
  top_hosts: Array<[string, number]>;
}

export interface DocumentCommunity {
  doc_id: string;
  doc_type: string;
  source_url: string;
  source_content_cid: string;
  source_page_cid: string;
  community_id: string;
  community_label: string;
}

export interface SearchFilters {
  docTypes?: string[];
  city?: string;
  state?: string;
  host?: string;
  limit?: number;
}

export interface SearchResult {
  docId: string;
  contentCid: string;
  pageCid: string;
  document: CorpusDocument;
  score: number;
  scoreParts: {
    keyword: number;
    vector: number;
    metadata: number;
  };
  snippet: string;
}

export interface GraphRagEvidence {
  query: string;
  results: SearchResult[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}
