# Portland Laws WebGPU/WASM GraphRAG Port Todo

This backlog is the executable implementation queue for
`docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md`.

The implementation daemon parses tasks with the heading format `## GRAPHRAG-...`
and the metadata bullets directly below each heading.

Priority guide:

- `P0`: foundation or blocker work
- `P1`: user-visible core path work
- `P2`: optional extension or optimization
- `P3`: polish

Track guide:

- `platform`: control plane, backlog wiring, daemon/supervisor, service manager
- `runtime`: browser workers, capability detection, model config, warning handling
- `data`: browser corpus export, derived reasoning metadata, manifest compatibility
- `ui`: Services-screen controls, diagnostics, model selection, citation polish
- `quality`: benchmarks, smoke coverage, browser compatibility, regression tests
- `ops`: runbooks, audit, release verification

## GRAPHRAG-000 Control Plane
- Status: completed
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md, docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_TODO.md, scripts/portland_graphrag_implementation_daemon.py, scripts/portland_graphrag_implementation_supervisor.py, scripts/manage_implementation_services.py, tests/test_portland_graphrag_implementation.py, tests/test_implementation_service_manager.py
- Validation: python scripts/portland_graphrag_implementation_daemon.py --once --no-implement; python scripts/portland_graphrag_implementation_supervisor.py --once --no-implement; python -m pytest tests/test_portland_graphrag_implementation.py tests/test_implementation_service_manager.py -q
- Acceptance: The Portland GraphRAG port lane has a dedicated backlog, state prefix, daemon, supervisor, and service-manager target on the shared todo control plane.

## GRAPHRAG-010 Upstream Review Refresh
- Status: completed
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: GRAPHRAG-000
- Outputs: docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md
- Validation: python -c "from pathlib import Path; text = Path('docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md').read_text(encoding='utf-8'); assert 'f01bf7484a0fa6ce9c24c99e3f0d8b59dbd6979d' in text; assert 'docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_TODO.md' in text"
- Acceptance: The plan reflects the current upstream Portland Laws commit, distinguishes already-ported functionality from remaining parity work, and defines a 211-specific scope boundary.

## GRAPHRAG-020 Backend Detection Worker Parity
- Status: todo
- Completion: artifact
- Priority: P0
- Track: runtime
- Depends on: GRAPHRAG-010
- Outputs: wallet_interface/ui/src/lib/backendDetection.ts, wallet_interface/ui/src/lib/backendDetectionWorkerService.ts, wallet_interface/ui/src/workers/backendDetectionWorker.ts, wallet_interface/ui/src/services/graphRagService.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Backend capability detection and optional benchmarking can run off the main thread, return a stable typed status object, and fall back safely to the main thread when worker startup fails.

## GRAPHRAG-021 Warning Suppression And ONNX Hygiene
- Status: todo
- Completion: artifact
- Priority: P1
- Track: runtime
- Depends on: GRAPHRAG-020
- Outputs: wallet_interface/ui/src/lib/warningSuppressionUtils.ts, wallet_interface/ui/src/workers/clientLLMWorker.ts, wallet_interface/ui/src/workers/backendDetectionWorker.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Known noisy WebGPU and ONNX Runtime warnings are filtered from normal browser use and tests without suppressing real inference or worker failures.

## GRAPHRAG-022 Conservative Model Policy And Selection
- Status: todo
- Completion: artifact
- Priority: P1
- Track: runtime
- Depends on: GRAPHRAG-020
- Outputs: wallet_interface/ui/src/lib/llmConfig.ts, wallet_interface/ui/src/lib/clientLLMWorkerService.ts, wallet_interface/ui/src/app/App.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: The 211 browser runtime recommends models based on device capability, keeps safe WASM fallbacks first-class, and exposes local generation as an explicit opt-in rather than a mandatory download.

## GRAPHRAG-030 Derived Service-Constraint Export
- Status: todo
- Completion: artifact
- Priority: P1
- Track: data
- Depends on: GRAPHRAG-010
- Outputs: scraper/browser_graphrag_corpus.py, scripts/build_browser_graphrag_corpus.py, wallet_interface/ui/src/lib/graphrag/types.ts
- Validation: python -m pytest tests/test_browser_graphrag_corpus.py -q
- Acceptance: The browser corpus builder can optionally export lightweight derived service-constraint metadata for eligibility, intake, hours, documents, and service area without requiring the full Portland legal-logic stack.

## GRAPHRAG-031 Logic-Aware Answer Builder
- Status: todo
- Completion: artifact
- Priority: P1
- Track: runtime
- Depends on: GRAPHRAG-022, GRAPHRAG-030
- Outputs: wallet_interface/ui/src/lib/graphrag/graphRag.ts, wallet_interface/ui/src/services/graphRagService.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: The answer builder can include optional derived service-constraint evidence when present, but still produces grounded deterministic summaries when that metadata is absent or local generation is unavailable.

## GRAPHRAG-040 Services-Screen GraphRAG Diagnostics
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ui
- Depends on: GRAPHRAG-020, GRAPHRAG-022
- Outputs: wallet_interface/ui/src/app/App.tsx, wallet_interface/ui/src/app/ServiceDetailScreen.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: The Services screen exposes meaningful runtime status for corpus readiness, retrieval worker, embedding worker, local generation, and browser backend capability without cluttering the default experience.

## GRAPHRAG-050 Quality And Compatibility Suite
- Status: todo
- Completion: artifact
- Priority: P0
- Track: quality
- Depends on: GRAPHRAG-020, GRAPHRAG-021, GRAPHRAG-022, GRAPHRAG-040
- Outputs: scripts/benchmark_211_retrieval.py, wallet_interface/ui/tests/smoke.spec.ts, wallet_interface/ui/tests/agent-action-convergence.spec.ts
- Validation: npm --prefix wallet_interface/ui run build; npm --prefix wallet_interface/ui run test:smoke; python scripts/benchmark_211_retrieval.py --output data/validation/retrieval_quality_benchmark.json
- Acceptance: Retrieval quality, worker startup, browser fallback behavior, and local-model gating are covered by executable checks that fail clearly when parity regresses.

## GRAPHRAG-060 Optional Browser Transport Experiments
- Status: todo
- Completion: artifact
- Priority: P2
- Track: data
- Depends on: GRAPHRAG-050
- Outputs: wallet_interface/ui/src/lib/graphrag/corpus.ts, docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: DuckDB-WASM, Parquet-WASM, or HNSW-WASM experiments are evaluated behind an explicit optional path, with the current JSON-plus-F32 corpus remaining the default unless a measured improvement justifies promotion.

## GRAPHRAG-070 Final Parity Audit
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ops
- Depends on: GRAPHRAG-021, GRAPHRAG-031, GRAPHRAG-040, GRAPHRAG-050
- Outputs: docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md
- Validation: python -c "from pathlib import Path; text = Path('docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md').read_text(encoding='utf-8'); assert 'Definition of Done' in text; assert 'Executable Backlog' in text"
- Acceptance: The plan is updated to reflect the completed parity work, the intentionally unported upstream subsystems, and the final recommended runtime architecture for 211 serverless browser GraphRAG.
