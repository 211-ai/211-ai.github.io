# ABBY-VOICE-AUTO-011 Objective Validation Repair

Date: 2026-07-25
Source gap fingerprint: `d5cfef28e2c8bad4150e3dbde15e17080b81d882`
Goal id: `ABBY-VOICE-G012`
Task id: `ABBY-VOICE-AUTO-011`
Goal title: Generalize immutable Hugging Face source snapshots
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-data`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G004`, `ABBY-VOICE-G005`, `ABBY-VOICE-G006`
Graph depth: 4
Bundle: `abby-voice/hf-sources`
Work scope: `goal_subgoal_multi_evidence_batch`

## Finding

The source objective scan reported three missing evidence terms:
`backward-compatible generic snapshot/cache API`, `tamper and mutable-ref
rejection tests`, and `no-network cache-hit test`. Its present-evidence
matches were unrelated inventory artifacts or the pre-generalization
SkillCenter implementation. They do not prove that arbitrary Hugging Face
dataset and bucket sources can reuse the verified cache, that the legacy
SkillCenter interface remains compatible, or that a populated cache hit is
network-free.

This repair replaces those coincidental matches with the defining generic
implementation, its explicit SkillCenter compatibility layer, and focused
offline assertions. It does not read or change remote Hugging Face state.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| backward-compatible generic snapshot/cache API | `HuggingFaceSnapshot` and `HuggingFaceSnapshotCache` in `ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py`; the compatibility exports and reader adapter in `ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/source_adapters/snapshot.py`; `test_generic_snapshot_api_preserves_skillcenter_wire_contract` and `test_generic_and_skillcenter_cache_share_existing_alias` in `ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py`; the complete legacy suite in `ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py` | Generic dataset manifests carry Hugging Face dataset ID, immutable revision, normalized relative repository path, expected full SHA-256, byte length, content CID, producer, and content-addressed cache path. Existing `SkillCenterSnapshot`, `SkillCenterSnapshotCache`, `HuggingFaceSkillCenterFetcher`, exception, serialization, artifact, and read-only bundle-reader behavior remains import- and wire-compatible. Generic and SkillCenter callers can verify the same cache alias rather than creating incompatible identities. |
| tamper and mutable-ref rejection tests | The generic aliases in `ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py` and underlying validation/cache-hit revalidation in `ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/source_adapters/snapshot.py`; `test_generic_cache_rehashes_hit_and_rejects_tamper`, `test_generic_snapshot_rejects_mutable_revision`, and `test_generic_cache_rejects_tampered_alias_without_refetch` in `ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py`; `test_snapshot_rejects_mutable_revisions`, `test_cache_hit_is_rehashed_and_tampering_is_rejected`, `test_stale_alias_is_rejected_instead_of_retargeted`, and `test_alias_with_traversal_is_rejected` in the legacy SkillCenter suite | Both generic and compatibility surfaces reject `main`, `master`, `latest`, and `refs/heads/*`. Every hit rehashes bytes and revalidates size and alias identity. Corrupt bytes, stale or unsafe aliases, path traversal, symlink escapes, and partial targets fail closed with typed validation or integrity errors. |
| no-network cache-hit test | `test_cache_hit_never_calls_network_or_fetcher` in `ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py`, supplemented by `test_offline_cache_miss_never_attempts_network` in the legacy suite | The focused hit test populates through an injected local fetcher, reopens with a fetcher and `hf_hub_download` replacement that both fail if invoked, and returns the reverified content-addressed bytes without calling either. A true offline miss remains a typed cache miss rather than attempting implicit network access. |
| pinned dataset commit receipt | `HuggingFaceRepository` in `ipfs_datasets_py/ipfs_datasets_py/huggingface/repository.py` and its injected-client assertions in `ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py` | A mutable requested ref is resolved before receipt construction, but the canonical receipt contains and fetches by the returned immutable commit SHA. The client is injected; imports and receipt decoding have no network or credential side effects. |
| deterministic bucket inventory | `HuggingFaceBucketObject`, `HuggingFaceBucketInventory`, and `HuggingFaceBucketStore` in `ipfs_datasets_py/ipfs_datasets_py/huggingface/bucket.py`; `test_bucket_inventory_digest_is_order_independent_and_complete`, `test_bucket_store_uses_injected_read_only_inventory_client`, `test_bucket_store_fetches_verifies_and_atomically_promotes`, and `test_bucket_store_rejects_tampered_download` in `ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py` | Entries are normalized and sorted, require path, non-negative size, full SHA-256, ETag, and media type, and contribute all fields to the canonical inventory digest. The inventory/fetch client is injected and read-only; fetched bytes are atomically promoted only after size and full SHA-256 verification. |

## Acceptance assertions

The focused gate establishes all of the following:

1. the reusable manifest and cache support arbitrary pinned Hugging Face
   dataset repository artifacts without weakening content identity or cache
   safety;
2. the original SkillCenter names, wire schema, manifest identity, verified
   aliases, injected fetcher, artifact projection, and reader remain usable;
3. dataset receipts use an immutable resolved commit and reject mutable refs
   in canonical manifests;
4. bucket inventory identity includes normalized path, size, full SHA-256,
   ETag, and media type and is insensitive to input ordering;
5. fetched and cached byte tampering, alias tampering, mutable refs, traversal,
   partial paths, and symlink escapes fail closed;
6. a verified cache hit does not call its fetcher or Hugging Face download
   function, while an offline miss raises the typed cache-miss error; and
7. the source adapters expose no remote write, delete, move, overwrite, or
   release-pointer operation.

## Validation receipt

Focused command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py
```

Result on 2026-07-25: **passed — 56 passed in 0.97s**.

Both test files are required in one invocation: the first is the regression
gate for the existing SkillCenter public surface, and the second proves the
generic dataset/bucket adapters plus the three repaired evidence terms. The
gate is offline and uses only injected local doubles; it requires no
credentials and makes no network or remote bucket call.

## Supervisor and child-goal alignment

This repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-011`, goal `ABBY-VOICE-G012`, P0, track `voice-data`, parent
G011, dependencies G004/G005/G006, graph depth 4, bundle
`abby-voice/hf-sources`, and merge family `objective/ABBY-VOICE-G012`.

No supervisor-generated todo, vector-index, graph, or task-status metadata was
manually completed or rewritten. The implementation daemon owns backlog
status regeneration after the validation gate. No smaller child goal is
needed: the generic API, SkillCenter compatibility, tamper/mutable-ref
rejection, and no-network hit are one cohesive source-identity and
verified-cache boundary. G013 owns Abby row interpretation and workset
construction; G021 alone owns publication and remote writes.
