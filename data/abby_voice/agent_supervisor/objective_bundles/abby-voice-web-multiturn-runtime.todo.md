# Objective Bundle: abby-voice/web-multiturn-runtime

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: validate deterministic multi-turn website voice chat through the package-owned router and thin website adapter.
Conflict policy: preserve browser speech and text-only fallbacks; fixtures contain no private caller audio or credentials.

## ABBY-VOICE-AUTO-036 Validate website multi-turn voice chat

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-web
- Depends on: ABBY-VOICE-AUTO-008, ABBY-VOICE-AUTO-010, ABBY-VOICE-AUTO-019
- Outputs: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent, wallet_interface/ui/tests, tests/voice/test_abby_voice_multiturn_e2e.py
- Validation: python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_pipeline.py
- Bundle: abby-voice/web-multiturn-runtime
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-web-multiturn-runtime.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G030
- Graph depth: 2
- Parallel lane: abby-voice-web
- Conflict policy: preserve browser speech and text-only fallbacks; fixtures contain no private caller audio or credentials.
- Predicted files: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent, wallet_interface/ui/tests, tests/voice/test_abby_voice_multiturn_e2e.py
- Changed paths:
- AST symbols: process_voice_turn, VoiceTurnResult, voice_router_adapter
- Interfaces: website voice proxy, VoiceTurnResult, browser audio result
- Submodules: ipfs_accelerate_py
- Generated artifacts: data/abby_voice/agent_supervisor/discovery
- Allow concurrent with: ABBY-VOICE-AUTO-034, ABBY-VOICE-AUTO-035, ABBY-VOICE-AUTO-037
- Goal id: ABBY-VOICE-G033
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/79f37ccf5ee0d29520e690c09e10989f4a1758374ee619c7283c260679397a3c
- Canonical task CID: baguqeeraphzxzt264djjkihgsdaj4eeyt5fbowbxj3tbtrzihqtam6jzpi6a
- Semantic identity: objective-evidence-obligation/v1/a3b1e51e4913f639a08c2e359c138467a00a1c8831c25d27af73cedfa4a916e4
- Acceptance subset: website adapter contract, ASR injection, multi-turn browser fixture, exact hit and miss trace, text-only degradation
- Preconditions: the unified voice router and exact precomputed resolver are importable.
- Effects: satisfy evidence requirement: website multi-turn runtime validation
- Evidence subset: website adapter contract, multi-turn browser fixture, hit and miss traces
- Resource class: cpu-medium
- Token class: high
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G033
- Rejection reasons: none (accepted)
- Missing evidence: website adapter contract, multi-turn browser fixture, hit and miss traces
- Embedding query: Abby website voice adapter browser multi turn ASR injected GraphRAG cache hit miss
- AST query: process_voice_turn, VoiceTurnResult, voice_router_adapter
- Surplus group: objective/ABBY-VOICE-G033
- Merge key: web-multiturn-runtime-20260728
- Merge family: objective/ABBY-VOICE-G033
- Merge role: aggregate
- Work item count: 2
- Work scope: website_multiturn_runtime
- Candidate kind: aggregate
- Acceptance: Inject deterministic text at the ASR boundary for multi-turn website conversations, assert exact precomputed, template, GraphRAG, fallback, and miss traces, and verify the browser receives valid audio or a structured text-only degradation.
