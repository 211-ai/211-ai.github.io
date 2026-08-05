# Variant lattice doctrine (v2)

Program: `voice-app-surface-full-coverage-v2`

## Floors

| Tier | Unique user texts / surface |
| --- | ---: |
| P0 | 500 |
| P1 | 150 |
| P2 | 80 |

## Axes

paraphrase, dialect (polite forms), slot, noise, multiturn, stt_partial, stt_drop, stt_soft, negative, pad.

## Layout

```text
data/voice_app_surface_full_coverage/variants/
  schema.json
  p0/<surface_id>.jsonl
  p1/<surface_id>.jsonl
  p2/<surface_id>.jsonl  # staff_only / never_voice open attempts (negative)
```

## Ban list

No URLs, file paths, import/exec smuggling in `user_text`.

## Tooling

```bash
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --write
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check --tier P0
```
