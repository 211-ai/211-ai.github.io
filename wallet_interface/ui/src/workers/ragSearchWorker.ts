import { build211GraphRagEvidence } from "../lib/graphrag/graphRag";
import { search211Corpus } from "../lib/graphrag/search";
import type { GraphRagEvidence, SearchMode, SearchResult } from "../lib/graphrag/types";

type RagSearchWorkerRequest =
  | {
      id: string;
      type: "search";
      data: {
        query: string;
        limit?: number;
        mode?: SearchMode;
        queryEmbedding?: number[];
      };
    }
  | {
      id: string;
      type: "evidence";
      data: {
        query: string;
        limit?: number;
        queryEmbedding?: number[];
      };
    }
  | {
      id: string;
      type: "status";
      data?: Record<string, never>;
    };

interface RagSearchWorkerResponse {
  id: string;
  success: boolean;
  data?: {
    results?: SearchResult[];
    evidence?: GraphRagEvidence;
    ready?: boolean;
  };
  error?: string;
}

self.onmessage = async (event: MessageEvent<RagSearchWorkerRequest>) => {
  const { id, type, data } = event.data;

  try {
    if (type === "status") {
      postResponse({ id, success: true, data: { ready: true } });
      return;
    }

    if (type === "search") {
      const queryEmbedding = data.queryEmbedding ? new Float32Array(data.queryEmbedding) : undefined;
      const results = await search211Corpus(data.query, {
        mode: data.mode || (queryEmbedding ? "hybrid" : "keyword"),
        queryEmbedding,
        limit: data.limit || 10,
      });
      postResponse({ id, success: true, data: { results } });
      return;
    }

    if (type === "evidence") {
      const queryEmbedding = data.queryEmbedding ? new Float32Array(data.queryEmbedding) : undefined;
      const evidence = await build211GraphRagEvidence(data.query, {
        queryEmbedding,
        limit: data.limit || 6,
      });
      postResponse({ id, success: true, data: { evidence } });
      return;
    }

    throw new Error(`Unknown 211 GraphRAG worker request: ${type}`);
  } catch (error) {
    postResponse({
      id,
      success: false,
      error: error instanceof Error ? error.message : "211 GraphRAG worker failed",
    });
  }
};

function postResponse(response: RagSearchWorkerResponse): void {
  self.postMessage(response);
}

export {};
