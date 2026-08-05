# Voice Exposure Doctrine

Program: `voice-app-surface-coverage-v1`  
Task: `VAS-006`

## Purpose

Classify every 211-AI app surface for voice/phone amenability. The matrix is
**authority** for whether the content plane may propose opening or acting on a
surface under a given channel/role.

## Classes

| Class | Client voice/phone | Meaning |
| --- | --- | --- |
| `voice_navigable` | allow after confirm | Open UI surface only |
| `voice_actionable` | allow after confirm (+auth if write) | Open and/or tool actions |
| `voice_read_only` | speak only (optional later) | No surface mutation |
| `phone_handoff` | handoff path | Live agent / safety |
| `staff_only` | **deny** on client channel | Provider portal |
| `never_voice` | **deny** | Too sensitive/destructive |

## Defaults

- Unknown surface → `never_voice`.
- Security, exports, sharing grants, audit → `never_voice`.
- Provider portal routes → `staff_only`.
- Calendar / messages / wallet / services → `voice_actionable` (pilot).
- Remaining client core → `voice_navigable`.

## Non-negotiables

1. Content never embeds executables or locators.
2. Catalog logical actions only.
3. Confidence never upgrades authority.
4. `staff_only` / `never_voice` fail closed on client voice/phone.
5. Human override of class requires written rationale in the matrix.

## Artifacts

- Matrix: `data/voice_app_surface_coverage/baseline/voice-exposure-matrix.json`
- Gaps: `data/voice_app_surface_coverage/baseline/coverage-gap-matrix.json`
