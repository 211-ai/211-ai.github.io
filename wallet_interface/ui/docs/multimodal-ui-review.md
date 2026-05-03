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
  desktop-chrome/
    manifest.json
    home.png
    register-filled.png
    register.png
    ...
  mobile-safari/
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
manifest = json.loads((ui_root / "artifacts/ui-screenshots/latest/mobile-safari/manifest.json").read_text())

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
2. Run `npm run review:visual` to send each screenshot and prompt through the
   multimodal router.
3. Run `npm run review:tasks` to convert findings into small UI tasks.
4. Run `npm run review:prompts` to create per-task implementation prompts.
5. Patch the UI.
6. Run `npm run build`, `npm run test:smoke`, and `npm run test:visual` again.

## Review Runner

Validate manifests without making model calls:

```bash
npm run review:visual:dry-run
```

Run the real multimodal review once your router provider is configured:

```bash
npm run review:visual
```

Optional provider/model overrides:

```bash
python3 scripts/review_screenshots.py --provider openai --model gpt-4.1-mini
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
  abby-ui-desktop-chrome-home-001.md
  ...
```
