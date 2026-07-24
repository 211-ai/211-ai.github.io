# ABBY-VOICE-AUTO-006 Objective Validation Repair

Date: 2026-07-23

Goal id: ABBY-VOICE-G007

Task id: ABBY-VOICE-AUTO-006

Goal title: Add GraphRAG response-template ingestion and retrieval

Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`

Priority: P0

Track: voice-graphrag

Heap parent goals: ABBY-VOICE-G004, ABBY-VOICE-G005, ABBY-VOICE-G011

Supervisor-recorded parent goals: ABBY-VOICE-G004, ABBY-VOICE-G005

Graph depth: 3

Bundle: abby-voice/graphrag-templates

Merge family: objective/ABBY-VOICE-G007

Merge role: validation_gate

Work scope: objective_validation_repair

Todo vector key: `a5461a4fe555f956`

Merge key: `48fb2e0da7bdd0b3`

Canonical task CID:
`baguqeeralrgle2takhb7xcvzkiqrhngtmle5phmu35wcp7mhpnd3xvc27r2q`

Source gap fingerprint:
`961cb0c87404aa2afd2afa62f661db994d5b25f6`

## Finding

The source objective scan reported the literal missing evidence term
`objective validation repair`. Its present-evidence section attributed the
GraphRAG provider, IPLD graph, hybrid retrieval, slot safety, provenance tests,
and completion receipt to unrelated Chainlink/ProveKit matrices, workflow
examples, conversation shards, and IndexTTS batch JSON because those files
happened to contain matching AST tokens or embedding phrases.

Those are token-coincidence matches. They neither define Abby response-template
retrieval nor assert its current-evidence safety policy. This receipt supersedes
that false-positive mapping without changing the source gap report.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| GraphRAGVoiceTemplateProvider implementation | `GraphRAGVoiceTemplateProvider`, `EvidenceRecord`, provider aliases, and plan mapping in `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py`; provider-shape and alias assertions in `ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py`; contract in `docs/data/ABBY_VOICE_GRAPHRAG.md` | The provider is synchronous, import-light, accepts current evidence, applies confidence/locale/intent/result constraints, and returns an unrendered router-compatible plan with grounded slots and machine provenance or `None`. |
| IPLD template intent evidence graph | `GraphNode`, `GraphEdge`, `TemplateGraphSnapshot`, `_build_graph`, valid CIDv1 content identities, and injected `IPLDKnowledgeGraph` publication in `voice/graphrag.py`; graph-kind, relationship, deterministic order/CID, non-mutation, round-trip, and injected-graph assertions in the focused suite | Canonical intent/template/slot/evidence/response/audio/provenance nodes and typed edges serialize deterministically. Evidence graph nodes retain source CIDs but no fact values; response examples are explicitly historical. |
| hybrid template retriever | `SlottedResponseIndex`, dependency-free lexical/sparse-vector/graph scoring, optional `IPLDVectorStore` publication/search, bounded query expansion, stable tie-breaking, and filters in `voice/graphrag.py`; lexical, injected-vector, tie, confidence, locale, intent, and limit assertions in the focused suite | Ranking combines normalized lexical/vector/graph evidence, exact intent, and current source coverage, then orders by confidence and stable template ID. It performs no model/network work by default and ignores collaborator answer/slot output. |
| slot binding safety policy | `_normalize_current_evidence`, `_bind_template`, `EvidenceRecord`, and `UnsafeSlotBindingError` in `voice/graphrag.py`; stale-value, missing-fact, disallowed-CID, malformed-evidence, and contradictory-current-source assertions in the focused suite; explicit policy in `ABBY_VOICE_GRAPHRAG.md` | Every placeholder binds only from an exact structured fact on current evidence with a CID declared by the template. Missing or disagreeing facts fail closed. `AbbyVoiceResponse.slot_values` are never indexed or read as current facts. |
| retrieval provenance tests | `TemplateMatch`, `IngestionReceipt`, graph/index CIDs, source records, and retrieval metadata in `voice/graphrag.py`; source ordering, CID, provenance ID, audio ID, score component, graph/index identity, JSON round-trip, and response-plan-only assertions in the focused suite | A returned slot cites emitted source IDs; emitted sources retain CIDs/facts/metadata; receipts retain canonical template, graph, index, audio, and provenance identities without inventing citations from prose. |
| ABBY-VOICE-G007 completion receipt | This file, the G007 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`, focused implementation tests, and `docs/data/ABBY_VOICE_GRAPHRAG.md` | The exact offline objective validation command passes and each G007 evidence phrase resolves to defining code and a focused assertion rather than unrelated artifacts. |

## Acceptance assertions

The focused suite establishes all of the following:

1. canonical v2 templates, responses, audio, and provenance form a typed
   intent/template/slot/evidence/response/audio/provenance graph;
2. source CIDs and relationships survive graph serialization while current
   fact values are never persisted in evidence nodes;
3. response examples are marked historical and their response/slot wording is
   absent from retrievable fact state;
4. canonical input mappings are not mutated, reversed input order produces the
   same graph/index JSON and CIDs, and nodes/edges are stably sorted;
5. exact duplicates are idempotent, while conflicting IDs, broken references,
   and slotted templates without source-CID allowlists reject before local
   state replacement;
6. the provider exposes every method name recognized by the lazy voice-router
   adapter and returns its expected mapping fields;
7. lexical, sparse-vector, injected-vector, and graph signals participate in
   deterministic hybrid ranking with a stable template-ID tie break;
8. locale, explicit intent, confidence boundary, and result limit filters are
   enforced;
9. every placeholder binds from an allowed current evidence fact and cites its
   source ID/CID;
10. a historical phone number is never returned when current cited evidence
    has a newer number;
11. missing, malformed, CID-less, disallowed, or contradictory current
    evidence fails closed without fabricating a slot value;
12. result provenance includes source IDs/CIDs, score components, template
    checksum/source/provenance IDs, graph/index CIDs, historical match IDs, and
    audio IDs in stable order;
13. returned templates remain response plans, including safe slotless plans,
    and no injected query-expander answer or slot field can replace them;
14. checked JSON export/restore preserves graph, index, and retrieval identity
    and rejects tampering; and
15. module import loads no FAISS, Transformers, NetworkX, IPLD CAR, model, or
    network collaborator.

All fixtures are synthetic public-service data. Tests use injected local
collaborators and perform no credential lookup, model download, paid request,
IPFS mutation, Hugging Face mutation, or other remote operation.

## Validation receipt

Exact command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py
```

Result recorded on 2026-07-23:

```text
19 passed in 0.52s
```

The suite emitted no skip, warning, network call, or optional-dependency
fallback.

## Supervisor and child-goal alignment

This repair preserves the supervisor-fed identity:

- task `ABBY-VOICE-AUTO-006` and goal `ABBY-VOICE-G007`;
- supervisor-recorded parents `ABBY-VOICE-G004` and `ABBY-VOICE-G005`, graph
  depth 3, bundle
  `abby-voice/graphrag-templates`, track `voice-graphrag`, and P0 priority;
- merge family `objective/ABBY-VOICE-G007`, merge role `validation_gate`, work
  scope `objective_validation_repair`, todo vector key `a5461a4fe555f956`, and
  merge key `48fb2e0da7bdd0b3`;
- exact focused validation command shown above;
- implementation output
  `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py`;
- test output
  `ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py`;
- contract output `docs/data/ABBY_VOICE_GRAPHRAG.md`;
- planning output `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`; and
- this discovery receipt.

The repository heap also records `ABBY-VOICE-G011` as a parent. That is a newer
heap refinement: G011 owns immutable inventory and complete curated
materialization, while this G007 implementation can ingest any already
canonical G004/G005 rows. The generated source gap, bundle shard, and todo
vector still list only G004/G005. This receipt preserves both states explicitly
so the supervisor can regenerate its derived backlog after merge; it does not
silently erase the newer heap dependency or claim that stale generated
metadata is already identical.

No supervisor-generated todo, vector index, graph, or task status was edited
manually. The implementation daemon owns backlog completion and post-merge
regeneration.

No smaller child goal is needed. G007 is the cohesive canonical indexing,
hybrid retrieval, and current-evidence binding boundary. G008 retains
voice-router rendering/orchestration, G009 retains safety/performance
evaluation, and G011 retains immutable source inventory and full curated
dataset materialization.
