# Abby UI

TypeScript-first frontend prototype for Abby safety check-ins, emergency
contacts, controlled disclosure, uploads, social services, shelter workflows,
recipient access, and benefits-protection opt-in.

The app currently uses local mock state and can be connected to the backend
later through `src/services/`.

## Development

```bash
npm install
npm run dev
```

## Verification

```bash
npm run build
npm run test
```

For focused checks:

```bash
npm run test:smoke
npm run test:visual
npm run review:visual:dry-run
npm run review:tasks
npm run review:prompts -- --include-blocked
```

The visual test writes review screenshots and manifests to
`artifacts/ui-screenshots/latest/`, including default and stateful UI scenarios.
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
