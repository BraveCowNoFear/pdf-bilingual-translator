#!/usr/bin/env python
"""Extract PDF text blocks as context for from-scratch bilingual LaTeX reconstruction."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from statistics import median

import fitz
from PIL import Image


def clean_text(text: str) -> str:
    text = text.replace("\uf0b7", "- ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def union_bbox(a, b):
    return [
        min(a[0], b[0]),
        min(a[1], b[1]),
        max(a[2], b[2]),
        max(a[3], b[3]),
    ]


def line_kind(text: str, size: float, flags: int, page_no: int) -> str:
    del flags, page_no
    t = text.strip()
    if (".." in t or re.search(r"\.{3,}", t)) and re.search(r"\s\d+$", t) and len(t) > 20:
        return "toc"
    if re.match(r"^(Figure|Fig\.|Table)\s+\d+", t, re.IGNORECASE):
        return "caption"
    if re.match(r"^(\d+(\.\d+)*\s+|Appendix\s+[A-Z]|Part\s+[A-Z]\b)", t) and size >= 10:
        return "heading"
    if size >= 13:
        return "heading"
    if t.endswith("?") and size >= 10.5 and len(t) < 90:
        return "subheading"
    if re.match(r"^([-*•]\s+|\d+\.|[a-z]\))\s+", t):
        return "list"
    return "body"


def should_skip_line(bbox, page_height: float, header_margin: float, footer_margin: float) -> bool:
    _x0, y0, _x1, y1 = bbox
    if header_margin >= 0 and y1 <= header_margin:
        return True
    if footer_margin >= 0 and y0 >= page_height - footer_margin:
        return True
    return False


def extract_lines(page: fitz.Page, page_no: int, header_margin: float, footer_margin: float):
    data = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
    lines = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts = []
            sizes = []
            flags = 0
            for span in line.get("spans", []):
                s = span.get("text", "")
                if s:
                    parts.append(s)
                    sizes.append(float(span.get("size", 10.0)))
                    flags |= int(span.get("flags", 0))
            text = clean_text("".join(parts))
            if not text:
                continue
            bbox = [float(v) for v in line.get("bbox", block.get("bbox"))]
            if should_skip_line(bbox, page.rect.height, header_margin, footer_margin):
                continue
            size = median(sizes) if sizes else 10.0
            lines.append(
                {
                    "text": text,
                    "bbox": bbox,
                    "font_size": round(size, 2),
                    "flags": flags,
                    "kind": line_kind(text, size, flags, page_no),
                }
            )
    lines.sort(key=lambda r: (round(r["bbox"][1], 1), round(r["bbox"][0], 1)))
    return lines


def same_paragraph(prev, cur) -> bool:
    if prev["kind"] != cur["kind"]:
        return False
    if prev["kind"] not in {"body", "list"}:
        return False
    pb = prev["bbox"]
    cb = cur["bbox"]
    vertical_gap = cb[1] - pb[3]
    if vertical_gap < -1 or vertical_gap > 13:
        return False
    if abs(cb[0] - pb[0]) <= 9:
        return True
    if prev["kind"] == "list" and cb[0] > pb[0] and cb[0] - pb[0] <= 45:
        return True
    return False


def group_lines(lines):
    groups = []
    for line in lines:
        if groups and same_paragraph(groups[-1], line):
            groups[-1]["text"] = groups[-1]["text"] + " " + line["text"]
            groups[-1]["bbox"] = union_bbox(groups[-1]["bbox"], line["bbox"])
            groups[-1]["font_size"] = round(
                (groups[-1]["font_size"] * groups[-1]["line_count"] + line["font_size"])
                / (groups[-1]["line_count"] + 1),
                2,
            )
            groups[-1]["line_count"] += 1
        else:
            groups.append({**line, "line_count": 1})
    return groups


def page_image(page: fitz.Page, scale: float = 2.0) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def sample_bg(img: Image.Image, bbox, scale: float = 2.0):
    x0, y0, x1, y1 = [int(round(v * scale)) for v in bbox]
    x0 = max(0, min(img.width - 1, x0 + 2))
    y0 = max(0, min(img.height - 1, y0 + 2))
    x1 = max(x0 + 1, min(img.width, x1 - 2))
    y1 = max(y0 + 1, min(img.height, y1 - 2))
    crop = img.crop((x0, y0, x1, y1))
    thumb = crop.resize((min(24, crop.width), min(24, crop.height)))
    pixel_iter = thumb.get_flattened_data() if hasattr(thumb, "get_flattened_data") else thumb.getdata()
    pixels = list(pixel_iter)
    light = [p for p in pixels if sum(p) >= 500]
    pool = light if len(light) >= 8 else pixels
    rgb = [int(median([p[i] for p in pool])) for i in range(3)]
    if sum(rgb) / 3 >= 222:
        return [255, 255, 255]
    return rgb


def align_for_block(block, page_width: float) -> str:
    x0, _y0, x1, _y1 = block["bbox"]
    center = (x0 + x1) / 2
    width = x1 - x0
    if width < page_width * 0.68 and abs(center - page_width / 2) < page_width * 0.12:
        if block["kind"] in {"heading", "subheading"} or block["font_size"] >= 12:
            return "center"
    return "left"


def build_manifest(input_pdf: Path, doc_id: str, header_margin: float, footer_margin: float):
    doc = fitz.open(input_pdf)
    pages = []
    for page_index, page in enumerate(doc):
        page_no = page_index + 1
        img = page_image(page)
        blocks = []
        for idx, block in enumerate(group_lines(extract_lines(page, page_no, header_margin, footer_margin)), start=1):
            block_id = f"{doc_id}-p{page_no:03d}-b{idx:03d}"
            bg = sample_bg(img, block["bbox"])
            block["id"] = block_id
            block["page"] = page_no
            block["bg_rgb"] = bg
            block["align"] = align_for_block(block, page.rect.width)
            block["bbox"] = [round(v, 2) for v in block["bbox"]]
            blocks.append(block)
        pages.append(
            {
                "page": page_no,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "blocks": blocks,
            }
        )
    return {
        "doc_id": doc_id,
        "source_pdf": str(input_pdf),
        "page_count": len(doc),
        "pages": pages,
    }


def write_chunks(manifest: dict, chunk_dir: Path, pages_per_chunk: int):
    chunk_dir.mkdir(parents=True, exist_ok=True)
    pages = manifest["pages"]
    outputs = []
    for chunk_idx in range(math.ceil(len(pages) / pages_per_chunk)):
        part = pages[chunk_idx * pages_per_chunk : (chunk_idx + 1) * pages_per_chunk]
        payload = {
            "doc_id": manifest["doc_id"],
            "source_pdf": manifest["source_pdf"],
            "instructions": (
                "Use these text blocks as context for from-scratch Simplified Chinese LaTeX "
                "reconstruction. Preserve numbers, units, variables, citations, formulas, tables, "
                "and visible order; keep technical/proper terms bilingual."
            ),
            "pages": [
                {
                    "page": p["page"],
                    "blocks": [
                        {
                            "id": b["id"],
                            "kind": b["kind"],
                            "text": b["text"],
                        }
                        for b in p["blocks"]
                    ],
                }
                for p in part
            ],
        }
        out = chunk_dir / f"{manifest['doc_id']}_pages_{part[0]['page']:03d}_{part[-1]['page']:03d}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(str(out))
    return outputs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_pdf", type=Path)
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--chunk-dir", type=Path)
    ap.add_argument("--pages-per-chunk", type=int, default=10)
    ap.add_argument("--header-margin", type=float, default=48.0)
    ap.add_argument("--footer-margin", type=float, default=38.0)
    args = ap.parse_args()

    manifest = build_manifest(args.input_pdf, args.doc_id, args.header_margin, args.footer_margin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)
    if args.chunk_dir:
        for path in write_chunks(manifest, args.chunk_dir, args.pages_per_chunk):
            print(path)


if __name__ == "__main__":
    main()
