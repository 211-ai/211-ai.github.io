# Abby Notes 3: Detailed Agent Todo List

Last updated: 2026-05-04

Source: informal Abby UI notes from the user.

## Goal

Turn the requested Abby Notes 3 changes into a concrete implementation backlog for an agent working in `wallet_interface/ui`.

These notes refine and sometimes supersede earlier Abby notes. Where this file conflicts with `docs/abby notes 2.md`, treat this file as the newer product direction, but keep privacy, consent, accessibility, and safety review gates visible in the implementation handoff.

## Primary App Areas

- App shell and route rendering: `wallet_interface/ui/src/app/App.tsx`
- Shared UI primitives: `wallet_interface/ui/src/components/ui.tsx`
- Domain types: `wallet_interface/ui/src/models/abby.ts`
- Mock data and persistence defaults: `wallet_interface/ui/src/services/mockAbbyService.ts`
- Global styling and responsive behavior: `wallet_interface/ui/src/styles/global.css`
- Visual capture tests: `wallet_interface/ui/tests/visual-capture.spec.ts`
- Smoke tests: `wallet_interface/ui/tests/smoke.spec.ts`
- Screenshot output: `wallet_interface/ui/artifacts/ui-screenshots/latest/`

## Important Product Notes

- The original notes skip number 11. Do not invent a requirement for note 11.
- Notes 3 changes the profile photo/photo ID requirement: PDF should now be allowed in the "photo or photo ID" section, and there should be no thumbnail preview.
- Notes 3 changes sharing-rule defaults: all sharing-rule scopes should start checked unless the user unchecks them, and saved unchecked choices must stay unchecked.
- Notes 3 requests benefits opt-in and analytics opt-in to start checked. This is sensitive and should be clearly marked as needing legal/privacy review before production.
- "Third grade reading level" applies to the public/user-facing app. Staff/admin sections may use more precise operational terms when needed.

## Agent Working Rules

- Inspect current behavior before editing because some Notes 2 work may already be implemented.
- Keep client-side state acceptable only for prototype/demo behavior; do not represent localStorage as production security.
- Treat profile, contact, sharing, benefits, analytics, shelter, and uploaded-document data as sensitive.
- Make opt-out controls visible, plain-language, and persistent.
- Do not persist temporary UI reveal states unless specifically required.
- Make all new buttons, checkboxes, toggles, and upload controls keyboard accessible.
- Respect reduced-motion settings if animations are touched.
- Run build, smoke tests, and visual capture after implementation.

## Priority Order

1. Update dashboard/home actions and check-in communication controls.
2. Update registration copy, PDF support, and no-thumbnail upload behavior.
3. Update contacts and shelter contact-request/nudge workflows.
4. Update sharing, benefits, analytics, and persistence defaults.
5. Remove document sensitivity from the vault.
6. Apply third-grade reading-level copy pass to user-facing screens.
7. Run tests, capture screenshots, and document privacy/legal caveats.

## Detailed Todo Backlog

### ABBY3-001: Dashboard Overview Actions Cleanup

Source notes: 1, 2

Tasks:

- [x] Locate the dashboard overview/home overview area.
- [x] Remove the standalone check-in button from the dashboard overview.
- [x] Keep the check-in action only in the quick actions section.
- [x] Combine or align the "check-in now" and "next check-in" quick action so the user sees one clear check-in action.
- [x] Make the words "Check in now" larger on the quick action button.
- [x] Ensure the enlarged label does not wrap awkwardly or clip on mobile.
- [x] Update the dashboard overview so it has only a Contacts button and a Sharing button.
- [x] Confirm dashboard overview still shows useful status without adding extra action buttons.
- [x] Avoid nested buttons or clickable elements.

Acceptance criteria:

- Dashboard overview no longer has a check-in button.
- Quick actions contains the only check-in button/next-check-in action.
- "Check in now" is visibly larger than the surrounding supporting text.
- Dashboard overview has exactly two action buttons: Contacts and Sharing.
- Keyboard users can reach and activate every remaining dashboard action.

Verification:

- Inspect desktop and mobile home/dashboard screenshots.
- Add or update a smoke test that confirms the quick action check-in route still works.

### ABBY3-002: Check-In Communication Method Controls

Source notes: 3, 4, 5

Tasks:

- [x] Locate the check-in settings or check-in page communication method controls.
- [x] Replace passive SMS, email, and web chips/toggles with real buttons or button-like controls.
- [x] Use plain labels: "Texting allowed", "Email allowed", and "Web allowed".
- [x] Allow users to check in by SMS, email, or web when that method is enabled and required contact details exist.
- [x] Add a note on the check-in page reminding users that they can check in by text, email, or web.
- [x] Keep the note short and simple.
- [x] When a user tries to check in by text without a phone number, show a clear message asking them to add a phone number to their account or use another approved check-in method.
- [x] When a user tries to check in by email without an email address, show a clear message asking them to add an email to their account or use another approved check-in method.
- [x] When a user tries to check in by web while web check-in is disabled, show a clear message asking them to choose an approved check-in method.
- [x] If a communication method is disabled, make its disabled/unavailable state understandable without relying only on color.
- [x] Persist allowed communication methods on submit if the app already persists check-in policy settings.

Acceptance criteria:

- SMS/text, email, and web controls are actual interactive controls.
- Missing contact information blocks that method and tells the user how to fix it.
- The check-in page includes a reminder that check-in can happen by text, email, or web.
- Enabled/disabled states are accessible to screen readers.

Verification:

- Smoke-test check-in with phone missing, email missing, web enabled, and web disabled states.
- Inspect check-in screenshots for clear button states and simple copy.

### ABBY3-003: Shelter Contact List Nudge And Request Flows

Source notes: 6, 7

Tasks:

- [x] Add or locate a shelter-to-user contact-list nudge flow.
- [x] Allow verified shelter staff to nudge a user to add that shelter to the user's contact list.
- [x] Make the nudge a request, not an automatic contact-list change.
- [x] Show the user a clear approve/deny choice for the shelter nudge.
- [x] Add or locate a user-to-shelter request flow.
- [x] Allow users to request that a shelter be added to their contact list.
- [x] Give shelters a review/approve/deny state for user requests if a shelter portal exists.
- [x] Track request state: pending, approved, denied, and canceled if useful.
- [x] Prevent duplicate pending requests between the same user and shelter.
- [x] Make request copy simple and non-coercive.
- [x] Keep contact sharing separate from adding a shelter as a contact; adding the shelter should not grant every sharing scope unless sharing rules say so.

Acceptance criteria:

- Verified shelter staff can send a contact-list nudge to a user.
- Users can request to add a shelter to contacts.
- Both flows require the receiving side to accept before the contact is active.
- Contact-list requests do not silently expand data sharing.
- Requests are visible with clear pending/approved/denied state.

Verification:

- Add mock data for pending shelter nudges and user requests.
- Smoke-test staff nudge creation, user approval, user request creation, and shelter approval.

### ABBY3-004: Registration Photo Or Photo ID Allows PDFs And No Thumbnail

Source note: 8

Tasks:

- [x] Locate the "photo or photo ID" upload field in registration.
- [x] Update accepted file types to allow image files and PDFs.
- [x] Include at least JPEG, PNG, WebP, and PDF unless existing product constraints require additional types.
- [x] Remove thumbnail preview behavior from this field.
- [x] Do not show an image thumbnail or PDF preview by default.
- [x] If the existing UI has a "See preview" control from Notes 2, remove it for this registration field or replace it with a non-thumbnail file detail view if needed.
- [x] Show the selected file name and file type instead of a thumbnail.
- [x] Keep validation clear when unsupported file types are selected.
- [x] Ensure uploaded PDFs are treated as identity documents, not profile photos for display.
- [x] Update any tests or docs that previously said PDFs were not accepted here.

Acceptance criteria:

- The registration "photo or photo ID" field accepts PDF.
- No thumbnail or visual preview appears for this registration upload.
- Users can still tell which file they selected.
- Unsupported file types produce a clear error.
- The implementation does not accidentally show sensitive ID images in a preview.

Verification:

- Manually test JPEG, PNG, WebP, PDF, and unsupported file selection.
- Inspect registration screenshot to confirm no thumbnail is shown.

### ABBY3-005: Registration Pronouns Placeholder Copy

Source note: 9

Tasks:

- [x] Locate the pronouns field in registration/profile.
- [x] Change the placeholder or helper example from "she/her, he/him, they/them" to "call me she/her, he/him, they/them".
- [x] Keep the field label concise, such as "Pronouns".
- [x] Ensure the example is not mistaken for a required format.
- [x] Make sure the copy appears in staff-created user account forms too if those reuse registration fields.

Acceptance criteria:

- Pronouns example text reads exactly or very close to: "call me she/her, he/him, they/them".
- The field still accepts free-form pronouns.
- The copy is consistent anywhere registration fields are reused.

Verification:

- Inspect registration and staff-created user account forms.
- Search for stale placeholder copy.

### ABBY3-006: Registration Reminder Helper Text Size

Source note: 10

Tasks:

- [x] Locate helper text that says "Used for text reminders" and "Used for email reminders".
- [x] Make both helper lines larger and easier to read.
- [x] Keep the helper text visually subordinate to the field label.
- [x] Ensure larger helper text does not crowd mobile registration layout.
- [x] Use a reusable helper-text class or component style if possible.

Acceptance criteria:

- Text reminder and email reminder helper copy is visibly larger.
- The larger helper text remains readable and does not clip.
- The change is consistent for both phone and email fields.

Verification:

- Inspect registration screenshots on mobile and desktop.

### ABBY3-007: Third Grade Reading-Level Copy Pass

Source note: 12

Tasks:

- [x] Review user-facing copy across home/dashboard, registration, check-in, contacts, sharing rules, uploads, social services, benefits opt-in, analytics opt-in, recipient access, and security.
- [x] Rewrite public/user-facing copy toward a third grade reading level.
- [x] Keep sentences short.
- [x] Prefer common words over technical words.
- [x] Replace abstract terms with direct action words.
- [x] Keep staff/admin sections exempt where precise operational wording is needed.
- [x] Do not remove important legal, privacy, safety, or consent meaning just to simplify wording.
- [x] Keep labels specific enough for accessibility and screen-reader users.
- [x] Add final handoff notes for any copy that could not be simplified without losing meaning.

Suggested copy rules:

- Use "You can..." instead of "Users may..."
- Use "Text" instead of "SMS" in most visible copy, with "SMS" only where technically necessary.
- Use "Share" instead of "disclose" in most user-facing text.
- Use "File" or "document" instead of "asset".
- Use "Help" or "support" instead of "liaison" where possible.
- Use "Turn off" instead of "opt out" when space allows.

Acceptance criteria:

- Core user screens are understandable to a third grade reader.
- Staff/admin screens may retain precise terms.
- Consent and privacy warnings remain accurate.
- No critical meaning is removed.

Verification:

- Manually review visible copy in screenshots.
- Optionally paste representative copy into a reading-level checker if available.

### ABBY3-008: Center Add Recipient Button

Source note: 13

Tasks:

- [x] Locate the contacts add-recipient button.
- [x] Center the add-recipient button within its section instead of aligning it flush to one side.
- [x] Keep button width appropriate for mobile and desktop.
- [x] Ensure the button remains visually connected to the add-recipient form.
- [x] Confirm focus, hover, active, and disabled states still work.

Acceptance criteria:

- Add recipient button is centered.
- Contacts layout remains clean on mobile and desktop.
- The button remains easy to find and use.

Verification:

- Inspect contacts screenshots.

### ABBY3-009: Sharing Rules Default Everything Checked With Persistent Unchecks

Source note: 14

Tasks:

- [x] Locate sharing-rule default state for recipients and data scopes.
- [x] Change default behavior so every sharing-rule option starts checked.
- [x] If the user unchecks an option, save that unchecked choice.
- [x] Reopen sharing rules with saved choices exactly as the user left them.
- [x] Make saved user choices override default checked state.
- [x] Ensure defaults apply only when no prior user choice exists.
- [x] Include all current scopes, including missed check-in and found permanent housing if those exist from Notes 2.
- [x] Add clear plain-language text explaining that the user can turn off any item before saving.
- [x] Add a privacy/legal review note because default-enabled sensitive sharing may require explicit compliance review before production.
- [x] Avoid changing backend authorization assumptions unless a backend API contract exists.

Acceptance criteria:

- New sharing-rule sessions start with all options checked.
- User-unchecked options stay unchecked after submit, route change, and refresh.
- The UI makes it obvious that the user can turn items off.
- The implementation includes a production review caveat for sensitive default sharing.

Verification:

- Smoke-test new recipient defaults.
- Smoke-test unchecking several scopes, saving, refreshing, and reopening.

### ABBY3-010: Remove Sensitivity From Document Vault

Source note: 15

Tasks:

- [x] Locate document vault upload and list UI.
- [x] Remove the sensitivity field/control from the document vault.
- [x] Remove sensitivity badges or labels from stored upload cards/list rows.
- [x] Update upload item mock data only if needed for UI consistency.
- [x] Avoid broad data-model churn unless tests or TypeScript require it.
- [x] If `UploadItem.sensitivity` remains in the type for compatibility, stop showing it in user-facing UI.
- [x] Update tests or screenshots that expect sensitivity text.

Acceptance criteria:

- Users no longer see or set document sensitivity in the vault.
- Upload list remains useful with file name, short summary/title, category if still used, storage status, and sharing status.
- TypeScript build passes.

Verification:

- Search for visible sensitivity copy in UI source.
- Inspect uploads screenshots.

### ABBY3-011: Benefits Opt-In Defaults Checked With Persistent Opt-Out

Source note: 16

Tasks:

- [x] Locate benefits opt-in state and UI.
- [x] Set explicit opt-in checkbox/control to checked by default.
- [x] Allow the user to uncheck it.
- [x] Persist the unchecked state after submit, route change, and refresh.
- [x] Keep the copy simple and clear about what the benefits setting does.
- [x] Avoid implying government or benefits agency action is guaranteed.
- [x] Add privacy/legal review note because default-enabled benefits consent can be legally sensitive.
- [x] Ensure screen readers announce checked state correctly.

Acceptance criteria:

- Benefits opt-in starts checked for a new user/session with no saved preference.
- If the user unchecks it and saves, it stays unchecked.
- The setting remains clear, reversible, and accessible.
- The final handoff flags this default as needing policy/legal approval before production.

Verification:

- Smoke-test default checked state and saved unchecked state.
- Inspect benefits opt-in screenshot.

### ABBY3-012: Analytics Defaults Checked With Persistent Opt-Out

Source note: 17

Tasks:

- [x] Locate analytics opt-in state and UI.
- [x] Set analytics checkboxes/toggles to checked by default.
- [x] Allow the user to uncheck analytics choices.
- [x] Persist unchecked choices after submit, route change, and refresh.
- [x] Keep analytics copy at third grade reading level where possible.
- [x] Make clear what information analytics may use and why.
- [x] Add privacy/legal review note because default-enabled analytics can require consent-policy review.
- [x] Do not include staff/admin analytics controls unless they already exist and are clearly separate.

Acceptance criteria:

- Analytics options start checked when no saved preference exists.
- User-unchecked analytics options remain unchecked after save and refresh.
- The copy makes analytics understandable without hiding privacy meaning.
- The final handoff flags this default as needing policy/legal approval before production.

Verification:

- Smoke-test default checked analytics state and saved opt-out state.
- Inspect analytics screenshot.

### ABBY3-013: Cross-Screen Persistence Audit

Source notes: 5, 9, 14, 16, 17

Tasks:

- [x] Audit state persistence for check-in methods, sharing-rule scopes, benefits opt-in, analytics opt-in, and registration fields.
- [x] Ensure new defaults apply only when no saved preference exists.
- [x] Ensure saved opt-outs and unchecked values are never overwritten by defaults.
- [x] Ensure missing phone/email warnings do not persist as stale errors after the user fixes the field.
- [x] Keep temporary UI states out of persistence unless requested.

Acceptance criteria:

- Refreshing the app preserves saved user choices.
- New users get the requested default checked states.
- Existing saved choices are respected.
- Errors clear when the user fixes missing information.

Verification:

- Manual refresh testing across check-in, sharing rules, benefits, and analytics.
- Add smoke tests for the highest-risk persistence paths.

### ABBY3-014: Final Copy And Terminology Sweep

Source notes: all

Tasks:

- [x] Search for stale or conflicting copy from Notes 2.
- [x] Update any text that says PDFs are not accepted for photo/photo ID.
- [x] Update any text that says photo/photo ID preview can be shown, unless a non-thumbnail file detail view remains.
- [x] Ensure "Texting allowed", "Email allowed", and "Web allowed" appear consistently in check-in controls.
- [x] Ensure "call me she/her, he/him, they/them" appears in pronouns examples.
- [x] Ensure "Used for text reminders" and "Used for email reminders" are still present if the user asked for those exact helper lines, but styled larger.
- [x] Keep third-grade-level copy in user-facing sections.

Acceptance criteria:

- No stale visible copy contradicts Notes 3.
- The app uses the requested labels exactly where exact wording was requested.
- The copy pass does not weaken safety or consent meaning.

Verification:

```powershell
rg "PDF|preview|SMS|she/her|Used for text reminders|Used for email reminders|sensitivity" wallet_interface/ui/src
```

### ABBY3-015: Tests, Screenshots, And Final Handoff

Source notes: all

Tasks:

- [x] Run TypeScript build.
- [x] Run smoke tests.
- [x] Run visual capture tests.
- [x] Review screenshots for dashboard, check-in, registration, contacts, sharing rules, uploads, benefits, and analytics.
- [x] Update visual tests if the route inventory or expected screenshots changed.
- [x] In final handoff, list changed files.
- [x] In final handoff, list commands run and pass/fail status.
- [x] In final handoff, list screenshot paths or grouped screenshot inventory.
- [x] In final handoff, call out any production review caveats for default-enabled sharing, benefits, and analytics.
- [x] In final handoff, call out any blocked or intentionally deferred work.

Acceptance criteria:

- Build passes.
- Smoke tests pass or failures are explained.
- Visual capture passes or failures are explained.
- The user can see which screenshots prove the changes.
- Privacy/legal caveats are explicit.

Verification commands:

```powershell
cd wallet_interface/ui
npm run build
npm run test:smoke
npm run test:visual
```

## Suggested Work Split For Multiple Agents

### Agent A: Dashboard, Check-In, And Registration

- ABBY3-001
- ABBY3-002
- ABBY3-004
- ABBY3-005
- ABBY3-006

### Agent B: Contacts And Shelter Requests

- ABBY3-003
- ABBY3-008

### Agent C: Defaults, Vault, And Persistence

- ABBY3-009
- ABBY3-010
- ABBY3-011
- ABBY3-012
- ABBY3-013

### Agent D: Reading Level, QA, And Handoff

- ABBY3-007
- ABBY3-014
- ABBY3-015

## Notes For The Implementation Agent

- Notes 3 should be treated as the latest request set.
- Allowing PDFs in photo/photo ID changes the earlier profile-photo behavior. Do not show thumbnails for this field.
- Default-checked sharing, benefits, and analytics should be implemented carefully in prototype state, with saved user opt-outs preserved.
- Default-enabled consent flows are sensitive. Flag them for product, privacy, and legal review before production.
- Keep the user-facing app very simple to read. Staff sections can be more technical where needed.
