# Objective Bundle: abby-voice/wallet-adoption

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-010 Implement Abby voice objective: Adopt the unified router in wallet_interface

- Status: completed
- Completion: manual
- Priority: P1
- Track: voice-integration
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
- Validation: python -m pytest -q wallet_interface/tests && npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
- Bundle: abby-voice/wallet-adoption
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-wallet-adoption.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G008, ABBY-VOICE-G009
- Graph depth: 6
- Parallel lane: abby-voice-integration
- Conflict policy: use a feature flag and preserve all existing fallback paths until end-to-end receipts pass in deployed-like tests
- Predicted files: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
- Changed paths:
- AST symbols: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
- Interfaces: wallet voice proxy HTTP, VoiceTurnResult JSON, browser audio fallbacks
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G010
- Canonical task key: task/v1/8f4d68d7cc38d7ab3d64df9721d06b43edba047d126ebe0668e1eac8976e8db4
- Canonical task CID: baguqeerar5gwrv6mhdl2wple36lsdudlipw3ubd5cjxl4bti4hvmrf3orw2a
- Missing evidence: objective validation repair
- Embedding query: wallet Abby voice proxy shared router browser SpeechRecognition WebGPU browser speech rollout
- AST query: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
- Surplus group: objective/ABBY-VOICE-G010
- Merge key: 91d0485fb9dd252a
- Merge family: objective/ABBY-VOICE-G010
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: af92a5fb52cc760a
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G010. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-010-objective-gap-7d1d7d72091a.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## ABBY-VOICE-AUTO-017 Implement Abby voice objective: Adopt the unified router in wallet_interface

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: voice-integration
- Depends on: ABBY-VOICE-AUTO-019, ABBY-VOICE-AUTO-020
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
- Validation: python -m pytest -q wallet_interface/tests && npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
- Bundle: abby-voice/wallet-adoption
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-wallet-adoption.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G008, ABBY-VOICE-G009
- Graph depth: 7
- Objective heap index: 7
- Parallel lane: abby-voice-integration
- Conflict policy: use a feature flag and preserve all existing fallback paths until end-to-end receipts pass in deployed-like tests
- Predicted files: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
- Changed paths:
- AST symbols: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
- Interfaces: wallet voice proxy HTTP, VoiceTurnResult JSON, browser audio fallbacks
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G010
- Canonical task key: task/v1/73ca6376603b98d53f5a44598f2ee86e9bbe845a474c396d7b1595e67d0c3fd5
- Canonical task CID: baguqeeraopfgg5tahomnkp22irmy6lxin2n35bc2i5gds3l3cwk6m7imh7kq
- Semantic identity: objective-evidence-obligation/v1/930680fbaa1db6c01aaec79a39014f229361d6e787eff7b98bce851fe42fb0d6
- Acceptance subset: focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
- Preconditions: objective goal ABBY-VOICE-G010 is schedulable
- Effects: satisfy evidence requirement: focused tests cover provenance, satisfy evidence requirement: `AgentAudioChatSurface` retains browser SpeechRecognition, satisfy evidence requirement: the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
- Evidence subset: focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G010
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/930680fbaa1db6c01aaec79a39014f229361d6e787eff7b98bce851fe42fb0d6
- Missing evidence: focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
- Embedding query: wallet Abby voice proxy shared router browser SpeechRecognition WebGPU browser speech rollout
- AST query: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
- Surplus group: objective/ABBY-VOICE-G010
- Merge key: 110e7058228f20d9
- Merge family: objective/ABBY-VOICE-G010
- Merge role: aggregate
- Work item count: 3
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: d5e0b6da0795e234
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G010. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-017-objective-gap-25c15bfd594c.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
