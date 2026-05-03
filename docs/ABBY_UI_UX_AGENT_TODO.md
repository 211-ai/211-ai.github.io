# Abby UI/UX Agent Todo List

Last updated: 2026-05-02

Source reviewed: `docs/Abby Requirements.md`

## Goal

Design and implement a TypeScript-first responsive web/PWA experience for Abby:
a safety check-in, emergency disclosure, and social-services liaison product for
people who may need durable support, including people using homeless shelters.

The first UI target is a mobile-friendly experience that also works well on
desktop. The product should make the user's next action obvious, protect highly
sensitive personal information, and avoid exposing details unless the user has
explicitly chosen who can see them.

## Product Requirements Summary

- Collect a robust registration profile, with minimum required information:
  legal/preferred name, birth date, and photo.
- Add CAPTCHA or equivalent bot prevention during account registration and other
  abuse-prone public forms.
- Let users choose check-in reminders by email, text, and website/app check-in.
- Enforce a maximum check-in interval of one month before escalation, while
  allowing users to choose a shorter interval.
- Let users upload personal information and documents they choose to store.
- Let users define emergency contacts, agencies, police precincts, social
  workers, and other recipients.
- Let users choose what information each recipient or agency can access if the
  user misses check-ins.
- Send secure access links to selected recipients after the escalation policy is
  triggered.
- Provide a liaison entry point for additional government and social services.
- Provide free access for homeless shelters and shelter staff workflows.
- If a user explicitly opts into benefits-protection escalation, design a flow
  that can notify the correct Social Security contact to hold payment, subject
  to legal and policy review.
- The main mobile app screen should be simple: a top card labeled
  "Emergency contacts" and a second card labeled "Social services".

## Agent Constraints

- Use TypeScript for UI implementation work.
- Prefer a responsive web/PWA architecture unless the project later chooses a
  native app shell.
- Keep cryptography, UCAN authorization, storage, proof logic, and policy
  evaluation out of the UI layer. The UI should call wallet/app APIs.
- Treat profile, location, identity, emergency, shelter, benefits, and uploaded
  document data as highly sensitive.
- Do not design dark patterns around consent. Sharing, escalation, and agency
  disclosure must be explicit, reviewable, and revocable.
- Build for mobile first, then adapt to tablet and desktop.
- Meet WCAG 2.2 AA accessibility expectations for all core flows.

## Suggested TypeScript App Shape

Use this as the default if no frontend app exists yet:

```text
wallet_interface/ui/
  package.json
  tsconfig.json
  src/
    app/
    components/
    features/
      registration/
      checkIn/
      emergencyContacts/
      disclosureRules/
      documentVault/
      socialServices/
      shelterPortal/
      agencyAccess/
    models/
    services/
    styles/
    tests/
```

Suggested baseline stack:

- React + TypeScript for the UI.
- Vite for local development.
- CSS modules, Tailwind, or the repo's future design system for styling.
- Playwright for desktop/mobile UI smoke tests.
- Vitest or Jest for component and state tests.

## Domain Types Draft

Agents should refine these during implementation rather than treating them as
final API contracts.

```ts
export type CheckInChannel = "email" | "sms" | "web";

export type DisclosureRecipientType =
  | "emergency_contact"
  | "police_precinct"
  | "social_worker"
  | "shelter_staff"
  | "government_liaison"
  | "benefits_agency";

export type DisclosureDataScope =
  | "identity_minimum"
  | "profile"
  | "photo"
  | "current_location"
  | "uploaded_documents"
  | "medical_notes"
  | "shelter_history"
  | "benefits_information"
  | "custom";

export interface RegistrationProfileDraft {
  legalName: string;
  preferredName?: string;
  dateOfBirth: string;
  photoAssetId: string;
  phone?: string;
  email?: string;
  preferredCheckInChannels: CheckInChannel[];
  captchaToken: string;
}

export interface CheckInPolicyDraft {
  intervalDays: number;
  reminderChannels: CheckInChannel[];
  gracePeriodHours: number;
  escalationEnabled: boolean;
}

export interface DisclosureRecipientDraft {
  id: string;
  type: DisclosureRecipientType;
  displayName: string;
  email?: string;
  phone?: string;
  agencyName?: string;
  precinctName?: string;
  allowedScopes: DisclosureDataScope[];
}

export interface EscalationRuleDraft {
  checkInPolicyId: string;
  recipientIds: string[];
  secureLinkExpiresHours: number;
  requiresUserOptIn: true;
}
```

## Todo Backlog

### ABBY-001: Product Information Architecture

- [ ] Create a sitemap covering unauthenticated, user, shelter, emergency
  recipient, agency, and admin experiences.
- [ ] Define the primary navigation for mobile and desktop.
- [ ] Separate everyday user flows from emergency recipient and agency access
  flows.
- [ ] Define what can be completed before account creation and what requires an
  authenticated wallet/session.

Acceptance criteria:

- Sitemap includes registration, check-in, emergency contacts, social services,
  uploads, sharing rules, shelter access, recipient access link, and agency
  liaison flows.
- Mobile first screen includes exactly two primary cards:
  "Emergency contacts" and "Social services".
- Desktop layout preserves the same two primary actions while exposing secondary
  status and setup tasks without crowding the page.

### ABBY-002: Responsive Design System Foundation

- [ ] Create TypeScript-friendly UI primitives for buttons, inputs, cards,
  dialogs, steppers, banners, status indicators, and navigation.
- [ ] Define spacing, typography, color, focus, error, disabled, and loading
  states.
- [ ] Define mobile, tablet, and desktop breakpoints.
- [ ] Define sensitive-data display patterns, including redaction, reveal, and
  copy-disabled states where appropriate.

Acceptance criteria:

- Components are keyboard accessible and screen-reader labeled.
- Touch targets are at least 44px in core mobile flows.
- Error states include actionable recovery text.
- No core flow depends on hover-only interactions.

### ABBY-003: Registration UX

- [ ] Design and implement account registration screens.
- [ ] Collect minimum required fields: name, birth date, and photo.
- [ ] Add optional fields for email, phone, preferred name, location, shelter
  affiliation, social worker, emergency contact starter info, and service needs.
- [ ] Add CAPTCHA or an equivalent bot-protection placeholder integration.
- [ ] Explain why each sensitive field is requested and whether it is required.
- [ ] Add save-and-resume support for longer registration.

Acceptance criteria:

- User cannot complete registration without name, birth date, photo, and bot
  check completion.
- Optional fields are clearly optional.
- The UI supports mobile photo upload/capture and desktop file upload.
- The profile review screen lets the user confirm data before submission.

### ABBY-004: Check-In Setup UX

- [ ] Create a check-in setup flow for email, text, and web/app check-ins.
- [ ] Let users select a check-in interval from safe presets and a custom value.
- [ ] Enforce a maximum interval of 30 days.
- [ ] Add reminder schedule preview.
- [ ] Add missed-check-in grace period and escalation explanation.
- [ ] Add a one-tap check-in action after setup.

Acceptance criteria:

- Interval validation prevents values over 30 days.
- Users can choose shorter intervals.
- The next scheduled check-in date is visible.
- The one-tap check-in state works on mobile and desktop layouts.

### ABBY-005: Emergency Contacts UX

- [ ] Create the "Emergency contacts" main card and destination screen.
- [ ] Let users add emergency contacts by name, relationship, phone, and email.
- [ ] Let users add social workers, police precincts, and agencies as
  escalation recipients.
- [ ] Include verification states for contact methods.
- [ ] Show each recipient's access status and disclosure scope.

Acceptance criteria:

- Users can add, edit, remove, and reorder recipients.
- Each recipient clearly shows what they can access.
- The UI warns before removing the last active recipient.
- Mobile layout supports quick scanning without horizontal scrolling.

### ABBY-006: Disclosure Rules UX

- [ ] Build a sharing-rules flow that maps recipients to allowed data scopes.
- [ ] Provide plain-language scope labels for identity, photo, location,
  uploads, medical notes, shelter history, benefits information, and custom
  notes.
- [ ] Add review and confirmation before enabling emergency disclosure.
- [ ] Add revocation and history views.

Acceptance criteria:

- No recipient receives access by default.
- Users can grant different scopes to different recipients.
- Users can preview the information package for each recipient type.
- Every disclosure rule has an expiration or review reminder.

### ABBY-007: Document And Information Upload UX

- [ ] Create upload screens for user-chosen documents, photos, notes, and other
  information.
- [ ] Support mobile camera upload and desktop file upload.
- [ ] Let users categorize uploads and mark sensitivity.
- [ ] Show upload status, encryption/storage status placeholder, and sharing
  eligibility.
- [ ] Provide empty, loading, failed, and successful upload states.

Acceptance criteria:

- Users can upload at least one file from mobile and desktop flows.
- Uploaded items are not shared until the user explicitly includes them in a
  disclosure rule.
- The UI distinguishes stored items from shared items.
- Failed uploads have retry and remove actions.

### ABBY-008: Social Services UX

- [ ] Create the "Social services" main card and destination screen.
- [ ] Provide a government-services liaison entry point below or near emergency
  setup.
- [ ] Support service categories such as shelter, food, health, legal,
  benefits, transportation, employment, and crisis support.
- [ ] Integrate with existing 211 service matching concepts using derived,
  consented profile needs.
- [ ] Add a guided intake path for users who do not know what service category
  they need.

Acceptance criteria:

- Main mobile screen shows "Social services" as the second primary card.
- Users can browse service categories and start a liaison request.
- The UI can display matched services from an API response.
- The flow does not require users to share emergency-disclosure data unless they
  choose to.

### ABBY-009: Shelter Access UX

- [ ] Design a free shelter portal onboarding flow.
- [ ] Let shelter staff invite or assist users without taking ownership of the
  user's private wallet.
- [ ] Include role-based views for shelter staff, administrators, and users.
- [ ] Add assisted-registration and contact-verification patterns.
- [ ] Define abuse-prevention and audit prompts for staff actions.

Acceptance criteria:

- Shelter workflows are clearly separate from personal user account workflows.
- Staff actions require role context and audit logging hooks.
- Assisted setup keeps final sharing choices under user control when possible.
- The UI supports low-bandwidth and shared-device assumptions.

### ABBY-010: Emergency Recipient Access UX

- [ ] Design the secure-link experience recipients see after escalation.
- [ ] Include recipient identity verification before sensitive data is shown.
- [ ] Display only the scopes that user authorized for that recipient.
- [ ] Include next-step guidance for contacting the user, shelter, social
  worker, police precinct, or liaison.
- [ ] Add link expiration and expired-link recovery states.

Acceptance criteria:

- A recipient cannot see more than the authorized scope.
- Expired, revoked, and already-used access states are designed.
- The recipient screen is mobile-friendly for use in the field.
- Emergency information is clear without exposing unrelated wallet data.

### ABBY-011: Benefits Protection Opt-In UX

- [ ] Design an explicit opt-in flow for benefits-related escalation.
- [ ] Explain that Social Security payment-hold notification depends on legal,
  policy, and agency integration review.
- [ ] Collect only the minimum data needed for the future integration.
- [ ] Add consent review, revoke, and audit history views.

Acceptance criteria:

- This flow is never enabled by default.
- UI copy distinguishes "request/notify" from guaranteed agency action.
- The design includes legal-review placeholders before implementation.
- Benefits data is isolated from general emergency contact disclosure unless the
  user separately authorizes sharing.

### ABBY-012: Authentication, Recovery, And CAPTCHA UX

- [ ] Design login, logout, session timeout, account recovery, and device
  verification screens.
- [ ] Add CAPTCHA placement for registration and abuse-prone unauthenticated
  actions.
- [ ] Provide shared-device safety prompts, especially for shelter contexts.
- [ ] Add passkey or device-key UI placeholders if supported by the wallet
  backend later.

Acceptance criteria:

- Users can understand whether they are signed in on a personal or shared
  device.
- Recovery flow does not disclose account existence unnecessarily.
- CAPTCHA failure and retry states are designed.
- Session expiration preserves unsaved safe draft data where possible.

### ABBY-013: Desktop Layouts

- [ ] Adapt all core flows to desktop without changing the mobile-first task
  order.
- [ ] Add desktop dashboard views for check-in status, contacts, social
  services, uploads, and disclosure rules.
- [ ] Ensure desktop layouts do not hide critical actions in mobile-only
  controls.

Acceptance criteria:

- All mobile flows are usable at common desktop widths.
- Desktop uses the extra space for status and review, not unrelated marketing
  content.
- Forms remain readable and navigable with keyboard and screen reader.

### ABBY-014: Accessibility And Safety Review

- [ ] Run an accessibility review of registration, check-in, emergency contacts,
  disclosure rules, upload, and recipient access flows.
- [ ] Validate color contrast, focus order, form labels, error messages, and
  screen-reader announcements.
- [ ] Review crisis and emergency wording for clarity and non-alarming tone.
- [ ] Add reduced-motion and low-bandwidth considerations.

Acceptance criteria:

- Core flows meet WCAG 2.2 AA expectations.
- Error and escalation language is direct, specific, and non-punitive.
- No critical state is communicated by color alone.
- Test notes identify remaining accessibility risk.

### ABBY-015: Privacy, Consent, And Legal Review Gates

- [ ] Mark legal/policy review gates for police precinct notification, social
  worker notification, benefits agency notification, shelter staff access, and
  missing-person escalation.
- [ ] Define consent receipts and audit events needed by the UI.
- [ ] Define revocation UX for each consent and disclosure type.
- [ ] Define data minimization requirements for each screen.

Acceptance criteria:

- High-impact escalation flows are blocked behind explicit legal/policy review
  before production release.
- Every sensitive sharing action has confirmation, review, and revocation UX.
- The UI does not imply that an agency action is guaranteed unless the backend
  integration and policy allow it.

### ABBY-016: Agent Handoff Package

- [ ] Produce mobile wireframes for the first-run flow and the two-card home
  screen.
- [ ] Produce desktop wireframes for dashboard, registration, contacts, social
  services, and recipient access.
- [ ] Produce TypeScript component/task tickets for each screen.
- [ ] Produce API contract assumptions for frontend integration.
- [ ] Produce Playwright smoke-test scenarios for mobile and desktop.

Acceptance criteria:

- Handoff includes screen inventory, route inventory, component inventory,
  state inventory, and open questions.
- Each screen has success, empty, loading, error, and permission-denied states
  where relevant.
- Frontend implementation agents can start work without rereading the raw
  requirements file.

## Initial Route Inventory

```text
/register
/register/review
/check-in
/contacts
/contacts/:recipientId
/sharing-rules
/uploads
/social-services
/social-services/liaison
/shelter
/shelter/assist-registration
/recipient-access/:token
/benefits-protection
/settings/security
/settings/audit
```

## Initial Component Inventory

- `AppShell`
- `MobileHomeActionCards`
- `EmergencyContactsCard`
- `SocialServicesCard`
- `RegistrationStepper`
- `PhotoCaptureInput`
- `CaptchaGate`
- `CheckInPolicyForm`
- `OneTapCheckInButton`
- `RecipientEditor`
- `DisclosureScopePicker`
- `DisclosureReviewPanel`
- `UploadVaultList`
- `ServiceCategoryGrid`
- `LiaisonRequestForm`
- `ShelterStaffPortal`
- `RecipientAccessGate`
- `SensitiveDataReveal`
- `ConsentReceiptList`
- `AuditTimeline`

## Open Questions

- What jurisdiction is the first deployment intended for?
- What exact agency relationships exist for police precincts, social workers,
  shelters, and Social Security workflows?
- What identity verification level is required before emergency recipients can
  view disclosed information?
- Should missed check-ins trigger a human review step before outside
  notification?
- What communication provider will be used for email and SMS?
- What CAPTCHA provider or abuse-prevention service should be used?
- What frontend stack should become canonical if `wallet_interface/ui` does not
  already exist?
- What data is legally required, optional, or prohibited for shelter-assisted
  registration?

