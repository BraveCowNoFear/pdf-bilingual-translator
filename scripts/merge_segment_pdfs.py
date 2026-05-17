#!/usr/bin/env python
"""Merge independently built segment PDFs in page order."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


RANGE_RE = re.compile(r"(\d+)-(\d+)")


def parse_range(path: Path):
    m = RANGE_RE.search(path.parent.name) or RANGE_RE.search(path.stem)
    if not m:
        raise ValueError(f"Cannot infer page range from {path}")
    return int(m.group(1)), int(m.group(2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments-dir", type=Path, required=True)
    ap.add_argument("--output-pdf", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, help="Optional JSON merge manifest for coordinator debugging.")
    ap.add_argument("--order-log", type=Path, help="Optional text file listing merged segment order.")
    args = ap.parse_args()

    pdfs = sorted(args.segments_dir.glob("**/segment.pdf"), key=parse_range)
    if not pdfs:
        raise SystemExit("No segment.pdf files found")

    expected_next = 1
    out = fitz.open()
    rows = []
    for pdf in pdfs:
        start, end = parse_range(pdf)
        if start != expected_next:
            raise SystemExit(f"Page range gap or overlap before {pdf}: expected {expected_next}, got {start}")
        doc = fitz.open(pdf)
        expected_pages = end - start + 1
        if len(doc) != expected_pages:
            raise SystemExit(f"{pdf} has {len(doc)} pages, expected {expected_pages}")
        out.insert_pdf(doc)
        rows.append({"segment_pdf": str(pdf), "page_from": start, "page_to": end, "pages": len(doc)})
        expected_next = end + 1

    args.output_pdf.parent.mkdir(parents=True, exist_ok=True)
    if args.output_pdf.exists():
        args.output_pdf.unlink()
    out.save(args.output_pdf)
    out.close()

    if args.order_log:
        args.order_log.parent.mkdir(parents=True, exist_ok=True)
        args.order_log.write_text(
            "\n".join(f"{r['page_from']:03d}-{r['page_to']:03d}\t{r['segment_pdf']}" for r in rows) + "\n",
            encoding="utf-8",
        )
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(
                {"output_pdf": str(args.output_pdf), "segments": rows, "page_count": expected_next - 1},
                indent=2,
            ),
            encoding="utf-8",
        )
    print(args.output_pdf)


if __name__ == "__main__":
    main()
