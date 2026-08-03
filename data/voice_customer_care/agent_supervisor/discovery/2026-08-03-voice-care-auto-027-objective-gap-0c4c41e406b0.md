# VOICE-CARE-AUTO-027 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 0c4c41e406b0f11623f423ebf9e2e3e9d13872b6
Goal id: VOICE-CARE-G007
Goal title: Build the deployment-owned action catalog and resolver
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: action-runtime
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 0
Bundle: voice-care/action-catalog
Parallel lane: voice-care-runtime
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: deployment action catalog resolver allowlist descriptor CID schema interface capability lazy adapter
AST query: ActionCatalog, ActionRegistration, ActionResolver, CatalogSnapshot
Conflict policy: domain packs may reference catalog entries but never register, replace, or widen them
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py, ipfs_accelerate_py/test/test_action_catalog.py
AST symbols: ActionCatalog, ActionRegistration, ActionResolver, CatalogSnapshot
Interfaces: MCP IDL registry, CLI registry, callable registry, workflow registry, supervisor control
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/1ac6927654fbdfbd7a7e59949b20710e13d9aceb305eafc8c0c36d98de78637c
Acceptance subset: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py, ipfs_accelerate_py/test/test_action_catalog.py
Preconditions: objective goal VOICE-CARE-G007 is schedulable
Effects: satisfy evidence requirement: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py, satisfy evidence requirement: ipfs_accelerate_py/test/test_action_catalog.py
Evidence subset: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py, ipfs_accelerate_py/test/test_action_catalog.py
Dependencies: VOICE-CARE-G006
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G007
Rejection reasons: none (accepted)

## Goal

Resolve domain-pack action references against an allowlisted deployment catalog with exact descriptor, schema, interface, owner, version, and capability identities.

## Missing Evidence

- ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py
- ipfs_accelerate_py/test/test_action_catalog.py

## Present Evidence

- immutable catalog snapshot: ipfs_accelerate_py/docs/MCP_SERVER.md (embedding:0.36), ipfs_accelerate_py/docs/architecture/AI_SERVICE_CATALOG.md (embedding:0.33), ipfs_accelerate_py/ipfs_accelerate_py/endpoint_usage/resolution.py (exact)
- descriptor registration and discovery: ipfs_accelerate_py/docs/MCP_SERVER.md (embedding:0.32), ipfs_accelerate_py/docs/architecture/AGENT_SUPERVISOR_ARCHITECTURE.md (embedding:0.32), ipfs_accelerate_py/docs/archive/sessions/LIBP2P_FIX_SUMMARY.md (embedding:0.34)
- CID and schema verification: docs/data/ABBY_VOICE_GRAPHRAG.md (embedding:0.32), docs/reports/ABBY_VOICE_EVALUATION.md (embedding:0.30), docs/specs/CHAINLINK_ZKML_LLM_ROUTER_UI_WORKFLOW_MATRIX.md (embedding:0.30)
- duplicate/drift rejection: docs/specs/HMIS_INTEGRATION_THREAT_MODEL.md (embedding:0.37)
- lazy adapter factories: ipfs_accelerate_py/ipfs_accelerate_py/cli_runtime/endpoints.py (embedding:0.37)

## Suggested Handling

Create a fail-closed resolver and capability-discovery snapshot shared by every adapter.
