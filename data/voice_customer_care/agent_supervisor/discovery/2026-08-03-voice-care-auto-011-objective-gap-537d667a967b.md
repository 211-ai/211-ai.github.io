# VOICE-CARE-AUTO-011 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 537d667a967b9cd61178fcb99211d715589d9879
Goal id: VOICE-CARE-G012
Goal title: Implement the sandboxed CLI action adapter
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: adapters
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 11
Bundle: voice-care/adapter-cli
Parallel lane: voice-care-adapters
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: sandbox CLI action adapter argv allowlist executable identity timeout resource output redaction injection
AST query: CLIActionAdapter, CLIActionRegistration, build_argv, CLISandboxPolicy
Conflict policy: never use shell expansion, shell=True, caller-controlled cwd, arbitrary environment inheritance, or pack-defined executable paths
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py, ipfs_accelerate_py/test/test_action_cli_adapter.py
AST symbols: CLIActionAdapter, CLIActionRegistration, build_argv, CLISandboxPolicy
Interfaces: native CLI MCP tools, subprocess execution policy
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/715f652fc559f678e3288e2b5720c275b642390418da3672cbd9d659e413d837
Acceptance subset: sandbox/resource policy, injection and environment-leak tests
Preconditions: objective goal VOICE-CARE-G012 is schedulable
Effects: satisfy evidence requirement: sandbox/resource policy, satisfy evidence requirement: injection and environment-leak tests
Evidence subset: sandbox/resource policy, injection and environment-leak tests
Dependencies: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G012
Rejection reasons: none (accepted)

## Goal

Invoke allowlisted CLI operations as validated argv in a bounded environment with absolute executable identity, resource limits, timeout, cancellation, and redaction.

## Missing Evidence

- sandbox/resource policy
- injection and environment-leak tests

## Present Evidence

- CLI registration schema: ipfs_accelerate_py/test/mcp_server/test_cli_endpoint_tools.py (embedding:0.30), ipfs_kit_py/ipfs_kit_py/cli_old.py (embedding:0.32)
- argv builder: ipfs_datasets_py/ipfs_datasets_py/logic/hammers/policy.py (exact)
- output bounds: docs/specs/WORLD_AID_GATE_FIRST_LAUNCHER.md (exact), ipfs_accelerate_py/docs/LLM_ROUTER.md (exact), ipfs_accelerate_py/ipfs_accelerate_py/mcp/tools/cli_endpoint_adapters.py (exact)

## Suggested Handling

Add the minimum safe CLI adapter behind the shared catalog and policy gate.
