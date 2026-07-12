# Abby Handoff Contracts And Governance

Last updated: 2026-05-04

Purpose: provide documentation-only assumptions for TypeScript implementation
tasks, frontend API contracts, legal/policy gates, consent, audit, revocation,
and data minimization.

## TypeScript Component And Task Ticket Assumptions

Each implementation ticket should preserve mobile-first order, use typed domain
models, and keep wallet, cryptography, storage, proof, UCAN, and policy
evaluation concerns behind app/service APIs.

| Ticket | Screen or component | Assumptions and tasks |
| --- | --- | --- |
| TS-001 | `RegistrationStepper` | Add required identity group, optional support fields, field-purpose helper text, CAPTCHA state, save/resume draft, and create-profile confirmation. |
| TS-002 | `MobileHomeActionCards` | Ensure first viewport has only "Emergency contacts" and "Social services" as primary cards, with secondary status below. |
| TS-003 | `DashboardStatusPanel` | Show next check-in, active recipients, sharing reminders, upload count, and recent audit event without raw sensitive data. |
| TS-004 | `RecipientEditor` | Support emergency contact, social worker, police precinct, shelter staff, government liaison, and benefits agency types with verification state. |
| TS-005 | `DisclosureReviewPanel` | Preview authorized scopes per recipient, require confirmation, show review reminder or expiration, and expose revocation entry points. |
| TS-006 | `ServiceCategoryGrid` and `GuidedServiceIntake` | Support service browsing, "not sure what I need" intake, matched service results, and consented profile-derived needs. |
| TS-007 | `RecipientAccessGate` | Handle token status, recipient verification, scoped package display, expired/revoked/already-used recovery, and permission-denied states. |
| TS-008 | `ShelterStaffPortal` | Add role context, assisted-registration workflow, audit prompts, and shared-device/low-bandwidth states. |
| TS-009 | `ConsentReceiptList` | List active, revoked, expired, and pending consents with receipt details and audit links. |
| TS-010 | `AuditTimeline` | Render user-readable audit events for consent, disclosure, recipient access, staff actions, and policy-gated notifications. |

## API Contract Assumptions

Contracts below are frontend assumptions, not final backend designs.

Common response rules:
- Every sensitive read must return only scopes authorized for the current
  session, role, token, and policy gate.
- Mutating endpoints should return `auditEventId` and, when applicable,
  `consentReceiptId`.
- Error responses should include stable `code`, safe `message`, and optional
  field-level validation details.
- API responses should not reveal account existence in unauthenticated recovery,
  CAPTCHA, recipient-token, or verification flows.

```ts
type ApiErrorCode =
  | "validation_failed"
  | "captcha_failed"
  | "authentication_required"
  | "permission_denied"
  | "policy_gate_required"
  | "token_expired"
  | "token_revoked"
  | "not_found"
  | "rate_limited";

interface ApiEnvelope<T> {
  data?: T;
  error?: {
    code: ApiErrorCode;
    message: string;
    fields?: Record<string, string>;
  };
  auditEventId?: string;
  consentReceiptId?: string;
}
```

Expected endpoint groups:

| Area | Endpoint assumption | Notes |
| --- | --- | --- |
| Registration | `POST /api/abby/registration/drafts`, `POST /api/abby/profile` | Drafts may be local-only until session creation; profile create requires CAPTCHA and minimum identity. |
| Check-in | `GET/PUT /api/abby/check-in-policy`, `POST /api/abby/check-ins` | Backend validates max interval of 30 days and computes next due date. |
| Contacts | `GET/POST /api/abby/recipients`, `PATCH/DELETE /api/abby/recipients/:id` | Recipient type determines verification and policy requirements. |
| Disclosure | `GET/PUT /api/abby/disclosure-rules`, `POST /api/abby/disclosure-rules/:id/revoke` | Rule changes create consent receipts and audit events. |
| Uploads | `POST /api/abby/uploads`, `GET /api/abby/uploads` | Upload metadata and sharing eligibility are separate from file storage. |
| Social services | `POST /api/abby/service-matches`, `POST /api/abby/liaison-requests` | Matching can use only consented derived needs. |
| Shelter | `GET /api/abby/shelter/queue`, `POST /api/abby/shelter/assist-registration` | Staff actions require role context and audit prompts. |
| Recipient access | `GET /api/abby/recipient-access/:token/status`, `POST /api/abby/recipient-access/:token/verify`, `GET /api/abby/recipient-access/:token/package` | Package endpoint returns authorized scopes only. |
| Benefits | `POST /api/abby/benefits-protection/consent`, `POST /api/abby/benefits-protection/revoke` | Must remain disabled unless policy gate is approved. |
| Audit | `GET /api/abby/audit-events`, `GET /api/abby/consent-receipts` | User-readable, filterable, and export-ready later. |

## Legal And Policy Review Gates

Production UI must block high-impact escalation behind explicit gate status
from backend/admin configuration. Pending gates may be shown as unavailable,
pilot-only, or "request review" states, but the UI must not imply the agency
action is guaranteed.

| Gate | Applies to | Minimum release state |
| --- | --- | --- |
| Police precinct notification | Missing-person escalation and precinct recipient access | Block until jurisdiction, legal basis, dispatch workflow, and human review rules are approved. |
| Social worker notification | Social worker recipient access and liaison escalation | Block or pilot-limit until agency relationship, consent language, and contact verification are approved. |
| Benefits agency notification | Social Security/payment-hold opt-in | Explicit opt-in only; block sending until legal, policy, and agency integration review are approved. |
| Shelter staff access | Shelter-assisted registration and staff workflows | Block until staff roles, audit logging, user consent, and shared-device safety requirements are approved. |
| Missing-person escalation | Any missed-check-in outside notification | Block until escalation threshold, grace period, human review, false-positive handling, and revocation behavior are approved. |

## Consent Receipts

Create a receipt for every sensitive sharing, escalation, liaison, shelter
assist, benefits, and recipient access authorization.

Receipt fields:
- `id`, `userId`, `createdAt`, `updatedAt`, `status`
- consent type and plain-language summary
- recipient or agency id, type, and verified contact channel
- authorized data scopes
- purpose, trigger condition, expiration or review date
- policy gate version and UI copy version
- capture context: session/device type, assisted-by staff id if relevant
- revocation timestamp and revocation reason when available

Statuses: `draft`, `active`, `revoked`, `expired`, `superseded`,
`policy_pending`.

## Audit Events

Audit events should be user-readable and include enough structure for later
compliance review without displaying raw sensitive payloads.

Required event families:
- profile created or updated
- CAPTCHA passed or failed for abuse-prone action
- check-in policy created, changed, disabled, or escalated
- recipient created, verified, changed, removed, or reordered
- disclosure rule created, confirmed, previewed, changed, revoked, expired
- upload created, categorized, marked sensitive, included/excluded from sharing
- recipient access link generated, opened, verified, viewed, expired, revoked
- shelter staff viewed, assisted, invited, verified, or submitted on behalf of a user
- liaison request created, matched, sent, closed, or failed
- benefits protection consent created, revoked, blocked by policy, or notified
- admin policy gate changed

## Revocation UX

Revocation must be visible from the relevant settings/detail page and from the
global consent/audit area.

| Consent or disclosure type | Revocation UX |
| --- | --- |
| Recipient disclosure rule | Recipient detail and sharing rules page show revoke action, impact preview, confirmation, receipt update, and audit event. |
| Secure access link | Recipient access status shows revoke/expire action for the user and safe revoked state for the recipient. |
| Social services liaison | Liaison request detail allows cancel/revoke before submission; after submission, show what was sent and who to contact. |
| Shelter staff assistance | User can end assisted access; staff portal loses access and records an audit event. |
| Benefits protection | Benefits page shows revoke opt-in, explains future notifications stop, and preserves historical receipts. |
| Check-in escalation policy | Check-in settings allow disabling escalation after warning that outside notification will not happen. |
| Upload sharing | Upload detail and sharing preview allow removing a file/scope from current and future disclosure packages. |

## Data Minimization Requirements

Screen-level rules:
- First run: collect no sensitive data except a local draft choice and
  shared-device preference.
- Registration: required only legal name, birth date, photo/photo ID, and bot
  check; all other fields are optional and must explain purpose.
- Home/dashboard: show status, counts, and reminders; avoid raw address,
  document names, medical notes, or benefits identifiers.
- Contacts: collect only contact details needed for the chosen recipient type
  and verification channel.
- Disclosure rules: show only the selected recipient, selected scopes, preview,
  review date, and revocation state.
- Uploads: separate storage metadata from sharing state; default uploaded items
  to not shared until explicitly selected.
- Social services: use derived needs instead of raw emergency/profile data
  whenever possible.
- Shelter portal: staff see only assigned workflow fields and must not take
  ownership of the user's wallet or final sharing decisions when user control is
  possible.
- Recipient access: show only authorized scopes; omit unrelated wallet,
  contact, document, benefits, and audit data.
- Benefits protection: collect only fields required for future policy-reviewed
  notification; isolate benefits data from general emergency disclosure unless
  separately authorized.
- Audit/settings: show event metadata and plain-language summaries rather than
  full sensitive payloads.

## Implementation Open Questions

- Which backend owns policy gate evaluation and gate versioning?
- Which consent text versions need legal approval before pilots?
- Which recipient identity verification providers are acceptable?
- Can social services matching run fully on derived needs, or are any raw fields
  required by the initial 211 integration?
- What retention period applies to expired recipient links and revoked receipts?
