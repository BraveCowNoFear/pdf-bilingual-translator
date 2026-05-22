#!/usr/bin/env python
"""Extract embedded PDF images and render page-region crops for LaTeX reconstruction."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


def safe_name(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    return name.strip("._") or "asset"


def fmt_rect(rect) -> str:
    if rect is None:
        return ""
    return ",".join(f"{float(v):.2f}" for v in rect)


def extract_embedded_images(doc: fitz.Document, out_dir: Path):
    image_dir = out_dir / "figures" / "embedded"
    image_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    saved_paths: dict[int, Path] = {}
    for page_index, page in enumerate(doc, start=1):
        for image_index, image in enumerate(page.get_images(full=True), start=1):
            xref = int(image[0])
            if xref not in saved_paths:
                info = doc.extract_image(xref)
                ext = info.get("ext", "png")
                path = image_dir / f"xref{xref}.{ext}"
                path.write_bytes(info["image"])
                saved_paths[xref] = path
            else:
                info = doc.extract_image(xref)
                path = saved_paths[xref]

            rects = page.get_image_rects(xref)
            if not rects:
                rects = [None]
            for rect_index, rect in enumerate(rects, start=1):
                rows.append(
                    {
                        "type": "embedded",
                        "page": page_index,
                        "name": f"p{page_index:03d}_img{image_index:02d}_rect{rect_index:02d}",
                        "xref": xref,
                        "path": str(path),
                        "width": info.get("width"),
                        "height": info.get("height"),
                        "colorspace": info.get("colorspace"),
                        "bbox": fmt_rect(rect),
                        "dpi": "",
                        "pixel_width": "",
                        "pixel_height": "",
                    }
                )
    return rows


def render_clips(doc: fitz.Document, clips_path: Path | None, out_dir: Path, default_dpi: int):
    if not clips_path:
        return []
    data = json.loads(clips_path.read_text(encoding="utf-8"))
    clips = data.get("clips", data if isinstance(data, list) else [])
    clip_dir = out_dir / "figures"
    clip_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, clip in enumerate(clips, start=1):
        page_no = int(clip["page"])
        page = doc[page_no - 1]
        bbox = clip.get("bbox")
        if not bbox or len(bbox) != 4:
            raise ValueError(f"Clip {idx} missing bbox")
        rect = fitz.Rect([float(v) for v in bbox])
        dpi = int(clip.get("dpi", default_dpi))
        scale = dpi / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
        name = safe_name(str(clip.get("name", f"p{page_no:03d}_clip{idx:02d}")))
        path = clip_dir / f"{name}.png"
        pix.save(path)
        rows.append(
            {
                "type": "clip",
                "page": page_no,
                "name": name,
                "xref": "",
                "path": str(path),
                "width": "",
                "height": "",
                "colorspace": "",
                "bbox": fmt_rect(rect),
                "dpi": dpi,
                "pixel_width": pix.width,
                "pixel_height": pix.height,
            }
        )
    return rows


def write_asset_index(rows: list[dict], out_dir: Path) -> Path:
    out = out_dir / "asset_index.tsv"
    headers = [
        "type",
        "page",
        "name",
        "xref",
        "path",
        "bbox",
        "width",
        "height",
        "dpi",
        "pixel_width",
        "pixel_height",
        "colorspace",
    ]
    lines = ["\t".join(headers)]
    for row in rows:
        lines.append("\t".join(str(row.get(h, "")) for h in headers))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_pdf", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--clips", type=Path, help="JSON with clips: [{page,name,bbox,dpi?}]")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--no-embedded", action="store_true")
    ap.add_argument("--write-manifest-json", action="store_true")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.input_pdf)
    embedded = [] if args.no_embedded else extract_embedded_images(doc, args.out_dir)
    clips = render_clips(doc, args.clips, args.out_dir, args.dpi)
    rows = embedded + clips
    index = write_asset_index(rows, args.out_dir)
    print(index)

    if args.write_manifest_json:
        manifest = {
            "source_pdf": str(args.input_pdf),
            "embedded_images": embedded,
            "clips": clips,
        }
        out = args.out_dir / "asset_manifest.json"
        out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(out)


if __name__ == "__main__":
    main()
