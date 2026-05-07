# Abby Notes 3 Copy And QA Handoff

Date: 2026-05-04

Scope: ABBY3-007, ABBY3-014, and ABBY3-015, plus final integration notes for the Notes 3 work in `wallet_interface/ui`.

## Completed

- Simplified public copy across home, registration, check-in, contacts, sharing, uploads, services, benefits, analytics, recipient access, and security.
- Replaced public permission summaries with plain labels such as "open file contents", "make a safe summary", "read exact location", and "ask group questions".
- Kept exact requested labels visible: "Texting allowed", "Email allowed", "Web allowed", "call me she/her, he/him, they/them", "Used for text reminders.", and "Used for email reminders."
- Kept PDF support and no-thumbnail behavior for photo or photo ID in registration and staff-created user forms.
- Kept shelter contact requests consent-based: staff nudges and user requests stay pending until the receiving side approves, and duplicate pending requests are blocked.
- Kept default-on sharing, benefits, and analytics reversible and persistent, with visible privacy/legal review notes.
- Removed visible document sensitivity from the vault while leaving compatibility fields in the model/API path.

## Verification

- `npm run build` passed.
- `$env:PLAYWRIGHT_PORT='5194'; npm run test:smoke` passed: 47 passed, 1 skipped desktop mobile-navigation case.
- `$env:PLAYWRIGHT_PORT='5195'; npm run test:visual` passed: 2 passed.
- `$env:PLAYWRIGHT_PORT='5192'; npm run test:smoke` passed after the plain-permission-label follow-up: 47 passed, 1 skipped desktop mobile-navigation case.
- `$env:PLAYWRIGHT_PORT='5193'; npm run test:visual` passed after the plain-permission-label follow-up: 2 passed.
- `npm run review:visual:dry-run` passed and regenerated 43 screenshot review entries.
- `npm run review:tasks` passed and regenerated 43 review backlog tasks.
- `npm run review:prompts` passed and left only the prompt index because there are no active generated prompt files.

## Screenshot Inventory

- Desktop manifest: `wallet_interface/ui/artifacts/ui-screenshots/latest/desktop/manifest.json`
- Mobile manifest: `wallet_interface/ui/artifacts/ui-screenshots/latest/mobile/manifest.json`
- Reviewed key captures: `home`, `register-filled`, `check-in`, `contacts`, `contacts-add-recipient-draft`, `sharing-rules`, `uploads`, `benefits-protection`, and `analytics`.
- Current visual capture inventory also includes services, shelter, recipient access, security, and audit states for desktop and mobile.

## Changed Files

- `docs/abby notes 3.md`
- `docs/abby notes 2.md`
- `wallet_interface/ui/docs/abby3-agent-d-copy-qa.md`
- `wallet_interface/ui/src/app/App.tsx`
- `wallet_interface/ui/src/services/capabilities.ts`
- `wallet_interface/ui/src/services/mockAbbyService.ts`
- `wallet_interface/ui/src/styles/global.css`
- `wallet_interface/ui/tests/smoke.spec.ts`
- `wallet_interface/ui/tests/visual-capture.spec.ts`
- `wallet_interface/ui/tests/refinement-iteration.spec.ts`
- `wallet_interface/ui/artifacts/ui-screenshots/latest/**`
- `wallet_interface/ui/artifacts/ui-review/latest/**`
- `wallet_interface/ui/dist/**` from the production build

## Caveats

- Default-enabled sharing, benefits notification, and analytics choices need product, privacy, and legal approval before production release.
- Prototype persistence uses browser local storage and should not be described as production security.
- Some advanced wallet/proof/audit strings remain exact on purpose in operational, API, proof, export, and audit contexts, including DID values, receipt hashes, `analytics/contribute`, `location/prove_region`, and `proof/verify`. These preserve permission and audit meaning and should be reviewed by product/legal rather than removed only for reading level.
- No Agent D work is blocked. The remaining production work is review/approval, not an implementation blocker in the current UI.
