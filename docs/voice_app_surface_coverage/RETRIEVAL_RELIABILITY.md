# Retrieval Reliability (VAS-019)

Program: `voice-app-surface-coverage-v1`  
Generated: `2026-08-05T18:14:55.667364+00:00`

## Method

Symbolic keyword router over P0 variant lattices (`symbolic_keyword_router_v1`).
Authority remains catalog + exposure gates; this measures surface reachability of paraphrases.

## Thresholds

- P0 top-1 ≥ **0.75**
- P0 top-3 ≥ **0.90**

## Latest receipt

See `data/voice_app_surface_coverage/reports/retrieval-reliability.json`.

```bash
python scripts/voice_app_surface_coverage/eval_variant_retrieval.py --check
```
