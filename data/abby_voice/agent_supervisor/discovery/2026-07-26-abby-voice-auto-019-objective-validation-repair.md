# ABBY-VOICE-AUTO-019 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `0d53313c748d9850cce414240ed6077bff575340`
Goal id: `ABBY-VOICE-G019`
Task id: `ABBY-VOICE-AUTO-019`
Goal title: Load pinned releases and resolve precomputed audio safely
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-integration`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G008`, `ABBY-VOICE-G018`
Graph depth: 4
Bundle: `abby-voice/runtime-release`
Work scope: `goal_subgoal_multi_evidence_batch`
Implementation status: validated offline; authoritative daemon completion pending

## Finding

The objective scan correctly found that G019 named, but did not yet define or
test, **runtime resolution**, **revision-pinned streaming/release loader**,
**exact audio resolver**, and **stale-slot regression test**. Present-evidence
matches pointed at unrelated embedding docs and residual precompute batch JSON
rather than a voice-specific pinned release loader and exact precomputed-audio
path in the router.

Conflict policy from the gap: add revision support to the existing streaming
loader; resolver failure falls through to live TTS or text-only output and
never serves a near or stale match. Identifier-only precomputed-audio matching
is removed.

## Scope-safe authorized paths

| Path | Role |
| --- | --- |
| `ipfs_datasets_py/ipfs_datasets_py/voice/release_loader.py` | `AbbyVoiceReleaseLoader` — revision-pinned streaming/release loader; requires release manifest + immutable commit SHA; validates descriptors before use; content-addressed GraphRAG restore |
| `ipfs_accelerate_py/ipfs_accelerate_py/voice_audio_resolver.py` | `PrecomputedVoiceAudioResolver` — exact audio resolver; full synthesis identity; stale-slot invalidation |
| `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` | `process_voice_turn` runtime resolution: precomputed exact hit before live TTS; miss falls through without weakening GraphRAG provenance |
| `ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py` | Offline evidence suite covering all four acceptance terms plus text-only/live-TTS fallback |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-019-objective-validation-repair.md` | This authoritative evidence map |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G019 evidence linkage |

Protected `data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md` was not
modified. Package-root `__init__.py` re-exports were not mutated (scope-safe;
callers import defining modules directly).

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| runtime resolution | `process_voice_turn(..., audio_resolver=...)` in `voice_router.py`; `RUNTIME_RESOLUTION_EVIDENCE_TERM`; `test_runtime_resolution_uses_precomputed_audio_without_live_tts`; end-to-end release→router test | After grounded rendering, exact precomputed audio is preferred; live TTS is not called on hit; stage trace records `runtime_resolution=True` and resolver reason. |
| revision-pinned streaming/release loader | `AbbyVoiceReleaseLoader` in `release_loader.py`; `open_revision_pinned_streaming_loader` pins `datasets.load_dataset(..., revision=<commit_sha>, streaming=True)` then wraps `HuggingFaceStreamingLoader`; mutable `main`/`master`/`latest` rejected; local load validates descriptors before use | Loader requires release manifest + immutable commit SHA; downloads/uses only manifest, GraphRAG support index, and selected Parquet shards; descriptors verified before row use. |
| exact audio resolver | `PrecomputedVoiceAudioResolver` / `SynthesisIdentity` in `voice_audio_resolver.py`; `EXACT_AUDIO_RESOLVER_EVIDENCE_TERM`; focused exact-match and identity-mismatch tests | A precomputed artifact matches only exact rendered spoken-text SHA-256 and full provider/model/voice/version/locale/reference/codec/rate/channel/generation identity. Identifier-only matching is rejected. |
| stale-slot regression test | `REASON_STALE_SLOT_INVALIDATED` path; `STALE_SLOT_REGRESSION_TEST_EVIDENCE_TERM`; `test_stale_slot_regression_test_invalidates_phone_change`; router path `test_stale_slot_runtime_path_falls_through_without_serving_stale_audio` | Changing a grounded phone (or other factual slot) invalidates stale audio even when template/response identifiers are unchanged; never serves phone-A audio for phone-B rendering. |
| content-addressed GraphRAG restore | `SlottedResponseIndex.from_dict` over `manifests/graphrag-index.json` in `AbbyVoiceReleaseLoader.load_local`; graph/index CID equality checks | Restored index CIDs must match the sealed release manifest. |
| text-only or live-TTS fallback receipt | Miss path records deterministic `resolver_reason` on synthesis stage traces; live TTS success preserves GraphRAG provenance; total failure returns `text_only` without false audio | Resolver failure falls through without inventing near matches or weakening provenance. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-019-objective-validation-repair.md | this receipt + `G019_AUTHORITATIVE_EVIDENCE_MAP` / `test_evidence_phrases_are_discoverable` | Residual scan must re-find the four evidence phrases on the authorized paths. |

## Acceptance assertions

1. The loader requires a release manifest plus immutable dataset commit SHA,
   validates descriptors before use, and loads only the manifest, relevant
   GraphRAG support indexes, and selected Parquet shards.
2. A precomputed artifact matches only the exact rendered spoken-text SHA-256
   and the full provider/model/voice/version/locale/reference/codec/rate/
   channel/generation identity.
3. Changing a grounded phone, address, ZIP, hours, eligibility, amount, or
   emergency slot invalidates stale audio even if the template or
   slotted-response identifier is unchanged.
4. Missing or invalid audio records a deterministic resolver reason and falls
   through to live TTS or text-only behavior without weakening GraphRAG
   provenance.
5. Runtime caller audio and transcripts are neither cached into the public
   release nor written into ordinary receipts.
6. Defining symbols are importable from the task-owned modules without mutating
   package-root `__init__.py`.

## Validation receipt

Command:

```text
python -m pytest -q ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py ipfs_accelerate_py/test/test_voice_router_graphrag.py
```

Result on 2026-07-26: **passed — 20 passed**.

The gate is offline and uses only local fixtures; it requires no credentials
and performs no network or remote bucket/dataset write.

## Supervisor and child-goal alignment

This evidence remains aligned with merge family `objective/ABBY-VOICE-G019`,
bundle `abby-voice/runtime-release`, and parallel lane
`abby-voice-integration`. No supervisor-generated TODO, vector index, objective
graph, or task-status metadata was manually completed or regenerated; the
implementation daemon remains responsible for rebuilding those artifacts after
its validation gate.

No smaller child goal is needed. Pinned release loading, exact audio reuse,
stale-slot invalidation, and router runtime resolution form one G019 boundary.
G010 owns wallet rollout; G020 owns deployed-like end-to-end gates; G021 alone
owns publication and promotion.
