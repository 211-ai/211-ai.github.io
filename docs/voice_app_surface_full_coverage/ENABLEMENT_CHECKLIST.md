# Enablement checklist — voice-app-surface-full-coverage-v2

| Goal | Evidence artifact | Done when |
| --- | --- | --- |
| G010 Sync submodules | `baseline/submodule-pins.json`, voice-module-probe | pins match origin/main, probe ok |
| G020 Inventory | `baseline/app-surface-inventory.json` | all RouteIds present |
| G030 Exposure | `baseline/voice-exposure-matrix.json` | 100% classified |
| G040 Catalog | `catalog/surface-catalog-delta.json` | descriptors + matrix |
| G050 Bindings | `SURFACE_BINDINGS.md`, binding tests | never_voice deny |
| G060 Variants | `variants/p0..p2`, floor receipts | floors met |
| G070 DAG fold | `reports/dag-fold-receipt.json` | fold applied |
| G080 Retrieval | `reports/retrieval-reliability.json` | meets thresholds |
| G090 Speech | action/surface/dag speech frames | audit_speech_frames OK |
| G100 Audio | `reports/audio-regen-batch.json` | production staged |
| G110 E2E | e2e-surface-matrix / adversarial / dag-sim | green |
| G120 Ops | projection + PROGRAM_SIGNOFF | overall green |

## Product flags (human only)

- `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`
- `WALLET_VOICE_ACTION_EXECUTE_ENABLED`

Workers never flip these.
