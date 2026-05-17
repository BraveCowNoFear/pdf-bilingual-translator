#!/usr/bin/env python
"""Compile a segment LaTeX source into segment.pdf with a stable XeLaTeX loop."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", type=Path, help="Path to latex/segment.tex")
    ap.add_argument("--output-pdf", type=Path, required=True, help="Path to write segment.pdf")
    ap.add_argument("--engine", default="xelatex")
    ap.add_argument("--runs", type=int, default=2)
    args = ap.parse_args()

    tex = args.tex.resolve()
    if not tex.exists():
        raise SystemExit(f"LaTeX source not found: {tex}")
    if shutil.which(args.engine) is None:
        raise SystemExit(f"LaTeX engine not found on PATH: {args.engine}")

    output_pdf = args.output_pdf.resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    build_log = output_pdf.parent / "build.log"

    cmd = [
        args.engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        tex.name,
    ]
    log_parts: list[str] = []
    for run_index in range(1, max(1, args.runs) + 1):
        proc = subprocess.run(
            cmd,
            cwd=tex.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        log_parts.append(f"===== {args.engine} run {run_index} exit {proc.returncode} =====\n")
        log_parts.append(proc.stdout)
        if proc.stderr:
            log_parts.append("\n===== stderr =====\n")
            log_parts.append(proc.stderr)
        if proc.returncode != 0:
            build_log.write_text("".join(log_parts), encoding="utf-8")
            raise SystemExit(proc.returncode)

    built_pdf = tex.with_suffix(".pdf")
    if not built_pdf.exists():
        build_log.write_text("".join(log_parts), encoding="utf-8")
        raise SystemExit(f"Expected PDF was not produced: {built_pdf}")

    if built_pdf != output_pdf:
        if output_pdf.exists():
            output_pdf.unlink()
        built_pdf.replace(output_pdf)
    build_log.write_text("".join(log_parts), encoding="utf-8")
    print(output_pdf)


if __name__ == "__main__":
    main()
