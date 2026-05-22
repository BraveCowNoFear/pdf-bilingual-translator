---
name: pdf-bilingual-translator
description: Translate one or more PDFs into polished Simplified Chinese while preserving layout, headers/footers, original figures, tables, formulas, and visual style. Use when Codex receives PDFs and the user asks for Chinese translation, bilingual technical/proper terms, LaTeX/PDF output, figure/table label translation, or strict page-by-page visual QA with subagents.
---

# PDF Bilingual Translator

## Non-Negotiables

- Use 6 subagents for each PDF file.
- The main agent is a coordinator only: prepare sources, shard pages, dispatch workers, merge segment PDFs, spawn independent QA batches, and deliver.
- Do not let the main agent translate full documents or replace worker-local visual QA.
- Do not call third-party translation services unless the user explicitly approves.
- Keep original headers and footers unchanged by default.
- Preserve original figures, charts, screenshots, page sizes, page order, and overall visual style.
- Rebuild body text, captions, tables, and formulas from scratch in LaTeX. Final production must be native LaTeX composition plus original PDF-derived figure assets.
- Translate visible body text, captions, table text, form labels, callouts, and figure-internal labels.
- Render technical/proper terms as bilingual: `中文术语 (English term)`.
- Extract/crop figures and graphical chart assets from the original PDF, edit labels with controlled masks/overlays, and insert those assets into the LaTeX source.

## Architecture

### Main Coordinator

The main agent must:

1. Copy input PDFs into `tmp/pdfs/<job>/inputs/`.
2. Render source pages and extract block/asset helper materials for sharding and worker context.
3. Spawn 6 translation workers for each PDF file.
4. Assign each translation worker a disjoint continuous page range that maps to exactly one segment directory.
5. Wait only to collect completed segment LaTeX projects and segment PDFs.
6. Reject incomplete segments and reassign them to a fresh worker; never silently replace worker-local production or QA.
7. Merge only segments that passed worker-local QA pass 1 and pass 2 with one PNG and one QA report record per assigned page.
8. Close or let translation workers finish before starting independent QA.
9. Spawn a fresh QA worker batch for round 3. Assign QA ownership by whole segment only: a QA worker may own one or more complete segment directories, but no segment may be split across QA workers in the same pass. Those workers visually inspect pages and directly modify responsible segment LaTeX/assets, rebuild, and rerender.
10. Spawn a fresh QA worker batch for round 4 after round 3 fixes. Round 4 uses the same whole-segment ownership rule, and workers again directly patch LaTeX/assets if any defects remain.
11. Deliver final PDFs only after all four page-level render passes exist, every page has individual pass evidence and a per-page QA record, and no defects remain.

The main agent may inspect artifacts and spot-check only to decide routing. It must not become the primary page-by-page visual reviewer. If a worker returns only multi-page contact sheets, gallery screenshots, or a paragraph-level summary, the main agent must mark the pass incomplete and send the same worker back to produce individual page evidence.

### Translation Worker

Each translation worker owns one page range and must complete the whole local loop:

1. Read only its work package: source PDF, source page PNGs, block/asset helper materials, approved sample reference, and scripts.
2. Translate every visible body/caption/table/figure label in its range into Simplified Chinese with bilingual technical/proper terms.
3. Extract or crop original figure/chart assets from its range and create masked bilingual figure assets as needed.
4. Write complete page-range LaTeX from scratch: text, headings, formulas, tables, captions, figure placement, and footnotes.
5. Build its own `segment.pdf` from that LaTeX.
6. Render every assigned page to PNG.
7. Perform visual QA pass 1 page by page against the original source PNGs, using one translated PNG per assigned page. Patch LaTeX/assets/layout, rebuild, rerender affected pages, and write a per-page pass 1 QA report.
8. Perform visual QA pass 2 page by page using one translated PNG per assigned page. Patch/rebuild/rerender until no defects remain, and write a per-page pass 2 QA report.
9. Return the complete LaTeX project, figure assets, compiled segment PDF, pass 1 PNGs, pass 2 PNGs, pass 1/2 per-page QA reports, and a concise completion note.

LaTeX source references images with `\includegraphics{...}`; the compiled PDF embeds those image bytes. Therefore workers must return both the LaTeX project and every referenced asset, plus `segment.pdf` as proof that the project builds.

### Independent QA Workers

After all translation workers complete and the main coordinator merges the document:

- Spawn a new QA worker batch for pass 3. These workers must not inherit translation-worker context.
- Assign QA workers by complete segment ranges, not arbitrary page slices. A QA worker may receive multiple complete segments if needed, but two QA workers must never edit the same segment in the same pass.
- QA workers inspect the merged final PDF page by page for every page in their assigned segment range(s), with exactly one translated PNG per assigned absolute page number, and compare each page against its matching source page PNG.
- On any defect, including `minor`, the QA worker directly edits the responsible segment's `latex/segment.tex` and assets, rebuilds that segment, rerenders affected pages, and asks the coordinator to remerge.
- Spawn another fresh QA worker batch for pass 4 after pass 3 fixes are closed.
- Pass 4 is acceptance QA. Any remaining defect, including `minor`, blocks delivery and must be fixed by that QA worker before final delivery.

Do not create extra repair subagents for pass 3/4 defects. The QA worker that finds the defect owns the direct fix, rebuild, and rerender loop for its assigned pages.

QA workers must return per-page QA reports for their assigned segment range(s). A QA worker report that summarizes multiple pages without one record per page is incomplete and must be rejected.

## Sharding

Split each PDF into 6 disjoint continuous page ranges:

- For dense tables/equations/landscape pages, keep those pages in shorter ranges by moving neighboring easier pages into other ranges.
- Never assign overlapping pages to translation workers.
- Pass 3 and pass 4 QA sharding must reuse these complete segment ranges as the ownership unit. Do not split a segment across multiple QA workers; if worker budget is tight, assign multiple complete segments to one QA worker.

For multi-PDF jobs, shard each PDF independently and assign 6 workers to each PDF.

## Artifact Contract

Each translation worker writes a self-contained LaTeX segment project:

```text
segments/<doc_id>/<start>-<end>/
  latex/
    segment.tex
  assets/
    figures/
      embedded/
    masks/
  segment.pdf
  source/page_###.png
  pass_1/page_###.png
  pass_2/page_###.png
  qa/pass_1_pages.json
  qa/pass_2_pages.json
  build.log
```

Required properties:

- `latex/segment.tex` is the source of truth for the full page range and must compile without coordinator rewriting.
- `assets/figures/` contains all referenced figure assets, including exact page-region crops and embedded PDF images under `assets/figures/embedded/`; `assets/masks/` contains mask/overlay assets referenced by `segment.tex`.
- `segment.pdf` page count exactly equals `end - start + 1`.
- `source/page_###.png` are original PDF renderings for the assigned absolute page numbers.
- `pass_1/page_###.png` and `pass_2/page_###.png` are rendered from the translated segment after each worker QA pass.
- `qa/pass_1_pages.json` and `qa/pass_2_pages.json` contain one record per assigned page. Each record must include `page`, `source_png`, `translated_png`, `status`, `defects`, `fixes_applied`, and `rerendered`.

After merge, the coordinator writes:

```text
merged/<doc_id>/
  final.pdf
  source/page_###.png
  pass_3/page_###.png
  pass_4/page_###.png
  qa/pass_3_pages.json
  qa/pass_4_pages.json
  build.log
```

Coordinator-side helper manifests from scripts are allowed for preparation and routing, but they are not translation deliverables and must not replace visual inspection. Final pass 3 and pass 4 reports must contain one record per absolute page in the merged PDF.

## Build Tools

Use these scripts as low-level helpers. Workers may call them directly.

Extract original figure/chart assets or exact page-region crops:

```bash
python scripts/extract_pdf_assets.py input.pdf --out-dir segments/mydoc/001-008/assets --dpi 300
```

Compile a segment LaTeX project. The script runs XeLaTeX twice, writes `segment.pdf`, captures `build.log`, and fails on missing output:

```bash
python scripts/compile_segment_latex.py segments/mydoc/001-008/latex/segment.tex --output-pdf segments/mydoc/001-008/segment.pdf
```

Render source pages or translated pages to flat page PNGs for QA. The `--flat-pages` flag is mandatory for QA passes; with `--flat-pages`, contact sheets are not generated unless `--contact-sheet` is explicitly set. The script name includes "contact_sheets" for legacy reasons, but QA output must be one PNG per page:

```bash
python scripts/render_contact_sheets.py input.pdf --out-dir segments/mydoc/001-008/source --dpi 150 --page-from 1 --page-to 8 --flat-pages
python scripts/render_contact_sheets.py segments/mydoc/001-008/segment.pdf --out-dir segments/mydoc/001-008/pass_1 --dpi 150 --flat-pages
python scripts/render_contact_sheets.py segments/mydoc/010-018/segment.pdf --out-dir segments/mydoc/010-018/pass_1 --dpi 150 --flat-pages --page-number-offset 9
```

When rendering a segment PDF whose first absolute source page is not page 1, pass `--page-number-offset <segment_start - 1>` so rendered QA evidence is named by absolute page number.

If a render command produces a single image containing more than one PDF page, that output is an index/contact sheet only and is invalid for QA evidence. Rerun the render with `--flat-pages` before inspection. Generate contact sheets only as explicit navigation aids, preferably outside the pass evidence directories.

Merge completed segment PDFs:

```bash
python scripts/merge_segment_pdfs.py --segments-dir segments/mydoc --output-pdf output/pdf/mydoc_zh.pdf
```

Validate the complete job artifact contract before delivery:

```bash
python scripts/validate_job_artifacts.py tmp/pdfs/<job> --write-json tmp/pdfs/<job>/output/artifact_validation.json
```

The validator must pass before delivery. It checks segment and merged PDF page counts, absolute page-numbered PNG evidence, required per-page QA JSON records, build logs, and referenced `\includegraphics{...}` assets. Contact sheets may exist as navigation aids, but the validator warns about them and never counts them as QA evidence.

## Visual QA Rules

Every visual QA pass is strictly page-by-page. This is mandatory for pass 1, pass 2, pass 3, and pass 4.

Forbidden QA shortcuts:

- Do not inspect multi-page contact sheets, montages, grids, gallery screenshots, combined screenshots, or stitched images as the primary QA evidence.
- Do not render multiple PDF pages into one PNG and call that page-level QA.
- Do not accept "I checked the batch/contact sheet and it looks fine" as a QA result.
- Do not skip pages that appear visually simple.

Required QA evidence for every pass:

- Render exactly one flat PNG per PDF page being checked, named by absolute page number: `page_001.png`, `page_002.png`, and so on.
- Open or inspect each rendered PNG individually against the matching original source PNG.
- Record a per-page result for every assigned page in that pass: `page`, `status`, `defects`, `fixes_applied`, and `rerendered`.
- If a page is patched, rerender that individual page and update the per-page result after the fix.
- A pass is incomplete if any assigned page lacks its own translated PNG, matching source PNG, or per-page QA result.

Contact sheets are allowed only as a navigation/index aid after the individual page PNGs already exist. They never count as pass 1, pass 2, pass 3, or pass 4 evidence.

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

Defect severity:

- `critical`: page blank, wrong page, lost figure/table/formula, unreadable page, compile/render failure.
- `major`: untranslated body/caption/table text, severe overlap/clipping, obvious bad mask, wrong technical meaning.
- `minor`: cosmetic alignment issues that do not harm readability. Minor defects still block final delivery until fixed.

No final delivery with any open defects.

## Sample Reference

Use the approved P5 six-page sample set before adapting style. It contains three original source pages and three translated LaTeX pages:

- Combined six-page reference PDF: `assets/p5-sample/p5_sample_reference_6_pages.pdf`
- Figure page pair: `assets/p5-sample/original_prepwork_p18.pdf` and `assets/p5-sample/translated_prepwork_p18_preserve_figure.pdf`
- Table page pair: `assets/p5-sample/original_prepwork_p26.pdf` and `assets/p5-sample/translated_prepwork_p26_table.pdf`
- Formula page pair: `assets/p5-sample/original_prepwork_p37.pdf` and `assets/p5-sample/translated_prepwork_p37_formula.pdf`
- LaTeX sources: `assets/p5-sample/p18_sample_preserve_figure.tex`, `assets/p5-sample/p26_table_sample.tex`, and `assets/p5-sample/p37_formula_sample.tex`
- PNG previews with matching filenames are in `assets/p5-sample/`.
- Notes: `references/p5-sample-comparison.md`

The sample set demonstrates the required pattern: keep headers and footers untranslated, preserve original figures, rebuild tables and formulas in LaTeX, translate captions/body text, keep technical terms bilingual, and add Chinese labels beside original image labels.

## LaTeX Production Rules

- Build the final document as real LaTeX pages with original PDF-derived figure assets.
- Recreate headings, paragraphs, lists, equations, tables, captions, footnotes, and cross references in LaTeX.
- Keep headers/footers visually consistent with the source and untranslated unless requested otherwise.
- Use original PDF images for figures/charts: crop or extract them, then mask English labels only where needed and overlay bilingual labels.
- For diagrams with embedded English labels, keep the original visual geometry and add `中文 (English)` labels using controlled masks or adjacent overlays.
- For tables, rebuild the grid and text in LaTeX when the table has translatable content. Do not use screenshot tables as the final table representation.
- For formulas, write LaTeX math explicitly. Do not accept PDF-extracted private-use glyphs, mojibake, square boxes, or `????` artifacts.
- Each worker must compare its rendered LaTeX pages against the original source page images for style, spacing, figure placement, and page density.
- Do not use a whole-page source PDF as the translated page background. Whole-page backgrounds hide formula/font failures and make body text non-native.
- Do not redraw original figures with TikZ or a new diagram unless the source figure cannot be recovered and the user approves.
- Do not write Chinese LaTeX through PowerShell here-strings. Use UTF-8 files and compile/read them directly.

## Failure Gates

- A segment without buildable `latex/segment.tex`, complete assets, `segment.pdf`, source PNGs, pass 1 PNGs, and pass 2 PNGs is not mergeable.
- Missing assets referenced by LaTeX block merge.
- Any page missing pass 1 or pass 2 PNGs blocks merge.
- Any pass 1 or pass 2 QA report missing one record per assigned page blocks merge.
- Any pass 1 or pass 2 evidence image that contains more than one PDF page blocks merge.
- Translation workers must finish before independent QA pass 3 starts.
- Pass 3 and pass 4 must be performed by fresh QA workers.
- Any pass 3 or pass 4 QA report missing one record per absolute page assigned to that QA worker blocks delivery.
- Any pass 3 or pass 4 evidence image that contains more than one PDF page blocks delivery.
- QA workers directly modify LaTeX/assets and rebuild/rerender when they find any defects.
- Any open defect, including `minor`, blocks delivery.
- `scripts/validate_job_artifacts.py tmp/pdfs/<job>` must pass before delivery.
