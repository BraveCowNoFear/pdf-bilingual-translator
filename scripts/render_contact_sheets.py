#!/usr/bin/env python
"""Render PDF pages to PNGs and optional contact sheets for visual QA."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


def render_pages(
    pdf: Path,
    out_dir: Path,
    dpi: int,
    page_from: int | None,
    page_to: int | None,
    page_number_offset: int,
) -> list[Path]:
    doc = fitz.open(pdf)
    if len(doc) == 0:
        return []

    first = 1 if page_from is None else page_from
    last = len(doc) if page_to is None else page_to
    if first < 1 or last > len(doc) or first > last:
        raise ValueError(f"Invalid page range {first}-{last} for {pdf} with {len(doc)} pages")

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    scale = dpi / 72
    for page_no in range(first, last + 1):
        page = doc[page_no - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        label = page_no + page_number_offset
        path = out_dir / f"page_{label:03d}.png"
        pix.save(path)
        rendered.append(path)
    return rendered


def make_contact(images: list[Path], output_prefix: Path, cols: int, thumb_width: int) -> list[Path]:
    if not images:
        return []
    sheets: list[Path] = []
    batch_size = cols * 4
    font = ImageFont.load_default()
    for batch_idx in range(math.ceil(len(images) / batch_size)):
        batch = images[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        thumbs = []
        for path in batch:
            img = Image.open(path).convert("RGB")
            ratio = thumb_width / img.width
            thumb = img.resize((thumb_width, int(img.height * ratio)))
            canvas = Image.new("RGB", (thumb.width, thumb.height + 22), "white")
            canvas.paste(thumb, (0, 0))
            draw = ImageDraw.Draw(canvas)
            draw.text((6, thumb.height + 5), path.stem, fill=(0, 0, 0), font=font)
            thumbs.append(canvas)
        cell_w = max(t.width for t in thumbs)
        cell_h = max(t.height for t in thumbs)
        rows = math.ceil(len(thumbs) / cols)
        sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "white")
        for idx, thumb in enumerate(thumbs):
            x = (idx % cols) * cell_w
            y = (idx // cols) * cell_h
            sheet.paste(thumb, (x, y))
        out = output_prefix.with_name(f"{output_prefix.name}_{batch_idx + 1:02d}.png")
        sheet.save(out)
        sheets.append(out)
    return sheets


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=120)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--thumb-width", type=int, default=360)
    ap.add_argument("--page-from", type=int)
    ap.add_argument("--page-to", type=int)
    ap.add_argument(
        "--page-number-offset",
        type=int,
        default=0,
        help="Add this to rendered page labels; use start_page - 1 for segment PDFs.",
    )
    ap.add_argument("--flat-pages", action="store_true", help="Write page_###.png directly under --out-dir.")
    ap.add_argument(
        "--contact-sheet",
        action="store_true",
        help="Also generate contact sheets. Flat-page QA renders skip contact sheets unless this is set.",
    )
    ap.add_argument("--no-contact", action="store_true", help="Skip contact sheet generation.")
    ap.add_argument("--write-manifest-json", action="store_true", help="Write render_manifest.json.")
    args = ap.parse_args()

    pages_dir = args.out_dir if args.flat_pages else args.out_dir / "pages"
    pages = render_pages(
        args.pdf,
        pages_dir,
        args.dpi,
        args.page_from,
        args.page_to,
        args.page_number_offset,
    )
    make_sheets = not args.no_contact and (not args.flat_pages or args.contact_sheet)
    sheets = make_contact(pages, args.out_dir / "contact", args.cols, args.thumb_width) if make_sheets else []

    if args.write_manifest_json:
        manifest = {
            "pdf": str(args.pdf),
            "pages": [str(p) for p in pages],
            "contact_sheets": [str(s) for s in sheets],
        }
        out = args.out_dir / "render_manifest.json"
        out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(out)
    else:
        for path in pages + sheets:
            print(path)


if __name__ == "__main__":
    main()
