import { answerWith211GraphRag, build211GraphRagEvidence, search211Corpus } from "../lib/graphrag";
import { clientEmbeddingWorkerService } from "../lib/clientEmbeddingWorkerService";

export async function search211Info(query: string, limit = 10) {
  const queryEmbedding = await tryGenerateQueryEmbedding(query);
  return search211Corpus(query, {
    mode: queryEmbedding ? "hybrid" : "keyword",
    queryEmbedding,
    limit,
  });
}

export async function build211InfoEvidence(query: string, limit = 6) {
  const queryEmbedding = await tryGenerateQueryEmbedding(query);
  return build211GraphRagEvidence(query, { queryEmbedding, limit });
}

export async function answer211InfoQuestion(
  question: string,
  options: {
    useLocalModel?: boolean;
    maxTokens?: number;
  } = {},
) {
  const queryEmbedding = await tryGenerateQueryEmbedding(question);
  return answerWith211GraphRag(question, {
    queryEmbedding,
    useLocalModel: options.useLocalModel,
    maxTokens: options.maxTokens,
  });
}

async function tryGenerateQueryEmbedding(query: string): Promise<Float32Array | undefined> {
  try {
    return await clientEmbeddingWorkerService.generateEmbedding(query);
  } catch (error) {
    console.warn("211 query embedding unavailable; using keyword retrieval only", error);
    return undefined;
  }
}
