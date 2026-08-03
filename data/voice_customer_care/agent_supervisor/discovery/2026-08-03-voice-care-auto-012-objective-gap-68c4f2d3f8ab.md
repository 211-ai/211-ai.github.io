# VOICE-CARE-AUTO-012 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 68c4f2d3f8abc7e9b364cba1dee614e466958689
Goal id: VOICE-CARE-G013
Goal title: Implement the registered Python callable adapter
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: adapters
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 12
Bundle: voice-care/adapter-python
Parallel lane: voice-care-adapters
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: Python callable class method action adapter registration dependency injection async schema timeout
AST query: PythonActionAdapter, CallableRegistration, RegisteredCallableResolver
Conflict policy: no caller-supplied imports, eval, exec, arbitrary getattr chains, or implicit global singleton resolution
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/python.py, ipfs_accelerate_py/test/test_action_python_adapter.py
AST symbols: PythonActionAdapter, CallableRegistration, RegisteredCallableResolver
Interfaces: action catalog, application service methods
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/6c5530527e135468f2f4d9b1b8900eaeb091bc5e437940445620a0feaa38be37
Acceptance subset: arbitrary-import and attribute-traversal rejection tests
Preconditions: objective goal VOICE-CARE-G013 is schedulable
Effects: satisfy evidence requirement: arbitrary-import and attribute-traversal rejection tests
Evidence subset: arbitrary-import and attribute-traversal rejection tests
Dependencies: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G013
Rejection reasons: none (accepted)

## Goal

Invoke reviewed Python functions and class methods by catalog registration key with validated dependencies, arguments, results, timeout, cancellation, and explicit side-effect metadata.

## Missing Evidence

- arbitrary-import and attribute-traversal rejection tests

## Present Evidence

- callable registry: ipfs_datasets_py/benchmarks/logic_pipeline/source_executor.py (embedding:0.34), ipfs_datasets_py/ipfs_datasets_py/logic/backends/installers/hyperproperty.py (embedding:0.40), ipfs_datasets_py/ipfs_datasets_py/processors/multimedia/omni_converter_mk2/core/text_normalizer/_text_normalizer.py (embedding:0.30)
- dependency injection: ipfs_accelerate_py/docs/EMBEDDINGS_ROUTER.md (exact), ipfs_accelerate_py/docs/LLM_ROUTER.md (exact), ipfs_accelerate_py/docs/api/overview.md (exact)
- sync/async support: ipfs_accelerate_py/docs/features/github-cache/overview.md (embedding:0.45), ipfs_accelerate_py/docs/guides/infrastructure/README.md (embedding:0.31), ipfs_accelerate_py/ipfs_accelerate_js/test/browser/test_webnn_minimal.ts (embedding:0.65)
- result validation: ipfs_accelerate_py/test/BATTERY_IMPACT_ANALYSIS.md (exact), ipfs_accelerate_py/test/PYTHON_SDK_ENHANCEMENT.md (exact), ipfs_accelerate_py/test/duckdb_api/README.md (exact)

## Suggested Handling

Provide an in-process adapter for reviewed application methods without weakening catalog controls.
