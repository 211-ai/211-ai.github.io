import { get211RelatedGraph } from "./corpus";
import { search211Corpus } from "./search";
import type { GraphEdge, GraphNode, GraphRagEvidence, SearchResult } from "./types";

export interface GraphRagAnswer {
  question: string;
  answer: string;
  evidence: GraphRagEvidence;
  usedLocalModel: boolean;
}

export async function build211GraphRagEvidence(
  query: string,
  options: {
    queryEmbedding?: Float32Array | number[];
    limit?: number;
  } = {},
): Promise<GraphRagEvidence> {
  const results = await search211Corpus(query, {
    mode: options.queryEmbedding ? "hybrid" : "keyword",
    queryEmbedding: options.queryEmbedding,
    limit: options.limit || 6,
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
  if (evidence.results.length === 0) {
    return {
      question: trimmedQuestion,
      answer:
        "I could not find a relevant record in the local 211 corpus for that question. For immediate service navigation, contact 211 directly.",
      evidence,
      usedLocalModel: false,
    };
  }

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
      options.maxTokens || 220,
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

export function build211GraphRagPrompt(question: string, evidence: GraphRagEvidence): string {
  const evidenceBlock = evidence.results
    .map((result, index) => {
      const document = result.document;
      return `[${index + 1}] ${document.title || document.provider_name || document.doc_id}
Type: ${document.doc_type}
Provider: ${document.provider_name || "not listed"}
Program: ${document.program_name || "not listed"}
Categories: ${document.categories || "not listed"}
Location: ${[document.city, document.state].filter(Boolean).join(", ") || "not listed"}
Source: ${document.source_url}
Content CID: ${document.source_content_cid}
Excerpt: ${cleanExcerpt(result.snippet || document.text.slice(0, 900))}`;
    })
    .join("\n\n");

  return `You answer questions about local social services using only the 211 corpus evidence below.
This is service navigation information, not emergency assistance, medical advice, legal advice, or eligibility approval.
If the evidence is incomplete, say what is missing and recommend contacting 211 or the listed provider.
Every factual sentence must cite at least one evidence number like [1] or [2].
Do not invent phone numbers, hours, addresses, eligibility rules, or application steps.

Question: ${question}

Evidence:
${evidenceBlock}

Knowledge graph context:
${formatGraphContext(evidence.nodes, evidence.edges)}

Answer:`;
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

function formatGraphContext(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeLabels = new Map(nodes.map((node) => [node.node_id, `${node.label} (${node.node_type})`]));
  const nodeLines =
    nodes
      .slice(0, 18)
      .map((node) => `- ${nodeLabels.get(node.node_id)}`)
      .join("\n") || "- None retrieved.";
  const edgeLines =
    edges
      .slice(0, 18)
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

function cleanExcerpt(excerpt: string): string {
  return excerpt.replace(/\s+/g, " ").trim();
}
