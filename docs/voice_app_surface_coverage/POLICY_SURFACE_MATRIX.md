# Policy × Surface Matrix (VAS-009)

Program: `voice-app-surface-coverage-v1`

## Dual gates (unchanged)

| Action class | Unconfirmed | Confirmed | Confirmed + auth |
| --- | --- | --- | --- |
| Read (open surface, read calendar) | `confirm` | `permit_read` | `permit_read` |
| Write (create reminder, leave message) | `confirm` | `deny` (auth) | `permit_execute` |
| Human handoff | `handoff` | `handoff` | `handoff` |
| Safety escalate | `handoff` | `handoff` | `handoff` |

Confidence never upgrades authority (`PilotPolicy`).

## Surface exposure overlay

Applied **after** catalog permit, at the wallet app binding boundary:

| Exposure class | Client voice/phone | Client chat | Staff role |
| --- | --- | --- | --- |
| `voice_navigable` | open after confirm | open after confirm | same |
| `voice_actionable` | open/tool after gates | same | same |
| `voice_read_only` | deny open | optional later | n/a |
| `staff_only` | deny | deny (client) | allow later |
| `never_voice` | deny | deny | deny by default |

Error codes: `surface_never_voice`, `surface_staff_only`, `surface_voice_read_only`.

## Validation

```bash
PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py \
  python -m pytest -q ipfs_accelerate_py/test/test_action_policy_pilot.py
python -m pytest -q wallet_interface/tests/test_voice_app_action_binding.py \
  wallet_interface/tests/test_voice_app_action_binding_surfaces.py
```
