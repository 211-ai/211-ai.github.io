# VOICE-CARE-AUTO-010 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 36954e05f4b37a5773145564ac44df39a8b1f04f
Goal id: VOICE-CARE-G011
Goal title: Implement the MCP and MCP++ action adapter
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: adapters
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 10
Bundle: voice-care/adapter-mcp
Parallel lane: voice-care-adapters
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: MCP MCP++ action adapter dispatch IDL UCAN temporal policy CID artifact event DAG
AST query: MCPActionAdapter, MCPPlusPlusActionAdapter, MCPInterfaceBinding
Conflict policy: use canonical mcp_server surfaces; do not add a second dispatcher or bypass IDL and policy checks
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/mcp.py, ipfs_accelerate_py/test/test_action_mcp_adapter.py
AST symbols: MCPActionAdapter, MCPPlusPlusActionAdapter, MCPInterfaceBinding
Interfaces: unified MCP tools_dispatch, IDL registry, UCAN delegation, temporal policy
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/89466396c296eba98855f21bb5d10d1568918a07aa20431136c2e0d9afc7e276
Acceptance subset: fake server tests
Preconditions: objective goal VOICE-CARE-G011 is schedulable
Effects: satisfy evidence requirement: fake server tests
Evidence subset: fake server tests
Dependencies: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G011
Rejection reasons: none (accepted)

## Goal

Invoke reviewed MCP tools through canonical discovery and dispatch and MCP++ tools through IDL, UCAN, temporal-policy, artifact, and event-DAG bindings.

## Missing Evidence

- fake server tests

## Present Evidence

- capability and IDL discovery: ipfs_accelerate_py/README.md (embedding:0.37), ipfs_accelerate_py/config/formal_verification_toolchains.lock.json (embedding:0.36), ipfs_accelerate_py/docs/BEST_PRACTICES.md (embedding:0.36)
- input/output parity: ipfs_datasets_py/docs/BATCH_327_PARITY_TESTING_SUMMARY.md (embedding:0.37), ipfs_datasets_py/ipfs_datasets_py/processors/multimedia/omni_converter_mk2/utils/llm/constants.py (embedding:0.62), ipfs_kit_py/archive/reorganization_backup_root/BUCKET_VFS_INTERFACES_COMPLETE.md (embedding:0.37)
- descriptor drift and downgrade rejection: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/repository_forest.py (embedding:0.36)
- MCP and MCP++ receipts: ipfs_accelerate_py/README.md (embedding:0.31), ipfs_accelerate_py/docs/BEST_PRACTICES.md (embedding:0.32), ipfs_accelerate_py/docs/MCP_SERVER.md (embedding:0.34)

## Suggested Handling

Adapt existing MCP/MCP++ capabilities to the shared action lifecycle.
