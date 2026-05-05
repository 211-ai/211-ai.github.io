# 211 Service Navigation Portal Todo

This backlog is the executable implementation queue for
`docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md`.

The portal implementation daemon parses tasks with the heading format
`## PORTAL-...` and the metadata bullets directly below each heading.

Priority guide:

- `P0`: foundation or blocker work
- `P1`: user-visible core path work
- `P2`: adjacent capability or hardening work

## PORTAL-000 Portal Control Plane
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/211_SERVICE_NAVIGATION_PORTAL_TODO.md, scripts/portal_implementation_daemon.py, scripts/portal_implementation_supervisor.py, tests/test_portal_implementation_daemon.py
- Validation: python scripts/portal_implementation_daemon.py --once; python scripts/portal_implementation_supervisor.py --once; python -m pytest tests/test_portal_implementation_daemon.py -q
- Acceptance: The backlog can be parsed, durable state is written, a next task is selected, and the supervisor can rewrite strategy without mutating source code.

## PORTAL-010 Portal Package Builder
- Status: todo
- Completion: artifact
- Priority: P0
- Track: data
- Depends on: PORTAL-000
- Outputs: scripts/build_service_portal_package.py, data/portal/documents.portal.parquet, data/portal/service_portal_manifest.json
- Validation: python scripts/build_service_portal_package.py --output-dir data/portal
- Acceptance: A deterministic portal package is built from the existing retrieval corpus with normalized service fields and CID provenance.

## PORTAL-011 Portal Extraction Coverage
- Status: todo
- Completion: artifact
- Priority: P0
- Track: data
- Depends on: PORTAL-010
- Outputs: tests/test_service_portal_package.py, data/portal/extraction_coverage_report.json
- Validation: python -m pytest tests/test_service_portal_package.py -q
- Acceptance: Coverage and parser tests validate phone, address, hours, eligibility, and provenance extraction quality.

## PORTAL-012 Portal Package Publish And Audit
- Status: completed
- Priority: P1
- Track: data
- Depends on: PORTAL-010, PORTAL-011
- Outputs: scripts/upload_hf_portal_package.py, data/portal/upload_audit.json
- Validation: python scripts/upload_hf_portal_package.py --repo endomorphosis/211-info --source data/portal
- Acceptance: Portal package artifacts upload to Hugging Face with matching hashes and a recorded audit manifest.

## PORTAL-020 Service Detail Route
- Status: completed
- Priority: P1
- Track: ui
- Depends on: PORTAL-010
- Outputs: wallet_interface/ui/src/app/ServiceDetailScreen.tsx, wallet_interface/ui/src/app/App.tsx
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Search results can open a dedicated service detail route that renders provider, program, source URL, CID, and timestamps.

## PORTAL-021 Provenance Panel And Search Navigation
- Status: todo
- Priority: P1
- Track: ui
- Depends on: PORTAL-020
- Outputs: wallet_interface/ui/src/components/services/ServiceProvenancePanel.tsx, wallet_interface/ui/src/services/graphRagService.ts
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: The detail screen exposes source spans, extraction confidence, and a reliable navigation path from the current Services experience.

## PORTAL-030 Mobile Action Service
- Status: todo
- Priority: P1
- Track: mobile
- Depends on: PORTAL-020
- Outputs: wallet_interface/ui/src/services/serviceActionService.ts, wallet_interface/ui/src/lib/calendar/ics.ts, tests/test_service_action_service.ts
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Call, text, email, map, share, and calendar URLs are standards-compliant and generated only when backing data exists.

## PORTAL-031 Interaction Intent Capture
- Status: todo
- Priority: P1
- Track: mobile
- Depends on: PORTAL-030, PORTAL-041
- Outputs: wallet_interface/ui/src/services/serviceInteractionService.ts, tests/test_service_interaction_service.ts
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: User-initiated actions can emit wallet-ready interaction intents without assuming direct OS permissions.

## PORTAL-040 Wallet Service Models
- Status: completed
- Priority: P0
- Track: wallet
- Depends on: PORTAL-010
- Outputs: wallet_interface/ui/src/models/abby.ts, wallet_interface/app_service.py
- Validation: python -m pytest tests/test_wallet_interface_api.py -q
- Acceptance: Saved service, service plan, and interaction event models exist with CID, provenance, privacy, and follow-up fields.

## PORTAL-041 Wallet Portal API
- Status: completed
- Priority: P0
- Track: wallet
- Depends on: PORTAL-040
- Outputs: wallet_interface/api.py, tests/test_wallet_interface_api.py
- Validation: python -m pytest tests/test_wallet_interface_api.py -q
- Acceptance: API endpoints support create, read, update, and revoke flows for saved services, plans, reminders, and interactions.

## PORTAL-042 Saved Services And Plans UI
- Status: todo
- Priority: P1
- Track: wallet
- Depends on: PORTAL-020, PORTAL-041
- Outputs: wallet_interface/ui/src/app/ServicePlanScreen.tsx, wallet_interface/ui/src/components/services/SavedServicesPanel.tsx
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Users can save a service, create a plan, maintain a checklist, and persist encrypted notes across refreshes.

## PORTAL-050 Interaction Timeline
- Status: todo
- Priority: P1
- Track: wallet
- Depends on: PORTAL-031, PORTAL-041
- Outputs: wallet_interface/ui/src/app/InteractionsScreen.tsx, wallet_interface/ui/src/components/services/InteractionTimeline.tsx
- Validation: npm --prefix wallet_interface/ui test -- --runInBand; python -m pytest tests/test_wallet_interface_api.py -q
- Acceptance: Service interactions can be filtered by service, worker, status, and time while preserving safe audit metadata boundaries.

## PORTAL-060 Worker Collaboration Grants
- Status: todo
- Priority: P1
- Track: collab
- Depends on: PORTAL-042, PORTAL-041
- Outputs: wallet_interface/ui/src/components/services/ServicePlanSharingPanel.tsx, wallet_interface/app_service.py
- Validation: npm --prefix wallet_interface/ui test -- --runInBand; python -m pytest tests/test_wallet_interface_api.py -q
- Acceptance: Users can share a service plan with a worker under explicit scoped grants and the action is auditable.

## PORTAL-061 Worker Redaction And Revocation
- Status: todo
- Priority: P1
- Track: collab
- Depends on: PORTAL-060
- Outputs: wallet_interface/ui/src/components/services/WorkerServicePlanView.tsx, tests/test_wallet_interface_api.py
- Validation: python -m pytest tests/test_wallet_interface_api.py -q
- Acceptance: Worker views expose only granted fields and revocation removes future access while preserving audit history.

## PORTAL-070 PWA Offline Shell
- Status: todo
- Priority: P2
- Track: pwa
- Depends on: PORTAL-020, PORTAL-042
- Outputs: wallet_interface/ui/public/manifest.webmanifest, wallet_interface/ui/src/pwa/serviceWorker.ts
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Public service detail pages and saved-service shells can render offline without leaking private wallet plaintext into browser caches.

## PORTAL-071 Offline Sync Queue
- Status: todo
- Priority: P2
- Track: pwa
- Depends on: PORTAL-070, PORTAL-050
- Outputs: wallet_interface/ui/src/pwa/offlineInteractionQueue.ts, tests/test_offline_interaction_queue.ts
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Pending offline interactions are visible, replayable, and auditable after reconnection.

## PORTAL-080 Production Readiness
- Status: todo
- Priority: P1
- Track: ops
- Depends on: PORTAL-012, PORTAL-050, PORTAL-061, PORTAL-070
- Outputs: docs/211_SERVICE_NAVIGATION_PORTAL_RUNBOOK.md, docs/211_SERVICE_NAVIGATION_PORTAL_THREAT_MODEL.md, data/portal/release_checklist.json
- Validation: python -m pytest tests/test_wallet_interface_api.py -q; npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Accessibility, mobile smoke coverage, privacy review, artifact auditing, and release operations are documented and verifiable.
