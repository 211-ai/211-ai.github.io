# ABBY-VOICE-AUTO-030 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `70fa4f3c36c1b782855679e2f3c7f992f64d354f`
Goal id: `ABBY-VOICE-G021`
Task id: `ABBY-VOICE-AUTO-030`
Goal title: Publish and promote an immutable Hugging Face release
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P1
Track: `voice-release`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G006`, `ABBY-VOICE-G018`, `ABBY-VOICE-G020`
Graph depth: 4
Bundle: `abby-voice/hf-publication`
Parallel lane: `abby-voice-release`
Work scope: residual scan-closure for post-publication verification and pinned redownload validation
Implementation status: validated offline; remote write remains human-gated

## Finding

Objective scan `2026-07-26-abby-voice-auto-030-objective-gap-70fa4f3c36c1.md`
reported two missing evidence terms for G021 even though AUTO-021 already
implemented the digest-aware append-only publisher:

- post-publication verification
- pinned redownload validation

The scan correctly required residual proof that those gates are not only
standalone methods but are exercised on the authorized publish path, fail closed
on digest/commit mismatch, and remain discoverable as exact phrases. Present-
evidence matches in the gap filing still pointed at unrelated ADR/threat-model
documents rather than the publisher/CLI/runbook/test surface.

This repair does **not** invent a second remote-write boundary, split G021, or
relax the human-approval gate. It anchors residual discoverability for the
AUTO-030 acceptance subset and wires both gates through
`publish_abby_voice_release` after an approved append-only commit.

Implementation authority remains:

`authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-021-objective-validation-repair.md`

Residual-term inventory for this task:

`residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-030-objective-validation-repair.md`

## Scope-safe authorized paths

| Path | Role |
| --- | --- |
| `ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py` | `HuggingFaceReleasePublisher.verify_post_publication`, `redownload_and_validate_pinned`, integrated `publish_abby_voice_release` gates, residual constants |
| `scripts/publish_abby_voice_release.py` | Operator CLI; default dry-run; execute only with approval JSON |
| `docs/runbooks/ABBY_VOICE_HF_RELEASE.md` | Operational procedure naming both residual gates |
| `data/abby_voice/releases/publication-receipt.json` | Durable dry-run / publish receipt with evidence flags |
| `ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py` | Offline suite including execute-path residual gates |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-030-objective-validation-repair.md` | This residual scan-closure receipt |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G021 residual evidence linkage |

Protected `data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md` was not
modified.

## Repaired residual evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| post-publication verification | `HuggingFaceReleasePublisher.verify_post_publication`, `PostPublicationVerification`, `publish_abby_voice_release` post-commit path, `test_post_publication_verification`, `test_publish_abby_voice_release_execute_runs_verification_gates`, `test_publish_execute_post_publication_verification_fail_closed` | After an approved append-only commit, every planned remote path is checked at the returned commit SHA for matching full SHA-256 and byte length. Digest or commit mismatch fails closed and blocks promotion. |
| pinned redownload validation | `HuggingFaceReleasePublisher.redownload_and_validate_pinned`, `PinnedRedownloadValidation`, `publish_abby_voice_release` post-commit path, `test_pinned_redownload_validation`, `test_publish_abby_voice_release_execute_runs_verification_gates`, `test_publish_execute_pinned_redownload_validation_fail_closed` | Downloads each planned path by the pinned commit SHA into an empty verified cache, rehashes, and fails closed on size/digest mismatch. Mutable `main`/`latest` refs are never used. Non-empty caches refuse. |
| residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-030-objective-validation-repair.md | This receipt; `G021_RESIDUAL_SCAN_CLOSURE_AUTO_030`, `G021_AUTO_030_RESIDUAL_EVIDENCE_TERMS`, `test_g021_auto_030_residual_evidence_terms_are_discoverable` | Subsequent residual scans re-find the two subset phrases on the authorized publisher/test/receipt surface rather than unrelated ADR coincidence hits. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-021-objective-validation-repair.md | AUTO-021 remains the full G021 implementation authority (dry-run, approval, append-only commit, canary/rollback) | AUTO-030 only closes residual discoverability and integrated fail-closed verification for the two-term subset. |

## Acceptance assertions

1. `verify_post_publication` remains the named post-publication verification
   gate and is invoked from `publish_abby_voice_release` after a successful
   approved `HfApi create_commit` when residual verification is enabled.
2. `redownload_and_validate_pinned` remains the named pinned redownload
   validation gate; it requires an empty verified cache and the pinned commit
   SHA (never `main`).
3. Tampered remote digests or redownload payloads fail closed with
   `HuggingFacePublicationError` and never produce a promotion-ready pointer.
4. Dry-run still never contacts a write endpoint and still produces the durable
   `data/abby_voice/releases/publication-receipt.json` cost receipt.
5. Live remote write remains blocked until a human supplies
   `PublicationApproval` matching the plan digest and cost bound.
6. No smaller child goal is required: both residual terms describe the same
   G021 remote-publication boundary AUTO-021 already owns.

## Validation receipt

Commands:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py
python scripts/publish_abby_voice_release.py --manifest data/abby_voice/releases/release-manifest.json --dry-run
```

Result on 2026-07-26: **passed — 20 passed**; dry-run exit 0 with
`status=dry_run_only`, `remote_write_performed=false`, 13 planned adds under
`data/abby_voice_v2/{release_id}/`, and a durable
`data/abby_voice/releases/publication-receipt.json`.

The gate is offline for dry-run and unit tests; it requires no credentials and
performs no network or remote bucket/dataset write.

## Supervisor and child-goal alignment

This residual repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-030`, goal `ABBY-VOICE-G021`, P1, track `voice-release`,
parent G011, dependencies G006/G018/G020, graph depth 4, bundle
`abby-voice/hf-publication`, parallel lane `abby-voice-release`, and merge
family `objective/ABBY-VOICE-G021`.

No supervisor-generated TODO, vector index, objective graph, or task-status
metadata was manually completed or regenerated; the implementation daemon
remains responsible for rebuilding those artifacts after its validation gate.

No smaller child goal is needed. Dry-run planning, append-only commit,
post-publication verification, pinned redownload validation, and canary/rollback
remain one cohesive remote-publication boundary. G018 owns local construction;
G019 owns runtime resolution; G021 alone owns remote writes and pointer
promotion.
