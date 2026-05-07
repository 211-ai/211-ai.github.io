#!/usr/bin/env python3
"""
Slice ABBY watercolor-style PNG assets from the generated UI preview and the original ABBY reference image.

Usage:
  python scripts/slice_png_assets.py \
    --preview /path/to/modern_dashboard_with_soft_watercolor_accents.png \
    --reference /path/to/image.png \
    --out assets/png

The script deliberately uses crops that avoid UI/body text. For assets that sit on a white/off-white matte,
it computes a soft alpha channel so the PNG can be layered in HTML/CSS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RGBA = Image.Image
Box = Tuple[int, int, int, int]


def _median_border_rgb(arr: np.ndarray, margin: int = 4) -> np.ndarray:
    h, w = arr.shape[:2]
    strips = [arr[:margin, :, :3], arr[h-margin:, :, :3], arr[:, :margin, :3], arr[:, w-margin:, :3]]
    border = np.concatenate([s.reshape(-1, 3) for s in strips], axis=0)
    return np.median(border, axis=0)


def soft_matte_to_alpha(
    img: Image.Image,
    threshold: float = 3.0,
    gain: float = 9.0,
    min_alpha_keep: int = 0,
    blur: float = 0.9,
    bg_rgb: Tuple[int, int, int] | None = None,
) -> Image.Image:
    """Convert near-white/off-white background to a soft alpha channel.

    This is intentionally gentler than hard chroma-keying; watercolor edges remain semi-transparent.
    """
    rgb = img.convert("RGB")
    arr = np.asarray(rgb).astype(np.float32)
    bg = np.array(bg_rgb, dtype=np.float32) if bg_rgb is not None else _median_border_rgb(arr)
    # Euclidean distance from background. Use a little saturation help to preserve blue/green washes.
    diff = np.sqrt(np.sum((arr - bg) ** 2, axis=2))
    sat_boost = (np.max(arr, axis=2) - np.min(arr, axis=2)) * 0.42
    score = diff + sat_boost
    alpha = np.clip((score - threshold) * gain, 0, 255)
    if min_alpha_keep:
        alpha = np.where(alpha > 0, np.maximum(alpha, min_alpha_keep), 0)
    alpha_img = Image.fromarray(alpha.astype(np.uint8), "L")
    if blur:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(blur))
    out = rgb.convert("RGBA")
    out.putalpha(alpha_img)
    return out


def ellipse_crop(img: Image.Image, feather: float = 2.0, inset: int = 0) -> Image.Image:
    """Make an oval/circular crop transparent outside the ellipse."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((inset, inset, w - inset, h - inset), fill=255)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    rgba.putalpha(mask)
    return rgba


def save_resized(img: Image.Image, path: Path, max_width: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if max_width and img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(round(img.height * ratio))), Image.Resampling.LANCZOS)
    img.save(path, optimize=True)


def export_preview_assets(preview: Image.Image, out: Path) -> list[dict]:
    # Coordinates are tuned for the 1579 x 996 generated preview.
    specs = [
        {
            "name": "preview-header-landscape.png",
            "box": (935, 20, 1555, 190),
            "desc": "Text-free header landscape from preview: mountains, skyline, partial bridge, evergreens.",
            "alpha": {"threshold": 2.2, "gain": 8.5, "blur": 1.0},
        },
        {
            "name": "preview-sidebar-evergreens.png",
            "box": (185, 690, 330, 930),
            "desc": "Text-free sidebar evergreen cluster from preview.",
            "alpha": {"threshold": 2.4, "gain": 9.5, "blur": 1.0},
        },
        {
            "name": "preview-support-badge.png",
            "box": (404, 725, 575, 902),
            "desc": "Circular support badge with heart, mountains, and evergreens from preview.",
            "ellipse": True,
        },
        {
            "name": "preview-support-bridge-watermark.png",
            "box": (1165, 760, 1528, 908),
            "desc": "Text-free bridge/water watermark for support card from preview.",
            "alpha": {"threshold": 2.0, "gain": 8.0, "blur": 1.0},
        },
        {
            "name": "preview-quick-action-wash.png",
            "box": (760, 444, 1218, 540),
            "desc": "Text-free watercolor wash from the quick action panel.",
            "alpha": {"threshold": 1.4, "gain": 10.5, "blur": 1.2, "min_alpha_keep": 18},
        },
        {
            "name": "preview-sidebar-wash.png",
            "box": (190, 330, 324, 585),
            "desc": "Text-free pale sidebar watercolor wash.",
            "alpha": {"threshold": 1.1, "gain": 11.0, "blur": 1.4, "min_alpha_keep": 12},
        },
        {
            "name": "preview-card-wash-right.png",
            "box": (1240, 705, 1518, 820),
            "desc": "Text-free soft wash from the support card right side.",
            "alpha": {"threshold": 1.0, "gain": 9.0, "blur": 1.5, "min_alpha_keep": 10},
        },
    ]
    manifest = []
    for spec in specs:
        crop = preview.crop(spec["box"])
        if spec.get("ellipse"):
            processed = ellipse_crop(crop, feather=2.0)
        elif "alpha" in spec:
            processed = soft_matte_to_alpha(crop, **spec["alpha"])
        else:
            processed = crop.convert("RGBA")
        target = out / "from-preview" / spec["name"]
        save_resized(processed, target)
        manifest.append({
            "file": str(target.relative_to(out.parent.parent)),
            "source": "generated preview",
            "crop_box": spec["box"],
            "description": spec["desc"],
        })
    return manifest


def export_reference_assets(ref: Image.Image, out: Path) -> list[dict]:
    # Coordinates are tuned for the 2048 x 2048 ABBY reference image.
    specs = [
        {
            "name": "reference-landscape-clean.png",
            "box": (180, 70, 1840, 930),
            "desc": "Original ABBY reference landscape with mountain, skyline, bridge, and evergreens; no ABBY text.",
            "alpha": {"threshold": 4.0, "gain": 7.5, "blur": 1.0},
            "max_width": 1200,
        },
        {
            "name": "reference-bridge-skyline-clean.png",
            "box": (190, 520, 1290, 930),
            "desc": "Original ABBY reference bridge and skyline; no wordmark text.",
            "alpha": {"threshold": 4.5, "gain": 8.2, "blur": 1.0},
        },
        {
            "name": "reference-evergreens-clean.png",
            "box": (1240, 250, 1840, 930),
            "desc": "Original ABBY reference evergreen cluster; no wordmark text.",
            "alpha": {"threshold": 3.8, "gain": 8.5, "blur": 1.0},
        },
        {
            "name": "reference-mountain-wash-clean.png",
            "box": (180, 70, 1680, 550),
            "desc": "Original ABBY reference mountain and mist wash; no wordmark text.",
            "alpha": {"threshold": 2.8, "gain": 6.8, "blur": 1.3, "min_alpha_keep": 8},
        },
        {
            "name": "reference-heart-clean.png",
            "box": (970, 1560, 1100, 1685),
            "desc": "Original ABBY reference heart only; text and divider lines removed by crop.",
            "alpha": {"threshold": 4.0, "gain": 11.0, "blur": 0.7},
        },
    ]
    manifest = []
    for spec in specs:
        crop = ref.crop(spec["box"])
        processed = soft_matte_to_alpha(crop, **spec["alpha"])
        target = out / "from-reference" / spec["name"]
        save_resized(processed, target, max_width=spec.get("max_width"))
        manifest.append({
            "file": str(target.relative_to(out.parent.parent)),
            "source": "original ABBY reference image",
            "crop_box": spec["box"],
            "description": spec["desc"],
        })
    return manifest


def make_montage(asset_paths: Iterable[Path], target: Path) -> None:
    thumbs = []
    for p in asset_paths:
        im = Image.open(p).convert("RGBA")
        # Checker-ish light background so transparent assets are visible.
        bg = Image.new("RGBA", im.size, (250, 251, 248, 255))
        bg.alpha_composite(im)
        max_w, max_h = 330, 180
        ratio = min(max_w / bg.width, max_h / bg.height, 1.0)
        if ratio < 1:
            bg = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (360, 245), (250, 251, 248))
        card.paste(bg.convert("RGB"), ((360 - bg.width)//2, 18))
        draw = ImageDraw.Draw(card)
        label = p.name
        # Simple label wrap.
        if len(label) > 34:
            label = label[:31] + "..."
        draw.text((18, 205), label, fill=(7, 49, 74))
        thumbs.append(card)
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    montage = Image.new("RGB", (cols * 360, rows * 245), (238, 246, 244))
    for i, card in enumerate(thumbs):
        x = (i % cols) * 360
        y = (i // cols) * 245
        montage.paste(card, (x, y))
    target.parent.mkdir(parents=True, exist_ok=True)
    montage.save(target, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    preview = Image.open(args.preview).convert("RGB")
    ref = Image.open(args.reference).convert("RGB")

    manifest = []
    manifest.extend(export_preview_assets(preview, out))
    manifest.extend(export_reference_assets(ref, out))

    # Save manifest next to assets.
    pack_root = out.parent.parent
    manifest_path = pack_root / "asset-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    asset_paths = [pack_root / item["file"] for item in manifest]
    montage_path = pack_root / "docs" / "png-asset-montage.png"
    make_montage(asset_paths, montage_path)

    print(f"Wrote {len(manifest)} PNG assets to {out}")
    print(f"Manifest: {manifest_path}")
    print(f"Montage: {montage_path}")


if __name__ == "__main__":
    main()
