# Variant Lattice (VAS-012+)

Program: `voice-app-surface-coverage-v1`

## Purpose

Generate large sets of request paraphrases so phone/voice NLU and the slotted
DAG can reach each exposed surface under many phrasings (e.g. “what is on my
calendar”, “any appointments tomorrow”, “show my day”).

## Schema

See `data/voice_app_surface_coverage/variants/schema.json`.

Each surface file: `data/voice_app_surface_coverage/variants/<surface_id>.jsonl`

## Floors

| Priority | Unique `user_text` |
| --- | ---: |
| P0 | ≥ 200 |
| P1 | ≥ 50 |

## Axes

- `paraphrase` — intent-preserving rewordings
- `slot` — with/without date, service name, etc.
- `noise` — STT-like fragments
- `negative` — wrong surface / cancel / refuse
- `multiturn` — shell lines for confirm→execute

## Generator

```bash
python scripts/voice_app_surface_coverage/build_surface_variant_lattice.py --write --priority P0
python scripts/voice_app_surface_coverage/build_surface_variant_lattice.py --check --priority P0
```

Deterministic templates first; optional LLM fill only behind this schema.
