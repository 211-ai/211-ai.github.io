# Abby-aware action proposal retrieval

| Field | Value |
| --- | --- |
| Schema id | `voice-action/action-retrieval@1` |
| Schema version | `abby_action_retrieval_v1` |
| Task | `VOICE-ACTION-008` |
| Goal | `VOICE-ACTION-G050` |
| Python module | `ipfs_datasets_py.voice.action_retrieval` |
| Plane | **Content** (never authority / execute) |
| Doctrine | `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` |

This module projects Abby **slotted-DAG routes** (and optional GraphRAG grounded
response plans) into authority-free **action proposal candidates**. Retrieval
may only *propose* catalog-referenced logical actions. It never executes
adapters, never invents descriptors from free-text transcripts, and never
embeds executable locators.

## Dual-plane rule

```text
content plane (action retrieval)
  -> route + action-link map + template_id + evidence digests
  -> ActionProposalCandidate | explicit no_action
authority plane (catalog / policy / confirmation / adapter)
  -> ActionDecision / ActionReceipt + spoken outcome
```

**Authority monotonicity:** retrieval confidence, model output, embeddings, and
transcript free text may reduce confidence, request clarification, or attach
evidence. They can **never** increase authority or invent catalog descriptors.

## Normative pipeline

```text
channel input
  -> STT / transcript                                         [input]
  -> Abby GraphRAG plan (optional) + slotted DAG route        [content]
  -> action-link route map (VOICE-ACTION-004/005)             [content]
  -> ActionProposalCandidate (logical_action, evidence, ids)  [content emit]
  -> fail-closed policy / consent / confirmation              [authority]
  -> deployment-owned catalog binding                         [authority]
  -> admitted adapter                                         [authority]
```

## Inputs

| Input | Authoritative? | Notes |
| --- | --- | --- |
| Slotted-DAG `route` | **Yes** | Lower-snake route id from the response DAG |
| Action-link projection | **Yes** | `docs/phone_dialog_generation/slotted_response_action_links.json` |
| Catalog / descriptor map | Restrictive only | May only *reject* unknown logical actions (fail closed to `no_action`) |
| GraphRAG grounded plan | Non-authority | Supplies `template_id`, evidence CIDs, confidence |
| Transcript free text | Non-authority | Digested for provenance; never binds descriptors |
| Embeddings / suggested actions | Non-authority | Ignored for logical_action / descriptor binding |

## Outputs

### `ActionProposalCandidate`

Authority-free candidate. Either a proposal or an explicit `no_action`.

| Field | Type | Rules |
| --- | --- | --- |
| `route` | string | Lower-snake slotted-DAG route id |
| `logical_action` | string | Catalog logical action id, or `no_action` |
| `classification` | string | From the action-link map (`content-only`, `proposal-eligible`, `safety-overlay`) |
| `outcome` | string | `proposal` or `no_action` |
| `proposal_id` | string | Deterministic `prop-<sha256-prefix-16>` over content fields |
| `descriptor_id` | string \| null | Optional content-plane catalog reference; null for `no_action` |
| `template_id` | string \| null | Abby template id when known |
| `evidence` | string[] | Evidence CIDs / digests only (de-duplicated, order-preserving) |
| `confidence` | float | Clamped to `[0, 1]`; never upgrades authority |
| `arguments` | object | String-to-string; **forbidden** executable keys (see below) |
| `confirmation_frame_id` | string \| null | Content frame id from the action link |
| `outcome_frame_ids` | object | Content outcome frames from the action link |
| `link_id` | string \| null | Action-link content id when available |
| `metadata` | object | Always includes `template_id` and `evidence_digest` when present |

### `ActionRetrievalResult`

One retrieval turn:

- `route`, `candidates`, `primary`
- `transcript_digest` (SHA-256; raw adversarial text is not authority)
- optional `grounded_response` (GraphRAG plan, re-scanned for forbidden fields)

## Fail-closed rules

1. **Missing route map → `no_action`.** Unmapped routes never invent actions.
2. **Content-only routes → `no_action`.** Spoken response only; no side-effect proposal.
3. **Catalog reject → `no_action`.** When `require_catalog_entry=true` or an
   allowlist is configured, unknown logical actions fail closed instead of
   inventing descriptor ids.
4. **Transcript injection is ignored.** Strings such as
   `descriptor_id=voice.cli.evil.v1` or `logical_action=shell_exec` inside the
   transcript **do not** change binding. Helpers expose
   `extract_injection_claims` so tests can prove non-interference.
5. **Suggested logical actions / descriptor ids are non-authoritative.** Callers
   may pass embedding hints; the symbolic route map wins.
6. **Forbidden fields fail closed** on arguments, metadata, and grounded plans
   (aligned with `INV-CONTENT-001` and `action_runtime.contracts.ActionProposal`):

| Forbidden class | Fields |
| --- | --- |
| Shell / process | `command`, `argv`, `executable`, `shell`, `cwd` |
| Environment / secrets | `env`, `credentials`, `secret` |
| Code locators | `import`, `import_path` |
| Network locators | `url`, `webhook` |
| Path smuggling | any key ending in `_path` |

## Catalog validity

A result is **catalog-valid or `no_action`** when every candidate either:

- has `outcome=no_action` / `logical_action=no_action`, or
- names a logical action present in the allowlist (when provided) and, when a
  descriptor map is provided, carries the matching `descriptor_id`.

Sampling helper:

```python
from ipfs_datasets_py.voice.action_retrieval import (
    ActionProposalRetriever,
    catalog_valid_or_no_action,
)

retriever = ActionProposalRetriever.from_action_links_path(
    require_catalog_entry=True,
)
for result in retriever.sample_routes():
    assert catalog_valid_or_no_action(result)
```

## Python API surface

```python
from ipfs_datasets_py.voice.action_retrieval import (
    ActionProposalCandidate,
    ActionProposalRetriever,
    ActionRetrievalResult,
    catalog_valid_or_no_action,
    load_action_link_document,
    retrieve_action_proposals,
)

# Symbolic route map (default projection from VOICE-ACTION-005)
retriever = ActionProposalRetriever.from_action_links_path()

# Single route with optional GraphRAG plan
result = retriever.retrieve(
    route="app_surface_navigation",
    transcript="open the app for me",
    template_id="tmpl.app_surface.v1",
    evidence=("bafy…",),
    confidence=0.8,
)

# Functional API
result = retrieve_action_proposals(
    route="live_agent",
    template_id="tmpl.handoff.v1",
    evidence=("bafy…",),
)
```

### GraphRAG integration

When `grounded_response` is a plan dict from
`GraphRAGVoiceTemplateProvider.retrieve` / `retrieve_candidates`:

- `template_id` is taken from the plan when not supplied explicitly;
- evidence CIDs are collected from `sources[*].cid` and plan metadata
  (`index_cid`, `graph_cid`, `template_content_sha256`, …);
- plan confidence is used when present;
- plan free text **never** overrides the symbolic route → logical_action map.

Embeddings remain optional and non-authoritative.

## Determinism

- `proposal_id = prop-` + first 16 hex chars of SHA-256 over
  `{schema, route, logical_action, template_id, evidence, descriptor_id}`.
- Evidence lists are de-duplicated while preserving first-seen order.
- Transcripts are stored only as `transcript_digest` on the result envelope.
- Serialization helpers reuse `action_links.content_digest` (UTF-8 JSON,
  `sort_keys=True`, compact separators, `allow_nan=False`).

## Ownership

| Owner | Owns | Must not own |
| --- | --- | --- |
| `ipfs_datasets_py.voice.action_retrieval` | Content-plane proposal candidates, route sampling, injection non-interference | Catalog bindings, policy grants, adapter execution |
| `ipfs_accelerate_py.action_runtime.voice_bridge` | Authority-plane proposal factory / multi-route catalog validation (VOICE-ACTION-009) | Abby slotted DAG rebuild |
| Action-link projection | Route → logical_action map (VOICE-ACTION-004/005) | Executables |

## Related artifacts

| Artifact | Path |
| --- | --- |
| Integration doctrine | `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` |
| Action-link schema | `docs/voice_action_dag/schemas/action-link-v1.md` |
| Action-link projection | `docs/phone_dialog_generation/slotted_response_action_links.json` |
| Python implementation | `ipfs_datasets_py/ipfs_datasets_py/voice/action_retrieval.py` |
| Unit tests | `ipfs_datasets_py/tests/unit/voice/test_action_retrieval.py` |
| GraphRAG plans | `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py` |

## Non-goals (v1)

- Executing adapters or claiming side-effect success.
- Authority-plane catalog mutation or policy grants.
- Treating transcript free text or embeddings as descriptor authority.
- Replacing `voice_bridge` multi-route catalog upgrades (see VOICE-ACTION-009).

## Acceptance (VOICE-ACTION-008)

1. Route samples from the slotted-DAG action-link projection produce
   **catalog-valid proposals or explicit `no_action`**.
2. Adversarial transcripts cannot invent descriptors or smuggle
   command/argv/url/import fields.
3. Evidence digests and template ids are attached on candidates (including
   `no_action` outcomes when supplied).
