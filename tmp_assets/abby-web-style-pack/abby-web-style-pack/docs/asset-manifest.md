# ABBY Web Asset Manifest

This pack separates **production assets** from **reference images**.

## Production assets to upload with the website

Upload these folders with your HTML/CSS/JS bundle:

```text
assets/
css/
```

The CSS file assumes this relative structure:

```text
index.html
assets/...
css/abby-theme.css
```

## Assets

| File | Purpose | Recommended use |
|---|---|---|
| `assets/abby-logo-mark.svg` | Small app mark | Sidebar, favicon fallback, compact header |
| `assets/favicon.svg` | Browser favicon | `<link rel="icon" href="assets/favicon.svg">` |
| `assets/abby-logo-lockup.svg` | Larger logo lockup | Marketing header or splash screen |
| `assets/watercolor-wash.svg` | Full-page watercolor wash | Body/app shell background |
| `assets/watercolor-card-wash.svg` | Soft card wash | Check-in panel/card backgrounds |
| `assets/abby-header-landscape.svg` | Mountain + bridge + skyline + evergreens | Low-opacity page header decoration |
| `assets/abby-bridge-watermark.svg` | Bridge/water motif | Bottom support card or empty state decoration |
| `assets/abby-evergreen-cluster.svg` | Evergreen cluster | Sidebar or corner decoration |
| `assets/abby-help-badge.svg` | Round heart/landscape badge | “Need help today?” or service card |
| `assets/abby-heart.svg` | Heart accent | Small dividers, empty states, supportive labels |

## Reference files not required for production

The `reference/` folder contains the original source image, the original Playwright screenshot, and the generated style preview. These are for design review and AI-agent context only.

```text
reference/abby-logo-reference.png
reference/home-original.png
reference/home-style-preview.png
```

## Accessibility notes

Decorative SVGs should usually be added with `aria-hidden="true"` or as CSS backgrounds. Avoid placing important text directly on top of decorative artwork. Keep the main UI labels, dates, buttons, and nav items in a readable sans-serif font.
