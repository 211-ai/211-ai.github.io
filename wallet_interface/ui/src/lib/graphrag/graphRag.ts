import { get211RelatedGraph } from "./corpus";
import { search211Corpus } from "./search";
import type { GraphEdge, GraphNode, GraphRagEvidence, SearchCoordinates, SearchFilters, SearchResult } from "./types";

export interface GraphRagAnswer {
  question: string;
  answer: string;
  evidence: GraphRagEvidence;
  usedLocalModel: boolean;
}

export const DEFAULT_GRAPH_RAG_MODEL_MAX_TOKENS = 150;

interface GraphRagPromptOptions {
  maxResults?: number;
  excerptCharacters?: number;
  graphNodeLimit?: number;
  graphEdgeLimit?: number;
}

export async function build211GraphRagEvidence(
  query: string,
  options: {
    queryEmbedding?: Float32Array | number[];
    filters?: SearchFilters;
    limit?: number;
    preferredClusterIds?: number[];
    currentCoordinates?: SearchCoordinates;
  } = {},
): Promise<GraphRagEvidence> {
  const results = await search211Corpus(query, {
    filters: options.filters,
    mode: options.queryEmbedding ? "hybrid" : "keyword",
    queryEmbedding: options.queryEmbedding,
    limit: options.limit || 6,
    preferredClusterIds: options.preferredClusterIds,
    currentCoordinates: options.currentCoordinates,
  });
  const related = await get211RelatedGraph(results.map((result) => result.docId));
  return {
    query,
    results,
    nodes: related.nodes,
    edges: related.edges,
  };
}

export async function answerWith211GraphRag(
  question: string,
  options: {
    queryEmbedding?: Float32Array | number[];
    useLocalModel?: boolean;
    maxTokens?: number;
  } = {},
): Promise<GraphRagAnswer> {
  const trimmedQuestion = question.trim();
  if (!trimmedQuestion) {
    throw new Error("Question is required");
  }

  const evidence = await build211GraphRagEvidence(trimmedQuestion, {
    queryEmbedding: options.queryEmbedding,
    limit: 6,
  });

  if (options.useLocalModel === false || shouldDisableLocalLlm()) {
    return {
      question: trimmedQuestion,
      answer: buildEvidenceSummary(evidence.results),
      evidence,
      usedLocalModel: false,
    };
  }

  try {
    const { clientLLMWorkerService } = await import("../clientLLMWorkerService");
    const rawAnswer = await clientLLMWorkerService.generateText(
      build211GraphRagPrompt(trimmedQuestion, evidence),
      options.maxTokens || DEFAULT_GRAPH_RAG_MODEL_MAX_TOKENS,
    );
    const answer = clean211GraphRagModelAnswer(rawAnswer);
    return {
      question: trimmedQuestion,
      answer: isGrounded211GraphRagAnswer(answer) ? answer : buildEvidenceSummary(evidence.results),
      evidence,
      usedLocalModel: isGrounded211GraphRagAnswer(answer),
    };
  } catch (error) {
    console.warn("211 GraphRAG local model unavailable; falling back to evidence summary", error);
    return {
      question: trimmedQuestion,
      answer: buildEvidenceSummary(evidence.results),
      evidence,
      usedLocalModel: false,
    };
  }
}

export function build211GraphRagPrompt(
  question: string,
  evidence: GraphRagEvidence,
  options: GraphRagPromptOptions = {},
): string {
  const maxResults = options.maxResults ?? 4;
  const excerptCharacters = options.excerptCharacters ?? 420;
  const evidenceBlock = evidence.results
    .slice(0, maxResults)
    .map((result, index) => {
      const document = result.document;
      const label = document.provider_name || document.program_name || document.title || document.doc_id;
      return [
        `[${index + 1}] ${label}`,
        `Program: ${document.program_name || "not listed"}`,
        `Categories: ${document.categories || "not listed"}`,
        `Location: ${[document.city, document.state].filter(Boolean).join(", ") || "not listed"}`,
        `Source: ${document.source_url || document.source_content_cid || document.doc_id}`,
        `Excerpt: ${cleanExcerpt(result.snippet || document.text, excerptCharacters)}`,
      ].join("\n");
    })
    .join("\n\n");

  return `You are Abby, answering a public 211 service-navigation question.
Use only the evidence below. Do not use outside knowledge.
Do not invent phone numbers, hours, addresses, eligibility rules, availability, or application steps.
This is not emergency, medical, legal, or eligibility advice.

Question: ${question}

Evidence:
${evidenceBlock}

Related graph hints:
${formatGraphContext(evidence.nodes, evidence.edges, {
  nodeLimit: options.graphNodeLimit ?? 8,
  edgeLimit: options.graphEdgeLimit ?? 8,
})}

Write the answer in this format:
- Direct answer: 1-2 short sentences. Cite each factual sentence with [1], [2], etc.
- Best matches: up to 3 bullets with the provider/program and why it matches. Cite every bullet.
- Missing or confirm: one short sentence naming details the evidence does not prove, if any.

Keep it under 120 words. Return only the answer.`;
}

export function buildEvidenceSummary(results: SearchResult[]): string {
  const lead = results
    .slice(0, 4)
    .map((result, index) => {
      const document = result.document;
      const label = document.provider_name || document.program_name || document.title || result.docId;
      return `[${index + 1}] ${label}: ${cleanExcerpt(result.snippet || document.text.slice(0, 500))}`;
    })
    .join("\n\n");

  return `The strongest local 211 corpus matches are:\n\n${lead}\n\nUse the cited source pages or contact 211/the listed provider to confirm current availability and eligibility.`;
}

function formatGraphContext(
  nodes: GraphNode[],
  edges: GraphEdge[],
  options: { nodeLimit?: number; edgeLimit?: number } = {},
): string {
  const visibleNodes = nodes.slice(0, options.nodeLimit ?? 18);
  const visibleNodeIds = new Set(visibleNodes.map((node) => node.node_id));
  const nodeLabels = new Map(visibleNodes.map((node) => [node.node_id, `${node.label} (${node.node_type})`]));
  const nodeLines =
    visibleNodes
      .map((node) => `- ${nodeLabels.get(node.node_id)}`)
      .join("\n") || "- None retrieved.";
  const edgeLines =
    edges
      .filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
      .slice(0, options.edgeLimit ?? 18)
      .map((edge) => {
        const source = nodeLabels.get(edge.source) || edge.source;
        const target = nodeLabels.get(edge.target) || edge.target;
        return `- ${source} ${edge.relation.replace(/_/g, " ").toLowerCase()} ${target}`;
      })
      .join("\n") || "- None retrieved.";
  return `Entities:\n${nodeLines}\nRelationships:\n${edgeLines}`;
}

function shouldDisableLocalLlm(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem("211_DISABLE_LOCAL_LLM") === "true";
}

export function clean211GraphRagModelAnswer(answer: string): string {
  return answer
    .replace(/<\|[^>]+?\|>/g, "")
    .replace(/^answer:\s*/i, "")
    .trim();
}

export function isGrounded211GraphRagAnswer(answer: string): boolean {
  return answer.length >= 24 && /\[[1-6]\]/.test(answer);
}

function cleanExcerpt(excerpt: string, maxCharacters = 500): string {
  const normalized = excerpt.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxCharacters) return normalized;
  const truncated = normalized.slice(0, maxCharacters).replace(/\s+\S*$/, "").trim();
  return `${truncated}...`;
}
