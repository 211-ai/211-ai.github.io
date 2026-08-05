# Voice Action DAG × Abby — Production Enablement Checklist

Program: `voice-action-dag-abby-v1`  
Board namespace: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G150`  
Task: `VOICE-ACTION-031`  
Companion runbook: `docs/planning/VOICE_ACTION_DAG_ABBY_AGENT_SUPERVISOR_RUNBOOK.md`

This checklist is the **operator gate** for enabling Abby voice-action product
behavior in a real environment. Autonomous supervisor workers never complete
or self-approve these rows. Mark each item only with human evidence (command
output, receipt IDs, deployment revision, or signed review).

Default posture: **both flags off, fake transports only, no live credentials.**

---

## 0. Identity of the enablement attempt

| Field | Value |
| --- | --- |
| Environment (dev / staging / prod canary / prod) | |
| Deployment revision / image digests | |
| Operator(s) | |
| Date (UTC) | |
| Catalog id + digest | |
| Binding id (if execute enabled) | |
| Rollback owner on-call | |

---

## 1. Plan integrity and protected namespace

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 1.1 | `python scripts/validate_voice_action_dag_abby_plan.py` exits 0 | | |
| 1.2 | Protected plan paths unchanged by workers (integration plan, objectives, todo, supervisor.json, validator) | | |
| 1.3 | Runtime policy still denies network, credentials, publication, live telephony/SMS, HF publish by default | | |
| 1.4 | Supervisor refill remains sole-owned by `voice-action-grok-0` (no transfer of refill authority) | | |

---

## 2. Offline proofs (fake transports only)

All of the following must pass **without** network, live carriers, or production
secrets. Prefer a clean private validation environment.

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 2.1 | Doctrine invariants: `python -m pytest -q tests/voice_action_dag/test_doctrine_invariants.py` | | |
| 2.2 | Handoff truthfulness: `python -m pytest -q ipfs_accelerate_py/test/test_action_human_handoff_adapter.py` | | |
| 2.3 | Deployment binding: `python -m pytest -q ipfs_accelerate_py/test/test_action_deployment_binding.py` (confirm cannot override mismatch) | | |
| 2.4 | Offline pilot matrix (12 routes, fake adapters): `python -m pytest -q tests/e2e/voice_action_dag/test_abby_pilot_matrix.py` | | |
| 2.5 | Adversarial suite green when present (`tests/e2e/voice_action_dag/test_abby_adversarial.py`) | | |
| 2.6 | Wallet dual-gate: `python -m pytest -q wallet_interface/tests/test_ai_router_voice_action.py` | | |
| 2.7 | Unified router adapter tests: `python -m pytest -q wallet_interface/tests/test_voice_router_adapter.py` | | |
| 2.8 | Matrix receipt shows network denied and fake-only adapters | | |

---

## 3. Feature flags (documented defaults)

### 3.1 `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`

| Property | Expected |
| --- | --- |
| Source | `wallet_interface/helpers/_voice_router_adapter.py` (`UNIFIED_VOICE_ROUTER_FLAG`) |
| Default | off (`0` / unset) |
| On | Wallet delegates to shared `process_voice_turn` and emits canonical receipt |
| Off / rollback | Legacy proxy path; browser SpeechRecognition / WebGPU / speech fallbacks remain |

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 3.1.1 | Deployed config has flag **off** before canary | | |
| 3.1.2 | Offline router + UI gates green (see runbook §8 / `ABBY_VOICE_ROUTER_ROLLOUT.md`) | | |
| 3.1.3 | Canary enable (`=1`) on a single proxy slice | | |
| 3.1.4 | Successful receipt: non-empty `response_text` / `spoken_text`, stage traces, provenance | | |
| 3.1.5 | Degraded or text-only receipt recorded with explicit `fallback_reasons` | | |
| 3.1.6 | Flag-off rollback tested (`=0` + process reload) | | |
| 3.1.7 | Ordinary logs/metrics do not retain raw input audio | | |

### 3.2 `WALLET_VOICE_ACTION_EXECUTE_ENABLED`

| Property | Expected |
| --- | --- |
| Source | `wallet_interface/helpers/_voice_action_surface.py` (`VOICE_ACTION_EXECUTE_FLAG`) |
| Default | off (`0` / unset) |
| On | Allows adapter execute **only with** explicit per-request confirm |
| Off / kill switch | Proposals + confirm decisions remain; adapters never run |

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 3.2.1 | Deployed config has execute flag **off** while proving proposal/confirm UX | | |
| 3.2.2 | Confirm without execute flag produces **no** adapter receipt / side effect | | |
| 3.2.3 | Execute flag without confirm produces **no** side effect | | |
| 3.2.4 | Both gates present → expected read/execute path under pilot policy | | |
| 3.2.5 | Production path also passes signed deployment binding (catalog digest + adapter identities) | | |
| 3.2.6 | Binding mismatch denies execute even when `confirmed=true` | | |
| 3.2.7 | Kill switch: set `WALLET_VOICE_ACTION_EXECUTE_ENABLED=0` and reload; new mutations stop | | |

### 3.3 Recommended enablement order

| Step | Flag state | Goal |
| --- | --- | --- |
| A | both off | Ship code; legacy voice healthy |
| B | unified on, execute off | Canary unified receipts |
| C | unified on, execute off | Prove proposal + confirm without side effects |
| D | both on (canary) | Dual-gated execute for one slice |
| E | expand only after metrics/SLOs hold | Broader enablement |

---

## 4. Fake vs live transports

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 4.1 | CI and supervisor workers still require fake adapters (`require_fake_adapters: true`) | | |
| 4.2 | No autonomous task enables live telephony, SMS, HF publish, or credentials | | |
| 4.3 | Product live transports (if any) are human-configured outside worker env | | |
| 4.4 | Live PSTN / SMS / paid endpoints documented with owner and kill switch | | |
| 4.5 | Fake telephony paths may yield `unknown` without claiming transfer success | | |
| 4.6 | Exactly-once delivery is **not** claimed for external providers | | |

---

## 5. Handoff truthfulness

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 5.1 | Handoff request creation yields `accepted`, never silent `succeeded` | | |
| 5.2 | `allows_spoken_success` / spoken success frames only when status is `succeeded` **and** `provider_confirmation` is present | | |
| 5.3 | `accepted` / `started` / `unknown` / `failed` never play transfer-complete wording | | |
| 5.4 | Content-plane `live_agent` speech remains advisory without authority receipt | | |
| 5.5 | Safety overlay may force escalate/handoff **request** without tool smuggling | | |
| 5.6 | UI/API never labels transfer complete on metadata-only escalation | | |
| 5.7 | Privacy: handoff receipts redact raw summaries by default | | |

---

## 6. Parallel lane ownership (ops readiness)

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 6.1 | Four shard lanes present; only `voice-action-grok-0` owns refill and git GC | | |
| 6.2 | Merge target is `agent/voice-action-dag-abby` from pinned base only; FF merges | | |
| 6.3 | Task parallel lanes (wave-00 … wave-06) respected; no cross-lane exclusive-file thrash | | |
| 6.4 | Adapter exclusive owners (app / calendar / messages / service / handoff) unchanged without review | | |
| 6.5 | Docs lane (`wave-06-docs`) owns this checklist + runbook only | | |
| 6.6 | Binding lane owns signed deployment binding; content cannot widen it | | |

---

## 7. Signed deployment binding (required before production execute)

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 7.1 | Binding environment is `production` for production execute | | |
| 7.2 | Signature verifies with operator key (HMAC-SHA256); key not in content plane | | |
| 7.3 | Runtime `catalog_digest` matches binding | | |
| 7.4 | Runtime adapter identity set matches binding rows | | |
| 7.5 | Confirm cannot override digest or identity mismatch | | |
| 7.6 | Expiry / issuer / nonce reviewed for the canary window | | |

Reference: `docs/voice_action_dag/DEPLOYMENT_BINDING.md`.

---

## 8. Canary execute scenarios

Run only after §1–§7 pass and execute flag is canary-enabled.

| # | Scenario | Expected | Pass? | Receipt / ID |
| --- | --- | --- | --- | --- |
| 8.1 | Content-only route (e.g. `repeat_or_restate`) | `no_action`; no adapter invoke | | |
| 8.2 | Tool-adjacent route without confirm | Decision `confirm` / deny; **no** execute | | |
| 8.3 | Read action with confirm + execute flag | Fake or admitted adapter succeeds; spoken outcome matches receipt | | |
| 8.4 | Write action without auth session | Denied / confirm; no mutation | | |
| 8.5 | `live_agent` handoff request | Receipt `accepted`; spoken success **forbidden** | | |
| 8.6 | Handoff with provider confirmation (staging only) | `succeeded` only with confirmation token; then success speech allowed | | |
| 8.7 | Safety escalate | Handoff/overlay path; no unrelated calendar/message write | | |
| 8.8 | Kill switch mid-canary | New executes stop; status/handoff request paths remain safe | | |

---

## 9. Observability and privacy

| # | Check | Pass? | Evidence |
| --- | --- | --- | --- |
| 9.1 | Metrics cover status, stage failures, fallback rate, deny rate, unknown outcomes, p95 latency | | |
| 9.2 | Logs omit raw audio, credentials, secrets, and over-broad handoff summaries | | |
| 9.3 | Receipt IDs retained for incident review without private caller audio | | |
| 9.4 | On-call knows both flag kill switches and supervisor `stop` | | |

---

## 10. Final signoff

Production (or production-canary) execute may proceed only when **all** of the
following are true:

| Gate | Named approver | Date | Pass? |
| --- | --- | --- | --- |
| Offline proofs (§2) | | | |
| Unified router canary + rollback (§3.1) | | | |
| Dual-gate execute proof (§3.2) | | | |
| Transport policy (§4) | | | |
| Handoff truthfulness (§5) | | | |
| Lane ownership / control plane (§6) | | | |
| Signed binding (§7) | | | |
| Canary scenarios (§8) | | | |
| Privacy / observability (§9) | | | |

**Fail closed:** any unchecked required row blocks enablement. Do not treat
green unit tests alone as production authority when live transports or
credentials are involved.

### Kill switches (always available)

```bash
export WALLET_VOICE_ACTION_EXECUTE_ENABLED=0
export WALLET_VOICE_UNIFIED_ROUTER_ENABLED=0
# reload / restart the wallet proxy deployment
```

Supervisor emergency stop:

```bash
python scripts/voice_action_dag/supervisor_control.py stop
```

---

## 11. Document ownership

| Document | Owner |
| --- | --- |
| This checklist | Operations (`wave-06-docs`) |
| Agent supervisor runbook | Operations (`wave-06-docs`) |
| Unified router staged rollout | `docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md` |
| Doctrine / handoff / binding freezes | Architecture and adapter owners as cited in each freeze doc |

Task acceptance (VOICE-ACTION-031): runbook documents
`WALLET_VOICE_UNIFIED_ROUTER_ENABLED`, `WALLET_VOICE_ACTION_EXECUTE_ENABLED`,
fake vs live transports, handoff truthfulness, and parallel lane ownership;
this checklist is the operator execution of that runbook.
