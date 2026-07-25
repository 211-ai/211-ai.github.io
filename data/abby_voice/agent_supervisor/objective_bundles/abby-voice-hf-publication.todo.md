# Objective Bundle: abby-voice/hf-publication

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-021 Implement Abby voice objective: Publish and promote an immutable Hugging Face release

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: voice-release
- Depends on: ABBY-VOICE-AUTO-009, ABBY-VOICE-AUTO-018, ABBY-VOICE-AUTO-020
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py, scripts/publish_abby_voice_release.py, docs/runbooks/ABBY_VOICE_HF_RELEASE.md, data/abby_voice/releases/publication-receipt.json
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py && python scripts/publish_abby_voice_release.py --manifest data/abby_voice/releases/release-manifest.json --dry-run
- Bundle: abby-voice/hf-publication
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-hf-publication.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 11
- Parallel lane: abby-voice-release
- Conflict policy: autonomous work stops after a dry run; no delete move overwrite mutable-main URL or pointer promotion occurs without explicit human approval of the exact manifest commit operations credentials scope and cost bound
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py, scripts/publish_abby_voice_release.py, docs/runbooks/ABBY_VOICE_HF_RELEASE.md, data/abby_voice/releases/publication-receipt.json, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py
- Changed paths:
- AST symbols: HuggingFaceReleasePublisher, publish_abby_voice_release, validate_abby_voice_hf_release
- Interfaces: HfApi create_commit, Abby release manifest, runtime release pointer
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/releases/publication-receipt.json
- Allow concurrent with:
- Goal id: ABBY-VOICE-G021
- Canonical task key: task/v1/e327bc9ed65bbd9070c5c30adf846fd6a597e7ab7ade557b9ed9321f04fd8489
- Canonical task CID: baguqeera4mt3zhwwlo6za4gfymfn7bdp22szpz5lplpfk6463ezb6bh5qseq
- Semantic identity: objective-evidence-obligation/v1/440386f69d9b031ad057cb8dce5fdd28769cdc601c66ae070f354ff148373cb1
- Acceptance subset: post-publication verification, dry-run diff and cost receipt, pinned redownload validation
- Preconditions: objective goal ABBY-VOICE-G021 is schedulable
- Effects: satisfy evidence requirement: post-publication verification, satisfy evidence requirement: dry-run diff and cost receipt, satisfy evidence requirement: pinned redownload validation
- Evidence subset: post-publication verification, dry-run diff and cost receipt, pinned redownload validation
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G021
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/440386f69d9b031ad057cb8dce5fdd28769cdc601c66ae070f354ff148373cb1
- Missing evidence: post-publication verification, dry-run diff and cost receipt, pinned redownload validation
- Embedding query: Hugging Face append only publish commit SHA verify canary rollback Abby voice
- AST query: HuggingFaceReleasePublisher, publish_abby_voice_release, validate_abby_voice_hf_release
- Surplus group: objective/ABBY-VOICE-G021
- Merge key: 76b9de750361da43
- Merge family: objective/ABBY-VOICE-G021
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
- Todo vector key: a25bb2a2fb26cb73
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G021. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-021-objective-gap-529dc663eadc.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (post-publication verification, dry-run diff and cost receipt, pinned redownload validation), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
