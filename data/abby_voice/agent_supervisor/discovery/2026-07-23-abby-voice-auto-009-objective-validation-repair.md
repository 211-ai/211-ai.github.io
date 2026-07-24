# ABBY-VOICE-AUTO-009 Objective Validation Repair

Date: 2026-07-23
Goal id: `ABBY-VOICE-G006`
Task id: `ABBY-VOICE-AUTO-009`
Goal title: Produce a safe Hugging Face bucket and dataset migration plan
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P1
Track: voice-data
Parents: `ABBY-VOICE-G004`, `ABBY-VOICE-G005`
Graph depth: 3
Bundle: `abby-voice/huggingface-migration`
Work scope: `objective_validation_repair`
Source gap fingerprint: `a78d6dd48ff4daf6276d57dcc1c2372b5fe30c2d`

## Finding

The source objective scan reported the synthetic missing evidence term
`objective validation repair`. It also attributed bucket inventory, canonical
prefix, Dataset Viewer, `data_files`, `configs`, `splits`, and migration
operations to unrelated JSON, batch, and review artifacts through AST-token
coincidence. Those files do not define or assert the G006 safety policy and
are not accepted as evidence.

This receipt repairs the evidence mapping without reading or changing remote
Hugging Face state. The machine-readable plan, Dataset Card template, focused
offline test, and objective heap acceptance gate are authoritative.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| Bucket inventory summary | `inventory_summary`, known source prefixes, and the read-only receipt schema in `data/abby_voice/huggingface/migration-plan.json`; inventory assertions in `tests/voice/test_abby_voice_hf_migration.py` | Remote counts, revisions, byte totals, and costs remain explicitly unknown until a human-approved `list_bucket_tree` snapshot. Local manifest counts are labeled local evidence and never presented as remote facts. |
| Proposed canonical prefix layout | `canonical_prefix_layout` in `data/abby_voice/huggingface/migration-plan.json`; layout and isolation sections in `docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md` and `data/abby_voice/huggingface/README.template.md` | Raw artifacts are date/run scoped; curated release/config/split paths are immutable and separate; indexes, manifests, batch wrappers, and run output cannot enter a config directory. |
| Hugging Face Dataset YAML with separate configs and splits | `dataset_yaml.configs[].data_files` in the JSON plan and YAML front matter in `data/abby_voice/huggingface/README.template.md` | Exactly five named configs have schema-specific Parquet paths. Paths are unique, split-labeled, and contain no heterogeneous metadata or batch files. |
| Dry-run copy/upload plan | `dry_run_migration.steps` for `list_bucket_tree`, local builder, `upload_hf_abby_tts_dataset`, and `sync_bucket`; dry-run procedure in the migration document | Staging produces a local manifest only. No step enables upload, and every proposed copy is approval-gated with source and destination checksums. |
| Delete plan and rollback | `dry_run_migration.delete_plan` and `rollback` in the JSON plan; safety and rollback sections in the README/document | Delete, move, rewrite, overwrite, and force-upload operations are prohibited. Rollback selects a previous immutable release and retains all source/candidate objects. |
| Checksums, counts, and costs | `local_build_evidence` and `checksums_counts_costs` in the JSON plan; inventory/cost sections in the migration document | Local builder counts and digests are reproducible. Remote counts/costs are null until inventory, with a declared cost formula and release-receipt fields. |
| Dataset Viewer validation procedure | `dataset_viewer_validation` in the JSON plan; preflight and post-publication procedure in `docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md` and the README template | Local schema/split/checksum/reference smoke loads precede approval; post-upload Viewer config/split/row-count checks use an immutable revision and retained response digest. |
| ABBY-VOICE-G006 completion receipt | This receipt, the G006 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`, and `tests/voice/test_abby_voice_hf_migration.py` | Each G006 claim resolves to the defining plan/template and a focused offline assertion. This is evidence repair, not a claim that remote publication occurred. |

## Acceptance assertions

The focused suite establishes all of the following:

1. the plan is deterministic, review-only, and explicitly prohibits remote
   writes, moves, rewrites, uploads without approval, and deletes;
2. both source interfaces (`Publicus/abby-voice` bucket and
   `Publicus/211-abby-tts` dataset) and their known mutable/legacy prefixes are
   named;
3. five independent Parquet configs and their `data_files` split mappings are
   unique and isolated from manifests, indexes, batch wrappers, and run output;
4. local input counts, quarantine/warning counts, source SHA-256, and builder
   manifest SHA-256 are recorded while remote counts and costs remain null;
5. the dry-run vocabulary explicitly covers `list_bucket_tree`,
   `upload_hf_abby_tts_dataset`, `sync_bucket`, copy/upload review, and an
   empty prohibited delete plan;
6. Dataset Viewer validation checks fixed schemas, Parquet readability, split
   isolation, references, checksums, and signed immutable revisions; and
7. rollback is release selection, never destructive source cleanup.

All focused assertions are local-only, use no credentials, make no network
call, and do not mutate a remote bucket or dataset.

## Validation receipt

Focused command:

```text
python -m pytest -q tests/voice/test_abby_voice_hf_migration.py
```

Result on 2026-07-23: **passed — 4 passed**.

Required task command:

```text
python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check
test -f data/abby_voice/huggingface/migration-plan.json
```

Result on 2026-07-23: **passed**. The offline builder reported 13,809 input
rows, 13,779 accepted responses, 13,779 provenance rows, 30 quarantined rows,
and 13,779 missing-audio warnings. The warning is expected for this checked-in
text manifest under the permissive local policy; it is not a remote inventory.

## Supervisor and child-goal alignment

The heap remains aligned with the supervisor-fed task identity:

- task `ABBY-VOICE-AUTO-009`, goal `ABBY-VOICE-G006`, bundle
  `abby-voice/huggingface-migration`, P1, and `voice-data`;
- parents G004/G005 and graph depth 3;
- conflict policy: plan-only, no remote writes/moves/deletes;
- outputs: this receipt, the objective heap, the migration plan, and the
  Dataset Card template; and
- focused validation: `tests/voice/test_abby_voice_hf_migration.py` plus the
  required offline builder check.

No supervisor-generated todo/vector metadata was manually completed or
rewritten. The implementation daemon owns backlog status regeneration after
merge. No smaller child goal is required: G006 owns the migration plan and
safety gate, G011 owns complete curated materialization, and G009 owns
evaluation content.
