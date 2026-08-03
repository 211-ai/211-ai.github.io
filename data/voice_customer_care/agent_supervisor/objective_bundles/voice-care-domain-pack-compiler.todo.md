# Objective Bundle: voice-care/domain-pack-compiler

Source todo: data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## VOICE-CARE-AUTO-004 Implement reusable voice customer-care objective: Build the deterministic domain-pack compiler and validator

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: domain-data
- Depends on: VOICE-CARE-AUTO-002, VOICE-CARE-AUTO-003
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/compiler.py, ipfs_datasets_py/ipfs_datasets_py/conversation/cli.py, ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- Board namespace: VOICE_CUSTOMER_CARE_TODO.md
- Evidence inputs: data/voice_customer_care/agent_supervisor/discovery
- Discovery evidence: /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-004-objective-gap-7af35550f39e.md
- Bundle: voice-care/domain-pack-compiler
- Bundle shard: data/voice_customer_care/agent_supervisor/objective_bundles/voice-care-domain-pack-compiler.todo.md
- Bundle strategy: explicit
- Graph parents: VOICE-CARE-G001
- Graph depth: 1
- Objective heap index: 3
- Parallel lane: voice-care-data
- Conflict policy: compilation is local and read-only with respect to source data; no implicit upload, pin, or mutable remote fetch
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/compiler.py, ipfs_datasets_py/ipfs_datasets_py/conversation/cli.py, ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- Changed paths:
- Context paths: ipfs_datasets_py/ipfs_datasets_py/conversation/compiler.py, ipfs_datasets_py/ipfs_datasets_py/conversation/cli.py, ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- AST symbols: DomainPackCompiler, CompilationReceipt, compile_domain_pack, validate_compiled_pack
- Interfaces: domain pack schemas, multiformats CID, GraphRAG index
- Submodules: ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: VOICE-CARE-G004
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/73cbc65614fcfd2f12d85b48aa7d24c9a26848122bf46bef2fda712cd48bd583
- Canonical task CID: baguqeeraopf4mvqu7t6s6ewylneku7jezgrgqsasfp2gx3zp3jyszvel2wbq
- Semantic identity: objective-evidence-obligation/v1/97b9ee9c17361461a022525f97bc292705255193dd255a694e9337beaf96544c
- Acceptance subset: reproducibility receipt, actionable validation diagnostics
- Preconditions: objective goal VOICE-CARE-G004 is schedulable
- Effects: satisfy evidence requirement: reproducibility receipt, satisfy evidence requirement: actionable validation diagnostics
- Evidence subset: reproducibility receipt, actionable validation diagnostics
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Context budget tokens: 4096
- Provider role: grok, codex-review
- Resources: cpu-medium
- Merge fate: objective/VOICE-CARE-G004
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/97b9ee9c17361461a022525f97bc292705255193dd255a694e9337beaf96544c
- Missing evidence: reproducibility receipt, actionable validation diagnostics
- Embedding query: deterministic domain pack compiler graph retrieval form localization evaluation CID cache diagnostics
- AST query: DomainPackCompiler, CompilationReceipt, compile_domain_pack, validate_compiled_pack
- Surplus group: objective/VOICE-CARE-G004
- Merge key: 0cd87ec8d5e720bd
- Merge family: objective/VOICE-CARE-G004
- Merge role: aggregate
- Work item count: 2
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 4aef12cab5edb967
- Acceptance: Objective scan filed this gap for VOICE-CARE-G004. Use evidence in /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-004-objective-gap-7af35550f39e.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (reproducibility receipt, actionable validation diagnostics), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
