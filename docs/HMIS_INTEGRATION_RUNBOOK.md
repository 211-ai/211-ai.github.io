# HMIS Integration Runbook

## Environment setup
- Configure `HMIS_MODE`, `HMIS_ADAPTER`, and environment-specific credentials before enabling writes.
- Verify `state/hmis/field_mappings.json` and `state/hmis/program_links.json` are current for the local CoC.

## Credential rotation
- Rotate API or file-exchange credentials with the HMIS lead approval owner.
- Re-run sandbox validation after every credential change.

## Outage handling
- Pause submissions by switching `HMIS_MODE=disabled` or disabling the submission feature flag.
- Continue drafting referrals locally while routing new submissions to manual review.

## Reconciliation
- Run `python scripts/hmis_reconciliation_job.py --once --dry-run` before production cutover.
- Review unresolved reconciliation queue items and retry only after payload fixes or HMIS-side confirmation.

## Monitoring
- Inspect `hmis-audit.jsonl` or repository-backed audit state for failed and retryable events.
- Track queue depth, retry counts, and stale draft age during launch week.

## Launch gates
- Governance matrix approved.
- Consent disclosure contract approved.
- Threat model and retention review signed off.
- Sandbox fixtures and end-to-end tests passing.
