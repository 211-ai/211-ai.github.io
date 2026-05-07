import { load211Bm25, load211Documents, load211Embeddings } from "./corpus";
import type { Bm25Document, CorpusDocument, SearchFilters, SearchMode, SearchResult } from "./types";

const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "by",
  "for",
  "from",
  "how",
  "i",
  "in",
  "is",
  "it",
  "near",
  "of",
  "on",
  "or",
  "the",
  "to",
  "with",
]);

interface RankedScore {
  docId: string;
  score: number;
}

export async function search211Corpus(
  query: string,
  options: {
    filters?: SearchFilters;
    mode?: SearchMode;
    queryEmbedding?: Float32Array | number[];
    limit?: number;
    candidateLimit?: number;
  } = {},
): Promise<SearchResult[]> {
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    return [];
  }

  const mode = options.mode || "hybrid";
  const limit = options.limit || options.filters?.limit || 20;
  const candidateLimit = options.candidateLimit || Math.max(limit * 10, 200);

  const [{ documents, documentById }, keywordScores, vectorScores] = await Promise.all([
    load211Documents(),
    mode !== "vector" ? keywordSearch211(trimmedQuery, candidateLimit) : Promise.resolve(new Map<string, number>()),
    mode !== "keyword" && options.queryEmbedding
      ? vectorSearch211(options.queryEmbedding, candidateLimit)
      : Promise.resolve(new Map<string, number>()),
  ]);

  const normalizedKeyword = normalizeScores(keywordScores);
  const normalizedVector = normalizeScores(vectorScores);
  const candidates = new Set([...keywordScores.keys(), ...vectorScores.keys()]);

  if (candidates.size === 0) {
    const loweredQuery = trimmedQuery.toLowerCase();
    for (const document of documents) {
      if (document.title.toLowerCase().includes(loweredQuery)) {
        candidates.add(document.doc_id);
      }
    }
  }

  const results: SearchResult[] = [];
  for (const docId of candidates) {
    const document = documentById.get(docId);
    if (!document || !matchesFilters(document, options.filters)) {
      continue;
    }

    const keyword = normalizedKeyword.get(docId) || 0;
    const vector = normalizedVector.get(docId) || 0;
    const metadata = metadataScore(document, trimmedQuery);
    const score =
      mode === "keyword"
        ? keyword * 2 + metadata
        : mode === "vector"
          ? vector * 2 + metadata * 0.5
          : keyword * 1.4 + vector * 2 + metadata;

    results.push({
      docId,
      contentCid: document.source_content_cid,
      pageCid: document.source_page_cid,
      document,
      score,
      scoreParts: { keyword, vector, metadata },
      snippet: buildSnippet(document.text, trimmedQuery),
    });
  }

  return results.sort((left, right) => right.score - left.score).slice(0, limit);
}

export async function keywordSearch211(query: string, limit = 200): Promise<Map<string, number>> {
  const terms = tokenizeSearchText(query);
  if (terms.length === 0) {
    return new Map();
  }

  const payload = await load211Bm25();
  const ranked: RankedScore[] = [];
  for (const document of payload.documents) {
    const score = scoreBm25Document(document, terms, payload.k1, payload.b, payload.avgdl);
    if (score > 0) {
      ranked.push({ docId: document.doc_id, score });
    }
  }
  ranked.sort((left, right) => right.score - left.score);
  return new Map(ranked.slice(0, limit).map((row) => [row.docId, row.score]));
}

export async function vectorSearch211(
  queryEmbedding: Float32Array | number[],
  limit = 200,
): Promise<Map<string, number>> {
  const { index, vectors } = await load211Embeddings();
  const queryVector = queryEmbedding instanceof Float32Array ? queryEmbedding : new Float32Array(queryEmbedding);
  if (queryVector.length !== index.dimension) {
    throw new Error(`Query embedding dimension ${queryVector.length} did not match ${index.dimension}`);
  }

  const queryNorm = vectorNorm(queryVector);
  if (queryNorm === 0) {
    return new Map();
  }

  const ranked: RankedScore[] = [];
  for (let row = 0; row < index.count; row += 1) {
    const offset = row * index.dimension;
    let dot = 0;
    let candidateNormSquared = 0;
    for (let column = 0; column < index.dimension; column += 1) {
      const value = vectors[offset + column] || 0;
      const queryValue = queryVector[column] || 0;
      dot += value * queryValue;
      candidateNormSquared += value * value;
    }
    const candidateNorm = Math.sqrt(candidateNormSquared);
    if (candidateNorm > 0) {
      ranked.push({ docId: index.doc_ids[row], score: dot / (queryNorm * candidateNorm) });
    }
  }

  ranked.sort((left, right) => right.score - left.score);
  return new Map(ranked.slice(0, limit).map((row) => [row.docId, row.score]));
}

export function tokenizeSearchText(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .split(/\s+/)
    .map((term) => term.trim())
    .filter((term) => term.length > 1 && !STOP_WORDS.has(term));
}

function scoreBm25Document(document: Bm25Document, queryTerms: string[], k1: number, b: number, avgdl: number): number {
  let score = 0;
  const docLength = Math.max(document.document_length || 0, 1);
  const lengthNorm = 1 - b + (b * docLength) / Math.max(avgdl, 1);
  for (const term of queryTerms) {
    const tf = document.terms[term] || 0;
    if (tf <= 0) {
      continue;
    }
    const idf = document.term_idf?.[term] || 1;
    score += idf * ((tf * (k1 + 1)) / (tf + k1 * lengthNorm));
  }
  return score;
}

function normalizeScores(scores: Map<string, number>): Map<string, number> {
  if (scores.size === 0) {
    return new Map();
  }
  const values = [...scores.values()];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) {
    return new Map([...scores.keys()].map((key) => [key, 1]));
  }
  return new Map([...scores.entries()].map(([key, value]) => [key, (value - min) / (max - min)]));
}

function metadataScore(document: CorpusDocument, query: string): number {
  const loweredQuery = query.toLowerCase();
  let score = 0;
  if (document.title.toLowerCase().includes(loweredQuery)) {
    score += 1.5;
  }
  for (const value of [document.provider_name, document.program_name, document.categories, document.city]) {
    if (value && value.toLowerCase().includes(loweredQuery)) {
      score += 0.5;
    }
  }
  return score;
}

function matchesFilters(document: CorpusDocument, filters?: SearchFilters): boolean {
  if (!filters) {
    return true;
  }
  if (filters.docTypes?.length && !filters.docTypes.includes(document.doc_type)) {
    return false;
  }
  if (filters.city && document.city.toLowerCase() !== filters.city.toLowerCase()) {
    return false;
  }
  if (filters.state && document.state.toLowerCase() !== filters.state.toLowerCase()) {
    return false;
  }
  if (filters.host && document.host.toLowerCase() !== filters.host.toLowerCase()) {
    return false;
  }
  return true;
}

function buildSnippet(text: string, query: string, radius = 180): string {
  const cleanText = text.replace(/\s+/g, " ").trim();
  if (!cleanText) {
    return "";
  }
  const terms = tokenizeSearchText(query);
  const loweredText = cleanText.toLowerCase();
  const firstHit = terms
    .map((term) => loweredText.indexOf(term))
    .filter((index) => index >= 0)
    .sort((left, right) => left - right)[0];
  if (firstHit === undefined) {
    return cleanText.slice(0, radius * 2);
  }
  const start = Math.max(0, firstHit - radius);
  const end = Math.min(cleanText.length, firstHit + radius);
  return `${start > 0 ? "..." : ""}${cleanText.slice(start, end)}${end < cleanText.length ? "..." : ""}`;
}

function vectorNorm(vector: Float32Array): number {
  let total = 0;
  for (const value of vector) {
    total += value * value;
  }
  return Math.sqrt(total);
}
