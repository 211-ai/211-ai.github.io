# Abby Voice Router Agent-Supervisor Runbook

## Outcome

The objective heap at
`docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` is intended to drive
autonomous, bundle-local implementation across `ipfs_accelerate_py`,
`ipfs_datasets_py`, and the wallet integration.

The target flow is:

```text
audio
  -> STT provider/fallback
  -> transcript
  -> 211 GraphRAG evidence + response-frame retrieval
  -> grounded slot binding + spoken-text normalization
  -> TTS provider/fallback
  -> audio + transcript + evidence/template/provider provenance
```

GraphRAG templates are response plans. They must never supply a phone number,
address, hours, eligibility rule, or other changing fact unless that value is
bound from current cited evidence.

## Why the data work is separate

`Publicus/abby-voice` is a mutable storage bucket, not a Dataset Viewer dataset.
Its public page currently reports 35,542 objects below `runs/`, alongside
temporary, smoke-test, task, and batch prefixes. It is appropriate as a raw
artifact store, but not as the canonical training/runtime table.

`Publicus/211-abby-tts` is the dataset repository currently consumed by the
wallet. Dataset Viewer can preview only a partial shape and reports:

- preview available, but viewer/search/filter/statistics unavailable;
- a cast failure caused by mixing response rows with query indexes, runtime
  manifests, summaries, and provenance documents;
- a nested `byId` index object being treated as a row;
- incompatible 34-column response records and 12-column aggregate/index
  records in one default configuration.

The migration goals therefore create separate, schema-stable configurations:

- `responses`: one normalized utterance/response row per stable response ID;
- `templates`: intents, response frames, reusable edges, and allowed slot kinds;
- `audio`: one asset row per content hash with audio metadata and consent/license
  fields;
- `provenance`: source manifests, CIDs, transformations, and validation receipts;
- `evaluation`: public/synthetic voice turns and expected safety/grounding
  outcomes.

Large binary audio may remain in the bucket or dataset assets, but rows must
refer to it by stable content hash and URL. Runtime indexes and aggregate
manifests belong in named metadata paths or generated artifacts, not in row
files matched by a dataset config.

## Safety boundaries for autonomous lanes

- Do not upload, move, overwrite, or delete Hugging Face content.
- Do not use production API keys or paid endpoints in tests.
- Do not include private caller audio, secrets, wallet records, or PII in
  fixtures.
- Use injected/fake transports for remote TTS and STT provider tests.
- Preserve `text_to_speech(...)` and `speech_to_text(...)` compatibility.
- Keep `ipfs_datasets_py` optional at `voice_router` import time.
- Require current cited evidence for factual slots.
- Preserve browser SpeechRecognition, local WebGPU audio, and browser speech
  fallbacks during wallet adoption.

## Generate objective tasks

From the repository root:

```bash
PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objective_daemon \
  --repo-root . \
  --objective-path docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md \
  --todo-path data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md \
  --discovery-dir data/abby_voice/agent_supervisor/discovery \
  --bundle-dir data/abby_voice/agent_supervisor/objective_bundles \
  --dataset-dir data/abby_voice/agent_supervisor/objective_datasets \
  --graph-path data/abby_voice/agent_supervisor/objective_graph.json \
  --task-prefix ABBY-VOICE-AUTO- \
  --objective-summary-prefix "Implement Abby voice objective" \
  --discovery-output-path data/abby_voice/agent_supervisor/discovery \
  --plan-evaluation-path data/abby_voice/agent_supervisor/plan_evaluations.json \
  --analysis-escalation-path data/abby_voice/agent_supervisor/analysis_escalation.json \
  --objective-generation-path data/abby_voice/agent_supervisor/objective_generation.json \
  --max-findings 30 \
  --surplus-findings-per-goal 1 \
  --no-reconcile-goal-completion
```

`--no-reconcile-goal-completion` is recommended for the first scan because the
heap describes a new cross-submodule program and should not be closed by weak
textual similarity to existing code.

## Review the generated plan

Inspect:

```text
data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
data/abby_voice/agent_supervisor/objective_graph.json
data/abby_voice/agent_supervisor/objective_bundles/index.json
data/abby_voice/agent_supervisor/objective_bundles/todo_vector_index.json
data/abby_voice/agent_supervisor/discovery/
```

Plan implementation lanes without starting them:

```bash
ipfs-accelerate-agent-bundle-supervisor \
  --repo-root . \
  --bundle-index-path data/abby_voice/agent_supervisor/objective_bundles/index.json \
  --state-root data/abby_voice/agent_supervisor/lane_state \
  --worktree-root /tmp/abby-voice-agent-worktrees \
  --log-dir data/abby_voice/agent_supervisor/logs \
  --manifest-path data/abby_voice/agent_supervisor/lane-manifest.json \
  --task-prefix ABBY-VOICE-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --max-lanes 4 \
  --no-implement
```

## Start autonomous implementation

Only after reviewing the todo board, conflict surfaces, validation commands, and
the Hugging Face no-write constraints:

```bash
ipfs-accelerate-agent-bundle-supervisor \
  --repo-root . \
  --bundle-index-path data/abby_voice/agent_supervisor/objective_bundles/index.json \
  --state-root data/abby_voice/agent_supervisor/lane_state \
  --worktree-root /tmp/abby-voice-agent-worktrees \
  --log-dir data/abby_voice/agent_supervisor/logs \
  --manifest-path data/abby_voice/agent_supervisor/lane-manifest.json \
  --task-prefix ABBY-VOICE-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 3 \
  --max-lanes 4 \
  --implement \
  --start
```

The data, provider-routing, GraphRAG, evaluation, and wallet bundles use separate
parallel lanes. Parent-goal dependencies and declared conflict surfaces should
keep shared `voice_router.py` integration work behind the focused contracts and
tests.
