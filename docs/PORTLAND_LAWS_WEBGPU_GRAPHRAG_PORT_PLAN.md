# Portland Laws WebGPU GraphRAG Port Plan

Reviewed source repository: `https://github.com/portland-laws/portland-laws.github.io`

Reviewed local clone: `/tmp/portland-laws.github.io.review`

Reviewed commit: `168b7300b7acd662ae3c3a8a71cc819a3cf6167a`

Target repository: `211-AI`

## Current Implementation Status

Implemented in this repository:

- Browser corpus exporter: `scraper/browser_graphrag_corpus.py`
- Export CLI: `scripts/build_browser_graphrag_corpus.py`
- Export tests: `tests/test_browser_graphrag_corpus.py`
- Static browser corpus: `wallet_interface/ui/public/corpus/211-info/current`
- Frontend GraphRAG modules: `wallet_interface/ui/src/lib/graphrag/*`
- Browser backend detection: `wallet_interface/ui/src/lib/backendDetection.ts`
- Local embedding worker/service: `wallet_interface/ui/src/workers/embeddingWorker.ts` and `wallet_interface/ui/src/lib/clientEmbeddingWorkerService.ts`
- Local LLM worker/service: `wallet_interface/ui/src/workers/clientLLMWorker.ts` and `wallet_interface/ui/src/lib/clientLLMWorkerService.ts`
- High-level UI-facing service: `wallet_interface/ui/src/services/graphRagService.ts`

Current generated corpus checkpoint:

- Documents: `22,640`
- Embeddings: `22,640` vectors, `384` dimensions, source model `BAAI/bge-small-en-v1.5`
- Graph neighborhoods: `22,640`
- Graph neighborhood shards: `46`
- Graph communities: `41`
- Browser artifact manifest CID: `bafkreiccipcyn7shu5kke2dlutsp2zz27gkkh6iuj3qzyevylifwhusmhe`
- Generated manifest CID: `bafkreien2rm4gcsgr4p52cokznlyzwl6fmb6ymrfltby6yd5sw3c5uianm`

Validation completed:

- `python -m pytest tests/test_browser_graphrag_corpus.py tests/test_retrieval_package.py -q`
- `python -m compileall scraper scripts tests -q`
- `npx tsc --noEmit`
- `npm run build`

Open work:

- Add a visible UI entry point for 211 GraphRAG search/answering.
- Add browser smoke tests that exercise `search211Info()` through Vite/Playwright.
- Decide whether to keep the current full JSON corpus layout or add smaller BM25/document shards for lower-memory mobile browsers.
- Validate browser vector retrieval quality between Python-generated `BAAI/bge-small-en-v1.5` vectors and browser-side `Xenova/bge-small-en-v1.5` query vectors.

## Goal

Port the Portland Laws browser-native language modeling and GraphRAG pattern into
this repository so the 211 corpus can run retrieval, graph expansion, and local
answer generation serverlessly in the browser using WebGPU/WebNN/WASM-capable
paths where available.

The target runtime should work without a server-side LLM call:

1. Load static 211 corpus artifacts from Vite public assets or Hugging Face.
2. Run BM25, vector, and graph retrieval in browser workers.
3. Generate query embeddings locally with Transformers.js.
4. Generate grounded answers locally with a browser model when hardware supports it.
5. Fall back to citation-rich evidence summaries when local model inference is not available.

## Source Repository Review

The Portland Laws repo is a Vite/React static site with a prepared legal corpus
and browser-native GraphRAG. The relevant implementation is concentrated in a
small set of files, even though the repo also contains game, logic, and old
AI Town code.

Important source files:

- `package.json`
- `vite.config.ts`
- `index.html`
- `CLIENT_LLM_IMPLEMENTATION.md`
- `MODEL_GUIDE.md`
- `ARCHITECTURE.md`
- `scripts/prepare-portland-corpus.mjs`
- `scripts/extract-portland-corpus.py`
- `src/lib/llmConfig.ts`
- `src/lib/backendDetection.ts`
- `src/workers/clientLLMWorker.ts`
- `src/lib/clientLLMWorkerService.ts`
- `src/workers/embeddingWorker.ts`
- `src/lib/clientEmbeddingWorkerService.ts`
- `src/lib/portlandCorpus.ts`
- `src/lib/portlandGraphRag.ts`
- `src/lib/portlandLogic.ts`

Relevant dependencies in the source repo:

- `@xenova/transformers`
- `onnxruntime-web`
- `parquet-wasm`
- `@duckdb/duckdb-wasm`
- `hnswlib-wasm`
- React/Vite/TypeScript

Only some of these are essential for the first port. The source runtime's core
RAG path uses Transformers.js, generated JSON, and `Float32Array` embeddings.
It does not require DuckDB-WASM or hnswlib-WASM for the current search path.

## Source Architecture

The source browser stack has four main layers.

**1. Hardware Detection**

`src/lib/backendDetection.ts` checks browser support for:

- WebNN: feature detection and benchmarking only
- WebGPU: adapter/device creation and FLOPS benchmark
- WASM
- WebGL
- WASM SIMD
- WASM threads via `SharedArrayBuffer`

Important finding: WebNN is not currently used as a real Transformers.js or
ONNX inference provider in the source code. It is detected and benchmarked, but
the actual model path is WebGPU or WASM.

**2. Local LLM Runtime**

`src/workers/clientLLMWorker.ts` runs text generation in a web worker using
`@xenova/transformers`. It detects WebGPU and SIMD, configures ONNX Runtime
where possible, loads a text generation pipeline, and falls back to
`Xenova/distilgpt2` when larger models fail.

`src/lib/clientLLMWorkerService.ts` wraps worker calls with request IDs,
timeouts, model switching, and prompt formatting.

`src/lib/llmConfig.ts` defines supported models:

- `Xenova/distilgpt2`
- `Xenova/gpt2`
- `Xenova/LaMini-GPT-774M`
- `onnx-community/Llama-3.2-1B-Instruct`
- `onnx-community/Llama-3.2-3B-Instruct`
- `webml-community/qwen3-webgpu`
- `webml-community/deepseek-r1-webgpu`

Practical finding: the large WebGPU models are aspirational for many browsers.
The production-safe default should remain a small WASM-compatible model and an
evidence-summary fallback.

**3. Local Embedding Runtime**

`src/workers/embeddingWorker.ts` uses `@xenova/transformers` feature extraction
with `Xenova/gte-small`, mean pooling, normalization, and browser cache.

`src/lib/clientEmbeddingWorkerService.ts` wraps embedding worker requests.

This is directly portable, with one important adjustment: our generated
embeddings currently use `BAAI/bge-small-en-v1.5`, so the browser query model
must use a compatible browser model or we need to rebuild exported embeddings
for a browser-compatible model. For first implementation, use a manifest field
that explicitly declares the query model and block vector search if dimensions
or model family do not match.

**4. Static Corpus and GraphRAG**

`scripts/prepare-portland-corpus.mjs` downloads canonical Parquet assets from a
Hugging Face dataset and writes an artifacts manifest.

`scripts/extract-portland-corpus.py` converts Parquet assets into browser-friendly
files:

- `generated/sections.json`
- `generated/section-index.json`
- `generated/bm25-documents.json`
- `generated/embedding-index.json`
- `generated/embeddings.f32`
- `generated/entities.json`
- `generated/relationships.json`
- `generated/graph-adjacency.json`
- `generated/logic-proof-summaries.json`
- `generated/generated-manifest.json`

`src/lib/portlandCorpus.ts` loads those static files and provides:

- keyword BM25 search
- brute-force vector search over `Float32Array`
- hybrid scoring
- graph neighborhood expansion from adjacency JSON
- section-scoped GraphRAG evidence construction

`src/lib/portlandGraphRag.ts` builds a grounded prompt with evidence, graph
context, and logic metadata. It uses the local LLM worker when available and
falls back to a deterministic evidence summary when local inference fails.

## Source Constraints and Issues

These are important before porting.

- WebNN is detection-only. Calling this a WebNN inference stack would be inaccurate until a real WebNN execution provider is wired.
- The source vector search is brute force. That is fine for Portland's 3,052 sections, but the 211 package has 22,640 documents. It is still feasible in a worker with 384-dim vectors, but it should not run on the main thread.
- The source graph adjacency is very large JSON for its corpus. Our 211 graph has 48,864 nodes and 649,052 edges, so shipping a full all-edge adjacency JSON eagerly would be too heavy.
- The source relies on cross-origin isolation headers for `SharedArrayBuffer` and WASM threading. The target Vite config must add COOP/COEP headers for dev and deployment must preserve them.
- Large local LLM models can require hundreds of MB to multiple GB of browser cache and memory. The product path must make smaller defaults useful.
- The source uses `@xenova/transformers` v2.17.2. Newer Transformers.js packages may change model IDs, device options, and WebGPU support. We should pin initially, then upgrade deliberately.

## Target Repository State

This repo already has a strong backend packaging pipeline:

- `scraper/build_retrieval_package.py`
- `data/retrieval_package/content/documents.parquet`
- `data/retrieval_package/retrieval/bm25_documents.parquet`
- `data/retrieval_package/retrieval/bm25_terms.parquet`
- `data/retrieval_package/retrieval/vector_embeddings.parquet`
- `data/retrieval_package/graph/knowledge_graph_nodes.parquet`
- `data/retrieval_package/graph/knowledge_graph_edges.parquet`
- `data/retrieval_package/graph/graph_node_metrics.parquet`
- `data/retrieval_package/graph/graph_communities.parquet`
- `data/retrieval_package/graph/document_communities.parquet`
- Hugging Face dataset: `endomorphosis/211-info`

Current package counts:

- documents: `22,640`
- page documents: `11,787`
- service documents: `10,853`
- BM25 term rows: `3,265,286`
- embeddings: `22,640`
- graph nodes: `48,864`
- graph edges: `649,052`
- graph communities: `41`

The frontend target is `wallet_interface/ui`, which is a Vite/React app. The
current service screen is static and uses `serviceMatches` from
`wallet_interface/ui/src/services/mockAbbyService.ts`.

## Port Strategy

Do not copy the Portland app wholesale. Port the runtime pattern into a
211-specific module tree and generate browser artifacts from this repo's
existing CID-indexed Parquet package.

Recommended target layout:

```text
wallet_interface/ui/public/corpus/211-info/current/
  artifacts.manifest.json
  generated/
    documents.json
    document-index.json
    bm25-documents.json
    embedding-index.json
    embeddings.f32
    graph-neighborhoods.json
    graph-communities.json
    document-communities.json
    generated-manifest.json

wallet_interface/ui/src/lib/graphrag/
  types.ts
  backendDetection.ts
  llmConfig.ts
  corpus.ts
  search.ts
  graph.ts
  prompts.ts
  answer.ts

wallet_interface/ui/src/workers/
  llmWorker.ts
  embeddingWorker.ts
  ragSearchWorker.ts

wallet_interface/ui/src/services/
  graphRagService.ts
```

Recommended backend/export script:

```text
scripts/build_browser_graphrag_corpus.py
```

This script should read `data/retrieval_package` Parquet artifacts and write
browser-ready files under `wallet_interface/ui/public/corpus/211-info/current`.

## Artifact Design for 211

The source Portland generated files are a good starting point, but the 211 graph
is bigger. Use a more selective browser export.

**Required generated artifacts**

- `documents.json`: compact document rows keyed by `source_content_cid` and `doc_id`
- `document-index.json`: `doc_id -> row index` and `source_content_cid -> row index`
- `embedding-index.json`: count, dimension, model, binary path, doc IDs, content CIDs
- `embeddings.f32`: contiguous little-endian float32 vectors
- `bm25-documents.json`: compact per-document term frequencies or top term postings
- `graph-communities.json`: community summary rows from `graph_communities.parquet`
- `document-communities.json`: document-to-community lookup
- `graph-neighborhoods.json`: bounded graph neighborhoods for documents and key terms
- `generated-manifest.json`: sizes, counts, schema version, source package CID

**Avoid for first browser build**

- Do not eagerly ship every graph edge as full JSON.
- Do not eagerly ship all `3,265,286` BM25 rows as uncompressed row JSON.
- Do not run Parquet parsing in the main UI thread.

**Graph export rule**

For each document node:

- Include direct `HAS_KEYTERM`, `DERIVED_FROM_PAGE`, `IN_CATEGORY`, `LOCATED_IN`, and `PROVIDES_SERVICE` edges.
- Include top-N `CO_OCCURS_WITH` keyterm edges by score.
- Include community labels and top community terms.
- Keep full graph Parquet downloadable for advanced tooling, but use bounded neighborhoods for browser answer generation.

This keeps serverless GraphRAG responsive while preserving CID traceability.

## Runtime Design

**RAG search worker**

`ragSearchWorker.ts` should own:

- corpus loading and caching
- BM25 scoring
- vector scoring over `Float32Array`
- hybrid score fusion
- graph expansion
- community lookup

The main thread should only call:

```ts
search211Corpus(query, options)
answer211GraphRag(question, options)
```

**Embedding worker**

Port `embeddingWorker.ts` and `clientEmbeddingWorkerService.ts`, but rename for
211 and make the model explicit from the corpus manifest.

First compatible options:

- Rebuild the package embeddings with `Xenova/gte-small` compatible output.
- Or use `BAAI/bge-small-en-v1.5` only if a browser-compatible Transformers.js
  model produces the same dimension and semantic space.

Until that is confirmed, vector search must gracefully degrade to BM25 plus graph
community expansion.

**LLM worker**

Port `clientLLMWorker.ts`, `clientLLMWorkerService.ts`, and `llmConfig.ts`, but
change prompts from character dialogue to grounded service navigation.

Recommended defaults:

- Default model: `Xenova/distilgpt2` only for smoke compatibility, but do not rely on it for production answer quality.
- Recommended local answer model: a small instruction model that Transformers.js can run in WebGPU/WASM reliably after validation.
- Always keep deterministic evidence-summary fallback.

**Backend detection**

Port `backendDetection.ts`, but label capabilities accurately:

- `webgpu`: usable for Transformers.js/ONNX acceleration if model supports it
- `wasm`: baseline inference path
- `simd`: optimization capability
- `threads`: only when COOP/COEP enables `SharedArrayBuffer`
- `webnn`: experimental detection, not an inference provider until wired

## Prompt Design for 211 GraphRAG

The 211 answer prompt should be stricter than the Portland prompt because users
may rely on service access information.

Prompt rules:

- Use only retrieved evidence.
- Cite every factual sentence with source numbers.
- Include provider/program name, phone, URL, location, and eligibility only when evidence contains it.
- Say when evidence is insufficient.
- State that information may have changed and link to the source page.
- Do not infer eligibility, availability, or legal/medical advice.

Fallback answer should list top evidence rows with citations and source URLs
without invoking a model.

## UI Integration

The first UI integration should be in the existing Services screen:

- Add a search box.
- Add a mode selector: keyword, vector, hybrid.
- Add result cards with provider, program, category, phone, city/state, and source URL.
- Add a "Ask local GraphRAG" panel that returns a cited answer.
- Add runtime status badges for WebGPU/WASM/local model/vector index availability.
- Keep the existing wallet privacy framing: service matching should use user-entered needs or coarse wallet-derived facts, not precise location unless explicitly converted to a coarse claim.

Suggested target file changes:

- `wallet_interface/ui/package.json`
- `wallet_interface/ui/vite.config.ts`
- `wallet_interface/ui/index.html`
- `wallet_interface/ui/src/app/App.tsx`
- `wallet_interface/ui/src/lib/graphrag/*`
- `wallet_interface/ui/src/workers/*`
- `wallet_interface/ui/src/services/graphRagService.ts`
- `wallet_interface/ui/tests/smoke.spec.ts`

## Phased Implementation Plan

**Phase 1: Browser corpus exporter**

- Add `scripts/build_browser_graphrag_corpus.py`.
- Read local retrieval package Parquet artifacts.
- Write compact browser assets to `wallet_interface/ui/public/corpus/211-info/current`.
- Include CID fields in every document and graph lookup.
- Add a small fixture test that verifies counts, embedding dimensions, and manifest consistency.

Acceptance criteria:

- `documents.json` row count matches `documents.parquet`.
- `embedding-index.json.count` matches `vector_embeddings.parquet`.
- `document-communities.json` covers every document.
- Generated files load with plain `fetch`.

**Phase 2: Frontend dependency and isolation setup**

- Add `@xenova/transformers` and `onnxruntime-web` to `wallet_interface/ui`.
- Consider `parquet-wasm` only for advanced direct-Parquet loading, not the first path.
- Add Vite dev headers:
  - `Cross-Origin-Embedder-Policy: require-corp`
  - `Cross-Origin-Opener-Policy: same-origin`
- Add matching meta tags to `index.html`.
- Verify the app still builds and Playwright smoke tests still run.

Acceptance criteria:

- `npm run build` passes.
- `crossOriginIsolated` is true in Chromium dev server when headers are active.
- Existing wallet UI still loads.

**Phase 3: Port runtime services**

- Port and adapt `backendDetection.ts`.
- Port and adapt `embeddingWorker.ts`.
- Port and adapt `clientEmbeddingWorkerService.ts`.
- Port and adapt `clientLLMWorker.ts`.
- Port and adapt `clientLLMWorkerService.ts`.
- Rename modules into a `graphrag` namespace so Portland-specific naming does not leak into 211.

Acceptance criteria:

- Runtime status detects WebGPU/WASM/SIMD without crashing.
- Embedding worker loads or reports an actionable fallback.
- LLM worker can initialize the default model or explicitly report fallback mode.

**Phase 4: Implement 211 search and graph expansion**

- Implement corpus loader.
- Implement BM25 search over generated data.
- Implement vector search in `ragSearchWorker.ts`.
- Implement hybrid score fusion.
- Implement graph expansion using bounded neighborhoods and community labels.
- Return `GraphRagEvidence` with documents, services, graph nodes, graph edges, and communities.

Acceptance criteria:

- Query `shelter tonight` returns shelter/service rows.
- Query `food pantry` returns food-related services.
- Search worker does not block UI during index load or scoring.
- Result rows include source CIDs and source URLs.

**Phase 5: Implement answer generation**

- Build a 211-specific grounded prompt.
- Add deterministic evidence summary fallback.
- Add local model answer generation.
- Reject ungrounded model output that lacks citations.
- Cap context length and include only top evidence plus compact graph context.

Acceptance criteria:

- Every accepted model answer includes citations.
- When model fails or is disabled, evidence summary still works.
- No server-side API is required for answer generation.

**Phase 6: Services screen integration**

- Replace static `serviceMatches` display with live GraphRAG search.
- Preserve existing mock data as a fallback.
- Add runtime status, search controls, and cited answer panel.
- Keep mobile layout usable and avoid loading models until the user asks for an answer.

Acceptance criteria:

- Initial screen loads without downloading an LLM.
- Search works before model initialization.
- Local answer generation is opt-in or lazy.
- UI remains responsive on mobile.

**Phase 7: Tests and validation**

- Add TypeScript unit tests for tokenization, BM25, hybrid scoring, graph expansion, and prompt grounding checks.
- Add worker integration tests where feasible.
- Add Playwright tests for:
  - search results render
  - answer fallback renders with citations
  - model disabled path works
  - keyboard navigation on Services screen
- Add a corpus manifest validation test.

Acceptance criteria:

- `npm run build` passes.
- `npm run test:smoke` passes.
- Python exporter tests pass.

**Phase 8: Hugging Face and deployment polish**

- Upload browser-generated artifacts to `endomorphosis/211-info` under a separate path such as `browser/211-info/current`.
- Add manifest fields linking:
  - source Parquet artifact CIDs
  - generated browser artifact CIDs
  - build timestamp
  - embedding model and dimension
- Support loading from either bundled `public/` assets or the Hugging Face dataset URL.

Acceptance criteria:

- Static app can run entirely from bundled assets.
- Static app can also fetch browser artifacts from Hugging Face when configured.
- Manifest CID links browser files back to source Parquet artifacts.

## Migration Mapping

| Portland source | 211 target | Action |
| --- | --- | --- |
| `src/lib/backendDetection.ts` | `wallet_interface/ui/src/lib/graphrag/backendDetection.ts` | Port and rename. Clarify WebNN as detection-only. |
| `src/lib/llmConfig.ts` | `wallet_interface/ui/src/lib/graphrag/llmConfig.ts` | Port with 211 defaults and safer model list. |
| `src/workers/clientLLMWorker.ts` | `wallet_interface/ui/src/workers/llmWorker.ts` | Port, adjust prompts and output validation. |
| `src/lib/clientLLMWorkerService.ts` | `wallet_interface/ui/src/lib/graphrag/llmWorkerService.ts` | Port request/timeout wrapper. |
| `src/workers/embeddingWorker.ts` | `wallet_interface/ui/src/workers/embeddingWorker.ts` | Port with manifest-driven model. |
| `src/lib/clientEmbeddingWorkerService.ts` | `wallet_interface/ui/src/lib/graphrag/embeddingWorkerService.ts` | Port request wrapper. |
| `scripts/extract-portland-corpus.py` | `scripts/build_browser_graphrag_corpus.py` | Reimplement for 211 Parquet schema. |
| `src/lib/portlandCorpus.ts` | `wallet_interface/ui/src/lib/graphrag/corpus.ts`, `search.ts`, `graph.ts` | Adapt to 211 document/service schemas. |
| `src/lib/portlandGraphRag.ts` | `wallet_interface/ui/src/lib/graphrag/answer.ts`, `prompts.ts` | Adapt to service navigation and source citations. |
| `public/corpus/portland-or/current/generated/*` | `wallet_interface/ui/public/corpus/211-info/current/generated/*` | Generate from 211 package, do not copy Portland data. |

## Risks

- Browser memory: full 211 embeddings are manageable, but full graph JSON can be too heavy. Use bounded neighborhoods and lazy loading.
- Model quality: small browser LLMs may produce weak answers. Keep retrieval and evidence summary useful without generation.
- WebGPU availability: many users will not have reliable WebGPU. WASM and no-model fallback must be first-class.
- WebNN maturity: WebNN support is still limited and source repo does not use it for real inference. Treat it as future capability.
- COOP/COEP: required for WASM threads but can break cross-origin resources unless they send compatible headers.
- Embedding compatibility: offline `BAAI/bge-small-en-v1.5` vectors must match the browser query embedding model, or vector search scores are invalid.
- Bundle size: do not import Transformers.js into the main bundle. Keep it worker-only and lazy.

## Recommended First Slice

The best first implementation slice is:

1. Build browser corpus exporter from current `data/retrieval_package`.
2. Add a search worker that supports BM25 plus community-aware graph expansion.
3. Add Services screen search UI using deterministic evidence summaries.
4. Add embedding worker and vector search after model compatibility is verified.
5. Add local LLM answer generation last.

This ordering gives useful serverless GraphRAG without waiting on browser model
performance, and it keeps the high-risk WebGPU model path isolated.

## Definition of Done

The port is complete when:

- The Services screen can search the 211 corpus with no backend API.
- Results are traceable to `source_content_cid`, `source_page_cid`, and source URL.
- Graph context includes communities and bounded neighboring nodes.
- Browser-side BM25 works on all modern browsers.
- Browser-side vector search works when embedding compatibility is verified.
- Browser-side local answer generation works when supported, with cited output.
- The app has deterministic no-model fallback output.
- Generated browser artifacts are published to Hugging Face with CID-linked manifests.
- Existing wallet flows continue to pass their smoke tests.
