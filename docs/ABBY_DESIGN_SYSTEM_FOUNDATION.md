# Abby Design System Foundation

Last updated: 2026-05-04

## UI Primitives

- Buttons: `Button` supports primary, secondary, danger, and quiet variants with icon+text content.
- Fields: `Field` centralizes labels, help text, required markers, `required`, and `aria-required`.
- Cards and rows: `ActionCard`, `.list-item`, `.scope-editor`, `.analytics-card`, `.timeline-event`, and `.status-panel` cover repeated actions, records, scopes, audits, and dashboard metrics.
- Status: `Badge` and `StatusBanner` provide neutral, success, warning, and danger-adjacent states without relying on color alone.

## Spacing And Layout

- Base screen padding: `20px 16px 40px` on mobile and `32px` on desktop.
- Section gap: `14px`; screen gap: `20px`; compact row/chip gap: `8px`.
- Cards and controls use `8px` radii to match the app's restrained dashboard style.
- Form and grid tracks use `minmax(0, 1fr)` to avoid overflow on narrow viewports.

## Typography

- The app font stack is centralized in `--abby-font-family` and inherits into buttons, fields, inputs, selects, and textareas.
- Headings use fixed sizes rather than viewport-scaled type.
- Required markers are visually larger than label text and include screen-reader-only required copy.

## Color And States

- Primary action and focus color: teal `#0f766e`.
- Warning/error color: red/orange family for destructive or caution states.
- Informational panels use blue, success uses green, and warning uses yellow with text labels.
- Disabled buttons reduce opacity and remove pointer affordance.

## Breakpoints

- Mobile first: single-column forms, lists, dashboard cards, and nav.
- Desktop breakpoint: `760px`, enabling the sidebar, two-column forms, multi-column dashboards, and wider screen padding.
- Wide content max width: `1180px`.

## Sensitive Data Patterns

- Hidden by default: profile-photo previews, staff/admin PINs, recipient access packages before verification.
- Reveal controls: "See preview" / "Hide preview"; recipient verification before emergency package display.
- Redaction by absence: missing contact methods show explicit "No phone" or "No email" badges rather than blank cells.
- Revocation states: sharing rules, benefits consent, and staff verification have visible revoke/history affordances.

## Loading And Failure States

- Uploads support empty, generating, fallback, failed, stored, private, and sharing-eligible states.
- Recipient access supports pending, approved, rejected, approval-threshold, active-link, and expired-link recovery states.
- PIN and verification flows expose missing, invalid, verified, revoked, and recovery guidance states.
