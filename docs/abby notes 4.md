# Abby Notes 4: Detailed Agent Todo List

Last updated: 2026-05-04

Source: informal Abby UI notes from the user.

## Goal

Turn Abby Notes 4 into an implementation-ready backlog for an agent working in `wallet_interface/ui`.

These notes mainly refine the emergency contacts and sharing-rules experience. Treat this file as the latest product direction for contacts and sharing. It should be implemented together with the Notes 3 behavior that sharing-rule boxes start checked by default unless the user unchecks and saves them.

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

- Emergency contacts should let the user add a shelter or group at the top.
- Saved people/contacts should appear underneath, near the bottom of the contacts section.
- Contacts and sharing rules should be combined into one flow.
- Clicking a saved person should let the user edit that person's sharing rules.
- Adding a new person should show sharing-rule checkboxes immediately, so the user can uncheck anything they do not want to share.
- Sharing-rule copy under "Minimum identity" must say exactly: `name, birthdate and contact status`.
- The benefits notice page must not mention missed check-ins.

## Agent Working Rules

- Inspect current behavior before editing because earlier Notes 2 and Notes 3 work may already be partially implemented.
- Keep sharing-rule choices persistent. Saved unchecked boxes must stay unchecked after route changes and refresh.
- Keep all sensitive sharing choices explicit and reviewable.
- Use simple user-facing copy consistent with the Notes 3 third-grade reading-level direction.
- Make every contact row, edit action, checkbox, and add flow keyboard accessible.
- Avoid nested interactive elements. A clickable contact row should not contain another uncoordinated clickable button unless the markup is accessible.
- Run build, smoke tests, and visual capture after implementation.

## Priority Order

1. Rework the contacts screen structure so add shelter/group is at the top and saved people appear below.
2. Combine contacts and sharing rules into one editable contacts flow.
3. Add sharing-rule checkboxes to the add-person/add-recipient flow.
4. Update exact sharing-rule copy for Minimum identity.
5. Remove missed-check-in language from the benefits notice page.
6. Update tests, screenshots, and final handoff.

## Detailed Todo Backlog

### ABBY4-001: Emergency Contacts Layout Reorder

Source note: 1

Tasks:

- [x] Locate the emergency contacts or contacts route.
- [x] Identify the current add-recipient form, saved contacts list, and any shelter/group contact controls.
- [x] Move or add an "Add shelter or group" section to the top of the emergency contacts screen.
- [x] Keep this shelter/group add section visually distinct from adding an individual person.
- [x] Place the saved people/contacts list underneath the add shelter/group area.
- [x] If there is also an add-person form, decide whether it belongs directly under add shelter/group or inside the same top add area.
- [x] Ensure previously inputted people appear below the add controls.
- [x] Keep saved contacts easy to scan on mobile.
- [x] Preserve existing edit, delete, verification, and status behavior for saved contacts.
- [x] Make sure the contacts page still works if there are no saved people yet.

Acceptance criteria:

- The top of the emergency contacts screen lets the user add a shelter or group.
- Saved people the user already entered appear underneath the add area.
- Empty-state text is clear if no contacts exist yet.
- Layout works on mobile and desktop without horizontal scrolling.
- Existing saved contact actions still work.

Verification:

- Inspect desktop and mobile contacts screenshots.
- Smoke-test adding a shelter/group and confirming saved people remain visible below.

### ABBY4-002: Combine Contacts And Sharing Rules Into One Flow

Source note: 2

Tasks:

- [x] Locate the standalone sharing-rules route and UI.
- [x] Locate recipient/contact data state and allowed sharing scopes.
- [x] Design the contacts screen so each saved person/group/shelter owns its sharing-rule settings.
- [x] When a user clicks a saved person, open an edit view, inline panel, drawer, or modal for that contact.
- [x] The contact edit view must include that contact's sharing-rule checkboxes.
- [x] Let users change sharing rules for that contact from the contact edit view.
- [x] Persist changes when the user saves.
- [x] Decide what should happen to the old Sharing navigation item:
  - Preferred prototype path: keep a route for compatibility, but redirect or route it to the combined contacts/sharing screen.
  - If the app still needs a Sharing button from Notes 3 dashboard, make it open the contacts screen focused on sharing settings.
- [x] Avoid duplicate, conflicting sharing-rule UIs.
- [x] Update copy so users understand sharing choices live inside each contact.
- [x] Keep sharing-rule defaults from Notes 3: all options start checked when no saved choice exists.
- [x] Keep saved unchecked choices unchanged when reopening a contact.

Acceptance criteria:

- Users can edit sharing rules by clicking an existing saved person/contact.
- Users do not need to visit a separate sharing page to change a contact's sharing settings.
- Existing sharing route/nav does not break; it leads users to the combined contacts/sharing experience or an intentional compatibility state.
- Sharing choices persist per contact.
- No duplicate UI creates conflicting saved values.

Verification:

- Smoke-test clicking a saved contact, unchecking scopes, saving, refreshing, and reopening the same contact.
- Smoke-test the old sharing route or dashboard Sharing button.
- Inspect contacts and sharing screenshots.

### ABBY4-003: Add Sharing Checkboxes During New Person Creation

Source note: 2

Tasks:

- [x] Locate the add-recipient/add-person form.
- [x] Add sharing-rule checkboxes directly into the new person form.
- [x] Show the same sharing scopes used for saved contact editing.
- [x] Default every sharing checkbox to checked for a new person, consistent with Notes 3.
- [x] Let the user uncheck any sharing scope before saving the new person.
- [x] Save the new person with the selected sharing scopes.
- [x] After saving, show the new person in the saved contacts list with their sharing choices available for editing.
- [x] If adding a shelter or group uses a different form, include equivalent sharing-rule controls there too unless product requires a different path.
- [x] Make checkbox labels simple and readable.
- [x] If many sharing scopes create a long form, group them with a compact heading and avoid overwhelming the screen.

Acceptance criteria:

- New people can be created with sharing choices in the same form.
- All sharing boxes start checked for a brand-new contact.
- If the user unchecks boxes before saving, those unchecked choices are saved.
- The new contact's edit view shows the same saved choices.
- The form remains usable on mobile.

Verification:

- Smoke-test adding a new person with all scopes checked.
- Smoke-test adding a new person after unchecking several scopes.
- Confirm saved choices persist after refresh.

### ABBY4-004: Exact Minimum Identity Copy Change

Source note: 3

Tasks:

- [x] Locate the `Minimum identity` sharing scope definition or copy.
- [x] Change the helper/detail text from `name, birthdate, and contact status` to `name, birthdate and contact status`.
- [x] Ensure this exact copy appears anywhere the Minimum identity detail is shown, including add-person and edit-contact sharing controls.
- [x] Do not change the scope label unless necessary.
- [x] Search for older copy variants and update user-facing instances.

Acceptance criteria:

- Minimum identity detail says exactly: `name, birthdate and contact status`.
- No user-facing sharing-rule detail still says `name, birthdate, and contact status`.
- TypeScript build passes.

Verification:

```powershell
rg "name, birthdate, and contact status|name, birthdate and contact status" wallet_interface/ui/src
```

### ABBY4-005: Remove Missed Check-In Language From Benefits Notice

Source note: 4

Tasks:

- [x] Locate the benefits opt-in/benefits notice page.
- [x] Search for missed-check-in language on that page.
- [x] Remove mentions of missed check-ins from the benefits notice page.
- [x] Replace removed text with benefits-specific language if the page needs context.
- [x] Avoid implying benefits notices are triggered by missed check-ins.
- [x] Keep any missed-check-in sharing scope available elsewhere if Notes 2/3 already require it.
- [x] Confirm missed-check-in wording is removed only from the benefits notice page, not from the check-in or sharing-rule areas where it may still be relevant.

Acceptance criteria:

- Benefits notice page does not mention missed check-ins.
- Benefits copy remains clear about what benefits opt-in does.
- Check-in and sharing-rule pages keep any required missed-check-in behavior.

Verification:

```powershell
rg "missed check|missed-check|check-in" wallet_interface/ui/src/app wallet_interface/ui/src/components wallet_interface/ui/src/services
```

Manually inspect only the benefits notice result locations to confirm missed-check-in wording is gone there.

### ABBY4-006: Combined Contacts And Sharing Persistence Audit

Source notes: 1, 2

Tasks:

- [x] Audit contact state shape for people, shelters, groups, and sharing scopes.
- [x] Confirm every recipient/contact has a stable ID.
- [x] Confirm allowed sharing scopes are stored per contact.
- [x] Confirm add, edit, delete, and reorder actions do not wipe sharing scopes.
- [x] Confirm defaults apply only when creating a new contact or opening a contact with no saved choices.
- [x] Confirm unchecked saved choices stay unchecked after save, route change, and browser refresh.
- [x] Confirm deleting a contact removes or ignores its sharing rules without affecting other contacts.
- [x] Confirm staff/shelter contact requests, if implemented from Notes 3, produce contacts that can be edited in the combined flow.

Acceptance criteria:

- Contact and sharing state remains consistent after all common contact actions.
- Sharing choices are attached to the correct contact.
- No contact action accidentally resets all sharing scopes.
- Browser refresh preserves saved sharing choices.

Verification:

- Add smoke coverage for add, edit sharing, delete, and refresh.
- Manually test at least one person contact and one shelter/group contact.

### ABBY4-007: Accessibility And Mobile Usability For Combined Flow

Source notes: 1, 2

Tasks:

- [x] Ensure saved contact rows are keyboard reachable.
- [x] Ensure pressing Enter or Space opens the contact edit/sharing panel.
- [x] Give contact edit panels, drawers, or modals accessible names.
- [x] Ensure checkbox groups have a readable legend or heading.
- [x] Ensure the add shelter/group section is announced clearly by screen readers.
- [x] Keep focus inside modal/drawer if one is used.
- [x] Return focus to the triggering contact row after closing an edit modal/drawer.
- [x] Ensure touch targets are at least 44px tall in core contact actions.
- [x] Confirm the combined contact/sharing flow does not require hover.

Acceptance criteria:

- Keyboard-only users can add a contact, open a saved contact, edit sharing choices, save, and close.
- Screen-reader labels describe the contact and sharing sections clearly.
- Mobile users can complete the flow without horizontal scrolling or clipped text.

Verification:

- Manual keyboard pass on the contacts screen.
- Inspect mobile contacts screenshot and any contact-edit interaction screenshot if available.

### ABBY4-008: Tests, Screenshots, And Final Handoff

Source notes: all

Tasks:

- [x] Run TypeScript build.
- [x] Run smoke tests.
- [x] Run visual capture tests.
- [x] Review contacts, sharing, and benefits screenshots.
- [x] Update visual capture tests if the combined contacts/sharing flow changes route expectations.
- [x] Update smoke tests for the combined contacts/sharing flow.
- [x] In final handoff, list changed files.
- [x] In final handoff, list commands run and pass/fail status.
- [x] In final handoff, list screenshot paths or grouped screenshot inventory.
- [x] In final handoff, mention that Notes 4 supersedes older separate contacts/sharing behavior.
- [x] In final handoff, note any intentionally retained compatibility route for Sharing.

Acceptance criteria:

- Build passes.
- Smoke tests pass or failures are explained.
- Visual capture passes or failures are explained.
- The final response makes the combined contacts/sharing behavior clear.
- Screenshot inventory includes proof of the updated contacts and benefits screens.

Verification commands:

```powershell
cd wallet_interface/ui
npm run build
npm run test:smoke
npm run test:visual
```

## Suggested Work Split For Multiple Agents

### Agent A: Contacts Layout And Add Flow

- ABBY4-001
- ABBY4-003
- ABBY4-007

### Agent B: Sharing Merge And Persistence

- ABBY4-002
- ABBY4-006

### Agent C: Copy, Benefits Cleanup, And QA

- ABBY4-004
- ABBY4-005
- ABBY4-008

## Notes For The Implementation Agent

- Treat Contacts as the new home for sharing-rule edits.
- Keep a compatibility path for the old Sharing route if tests, nav, or dashboard buttons still point to it.
- Sharing choices are sensitive. Even though Notes 3 says scopes default checked, saved user unchecks must always win.
- Benefits notice copy should focus only on benefits opt-in behavior and should not mention missed check-ins.
