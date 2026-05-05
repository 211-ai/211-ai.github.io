# AI Agent Chat Accessibility And Mobile Review

Last updated: 2026-05-05

## Scope Reviewed

- `wallet_interface/ui/src/components/agent/AgentChatDrawer.tsx`
- `wallet_interface/ui/src/components/agent/AgentChatBottomSheet.tsx`
- `wallet_interface/ui/src/components/agent/AgentMessageList.tsx`
- `wallet_interface/ui/src/components/agent/AgentComposer.tsx`
- `wallet_interface/ui/src/components/agent/AgentConfirmationCard.tsx`
- `wallet_interface/ui/src/styles/global.css`

This review covers the AGENT-021 drawer and AGENT-022 confirmation-card surfaces called out by AGENT-082: keyboard operation, focus behavior, screen-reader semantics, reduced-motion handling, and mobile viewport behavior for the assistant drawer, mobile bottom sheet, and confirmation cards.

## Current Result

The chat entry point, desktop drawer, mobile bottom sheet, message log, composer, and confirmation cards have a usable baseline for keyboard and screen-reader users. The current implementation uses native buttons and textarea controls, visible focus outlines, labeled assistant regions, status announcements, explicit confirmation summaries, and responsive CSS that switches from mobile bottom sheet to desktop drawer at larger widths.

The main gaps are not blocking for this documentation task, but should be covered before declaring the chat UI fully accessible: focus is not moved into the drawer or returned to the launcher on close, the conversation log does not set `aria-live`, the assistant containers are labeled as complementary regions instead of dialogs, and the bottom sheet has no Escape-key or focus-management behavior.

## Keyboard Review

- Pass: the assistant launcher, close buttons, sheet expand/collapse controls, composer submit button, and confirmation-card actions are native buttons. They are keyboard reachable and inherit the shared focus-visible outline.
- Pass: the composer sends with Enter and preserves multiline entry with Shift+Enter in `AgentComposer.tsx`.
- Pass: confirmation cards expose separate Confirm and Cancel buttons and disable both actions after the confirmation is no longer pending.
- Risk: opening the drawer or bottom sheet does not programmatically focus the assistant heading, message composer, or first pending confirmation. Keyboard users remain at the launcher/previous focused app control and must tab into the newly mounted assistant.
- Risk: closing the assistant does not explicitly return focus to the launcher. Because the launcher is conditionally unmounted while open, focus recovery depends on browser behavior.
- Risk: Escape does not close the drawer or bottom sheet. This is acceptable for a non-modal complementary panel, but should be added if the assistant is treated as a dialog-like surface.

## Focus Review

- Pass: shared CSS provides a 3px high-contrast outline for buttons, inputs, selects, and textareas.
- Pass: the drawer and sheet use fixed positioning with `pointer-events: none` on the shell and `pointer-events: auto` on active controls, so visible app content remains interactable when the assistant is open.
- Pass: the message list is independently scrollable, reducing the chance that keyboard focus moves behind the composer on long conversations.
- Risk: new pending confirmation cards are appended to the log, but focus is not moved to them and no explicit announcement is made. A screen-reader or keyboard user may not realize a confirmation requiring action appeared.
- Risk: the bottom-sheet grip is only 28px tall. The duplicate expand/collapse icon button in the header mitigates this, but the grip itself is below the common 44px touch-target target.

## Screen-Reader Review

- Pass: desktop and mobile assistant containers use `aria-label="Abby assistant"`.
- Pass: launcher buttons include `aria-controls` and `aria-expanded`; the bottom-sheet expand controls also expose `aria-controls`, `aria-expanded`, and state-specific labels.
- Pass: decorative lucide icons are hidden with `aria-hidden`.
- Pass: the conversation list uses `role="log"` with a descriptive `aria-label`, and messages identify sender and time in text.
- Pass: the composer textarea has a screen-reader-only label.
- Pass: confirmation cards have a descriptive section label, risk text, action summary, before/after definition list, optional details list, optional expiry, and explicit Confirm/Cancel labels.
- Risk: `role="log"` does not include `aria-live` or `aria-relevant`, so automatic announcement behavior may be inconsistent across assistive technologies.
- Risk: the drawer and bottom sheet are complementary surfaces, not `role="dialog"` / `aria-modal`. This matches the plan requirement not to hide the app behind chat, but the implementation should avoid modal assumptions in tests and copy.
- Risk: status regions for "Read-only chat" and "Abby is checking public app context" are useful, but repeated mounting could be verbose if responses update quickly.

## Reduced Motion Review

- Pass: global `prefers-reduced-motion: reduce` rules effectively disable animations, transitions, smooth scrolling, and active transforms across the UI.
- Pass: the assistant drawer, bottom sheet, and confirmation cards do not define custom entrance animations that bypass the global reduced-motion rule.
- Risk: `AgentMessageList` calls `scrollIntoView` when messages, confirmations, or results change. It does not request smooth scrolling, and reduced motion forces `scroll-behavior: auto`, so this is acceptable. Future smooth-scroll changes should remain behind the reduced-motion rule.

## Mobile Viewport Review

- Pass: the mobile assistant uses a bottom sheet by default and the desktop drawer is hidden until the larger viewport media query.
- Pass: the mobile launcher respects `env(safe-area-inset-bottom)`, and the sheet itself includes safe-area bottom padding.
- Pass: the sheet starts at `min(62dvh, 560px)` and can expand to `calc(100dvh - 72px - env(safe-area-inset-top))`, preserving app context while allowing a nearly full-screen chat view.
- Pass: `.app-chat-open .main` adds bottom padding on mobile so app content is not fully hidden behind the open sheet.
- Pass: the message list and composer have constrained grid rows and textarea heights inside the sheet.
- Risk: very small landscape viewports may leave limited room for the message log once the header, task status, typing status, and composer are visible. Playwright should keep a narrow-height mobile coverage point for this surface.
- Risk: the mobile bottom sheet is not draggable. This is acceptable because expansion and collapse are available through buttons, but future visual affordances should not imply a gesture-only interaction.

## Confirmation Card Review

- Pass: cards do not rely on color alone. Risk is named in text, the action summary is textual, and before/after states are rendered in a semantic definition list.
- Pass: action buttons use visible text plus icons and have confirmation-specific accessible labels.
- Pass: disabled state follows confirmation status, preventing duplicate confirm/cancel interaction after resolution.
- Pass: details and expiry are textual and remain visible in the card body.
- Risk: resolved cards keep an `aria-label` that says "Confirmation required" even after `status` is approved, denied, expired, or failed if the card remains rendered through message history. Consider deriving the label from status in a follow-up.
- Risk: current app wiring in `App.tsx` passes messages/responding to `AgentChatDrawer` but does not pass pending confirmations, confirm, or cancel handlers yet. The card component is ready, but the app shell needs full controller integration before end-to-end confirmation-card accessibility can be validated in browser smoke tests.

## Recommended Follow-Ups

- Move focus into the assistant on open, ideally to the composer when no confirmation is pending and to the first pending confirmation card when confirmation is required.
- Return focus to the assistant launcher after close.
- Add `aria-live="polite"` and `aria-relevant="additions text"` to the conversation log, or add a separate polite live region for new assistant messages and confirmation requests.
- Add Escape-key close behavior for both drawer and bottom sheet if product behavior remains non-destructive.
- Add Playwright coverage for keyboard open, send, close, mobile expand/collapse, reduced-motion rendering, and a pending confirmation card with Confirm/Cancel actions.
- Update confirmation-card accessible labels to reflect resolved statuses after confirmation history is retained in the log.

## Validation Notes

AGENT-082 validation command: `npm --prefix wallet_interface/ui test -- tests/smoke.spec.ts`.

This review does not mark AGENT-082 complete in the backlog metadata. It only adds the requested review artifact.
