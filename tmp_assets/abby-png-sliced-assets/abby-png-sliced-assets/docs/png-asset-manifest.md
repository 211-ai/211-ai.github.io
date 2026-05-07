# ABBY PNG Sliced Asset Manifest

These are PNG assets sliced from the generated website preview and the original ABBY reference image. They are meant to replace the rough SVGs with real watercolor-style PNGs.

## Production upload

Upload these folders with your site:

```text
assets/png/
css/abby-png-assets.css
```

The `source/` and `scripts/` folders are for regeneration only. They do not need to be deployed.

## Assets from the generated website preview

| File | Use |
|---|---|
| `assets/png/from-preview/preview-header-landscape.png` | Header decoration: faint mountains, skyline, bridge, evergreens. |
| `assets/png/from-preview/preview-sidebar-evergreens.png` | Bottom sidebar evergreen decoration. |
| `assets/png/from-preview/preview-support-badge.png` | Circular support badge for a help/service card. |
| `assets/png/from-preview/preview-support-bridge-watermark.png` | Bridge watermark for the support card. |
| `assets/png/from-preview/preview-quick-action-wash.png` | Soft wash for the check-in / quick action panel. |
| `assets/png/from-preview/preview-sidebar-wash.png` | Pale vertical wash for sidebar/background decoration. |
| `assets/png/from-preview/preview-card-wash-right.png` | Pale wash for large cards or lower page backgrounds. |

## Assets from the original ABBY reference image

| File | Use |
|---|---|
| `assets/png/from-reference/reference-landscape-clean.png` | Larger original ABBY landscape without wordmark/text. Good for landing hero or page watermark. |
| `assets/png/from-reference/reference-bridge-skyline-clean.png` | Original bridge + skyline without wordmark/text. |
| `assets/png/from-reference/reference-evergreens-clean.png` | Original evergreen cluster without wordmark/text. |
| `assets/png/from-reference/reference-mountain-wash-clean.png` | Original mountain/mist wash without wordmark/text. |
| `assets/png/from-reference/reference-heart-clean.png` | Original green heart only. |

## Notes

- The crops intentionally avoid UI copy and ABBY wordmark text.
- Backgrounds are converted to soft alpha so the assets can sit on off-white, mist, or pale teal website backgrounds.
- Use these as decorative assets; keep live website text in HTML for accessibility and responsiveness.
