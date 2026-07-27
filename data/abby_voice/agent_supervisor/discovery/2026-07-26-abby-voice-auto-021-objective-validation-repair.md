# ABBY-VOICE-AUTO-021 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `529dc663eadc929a142b83896357bdf3f14dad45`
Goal id: `ABBY-VOICE-G021`
Task id: `ABBY-VOICE-AUTO-021`
Goal title: Publish and promote an immutable Hugging Face release
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P1
Track: `voice-release`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G006`, `ABBY-VOICE-G018`, `ABBY-VOICE-G020`
Graph depth: 4
Bundle: `abby-voice/hf-publication`
Work scope: `goal_subgoal_multi_evidence_batch`
Implementation status: validated offline; remote write remains human-gated

## Finding

The objective scan correctly found that G021 named, but did not yet define or
test, **post-publication verification**, **dry-run diff and cost receipt**, and
**pinned redownload validation**. Present-evidence matches pointed at unrelated
threat-model and ADR documents rather than a digest-aware append-only publisher
with a fail-closed promotion workflow.

## Scope-safe authorized paths

| Path | Role |
| --- | --- |
| `ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py` | `HuggingFaceReleasePublisher`, dry-run plan, `HfApi create_commit` publish, post-publication verification, pinned redownload validation, canary/rollback pointer |
| `scripts/publish_abby_voice_release.py` | Operator CLI; default dry-run; execute only with approval JSON |
| `docs/runbooks/ABBY_VOICE_HF_RELEASE.md` | Operational procedure for plan, approve, publish, verify, redownload, canary, rollback |
| `data/abby_voice/releases/publication-receipt.json` | Generated dry-run receipt for the checked-in local release manifest |
| `ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py` | Offline evidence suite |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-021-objective-validation-repair.md` | This authoritative evidence map |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G021 evidence linkage |

Protected `data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md` was not
modified. Package-root `huggingface/__init__.py` was not mutated (callers import
defining symbols from `publisher.py` directly).

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| dry-run diff and cost receipt | `HuggingFaceReleasePublisher.plan_dry_run`, `estimate_publication_cost`, `PublicationPlan`, CLI `--dry-run`, `data/abby_voice/releases/publication-receipt.json`, focused dry-run tests | Produces a deterministic operation list (add only), byte totals, estimated cost, immutable release prefix, plan digest, and prohibited delete/move/overwrite ops. Never contacts a write endpoint (`remote_write_contacted=false`). Never skips by basename alone. |
| post-publication verification | `HuggingFaceReleasePublisher.verify_post_publication`, `PostPublicationVerification`, focused verification tests | After an approved append-only commit, every planned remote path is checked at the returned commit SHA for matching full SHA-256 and byte length. Digest or commit mismatch fails closed and blocks promotion. |
| pinned redownload validation | `HuggingFaceReleasePublisher.redownload_and_validate_pinned`, `PinnedRedownloadValidation`, focused redownload tests | Downloads each planned path by the pinned commit SHA into an empty verified cache, rehashes, and fails closed on size/digest mismatch. Mutable `main`/`latest` refs are never used. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-021-objective-validation-repair.md | this receipt + `G021_AUTHORITATIVE_EVIDENCE_MAP` / `test_evidence_phrases_are_discoverable_in_implementation_modules` | Residual scan must re-find the three evidence phrases on the authorized paths rather than unrelated ADR/threat-model coincidence hits. |

## Acceptance assertions

1. Before approval, the publisher can only produce a deterministic dry-run
   operation list, byte totals, estimated cost, target immutable release prefix,
   and hashes; it cannot contact a write endpoint.
2. The approved transaction uploads by full relative path and digest under a new
   release ID, never skips by basename, never deletes or rewrites a legacy
   object, and records the returned commit SHA via `HfApi create_commit`.
3. The release is downloaded by returned commit SHA into an empty verified cache
   and every planned path revalidates (size + full SHA-256).
4. Consumer promotion is a separate reviewed step with a bounded canary.
   Rollback restores the previous pinned manifest/commit and never deletes the
   failed release.
5. Tokens are never persisted in task rows, manifests, logs, receipts, or source
   control (`tokens_persisted: false`; approval notes reject credential-like
   material).
6. `validate_abby_voice_hf_release` remains the local G018 validator and is
   discoverable for G021 AST scans alongside
   `HuggingFaceReleasePublisher` and `publish_abby_voice_release`.

## Validation receipt

Commands:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py
python scripts/publish_abby_voice_release.py --manifest data/abby_voice/releases/release-manifest.json --dry-run
```

Result on 2026-07-26: **passed — 16 passed**; dry-run exit 0 with
`status=dry_run_only`, `remote_write_performed=false`, 13 planned adds under
`data/abby_voice_v2/{release_id}/`, and a durable
`data/abby_voice/releases/publication-receipt.json`.

The gate is offline for dry-run and unit tests; it requires no credentials and
performs no network or remote bucket/dataset write. Live publish remains blocked
until a human supplies an approval JSON matching the plan digest and cost bound.

## Supervisor and child-goal alignment

This evidence remains aligned with merge family `objective/ABBY-VOICE-G021`,
bundle `abby-voice/hf-publication`, and parallel lane `abby-voice-release`. No
supervisor-generated TODO, vector index, objective graph, or task-status
metadata was manually completed or regenerated; the implementation daemon
remains responsible for rebuilding those artifacts after its validation gate.

No smaller child goal is needed. Dry-run planning, append-only commit,
post-publication verification, pinned redownload validation, and canary/rollback
form one cohesive remote-publication boundary. G018 owns local construction;
G019 owns runtime resolution; G021 alone owns remote writes and pointer
promotion. Failure to obtain human approval is a valid blocked state, not
permission for an autonomous workaround.
