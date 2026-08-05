# Coverage Gaps

Program: `voice-app-surface-coverage-v1`  
Task: `VAS-007`  
Generated: `2026-08-05T17:35:10.635655+00:00`

P0 surfaces with holes: **5**

| surface | class | priority | dag edges | holes |
| --- | --- | --- | ---: | --- |
| `analytics` | voice_read_only | P1 | 0 | — |
| `audit` | never_voice | P2 | 0 | — |
| `benefits-protection` | never_voice | P1 | 0 | — |
| `calendar` | voice_actionable | P0 | 403 | — |
| `check-in` | voice_navigable | P0 | 113 | dag_density_below_p0_floor |
| `contacts` | voice_navigable | P0 | 113 | dag_density_below_p0_floor |
| `exports` | never_voice | P0 | 0 | — |
| `home` | voice_navigable | P0 | 113 | dag_density_below_p0_floor |
| `interactions` | voice_navigable | P0 | 113 | dag_density_below_p0_floor |
| `messages` | voice_actionable | P0 | 226 | — |
| `proof-center` | voice_read_only | P1 | 0 | — |
| `provider-analytics` | staff_only | P2 | 0 | — |
| `provider-cases` | staff_only | P1 | 0 | — |
| `provider-clients` | staff_only | P1 | 0 | — |
| `provider-messages` | staff_only | P1 | 0 | — |
| `provider-operations` | staff_only | P2 | 0 | — |
| `provider-proofs` | staff_only | P2 | 0 | — |
| `recipient-access` | never_voice | P0 | 0 | — |
| `register` | voice_navigable | P1 | 0 | dag_density_below_p0_floor, no_dag_route_mapping |
| `security` | never_voice | P0 | 0 | — |
| `settings` | voice_navigable | P0 | 113 | dag_density_below_p0_floor |
| `sharing-rules` | never_voice | P0 | 0 | — |
| `shelter` | staff_only | P1 | 0 | — |
| `social-services` | voice_actionable | P0 | 2227 | — |
| `uploads` | voice_actionable | P0 | 246 | — |
