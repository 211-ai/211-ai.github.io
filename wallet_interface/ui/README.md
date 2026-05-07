# Abby UI

TypeScript-first frontend prototype for Abby safety check-ins, emergency
contacts, controlled disclosure, uploads, social services, shelter workflows,
recipient access, and benefits-protection opt-in.

The app currently uses local mock state and can be connected to the backend
later through `src/services/`.

Access requests and grant receipts can be loaded from the wallet API by setting:

```bash
VITE_WALLET_API_BASE_URL=http://localhost:8000
VITE_DEMO_WALLET_ID=wallet-...
VITE_DEMO_ACTOR_DID=did:key:owner
```

When those variables are absent, the recipient-access screen uses local mock
access-request and receipt state for demos and tests.
The uploads screen also uses the same API config to list encrypted document
records and add files through the multipart wallet document endpoint, with a
text-document fallback for simpler local API deployments.
API-backed uploads expose owner document viewing through the wallet decrypt
endpoint; plaintext is shown only after the connected wallet actor requests it.
Owners can also create record-scoped grants from an uploaded document for
analysis, document viewing, or bounded re-delegation. View and delegation
grants can request a record-scoped multi-sig approval inline, then reuse the
returned approval ID when creating the grant. Document-view grants can also
require recipient presence, which the recipient access flow satisfies through a
signed invocation before decrypting.
The Security screen lists threshold approvals for the wallet so controllers can
review pending record-grant and wallet-governance approvals without copying IDs
between screens.
API-loaded documents show encrypted storage health by calling each record's
storage verification endpoint. If a stored record reports a storage problem,
the uploads screen can call the wallet storage repair endpoint for that record.
The Security screen can also request a wallet-level encrypted storage report
showing total replicas, failed replicas, and the IPFS/S3/Filecoin provider mix,
then repair all configured replicas from available encrypted copies.
Active `record/analyze` receipts expose an analysis action that creates an
encrypted, derived-only artifact; the UI shows artifact metadata and storage
reference rather than raw document plaintext. Active `record/decrypt` receipts
expose a separate document-view action that decrypts only after the recipient
invokes that specific grant. Active receipts held by the current actor that
include `record/share` or `document/share` can also create attenuated delegated
grants for another DID through the wallet API.
Recipient receipts can also run redacted document analysis and vector-profile
creation when their output caveats allow it. Those actions show safe derived
output alongside encrypted artifact metadata, matching the wallet package's
`redacted_derived_only` and `vector_profile` output caveats. The API client also
exposes redacted text extraction, form analysis, and GraphRAG helpers for later
UI flows.
When connected to the wallet API, the audit screen loads the wallet audit
timeline so grant, invocation, analysis, repair, and revocation events remain
traceable with actor, resource, decision, and grant metadata.

Approving, rejecting, and revoking access requests call the wallet API when
`VITE_DEMO_ACTOR_DID` is set. For demo wallets that need explicit key material
to issue useful decrypt grants, also set `VITE_DEMO_ISSUER_KEY_HEX` and
`VITE_DEMO_AUDIENCE_KEY_HEX`.
The multi-sig approval button calls the wallet approval endpoint when the
access-request review item includes an `approval_id`; otherwise it stays in the
local demo path.
For browser demos or smoke tests against a mock API, the same config can be
placed in `localStorage` under `abby-wallet-api-config` with `apiBaseUrl`,
`walletId`, and optional key/DID fields. Build-time env config takes precedence.
Non-secret demo config can also be supplied as URL parameters:
`walletApiBaseUrl`, `walletId`, and `actorDid`.

## Development

```bash
npm install
npm run dev
```

## Verification

```bash
npm run build
npm run test
npm run test:fullstack
```

For focused checks:

```bash
npm run test:smoke
npm run test:fullstack
npm run test:visual
npm run test:refinement
npm run review:visual:dry-run
npm run review:tasks
npm run review:prompts -- --include-blocked
```

The visual test writes review screenshots and manifests to
`artifacts/ui-screenshots/latest/`, including default and stateful UI scenarios.
The refinement test writes a smaller iteration packet to
`artifacts/ui-iterations/latest/` for faster multimodal review and UI/UX
revision loops.
See
`docs/multimodal-ui-review.md` for the `ipfs_datasets_py.multimodal_router`
review loop.

## GitHub Pages

The Vite app uses relative asset paths and hash-based routes, so the built app
works from a GitHub Pages project URL such as:

```text
https://<owner>.github.io/<repo>/
```

The repository workflow at `.github/workflows/abby-ui-pages.yml` builds this
subdirectory and publishes `wallet_interface/ui/dist` with GitHub Actions Pages.
In the repository settings, set Pages source to "GitHub Actions".

The UI is mobile-first and also includes desktop layouts. The mobile home screen
keeps the required primary actions as two cards: "Emergency contacts" followed
by "Social services".
