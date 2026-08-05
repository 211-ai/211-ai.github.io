# Policy surface matrix (VAS2-011)

Program: `voice-app-surface-full-coverage-v2`  
Policy revision: `pilot-policy-matrix-v2`  
Updated: `2026-08-05T21:06:40.142044+00:00`

## Gates (fail closed)

| Risk class | Confirm | Auth | Notes |
| --- | --- | --- | --- |
| READ | required | if metadata auth_required | includes open_app_surface after surface gate |
| WRITE | required | always | calendar create, leave message, schedule callback |
| HUMAN | handoff path | n/a | handoff_live_agent, escalate_safety |
| ADMIN | elevated grant | always | default deny |

## Surface exposure (before class matrix)

For `open_app_surface` and `open_wallet_documents`:

| Exposure class | Client voice/phone/chat |
| --- | --- |
| voice_navigable / voice_actionable | allow (then confirm/auth) |
| voice_read_only | **deny** `surface_voice_read_only` |
| staff_only | **deny** `surface_staff_only` (unless role=staff) |
| never_voice | **deny** `surface_never_voice` |
| unknown | **deny** as never_voice |

Implementation: `ipfs_accelerate_py.action_runtime.policy_pilot.PilotPolicy` +
`surface_exposure.surface_exposure_deny_reason`.
