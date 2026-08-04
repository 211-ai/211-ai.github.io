# Abby content → logical-action link schema (v1)

| Field | Value |
| --- | --- |
| Schema id | `voice-action/action-link@1` |
| Schema version | `abby_content_action_link_v1` |
| Task | `VOICE-ACTION-004` |
| Goal | `VOICE-ACTION-G020` |
| Python module | `ipfs_datasets_py.voice.action_links` |
| Plane | **Content** (never authority / execute) |
| Doctrine | `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` (`INV-CONTENT-001`) |

This schema defines optional, versioned **content-plane** links from Abby
slotted-DAG routes to catalog **logical actions** plus optional confirmation
and outcome speech frame IDs. Links are deployment maps expressed as content
data; they do **not** grant execute authority and must never embed
executables.

Downstream rebuild (VOICE-ACTION-005) projects the full 12-route slotted DAG
into this shape.

## Dual-plane rule

```text
content plane (action-link record)
  -> route + logical_action + frame ids only
authority plane (catalog / policy / confirmation / adapter)
  -> ActionReceipt + spoken outcome selection
```

## Record shape (single link)

```json
{
  "schema": "voice-action/action-link@1",
  "schema_version": "abby_content_action_link_v1",
  "link_id": "action-link-<sha256-prefix-24>",
  "route": "app_surface_navigation",
  "logical_action": "open_app_surface",
  "classification": "proposal-eligible",
  "confirmation_frame_id": "frame.action.confirm.open_app_surface.v1",
  "outcome_frame_ids": {
    "success": "frame.action.outcome.open_app_surface.success.v1",
    "denied": "frame.action.outcome.open_app_surface.denied.v1",
    "failed": "frame.action.outcome.open_app_surface.failed.v1",
    "cancelled": "frame.action.outcome.open_app_surface.cancelled.v1",
    "unknown": "frame.action.outcome.open_app_surface.unknown.v1"
  },
  "evidence_cids": ["bafy…"],
  "notes": "optional operator note"
}
```

`logical_action_id` is accepted as a parse-time synonym for `logical_action`
(plan vocabulary); normalized output always emits `logical_action`.

### Required fields

| Field | Type | Rules |
| --- | --- | --- |
| `schema` | string | Must equal `voice-action/action-link@1` |
| `schema_version` | string | Must equal `abby_content_action_link_v1` |
| `route` | string | Lower-snake slotted-DAG route id (`^[a-z][a-z0-9_]{0,127}$`) |
| `logical_action` | string | Catalog logical action id, or `no_action` |
| `classification` | string | One of `content-only`, `proposal-eligible`, `safety-overlay` |

### Optional fields

| Field | Type | Rules |
| --- | --- | --- |
| `link_id` | string | If present, must match the deterministic id from content |
| `confirmation_frame_id` | string \| null | Safe content frame id; forbidden on `content-only` |
| `outcome_frame_ids` | object | Map of outcome role → frame id; empty or absent on `content-only` |
| `evidence_cids` | string[] | Content-plane evidence only; de-duplicated, order-preserving |
| `notes` | string \| null | Human annotation; not authority |

### Outcome frame roles

Keys of `outcome_frame_ids` are restricted to:

| Role | Meaning |
| --- | --- |
| `success` | Side effect completed **with** authority-plane receipt |
| `denied` | Policy / caller denied without execute |
| `failed` | Admitted attempt failed |
| `cancelled` | Caller cancelled during confirmation |
| `unknown` | Receipt missing or indeterminate (handoff must not claim success) |

### Classification rules

| Classification | `logical_action` | Frames |
| --- | --- | --- |
| `content-only` | **Must** be `no_action` | Must omit confirmation and outcome frames |
| `proposal-eligible` | Real catalog id (not `no_action`) | Optional confirmation / outcome frames |
| `safety-overlay` | Real catalog id (e.g. `escalate_safety`) | Optional confirmation / outcome frames |

Missing route maps fail closed as `no_action` / deny at consumers
(`ActionLinkDocument.logical_action_for`).

## Document shape (multi-link)

```json
{
  "schema": "voice-action/action-link@1",
  "schema_version": "abby_content_action_link_v1",
  "document_id": "action-link-doc-<sha256-prefix-24>",
  "source": "optional rebuild source label",
  "links": [ /* ActionLink records */ ],
  "content_digest": "<optional full sha256 of identity body>"
}
```

- Links are de-duplicated by `route` and sorted by `route` for stable digests.
- `document_id` and optional `content_digest` are content-addressed; mismatches
  fail closed.

## Forbidden content fields (fail closed)

Action-link records, nested objects, and argument maps **reject** these field
names (case-insensitive), matching doctrine `INV-CONTENT-001` and
`action_runtime.contracts.ActionProposal` bans:

| Forbidden class | Fields |
| --- | --- |
| Shell / process | `command`, `argv`, `executable`, `shell`, `cwd` |
| Environment / secrets | `env`, `credentials`, `secret` |
| Code locators | `import`, `import_path` |
| Network locators | `url`, `webhook` |
| Path smuggling | any key ending in `_path` |

Content may carry only:

- `logical_action` (catalog name or `no_action`);
- content frame ids;
- evidence CIDs and non-locator notes.

## Determinism

- Serialization uses UTF-8 JSON with `sort_keys=True`, compact separators, and
  `allow_nan=False`.
- `link_id` = `action-link-` + first 24 hex chars of SHA-256 over
  `{schema, route, logical_action, confirmation_frame_id, outcome_frame_ids}`.
- `outcome_frame_ids` keys are sorted before identity hashing.
- Golden vectors live in `golden_action_link_vectors()` /
  `golden_action_link_document()` and must digest identically across runs.

## Python API surface

```python
from ipfs_datasets_py.voice.action_links import (
    ActionLink,
    ActionLinkDocument,
    ActionLinkSchemaError,
    NO_ACTION,
    parse_action_link,
    parse_action_link_document,
    reject_forbidden_content_fields,
    validate_action_link,
    golden_action_link_document,
)
```

## Non-goals (v1)

- Catalog descriptor digests or adapter bindings (authority plane).
- Executable argv construction or MCP server URLs.
- Claiming handoff / transfer success without an authority-plane receipt.

## Related artifacts

| Artifact | Path |
| --- | --- |
| Integration doctrine | `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` |
| Assurance verdict schema | `docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json` |
| Python implementation | `ipfs_datasets_py/ipfs_datasets_py/voice/action_links.py` |
| Unit tests | `ipfs_datasets_py/tests/unit/voice/test_action_links.py` |
| Downstream projection | `docs/phone_dialog_generation/slotted_response_action_links.json` (VOICE-ACTION-005) |
