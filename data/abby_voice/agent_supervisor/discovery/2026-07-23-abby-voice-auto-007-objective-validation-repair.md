# ABBY-VOICE-AUTO-007 Objective Validation Repair

Date: 2026-07-23

Goal id: `ABBY-VOICE-G008`

Task id: `ABBY-VOICE-AUTO-007`

Goal title: Integrate GraphRAG templating into `voice_router`

Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`

Priority: P0

Track: `voice-graphrag`

Parent goals: `ABBY-VOICE-G002`, `ABBY-VOICE-G003`, `ABBY-VOICE-G007`

Graph depth: 4

Bundle: `abby-voice/router-graphrag-integration`

Work scope: `objective_validation_repair`

Source gap fingerprint: `3380db9aa1f3dcb10a9c90abfa30ce9f3bc4a654`

## Finding

The source objective scan reported the synthetic missing evidence term
`objective validation repair` and attributed the router's GraphRAG behavior to
unrelated generated Chainlink, ProveKit, world-ID, and IndexTTS artifacts. Those
token/AST matches do not define or validate the Abby voice-turn integration.
This receipt replaces those matches with directly authoritative code, tests,
and an objective-heap acceptance gate. No remote state was read or changed.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| Optional GraphRAG template boundary | `VoiceTemplateProvider`, `GraphRAGVoiceTemplateProvider`, and `process_voice_turn` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; canonical prompt helper in `ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py` | The router accepts an injected provider, builds a deterministic STT transcript/context/grounding query envelope, supports opt-in `prompt_parts`, and imports no `ipfs_datasets_py` or model dependency at module load. |
| Grounded slot binding | `_coerce_response_plan`, `_grounding_override_slots`, and `_render_grounded_plan` in `voice_router.py`; unsafe-source/conflicting-fact cases in `ipfs_accelerate_py/test/test_voice_router_graphrag.py` | Every placeholder has a non-empty slot, a known evidence source, and a matching structured current fact when that fact is declared. Unknown, missing, or conflicting evidence is rejected before TTS. |
| Citation stripping with retained machine provenance | `normalize_spoken_text` in `voice_templates.py`, router rendering, and the focused full-turn test | URLs, CIDs, and visual citation syntax are absent from synthesized text, while template ID, evidence CID, grounded slots, hashes, and stage details remain in `VoiceTurnResult.provenance`. Citation-only output fails closed. |
| Deterministic fallback and explicit stage traces | `DEFAULT_GROUNDED_FALLBACK` and `process_voice_turn` in `voice_router.py`; retrieval-failure, grounding-failure, and TTS-failure tests | Retrieval/grounding failures synthesize the safe fallback and record a stable reason/failed trace. TTS failure returns `text_only` with no false audio or output-audio hash. |
| Integration tests with a fake GraphRAG provider | `ipfs_accelerate_py/test/test_voice_router_graphrag.py` | The exact focused command passes using only in-memory STT, GraphRAG, and TTS fakes; prompt canonicalization and non-mutation are asserted. |
| ABBY-VOICE-G008 completion receipt | This file and the G008 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | Each G008 evidence term resolves to the defining implementation plus a focused offline assertion, not a coincidental token match. |

## Acceptance assertions

The focused suite establishes all of the following:

1. Prompt parts are canonical across mapping insertion order, preserve caller
   inputs, validate transcript/result limits, and contain instructions for
   response plans rather than generated final-answer prose.
2. The lazy adapter passes the prompt envelope to an explicitly opting-in
   backend and remains compatible with older narrow GraphRAG backend methods.
3. The complete path executes transcription, retrieval, rendering, and
   synthesis in order and returns a completed typed receipt.
4. Grounded factual slots cite current evidence; stale, unknown, and
   conflicting values fail closed before synthesis of the unsafe content.
5. Visual citations are stripped from spoken text but source CID and slot
   provenance are retained in the machine result.
6. Retrieval failure is visible and deterministic, the safe fallback remains
   synthesizable, and TTS failure produces text-only degradation without false
   audio.
7. Attribute, conversion, and format expressions are rejected rather than
   executed during template rendering.

## Validation receipt

Exact command:

```text
python -m pytest -q ipfs_accelerate_py/test/test_voice_router_graphrag.py
```

Result on 2026-07-23: **passed — 9 passed in 0.67s**.

The suite emitted no skip and made no network, credential, model, IPFS, or
Hugging Face call. The broader existing grounded-pipeline and contract suites
also passed after the additive integration:

```text
python -m pytest -q tests/voice/test_abby_voice_pipeline.py ipfs_accelerate_py/test/test_voice_router_contracts.py
```

Result: **49 passed** (one unrelated existing Starlette deprecation warning).

## Supervisor and child-goal alignment

This repair preserves the supervisor-fed identity:

- task `ABBY-VOICE-AUTO-007`, goal `ABBY-VOICE-G008`, P0, and track
  `voice-graphrag`;
- parents G002/G003/G007, graph depth 4, bundle
  `abby-voice/router-graphrag-integration`, and validation-gate role;
- implementation outputs `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`
  and `ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py`;
- focused test output `ipfs_accelerate_py/test/test_voice_router_graphrag.py`;
- planning output `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`; and
- exact offline validation command shown above.

No supervisor-generated todo, vector index, graph, or task-status metadata was
rewritten. The implementation daemon owns backlog regeneration after merge.
No smaller child goal is required: G008 is the cohesive router-side prompt,
rendering, provenance, fallback, and TTS orchestration boundary.
