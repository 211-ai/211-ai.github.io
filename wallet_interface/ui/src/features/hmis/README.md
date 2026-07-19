# HMIS Feature Slice

This slice owns the HMIS (Homeless Management Information System) integration UI
for the Abby application.

## Components

| Component | Responsibility |
| --- | --- |
| `HmisDashboard` | Operational overview: reconciliation queue, enrollment drafts, sync events |
| `HmisLookupPanel` | Read-only client/household/program search (Phase 2) |
| `HmisMatchReviewDrawer` | Staff review and confirm/reject of identity-match candidates |
| `HmisReferralDraftPanel` | Referral draft creation, validation, and submission (Phase 3) |
| `HmisReconciliationQueue` | Retry queue for failed or open reconciliation items (Phase 4) |
| `HmisSyncTimeline` | Submission history and sync-event audit trail (Phase 4) |
| `HmisEnrollmentDraftPanel` | Enrollment draft creation and submission (Phase 5) |

## Canonical import paths

```ts
import { HmisLookupPanel } from "features/hmis/components/HmisLookupPanel";
// or via slice barrel:
import { HmisLookupPanel } from "features/hmis";
```

The original `components/hmis/Hmis*.tsx` paths remain as backward-compatibility
re-export stubs so that any unreached import sites continue to compile.
