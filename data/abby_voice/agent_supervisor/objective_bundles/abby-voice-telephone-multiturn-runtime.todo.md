# Objective Bundle: abby-voice/telephone-multiturn-runtime

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: validate deterministic multi-turn telephone support through the package-owned router and synthetic caller fixtures.
Conflict policy: preserve emergency and human-escalation behavior and never persist private caller audio.

## ABBY-VOICE-AUTO-037 Validate telephone multi-turn support

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-telephone
- Depends on: ABBY-VOICE-AUTO-004, ABBY-VOICE-AUTO-007
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_multiturn_e2e.py, tests/voice/test_abby_voice_safety.py, tests/test_precompute_indextts_batch.py
- Validation: python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_safety.py tests/test_precompute_indextts_batch.py
- Bundle: abby-voice/telephone-multiturn-runtime
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-telephone-multiturn-runtime.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G030
- Graph depth: 2
- Parallel lane: abby-voice-telephone
- Conflict policy: use synthetic caller fixtures only; preserve emergency and human-escalation behavior and never persist private caller audio.
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_multiturn_e2e.py, tests/voice/test_abby_voice_safety.py, tests/test_precompute_indextts_batch.py
- Changed paths:
- AST symbols: process_voice_turn, VoiceTurnResult, normalize_indextts_spoken_text
- Interfaces: telephone voice webhook, SIP or telephony turn state, VoiceTurnResult
- Submodules: ipfs_accelerate_py
- Generated artifacts: data/abby_voice/agent_supervisor/discovery
- Allow concurrent with: ABBY-VOICE-AUTO-034, ABBY-VOICE-AUTO-035, ABBY-VOICE-AUTO-036
- Goal id: ABBY-VOICE-G034
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/e97f2d451e788005261eaeef2151b2309613b648e380573a3e56bb1704f0befb
- Canonical task CID: baguqeera5f7s2ri6pcaakjq6v3xscunsgclbhnsi4oafoor6k25robhqx35q
- Semantic identity: objective-evidence-obligation/v1/6ec82c09f3b21b131124a1b23efa1d70aa5a3bb49943b91b903a196a1f4bcb5f
- Acceptance subset: telephone adapter contract, multi-turn call fixture, normalized phone and address slots, timeout and retry, escalation trace
- Preconditions: provider routing and GraphRAG template integration are available.
- Effects: satisfy evidence requirement: telephone multi-turn runtime validation, satisfy evidence requirement: normalized factual slot speech
- Evidence subset: telephone adapter contract, multi-turn call fixture, normalized factual slots, escalation trace
- Resource class: cpu-medium
- Token class: high
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G034
- Rejection reasons: none (accepted)
- Missing evidence: telephone adapter contract, multi-turn call fixture, normalized factual slots, escalation trace
- Embedding query: Abby telephone support line webhook SIP multi turn phone address normalized speech retry escalation
- AST query: process_voice_turn, VoiceTurnResult, normalize_indextts_spoken_text
- Surplus group: objective/ABBY-VOICE-G034
- Merge key: telephone-multiturn-runtime-20260728
- Merge family: objective/ABBY-VOICE-G034
- Merge role: aggregate
- Work item count: 2
- Work scope: telephone_multiturn_runtime
- Candidate kind: aggregate
- Acceptance: Run synthetic multi-turn telephone fixtures through the shared voice router, assert provider retry and escalation behavior, and prove phone and address audio contains no negative marker, spoken parenthesis, or address hyphenation.
