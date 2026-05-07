# Portland Laws WebGPU/WASM GraphRAG Port Plan

Source repository: https://github.com/portland-laws/portland-laws.github.io

Reviewed local clone: `/tmp/portland-laws.github.io`

Reviewed source commit: `f01bf7484a0fa6ce9c24c99e3f0d8b59dbd6979d`

Target repository: `211-AI`

Executable backlog: `docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_TODO.md`

Control plane:

- `scripts/portland_graphrag_implementation_daemon.py`
- `scripts/portland_graphrag_implementation_supervisor.py`
- `python scripts/manage_implementation_services.py start graphrag --no-implement`

## Executive Summary

The core serverless browser GraphRAG port is already present in `211-AI`.
What remains is not a greenfield port; it is parity and hardening work against
the current upstream Portland Laws runtime.

The practical conclusion from this review is:

- Keep the current 211 browser corpus format as the primary path.
- Keep browser inference worker-first and backend-optional.
- Treat WebNN as a capability signal, not as a shipped inference backend, until
  a real execution provider is wired and validated.
- Port only the useful runtime infrastructure from Portland Laws.
- Do not wholesale import the Portland Laws game, NPC, or broad legal-logic
  subsystems.

The dedicated backlog and daemon/supervisor lane created in this pass exists to
finish the remaining parity work without mixing it into the portal or agent-chat
lanes.

## Current 211 Status

This repository already contains the main browser GraphRAG building blocks:

- Browser corpus exporter:
  `scraper/browser_graphrag_corpus.py`
- Browser corpus build CLI:
  `scripts/build_browser_graphrag_corpus.py`
- Browser corpus tests:
  `tests/test_browser_graphrag_corpus.py`
- Browser corpus assets:
  `wallet_interface/ui/public/corpus/211-info/current`
- Browser GraphRAG modules:
  `wallet_interface/ui/src/lib/graphrag/*`
- Search worker:
  `wallet_interface/ui/src/workers/ragSearchWorker.ts`
- Embedding worker and service:
  `wallet_interface/ui/src/workers/embeddingWorker.ts`,
  `wallet_interface/ui/src/lib/clientEmbeddingWorkerService.ts`
- Local LLM worker and service:
  `wallet_interface/ui/src/workers/clientLLMWorker.ts`,
  `wallet_interface/ui/src/lib/clientLLMWorkerService.ts`
- Browser backend detection:
  `wallet_interface/ui/src/lib/backendDetection.ts`
- UI-facing GraphRAG service:
  `wallet_interface/ui/src/services/graphRagService.ts`
- Services-screen GraphRAG UI:
  `wallet_interface/ui/src/app/App.tsx`

Current local browser corpus checkpoint:

- Documents: `22,638`
- Embedding vectors: `22,638`
- Embedding dimension: `384`
- Embedding model: `BAAI/bge-small-en-v1.5`
- Graph neighborhood shards: `46`
- Graph communities: `41`
- Build manifest CID: `bafkreihcclqadxrfhx256soxaqdqvc66ejhsuy3krj5bf446zq2miaox4i`

This means the first-order port objective has already been met:

- serverless browser retrieval is present
- worker-based local embedding is present
- worker-based local generation is present
- corpus packaging is present
- citations and CIDs are already part of the public retrieval flow

## Upstream Repo Findings

The current upstream Portland Laws repo is a Vite/React static app with a much
larger product surface than `211-AI`, but the browser inference and GraphRAG
stack is still concentrated in a small, portable subset.

Key upstream files reviewed:

- `ARCHITECTURE.md`
- `CLIENT_LLM_IMPLEMENTATION.md`
- `MODEL_GUIDE.md`
- `src/lib/backendDetection.ts`
- `src/lib/backendDetectionWorkerService.ts`
- `src/lib/llmConfig.ts`
- `src/lib/clientLLMWorkerService.ts`
- `src/lib/clientEmbeddingWorkerService.ts`
- `src/lib/portlandCorpus.ts`
- `src/lib/portlandGraphRag.ts`
- `src/lib/portlandLogic.ts`
- `src/lib/warningSuppressionUtils.ts`
- `src/workers/backendDetectionWorker.ts`
- `src/workers/clientLLMWorker.ts`
- `src/workers/embeddingWorker.ts`
- `scripts/prepare-portland-corpus.mjs`
- `scripts/extract-portland-corpus.py`

Important upstream characteristics:

- WebGPU and WASM inference run through Transformers.js and ONNX Runtime Web.
- WebNN is detected, but it is not the actual inference path there either.
- Backend detection can run in a dedicated worker and includes benchmarking.
- Warning suppression is used to reduce noisy WebGPU and ONNX console spam.
- The GraphRAG answer layer can incorporate derived logic metadata in addition
  to retrieval evidence.
- Upstream includes optional heavy browser-side experiments and dependencies
  such as `@duckdb/duckdb-wasm`, `parquet-wasm`, and HNSW-related packages.

## Port Matrix

| Upstream Portland Laws | 211 target | Current state | Notes |
| --- | --- | --- | --- |
| `src/lib/backendDetection.ts` | `wallet_interface/ui/src/lib/backendDetection.ts` | ported | 211 version is simpler and does not benchmark FLOPS |
| `src/workers/backendDetectionWorker.ts` | no local equivalent yet | missing | useful parity item |
| `src/lib/backendDetectionWorkerService.ts` | no local equivalent yet | missing | useful parity item |
| `src/lib/llmConfig.ts` | `wallet_interface/ui/src/lib/llmConfig.ts` | ported | 211 version is intentionally conservative |
| `src/workers/clientLLMWorker.ts` | `wallet_interface/ui/src/workers/clientLLMWorker.ts` | ported | 211 uses a smaller, safer default model posture |
| `src/lib/clientLLMWorkerService.ts` | `wallet_interface/ui/src/lib/clientLLMWorkerService.ts` | ported | core pattern preserved |
| `src/workers/embeddingWorker.ts` | `wallet_interface/ui/src/workers/embeddingWorker.ts` | ported | 211 uses BGE instead of GTE |
| `src/lib/clientEmbeddingWorkerService.ts` | `wallet_interface/ui/src/lib/clientEmbeddingWorkerService.ts` | ported | core pattern preserved |
| `src/lib/portlandCorpus.ts` | `wallet_interface/ui/src/lib/graphrag/corpus.ts`, `search.ts` | ported | 211 split the runtime into smaller modules |
| `src/lib/portlandGraphRag.ts` | `wallet_interface/ui/src/lib/graphrag/graphRag.ts` | ported | prompt and fallback adapted for service navigation |
| `src/lib/warningSuppressionUtils.ts` | no local equivalent yet | missing | optional but useful |
| `src/lib/portlandLogic.ts` | no direct equivalent | intentionally not ported | adapt only the useful derived-evidence subset |
| `scripts/extract-portland-corpus.py` | `scraper/browser_graphrag_corpus.py` | reimplemented | 211 schema and graph packaging differ |
| main-thread retrieval path | `wallet_interface/ui/src/workers/ragSearchWorker.ts` | exceeded upstream | 211 already moved retrieval off the main thread |

## Recommended Port Boundary

The right boundary is narrower than the upstream repo:

Port and finish:

- backend detection worker parity
- warning suppression and worker diagnostics
- conservative model gating and model-selection UX
- optional 211-specific derived reasoning metadata where it improves service
  navigation
- benchmarking, smoke coverage, and runtime observability

Do not port wholesale:

- NPC or simulation code
- upstream gameplay UI
- full `src/lib/logic/*` theorem-prover stack
- broad ZK, proof, or municipal-law-specific logic infrastructure that does not
  map directly to 211 service navigation

For `211-AI`, the useful adaptation of the Portland logic path is not
formal legal proofing. It is a lighter service-constraint layer over fields
such as:

- eligibility
- intake instructions
- required documents
- hours
- service area
- languages
- access modality

That is the correct place to borrow the upstream “logic-aware GraphRAG” idea.

## Architecture Decisions

### 1. Keep JSON plus `Float32Array` as the default browser corpus format

Upstream carries optional DuckDB/Parquet/HNSW browser dependencies. They are
interesting, but the current 211 static corpus format is already working and is
simpler to:

- build
- test
- cache
- publish to Hugging Face
- debug in the browser

DuckDB-WASM or Parquet-WASM should be treated as optional later transport
experiments, not as a prerequisite for completing the port.

### 2. Keep retrieval worker-first

`211-AI` is already ahead of the upstream main-thread pattern by running search
and evidence construction in `ragSearchWorker.ts`. That should remain the
default.

### 3. Treat WebNN honestly

The current upstream repo detects WebNN but still runs inference via
Transformers.js over WebGPU or WASM. `211-AI` should make the same claim:

- WebNN capability can be detected and displayed.
- The shipped local inference path is WebGPU or WASM unless a real WebNN
  execution provider is later added and validated.

### 4. Keep deterministic fallback first-class

The 211 service domain is more action-sensitive than the Portland legal demo
flow. Search and evidence summary must always work even when:

- no embedding model has loaded
- no local LLM has loaded
- WebGPU is unavailable
- worker creation fails

### 5. Port only useful logic-aware evidence

If we add a logic-aware layer, it should be derived from 211 service constraints
and remain optional. The GraphRAG runtime must continue to function without it.

## Remaining Delta

### Runtime parity items

- Add a dedicated backend-detection worker and service wrapper.
- Standardize backend capability, benchmark, and diagnostic reporting through a
  single runtime interface.
- Port the useful subset of warning suppression for WebGPU and ONNX Runtime log
  noise.

### Model policy items

- Keep conservative browser defaults for 211.
- Add device-gated model recommendations rather than exposing all large models
  unguarded.
- Add explicit model-selection UI only after memory and answer-quality behavior
  are verified on representative hardware.

### Derived reasoning items

- Export optional derived service-constraint metadata alongside GraphRAG assets.
- Allow the answer builder to use those summaries when present.
- Do not add mandatory legal-logic or theorem-prover dependencies to the 211 UI.

### Quality and operations items

- Add an executable backlog for the remaining parity work.
- Run that backlog through the shared todo daemon/supervisor stack.
- Add a dedicated service-manager target so this lane can be supervised like the
  portal and agent lanes.

## Executable Backlog

The implementation queue created in this pass is:

- `docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_TODO.md`

The queue is supervised through:

- `scripts/portland_graphrag_implementation_daemon.py`
- `scripts/portland_graphrag_implementation_supervisor.py`

The service manager target is:

- `python scripts/manage_implementation_services.py status graphrag`
- `python scripts/manage_implementation_services.py start graphrag --no-implement`
- `python scripts/manage_implementation_services.py start graphrag --implement`

## Definition of Done

This port lane is complete when all of the following are true:

- Services-screen GraphRAG works fully serverlessly from the browser corpus.
- Local embedding and local generation remain optional, worker-based, and
  correctly gated by device capabilities.
- Backend capability reporting is consistent and off-main-thread when
  appropriate.
- WebGPU and ONNX warning suppression improves signal without hiding real
  failures.
- Optional 211-specific derived reasoning metadata can enrich answers without
  becoming a hard dependency.
- Browser build, smoke, retrieval benchmark, and compatibility checks pass.
- The remaining parity work is tracked and executable through the shared todo
  daemon/supervisor stack.
