#!/usr/bin/env python
"""Validate PDF bilingual translation job artifacts before delivery."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz


RANGE_RE = re.compile(r"^(\d+)-(\d+)$")
INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\{((?:\{[^{}]+\})+)\}")
REQUIRED_QA_FIELDS = {"page", "source_png", "translated_png", "status", "defects", "fixes_applied", "rerendered"}


def pdf_page_count(path: Path) -> int:
    with fitz.open(path) as doc:
        return len(doc)


def page_labels(directory: Path) -> list[int]:
    labels: list[int] = []
    for path in directory.glob("page_*.png"):
        try:
            labels.append(int(path.stem.split("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    return sorted(labels)


def expected_labels(start: int, end: int) -> list[int]:
    return list(range(start, end + 1))


def load_qa_records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("pages", "records", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    raise ValueError("QA JSON must be a list or contain a pages/records/results list")


def validate_qa_file(path: Path, expected: list[int], errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing QA file: {path}")
        return
    try:
        records = load_qa_records(path)
    except Exception as exc:  # noqa: BLE001 - surface malformed QA files directly.
        errors.append(f"invalid QA JSON {path}: {exc}")
        return

    seen = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"{path}: record {index} is not an object")
            continue
        missing = REQUIRED_QA_FIELDS - set(record)
        if missing:
            errors.append(f"{path}: page record {record.get('page', index)} missing fields {sorted(missing)}")
        try:
            seen.append(int(record.get("page")))
        except (TypeError, ValueError):
            errors.append(f"{path}: record {index} has invalid page value {record.get('page')!r}")

    if sorted(seen) != expected:
        errors.append(f"{path}: pages {sorted(seen)} do not match expected {expected}")


def graphicspath_dirs(tex: Path, text: str) -> list[Path]:
    dirs = []
    for match in GRAPHICSPATH_RE.finditer(text):
        for raw in re.findall(r"\{([^{}]+)\}", match.group(1)):
            dirs.append((tex.parent / raw).resolve())
    return dirs


def validate_graphics(tex: Path, errors: list[str]) -> None:
    if not tex.exists():
        errors.append(f"missing LaTeX source: {tex}")
        return
    text = tex.read_text(encoding="utf-8")
    search_dirs = [tex.parent.resolve(), *graphicspath_dirs(tex, text)]
    for raw in INCLUDEGRAPHICS_RE.findall(text):
        if "#" in raw:
            continue
        raw_path = Path(raw)
        candidates = [raw_path.resolve()] if raw_path.is_absolute() else [(directory / raw_path).resolve() for directory in search_dirs]
        if raw_path.suffix:
            if not any(candidate.exists() for candidate in candidates):
                errors.append(f"{tex}: missing includegraphics asset {raw}")
            continue
        alternatives = [
            candidate.with_suffix(suffix)
            for candidate in candidates
            for suffix in (".pdf", ".png", ".jpg", ".jpeg")
        ]
        if not any(path.exists() for path in alternatives):
            errors.append(f"{tex}: missing includegraphics asset {raw} with known image/PDF suffix")


def validate_segments(job_dir: Path, errors: list[str], warnings: list[str]) -> dict[str, int]:
    doc_pages: dict[str, int] = {}
    segments_root = job_dir / "segments"
    if not segments_root.exists():
        errors.append(f"missing segments directory: {segments_root}")
        return doc_pages

    for doc_dir in sorted(path for path in segments_root.iterdir() if path.is_dir()):
        max_page = 0
        expected_next = 1
        for segment_dir in sorted(path for path in doc_dir.iterdir() if path.is_dir()):
            match = RANGE_RE.match(segment_dir.name)
            if not match:
                warnings.append(f"ignoring non-range segment directory: {segment_dir}")
                continue
            start, end = int(match.group(1)), int(match.group(2))
            expected = expected_labels(start, end)
            if start != expected_next:
                errors.append(f"{doc_dir.name}/{segment_dir.name}: page range gap or overlap, expected start {expected_next}")
            expected_next = end + 1
            max_page = max(max_page, end)

            tex = segment_dir / "latex" / "segment.tex"
            segment_pdf = segment_dir / "segment.pdf"
            build_log = segment_dir / "build.log"
            if not segment_pdf.exists():
                errors.append(f"missing segment PDF: {segment_pdf}")
            else:
                count = pdf_page_count(segment_pdf)
                if count != len(expected):
                    errors.append(f"{segment_pdf}: has {count} pages, expected {len(expected)}")
            if not build_log.exists():
                errors.append(f"missing build log: {build_log}")
            validate_graphics(tex, errors)

            for pass_name in ("source", "pass_1", "pass_2"):
                labels = page_labels(segment_dir / pass_name)
                if labels != expected:
                    errors.append(f"{segment_dir / pass_name}: page labels {labels} do not match expected {expected}")
                contact_sheets = list((segment_dir / pass_name).glob("contact_*.png"))
                if contact_sheets:
                    warnings.append(f"{segment_dir / pass_name}: contains {len(contact_sheets)} contact sheet(s); do not count them as QA evidence")

            validate_qa_file(segment_dir / "qa" / "pass_1_pages.json", expected, errors)
            validate_qa_file(segment_dir / "qa" / "pass_2_pages.json", expected, errors)

        if max_page:
            doc_pages[doc_dir.name] = max_page
    return doc_pages


def validate_merged(job_dir: Path, doc_pages: dict[str, int], errors: list[str], warnings: list[str]) -> None:
    merged_root = job_dir / "merged"
    if not merged_root.exists():
        errors.append(f"missing merged directory: {merged_root}")
        return

    for doc_id, expected_page_count in sorted(doc_pages.items()):
        merged_dir = merged_root / doc_id
        expected = expected_labels(1, expected_page_count)
        if not merged_dir.exists():
            errors.append(f"missing merged doc directory: {merged_dir}")
            continue

        final_pdf = merged_dir / "final.pdf"
        if not final_pdf.exists():
            errors.append(f"missing final PDF: {final_pdf}")
        else:
            count = pdf_page_count(final_pdf)
            if count != expected_page_count:
                errors.append(f"{final_pdf}: has {count} pages, expected {expected_page_count}")

        if not (merged_dir / "build.log").exists():
            errors.append(f"missing merged build log: {merged_dir / 'build.log'}")

        for pass_name in ("source", "pass_3", "pass_4"):
            labels = page_labels(merged_dir / pass_name)
            if labels != expected:
                errors.append(f"{merged_dir / pass_name}: page labels {labels} do not match expected {expected}")
            contact_sheets = list((merged_dir / pass_name).glob("contact_*.png"))
            if contact_sheets:
                warnings.append(f"{merged_dir / pass_name}: contains {len(contact_sheets)} contact sheet(s); do not count them as QA evidence")

        validate_qa_file(merged_dir / "qa" / "pass_3_pages.json", expected, errors)
        validate_qa_file(merged_dir / "qa" / "pass_4_pages.json", expected, errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_dir", type=Path, help="Job directory such as tmp/pdfs/<job>")
    parser.add_argument("--write-json", type=Path, help="Optional path to write validation results")
    args = parser.parse_args()

    job_dir = args.job_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if not job_dir.exists():
        raise SystemExit(f"Job directory not found: {job_dir}")

    doc_pages = validate_segments(job_dir, errors, warnings)
    validate_merged(job_dir, doc_pages, errors, warnings)

    result = {
        "job_dir": str(job_dir),
        "documents": doc_pages,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
