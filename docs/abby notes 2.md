# Abby Notes 2: Detailed Agent Todo List

Last updated: 2026-05-04

Source: informal Abby UI notes from the user.

## Goal

Turn the requested Abby UI changes into a concrete implementation backlog an agent can work through inside `wallet_interface/ui`.

The implementation agent should inspect the current React/TypeScript app before editing. Several items may already be partially implemented, so the agent should verify current behavior, complete missing behavior, and avoid reverting unrelated local changes.

## Primary App Areas

- App shell and route rendering: `wallet_interface/ui/src/app/App.tsx`
- Shared UI primitives: `wallet_interface/ui/src/components/ui.tsx`
- Domain types: `wallet_interface/ui/src/models/abby.ts`
- Mock data and persistence defaults: `wallet_interface/ui/src/services/mockAbbyService.ts`
- Global styling and responsive behavior: `wallet_interface/ui/src/styles/global.css`
- Visual capture tests: `wallet_interface/ui/tests/visual-capture.spec.ts`
- Smoke tests: `wallet_interface/ui/tests/smoke.spec.ts`
- Screenshot output: `wallet_interface/ui/artifacts/ui-screenshots/latest/`

## Agent Working Rules

- Treat all profile, shelter, emergency contact, uploaded document, and sharing-rule data as sensitive.
- Keep client-side PIN logic as mock/demo only unless a backend API already exists; production PIN validation must not rely on secrets shipped in browser code.
- Preserve user control over sharing. Do not auto-share sensitive data beyond the explicit defaults requested for sharing rules.
- Make every clickable card, checkbox, toggle, select, upload, and navigation action keyboard accessible.
- Respect reduced-motion preferences for decorative animation.
- Run `npm run build` and targeted Playwright tests from `wallet_interface/ui` after changes.
- Capture and review screenshots before final handoff. The user specifically asked to see all screenshots.

## Priority Order

1. Complete low-risk UX/copy/layout fixes that affect existing screens.
2. Complete persistence and sharing-rule behavior.
3. Complete upload summary and photo/photo ID file detail behavior.
4. Complete shelter staff/admin/client-account workflows.
5. Complete bot-check status logic and shelter reporting lists.
6. Complete welcoming visual treatment and animation polish.
7. Run visual capture, smoke tests, and final screenshot handoff.

## Detailed Todo Backlog

### ABBY2-001: Baseline Screenshot Capture And Handoff

Source notes: 2, 3, 4

Tasks:

- [x] From `wallet_interface/ui`, run the existing visual capture flow.
- [x] Confirm screenshots are generated for desktop and mobile, if the test suite supports both.
- [x] Confirm at least these views are captured: home, register, check-in, contacts, sharing rules, uploads, social services, shelter, recipient access, benefits protection, analytics, security, and audit.
- [x] If any requested view is missing from `visual-capture.spec.ts`, add it.
- [x] Review screenshots for obvious layout breakage, clipped text, missing controls, blank screens, and overlapping elements.
- [x] In final handoff, list every screenshot path grouped by viewport.

Acceptance criteria:

- `wallet_interface/ui/artifacts/ui-screenshots/latest/` contains a current screenshot set.
- The final agent response includes a concise screenshot inventory.
- No captured route is blank or visibly broken.

Verification:

- Run `npm run test:visual`.
- Optionally run `npm run review:visual` if the script is working in this environment.

### ABBY2-002: Apply Comic Sans Typography

Source note: 0

Tasks:

- [x] Locate the global typography definition in `global.css`.
- [x] Set the app font stack to prefer Comic Sans, for example `"Comic Sans MS", "Comic Sans", cursive`, followed by a readable fallback.
- [x] Ensure form controls, buttons, labels, nav items, cards, and modals inherit the updated font unless a component intentionally overrides it.
- [x] Check that text remains readable on mobile and desktop.

Acceptance criteria:

- The whole Abby UI visibly uses the Comic Sans-style font stack.
- No text becomes clipped because of the font change.
- The visual change is centralized in CSS rather than repeated across components.

Verification:

- Inspect home, registration, check-in, sharing rules, and shelter screenshots.

### ABBY2-003: Make All Red Required Asterisks Larger

Source notes: 1, 7

Tasks:

- [x] Find the component or markup that renders required field asterisks.
- [x] Make every red asterisk slightly larger than its field label text.
- [x] Apply the same treatment to first-run/registration questions and every other required field in the app.
- [x] Preserve accessible required-field semantics with `required`, `aria-required`, or existing app conventions.
- [x] Make sure the asterisk does not shift label alignment or wrap awkwardly on mobile.

Acceptance criteria:

- All required asterisks are consistently larger and red.
- The implementation is reusable, not a one-off style on only one form.
- Screen readers can still identify required fields.

Verification:

- Inspect registration, shelter staff registration, staff-created client account forms, and any contact forms.

### ABBY2-004: Home Check-In Card Navigation And CTA Merge

Source notes: 5, 9

Tasks:

- [x] Locate the home screen check-in summary/card.
- [x] Make the entire next-check-in square/card clickable.
- [x] Route clicks to the check-in page.
- [x] Combine the "Next check-in" and "Check in now" affordances into one clear interactive element.
- [x] Include both status and action in the merged UI, such as next due date plus a check-in action label.
- [x] Ensure keyboard users can focus and activate the same card/button.
- [x] Avoid nested interactive elements inside another clickable element.

Acceptance criteria:

- Clicking or pressing Enter/Space on the home check-in card opens the check-in page.
- The home screen no longer has two competing check-in actions.
- The merged element clearly communicates the next check-in status and the action available.

Verification:

- Add or update a Playwright smoke assertion for home-to-check-in navigation.
- Confirm the home screenshot shows one coherent check-in element.

### ABBY2-005: Move Sharing Rules And Stored Uploads Count To Home Bottom

Source note: 8

Tasks:

- [x] Locate the home screen summary/status area.
- [x] Move the sharing-rules summary to the bottom of the home page.
- [x] Display the number of stored uploads near the sharing-rules summary.
- [x] Restyle the stored uploads number so it reads like status text or a metric, not a clickable button.
- [x] If the sharing-rules summary remains clickable, make only the intended control look clickable.
- [x] Confirm the moved content does not crowd primary home actions.

Acceptance criteria:

- Sharing choices appear near the bottom of the home page.
- Stored upload count is visually informative and not button-like.
- Primary home actions remain easy to scan.

Verification:

- Inspect desktop and mobile home screenshots.

### ABBY2-006: Registration And Profile Field Updates

Source notes: 10, 11, 12, 13, 14

Tasks:

- [x] Add a pronouns field to the profile/registration data model if it is not already present.
- [x] Render the pronouns field in the user-facing create-profile/register flow.
- [x] Replace every user-facing instance of "shelter affiliation" with "preferred shelter".
- [x] In the register section, change "account photo" to "photo or photo ID".
- [x] In the create-profile section only, visually separate identity fields from later fill-in fields.
- [x] The separated identity group should include legal name, preferred name, birthdate, and photo/photo ID.
- [x] Remove the entire profile review section from the create-profile flow.
- [x] Make sure removing profile review does not leave dead state, navigation, route anchors, or tests expecting the review step.

Acceptance criteria:

- Registration includes pronouns.
- "Preferred shelter" is used consistently.
- "Photo or photo ID" appears where the user asked for it.
- Legal name, preferred name, birthdate, and photo/photo ID read as one visual section.
- No profile review section appears in create profile.

Verification:

- Search for old copy: `rg "shelter affiliation|account photo|profile review" wallet_interface/ui/src`.
- Run registration smoke tests and inspect registration screenshots.

### ABBY2-007: Contacts Copy, Type Options, And Add Recipient Layout

Source notes: 6, 15, 16

Tasks:

- [x] Locate the contact recipient type dropdown.
- [x] Document the current dropdown options in the final handoff.
- [x] Confirm options match the domain model, likely including emergency contact, police precinct, social worker, shelter staff, government liaison, and benefits agency.
- [x] Change user-facing copy from "people and agencies" to "people and services".
- [x] Move the add-recipient form/section above the previously entered contacts list.
- [x] Ensure the contacts list still supports viewing, editing, deleting, and scope review if those actions exist.
- [x] Make the layout work on mobile without pushing the existing contacts too far down unnecessarily.

Acceptance criteria:

- The add-recipient section appears before the saved contacts list.
- The screen uses "people and services" wherever the user-facing phrase appears.
- The final response answers: "What are the options in the type dropdown menu for contacts?"

Verification:

- Inspect contacts screenshot.
- Search for stale copy: `rg "people and agencies" wallet_interface/ui/src`.

### ABBY2-008: Sharing Rule Defaults, Persistence, And New Scopes

Source notes: 17, 18, 28

Tasks:

- [x] Locate sharing-rule state and default recipient allowed scopes.
- [x] Make "Minimum identity" and "Photo" selected automatically when a user opens sharing rules for a recipient that has no saved custom choice.
- [x] If a user changes those selections, persist the changed values.
- [x] Persist user-selected radio buttons and checkboxes on submit so choices survive route changes and browser sessions.
- [x] Add "Missed check-in" as a selectable sharing-rule scope.
- [x] Add "Found permanent housing" as a selectable sharing-rule scope.
- [x] Confirm persistence covers all sharing-rule checkboxes, radio buttons, and any related toggles.
- [x] Avoid overwriting a user-customized recipient with defaults after the first save.

Acceptance criteria:

- New recipients default to selected minimum identity and photo scopes.
- Previously saved scope changes reopen exactly as the user saved them.
- Missed check-in and found permanent housing appear in sharing rules.
- Refreshing the browser does not lose submitted sharing-rule selections.

Verification:

- Add or update smoke tests for default sharing scopes and persistence.
- Manually test by selecting scopes, submitting, refreshing, and reopening sharing rules.

### ABBY2-009: Upload Summary Generation And Short Titles

Source notes: 19, 20

Tasks:

- [x] Locate the information-vault upload flow.
- [x] When a user uploads a file or document, generate a machine summary using text extraction or OCR when possible.
- [x] For text-like files, extract text directly.
- [x] For images, use OCR if the current dependency set supports it.
- [x] For unsupported files or extraction failure, fall back to the uploaded filename.
- [x] Format the machine-generated summary as a short title with fewer than 5 words.
- [x] Display the generated title near the uploaded item label so the user can recognize the document later.
- [x] Make loading, failed, and fallback summary states clear.

Acceptance criteria:

- Every uploaded item gets a machine-generated summary/title.
- The displayed title is 1 to 4 words.
- Upload still succeeds when OCR/text extraction fails.
- The summary supplements the user-provided label instead of replacing it.

Verification:

- Test text upload, image upload, and unsupported file fallback.
- Inspect uploads screenshot.

### ABBY2-010: Photo/Photo ID File Types And No Preview

Source note: 21

Notes 3 update: the current photo/photo ID field accepts image files and PDFs. It shows file details only, with no thumbnail or PDF preview.

Tasks:

- [x] Identify accepted profile-photo file types.
- [x] Ensure profile photo/photo ID upload accepts image file types needed by the app, such as JPEG, PNG, and WebP.
- [x] Accept PDF for the combined photo/photo ID field.
- [x] Add a concise UI note or final handoff explanation answering which photo/photo ID file types are accepted.
- [x] Do not show thumbnail or PDF preview UI for this registration field.
- [x] Do not add a "See preview" button or disclosure control for this registration field.
- [x] Show selected file name and type instead of a preview.
- [x] Treat uploaded PDFs as identity documents, not profile photos for display.
- [x] Keep unsupported file validation clear.

Acceptance criteria:

- No thumbnail or PDF preview is shown.
- There is no preview reveal control for this registration field.
- Accepted file types are clear.
- PDF is accepted for the photo/photo ID input.

Verification:

- Inspect registration screenshot and selected-file detail state.
- Manually test image and PDF selection with no preview.

### ABBY2-011: Assisted Access Visibility Rules

Source note: 22

Tasks:

- [x] Identify the assisted access page/section, if it exists.
- [x] Determine whether it currently appears for all users or only shelter staff.
- [x] Make assisted access visible only when the account/session is verified as shelter staff, unless product requirements state otherwise.
- [x] Hide or disable related navigation entries for non-staff users.
- [x] If a non-staff user reaches the route directly, show an access-denied or staff-verification-required state instead of sensitive staff tools.
- [x] Document the implemented behavior in the final handoff.

Acceptance criteria:

- Non-staff users cannot use assisted access.
- Verified shelter staff can see and use assisted access.
- The final response answers whether assisted access is only shown for shelter staff.

Verification:

- Add or update smoke tests for non-staff hidden route and staff-visible route.

### ABBY2-012: Shelter Staff Registration With Shelter PIN

Source note: 23

Tasks:

- [x] Add or complete a shelter-staff opt-in box near the bottom of the registration page.
- [x] The checkbox label must be exactly: "I am shelter staff".
- [x] When unchecked, shelter staff fields must be hidden.
- [x] When checked, show a shelter dropdown.
- [x] When checked, show a required shelter PIN input.
- [x] Require a valid staff PIN before the account can be verified as shelter staff.
- [x] Assign every shelter two 4-digit PINs in mock/demo data: one staff PIN and one administrator PIN.
- [x] Treat PIN visibility as developer-only. Do not expose PINs in normal user, staff, or admin UI.
- [x] In a production architecture note, state that PIN verification must move server-side.
- [x] Only after correct staff PIN verification should the shelter portal appear in the hamburger/nav and become usable.
- [x] Add error states for missing PIN, wrong PIN, and missing shelter selection.
- [x] Add success state for verified staff.
- [x] Add audit-friendly state names for staff verification.

Acceptance criteria:

- Shelter staff fields appear only after checking "I am shelter staff".
- Staff verification requires shelter selection and correct staff PIN.
- Shelter portal is hidden or locked for unverified users.
- The implementation includes mock/demo staff and admin PINs per shelter without exposing them in UI.

Verification:

- Smoke-test unverified user, wrong PIN, correct staff PIN, and shelter portal visibility.

### ABBY2-013: Shelter Administrator PIN Page And Staff Management

Source note: 24

Tasks:

- [x] Add a shelter administrator page or section available from verified shelter staff context.
- [x] Show an administrator PIN input before revealing administrator tools.
- [x] Verify the entered admin PIN against the selected shelter's admin PIN in mock/demo data.
- [x] After correct admin PIN entry, show all staff accounts for that shelter.
- [x] Let administrators delete staff accounts, with confirmation.
- [x] Let administrators change the required PIN for new staff registering at that shelter.
- [x] Let administrators rotate/change the PIN for all staff.
- [x] Separate staff PIN rotation from administrator PIN rotation unless the user explicitly requests both.
- [x] Add clear success/error messages for PIN changes and staff deletion.
- [x] Ensure administrator actions are represented in audit events or mock audit state if an audit system exists.

Acceptance criteria:

- Staff cannot see administrator tools without the correct administrator PIN.
- Administrator view lists staff only for the administrator's shelter.
- Administrator can delete staff accounts and change/rotate staff PINs.
- Actions update UI state immediately and persist across sessions if the app uses local persistence.

Verification:

- Smoke-test wrong admin PIN, correct admin PIN, staff list visibility, staff deletion, and staff PIN rotation.

### ABBY2-014: Staff-Created Client User Accounts

Source notes: 25, 26

Tasks:

- [x] In verified shelter staff context, add a section for creating non-staff client/user accounts.
- [x] Make clear that these are user accounts, not staff accounts.
- [x] Include all inputs available in the normal registration section.
- [x] Keep the field labels, required asterisks, validation, bot-check behavior, and preferred-shelter copy consistent with normal registration.
- [x] Automatically associate staff-created client accounts with the staff member's shelter.
- [x] Preserve client privacy boundaries and avoid implying staff owns the user's private account.
- [x] Add created-by staff metadata in mock state if needed for listing and audit.
- [x] Persist staff-created client accounts across sessions if the app uses local persistence.

Acceptance criteria:

- Verified staff can create a non-staff user account.
- The staff-created user form includes the same fields as registration.
- Created users show up in shelter user lists.
- Unverified users cannot create client accounts.

Verification:

- Smoke-test create-client flow from a verified staff session.
- Confirm created user appears in the correct shelter list after refresh.

### ABBY2-015: Shelter User Lists, Status Columns, And Sorting

Source note: 27

Tasks:

- [x] Add or complete a shelter users section visible to verified staff and administrators.
- [x] First list: users created by any staff member at the same shelter, even if the original staff member is no longer verified.
- [x] Second list: users who selected or mentioned that shelter as preferred shelter but were not necessarily created by shelter staff.
- [x] For each user, display name.
- [x] For each user, display whether their local precinct has ever been notified as an emergency contact.
- [x] For each user, display whether they failed the first/easy bot-check step.
- [x] Label failed easy bot-check status as a "Health check" tag.
- [x] For each user, display whether they found permanent housing.
- [x] In each list, sort users who found permanent housing to the bottom.
- [x] Within each found-housing group, sort by date registered.
- [x] Make sorting deterministic and documented in code.
- [x] Ensure staff can see users for their own shelter only.

Acceptance criteria:

- Two separate shelter user lists exist with clear headings.
- Required statuses appear next to each name.
- Found-housing users are at the bottom of their respective lists.
- Remaining order is by registration date.
- Users remain visible even if the creating staff account is deleted or unverified.

Verification:

- Add mock users covering each status combination.
- Add smoke assertions for list grouping and ordering.

### ABBY2-016: Mandatory Two-Step Bot Check And Health Check Tag

Source note: 29

Tasks:

- [x] Add a mandatory first bot-check step that is intentionally simple.
- [x] Add a mandatory second bot-check step that represents the real CAPTCHA/bot check.
- [x] Prevent registration completion until both required bot-check steps are handled according to app rules.
- [x] Track pass/fail status for the easy first step.
- [x] If a user fails the easy first step and either selected a preferred shelter or was registered by shelter staff, mark them with a health-check status.
- [x] Surface the health-check tag in shelter user lists.
- [x] Keep the copy gentle and non-stigmatizing. This status should suggest follow-up, not blame.
- [x] Persist bot-check status with the profile/client account.

Acceptance criteria:

- Registration includes two bot-check steps.
- The second step remains the real anti-abuse gate.
- Easy-step failure creates a health-check tag only in the shelter-related cases requested.
- Shelter lists display the health-check tag correctly.

Verification:

- Test pass/pass, fail/pass with preferred shelter, fail/pass without preferred shelter, and staff-created fail/pass cases.

### ABBY2-017: Sharing Rule Scope Persistence Across Sessions

Source note: 18

Tasks:

- [x] Audit all radio buttons and checkboxes across registration, check-in policy, sharing rules, shelter checklist, benefits opt-in, analytics opt-in, and security settings.
- [x] Decide which selections should persist on submit.
- [x] Persist those selections using the existing app persistence pattern.
- [x] Avoid persisting transient sensitive reveal states, such as preview-open, secret-visible, or temporary confirmation state.
- [x] Confirm refresh/reopen behavior is consistent across affected screens.

Acceptance criteria:

- User-submitted settings remain consistent across sessions.
- Sensitive temporary reveal states do not persist accidentally.
- Persistence behavior is predictable and documented in code or final handoff.
- Prototype note: durable form controls auto-save to local app state when changed; transient reveal states are not persisted.

Verification:

- Manual refresh test for each affected screen.
- Smoke tests for the highest-risk persistence flows: sharing rules, shelter verification, and check-in policy.

### ABBY2-018: Friendly Kid-Like Margin Art And Gentle Animation

Source note: 30

Tasks:

- [x] Add decorative butterflies, flowers, or similar hand-drawn margin art.
- [x] Keep art in the margins/background so it does not cover form fields, buttons, cards, or important status text.
- [x] Make the app feel more welcoming and upbeat.
- [x] Add subtle animation when a user clicks a button or toggles something.
- [x] Respect `prefers-reduced-motion`.
- [x] Make animations gentle and brief.
- [x] Avoid making decorative elements look like interactive controls unless they actually are interactive.
- [x] Confirm contrast and focus states remain accessible.

Acceptance criteria:

- Decorative art is visible on home and core forms without blocking content.
- Button/toggle interactions trigger a small visual response.
- Reduced-motion users do not get unnecessary animation.
- Screenshots show a warmer UI without visual clutter.

Verification:

- Inspect mobile and desktop screenshots for home, registration, sharing rules, and shelter.
- Check reduced-motion CSS behavior.

### ABBY2-019: Final Copy And Terminology Sweep

Source notes: 11, 13, 15

Tasks:

- [x] Search the UI source for stale phrases.
- [x] Replace "shelter affiliation" with "preferred shelter".
- [x] Replace "account photo" with "photo or photo ID" in the registration context.
- [x] Replace "people and agencies" with "people and services".
- [x] Fix obvious typos in user-facing copy found near touched areas, such as "preferre" or "uplaods", if present in the UI.
- [x] Keep data model names stable unless changing them is necessary.

Acceptance criteria:

- Requested terminology appears consistently in visible UI.
- No stale wording remains in user-facing source strings.

Verification:

- Run targeted searches:

```powershell
rg "shelter affiliation|account photo|people and agencies|preferre|uplaods" wallet_interface/ui/src
```

### ABBY2-020: Final Test And Handoff Checklist

Source notes: all

Tasks:

- [x] Run TypeScript build.
- [x] Run smoke tests.
- [x] Run visual capture tests.
- [x] Review screenshot output.
- [x] In the final response, include changed files.
- [x] In the final response, include commands run and whether they passed.
- [x] In the final response, include screenshot paths or a grouped screenshot inventory.
- [x] In the final response, answer these user questions:
  - What are the options in the contact type dropdown?
  - What photo file types are accepted?
  - Why is no thumbnail preview shown for photo/photo ID files?
  - Is assisted access shown only for shelter staff?
- [x] Note any production-security caveats, especially shelter PIN handling.

Acceptance criteria:

- The agent can prove the changes with build/test results and screenshots.
- The user gets direct answers to questions embedded in the notes.
- Any unimplemented or blocked item is clearly called out with the reason.

Verification commands:

```powershell
cd wallet_interface/ui
npm run build
npm run test:smoke
npm run test:visual
```

## Suggested Work Split For Multiple Agents

### Agent A: Existing UX And Copy

- [x] ABBY2-002
- [x] ABBY2-003
- [x] ABBY2-004
- [x] ABBY2-005
- [x] ABBY2-006
- [x] ABBY2-007
- [x] ABBY2-019

### Agent B: Sharing, Uploads, And Persistence

- [x] ABBY2-008
- [x] ABBY2-009
- [x] ABBY2-010
- [x] ABBY2-017

### Agent C: Shelter Staff, Admin, And Client Accounts

- [x] ABBY2-011
- [x] ABBY2-012
- [x] ABBY2-013
- [x] ABBY2-014
- [x] ABBY2-015
- [x] ABBY2-016

### Agent D: Visual Polish And Verification

- [x] ABBY2-001
- [x] ABBY2-018
- [x] ABBY2-020

## Notes For The Implementation Agent

- The current app appears to be a mock/demo UI, so local state persistence is acceptable for prototype behavior. Do not represent client-side state as production security.
- Shelter staff and administrator PINs are sensitive. Mock PINs can exist for prototype workflows, but real PIN validation belongs on a server.
- The "health check" tag is sensitive. Keep its language supportive and avoid showing it to people who do not have shelter staff/admin authorization.
- Sharing-rule defaults should help users start from a reasonable baseline, but saved user changes must win over defaults.
- Screenshot requests are part of the deliverable, not an optional QA step.
