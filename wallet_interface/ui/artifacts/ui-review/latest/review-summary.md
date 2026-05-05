# Abby UI Multimodal Review

Generated: 2026-05-04T22:29:48.681347+00:00
Dry run: True
Entries: 75

## desktop · Two-card home screen

- Route: `/`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\home.png`
- State: `default`

### Goals

- Contacts and Sharing should be the only overview cards.
- The combined next check-in and Check in now action should live in Quick actions.
- The next check-in status should be easy to find without crowding the overview cards.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Two-card home screen
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\home.png

Goals:
- Contacts and Sharing should be the only overview cards.
- The combined next check-in and Check in now action should live in Quick actions.
- The next check-in status should be easy to find without crowding the overview cards.

## desktop · Registration flow

- Route: `/#/register`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\register.png`
- State: `empty`

### Goals

- Required fields should be obvious without feeling punitive.
- Optional sensitive fields should feel clearly optional.
- The photo or photo ID field should allow image files and PDFs without promising a thumbnail preview.
- The bot-check controls should be visible and understandable.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Registration flow
Viewport: desktop
State: empty
Screenshot: artifacts\ui-screenshots\latest\desktop\register.png

Goals:
- Required fields should be obvious without feeling punitive.
- Optional sensitive fields should feel clearly optional.
- The photo or photo ID field should allow image files and PDFs without promising a thumbnail preview.
- The bot-check controls should be visible and understandable.

## desktop · Registration flow with profile draft

- Route: `/#/register`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\register-filled.png`
- State: `filled form`

### Goals

- Filled required and optional fields should remain readable.
- The selected photo or photo ID file should be clear without showing an image or PDF thumbnail.
- Identity details should read as a separate group from later fill-in fields.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Registration flow with profile draft
Viewport: desktop
State: filled form
Screenshot: artifacts\ui-screenshots\latest\desktop\register-filled.png

Goals:
- Filled required and optional fields should remain readable.
- The selected photo or photo ID file should be clear without showing an image or PDF thumbnail.
- Identity details should read as a separate group from later fill-in fields.

## desktop · Registration unsupported photo or ID file

- Route: `/#/register`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\register-invalid-file.png`
- State: `unsupported file selected`

### Goals

- Unsupported file feedback should be clear and close to the file field.
- The form should not show a selected-file preview or thumbnail.
- The error state should not crowd required identity fields on mobile.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Registration unsupported photo or ID file
Viewport: desktop
State: unsupported file selected
Screenshot: artifacts\ui-screenshots\latest\desktop\register-invalid-file.png

Goals:
- Unsupported file feedback should be clear and close to the file field.
- The form should not show a selected-file preview or thumbnail.
- The error state should not crowd required identity fields on mobile.

## desktop · Check-in setup

- Route: `/#/check-in`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\check-in.png`
- State: `default`

### Goals

- The 30-day check-in limit should be clear.
- Reminder channels and next check-in date should be easy to scan.
- The primary check-in action should be reachable on mobile.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Check-in setup
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\check-in.png

Goals:
- The 30-day check-in limit should be clear.
- Reminder channels and next check-in date should be easy to scan.
- The primary check-in action should be reachable on mobile.

## desktop · Check-in setup at 30 days

- Route: `/#/check-in`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\check-in-maximum-interval.png`
- State: `30 day interval`

### Goals

- The longest allowed interval should still feel safe and understandable.
- The missed check-in help-step explanation should remain visible.
- The next check-in preview should update without visual confusion.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Check-in setup at 30 days
Viewport: desktop
State: 30 day interval
Screenshot: artifacts\ui-screenshots\latest\desktop\check-in-maximum-interval.png

Goals:
- The longest allowed interval should still feel safe and understandable.
- The missed check-in help-step explanation should remain visible.
- The next check-in preview should update without visual confusion.

## desktop · Check-in unavailable method warning

- Route: `/#/check-in`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\check-in-email-warning.png`
- State: `email check-in unavailable`

### Goals

- The warning should tell the user what to do next.
- Disabled or unavailable methods should be understandable without relying on color.
- Check-in controls should remain reachable after the warning appears.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Check-in unavailable method warning
Viewport: desktop
State: email check-in unavailable
Screenshot: artifacts\ui-screenshots\latest\desktop\check-in-email-warning.png

Goals:
- The warning should tell the user what to do next.
- Disabled or unavailable methods should be understandable without relying on color.
- Check-in controls should remain reachable after the warning appears.

## desktop · Emergency contacts

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\contacts.png`
- State: `default`

### Goals

- The add shelter or group area should be at the top of the screen.
- The add person form should show sharing choices before saving.
- Saved contacts should appear underneath the add controls and stay easy to scan.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\contacts.png

Goals:
- The add shelter or group area should be at the top of the screen.
- The add person form should show sharing choices before saving.
- Saved contacts should appear underneath the add controls and stay easy to scan.

## desktop · Emergency contacts add-recipient form

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\contacts-add-recipient-draft.png`
- State: `draft recipient`

### Goals

- The add-recipient form should be easy to complete on mobile.
- Contact method fields should fit and remain labeled.
- The new-person sharing checkboxes should be visible and readable before save.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts add-recipient form
Viewport: desktop
State: draft recipient
Screenshot: artifacts\ui-screenshots\latest\desktop\contacts-add-recipient-draft.png

Goals:
- The add-recipient form should be easy to complete on mobile.
- Contact method fields should fit and remain labeled.
- The new-person sharing checkboxes should be visible and readable before save.

## desktop · Emergency contacts add-recipient form with sharing off

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\contacts-add-person-sharing-some-off.png`
- State: `draft recipient with medical and housing sharing off`

### Goals

- Unchecked sharing choices should be visible without feeling scary.
- The form should still fit cleanly on mobile after several fields are filled.
- The user should be able to review choices before adding the person.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts add-recipient form with sharing off
Viewport: desktop
State: draft recipient with medical and housing sharing off
Screenshot: artifacts\ui-screenshots\latest\desktop\contacts-add-person-sharing-some-off.png

Goals:
- Unchecked sharing choices should be visible without feeling scary.
- The form should still fit cleanly on mobile after several fields are filled.
- The user should be able to review choices before adding the person.

## desktop · Emergency contacts edit sharing panel

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\contacts-edit-sharing.png`
- State: `saved contact sharing editor open`

### Goals

- A saved contact should open into an obvious sharing edit panel.
- Checkboxes should have a clear group heading and readable labels.
- Save and cancel actions should be reachable without horizontal scrolling.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts edit sharing panel
Viewport: desktop
State: saved contact sharing editor open
Screenshot: artifacts\ui-screenshots\latest\desktop\contacts-edit-sharing.png

Goals:
- A saved contact should open into an obvious sharing edit panel.
- Checkboxes should have a clear group heading and readable labels.
- Save and cancel actions should be reachable without horizontal scrolling.

## desktop · Emergency contacts edit sharing panel with choices off

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\contacts-edit-sharing-some-off.png`
- State: `saved contact medical and housing sharing off`

### Goals

- Unchecked saved-contact sharing choices should be visually clear.
- The selected-count badge should update near the panel heading.
- The edit panel should remain compact enough for mobile review.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts edit sharing panel with choices off
Viewport: desktop
State: saved contact medical and housing sharing off
Screenshot: artifacts\ui-screenshots\latest\desktop\contacts-edit-sharing-some-off.png

Goals:
- Unchecked saved-contact sharing choices should be visually clear.
- The selected-count badge should update near the panel heading.
- The edit panel should remain compact enough for mobile review.

## desktop · Sharing compatibility route

- Route: `/#/sharing-rules`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\sharing-rules.png`
- State: `saved contact sharing editor open`

### Goals

- The old Sharing route should lead to the combined contacts and sharing screen.
- A saved contact should own its sharing-rule settings.
- The capability preview should stay visible inside the contact edit panel.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Sharing compatibility route
Viewport: desktop
State: saved contact sharing editor open
Screenshot: artifacts\ui-screenshots\latest\desktop\sharing-rules.png

Goals:
- The old Sharing route should lead to the combined contacts and sharing screen.
- A saved contact should own its sharing-rule settings.
- The capability preview should stay visible inside the contact edit panel.

## desktop · Sharing compatibility route with items turned off

- Route: `/#/sharing-rules`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\sharing-rules-some-items-off.png`
- State: `saved contact medical and housing sharing off`

### Goals

- Unchecked items should be visually clear but not alarming.
- The preview should update to plain item names after choices change.
- The compatibility route should avoid a second conflicting sharing editor.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Sharing compatibility route with items turned off
Viewport: desktop
State: saved contact medical and housing sharing off
Screenshot: artifacts\ui-screenshots\latest\desktop\sharing-rules-some-items-off.png

Goals:
- Unchecked items should be visually clear but not alarming.
- The preview should update to plain item names after choices change.
- The compatibility route should avoid a second conflicting sharing editor.

## desktop · Emergency contacts after shelter nudge approval

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\contacts-shelter-nudge-approved.png`
- State: `shelter nudge approved`

### Goals

- Approving a shelter nudge should add the shelter without implying broad sharing.
- The added shelter should be easy to find in the saved contacts list below the add controls.
- The request history should remain understandable after approval.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts after shelter nudge approval
Viewport: desktop
State: shelter nudge approved
Screenshot: artifacts\ui-screenshots\latest\desktop\contacts-shelter-nudge-approved.png

Goals:
- Approving a shelter nudge should add the shelter without implying broad sharing.
- The added shelter should be easy to find in the saved contacts list below the add controls.
- The request history should remain understandable after approval.

## desktop · Saved files and info

- Route: `/#/uploads`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\uploads.png`
- State: `default`

### Goals

- Upload affordance should work for camera/mobile and desktop file upload.
- Private versus sharing-eligible status should be visually distinct.
- The vault should not show or ask for a document sensitivity level.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Saved files and info
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\uploads.png

Goals:
- Upload affordance should work for camera/mobile and desktop file upload.
- Private versus sharing-eligible status should be visually distinct.
- The vault should not show or ask for a document sensitivity level.

## desktop · Saved files after adding a document

- Route: `/#/uploads`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\uploads-new-file.png`
- State: `new file added`

### Goals

- The newly added file should be visible without exposing document contents.
- Private versus share-eligible status should remain easy to scan.
- The upload area should still be available after a file is added.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Saved files after adding a document
Viewport: desktop
State: new file added
Screenshot: artifacts\ui-screenshots\latest\desktop\uploads-new-file.png

Goals:
- The newly added file should be visible without exposing document contents.
- Private versus share-eligible status should remain easy to scan.
- The upload area should still be available after a file is added.

## desktop · Social services

- Route: `/#/social-services`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\social-services.png`
- State: `default`

### Goals

- Service categories should be dense enough to scan but not cramped.
- The government-services help entry point should be visible.
- Matched services should be easy to compare on mobile and desktop.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Social services
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\social-services.png

Goals:
- Service categories should be dense enough to scan but not cramped.
- The government-services help entry point should be visible.
- Matched services should be easy to compare on mobile and desktop.

## desktop · Shelter portal

- Route: `/#/shelter`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\shelter.png`
- State: `default`

### Goals

- Shelter staff workflows should feel separate from personal account controls.
- Shared-device safety should be explicit.
- The portal should support low-bandwidth, repeated-use contexts.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Shelter portal
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\shelter.png

Goals:
- Shelter staff workflows should feel separate from personal account controls.
- Shared-device safety should be explicit.
- The portal should support low-bandwidth, repeated-use contexts.

## desktop · Shelter portal shared-device checklist

- Route: `/#/shelter`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\shelter-shared-device-checklist.png`
- State: `safety checklist checked`

### Goals

- Checked safety steps should be visually clear.
- Staff audit responsibility should remain visible.
- The workflow should still feel usable on a shared device.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Shelter portal shared-device checklist
Viewport: desktop
State: safety checklist checked
Screenshot: artifacts\ui-screenshots\latest\desktop\shelter-shared-device-checklist.png

Goals:
- Checked safety steps should be visually clear.
- Staff audit responsibility should remain visible.
- The workflow should still feel usable on a shared device.

## desktop · Shelter portal create-user draft

- Route: `/#/shelter`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\shelter-create-user-draft.png`
- State: `staff-created user draft`

### Goals

- Staff-created user fields should stay separate from shared-device safety controls.
- Photo or ID PDF support should be clear without a preview.
- Contact reminder helper copy should remain readable in the staff flow.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Shelter portal create-user draft
Viewport: desktop
State: staff-created user draft
Screenshot: artifacts\ui-screenshots\latest\desktop\shelter-create-user-draft.png

Goals:
- Staff-created user fields should stay separate from shared-device safety controls.
- Photo or ID PDF support should be clear without a preview.
- Contact reminder helper copy should remain readable in the staff flow.

## desktop · Emergency recipient access

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\recipient-access.png`
- State: `unverified`

### Goals

- Sensitive data should be hidden before verification.
- Recipient verification should be prominent and clear.
- The screen should be usable in the field on a phone.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency recipient access
Viewport: desktop
State: unverified
Screenshot: artifacts\ui-screenshots\latest\desktop\recipient-access.png

Goals:
- Sensitive data should be hidden before verification.
- Recipient verification should be prominent and clear.
- The screen should be usable in the field on a phone.

## desktop · Emergency recipient access after verification

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\recipient-access-verified.png`
- State: `verified`

### Goals

- Authorized disclosure scopes should be obvious after verification.
- The screen should not expose unrelated wallet data.
- The next action for contacting support should be clear.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency recipient access after verification
Viewport: desktop
State: verified
Screenshot: artifacts\ui-screenshots\latest\desktop\recipient-access-verified.png

Goals:
- Authorized disclosure scopes should be obvious after verification.
- The screen should not expose unrelated wallet data.
- The next action for contacting support should be clear.

## desktop · Recipient access ready for approval

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\recipient-access-approval-ready.png`
- State: `second approval recorded`

### Goals

- The request should clearly show that enough approvals are recorded.
- Approve and reject actions should remain easy to distinguish.
- Capability language should stay understandable before sharing starts.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Recipient access ready for approval
Viewport: desktop
State: second approval recorded
Screenshot: artifacts\ui-screenshots\latest\desktop\recipient-access-approval-ready.png

Goals:
- The request should clearly show that enough approvals are recorded.
- Approve and reject actions should remain easy to distinguish.
- Capability language should stay understandable before sharing starts.

## desktop · Recipient access active grant

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\recipient-access-active-grant.png`
- State: `grant approved`

### Goals

- Approved access should be visually distinct from pending requests.
- The revoke action should be visible without overpowering the receipt details.
- Sharing history should show the approved grant clearly.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Recipient access active grant
Viewport: desktop
State: grant approved
Screenshot: artifacts\ui-screenshots\latest\desktop\recipient-access-active-grant.png

Goals:
- Approved access should be visually distinct from pending requests.
- The revoke action should be visible without overpowering the receipt details.
- Sharing history should show the approved grant clearly.

## desktop · Recipient access revoked grant

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\recipient-access-grant-revoked.png`
- State: `grant revoked`

### Goals

- Revoked access should be obvious without hiding the audit trail.
- The screen should explain that access is turned off.
- Receipt status should remain readable on mobile.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Recipient access revoked grant
Viewport: desktop
State: grant revoked
Screenshot: artifacts\ui-screenshots\latest\desktop\recipient-access-grant-revoked.png

Goals:
- Revoked access should be obvious without hiding the audit trail.
- The screen should explain that access is turned off.
- Receipt status should remain readable on mobile.

## desktop · Benefits protection consent

- Route: `/#/benefits-protection`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\benefits-protection.png`
- State: `default`

### Goals

- The benefits checkbox should start checked unless the user saved it as off.
- The user should be able to turn it off in plain language.
- The page should not describe benefits notices as missed-check-in triggered.
- Agency action should not be implied as guaranteed.
- Legal/policy review limitations should be visible without overwhelming the user.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Benefits protection consent
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\benefits-protection.png

Goals:
- The benefits checkbox should start checked unless the user saved it as off.
- The user should be able to turn it off in plain language.
- The page should not describe benefits notices as missed-check-in triggered.
- Agency action should not be implied as guaranteed.
- Legal/policy review limitations should be visible without overwhelming the user.

## desktop · Benefits protection consent enabled

- Route: `/#/benefits-protection`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\benefits-protection-enabled.png`
- State: `checked`

### Goals

- The checked consent state should be visually explicit.
- Benefits notice copy should stay focused on benefits help, not missed check-ins.
- Legal and policy limitations should remain visible after consent is on.
- The save action should become available without implying guaranteed agency action.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Benefits protection consent enabled
Viewport: desktop
State: checked
Screenshot: artifacts\ui-screenshots\latest\desktop\benefits-protection-enabled.png

Goals:
- The checked consent state should be visually explicit.
- Benefits notice copy should stay focused on benefits help, not missed check-ins.
- Legal and policy limitations should remain visible after consent is on.
- The save action should become available without implying guaranteed agency action.

## desktop · Benefits protection consent off

- Route: `/#/benefits-protection`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\benefits-protection-off.png`
- State: `unchecked`

### Goals

- Turning benefits help off should be visibly clear.
- The copy should still avoid promising agency action.
- The privacy/legal review caveat should remain visible.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Benefits protection consent off
Viewport: desktop
State: unchecked
Screenshot: artifacts\ui-screenshots\latest\desktop\benefits-protection-off.png

Goals:
- Turning benefits help off should be visibly clear.
- The copy should still avoid promising agency action.
- The privacy/legal review caveat should remain visible.

## desktop · Group facts choice

- Route: `/#/analytics`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\analytics.png`
- State: `default`

### Goals

- Group facts choices should start checked unless the user saved them as off.
- The user should be able to turn off each available choice in plain language.
- Safe detail badges should be clearly separated from personal records.
- Group size and privacy-left limits should be understandable.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Group facts choice
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\analytics.png

Goals:
- Group facts choices should start checked unless the user saved them as off.
- The user should be able to turn off each available choice in plain language.
- Safe detail badges should be clearly separated from personal records.
- Group size and privacy-left limits should be understandable.

## desktop · Group facts selected study

- Route: `/#/analytics`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\analytics-consented.png`
- State: `one choice on`

### Goals

- The selected choice should be visually distinct from paused or available choices.
- Safe detail badges should remain visible after consent is on.
- Privacy-left and group-size limits should stay prominent.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Group facts selected study
Viewport: desktop
State: one choice on
Screenshot: artifacts\ui-screenshots\latest\desktop\analytics-consented.png

Goals:
- The selected choice should be visually distinct from paused or available choices.
- Safe detail badges should remain visible after consent is on.
- Privacy-left and group-size limits should stay prominent.

## desktop · Group facts choice with one option off

- Route: `/#/analytics`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\analytics-one-choice-off.png`
- State: `one choice off`

### Goals

- The off choice should be visually clear without making the user feel punished.
- Available and paused choices should remain easy to compare.
- Group size and privacy-left labels should remain visible.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Group facts choice with one option off
Viewport: desktop
State: one choice off
Screenshot: artifacts\ui-screenshots\latest\desktop\analytics-one-choice-off.png

Goals:
- The off choice should be visually clear without making the user feel punished.
- Available and paused choices should remain easy to compare.
- Group size and privacy-left labels should remain visible.

## desktop · Proof center

- Route: `/#/proof-center`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\proof-center.png`
- State: `default`

### Goals

- Proof creation controls should not imply private data is shown.
- Public proof inputs should be scannable.
- API-required state should be clear but not alarming.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Proof center
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\proof-center.png

Goals:
- Proof creation controls should not imply private data is shown.
- Public proof inputs should be scannable.
- API-required state should be clear but not alarming.

## desktop · Export center

- Route: `/#/exports`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\exports.png`
- State: `default`

### Goals

- Export bundle creation should communicate that records stay encrypted.
- Recipient and record fields should fit on mobile.
- Existing export status should be easy to scan.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Export center
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\exports.png

Goals:
- Export bundle creation should communicate that records stay encrypted.
- Recipient and record fields should fit on mobile.
- Existing export status should be easy to scan.

## desktop · Security settings

- Route: `/#/security`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\security.png`
- State: `default`

### Goals

- Security preferences should read as saved settings, not temporary reveal controls.
- Shared-device guidance should be visible without exposing sensitive data.
- Bot check copy should make prototype limits clear.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Security settings
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\security.png

Goals:
- Security preferences should read as saved settings, not temporary reveal controls.
- Shared-device guidance should be visible without exposing sensitive data.
- Bot check copy should make prototype limits clear.

## desktop · Security settings with wallet persistence

- Route: `/#/security`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\security-customized.png`
- State: `default wallet safety tools`

### Goals

- The layout should remain easy to scan on mobile.
- Wallet backup controls should not imply local-only preferences are production enforcement.
- Security tool tiles should be understandable without extra instructions.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Security settings with wallet persistence
Viewport: desktop
State: default wallet safety tools
Screenshot: artifacts\ui-screenshots\latest\desktop\security-customized.png

Goals:
- The layout should remain easy to scan on mobile.
- Wallet backup controls should not imply local-only preferences are production enforcement.
- Security tool tiles should be understandable without extra instructions.

## desktop · Audit history

- Route: `/#/audit`
- Screenshot: `artifacts\ui-screenshots\latest\desktop\audit.png`
- State: `default`

### Goals

- Consent and access history should be easy to scan.
- Audit entries should show actor and timestamp clearly.
- The screen should not expose more sensitive detail than needed.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Audit history
Viewport: desktop
State: default
Screenshot: artifacts\ui-screenshots\latest\desktop\audit.png

Goals:
- Consent and access history should be easy to scan.
- Audit entries should show actor and timestamp clearly.
- The screen should not expose more sensitive detail than needed.

## mobile · Two-card home screen

- Route: `/`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\home.png`
- State: `default`

### Goals

- Contacts and Sharing should be the only overview cards.
- The combined next check-in and Check in now action should live in Quick actions.
- The next check-in status should be easy to find without crowding the overview cards.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Two-card home screen
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\home.png

Goals:
- Contacts and Sharing should be the only overview cards.
- The combined next check-in and Check in now action should live in Quick actions.
- The next check-in status should be easy to find without crowding the overview cards.

## mobile · Mobile navigation menu

- Route: `/`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\mobile-navigation-open.png`
- State: `menu open`

### Goals

- The menu should expose all major routes without crowding.
- The current route should be visually indicated.
- Navigation labels should be clear enough for repeated mobile use.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Mobile navigation menu
Viewport: mobile
State: menu open
Screenshot: artifacts\ui-screenshots\latest\mobile\mobile-navigation-open.png

Goals:
- The menu should expose all major routes without crowding.
- The current route should be visually indicated.
- Navigation labels should be clear enough for repeated mobile use.

## mobile · Registration flow

- Route: `/#/register`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\register.png`
- State: `empty`

### Goals

- Required fields should be obvious without feeling punitive.
- Optional sensitive fields should feel clearly optional.
- The photo or photo ID field should allow image files and PDFs without promising a thumbnail preview.
- The bot-check controls should be visible and understandable.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Registration flow
Viewport: mobile
State: empty
Screenshot: artifacts\ui-screenshots\latest\mobile\register.png

Goals:
- Required fields should be obvious without feeling punitive.
- Optional sensitive fields should feel clearly optional.
- The photo or photo ID field should allow image files and PDFs without promising a thumbnail preview.
- The bot-check controls should be visible and understandable.

## mobile · Registration flow with profile draft

- Route: `/#/register`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\register-filled.png`
- State: `filled form`

### Goals

- Filled required and optional fields should remain readable.
- The selected photo or photo ID file should be clear without showing an image or PDF thumbnail.
- Identity details should read as a separate group from later fill-in fields.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Registration flow with profile draft
Viewport: mobile
State: filled form
Screenshot: artifacts\ui-screenshots\latest\mobile\register-filled.png

Goals:
- Filled required and optional fields should remain readable.
- The selected photo or photo ID file should be clear without showing an image or PDF thumbnail.
- Identity details should read as a separate group from later fill-in fields.

## mobile · Registration unsupported photo or ID file

- Route: `/#/register`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\register-invalid-file.png`
- State: `unsupported file selected`

### Goals

- Unsupported file feedback should be clear and close to the file field.
- The form should not show a selected-file preview or thumbnail.
- The error state should not crowd required identity fields on mobile.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Registration unsupported photo or ID file
Viewport: mobile
State: unsupported file selected
Screenshot: artifacts\ui-screenshots\latest\mobile\register-invalid-file.png

Goals:
- Unsupported file feedback should be clear and close to the file field.
- The form should not show a selected-file preview or thumbnail.
- The error state should not crowd required identity fields on mobile.

## mobile · Check-in setup

- Route: `/#/check-in`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\check-in.png`
- State: `default`

### Goals

- The 30-day check-in limit should be clear.
- Reminder channels and next check-in date should be easy to scan.
- The primary check-in action should be reachable on mobile.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Check-in setup
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\check-in.png

Goals:
- The 30-day check-in limit should be clear.
- Reminder channels and next check-in date should be easy to scan.
- The primary check-in action should be reachable on mobile.

## mobile · Check-in setup at 30 days

- Route: `/#/check-in`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\check-in-maximum-interval.png`
- State: `30 day interval`

### Goals

- The longest allowed interval should still feel safe and understandable.
- The missed check-in help-step explanation should remain visible.
- The next check-in preview should update without visual confusion.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Check-in setup at 30 days
Viewport: mobile
State: 30 day interval
Screenshot: artifacts\ui-screenshots\latest\mobile\check-in-maximum-interval.png

Goals:
- The longest allowed interval should still feel safe and understandable.
- The missed check-in help-step explanation should remain visible.
- The next check-in preview should update without visual confusion.

## mobile · Check-in unavailable method warning

- Route: `/#/check-in`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\check-in-email-warning.png`
- State: `email check-in unavailable`

### Goals

- The warning should tell the user what to do next.
- Disabled or unavailable methods should be understandable without relying on color.
- Check-in controls should remain reachable after the warning appears.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Check-in unavailable method warning
Viewport: mobile
State: email check-in unavailable
Screenshot: artifacts\ui-screenshots\latest\mobile\check-in-email-warning.png

Goals:
- The warning should tell the user what to do next.
- Disabled or unavailable methods should be understandable without relying on color.
- Check-in controls should remain reachable after the warning appears.

## mobile · Emergency contacts

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\contacts.png`
- State: `default`

### Goals

- The add shelter or group area should be at the top of the screen.
- The add person form should show sharing choices before saving.
- Saved contacts should appear underneath the add controls and stay easy to scan.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\contacts.png

Goals:
- The add shelter or group area should be at the top of the screen.
- The add person form should show sharing choices before saving.
- Saved contacts should appear underneath the add controls and stay easy to scan.

## mobile · Emergency contacts add-recipient form

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\contacts-add-recipient-draft.png`
- State: `draft recipient`

### Goals

- The add-recipient form should be easy to complete on mobile.
- Contact method fields should fit and remain labeled.
- The new-person sharing checkboxes should be visible and readable before save.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts add-recipient form
Viewport: mobile
State: draft recipient
Screenshot: artifacts\ui-screenshots\latest\mobile\contacts-add-recipient-draft.png

Goals:
- The add-recipient form should be easy to complete on mobile.
- Contact method fields should fit and remain labeled.
- The new-person sharing checkboxes should be visible and readable before save.

## mobile · Emergency contacts add-recipient form with sharing off

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\contacts-add-person-sharing-some-off.png`
- State: `draft recipient with medical and housing sharing off`

### Goals

- Unchecked sharing choices should be visible without feeling scary.
- The form should still fit cleanly on mobile after several fields are filled.
- The user should be able to review choices before adding the person.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts add-recipient form with sharing off
Viewport: mobile
State: draft recipient with medical and housing sharing off
Screenshot: artifacts\ui-screenshots\latest\mobile\contacts-add-person-sharing-some-off.png

Goals:
- Unchecked sharing choices should be visible without feeling scary.
- The form should still fit cleanly on mobile after several fields are filled.
- The user should be able to review choices before adding the person.

## mobile · Emergency contacts edit sharing panel

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\contacts-edit-sharing.png`
- State: `saved contact sharing editor open`

### Goals

- A saved contact should open into an obvious sharing edit panel.
- Checkboxes should have a clear group heading and readable labels.
- Save and cancel actions should be reachable without horizontal scrolling.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts edit sharing panel
Viewport: mobile
State: saved contact sharing editor open
Screenshot: artifacts\ui-screenshots\latest\mobile\contacts-edit-sharing.png

Goals:
- A saved contact should open into an obvious sharing edit panel.
- Checkboxes should have a clear group heading and readable labels.
- Save and cancel actions should be reachable without horizontal scrolling.

## mobile · Emergency contacts edit sharing panel with choices off

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\contacts-edit-sharing-some-off.png`
- State: `saved contact medical and housing sharing off`

### Goals

- Unchecked saved-contact sharing choices should be visually clear.
- The selected-count badge should update near the panel heading.
- The edit panel should remain compact enough for mobile review.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts edit sharing panel with choices off
Viewport: mobile
State: saved contact medical and housing sharing off
Screenshot: artifacts\ui-screenshots\latest\mobile\contacts-edit-sharing-some-off.png

Goals:
- Unchecked saved-contact sharing choices should be visually clear.
- The selected-count badge should update near the panel heading.
- The edit panel should remain compact enough for mobile review.

## mobile · Sharing compatibility route

- Route: `/#/sharing-rules`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\sharing-rules.png`
- State: `saved contact sharing editor open`

### Goals

- The old Sharing route should lead to the combined contacts and sharing screen.
- A saved contact should own its sharing-rule settings.
- The capability preview should stay visible inside the contact edit panel.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Sharing compatibility route
Viewport: mobile
State: saved contact sharing editor open
Screenshot: artifacts\ui-screenshots\latest\mobile\sharing-rules.png

Goals:
- The old Sharing route should lead to the combined contacts and sharing screen.
- A saved contact should own its sharing-rule settings.
- The capability preview should stay visible inside the contact edit panel.

## mobile · Sharing compatibility route with items turned off

- Route: `/#/sharing-rules`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\sharing-rules-some-items-off.png`
- State: `saved contact medical and housing sharing off`

### Goals

- Unchecked items should be visually clear but not alarming.
- The preview should update to plain item names after choices change.
- The compatibility route should avoid a second conflicting sharing editor.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Sharing compatibility route with items turned off
Viewport: mobile
State: saved contact medical and housing sharing off
Screenshot: artifacts\ui-screenshots\latest\mobile\sharing-rules-some-items-off.png

Goals:
- Unchecked items should be visually clear but not alarming.
- The preview should update to plain item names after choices change.
- The compatibility route should avoid a second conflicting sharing editor.

## mobile · Emergency contacts after shelter nudge approval

- Route: `/#/contacts`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\contacts-shelter-nudge-approved.png`
- State: `shelter nudge approved`

### Goals

- Approving a shelter nudge should add the shelter without implying broad sharing.
- The added shelter should be easy to find in the saved contacts list below the add controls.
- The request history should remain understandable after approval.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency contacts after shelter nudge approval
Viewport: mobile
State: shelter nudge approved
Screenshot: artifacts\ui-screenshots\latest\mobile\contacts-shelter-nudge-approved.png

Goals:
- Approving a shelter nudge should add the shelter without implying broad sharing.
- The added shelter should be easy to find in the saved contacts list below the add controls.
- The request history should remain understandable after approval.

## mobile · Saved files and info

- Route: `/#/uploads`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\uploads.png`
- State: `default`

### Goals

- Upload affordance should work for camera/mobile and desktop file upload.
- Private versus sharing-eligible status should be visually distinct.
- The vault should not show or ask for a document sensitivity level.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Saved files and info
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\uploads.png

Goals:
- Upload affordance should work for camera/mobile and desktop file upload.
- Private versus sharing-eligible status should be visually distinct.
- The vault should not show or ask for a document sensitivity level.

## mobile · Saved files after adding a document

- Route: `/#/uploads`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\uploads-new-file.png`
- State: `new file added`

### Goals

- The newly added file should be visible without exposing document contents.
- Private versus share-eligible status should remain easy to scan.
- The upload area should still be available after a file is added.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Saved files after adding a document
Viewport: mobile
State: new file added
Screenshot: artifacts\ui-screenshots\latest\mobile\uploads-new-file.png

Goals:
- The newly added file should be visible without exposing document contents.
- Private versus share-eligible status should remain easy to scan.
- The upload area should still be available after a file is added.

## mobile · Social services

- Route: `/#/social-services`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\social-services.png`
- State: `default`

### Goals

- Service categories should be dense enough to scan but not cramped.
- The government-services help entry point should be visible.
- Matched services should be easy to compare on mobile and desktop.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Social services
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\social-services.png

Goals:
- Service categories should be dense enough to scan but not cramped.
- The government-services help entry point should be visible.
- Matched services should be easy to compare on mobile and desktop.

## mobile · Shelter portal

- Route: `/#/shelter`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\shelter.png`
- State: `default`

### Goals

- Shelter staff workflows should feel separate from personal account controls.
- Shared-device safety should be explicit.
- The portal should support low-bandwidth, repeated-use contexts.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Shelter portal
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\shelter.png

Goals:
- Shelter staff workflows should feel separate from personal account controls.
- Shared-device safety should be explicit.
- The portal should support low-bandwidth, repeated-use contexts.

## mobile · Shelter portal shared-device checklist

- Route: `/#/shelter`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\shelter-shared-device-checklist.png`
- State: `safety checklist checked`

### Goals

- Checked safety steps should be visually clear.
- Staff audit responsibility should remain visible.
- The workflow should still feel usable on a shared device.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Shelter portal shared-device checklist
Viewport: mobile
State: safety checklist checked
Screenshot: artifacts\ui-screenshots\latest\mobile\shelter-shared-device-checklist.png

Goals:
- Checked safety steps should be visually clear.
- Staff audit responsibility should remain visible.
- The workflow should still feel usable on a shared device.

## mobile · Shelter portal create-user draft

- Route: `/#/shelter`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\shelter-create-user-draft.png`
- State: `staff-created user draft`

### Goals

- Staff-created user fields should stay separate from shared-device safety controls.
- Photo or ID PDF support should be clear without a preview.
- Contact reminder helper copy should remain readable in the staff flow.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Shelter portal create-user draft
Viewport: mobile
State: staff-created user draft
Screenshot: artifacts\ui-screenshots\latest\mobile\shelter-create-user-draft.png

Goals:
- Staff-created user fields should stay separate from shared-device safety controls.
- Photo or ID PDF support should be clear without a preview.
- Contact reminder helper copy should remain readable in the staff flow.

## mobile · Emergency recipient access

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\recipient-access.png`
- State: `unverified`

### Goals

- Sensitive data should be hidden before verification.
- Recipient verification should be prominent and clear.
- The screen should be usable in the field on a phone.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency recipient access
Viewport: mobile
State: unverified
Screenshot: artifacts\ui-screenshots\latest\mobile\recipient-access.png

Goals:
- Sensitive data should be hidden before verification.
- Recipient verification should be prominent and clear.
- The screen should be usable in the field on a phone.

## mobile · Emergency recipient access after verification

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\recipient-access-verified.png`
- State: `verified`

### Goals

- Authorized disclosure scopes should be obvious after verification.
- The screen should not expose unrelated wallet data.
- The next action for contacting support should be clear.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Emergency recipient access after verification
Viewport: mobile
State: verified
Screenshot: artifacts\ui-screenshots\latest\mobile\recipient-access-verified.png

Goals:
- Authorized disclosure scopes should be obvious after verification.
- The screen should not expose unrelated wallet data.
- The next action for contacting support should be clear.

## mobile · Recipient access ready for approval

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\recipient-access-approval-ready.png`
- State: `second approval recorded`

### Goals

- The request should clearly show that enough approvals are recorded.
- Approve and reject actions should remain easy to distinguish.
- Capability language should stay understandable before sharing starts.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Recipient access ready for approval
Viewport: mobile
State: second approval recorded
Screenshot: artifacts\ui-screenshots\latest\mobile\recipient-access-approval-ready.png

Goals:
- The request should clearly show that enough approvals are recorded.
- Approve and reject actions should remain easy to distinguish.
- Capability language should stay understandable before sharing starts.

## mobile · Recipient access active grant

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\recipient-access-active-grant.png`
- State: `grant approved`

### Goals

- Approved access should be visually distinct from pending requests.
- The revoke action should be visible without overpowering the receipt details.
- Sharing history should show the approved grant clearly.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Recipient access active grant
Viewport: mobile
State: grant approved
Screenshot: artifacts\ui-screenshots\latest\mobile\recipient-access-active-grant.png

Goals:
- Approved access should be visually distinct from pending requests.
- The revoke action should be visible without overpowering the receipt details.
- Sharing history should show the approved grant clearly.

## mobile · Recipient access revoked grant

- Route: `/#/recipient-access`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\recipient-access-grant-revoked.png`
- State: `grant revoked`

### Goals

- Revoked access should be obvious without hiding the audit trail.
- The screen should explain that access is turned off.
- Receipt status should remain readable on mobile.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Recipient access revoked grant
Viewport: mobile
State: grant revoked
Screenshot: artifacts\ui-screenshots\latest\mobile\recipient-access-grant-revoked.png

Goals:
- Revoked access should be obvious without hiding the audit trail.
- The screen should explain that access is turned off.
- Receipt status should remain readable on mobile.

## mobile · Benefits protection consent

- Route: `/#/benefits-protection`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\benefits-protection.png`
- State: `default`

### Goals

- The benefits checkbox should start checked unless the user saved it as off.
- The user should be able to turn it off in plain language.
- The page should not describe benefits notices as missed-check-in triggered.
- Agency action should not be implied as guaranteed.
- Legal/policy review limitations should be visible without overwhelming the user.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Benefits protection consent
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\benefits-protection.png

Goals:
- The benefits checkbox should start checked unless the user saved it as off.
- The user should be able to turn it off in plain language.
- The page should not describe benefits notices as missed-check-in triggered.
- Agency action should not be implied as guaranteed.
- Legal/policy review limitations should be visible without overwhelming the user.

## mobile · Benefits protection consent enabled

- Route: `/#/benefits-protection`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\benefits-protection-enabled.png`
- State: `checked`

### Goals

- The checked consent state should be visually explicit.
- Benefits notice copy should stay focused on benefits help, not missed check-ins.
- Legal and policy limitations should remain visible after consent is on.
- The save action should become available without implying guaranteed agency action.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Benefits protection consent enabled
Viewport: mobile
State: checked
Screenshot: artifacts\ui-screenshots\latest\mobile\benefits-protection-enabled.png

Goals:
- The checked consent state should be visually explicit.
- Benefits notice copy should stay focused on benefits help, not missed check-ins.
- Legal and policy limitations should remain visible after consent is on.
- The save action should become available without implying guaranteed agency action.

## mobile · Benefits protection consent off

- Route: `/#/benefits-protection`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\benefits-protection-off.png`
- State: `unchecked`

### Goals

- Turning benefits help off should be visibly clear.
- The copy should still avoid promising agency action.
- The privacy/legal review caveat should remain visible.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Benefits protection consent off
Viewport: mobile
State: unchecked
Screenshot: artifacts\ui-screenshots\latest\mobile\benefits-protection-off.png

Goals:
- Turning benefits help off should be visibly clear.
- The copy should still avoid promising agency action.
- The privacy/legal review caveat should remain visible.

## mobile · Group facts choice

- Route: `/#/analytics`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\analytics.png`
- State: `default`

### Goals

- Group facts choices should start checked unless the user saved them as off.
- The user should be able to turn off each available choice in plain language.
- Safe detail badges should be clearly separated from personal records.
- Group size and privacy-left limits should be understandable.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Group facts choice
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\analytics.png

Goals:
- Group facts choices should start checked unless the user saved them as off.
- The user should be able to turn off each available choice in plain language.
- Safe detail badges should be clearly separated from personal records.
- Group size and privacy-left limits should be understandable.

## mobile · Group facts selected study

- Route: `/#/analytics`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\analytics-consented.png`
- State: `one choice on`

### Goals

- The selected choice should be visually distinct from paused or available choices.
- Safe detail badges should remain visible after consent is on.
- Privacy-left and group-size limits should stay prominent.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Group facts selected study
Viewport: mobile
State: one choice on
Screenshot: artifacts\ui-screenshots\latest\mobile\analytics-consented.png

Goals:
- The selected choice should be visually distinct from paused or available choices.
- Safe detail badges should remain visible after consent is on.
- Privacy-left and group-size limits should stay prominent.

## mobile · Group facts choice with one option off

- Route: `/#/analytics`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\analytics-one-choice-off.png`
- State: `one choice off`

### Goals

- The off choice should be visually clear without making the user feel punished.
- Available and paused choices should remain easy to compare.
- Group size and privacy-left labels should remain visible.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Group facts choice with one option off
Viewport: mobile
State: one choice off
Screenshot: artifacts\ui-screenshots\latest\mobile\analytics-one-choice-off.png

Goals:
- The off choice should be visually clear without making the user feel punished.
- Available and paused choices should remain easy to compare.
- Group size and privacy-left labels should remain visible.

## mobile · Proof center

- Route: `/#/proof-center`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\proof-center.png`
- State: `default`

### Goals

- Proof creation controls should not imply private data is shown.
- Public proof inputs should be scannable.
- API-required state should be clear but not alarming.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Proof center
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\proof-center.png

Goals:
- Proof creation controls should not imply private data is shown.
- Public proof inputs should be scannable.
- API-required state should be clear but not alarming.

## mobile · Export center

- Route: `/#/exports`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\exports.png`
- State: `default`

### Goals

- Export bundle creation should communicate that records stay encrypted.
- Recipient and record fields should fit on mobile.
- Existing export status should be easy to scan.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Export center
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\exports.png

Goals:
- Export bundle creation should communicate that records stay encrypted.
- Recipient and record fields should fit on mobile.
- Existing export status should be easy to scan.

## mobile · Security settings

- Route: `/#/security`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\security.png`
- State: `default`

### Goals

- Security preferences should read as saved settings, not temporary reveal controls.
- Shared-device guidance should be visible without exposing sensitive data.
- Bot check copy should make prototype limits clear.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Security settings
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\security.png

Goals:
- Security preferences should read as saved settings, not temporary reveal controls.
- Shared-device guidance should be visible without exposing sensitive data.
- Bot check copy should make prototype limits clear.

## mobile · Security settings with wallet persistence

- Route: `/#/security`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\security-customized.png`
- State: `default wallet safety tools`

### Goals

- The layout should remain easy to scan on mobile.
- Wallet backup controls should not imply local-only preferences are production enforcement.
- Security tool tiles should be understandable without extra instructions.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Security settings with wallet persistence
Viewport: mobile
State: default wallet safety tools
Screenshot: artifacts\ui-screenshots\latest\mobile\security-customized.png

Goals:
- The layout should remain easy to scan on mobile.
- Wallet backup controls should not imply local-only preferences are production enforcement.
- Security tool tiles should be understandable without extra instructions.

## mobile · Audit history

- Route: `/#/audit`
- Screenshot: `artifacts\ui-screenshots\latest\mobile\audit.png`
- State: `default`

### Goals

- Consent and access history should be easy to scan.
- Audit entries should show actor and timestamp clearly.
- The screen should not expose more sensitive detail than needed.

### Feedback

DRY RUN: router call skipped.

This target is ready for multimodal review.

Screen: Audit history
Viewport: mobile
State: default
Screenshot: artifacts\ui-screenshots\latest\mobile\audit.png

Goals:
- Consent and access history should be easy to scan.
- Audit entries should show actor and timestamp clearly.
- The screen should not expose more sensitive detail than needed.
