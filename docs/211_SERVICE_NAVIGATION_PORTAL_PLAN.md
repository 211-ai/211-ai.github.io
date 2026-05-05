# 211 Service Navigation Portal Plan

## Goal

Build a user-facing portal on top of the scraped 211 corpus that helps people
find, evaluate, contact, visit, save, and track social-service resources from
the same raw data already collected from 211info.

The portal should not be another static directory. It should act like a
service-navigation workspace:

- Search and ask questions over the CID-indexed 211 corpus.
- Show structured service detail pages with source citations.
- Let mobile users call, text, email, open maps, create calendar reminders, and
  share service details.
- Track the user's interactions with services, service workers, documents,
  appointments, calls, eligibility notes, and follow-up tasks in the wallet.
- Preserve privacy boundaries: user data stays wallet-owned; service matching
  uses explicit user input, coarse location, or proofs rather than raw precise
  coordinates by default.

## Current Assets

The data foundation is already available.

- Retrieval package: `data/retrieval_package`
- Browser corpus: `wallet_interface/ui/public/corpus/211-info/current`
- Hugging Face dataset: `endomorphosis/211-info`
- Browser artifact path: `browser/211-info/current`
- Documents: `22,638`
- Page documents: `11,787`
- Service documents: `10,851`
- Embeddings: `22,638`, `384` dimensions, `BAAI/bge-small-en-v1.5`
- BM25 term rows: `3,191,432`
- Graph nodes: `48,851`
- Graph edges: `648,958`
- Graph communities: `41`
- Document communities: `22,638`
- Build manifest CID: `bafkreihcclqadxrfhx256soxaqdqvc66ejhsuy3krj5bf446zq2miaox4i`

The app foundation is also available.

- Services route: `wallet_interface/ui/src/app/App.tsx`
- Browser GraphRAG runtime: `wallet_interface/ui/src/lib/graphrag/*`
- GraphRAG service API: `wallet_interface/ui/src/services/graphRagService.ts`
- Wallet API client: `wallet_interface/ui/src/services/walletApi.ts`
- Wallet API/server: `wallet_interface/api.py`, `wallet_interface/app_service.py`
- Wallet domain models: `wallet_interface/ui/src/models/abby.ts`
- Audit, grants, proofs, exports, uploads, analytics, and recipient access flows
  already exist.

## Product Scope

The portal should support five primary user jobs.

1. Find services.
2. Decide whether a service is relevant and currently worth contacting.
3. Take action from a phone.
4. Track what happened.
5. Safely involve advocates, case workers, shelter staff, or providers.

### Find Services

Users should be able to search by plain language, category, location, urgency,
eligibility hints, and provider names.

Examples:

- "food pantry near Beaverton open today"
- "emergency shelter for women"
- "utility bill help"
- "mental health crisis line"
- "transportation to medical appointment"
- "help replacing ID"

Search modes:

- Fast keyword/graph search by default.
- Optional BGE hybrid vector search.
- Deterministic cited evidence summaries.
- Optional local browser LLM answer generation when explicitly requested.
- Filters for service type, city, county, language, access channel, and
  availability only after those fields are confidently extracted.

### Decide

Service detail pages should answer practical questions without inventing facts.

Required detail sections:

- Provider and program name.
- What the service provides.
- Who may be eligible.
- How to contact or apply.
- Phone, email, website, source URL.
- Address and map target when available.
- Hours and date-sensitive notes when available.
- Required documents or intake steps when available.
- Accessibility and language notes when available.
- Last scraped/build timestamp and source CID.
- Confidence/provenance for extracted fields.
- Warnings when information is missing or likely stale.

### Take Action

Mobile-first actions should use OS/browser capabilities.

- Call: `tel:` links for phone numbers.
- Text: `sms:` links where text contact is appropriate.
- Email: `mailto:` links.
- Open website: normal source/provider links.
- Maps: Apple Maps, Google Maps, and geo/search URL fallbacks.
- Calendar: downloadable `.ics` files and Web Share payloads for appointment
  or reminder events.
- Share: `navigator.share()` with title, summary, URL, and source CID fallback
  to clipboard copy.
- Save: wallet-backed saved service record.
- Prepare: checklist of questions, documents, eligibility notes, and travel
  steps.

The web app cannot silently read call logs, send texts, create calendar events,
or access contacts on every platform. All mobile integrations must be
user-initiated and degrade to copy/download links.

### Track

The portal should let users record interactions.

Interaction types:

- Viewed service.
- Saved service.
- Called provider.
- Texted provider.
- Emailed provider.
- Opened map.
- Planned visit.
- Created calendar reminder.
- Uploaded required document.
- Shared service or document with a case worker.
- Provider contacted user.
- Appointment scheduled.
- Appointment completed.
- Service unavailable.
- Needs follow-up.

Each interaction should carry:

- `interaction_id`
- `wallet_id`
- `service_doc_id`
- `source_content_cid`
- `source_page_cid`
- `provider_name`
- `program_name`
- `interaction_type`
- `timestamp`
- `status`
- `notes`
- `next_follow_up_at`
- `related_record_ids`
- `related_grant_ids`
- `related_proof_ids`
- `privacy_level`

### Involve Service Workers

"Service workers" in this product means human advocates, case workers, shelter
staff, government liaisons, and provider staff. Browser service-worker/PWA work
is a separate technical track.

Human service-worker workflows:

- User can add a worker/contact as a recipient.
- User can share a saved service plan with specific scopes.
- User can share only a redacted service summary by default.
- User can grant document analysis or decrypt access for required records.
- Worker can request access; user approves, rejects, or revokes.
- Worker interactions become audit events.
- Worker-visible views should show only data covered by active grants.

## Information Architecture

Recommended navigation additions:

- `Services`: search, recommendations, saved services, nearby/service-area
  filters.
- `Service Detail`: canonical detail page for one CID-indexed service.
- `Service Plan`: selected service plus checklist, reminders, documents, and
  sharing controls.
- `Interactions`: timeline of user/service/provider actions.
- `Workers`: case workers, advocates, provider contacts, permissions, and
  revocations.

Initial route plan:

- `/#/social-services`: keep current search and GraphRAG panel, add saved
  services and recent interactions.
- `/#/services/:docId`: service detail page.
- `/#/services/:docId/plan`: action plan and checklist.
- `/#/interactions`: cross-service interaction timeline.
- Reuse `/#/recipient-access`, `/#/sharing-rules`, `/#/uploads`,
  `/#/proof-center`, and `/#/audit` rather than duplicating wallet controls.

## Data Model

### Portal Service Record

Create a normalized portal record derived from the existing `documents.parquet`
and raw metadata.

Fields:

- `service_doc_id`
- `doc_type`
- `title`
- `provider_name`
- `program_name`
- `description`
- `categories`
- `source_url`
- `source_content_cid`
- `source_page_cid`
- `host`
- `city`
- `state`
- `addresses`
- `phones`
- `emails`
- `websites`
- `hours`
- `eligibility`
- `intake_steps`
- `required_documents`
- `fees`
- `languages`
- `accessibility`
- `geo`
- `source_extracts`
- `field_confidence`
- `updated_at`

Every extracted field must include provenance:

- Exact source text span when possible.
- Source URL.
- Source CID.
- Extraction method.
- Confidence.

### Saved Service

Wallet-backed user state.

Fields:

- `saved_service_id`
- `wallet_id`
- `service_doc_id`
- `source_content_cid`
- `label`
- `reason`
- `priority`
- `status`
- `created_at`
- `updated_at`
- `private_notes_record_id`

### Service Plan

Wallet-backed plan for taking action.

Fields:

- `plan_id`
- `wallet_id`
- `service_doc_id`
- `goal`
- `steps`
- `documents_needed`
- `questions_to_ask`
- `appointment_at`
- `reminder_at`
- `travel_target`
- `assigned_worker_recipient_id`
- `status`
- `related_interaction_ids`

### Interaction Event

Wallet-backed event log item, also mirrored into audit where appropriate.

Fields:

- `interaction_id`
- `wallet_id`
- `service_doc_id`
- `interaction_type`
- `channel`
- `actor_did`
- `counterparty_name`
- `counterparty_contact`
- `timestamp`
- `outcome`
- `notes_record_id`
- `next_action`
- `next_follow_up_at`
- `source_action_url`
- `related_grant_ids`
- `related_record_ids`

## Data Pipeline

### Phase A: Structured Service Extraction

Build a portal extraction package from the current retrieval package.

Inputs:

- `data/retrieval_package/content/documents.parquet`
- raw page/service metadata from DuckDB or raw JSONL where available
- browser corpus manifests and CIDs

Outputs:

- `data/portal/services.parquet`
- `data/portal/service_contacts.parquet`
- `data/portal/service_locations.parquet`
- `data/portal/service_hours.parquet`
- `data/portal/service_requirements.parquet`
- `data/portal/service_actions.parquet`
- `data/portal/extraction_manifest.json`

Extraction methods:

- Deterministic regex/parsing for phone, email, URLs, addresses, dates, and
  common hours patterns.
- Optional local LLM extraction only with strict JSON schema validation and
  source-span requirements.
- No field should be marked high confidence without a source span or structured
  raw value.

Acceptance criteria:

- At least 95% of service records keep provider/program/source fields.
- Phone/address/hour extraction reports coverage and confidence.
- Every extracted field links back to `source_content_cid`.
- The pipeline does not overwrite or remove the canonical scraped data.

### Phase B: Portal Browser Package

Create browser-friendly portal artifacts.

Outputs:

- `wallet_interface/ui/public/corpus/211-info/current/portal/services.json`
- `portal/service-index.json`
- `portal/contact-actions.json`
- `portal/location-actions.json`
- `portal/field-provenance.json`

The portal package should be separate from retrieval artifacts so search
performance and service detail rendering can evolve independently.

Acceptance criteria:

- Service detail page can load one service by `doc_id` or CID.
- Contact/map/calendar actions do not require loading the full retrieval graph.
- Browser package manifest links every portal artifact to its CID.

### Phase C: Hugging Face Publishing

Publish portal artifacts under a dedicated path.

Recommended paths:

- Parquet package: `portal/211-info/current/data/*`
- Browser package: `browser/211-info/current/portal/*`

Acceptance criteria:

- Audit script verifies size and SHA-256.
- Manifest records source retrieval package CID and portal package CIDs.
- Existing `data/` and `browser/` paths remain backwards compatible.

## Frontend Design

### Services Search

Enhance the existing Services screen.

Add:

- Search input with suggested prompts.
- Category chips.
- Saved/recent services rail.
- Result cards with phone/map/website badges when extracted.
- Result cards with "Save", "Plan", and "Share" actions.
- Filter drawer for city, distance/coarse area, channel, language, and category.
- Empty states that recommend broader searches or contacting 211 directly.

### Service Detail

Detail page layout:

- Header: provider/program/category/source trust indicator.
- Action bar: Call, Directions, Website, Calendar, Save, Share.
- Summary: deterministic evidence summary from source text.
- Practical details: eligibility, hours, documents, intake, fees.
- Location card: address, map buttons, distance only if user consented to
  coarse/precise location.
- Source/provenance panel: URL, CID, scrape/build timestamp, field confidence.
- Interaction panel: last contacted, notes, follow-up status.
- Worker sharing panel: share with a selected recipient under a scoped grant.

### Service Plan

Plan page layout:

- Goal and next step.
- Checklist.
- Documents needed, with links to wallet uploads.
- Questions to ask.
- Calendar/reminder controls.
- Travel plan.
- Assigned worker or advocate.
- Notes and interaction timeline.

### Interaction Timeline

Timeline should combine:

- User actions from the portal.
- Wallet audit events.
- Grants/revocations.
- Proof receipts.
- Upload/document references.
- Worker access requests.

Do not mix private notes into public audit logs. Store private notes as wallet
records and reference them by record ID.

## Mobile Integration Details

### Call

Use `tel:${phone}` with visible confirmation context.

Track only user intent:

- "User tapped call"
- phone label
- service CID
- timestamp

Do not imply the call connected unless the user records the outcome.

### Text

Use `sms:${phone}?&body=${encodedMessage}` only where texting is listed or user
chooses it.

### Maps

Use progressive fallbacks:

- `https://www.google.com/maps/search/?api=1&query=...`
- `https://maps.apple.com/?q=...`
- `geo:` links on Android when supported
- source URL if no address is extracted

Do not request precise location by default. If distance sorting is added, use:

- user-entered ZIP/city first
- coarse location grant second
- precise browser geolocation only after explicit permission

### Calendar

Generate `.ics` files client-side for:

- appointment reminders
- call-back reminders
- visit windows
- document deadlines

Because browser calendar APIs are inconsistent, `.ics` download/share is the
portable baseline.

### Notifications

Use browser notification permission only after the user creates a reminder.
Fallback to visible in-app reminders and downloadable calendar events.

### Contacts

Do not depend on Contacts Picker API for launch. Use explicit user-entered
recipient/contact fields and optional `vCard` export later.

### Web Share

Use `navigator.share()` when available. Fallback to copy-to-clipboard.
Shared payloads should include:

- service title
- provider/program
- source URL
- "verify details before visiting"
- source CID

## Wallet and Privacy Model

The public 211 corpus is not private. User interactions with it are private.

Public data:

- scraped service text
- source URLs
- provider/program details
- extracted service contact/location fields
- CIDs and provenance

Private wallet data:

- saved services
- search intent if stored
- notes
- reminders
- documents
- worker assignments
- interaction history
- precise location
- calls/text intents
- grants and revocations

Rules:

- Do not store private portal state in localStorage except ephemeral UI state.
- Persist private state as encrypted wallet records.
- Mirror only non-sensitive action metadata to audit logs.
- Keep GraphRAG prompts free of private wallet data unless the user explicitly
  opts in and the data stays inside the permitted execution boundary.
- Use coarse location/proofs for service-area matching whenever possible.

## API Plan

### Public Portal API

For server-backed mode:

- `GET /services/search?q=&category=&city=&limit=`
- `GET /services/{service_doc_id}`
- `GET /services/{service_doc_id}/related`
- `GET /services/{service_doc_id}/actions`
- `GET /services/{service_doc_id}/provenance`

These can be served from static browser artifacts first, then moved to FastAPI
only if needed for dynamic filtering or analytics.

### Wallet Portal API

Add wallet-backed endpoints:

- `POST /wallets/{wallet_id}/saved-services`
- `GET /wallets/{wallet_id}/saved-services`
- `PATCH /wallets/{wallet_id}/saved-services/{saved_service_id}`
- `DELETE /wallets/{wallet_id}/saved-services/{saved_service_id}`
- `POST /wallets/{wallet_id}/service-plans`
- `GET /wallets/{wallet_id}/service-plans`
- `PATCH /wallets/{wallet_id}/service-plans/{plan_id}`
- `POST /wallets/{wallet_id}/service-interactions`
- `GET /wallets/{wallet_id}/service-interactions`
- `POST /wallets/{wallet_id}/service-interactions/{interaction_id}/follow-up`
- `POST /wallets/{wallet_id}/services/{service_doc_id}/share-grants`

All write endpoints should audit:

- actor
- wallet
- service CID
- purpose
- grant IDs where relevant
- timestamp
- privacy class

## Service Worker / PWA Track

Browser service-worker support should be handled as a separate track from
human service-worker workflows.

PWA service worker goals:

- Cache shell UI.
- Cache compact portal detail artifacts.
- Avoid caching sensitive wallet records outside encrypted wallet storage.
- Allow offline viewing of saved services and plans if encrypted state is
  available.
- Queue user-created interaction events until online if policy allows.

Acceptance criteria:

- Public service details can be cached.
- Private wallet notes are not cached as plaintext.
- Offline actions are clearly marked as pending sync.

## Analytics and Feedback

Use privacy-preserving analytics only.

Useful aggregate metrics:

- categories searched
- services saved
- action buttons tapped
- service unavailable reports
- follow-up completion rates
- county/city-level demand with k-thresholds

Do not report:

- precise location
- raw query text by default
- private notes
- document contents
- provider conversation contents

User feedback:

- "Information was outdated"
- "Could not reach provider"
- "Eligibility mismatch"
- "Service helped"
- "Need follow-up"

Feedback should be stored as wallet-private first. Aggregation requires explicit
analytics consent.

## Implementation Phases

### Phase 1: Portal Data Package

Deliverables:

- `scripts/build_service_portal_package.py`
- `data/portal/*.parquet`
- extraction coverage report
- portal manifest with CIDs
- tests for phone/address/hours extraction

Acceptance criteria:

- Detail fields can be rendered without running GraphRAG.
- All structured fields retain source provenance.
- Package build is deterministic and auditable.

### Phase 2: Service Detail UI

Deliverables:

- `ServiceDetailScreen`
- route support for `/#/services/:docId`
- action bar with call/map/site/share/save placeholders
- source/provenance panel
- Playwright detail-page smoke test

Acceptance criteria:

- Opening a search result can navigate to a detail page.
- Detail page renders provider/program/source/CID.
- Action buttons are present only when the underlying field exists.

### Phase 3: Mobile Actions

Deliverables:

- `serviceActionService.ts`
- call/text/email/map/share/calendar helpers
- `.ics` generator
- interaction-intent capture
- tests for URL generation and `.ics` output

Acceptance criteria:

- Mobile action links are standards-compliant.
- Calendar files validate as ICS.
- Action taps can create wallet interaction events.

### Phase 4: Saved Services and Plans

Deliverables:

- saved-service models
- service-plan models
- wallet API endpoints
- UI for saving, planning, checklists, reminders, and follow-up
- encrypted private notes

Acceptance criteria:

- User can save a service from search/detail.
- User can create a plan with checklist and reminder.
- Saved services survive refresh through wallet persistence.

### Phase 5: Interaction Timeline

Deliverables:

- interaction event models
- timeline UI
- audit integration
- filters by service, worker, status, and time

Acceptance criteria:

- Call/map/calendar/share/save actions can be represented as interactions.
- Private notes remain wallet records.
- Audit logs contain safe metadata only.

### Phase 6: Worker Collaboration

Deliverables:

- share service plan with recipient
- worker access request flow for service-plan context
- scoped grant creation
- revocation handling
- worker-visible redacted service plan view

Acceptance criteria:

- User can share one saved service/plan with a case worker.
- Worker sees only granted fields.
- Revocation removes future access and appears in audit.

### Phase 7: PWA and Offline

Deliverables:

- service worker cache strategy
- installable PWA manifest review
- offline saved service shell
- pending interaction sync queue if approved

Acceptance criteria:

- Public service detail can open offline after caching.
- No private plaintext appears in Cache Storage.
- Pending offline actions are visible and auditable.

### Phase 8: Production Readiness

Deliverables:

- portal package HF upload/audit
- accessibility review
- mobile browser test matrix
- privacy/threat-model update
- operations runbook update
- release checklist

Acceptance criteria:

- iOS Safari and Android Chrome smoke tests pass.
- HF artifacts match local hashes.
- Security review signs off on wallet/private-state boundaries.

## Test Plan

Python tests:

- extraction parser tests
- portal package manifest tests
- CID/provenance integrity tests
- wallet API tests for saved services/plans/interactions

TypeScript tests:

- action URL generation
- ICS generation
- service detail field rendering
- interaction event construction
- privacy redaction helpers

Playwright tests:

- search to detail flow
- call/map/calendar/share buttons render correctly
- save service
- create plan
- add follow-up
- share plan with worker
- revoke worker access
- mobile layout and keyboard/screen-reader checks

Manual/mobile tests:

- iOS Safari call/map/calendar/share
- Android Chrome call/map/calendar/share
- low-connectivity/offline behavior
- large text/accessibility settings

## Risks

- 211 data can be stale; every user-facing detail needs source and verification
  language.
- Extracting addresses/hours from unstructured text may be noisy; confidence and
  provenance are required.
- Mobile browser APIs vary; use links/downloads/share fallbacks.
- Precise location is sensitive; prefer user-entered area, coarse location, or
  proof receipts.
- Service interaction history can reveal vulnerability; store it encrypted and
  scoped.
- Provider contacts may not support text/email even if strings are present; show
  channel confidence and source context.
- PWA offline caching must not leak wallet plaintext.

## Definition of Done

The portal is ready when:

- Users can search the 211 corpus and open structured service detail pages.
- Every service detail field links to source URL and CID provenance.
- Mobile users can call, navigate, share, and create reminders from service
  pages.
- Users can save services, create service plans, and track interactions.
- Users can share specific service plans or documents with service workers using
  scoped wallet grants.
- Revocation and audit behavior are visible and tested.
- Public service data and private wallet interaction data remain separate.
- Browser, API, extraction, and mobile smoke tests pass.
