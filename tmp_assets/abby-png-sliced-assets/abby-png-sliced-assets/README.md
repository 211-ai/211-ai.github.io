# ABBY PNG Sliced Assets

This pack contains text-free PNG assets sliced from:

1. The generated ABBY-style website preview.
2. The original ABBY watercolor reference image.

Use the PNGs instead of the earlier rough SVG assets.

## What to upload with the app

```text
assets/png/
css/abby-png-assets.css
```

## Helpful files

```text
docs/png-asset-montage.png       # visual overview of the PNG assets
docs/png-asset-manifest.md       # what each asset is for
docs/cli-slicing-notes.md        # how the slices were created
scripts/slice_png_assets.py      # regenerate the PNG slices
source/                          # source images for regeneration only
```

## CSS usage example

```css
.page-header::after {
  content: "";
  position: absolute;
  top: -12px;
  right: 24px;
  width: min(52vw, 620px);
  height: 180px;
  background: url("/assets/png/from-preview/preview-header-landscape.png") right top / contain no-repeat;
  opacity: 0.68;
  pointer-events: none;
}
```
