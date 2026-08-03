# VOICE-CARE-AUTO-017 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 1024381f120c966b4c77fd3887898d7adafdd040
Goal id: VOICE-CARE-G017
Goal title: Build provider-neutral telephony ingress egress and transfer adapters
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: telephony
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 17
Bundle: voice-care/telephony
Parallel lane: voice-care-telephony
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: telephone webhook SIP media stream DTMF barge in transfer human handoff provider neutral
AST query: TelephonyPort, TelephonySession, TelephonyTransferAdapter, process_telephone_interaction
Conflict policy: keep vendor SDKs optional behind adapters; tests use signed synthetic requests and no real calls
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/telephony.py, ipfs_accelerate_py/test/test_customer_care_telephony.py
AST symbols: TelephonyPort, TelephonySession, TelephonyTransferAdapter, process_telephone_interaction
Interfaces: TelephoneTurnState, process_telephone_turn, HandoffQueue
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/4f585162e005faf4c8c07661bf020b0c61dd04de89cc83e2cd789dc78e388f1d
Acceptance subset: telephony port contracts, signed webhook validation, transfer-confirmation matrix, multi-turn tests
Preconditions: objective goal VOICE-CARE-G017 is schedulable
Effects: satisfy evidence requirement: telephony port contracts, satisfy evidence requirement: signed webhook validation, satisfy evidence requirement: transfer-confirmation matrix, satisfy evidence requirement: multi-turn tests
Evidence subset: telephony port contracts, signed webhook validation, transfer-confirmation matrix, multi-turn tests
Dependencies: VOICE-CARE-G005, VOICE-CARE-G016
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G017
Rejection reasons: none (accepted)

## Goal

Adapt webhook, SIP, media-stream, DTMF, barge-in, playback, queue, and transfer operations to process_telephone_turn without making a telephony vendor part of the core.

## Missing Evidence

- telephony port contracts
- signed webhook validation
- transfer-confirmation matrix
- multi-turn tests

## Present Evidence

- replay protection: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/control/execution_permit.py (exact), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_usage_migration.py (exact), ipfs_accelerate_py/test/duckdb_api/distributed_testing/worker_reconnection_enhancements.py (exact)
- media limits: ipfs_datasets_py/ipfs_datasets_py/mcp_server/enterprise_api.py (embedding:0.31), ipfs_datasets_py/tests/unit_tests/multimedia_/ffmpeg_wrapper_/analyze_media/test_edge_cases.py (embedding:0.37), ipfs_kit_py/archive/mcp_final_20250414_082801/controllers/webrtc_controller.py (embedding:0.42)
- fake provider: ipfs_accelerate_py/docs/architecture/AI_SERVICE_CATALOG.md (exact), ipfs_accelerate_py/test/api/test_agent_supervisor_leanstral_proof_provider.py (embedding:0.34), ipfs_accelerate_py/test/api/test_agent_supervisor_tactician_hammer_capabilities.py (embedding:0.36)

## Suggested Handling

Turn the current thin telephone receipt boundary into a tested provider-neutral call-control port.
