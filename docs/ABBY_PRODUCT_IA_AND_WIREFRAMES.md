# Abby Product IA And Wireframe Notes

Last updated: 2026-05-04

Purpose: document the product information architecture, account boundary, and
mobile/desktop screen notes for Abby without requiring application code changes.

## Account Boundary

Pre-account actions must minimize sensitive collection and avoid implying that
emergency escalation is active before a wallet/session exists.

| Area | Pre-account allowed | Requires authenticated wallet/session |
| --- | --- | --- |
| First run | View plain-language product purpose, start registration, resume a local safe draft, choose shared-device safety mode | Persist profile, enable check-ins, save recipients, upload files, enable disclosures |
| Registration | Enter minimum identity fields, optional contact/service needs, complete CAPTCHA, save local draft | Create profile, bind wallet/session, store photo/document asset ids |
| Social services | Browse public service categories, start non-identifying liaison interest form if abuse-protected | Use derived profile needs, request matched services, share profile details with a liaison |
| Shelter | View shelter portal entry and shared-device guidance | Staff invite, assisted registration, role-based work queues, audited staff actions |
| Recipient access | Open token link, see expired/revoked/verification-required states | View scoped emergency package after token and identity verification |
| Agency/admin | None beyond public entry/help | Agency liaison queue, policy-reviewed notifications, admin audit/configuration |

## Sitemap

```text
Unauthenticated
  /register
    minimum identity
    optional contact and service needs
    CAPTCHA
    local save/resume
  /social-services/public
    public categories
    non-identifying liaison interest
  /shelter
    shelter portal entry
    shared-device safety prompts
  /recipient-access/:token
    token status
    recipient verification
    expired/revoked recovery

User wallet/session
  /
    Emergency contacts
    Social services
    check-in status
    setup progress
  /check-in
    interval
    reminders
    grace period
    one-tap check-in
  /contacts
    emergency contacts
    social workers
    police precincts
    agencies
    verification status
  /sharing-rules
    recipient scopes
    review and confirmation
    revocation
    history
  /uploads
    documents
    photos
    notes
    sharing eligibility
  /social-services
    categories
    matched services
    liaison requests
  /benefits-protection
    explicit opt-in
    legal/policy pending states
    consent and audit history
  /settings/security
    devices
    session timeout
    recovery
  /settings/audit
    consent receipts
    disclosure and staff action history

Shelter staff/session
  /shelter/dashboard
    role context
    client assistance queue
    low-bandwidth mode
  /shelter/assist-registration
    assisted registration
    contact verification
    user-controlled sharing review
  /shelter/admin
    staff roles
    audit prompts

Emergency recipient/session
  /recipient-access/:token
    verify recipient
    authorized package only
    next-step guidance
    link expiration and recovery

Agency/session
  /agency/liaison
    service request queue
    consent-scoped profile summary
  /agency/escalations
    reviewed notifications only

Admin/session
  /admin/policy-gates
    police, social worker, benefits, shelter, missing-person gate status
  /admin/audit
    production audit review
```

Everyday user routes are separated from emergency recipient and agency routes by
session type. Recipient and agency routes must never expose the user's wallet
navigation, unrelated uploads, unrelated contacts, or general account settings.

## Mobile Wireframe Notes

First-run:
- Single-column flow with shared-device prompt first when the app detects or is
  told it is running on a shelter/shared device.
- Primary actions: start registration, resume draft, browse social services.
- Keep emergency disclosure inactive until account creation, check-in policy,
  recipients, and sharing confirmation are complete.

Home:
- First viewport must contain exactly two primary cards, stacked in this order:
  "Emergency contacts" then "Social services".
- Below the two cards, show compact check-in status, setup tasks, disclosure
  review reminders, and stored upload count.
- Avoid exposing sensitive details on the home screen; use counts, status, and
  redacted labels.

Dashboard:
- Mobile dashboard is the lower portion of home, not a separate marketing page.
- Status blocks: next check-in, active recipients, active sharing rules,
  pending verifications, recent consent/audit event.
- Use progressive disclosure for anything sensitive.

Registration:
- Step order: shared-device safety, minimum identity, contact methods, optional
  support details, CAPTCHA, final create-profile confirmation.
- Minimum identity: legal name, birth date, photo or photo ID.
- Optional fields: preferred name, pronouns, email, phone, location, preferred
  shelter, social worker, starter emergency contact, service needs.
- Each field label/helper should state required/optional and why it is being
  requested.

Contacts:
- Add-recipient action appears before saved contacts.
- Recipient cards show type, verification state, access status, and authorized
  scope summary.
- Removing the last active recipient requires an explicit warning.

Social services:
- Categories: shelter, food, health, legal, benefits, transportation,
  employment, crisis support.
- Include "not sure what I need" guided intake.
- Matched services can use derived, consented profile needs only after session
  and consent exist.

Recipient access:
- Token landing first shows link state and verification requirements.
- Verified view shows only authorized scopes, expiration, revocation status, and
  next steps.
- Expired, revoked, already-used, and permission-denied states should provide
  safe support/recovery text without leaking account existence.

## Desktop Wireframe Notes

Dashboard:
- Preserve the two primary actions from mobile as the dominant left/top area.
- Use additional space for status, setup progress, and recent audit events.
- Do not add unrelated marketing or dense admin controls to the user dashboard.

Registration:
- Use a two-column layout only after the core step content remains readable:
  form on the left, explanation/review panel on the right.
- Keep the same mobile task order and keyboard order.
- Desktop upload supports file picker; mobile upload supports camera/library.

Contacts:
- Main column: add/edit recipient form and saved recipient list.
- Side panel: selected recipient's verification, authorized scopes, review
  reminder, and revocation status.
- Role/type options should include emergency contact, police precinct, social
  worker, shelter staff, government liaison, and benefits agency.

Social services:
- Left navigation or filter rail for categories on desktop.
- Main area lists matched or browsable services.
- Detail panel shows what profile-derived needs would be shared before any
  liaison request is submitted.

Recipient access:
- Narrow, task-focused layout even on desktop.
- Header shows emergency package status, verification state, and expiration.
- Body groups authorized data by scope with redacted/unavailable sections
  omitted, not disabled in place.

## Screen State Inventory

| Screen | Success | Empty | Loading | Error | Permission denied |
| --- | --- | --- | --- | --- | --- |
| First run | Start/resume available | No draft | Draft check | Draft unavailable | Shared-device restrictions |
| Home/dashboard | Status and actions | Setup not started | Profile/status sync | Sync failed | Session expired |
| Registration | Profile created | New draft | Save/create pending | CAPTCHA or validation failure | Existing session conflict |
| Contacts | Recipients listed | No recipients | Verification pending | Save/remove failed | Session expired |
| Social services | Categories/matches | No matches | Matching pending | Liaison request failed | Consent required |
| Recipient access | Scoped package shown | No scopes authorized | Verification pending | Token invalid | Expired/revoked/not verified |
| Shelter portal | Queue/actions shown | No assigned clients | Queue loading | Staff action failed | Role missing |

## Open Questions

- What jurisdiction is the first policy target?
- Is there a human review step before police, shelter, social worker, or agency
  notification?
- Which identity assurance level is required for each recipient type?
- Which service matching API supplies 211-derived categories and matches?
- Which email, SMS, CAPTCHA, and audit-log providers are canonical?
