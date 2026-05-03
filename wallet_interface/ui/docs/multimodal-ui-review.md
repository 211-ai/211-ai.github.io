# Multimodal UI Review Loop

The visual Playwright suite captures Abby UI screenshots for desktop and mobile
review and writes JSON manifests that can be consumed by an agent using
`ipfs_datasets_py.multimodal_router`.

## Capture Screenshots

```bash
npm run test:visual
```

Generated files are written under:

```text
wallet_interface/ui/artifacts/ui-screenshots/latest/
  desktop/
    manifest.json
    home.png
    register-filled.png
    register.png
    ...
  mobile/
    manifest.json
    home.png
    register.png
    ...
```

The artifact folder is gitignored because screenshots should be regenerated for
each UI review pass.

## Router Consumption Shape

Each manifest entry includes:

- `title`: human-readable screen name
- `path`: route used by Playwright
- `viewport`: Playwright project slug
- `state`: default, filled, checked, verified, or other scenario state
- `screenshotPath`: PNG path relative to `wallet_interface/ui`
- `goals`: route-specific UI/UX criteria
- `multimodalPrompt`: ready-to-send review prompt

Example Python shape:

```python
import json
from pathlib import Path
from ipfs_datasets_py import multimodal_router

ui_root = Path("wallet_interface/ui")
manifest = json.loads((ui_root / "artifacts/ui-screenshots/latest/mobile/manifest.json").read_text())

for item in manifest["screenshots"]:
    result = multimodal_router.generate_multimodal_text(
        item["multimodalPrompt"],
        image_paths=[ui_root / item["screenshotPath"]],
    )
    print(item["title"])
    print(result)
```

Recommended loop:

1. Run `npm run test:visual`.
2. Run `npm run review:health` to inspect the AccelerateManager endpoint and
   provider health report.
3. Run `npm run review:visual` to send each screenshot and prompt through the
   multimodal router. The default provider is `accelerate`, which routes through
   `ipfs_datasets_py.ml.accelerate_integration.manager.AccelerateManager`.
4. Run `npm run review:tasks` to convert findings into small UI tasks.
5. Run `npm run review:prompts` to create per-task implementation prompts.
6. Run `npm run review:validate` to verify manifests, screenshots, review
   results, backlog tasks, and prompt files agree.
7. Patch the UI.
8. Run `npm run build` and `npm run test` again.

The current visual capture set covers 43 screenshots: desktop and mobile states
for the main wallet flows, plus mobile navigation, active/revoked recipient
grants, and proof-center public-input receipts.

## Iterative Refinement Capture

Use the refinement capture for faster agent loops after a UI change:

```bash
npm run test:refinement
```

Generated files are written under:

```text
wallet_interface/ui/artifacts/ui-iterations/latest/
  desktop/
    manifest.json
    home.png
    register-filled.png
    ...
  mobile/
    manifest.json
    home.png
    mobile-navigation-open.png
    ...
```

Each manifest entry uses the same `screenshotPath`, `goals`, and
`multimodalPrompt` shape as the full visual suite. The refinement prompts also
include an iteration ID and, when configured, a previous screenshot path for
before/after comparison.

To compare against a previous capture, pass a baseline root:

```bash
UI_REFINEMENT_BASELINE_ROOT=artifacts/ui-iterations/previous npm run test:refinement
```

Recommended quick iteration loop:

```bash
npm run test:refinement
npm run review:health:strict
npm run review:refinement
npm run review:refinement:tasks
npm run review:refinement:prompts
npm run review:refinement:validate
```

When running on a machine with configured AccelerateManager credentials, add
the health-required validator:

```bash
npm run review:refinement:validate:health
```

For a no-provider smoke test of the handoff shape:

```bash
npm run review:refinement:dry-run
npm run review:refinement:tasks
npm run review:refinement:prompts -- --include-blocked
npm run review:refinement:validate
```

## Review Runner

Validate manifests without making model calls:

```bash
npm run review:visual:dry-run
```

Run the real multimodal review once your router provider is configured:

```bash
npm run review:visual
```

Real review runs reject empty, very short, or prompt-echo model responses so
the generated backlog is not polluted by bad provider output. For provider
debugging only, bypass that guard with:

```bash
python3 scripts/review_screenshots.py --limit 1 --allow-low-quality-feedback
```

The default route is:

```text
multimodal_router -> llm_router provider "accelerate" -> AccelerateManager
```

AccelerateManager can route to configured local or remote backends, including
Codex, GitHub Copilot, Gemini, Claude, Hugging Face, OpenAI/OpenRouter,
libp2p task-queue workers, and HTTP peer endpoints.

Health-check configured endpoints/providers:

```bash
npm run review:health
```

This writes:

```text
wallet_interface/ui/artifacts/ui-review/latest/accelerate-health.json
```

For an automated local agent handoff, use the strict health check:

```bash
npm run review:health:strict
```

Strict mode exits non-zero if AccelerateManager reports no usable backend. The
artifact validator can also require the health report:

```bash
npm run review:validate:health
```

The health report must include provider entries for Codex, GitHub Copilot,
Gemini, Claude, Hugging Face, OpenAI, and OpenRouter, plus p2p/HTTP endpoint
status.

Optional provider/model overrides:

```bash
python3 scripts/review_screenshots.py --provider accelerate --model codex_cli
```

Outputs are written under:

```text
wallet_interface/ui/artifacts/ui-review/latest/
  review-results.json
  review-summary.md
```

`review-results.json` is intended for follow-up agents. `review-summary.md` is
intended for human triage.

## Task Backlog Generation

Convert review output into agent-ready tasks:

```bash
npm run review:tasks
```

This writes:

```text
wallet_interface/ui/artifacts/ui-review/latest/
  refinement-backlog.json
  refinement-backlog.md
```

`refinement-backlog.json` is the best handoff file for an implementation agent.
Each task includes priority, route, viewport, state, screenshot path, source
feedback, suggested agent type, and acceptance criteria.

## Agent Prompt Generation

Generate implementation prompts for ready tasks:

```bash
npm run review:prompts
```

Dry-run reviews produce blocked review-needed tasks. To generate prompts for
those placeholders anyway:

```bash
npm run review:prompts -- --include-blocked
```

This writes one prompt per task plus an index:

```text
wallet_interface/ui/artifacts/ui-review/latest/agent-prompts/
  index.md
  abby-ui-desktop-home-001.md
  ...
```

## Artifact Validation

Validate the current generated review handoff:

```bash
npm run review:validate
```

The validator checks:

- `desktop/manifest.json` and `mobile/manifest.json`
- screenshot files referenced by manifests and review results
- review entry count versus manifest screenshot count
- backlog task count versus review entry count
- prompt files versus backlog task IDs
