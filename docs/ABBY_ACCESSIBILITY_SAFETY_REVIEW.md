# Abby Accessibility And Safety Review

Last updated: 2026-05-04

## Scope Reviewed

- Registration and staff registration
- Check-in setup
- Emergency contacts and sharing rules
- Recipient access
- Benefits protection
- Shelter shared-device workflows
- Security settings

## Accessibility Findings

- Form labels are explicit and tied to native inputs through the shared `Field` wrapper or visible label text.
- Required fields use both visible markers and `aria-required` / `required` semantics.
- Keyboard paths exist for route navigation, cards, status panels, checkboxes, buttons, disclosure controls, and upload inputs.
- Focus states use a high-contrast outline and do not rely on color alone.
- Statuses include text labels such as "Review required", "Disclosure revoked", "Phone verified", and "Summary failed".
- Motion is decorative, short, and disabled through `prefers-reduced-motion`.

## Contrast And Visual Safety

- Primary teal, warning yellow, success green, and danger red states include readable text labels.
- Required markers are red but accompanied by screen-reader text.
- Sensitive states use banners and badges rather than background color alone.
- Photo previews are hidden by default to reduce accidental exposure on shared devices.

## Focus Order

- Mobile order follows the visible task order: page title, status guidance, primary controls, form/list actions.
- Desktop order follows the sidebar route list, then screen content.
- Recipient rows expose move, verification, edit, review, and remove controls in a stable sequence.

## Error And Recovery Messaging

- PIN flows name missing shelter, missing PIN, wrong PIN, invalid administrator PIN, and revoked staff states.
- Upload failure keeps the item visible, falls back to a filename title, disables sharing, and offers retry/remove.
- Expired recipient links block sensitive display and ask for a new secure link.
- Removing the last active emergency recipient requires a second confirmation.

## Crisis And Emergency Tone

- Copy avoids blame language around missed check-ins, bot-check follow-up, and health-check tags.
- Warnings explain limits without promising agency or emergency outcomes.
- Benefits protection states that legal, policy, and agency integration review is required before production notification.

## Low-Bandwidth And Shared-Device Considerations

- Core workflows are text-first and do not require large media to understand state.
- Upload OCR/PDF extraction failures fall back gracefully.
- Shelter workflows include shared-device checklist prompts for user presence, clearing browser data, and audit logging.
- Security settings preserve session-timeout and recovery reminders without persisting transient reveal states.
