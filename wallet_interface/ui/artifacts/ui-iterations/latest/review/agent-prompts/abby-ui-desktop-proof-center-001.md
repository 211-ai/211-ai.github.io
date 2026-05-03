# ABBY-UI-DESKTOP-PROOF-CENTER-001: Proof center: Run multimodal review for desktop public proof receipts Proof center

You are an implementation agent working in `wallet_interface/ui`.

## Task

- Priority: `P3`
- Category: `review_needed`
- Suggested agent: `review-agent`
- Status: `blocked`
- Route: `/#/proof-center`
- Viewport: `desktop`
- State: `public proof receipts`
- Screenshot: `artifacts/ui-iterations/latest/desktop/proof-center.png`

## Source Feedback

Run multimodal review for desktop public proof receipts Proof center

## Acceptance Criteria

- Updated `/#/proof-center` remains usable in `desktop`.
- The `public proof receipts` UI state is preserved or improved.
- Changes are checked against `artifacts/ui-iterations/latest/desktop/proof-center.png` and a regenerated screenshot.
- No sensitive data is implied to be shared without explicit user action.

## Likely Files

- `src/app/App.tsx`
- `src/styles/global.css`
- `src/components/ui.tsx`
- `src/services/mockAbbyService.ts`
- `tests/smoke.spec.ts`
- `tests/visual-capture.spec.ts`

## Instructions

1. Inspect the screenshot and the route implementation before changing code.
2. Make the smallest UI/UX change that satisfies the task.
3. Preserve mobile and desktop behavior for the affected route.
4. Do not imply sensitive data is shared without explicit user action.
5. After patching, run:

```bash
npm run build
npm run test:smoke
npm run test:visual
```

6. Regenerate review artifacts when the visual state changes:

```bash
npm run review:visual:dry-run
npm run review:tasks
npm run review:prompts -- --include-blocked
```
