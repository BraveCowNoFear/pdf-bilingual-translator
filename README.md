# PDF Bilingual Translator

[English](./README.md) | [简体中文](./README.zh-CN.md)

`pdf-bilingual-translator` is an agent skill for translating PDFs into polished Simplified Chinese while preserving layout, figures, tables, formulas, headers, footers, and page order. It is written for Codex-style skills, but the workflow is runtime-neutral and can be used by Claude Code, OpenCode/OpenClaw, or any agent environment that can read a `SKILL.md` folder and run local scripts.

The skill's core idea is strict reconstruction: translate the document into native LaTeX pages, reuse original PDF-derived figure assets, rebuild tables and formulas, render every page, and run four page-by-page visual QA passes before delivery.

## What Is Included

- `SKILL.md` with the coordinator, worker, artifact, and QA workflow
- `scripts/extract_pdf_blocks.py` for PDF text-block manifests and page chunks
- `scripts/extract_pdf_assets.py` for embedded images and exact page-region crops
- `scripts/compile_segment_latex.py` for stable XeLaTeX segment builds
- `scripts/render_contact_sheets.py` for page PNG renders and contact sheets
- `scripts/merge_segment_pdfs.py` for ordered segment merging
- `references/translation-layout-rules.md` with public layout and strict page-by-page QA guidance
- `agents/openai.yaml` with Codex UI metadata
- `AGENTS.md` and `CLAUDE.md` as thin adapters for other agent environments

Public releases intentionally do not bundle private or copyrighted sample PDFs/PNGs. Use your own approved bilingual sample pages as optional project-local references.

## Install

Clone or copy this repository into the skills directory for your agent runtime.

Codex on Windows:

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
git clone https://github.com/BraveCowNoFear/pdf-bilingual-translator.git (Join-Path $skills "pdf-bilingual-translator")
```

Generic Unix-like layout:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/BraveCowNoFear/pdf-bilingual-translator.git "${CODEX_HOME:-$HOME/.codex}/skills/pdf-bilingual-translator"
```

For Claude Code, OpenCode, OpenClaw, or other filesystem-based agent environments, place the repository wherever that runtime loads skills or custom instructions. `AGENTS.md` and `CLAUDE.md` are thin adapters that point back to `SKILL.md`.

## Requirements

- Python 3.10+
- PyMuPDF and Pillow:

```bash
python -m pip install -r requirements.txt
```

- XeLaTeX from TeX Live, MacTeX, or MiKTeX for final PDF builds
- A CJK-capable LaTeX setup for Simplified Chinese output

The bundled scripts are local-only and do not call external network services.

## Runtime Model

The skill uses neutral roles so it can adapt to different agents:

- `coordinator`: routes work, prepares source renders/manifests, merges segment PDFs, and decides final delivery.
- `worker`: a subagent, delegated thread, task runner, or sequential page-range pass.
- `QA worker`: an independent page-by-page review and repair pass.

If your runtime supports subagents, use parallel workers and target six translation workers per PDF when practical. If it does not, process equivalent logical shards sequentially and keep the artifact contract unchanged. Every shard must produce flat per-page renders and per-page QA records; contact sheets are only navigation aids, not QA evidence.

## Quick Script Examples

Run commands from the skill directory.

```bash
python scripts/extract_pdf_blocks.py input.pdf --doc-id mydoc --output manifests/mydoc.json --chunk-dir chunks --pages-per-chunk 8
python scripts/extract_pdf_assets.py input.pdf --out-dir segments/mydoc/001-008/assets --clips clips.json --dpi 300
python scripts/compile_segment_latex.py segments/mydoc/001-008/latex/segment.tex --output-pdf segments/mydoc/001-008/segment.pdf
python scripts/render_contact_sheets.py segments/mydoc/001-008/segment.pdf --out-dir segments/mydoc/001-008/pass_1 --dpi 150 --flat-pages
python scripts/merge_segment_pdfs.py --segments-dir segments/mydoc --output-pdf output/pdf/mydoc_zh.pdf
```

## Suggested GitHub Topics

`codex-skill`, `agent-skill`, `pdf-translation`, `latex`, `bilingual`, `simplified-chinese`, `visual-qa`, `pymupdf`

## License

MIT. See `LICENSE`.
