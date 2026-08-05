# Voice × App-Surface Coverage Plan

## Outcome

Examine the **entire 211-AI app surface**, decide which parts are safe and
useful for the **voice / phone system**, expand the **Abby slotted response
DAG** so those surfaces are reachable under a large number of request
variants, and **regenerate precomputed audio** so the content plane covers the
full surface × DAG matrix.

This program is the natural follow-on to `voice-action-dag-abby-v1` (governed
actions exist). It closes the remaining product gap:

```text
many phrasings of a request
  → reliable DAG route / surface selection
  → catalog-bound ActionProposal
  → confirm / auth / handoff (authority plane)
  → app surface or tool adapter
  → Abby library audio for confirm + outcome
```

Companion artifacts:

| Artifact | Path |
| --- | --- |
| Goal heap | `docs/planning/voice_app_surface_coverage.objectives.md` |
| Task board | `docs/planning/voice_app_surface_coverage.todo.md` |
| Launch profile | `docs/planning/voice_app_surface_coverage.supervisor.json` |
| Preflight | `scripts/validate_voice_app_surface_coverage_plan.py` |
| Runbook | `docs/planning/VOICE_APP_SURFACE_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md` |

Preflight:

```bash
python scripts/validate_voice_app_surface_coverage_plan.py
```

## Prerequisites (wave 0)

1. **Sync submodules from origin/main** before parallel work:
   - `ipfs_accelerate_py` → `origin/main`
   - `ipfs_datasets_py` → `origin/main`
2. Record submodule SHAs into a pin receipt under
   `data/voice_app_surface_coverage/baseline/submodule-pins.json`.
3. Create merge target `agent/voice-app-surface-coverage` from the pinned
   monorepo base (default `origin/main` at plan freeze).
4. Re-pin `merge_target_creation.expected_base_commit` if monorepo `origin/main`
   moves after the submodule update.

Autonomous workers must **not** force-push, publish HF audio, or flip product
execute flags. Audio regeneration runs in staged/offline mode unless a
human-gated task explicitly enables live TTS Spaces.

## Starting inventory (known today)

### App surface (wallet UI)

Primary + secondary `RouteId`s (from `wallet_interface/ui` navigation):

| Family | Surfaces |
| --- | --- |
| Client core | `home`, `register`, `check-in`, `calendar`, `messages`, `contacts`, `social-services`, `interactions`, `uploads` (Wallet), `settings` |
| Client secondary | `recipient-access`, `benefits-protection`, `analytics`, `proof-center`, `exports`, `security` |
| Provider / staff | `shelter`, `provider-clients`, `provider-cases`, `provider-messages`, `provider-analytics`, `provider-proofs`, `provider-operations` |
| Ops | `audit` |

Agent tool modules (browser plane):

- `navigationTools`, `checkInTools`, `contactTools`, `serviceDetailTools`,
  `servicePlanTools`, `shelterTools`, `uploadTools`, `exportTools`,
  `recipientAccessTools`, `sharingRuleTools`, `securityTools`,
  `analyticsTools`, `proofTools`, `registrationTools`

Voice action binding today only fully exercises:

- `open_app_surface` (allowlisted surfaces; often demoed with `calendar`)
- `open_wallet_documents` → `uploads`
- calendar / messaging / service / handoff pilot adapters

**Gap:** most surfaces are navigable in the UI tool registry but lack dense
DAG exemplars, variant matrices, refined logical actions, and audio.

### Content plane (Abby DAG)

| Asset | Role | Scale (approx) |
| --- | --- | --- |
| `docs/phone_dialog_generation/slotted_response_dag.json` | Intent → response frames | ~13.6k edges, **12 routes** |
| `slotted_response_action_links.json` | Route → logical action | 12 rows |
| `action_speech_frames.jsonl` | Confirm/outcome text | 10 actions × 4 roles |
| IndexTTS / Whisper manifests | Precomputed audio | Large; incomplete for surface coverage |

Route density is skewed (`live_agent` ~7k edges; tool-adjacent surfaces often
&lt;300). That is insufficient for reliable phone NLU under paraphrase.

### Authority plane (pilot)

Catalog `211ai-pilot-v1` logical actions:

`handoff_live_agent`, `open_app_surface`, `open_wallet_documents`,
`read_calendar`, `create_calendar_reminder`, `read_provider_messages`,
`leave_provider_message`, `open_service_detail`, `schedule_service_callback`,
`escalate_safety`.

Offline e2e pilot matrix is green (`tests/e2e/voice_action_dag/`).

## Architectural rules (non-negotiable)

Inherited from `docs/voice_action_dag/INTEGRATION_DOCTRINE.md`:

1. **Dual plane** — content (DAG/audio) never embeds executables, URLs, argv,
   credentials, or import paths.
2. **Catalog only** — retrieval proposes logical actions already in a reviewed
   catalog.
3. **Fail closed** — reads need confirm; writes need confirm + auth; handoff
   never claims transfer success without a provider receipt.
4. **Surface allowlist** — voice may open only surfaces classified
   `voice_navigable` or `voice_actionable` for the active role/channel.
5. **Fake transports in workers** — no live telephony, SMS, or HF publish from
   autonomous lanes.
6. **Audio is content-addressed** — regenerate offline/staged; Whisper-gate
   before promotion; no ad-hoc request-path TTS for coverage claims.

## Program phases

### Phase A — Submodule sync + control plane

- Pull `ipfs_accelerate_py` / `ipfs_datasets_py` `origin/main`.
- Bootstrap supervisor profile, protected paths, merge target, preflight.
- Freeze doctrine addendum for *surface exposure classes*.

### Phase B — Full app-surface examination

Machine-readable inventory:

```text
data/voice_app_surface_coverage/baseline/
  app-surface-inventory.json     # every RouteId, screen, tool, deep link
  voice-exposure-matrix.json     # amenability class + risk + channel
  surface-capability-map.json    # surface → logical actions / tools
  coverage-gap-matrix.json       # DAG density, audio, adapter, e2e gaps
```

**Exposure classes** (normative for this program):

| Class | Meaning | Example |
| --- | --- | --- |
| `voice_navigable` | Open surface after confirm | home, calendar, messages, services |
| `voice_actionable` | Read/write tool on surface | read_calendar, leave message |
| `voice_read_only` | Speak grounded info; no UI mutation | many grounded_211 answers |
| `phone_handoff` | Live agent / safety only | crisis, complex case |
| `staff_only` | Provider portal; off client phone by default | provider-cases |
| `never_voice` | Too sensitive / destructive for voice | security, raw exports, grant admin |

Workers classify every surface with evidence (code symbol + risk note). Humans
may override class in the matrix before catalog expansion.

### Phase C — Expose amenable surfaces on the action plane

For each `voice_navigable` / `voice_actionable` surface:

1. Ensure catalog descriptor + risk metadata exist.
2. Expand `NAVIGATION_SURFACE_IDS` / app binding aliases as needed.
3. Wire policy predicates (role, channel, auth).
4. Attach offline fake adapters or reuse existing ones.
5. Add deterministic unit tests.

Target: **every client-core surface** is either catalog-bound or explicitly
`never_voice` / `staff_only` with rationale.

### Phase D — Expand the voice DAG for reliability under variants

For each exposed surface/action, author a **variant lattice**:

| Axis | Examples |
| --- | --- |
| Intent paraphrase | “what’s on my calendar”, “any appointments tomorrow”, “show my day” |
| Channel dialect | short SMS-like, long conversational, interrupted |
| Slot fill | with/without date, service name, provider name |
| Multi-turn | clarify → confirm → execute |
| Noise / STT error | partial words, homophones |
| Negative | wrong surface, refusal, cancel |

Deliverables:

- Per-surface blueprints under
  `data/voice_app_surface_coverage/variants/<surface_id>.jsonl`
- Expanded slotted DAG sections (or additive shard manifests) with **minimum
  exemplar floors** per surface (program default: **≥200 unique user
  paraphrases** for P0 client surfaces; **≥50** for P1).
- Rebuild action-link projection for any new routes.
- Retrieval reliability report: offline top-1 / top-3 hit rate over the
  variant lattice (fail closed if below thresholds).

Do **not** bloat `live_agent` further without a quota plan; prefer balancing
under-covered tool-adjacent and navigable surfaces.

### Phase E — Regenerate audio for full surface × DAG coverage

Pipeline (existing tools, orchestrated):

```text
action_speech_frames + surface navigation frames
  → stage_abby_action_audio / IndexTTS precompute
  → Whisper adjudication
  → public/private manifests
  → resolver exact-match offline smoke
```

Coverage claims require:

- confirm / success / deny / fail frames per logical action;
- navigation confirm/outcome frames per P0 surface (or shared templates with
  slot-safe surface labels);
- DAG response frames for high-traffic exemplars (or explicit
  `generate_required` with budget receipt);
- no secret leakage in spoken text;
- offline resolver hits for staged fixtures.

Live HF Space runs are **human-gated** (`VAS-0xx` audio batch tasks).

### Phase F — Prove coverage end-to-end

- Offline matrix: variant → route → proposal → confirm → fake adapter → speak.
- App-surface reachability matrix: every `voice_navigable` surface opened at
  least N ways.
- Adversarial: never_voice surfaces cannot be opened; staff routes denied on
  client channel; injection cannot invent descriptors.
- Enablement checklist + operator runbook update.

## Parallel lane map (summary)

| Wave | Lanes | Owns |
| --- | --- | --- |
| 00 | control, submodule-sync | pins, merge target, preflight |
| 01 | inventory, exposure | surface census, amenability matrix |
| 02 | catalog, policy, adapters | authority expansion |
| 03 | dag-variants (sharded by surface family), retrieval | content density + reliability |
| 04 | speech-frames, audio-stage, audio-validate | text + audio regeneration |
| 05 | e2e, adversarial, ops | proof + enablement |

Four supervisor shards (`task_shard_count: 4`) pick tasks by id modulo shard,
same pattern as `voice-action-dag-abby-v1`.

## Success criteria (program)

1. Submodules pinned to reviewed `origin/main` SHAs with receipt.
2. 100% of `RouteId`s classified in the exposure matrix with evidence.
3. Every `voice_navigable` / `voice_actionable` client surface has:
   - catalog + adapter binding,
   - ≥ floor of DAG paraphrases,
   - confirm/outcome speech frames,
   - offline e2e case green.
4. Audio coverage report shows staged or validated audio for P0 set; remaining
   rows are budgeted `generate_required` with explicit owner.
5. `never_voice` / `staff_only` surfaces are denied under client voice channel
   in adversarial tests.
6. Preflight validator green; merge train stays fast-forward only onto
   `agent/voice-app-surface-coverage`.

## Out of scope (this program)

- Replacing GraphRAG / IndexTTS stack.
- Live production telephony cutover.
- Redesigning provider portal UX.
- Unbounded LLM generation without symbolic floors and digests.
- Weakening dual-gate execute flags.

## Relationship to prior programs

| Program | Relationship |
| --- | --- |
| `voice-action-dag-abby-v1` | Prerequisite action plane; do not fork contracts needlessly |
| Reusable voice-care platform | Compatible; surface coverage is product depth, not platform rewrite |
| Abby TTS precompute pipelines | Reused for Phase E audio regeneration |

## Operator bootstrap (after plan land)

```bash
# 0) Clean tree on monorepo main
git status -sb

# 1) Pull submodules from origin/main (human or VAS-002)
git -C ipfs_accelerate_py fetch origin
git -C ipfs_accelerate_py checkout main
git -C ipfs_accelerate_py pull --ff-only origin main
git -C ipfs_datasets_py fetch origin
git -C ipfs_datasets_py checkout main
git -C ipfs_datasets_py pull --ff-only origin main

# 2) Record pins + update monorepo submodule pointers (human review)
python scripts/voice_app_surface_coverage/record_submodule_pins.py --write

# 3) Preflight
python scripts/validate_voice_app_surface_coverage_plan.py

# 4) Create merge target from pinned base (supervisor control)
# 5) Start 4-shard supervisor with external state root
```

See runbook for flags, fake-transport policy, and audio batch gates.
