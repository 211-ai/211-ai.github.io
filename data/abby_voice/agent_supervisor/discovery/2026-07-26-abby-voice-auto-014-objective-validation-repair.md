# ABBY-VOICE-AUTO-014 Objective Validation Repair

Date: 2026-07-26
Goal id: `ABBY-VOICE-G015`
Task id: `ABBY-VOICE-AUTO-014`
Status: complete

## Scope and evidence

The completed boundary adds canonical `voice.tts`, `voice.asr`, and
`voice.audio-validate` execution to the existing P2P worker without
duplicating provider retry behavior or storing audio in DuckDB.

- `ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py` strictly
  parses the G014 typed job payload and emits the exact
  `VoiceJobResult.from_job(...).to_payload()` shape.
- TTS output is atomically persisted outside the queue, rehashed, and exposed
  with a valid raw CIDv1 `ipfs://` URI. ASR verifies its input descriptor
  before provider execution.
- Runtime STT transcript identity is retained only as a privacy-safe digest in
  the provider receipt; dataset ASR lineage uses the canonical artifact
  digest. Raw audio and private transcript text never enter the task result.
- `p2p_tasks/task_types.py`, `worker.py`, and `service.py` share the canonical
  alias and capability boundary. The router uses the current async backend
  manager contract and independent TTS/STT device controls.
- `ipfs_accelerate_py/test/test_voice_job_worker.py` covers typed round trips,
  offline provider doubles, artifact integrity and limits, SSRF and traversal
  rejection, capability parity, backend compatibility, and device isolation.

The durable accelerator commits are `fab1be76` for the worker/router
implementation and `017ca416` for the canonical result and artifact repair.
The G014 contracts used by the executor are on accelerator ancestry at
`24c34d24`; the datasets bridge is on datasets ancestry at `5ccfe1da`.

## Validation receipt

Executed from the `ipfs_accelerate_py` submodule:

```text
python -m pytest -q test/test_voice_job_worker.py test/test_voice_router_contracts.py test/test_abby_voice_providers.py test/test_voice_job_contracts.py
```

Result: **PASS — 115 passed in 3.13s on 2026-07-26.**

The datasets-side bridge gate also passed independently:

```text
python -m pytest -q tests/unit/ml/test_voice_job_bridge.py
```

Result: **PASS — 9 passed.**

Selected Ruff checks, `compileall`, and `git diff --check` were clean.

## Objective boundary

No smaller child goal is needed. G015 owns executable voice handlers and
routing correctness. G016 remains responsible for queue recovery, resource
admission, and provider batching; G017 remains responsible for reconciling
quality receipts into the dataset.
