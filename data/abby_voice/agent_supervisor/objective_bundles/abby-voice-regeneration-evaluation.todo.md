# Objective Bundle: abby-voice/regeneration-evaluation

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: measure deterministic multi-turn retrieval outcomes and Whisper round-trip audio quality across website and telephone fixtures.
Conflict policy: offline deterministic fixtures are the blocking gate; live endpoint results are optional separately approved evidence and never contain private audio.

## ABBY-VOICE-AUTO-038 Measure multi-turn hit and miss ratios and audio quality

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-evaluation
- Depends on: ABBY-VOICE-AUTO-008, ABBY-VOICE-AUTO-036, ABBY-VOICE-AUTO-037
- Outputs: tests/voice/test_abby_voice_multiturn_e2e.py, tests/voice/test_abby_voice_distributed_pipeline.py, tests/voice/test_abby_voice_safety.py, docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md
- Validation: python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py
- Bundle: abby-voice/regeneration-evaluation
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-regeneration-evaluation.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G030
- Graph depth: 2
- Parallel lane: abby-voice-evaluation
- Conflict policy: offline deterministic fixtures are the blocking gate; live endpoint results are optional separately approved evidence and never contain private audio.
- Predicted files: tests/voice/test_abby_voice_multiturn_e2e.py, tests/voice/test_abby_voice_distributed_pipeline.py, tests/voice/test_abby_voice_safety.py, docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md
- Changed paths:
- AST symbols: process_voice_turn, VoiceStageTrace, speech_to_text
- Interfaces: multi-turn evaluation receipt, Whisper transcript comparison, hit and miss metrics
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts: docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md, data/abby_voice/agent_supervisor/discovery
- Allow concurrent with: ABBY-VOICE-AUTO-034, ABBY-VOICE-AUTO-035
- Goal id: ABBY-VOICE-G035
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/534ad0d0d97e37f1d0932ac7e8a72a6f9ec9b7e5cefecdd5acb320706879c123
- Canonical task CID: baguqeeraknfnbugzpy37duetfld6rjzkn6pmtn7fz37m3vnmwmqha2dzyerq
- Semantic identity: objective-evidence-obligation/v1/6b2891f6aaf155e3bbd8884b2f39a8c515aad0346cc2799e72b3247a7aa096da
- Acceptance subset: deterministic conversation corpus, hit and miss metric schema, website report, telephone report, Whisper transcript comparison, threshold gate
- Preconditions: website and telephone multi-turn fixtures emit per-turn traces.
- Effects: satisfy evidence requirement: multi-turn hit and miss ratios, satisfy evidence requirement: Whisper round-trip quality
- Evidence subset: deterministic conversation corpus, hit and miss metrics, Whisper transcript comparison, threshold gate
- Resource class: cpu-medium
- Token class: high
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G035
- Rejection reasons: none (accepted)
- Missing evidence: deterministic conversation corpus, hit and miss metrics, Whisper transcript comparison, threshold gate
- Embedding query: Abby multi turn cache hit miss ratio Whisper audio expected text website telephone evaluation
- AST query: process_voice_turn, VoiceStageTrace, speech_to_text
- Surplus group: objective/ABBY-VOICE-G035
- Merge key: regeneration-evaluation-20260728
- Merge family: objective/ABBY-VOICE-G035
- Merge role: aggregate
- Work item count: 3
- Work scope: multiturn_hit_miss_audio_quality
- Candidate kind: aggregate
- Acceptance: Run a deterministic multi-turn corpus across website and telephone fixtures, report exact cache, template, GraphRAG, fallback, live-TTS, and miss ratios, and use Whisper or an injected equivalent to verify returned audio matches normalized expected text.
