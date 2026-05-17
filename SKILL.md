---
name: pdf-bilingual-translator
description: Translate one or more PDFs into polished Simplified Chinese while preserving layout, headers/footers, original figures, tables, formulas, and visual style. Use when Codex, Claude Code, OpenCode/OpenClaw, or another agent runtime needs PDF translation, bilingual technical/proper terms, LaTeX/PDF output, figure/table label translation, or page-by-page visual QA. Works with subagents/workers when available and can fall back to sequential shards when the runtime has no delegation.
---

# PDF Bilingual Translator

Translate PDFs into polished Simplified Chinese by rebuilding the document as native LaTeX while preserving the original page geometry, figures, tables, formulas, and visual style.

## Runtime Compatibility

Use these terms generically:

- `coordinator`: the agent instance that receives the user request and owns routing, merging, and final delivery.
- `worker`: a delegated subagent, a separate thread, a task runner, or a sequential work pass over one page shard.
- `QA worker`: an independent review/fix pass. If the runtime supports fresh subagents, spawn fresh QA workers. If it does not, reset context as much as possible and review from rendered pages plus source pages, not from translation notes.

If the runtime supports subagents or parallel workers, use the maximum practical number allowed by the environment. If it does not, keep the same artifact contract and quality gates, but process shards sequentially.

Do not rely on Codex-specific tool names. Resolve `scripts/`, `references/`, and `assets/` relative to this skill directory in whatever skill/plugin layout the runtime uses.

## Non-Negotiables

- Do not call third-party translation services unless the user explicitly approves.
- Keep original headers and footers unchanged by default.
- Preserve original figures, charts, screenshots, page sizes, page order, and overall visual style.
- Rebuild body text, captions, tables, and formulas from scratch in LaTeX.
- Translate visible body text, captions, table text, form labels, callouts, and figure-internal labels.
- Render technical/proper terms as bilingual: `中文术语 (English term)`.
- Extract/crop figures and graphical chart assets from the original PDF, edit labels with controlled masks/overlays, and insert those assets into the LaTeX source.
- Never use a whole-page source PDF as the translated page background.
- Never represent translation results, QA results, or worker deliverables as JSON only. Success is proven by buildable LaTeX, used assets, compiled PDFs, page PNGs, and concise notes.

## Coordinator Workflow

1. Copy input PDFs into `tmp/pdfs/<job>/inputs/`.
2. Render source pages and extract block/asset helper manifests.
3. Split each PDF into disjoint continuous page ranges sized for the available worker capacity.
4. Assign each worker one page range.
5. Require each worker to return a self-contained LaTeX segment project, complete assets, `segment.pdf`, source page PNGs, pass 1 PNGs, pass 2 PNGs, and a completion note.
6. Reject incomplete segments and rerun or reassign them. Do not silently replace worker-local production or QA.
7. Merge only segments that passed worker-local QA pass 1 and pass 2.
8. Start independent QA pass 3 after all translation workers finish and the document is merged.
9. Start independent QA pass 4 after pass 3 fixes are closed.
10. Deliver final PDFs only after all four page-level render passes exist and no blocking defects remain.

The coordinator may inspect artifacts and spot-check routing decisions. It must not become the only page-by-page translator or visual reviewer unless the runtime has no worker capability; in that fallback, keep shard-local artifacts and the same QA gates.

## Translation Worker Workflow

Each worker owns one page range and must complete the full local loop:

1. Read only its work package: source PDF, source page PNGs, block/asset helper manifests, style reference, and scripts.
2. Translate every visible body/caption/table/figure label in its range into Simplified Chinese with bilingual technical/proper terms.
3. Extract or crop original figure/chart assets from its range and create masked bilingual figure assets as needed.
4. Write complete page-range LaTeX from scratch: text, headings, formulas, tables, captions, figure placement, and footnotes.
5. Build its own `segment.pdf`.
6. Render every assigned page to PNG.
7. Perform visual QA pass 1 page by page against the original source PNGs, patch LaTeX/assets/layout, rebuild, and rerender affected pages.
8. Perform visual QA pass 2 page by page, patch/rebuild/rerender until no blocking defects remain.
9. Return the complete LaTeX project, figure assets, compiled segment PDF, pass 1 PNGs, pass 2 PNGs, and a concise completion note.

LaTeX source references images with `\includegraphics{...}`; the compiled PDF embeds those image bytes. Workers must return both the LaTeX project and every referenced asset, plus `segment.pdf` as proof that the project builds.

## Independent QA Passes

After all translation workers complete and the coordinator merges the document:

- Pass 3 workers inspect the merged final PDF page by page, render pages themselves or use the merged render folder, and compare against source page PNGs.
- On any `critical` or `major` defect, the QA worker directly edits the responsible segment's `latex/segment.tex` and assets, rebuilds that segment, rerenders affected pages, and asks the coordinator to remerge.
- Pass 4 is acceptance QA. Any remaining `critical` or `major` defect blocks delivery and must be fixed before final delivery.

Do not create extra repair workers for pass 3/4 defects. The QA worker that finds a defect owns the direct fix, rebuild, and rerender loop for its assigned pages.

## Sharding

Prefer continuous page ranges sized to saturate available workers:

- 1-20 pages: one worker per 3-5 pages.
- 21-80 pages: one worker per 6-10 pages.
- Dense tables/equations/landscape pages: smaller shards.
- Multi-PDF jobs: shard each PDF independently but dispatch across all PDFs to fill worker capacity.

Never assign overlapping pages to translation workers.

## Artifact Contract

Each translation worker writes a self-contained LaTeX segment project:

```text
segments/<doc_id>/<start>-<end>/
  latex/
    segment.tex
  assets/
    figures/
    masks/
  segment.pdf
  source/page_###.png
  pass_1/page_###.png
  pass_2/page_###.png
  build.log
```

Required properties:

- `latex/segment.tex` is the source of truth for the full page range and must compile without coordinator rewriting.
- `assets/figures/` and `assets/masks/` contain only assets referenced by `segment.tex`.
- `segment.pdf` page count exactly equals `end - start + 1`.
- `source/page_###.png` are original PDF renderings for the assigned absolute page numbers.
- `pass_1/page_###.png` and `pass_2/page_###.png` are rendered from the translated segment after each worker QA pass.

After merge, the coordinator writes:

```text
merged/<doc_id>/
  final.pdf
  source/page_###.png
  pass_3/page_###.png
  pass_4/page_###.png
  build.log
```

Coordinator-side helper manifests from scripts are allowed for preparation and routing, but they are not translation deliverables and must not replace visual inspection.

## Build Tools

Use bundled scripts as low-level helpers. Workers may call them directly.

Extract text blocks for worker context and page sharding:

```bash
python scripts/extract_pdf_blocks.py input.pdf --doc-id mydoc --output manifests/mydoc.json --chunk-dir chunks --pages-per-chunk 8
```

Extract original figure/chart assets or exact page-region crops:

```bash
python scripts/extract_pdf_assets.py input.pdf --out-dir segments/mydoc/001-008/assets --clips clips.json --dpi 300
```

Compile a segment LaTeX project:

```bash
python scripts/compile_segment_latex.py segments/mydoc/001-008/latex/segment.tex --output-pdf segments/mydoc/001-008/segment.pdf
```

Render source pages or translated pages to flat page PNGs for QA:

```bash
python scripts/render_contact_sheets.py input.pdf --out-dir segments/mydoc/001-008/source --dpi 150 --page-from 1 --page-to 8 --flat-pages
python scripts/render_contact_sheets.py segments/mydoc/001-008/segment.pdf --out-dir segments/mydoc/001-008/pass_1 --dpi 150 --flat-pages
```

Merge completed segment PDFs:

```bash
python scripts/merge_segment_pdfs.py --segments-dir segments/mydoc --output-pdf output/pdf/mydoc_zh.pdf
```

## Visual QA Rules

Every visual QA pass is page-by-page, not contact-sheet-only.

Check each page for:

- blank pages, wrong orientation, page order errors, or missing headers/footers;
- lost, redrawn, or degraded figures/tables/formulas;
- formulas not rebuilt in LaTeX or rendered with broken glyphs;
- tables not rebuilt as LaTeX tables when they contain translatable text;
- figure/chart assets not sourced from the original PDF;
- visible original English body text that should be translated;
- translated text overflow, clipping, overlap, or unreadable font size;
- bad masks, gray blocks on white body text, broken table rules, or covered figure content;
- untranslated chart/table/figure labels;
- encoding artifacts such as `????`, replacement characters, private-use glyph boxes, or mojibake.

Blocking defects:

- `critical`: page blank, wrong page, lost figure/table/formula, unreadable page, compile/render failure.
- `major`: untranslated body/caption/table text, severe overlap/clipping, obvious bad mask, wrong technical meaning.
- `minor`: cosmetic alignment issues that do not harm readability.

No final delivery with open `critical` or `major` defects.

## Style Reference

Read `references/translation-layout-rules.md` before the first production pass. If a project provides its own approved bilingual sample pages in `assets/` or a user-supplied reference folder, inspect those samples first and treat them as the style anchor.

The default style pattern is:

- keep headers and footers visually consistent with the source and untranslated unless requested otherwise;
- preserve original figures and charts, adding bilingual labels with controlled masks or adjacent overlays;
- rebuild tables and formulas as native LaTeX;
- translate captions and body text into Chinese while keeping technical/proper terms bilingual;
- compare rendered translated pages against source page images after every pass.

## LaTeX Production Rules

- Build the final document as real LaTeX pages with original PDF-derived figure assets.
- Recreate headings, paragraphs, lists, equations, tables, captions, footnotes, and cross references in LaTeX.
- Use original PDF images for figures/charts: crop or extract them, then mask English labels only where needed and overlay bilingual labels.
- For diagrams with embedded English labels, keep the original visual geometry and add `中文 (English)` labels using controlled masks or adjacent overlays.
- For tables, rebuild the grid and text in LaTeX when the table has translatable content. Do not use screenshot tables as the final table representation.
- For formulas, write LaTeX math explicitly. Do not accept PDF-extracted private-use glyphs, mojibake, square boxes, or `????` artifacts.
- Do not redraw original figures with TikZ or a new diagram unless the source figure cannot be recovered and the user approves.
- Do not write Chinese LaTeX or JSON through shell here-strings in environments with uncertain encoding. Write UTF-8 files directly and compile/read them as UTF-8.

## Failure Gates

- A segment without buildable `latex/segment.tex`, complete assets, `segment.pdf`, source PNGs, pass 1 PNGs, and pass 2 PNGs is not mergeable.
- Missing assets referenced by LaTeX block merge.
- Any page missing pass 1 or pass 2 PNGs blocks merge.
- Translation workers must finish before independent QA pass 3 starts.
- Pass 3 and pass 4 must be independent of the translation pass whenever the runtime supports that separation.
- QA workers directly modify LaTeX/assets and rebuild/rerender when they find blocking defects.
- Any open `critical` or `major` defect blocks delivery.
