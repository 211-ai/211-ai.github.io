# Abby Voice GraphRAG Response Plans

## Scope and safety invariant

`ipfs_datasets_py.voice.graphrag` ingests canonical Abby voice v2 templates,
responses, audio metadata, and provenance into a deterministic response-frame
index. It retrieves response plans for the voice router. It does not generate
or return an uncited final answer.

The central invariant is:

> Historical response wording may improve intent retrieval, but historical
> slot values are never facts. Every placeholder returned to the router must
> be bound from a CID-bearing evidence record supplied for the current turn.

This boundary prevents a phone number, address, service name, opening status,
hours, or eligibility statement embedded in an old example from silently
becoming a current spoken claim. If current evidence is missing, disallowed, or
contradictory, the provider returns no plan and the router uses its explicit
degraded path.

## Inputs

The index accepts the four independent, flat v2 configurations defined in
`ipfs_datasets_py.voice.schema`:

| Configuration | GraphRAG use |
| --- | --- |
| `abby_voice_template_v2` | Response shell, intent, locale, declared slots, source-CID allowlist, safety labels, and provenance links |
| `abby_voice_response_v2` | Historical caller utterance for retrieval and response-to-template relationships; response text and slot values are not indexed as facts |
| `abby_voice_audio_v2` | Template/response audio relationships and content identity |
| `abby_voice_provenance_v2` | Transformation, source, revision, checksum, parent, and subject relationships |

`SlottedResponseIndex.from_rows(...)`, `ingest(...)`, and `ingest_records(...)`
all validate canonical schema and cross-config references before replacing the
local index state. Exact duplicates are idempotent. Conflicting rows with the
same stable ID, missing referenced templates/audio/provenance, and a slotted
template without a source-CID allowlist are rejected.

Inputs are parsed into immutable canonical rows and are never changed in place.
No order, clock, UUID, Python hash seed, local path, or remote state participates
in graph identity.

## Template-intent-evidence graph

The dependency-free graph snapshot uses these node kinds:

- `intent`: locale-scoped canonical intent;
- `template`: response frame and declared safety/grounding metadata;
- `slot`: one placeholder scoped to a template;
- `evidence`: a source CID link, deliberately without persisted fact values;
- `response`: historical intent exemplar, without response slot values;
- `audio`: content-addressed audio metadata; and
- `provenance`: source and transformation lineage.

Typed relationships include:

- `intent -ROUTES_TO-> template`;
- `template -DECLARES_SLOT-> slot`;
- `slot -REQUIRES_EVIDENCE-> evidence`;
- `template -SUPPORTED_BY-> evidence`;
- `response -INSTANCE_OF-> template`;
- `response -EXAMPLE_OF-> intent`;
- `response -HISTORICAL_BINDING-> slot`;
- `template|response -HAS_AUDIO-> audio`;
- `provenance -DESCRIBES-> template|response|audio`; and
- `provenance -DERIVED_FROM-> evidence`.

`HISTORICAL_BINDING` carries `value_indexed_as_fact: false`. Evidence nodes
carry `facts_persisted: false`. These flags are audit evidence; retrieval also
enforces the policy structurally by never reading `AbbyVoiceResponse.slot_values`
while binding a plan.

Nodes and edges are serialized in stable ID order. `graph_cid` and `index_cid`
are valid CIDv1/raw/sha2-256 identifiers over canonical JSON. The index CID
covers the canonical rows, normalized ranking weights, and graph CID.
`to_dict()` and `from_dict()` provide a checked JSON round trip; tampered
content does not retain the claimed CID.

## Hybrid retrieval

`SlottedResponseIndex.search(...)` combines three normalized signals:

1. lexical similarity across the intent, response shell, safety labels, tags,
   and historical caller utterances;
2. deterministic 256-dimensional signed hashed-token cosine similarity, or the
   maximum of that score and an injected vector-store score; and
3. graph relevance from intent/example similarity and the fraction of the
   template source-CID allowlist present in current evidence.

The default normalized weights are `0.45` lexical, `0.35` vector, and `0.20`
graph. Exact normalized intent matches receive at least `0.95`. Results are
ordered by descending confidence and then ascending stable template ID.
Locale, explicit intent, minimum score, and positive result limits are enforced
before a provider returns a plan.

An injected embedder may replace the deterministic sparse vector. An injected
vector store can implement `upsert_documents`, `add_documents`, or the current
`IPLDVectorStore.add_embeddings` shape and a `search` method. An injected
`GraphRAGLLMProcessor`-like collaborator may only expand retrieval query text
through `expand_query` or `enhance_query`. Returned answer or slot fields are
ignored; an LLM never supplies facts or final response prose.

## Current-evidence binding

`GraphRAGVoiceTemplateProvider` is synchronous and implements all backend names
recognized by the voice-router adapter:

- `retrieve_voice_template(...)`;
- `retrieve_template(...)`; and
- `retrieve(...)`.

Current grounding is supplied as `sources`, `evidence`, or `current_evidence`.
Each record must have:

- a non-empty `source_id`;
- a non-empty `cid`;
- a `facts` mapping whose keys are safe declared slot names and whose values
  are non-null JSON scalars suitable for deterministic spoken rendering; and
- optional `uri`, `text`/`excerpt`, and JSON-safe `metadata`.

For each template placeholder, the provider:

1. discards evidence whose CID is not in the template's declared
   `source_cids`;
2. finds current records containing a structured fact with the exact slot
   name;
3. fails closed if the fact is missing;
4. fails closed if allowed current sources disagree on the value;
5. binds the one agreed JSON value; and
6. attaches every agreeing evidence `source_id` to the slot.

All placeholders must bind, including slots not marked required by the dataset
schema, because the downstream formatter cannot safely render a partial frame.
A slotless clarification or safety shell may return without evidence because
it contains no inserted factual value.

Malformed evidence raises `UnsafeSlotBindingError`. A normal lack of matching
current evidence or conflicting current values excludes the candidate and
returns `None` when no other safe candidate exists.

## Router-compatible output

The provider returns a mapping compatible with
`ipfs_accelerate_py.voice_router.GraphRAGVoiceTemplateProvider`:

```json
{
  "template_id": "food-frame",
  "template": "{program} can help. Call {phone}.",
  "slots": [
    {
      "name": "program",
      "value": "Community Food Network",
      "source_ids": ["food-current"]
    },
    {
      "name": "phone",
      "value": "503-555-0111",
      "source_ids": ["food-current"]
    }
  ],
  "sources": [
    {
      "source_id": "food-current",
      "cid": "bafy-current-food",
      "uri": "ipfs://bafy-current-food",
      "text": "Current public service record.",
      "facts": {
        "program": "Community Food Network",
        "phone": "503-555-0111"
      },
      "metadata": {
        "revision": "2026-07-23"
      }
    }
  ],
  "confidence": 0.95,
  "intent": "food_assistance",
  "metadata": {
    "response_plan_only": true,
    "retrieval": "hybrid"
  }
}
```

The `template` remains unrendered. The voice router validates slot/source
identity and fact equality, renders the shell, strips visual citations from
spoken text, and retains machine provenance.

Retrieval metadata also includes:

- lexical, vector, and graph score components;
- exact-intent status;
- content-addressed `index_cid` and `graph_cid`;
- canonical template content SHA-256;
- allowed template source CIDs and provenance IDs;
- matched historical response IDs and available audio IDs; and
- `historical_example_values_used_as_facts: false`.

## IPLD and optional collaborators

The implementation names the production integration boundaries
`IPLDKnowledgeGraph`, `IPLDVectorStore`, `GraphRAGLLMProcessor`, and
`SlottedResponseIndex`, but imports the first three only for static typing.
Importing `ipfs_datasets_py.voice.graphrag` does not load FAISS, Transformers,
NetworkX, IPLD CAR support, an LLM, or a network client.

When an `IPLDKnowledgeGraph`-compatible object is injected, ingestion publishes
stable node/relationship IDs with their properties and reports its external
root CID when present. When a vector-store-compatible object is injected,
canonical template documents and deterministic embeddings are published once
per template ID. The local content-addressed graph and sparse index remain the
offline, reproducible source of retrieval behavior.

An asynchronous injected store is resolved only when no event loop is already
running. A synchronous voice-provider call inside a running loop fails clearly
instead of nesting an event loop or leaking a coroutine. External vector search
failures degrade to the built-in vector score and expose only a privacy-safe
exception type through `last_collaborator_errors`.

## Offline example

```python
from ipfs_datasets_py.voice import (
    AbbyVoiceTemplate,
    GraphRAGVoiceTemplateProvider,
    SlottedResponseIndex,
)

template = AbbyVoiceTemplate(
    template_id="food-frame",
    template_text="{program} can help. Call {phone}.",
    spoken_template="{program} can help. Call {phone}.",
    intent="food_assistance",
    slot_names=("program", "phone"),
    required_slot_names=("program", "phone"),
    factual_slot_names=("program", "phone"),
    source_cids=("bafy-current-food",),
    license_id="CC-BY-4.0",
    consent_status="not_required",
)

provider = GraphRAGVoiceTemplateProvider(
    SlottedResponseIndex.from_rows(templates=[template])
)
plan = provider.retrieve(
    "I need food assistance",
    language="en-US",
    grounding={
        "sources": [{
            "source_id": "food-current",
            "cid": "bafy-current-food",
            "facts": {
                "program": "Community Food Network",
                "phone": "503-555-0111",
            },
        }]
    },
)
```

The example is entirely local. Production callers decide how current evidence
is retrieved and verified before passing it to this boundary.

## Validation

Run the focused offline gate:

```bash
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py
```

The suite uses synthetic public-service metadata, injected collaborators, and
no credentials, model downloads, network calls, IPFS writes, or mutable remote
datasets.
