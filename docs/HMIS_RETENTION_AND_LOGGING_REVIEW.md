# HMIS Retention And Logging Review

- Retain HMIS audit events as append-only operational evidence.
- Mask phone, email, and free-text notes in staff lookup views.
- Store outbound staging batches under `data/hmis/` or repository-configured HMIS state roots.
- Reconciliation events must capture actor, action, local reference, external reference, and disposition.
- Production launch requires confirmation that local retention schedules align with CoC and HMIS-lead guidance.
