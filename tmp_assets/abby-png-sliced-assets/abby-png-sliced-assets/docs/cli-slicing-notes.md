# Command-line slicing notes

The rough SVGs were replaced with PNG slices. The basic stack is:

- **ImageMagick** for quick crop/export/strip operations.
- **Python + Pillow** for repeatable crop coordinates and soft alpha extraction.
- **OpenCV inpainting** can be used for text removal when a crop cannot avoid text, but this pack mostly avoids text by cropping clean regions.

## Quick crop with ImageMagick

Example: slice the header landscape from the generated preview.

```bash
magick source/generated-style-preview.png \
  -crop 620x170+935+20 \
  +repage \
  assets/png/from-preview/preview-header-landscape.raw.png
```

Example: slice the original ABBY landscape without the wordmark text.

```bash
magick source/abby-logo-reference.png \
  -crop 1660x860+180+70 \
  +repage \
  assets/png/from-reference/reference-landscape-clean.raw.png
```

## Regenerate all PNGs

```bash
python scripts/slice_png_assets.py \
  --preview source/generated-style-preview.png \
  --reference source/abby-logo-reference.png \
  --out assets/png
```

The Python script does three things:

1. Slices fixed text-free crop regions.
2. Converts off-white matte backgrounds into soft transparency.
3. Creates a montage preview at `docs/png-asset-montage.png`.

## Text removal strategy

Best option: crop around text instead of trying to repair it.

When unavoidable, use OpenCV inpainting with a mask over dark text. A minimal pattern looks like this:

```python
import cv2

img = cv2.imread("crop-with-text.png")
mask = cv2.imread("text-mask.png", cv2.IMREAD_GRAYSCALE)
clean = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
cv2.imwrite("cleaned.png", clean)
```

For production, still prefer a clean crop or a separately generated asset over heavy inpainting.
