# Abby Voice Publicus Regeneration Service

This runbook covers the persistent, resumable generation of the canonical Abby
audio queue through `Publicus/IndexTTS-2-Demo`.

## Retry Contract

`scripts/run_indextts_batch_generation.py` uses these process results:

| Exit | Meaning | Service action |
| --- | --- | --- |
| `0` | Backlog complete | Stop successfully |
| `75` | Hugging Face quota or rate limit | Read `state.retryAfter`, wait, then resume the same offset |
| `124` | Configured runtime deadline | Exit to the service manager |
| other nonzero | Batch, process, endpoint, or local-system failure | Exit to the service manager |

The batch state stores the provider's relative `retryAfter` hint together with
`updatedAt`. The quota launcher anchors an `HH:MM:SS` hint to `updatedAt`, so a
machine reboot does not start the full wait again. Numeric seconds, ISO-8601
timestamps, and HTTP `Retry-After` dates are also accepted. A missing or
malformed hint uses a five-minute fallback.

The launcher only retries exit `75` internally. It writes an observable status
receipt and returns every ordinary failure immediately. The service template
allows at most three rapid ordinary restarts in thirty minutes; it therefore
cannot hide a persistent code, disk, credential, or endpoint-contract failure
behind an unbounded restart loop.

## Files

- Unit template:
  `ops/systemd/user/abby-voice-publicus-regeneration.service`
- Batch checkpoint:
  `tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-batch-state.json`
- Quota wait receipt:
  `tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-quota-retry-status.json`
- Batch manifests:
  `tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-batches/`
- Per-batch live progress:
  `tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-progress/`

## Install Or Upgrade

Do not replace a healthy generator in the middle of a remote batch. Wait for a
completed batch checkpoint or a planned maintenance window. The repository
template assumes the checkout is `%h/211-AI/211-AI`; edit a copied unit if the
deployment checkout differs.

Keep Hugging Face credentials out of the unit. If they are not already
available through the normal credential chain, put them in the optional
operator-only environment file:

```bash
install -d -m 0700 "$HOME/.config/211-ai"
${EDITOR:-vi} "$HOME/.config/211-ai/abby-voice-publicus-regeneration.env"
chmod 0600 "$HOME/.config/211-ai/abby-voice-publicus-regeneration.env"
```

Install the reviewed template and activate it:

```bash
install -d -m 0755 "$HOME/.config/systemd/user"
install -m 0644 \
  ops/systemd/user/abby-voice-publicus-regeneration.service \
  "$HOME/.config/systemd/user/abby-voice-publicus-regeneration.service"
systemctl --user daemon-reload
systemctl --user enable --now abby-voice-publicus-regeneration.service
```

The checked-in template uses the Publicus Space, `remote-batch-size=4`, one
worker, canonical local hash filenames, and no direct bucket upload. Publish an
immutable Hugging Face dataset snapshot only after generation and quality
acceptance.

## Dedicated GPU Handoff

The checked-in service requires `Publicus/IndexTTS-2-Demo` to be running on one
dedicated `l40sx1`. Its `ExecCondition` verifies current hardware, requested
hardware, domain readiness, and the reviewed Space commit before any queue
process starts. It can wake a sleeping Space only when the requested hardware
still matches. A ZeroGPU or alternate-Space fallback is not a capacity escape
and is intentionally rejected.

After changing the Space source, run its focused tests, push the reviewed
commit, disable Dev Mode for production, and update both
`ABBY_TTS_EXPECTED_REVISION` and `--expected-revision` in the unit template.
Never update the pin merely to clear the gate. Wait for the runtime API to
report that exact revision on the expected hardware, then probe the contract:

```bash
python3 scripts/precompute_indextts_responses.py \
  --space-url https://publicus-indextts-2-demo.hf.space \
  --print-indextts-contract \
  --require-upload-capable-batch
```

Then run a bounded canary and review its transcripts and audio before resuming
the service. Because the URL remains unchanged, the existing checkpoint
identity and offset remain compatible.

The Space has a one-hour idle sleep setting. A completed queue is detected from
the checkpoint before the hardware API is queried, so an enabled service does
not wake paid hardware after completion.

For a genuinely new dedicated URL, change both the launcher's `--state` and the
child runner's `--state` to the same new checkpoint filename, and change both
the environment and child `--space-url`. The endpoint URL is part of
`runIdentity`, so reusing the old state intentionally fails closed. A new state
starts at offset zero; with the same accepted voice contract and without
`--force`, content-addressed outputs already present locally are reused. If the
voice or post-processing contract changes, use a separate output root and
promote it only after the full acceptance gate rather than mixing voices.

## Observe

```bash
systemctl --user status abby-voice-publicus-regeneration.service
journalctl --user -u abby-voice-publicus-regeneration.service -n 100
python3 scripts/wait_for_hf_space_hardware.py \
  --space-repo-id Publicus/IndexTTS-2-Demo \
  --expected-hardware l40sx1 \
  --expected-revision <reviewed-full-space-sha> \
  --timeout-seconds 1
jq . tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-batch-state.json
jq . tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-quota-retry-status.json
```

During a quota wait, the receipt has `phase: "waiting_for_quota"` plus
`retryAfter`, `retryAt`, `delaySeconds`, and whether the fallback was used. The
service remains active while sleeping, so systemd does not spend its ordinary
failure restart budget.

## Recovery

For a quota wait, do not restart the service merely to poll the provider. Verify
`retryAt` and let the launcher resume. A manual restart recomputes the remaining
delay from the checkpoint's `updatedAt`.

For an ordinary failure, inspect the journal and receipt. Repair credentials,
disk capacity, local files, or the endpoint contract before clearing the bounded
start limit:

```bash
systemctl --user reset-failed abby-voice-publicus-regeneration.service
systemctl --user start abby-voice-publicus-regeneration.service
```

Exit `75` is listed in `RestartPreventExitStatus` as a final safety net. The
template configures unlimited quota retries inside the launcher, so it should
not normally reach systemd. If an operator later sets a finite quota retry
budget, exhaustion stops for inspection instead of falling back to a blind
one-minute restart loop.

## Rented-Space Monitor

`scripts/monitor_abby_tts_space_and_run.py` applies the same policy to phase
checkpoints. It uses `retryAfter` even when the intermediate Python wrappers
translate the original exit `75` into exit `1`. These controls are available:

```text
--quota-retry-fallback-seconds 300
--quota-retry-minimum-seconds 60
--quota-retry-grace-seconds 15
--max-consecutive-wrapper-failures 3
```

Quota waits do not consume the ordinary wrapper-failure budget. Checkpoint
progress resets that budget; three consecutive non-quota exits without durable
progress stop for inspection. Local missing-file and permission failures remain
immediate terminal manual-repair conditions.
