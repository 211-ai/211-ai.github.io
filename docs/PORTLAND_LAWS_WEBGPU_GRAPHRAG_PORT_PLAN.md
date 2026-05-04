# Portland Laws WebGPU/WASM GraphRAG Port Plan

Source repository: https://github.com/portland-laws/portland-laws.github.io

Reviewed local clone: `/tmp/portland-laws-review.cLKXRz/portland-laws.github.io`

Reviewed source commit: `314470dbaf53625d06bdf276f1d2084dc1a7a93f`

Target repository: `211-AI`

## Current Port Status

This repository already has the core serverless GraphRAG path in place for the
211 corpus.

Implemented:

- CID-indexed retrieval package builder: `scraper/build_retrieval_package.py`
- Browser corpus exporter: `scraper/browser_graphrag_corpus.py`
- Browser export CLI: `scripts/build_browser_graphrag_corpus.py`
- Browser corpus tests: `tests/test_browser_graphrag_corpus.py`
- Static browser corpus: `wallet_interface/ui/public/corpus/211-info/current`
- Browser GraphRAG modules: `wallet_interface/ui/src/lib/graphrag/*`
- Browser backend detection: `wallet_interface/ui/src/lib/backendDetection.ts`
- Local embedding worker/service: `wallet_interface/ui/src/workers/embeddingWorker.ts`, `wallet_interface/ui/src/lib/clientEmbeddingWorkerService.ts`
- Local LLM worker/service: `wallet_interface/ui/src/workers/clientLLMWorker.ts`, `wallet_interface/ui/src/lib/clientLLMWorkerService.ts`
- Dedicated GraphRAG retrieval worker: `wallet_interface/ui/src/workers/ragSearchWorker.ts`
- Retrieval worker service: `wallet_interface/ui/src/lib/graphrag/searchWorkerService.ts`
- UI-facing service API: `wallet_interface/ui/src/services/graphRagService.ts`
- Services-screen GraphRAG search and cited-answer UI: `wallet_interface/ui/src/app/App.tsx`
- Services-screen GraphRAG runtime status panel for corpus, retrieval worker, embedding worker, and browser backend capability.
- Retrieval quality benchmark: `scripts/benchmark_211_retrieval.py`
- Vite cross-origin isolation headers for local development: `wallet_interface/ui/vite.config.ts`

Current retrieval package checkpoint:

- Documents: `22,638`
- Page documents: `11,787`
- Service documents: `10,851`
- BM25 term rows: `3,191,432`
- Embeddings: `22,638`
- Embedding model: `BAAI/bge-small-en-v1.5`
- Embedding dimensions: `384`
- PDF and Office/PPTX text extraction: enabled
- Graph nodes: `48,851`
- Graph edges: `648,958`
- Graph communities: `41`
- Document communities: `22,638`
- Build manifest CID: `bafkreihcclqadxrfhx256soxaqdqvc66ejhsuy3krj5bf446zq2miaox4i`

Current browser corpus checkpoint:

- Documents: `22,638`
- Embedding vectors: `22,638`
- BM25 documents: `22,638`
- Graph neighborhoods: `22,638`
- Graph neighborhood shards: `46`
- Graph communities: `41`
- Document communities: `22,638`
- Manifest artifact count: `55`
- Uploaded browser file count: `56`

Published package status:

- Hugging Face dataset: `endomorphosis/211-info`
- Retrieval package upload commit: `47863ed084c0c2054dd680e7ece3fc3978a38bf3`
- Final dataset commit after browser artifact upload: `7e91ace5bc45fc27d2f5e0cabda741fb052be81d`
- `data/content/documents.parquet` local/remote SHA-256: `b3a3041a2c82fbb5adfcf902f3bb6b89bbee6a492d081443e11e65752418549b`
- The full Parquet package under `data/` is uploaded and verified.
- Browser-generated assets under `browser/211-info/current` are uploaded and verified by size and SHA-256 hash.

Validation completed after this review:

- `npm run build` from `wallet_interface/ui`
- `npm run test:smoke` from `wallet_interface/ui`
- `python -m pytest tests/test_office_text_extraction.py tests/test_pdf_text_extraction.py tests/test_browser_graphrag_corpus.py tests/test_retrieval_package.py -q`
- `python -m compileall scraper scripts tests -q`
- `python scripts/audit_hf_retrieval_upload.py --verify-documents-hash`
- `python scripts/upload_hf_browser_artifacts.py --verify-hashes`
- `python scripts/validate_bge_embedding_compat.py --max-document-texts 3`
- `python scripts/benchmark_211_retrieval.py --output data/validation/retrieval_quality_benchmark.json`
- Production-preview click test: searched `food pantry` from `/#/social-services` and received `6 local matches`.
- Hugging Face remote-corpus preview test with `VITE_211_CORPUS_BASE_URL=https://huggingface.co/datasets/endomorphosis/211-info/resolve/main/browser/211-info/current`: searched `food pantry` and received `6 local matches`.
- Non-PDF binary-looking document scan: `0` rows.
- BGE browser/Python compatibility: dimensions match at `384`; cosine range `0.8953` to `0.9734`, mean `0.9395`.
- Retrieval benchmark: `food pantry`, `emergency shelter`, `utility assistance`, `rental assistance`, `mental health crisis support`, and `transportation` all pass top-5 relevance checks for required keyword and hybrid modes.

## Source Repository Findings

The Portland Laws repo is a Vite/React static app. It contains game and logic
code, but the browser language-modeling and RAG implementation is concentrated
in a small subset of files.

Relevant source files:

- `package.json`
- `vite.config.ts`
- `CLIENT_LLM_IMPLEMENTATION.md`
- `MODEL_GUIDE.md`
- `ARCHITECTURE.md`
- `scripts/prepare-portland-corpus.mjs`
- `scripts/extract-portland-corpus.py`
- `src/lib/backendDetection.ts`
- `src/lib/llmConfig.ts`
- `src/lib/clientLLMWorkerService.ts`
- `src/lib/clientEmbeddingWorkerService.ts`
- `src/workers/clientLLMWorker.ts`
- `src/workers/embeddingWorker.ts`
- `src/lib/portlandCorpus.ts`
- `src/lib/portlandGraphRag.ts`
- `src/lib/portlandLogic.ts`
- `src/lib/warningSuppressionUtils.ts`

Relevant source dependencies:

- `@xenova/transformers`
- `onnxruntime-web`
- `@duckdb/duckdb-wasm`
- `parquet-wasm`
- `hnswlib-wasm`
- `hnswlib-node`
- React, Vite, TypeScript, Playwright, Jest

Only `@xenova/transformers` and `onnxruntime-web` are required for the current
211 browser runtime. DuckDB-WASM, Parquet-WASM, and HNSW-WASM are useful future
options, but the first working path should continue to use generated JSON plus
`Float32Array` embeddings because it is simpler to ship, cache, and test.

## Source Architecture

**Backend Detection**

`src/lib/backendDetection.ts` detects WebNN, WebGPU, WASM, WebGL, WASM SIMD, and
WASM threads. It can also benchmark approximate FLOPS for available backends.

Important finding: WebNN is detection-only in the source repo. The actual model
execution path is Transformers.js over WebGPU or WASM. We should not describe
the current port as WebNN inference until an actual WebNN execution provider is
wired and verified.

**Local LLM Worker**

`src/workers/clientLLMWorker.ts` loads Transformers.js `text-generation` models
inside a web worker. It detects WebGPU/SIMD, configures ONNX Runtime options
where available, initializes a model pipeline, and falls back from WebGPU to
WASM when possible.

The source model list includes:

- `Xenova/distilgpt2`
- `Xenova/gpt2`
- `Xenova/LaMini-GPT-774M`
- `onnx-community/Llama-3.2-1B-Instruct`
- `onnx-community/Llama-3.2-3B-Instruct`
- `webml-community/qwen3-webgpu`
- `webml-community/deepseek-r1-webgpu`

For 211, small-model fallback must stay first-class. Larger WebGPU models can
produce better answers, but they have heavy initial downloads and unreliable
availability across user devices.

**Embedding Worker**

`src/workers/embeddingWorker.ts` uses `@xenova/transformers` feature extraction
with mean pooling and normalized output. Portland uses `Xenova/gte-small` for
browser query embeddings against precomputed `thenlper/gte-small` vectors.

For 211, the package currently uses `BAAI/bge-small-en-v1.5`, and the browser
query model defaults to `Xenova/bge-small-en-v1.5`. That is dimension-compatible,
but retrieval quality must be validated empirically because model naming alone
does not prove identical embedding space.

**Static Corpus Builder**

`scripts/prepare-portland-corpus.mjs` downloads Parquet artifacts from a Hugging
Face dataset and writes an artifact manifest.

`scripts/extract-portland-corpus.py` converts those Parquet files into browser
assets:

- `sections.json`
- `section-index.json`
- `bm25-documents.json`
- `embedding-index.json`
- `embeddings.f32`
- `entities.json`
- `relationships.json`
- `graph-adjacency.json`
- `logic-proof-summaries.json`
- `generated-manifest.json`

For 211, this maps to `scraper/browser_graphrag_corpus.py`, which already reads
this repo's Parquet package and exports documents, BM25 data, embeddings, graph
communities, document communities, and sharded graph neighborhoods.

**GraphRAG Runtime**

`src/lib/portlandCorpus.ts` loads static JSON/F32 assets, performs BM25 search,
brute-force vector search, hybrid score fusion, and graph neighborhood expansion.

`src/lib/portlandGraphRag.ts` builds a grounded prompt from retrieved sections,
knowledge graph context, and generated logic metadata. It calls the local LLM
worker when available and falls back to deterministic evidence summaries.

The 211 runtime now follows the same pattern, with service-navigation prompts
and bounded graph neighborhoods instead of full graph adjacency.

## What Was Ported or Adapted

The port intentionally does not copy the Portland app wholesale. The useful
runtime pattern has been adapted into 211-specific code.

Migration mapping:

| Portland source | 211 target | Current state |
| --- | --- | --- |
| `vite.config.ts` COOP/COEP headers | `wallet_interface/ui/vite.config.ts` | Ported |
| `src/lib/backendDetection.ts` | `wallet_interface/ui/src/lib/backendDetection.ts` | Ported, simplified |
| `src/lib/llmConfig.ts` | `wallet_interface/ui/src/lib/llmConfig.ts` | Ported with conservative 211 defaults |
| `src/workers/clientLLMWorker.ts` | `wallet_interface/ui/src/workers/clientLLMWorker.ts` | Ported, simplified |
| `src/lib/clientLLMWorkerService.ts` | `wallet_interface/ui/src/lib/clientLLMWorkerService.ts` | Ported |
| `src/workers/embeddingWorker.ts` | `wallet_interface/ui/src/workers/embeddingWorker.ts` | Ported with BGE default |
| `src/lib/clientEmbeddingWorkerService.ts` | `wallet_interface/ui/src/lib/clientEmbeddingWorkerService.ts` | Ported |
| `scripts/extract-portland-corpus.py` | `scraper/browser_graphrag_corpus.py` | Reimplemented for 211 schema |
| `src/lib/portlandCorpus.ts` | `wallet_interface/ui/src/lib/graphrag/corpus.ts`, `search.ts` | Ported and split |
| `src/lib/portlandGraphRag.ts` | `wallet_interface/ui/src/lib/graphrag/graphRag.ts` | Ported for service navigation |
| Main-thread retrieval in Portland | `wallet_interface/ui/src/workers/ragSearchWorker.ts` | Added for 211 scale |
| `src/lib/warningSuppressionUtils.ts` | Not yet ported | Optional polish |
| Portland logic metadata path | No 211 equivalent yet | Future enhancement |

## Target Runtime Design

The target should run without a backend LLM or search API.

Runtime flow:

1. Load static browser corpus assets from `wallet_interface/ui/public/corpus/211-info/current`.
2. Generate query embeddings in `embeddingWorker.ts` when available.
3. Run BM25/vector/hybrid retrieval in `ragSearchWorker.ts`.
4. Expand evidence through sharded graph neighborhoods and communities.
5. Build a service-navigation prompt with CIDs, source URLs, and compact graph context.
6. Generate an answer in `clientLLMWorker.ts` when the user opts into local generation.
7. Fall back to deterministic evidence summaries when local embedding or LLM inference fails.

The main thread should keep only orchestration, UI state, and result rendering.
Expensive retrieval and model loading should stay in workers.

## 211 Artifact Design

Current generated artifacts:

- `generated/documents.json`
- `generated/document-index.json`
- `generated/bm25-documents.json`
- `generated/embedding-index.json`
- `generated/embeddings.f32`
- `generated/graph-neighborhood-index.json`
- `generated/graph-neighborhoods/shard-*.json`
- `generated/graph-communities.json`
- `generated/document-communities.json`
- `generated/generated-manifest.json`
- `artifacts.manifest.json`

The 211 graph is too large to eagerly ship as one full adjacency JSON. The
current sharded-neighborhood design is the right direction:

- Keep each document connected to bounded direct context.
- Keep high-signal keyterm and co-occurrence edges.
- Keep community labels and top terms.
- Preserve `source_content_cid`, `source_page_cid`, source URL, node CIDs, and edge CIDs.
- Keep full Parquet graph artifacts on Hugging Face for offline or advanced tooling.

## Prompt Policy

The 211 prompt must be stricter than the Portland legal prompt because users may
act on service access information.

Rules:

- Use only retrieved 211 corpus evidence.
- Cite every factual sentence with evidence numbers.
- Include provider, program, phone, source URL, location, hours, and eligibility only when the evidence contains them.
- Do not invent availability, eligibility, addresses, phone numbers, application steps, or medical/legal guidance.
- If evidence is incomplete, say what is missing and recommend contacting 211 or the listed provider.
- Preserve source CIDs in the prompt for traceability, but use human-readable labels in the UI.

## Remaining Work

**Phase 1: UI Entry Point**

- Done: add a visible 211 GraphRAG search and answer panel to the Services screen.
- Done: keep model loading lazy; default BM25/graph search works before any LLM or embedding model is downloaded.
- Done: expose BGE-small hybrid vector search as an explicit browser-model opt-in.
- Done: show query/search/answer status in the Services-screen panel.
- Done: guard search and answer state against stale async responses.
- Done: expose lower-level corpus, retrieval worker, embedding worker, WebGPU/WASM, and cross-origin isolation status for diagnostics.
- Remaining: expose local LLM initialization status after model-selection UI is designed.

Acceptance criteria:

- Confirmed: searching `food pantry` returns cited 211 results.
- Done: `shelter` and `utility assistance` pass the benchmark top-5 relevance checks.
- Done: the first screen does not download an LLM.
- Done: the no-model evidence summary path works on desktop and mobile.

**Phase 2: Browser Artifact Upload**

- Done: upload generated browser assets to `endomorphosis/211-info` under `browser/211-info/current`.
- Done: add `scripts/upload_hf_browser_artifacts.py` for audit, upload, and optional SHA-256 verification.
- Done: support `VITE_211_CORPUS_BASE_URL` for loading either bundled assets or Hugging Face-hosted browser assets.

Acceptance criteria:

- Done: local browser artifacts and Hugging Face browser artifacts match by size and hash at commit `7e91ace5bc45fc27d2f5e0cabda741fb052be81d`.
- Done: the Vite app can load from bundled assets with no network dependency beyond model downloads.
- Done: the Vite app can load from Hugging Face when configured with `VITE_211_CORPUS_BASE_URL`.

**Phase 3: Retrieval Quality Validation**

- Done: build a small benchmark query set for 211 service navigation.
- Done: compare keyword-only, vector-only, and hybrid ranking.
- Done: confirm browser `Xenova/bge-small-en-v1.5` query vectors are compatible with package `BAAI/bge-small-en-v1.5` vectors.
- Not needed now: rebuild package embeddings with a browser-exact model. Current validation shows matching dimensions and strong short-query cosine alignment.
- Remaining: add stricter expected-result fixtures when product/service owners define canonical answers.

Acceptance criteria:

- Done: known queries rank expected service categories in the top 5.
- Vector search is disabled or downgraded when model/dimension metadata does not match.
- Hybrid search measurably improves at least some semantic queries without harming exact provider/category lookups.

**Phase 4: Worker Hardening**

- Done: add worker status and browser backend fields to `graphRagService.ts`.
- Done: add stale-response guards for rapid query and category changes in the Services screen.
- Consider moving embedding generation and retrieval into one coordinated worker pipeline if duplicate postMessage copies become a bottleneck.
- Port only the useful parts of `warningSuppressionUtils.ts` if ONNX/WebGPU warnings create noisy UX or test output.

Acceptance criteria:

- Rapid repeated searches do not show stale results.
- Worker failures always fall back to deterministic main-thread retrieval.
- Done: smoke tests assert the GraphRAG search worker reaches `Search worker ready`.
- Console output remains actionable during normal use.

**Phase 5: Local LLM Quality**

- Validate `Xenova/distilgpt2` only as a smoke fallback, not as a production answer model.
- Test `Xenova/LaMini-GPT-774M` for WASM answer quality.
- Test `onnx-community/Llama-3.2-1B-Instruct` and `3B` on WebGPU-capable machines.
- Add model-selection UI only after quality and memory behavior are known.

Acceptance criteria:

- Accepted generated answers include citations.
- Ungrounded generated output is rejected and replaced with evidence summary.
- Model download and inference failures do not block search.

**Phase 6: Data Hygiene**

- Done: extend extraction cleanup beyond PDF files to Office/PPTX uploads and binary `PK` payloads.
- Done: extract Office/PPTX text through the `ipfs_datasets_py` office utilities when possible and skip bogus binary service rows.
- Done: rebuild and re-upload the retrieval and browser packages after cleanup.
- Remaining: add `.docx` and `.xlsx` extraction coverage when those file types appear in the corpus.

Acceptance criteria:

- Done: `documents.parquet` has no raw non-PDF binary-looking document text.
- Done: extracted file metadata records original binary hashes and source CIDs.
- Done: browser corpus text fields remain UTF-8 safe and useful for retrieval.

**Phase 7: Tests**

- Add focused TypeScript tests for tokenization, BM25 scoring, hybrid score fusion, graph prompt grounding, and URL resolution.
- Done: add Playwright coverage for Services screen GraphRAG controls.
- Done: add Playwright coverage for Services screen search and fallback answer rendering.
- Done: add browser worker status smoke coverage through the Vite app.

Acceptance criteria:

- `npm run build` passes.
- `npm run test:smoke` passes.
- Python package/export tests pass.

## Risks

- WebNN is not currently an inference provider in the source or target.
- WebGPU support is uneven across browsers and devices.
- Browser LLM downloads can be hundreds of MB to multiple GB.
- Full 211 BM25 and vector search are feasible but must stay off the main thread.
- Full 211 graph adjacency is too heavy for eager browser loading.
- COOP/COEP is required for WASM threads and `SharedArrayBuffer`, but can affect cross-origin asset loading.
- Embedding compatibility between Python and browser model IDs has initial validation, but ranking quality still needs benchmark coverage.
- Future non-PDF binary uploads may need additional extractors beyond the current PDF and PPTX paths.

## Definition of Done

The port is complete when:

- The Services screen can search the 211 corpus with no backend API.
- Results are traceable to source URL, `source_content_cid`, and `source_page_cid`.
- Graph context includes bounded neighboring nodes and community metadata.
- Browser BM25 retrieval runs in a worker on all modern browsers.
- Browser vector retrieval runs when model compatibility is verified.
- Local answer generation works on supported WebGPU/WASM browsers.
- Fallback evidence summaries work everywhere.
- Browser artifacts are published to Hugging Face and verified.
- Existing wallet flows continue to pass smoke tests.
