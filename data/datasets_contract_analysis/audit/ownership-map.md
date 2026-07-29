# Datasets Contract Analysis Ownership Map

- Goal: `DSCON-G010`
- Task: `DSCON-001`
- Validation repair task: `DSCON-062`
- Generated: `2026-07-29T15:18:35Z`
- Freeze status: `frozen`
- Schema: `datasets_contract_analysis/ownership-map@1`

This map freezes **repository authorities**, **package ownership**, and
**dataset-manipulator surface owners** before implementation changes. A
repository reference in documentation is **not** an authority until its path
and Git identity are verified. Unresolved authority **fail closed**.

Companion artifacts:

- [`source-roots.json`](./source-roots.json)
- [`datasets-manipulator-drift.json`](./datasets-manipulator-drift.json)

## 1. Selected composition identity

| Root | Path | Commit | Tree | Clean | Verified |
| --- | --- | --- | --- | --- | --- |
| 211-AI superproject | `.` | `09c30d4b85f08e82a6ad6b622b54c98bd72600f7` | `763928e8cfb2aefa2997c0420a591030342a4efb` | True | True |
| **package authority** | `ipfs_datasets_py` | `92c1eddb55b40e4de57d51545f4bcdfbf3fab645` | `d272fc680ff8e81c8e25cd319649ce957594af16` | (see gitlink table) | True |

### Direct gitlinks

| Path | Gitlink commit | Checkout commit | Tree | Status | Clean |
| --- | --- | --- | --- | --- | --- |
| `ipfs_accelerate_py` | `10d2e5b254970d217f0b7ee7c74478efb7d71e4a` | `10d2e5b254970d217f0b7ee7c74478efb7d71e4a` | `bfd8fba10121cb1059206db8b76a546ce5d9a17b` | verified | True |
| `ipfs_datasets_py` | `92c1eddb55b40e4de57d51545f4bcdfbf3fab645` | `92c1eddb55b40e4de57d51545f4bcdfbf3fab645` | `d272fc680ff8e81c8e25cd319649ce957594af16` | verified | True |
| `ipfs_kit_py` | `276d766b8076b725a5a9e53bcf0c057f067acd10` | `276d766b8076b725a5a9e53bcf0c057f067acd10` | `58411be37d8f2b8ebee2b73c8569cabf61d7fdc8` | verified | True |

Nested non-package gitlinks recorded: **17**.  
Recursive package **mirror cycles** recorded without rescan: **14**.

Mirror policy: when a nested gitlink path names `ipfs_accelerate_py`,
`ipfs_datasets_py`, or `ipfs_kit_py`, it is inventory-only. The freeze does
**not** rescan those mirrors (avoids recursive package cycles).

## 2. External and runtime roots

| Root | Configured path | Expected pin | Status | Commit | Tree | Selected authority? |
| --- | --- | --- | --- | --- | --- | --- |
| Swissknife | `/home/barberb/swissknife` | `df11f08f` (`df11f08f`) | matches_expected | `df11f08fae17d35153e420fdcdc5b38d9f6b9a7f` | `0534225ee42d334318e02afa6c54da0dc2974e36` | no (read-only analysis root) |
| Hallucinate datasets | `/home/barberb/hallucinate_app/ipfs_datasets_py` | `8dc4f93e` (`8dc4f93e`) | matches_expected | `8dc4f93eba281d943e4f1e9ba40db46419a449ca` | `9ae978c9fe40a76d964eeef656fb65c252794389` | no (runtime copy) |

Swissknife is **read-only**. This program may analyze and propose tasks; it must
not mutate the Swissknife repository without separate reviewed authority.

Hallucinate `ipfs_datasets_py` at `8dc4f93e` and the home standalone checkout
are recorded for **revision-mismatch** detection. The **package authority** for
211-AI contract analysis is the superproject gitlink only.

## 3. Domain ownership summary

| Domain | Current home | Decision | Target owner |
| --- | --- | --- | --- |
| Dataset package authority | `ipfs_datasets_py` gitlink | **retain** as authority | 211-AI pin `92c1eddb55b4` |
| Canonical dataset load | `core_operations/dataset_loader.py` | **retain** / harden | `ipfs_datasets_py.core_operations.DatasetLoader` |
| Canonical dataset save | `core_operations/dataset_saver.py` | **retain** / harden | `ipfs_datasets_py.core_operations.DatasetSaver` |
| Canonical dataset convert | `core_operations/dataset_converter.py` | **retain** / harden | `ipfs_datasets_py.core_operations.DatasetConverter` |
| Canonical dataset manipulate | *(missing `dataset_manipulator.py`)* | **create** | `ipfs_datasets_py.core_operations.DatasetManipulator` |
| Legacy DatasetManager | `ipfs_datasets_py/dataset_manager.py` | **deprecate** (mock-success) | thin wrapper over canonical core after repair |
| Legacy `generate_clusters` methods | `ipfs_datasets_py/ipfs_datasets.py` (2 definitions) | **deprecate** shadowed no-op methods | canonical bounded manipulator operation |
| MCP load/process/save/convert tools | `mcp_server/tools/dataset_tools/*` | **retain** as thin adapters | must not own manipulation after DSCON-G330 |
| DataProcessor | `core_operations/data_processor.py` | **retain** (non-manipulator) | keep separate from DatasetManipulator |
| ipfs_kit DatasetManager shadows | `ipfs_kit_py/.../DatasetManager` (3 copies) | **retain** kit-local until mismatch policy | not package authority; duplicate definition finding |
| Accelerate native dataset tools | `ipfs_accelerate_py/.../native_dataset_tools.py` | **retain** as adapter | must bind selected package revision |
| Swissknife dataset descriptors | `/home/barberb/swissknife` | **retain** read-only | external consumer contracts only |
| Hallucinate runtime datasets copy | `/home/barberb/hallucinate_app/ipfs_datasets_py` | **record** only | never selected authority for 211-AI analysis |

## 4. Symbol ownership for dataset manipulator surfaces

| Symbol | Kind | Current path | Decision | Owner |
| --- | --- | --- | --- | --- |
| `DatasetLoader` | class | `ipfs_datasets_py/.../core_operations/dataset_loader.py` | **retain** | ipfs_datasets_py core_operations |
| `DatasetSaver` | class | `ipfs_datasets_py/.../core_operations/dataset_saver.py` | **retain** | ipfs_datasets_py core_operations |
| `DatasetConverter` | class | `ipfs_datasets_py/.../core_operations/dataset_converter.py` | **retain** | ipfs_datasets_py core_operations |
| `DataProcessor` | class | `ipfs_datasets_py/.../core_operations/data_processor.py` | **retain** | ipfs_datasets_py core_operations |
| `DatasetManipulator` | class | *(missing)* | **create** | ipfs_datasets_py core_operations (planned) |
| `DatasetManager` | class | `ipfs_datasets_py/.../dataset_manager.py` | **deprecate** after thin wrap | must not remain semantic authority |
| `DatasetManager` | class | `ipfs_kit_py/.../ai_ml_integration.py` | **retain** kit-local | kit shadow; not datasets authority |
| `DatasetManager` | class | `ipfs_kit_py/.../mcp/ai/dataset_manager.py` | **retain** kit-local | kit shadow; duplicate definition |
| `DatasetManager` | class | `ipfs_kit_py/.../mcp/ai/dataset_management/manager.py` | **retain** kit-local | kit shadow; duplicate definition |
| `generate_clusters` | async method | `ipfs_datasets_py/ipfs_datasets.py` (2 definitions) | **deprecate** | duplicate/shadowed monolith surface |
| `load_dataset` | function | MCP + kit + accelerate surfaces | **retain** adapters | thin wrappers over package authority |
| `process_dataset` | function | MCP tools | **repair** | stop mock-success; delegate to manipulator |
| `save_dataset` | function | MCP tools | **repair** | stop mock identity; delegate to saver |
| `convert_dataset_format` | function | MCP tools | **repair** | stop mock conversion; delegate to converter |

## 5. Frozen drift findings (ownership of defects)

These findings are inventory evidence for later repair goals. Categories required
by acceptance: **mock-success**, **nondeterministic** identity, **duplicate
definition**, **missing import**, **weak-test**.

| Finding | Category | Severity | Symbol | Path | Status |
| --- | --- | --- | --- | --- | --- |
| `DSCON-DRIFT-001` | mock-success | high | `ManagedDataset.save_async / ManagedDataset.save` | `ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py` | open |
| `DSCON-DRIFT-002` | mock-success | high | `DatasetManager.get_dataset` | `ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py` | open |
| `DSCON-DRIFT-003` | mock-success | high | `process_dataset` | `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/process_dataset.py` | open |
| `DSCON-DRIFT-004` | mock-success | high | `convert_dataset_format` | `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/convert_dataset_format.py` | open |
| `DSCON-DRIFT-005` | mock-success | medium | `save_dataset` | `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/save_dataset.py` | open |
| `DSCON-DRIFT-006` | nondeterministic-identity | medium | `save_dataset mock dataset_id` | `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/save_dataset.py` | open |
| `DSCON-DRIFT-007` | nondeterministic-identity | medium | `dataset serialization / processors` | `ipfs_datasets_py/ipfs_datasets_py/processors/serialization/dataset_serialization.py` | open |
| `DSCON-DRIFT-008` | duplicate-definition | high | `DatasetManager` | `multi` | open |
| `DSCON-DRIFT-009` | missing-import | high | `DatasetManipulator` | `ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py` | open |
| `DSCON-DRIFT-010` | missing-import | medium | `core_operations package surface` | `ipfs_datasets_py/ipfs_datasets_py/core_operations/` | open |
| `DSCON-DRIFT-011` | weak-test | medium | `dataset tools unit tests` | `ipfs_datasets_py/tests/mcp/unit/test_dataset_tools.py` | open |
| `DSCON-DRIFT-012` | weak-test | medium | `DatasetManager gherkin stubs` | `ipfs_datasets_py/tests/unit/test_stubs_from_gherkin/test_dataset_manager.py` | open |
| `DSCON-DRIFT-013` | revision-mismatch-risk | high | `package authority vs Hallucinate vs home checkout` | `external` | open |
| `DSCON-DRIFT-014` | duplicate-definition | high | `generate_clusters` | `ipfs_datasets_py/ipfs_datasets_py/ipfs_datasets.py` | open |

## 6. Authority selection rules (fail closed)

1. Path + Git commit/tree must be verified before a root is authoritative.
2. Documentation pins (`df11f08f`, `8dc4f93e`, `6672d6924`) are expectations;
   live status must be `matches_expected`, `changed`, or `absent` — never
   silently assumed.
3. Selected package authority is the 211-AI `ipfs_datasets_py` gitlink only.
4. Cross-revision contract comparison without a revision-mismatch label is
   forbidden.
5. Missing or dirty selected roots produce **Blocker** records; analysis may
   continue bootstrap implementation but must not claim whole-repository
   exhaustion or safety.
6. Unresolved authority **fail closed**.

## 7. Blockers

- No hard authority blockers. Exhaustion claims still require clean Swissknife and complete recursive manifests (later goals).

## 8. Acceptance coverage

| Criterion | Covered by |
| --- | --- |
| Clean commit/tree for selected roots and direct gitlinks | `source-roots.json` superproject + direct_gitlinks |
| Recursive mirror cycles without rescan | `source-roots.json` mirror_cycles (`rescan: false`) |
| Swissknife `df11f08f` or explicit changed/absent | `source-roots.json` swissknife.status |
| Hallucinate `8dc4f93e` + package authority | `source-roots.json` hallucinate_datasets + package_authority |
| mock-success / nondeterministic / duplicate / missing import / weak-test | `datasets-manipulator-drift.json` findings |
| Unresolved authority fails closed | `source-roots.json` fail_closed + blockers |
| objective validation repair | DSCON-062 executable validation contract and pinned-object evidence probes |

## 9. Objective validation repair

DSCON-062 closes the synthetic **objective validation repair** gate by running
`python scripts/contract_analysis/audit_scope.py --check`. The command validates all four
authorized artifacts, rehashes pinned commits and trees for the selected
authority, resolves every documented gitlink from its pinned parent tree, and
reproduces each required drift category from blobs in those verified revisions.
Its checked-in validation contract enumerates those proof obligations exactly;
exit code 0 is the completion signal, and undeclared proof fields fail closed.
Unselected external comparison roots retain their freeze-time path/commit/tree
evidence; if an isolated validation worker lacks those ambient checkouts, strict
availability and freshness verification is deferred to `--check-current`.
Documentation paths are never promoted to package authority.

Validation: `python scripts/contract_analysis/audit_scope.py --check`
