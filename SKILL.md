---
name: pdf-bilingual-translator
description: Translate one or more PDFs into polished Simplified Chinese while preserving layout, headers/footers, original figures, tables, formulas, and visual style. Use when Codex, Claude Code, OpenCode/OpenClaw, or another agent runtime needs PDF translation, bilingual technical/proper terms, LaTeX/PDF output, figure/table label translation, or strict page-by-page visual QA. Works with subagents/workers when available and falls back to sequential logical shards.
---

# PDF Bilingual Translator

Translate PDFs into polished Simplified Chinese by rebuilding the document as native LaTeX while preserving the original page geometry, figures, tables, formulas, and visual style.

## Runtime Compatibility

Use these terms generically:

- `coordinator`: the agent instance that receives the user request and owns routing, merging, and final delivery.
- `worker`: a delegated subagent, a separate thread, a task runner, or a sequential work pass over one page shard.
- `QA worker`: an independent review/fix pass. If the runtime supports fresh subagents, spawn fresh QA workers. If it does not, reset context as much as possible and review from rendered pages plus source pages, not from translation notes.

If the runtime supports subagents or parallel workers, use the maximum practical number allowed by the environment and target six translation workers per PDF. If it does not, keep the same artifact contract and quality gates, but process the same logical shards sequentially.

Do not rely on Codex-specific tool names. Resolve `scripts/`, `references/`, and optional `assets/` relative to this skill directory in whatever skill/plugin layout the runtime uses.

## Non-Negotiables

- Use a coordinator/worker workflow. The coordinator prepares sources, shards pages, dispatches workers or sequential shard passes, merges segment PDFs, runs independent QA, and delivers.
- Target six translation workers per PDF when the runtime can support them. With fewer workers, queue the same logical shards; with no delegation, process them sequentially.
- The coordinator must not translate full documents or replace worker-local visual QA when worker capability exists.
- Do not call third-party translation services unless the user explicitly approves.
- Keep original headers and footers unchanged by default.
- Preserve original figures, charts, screenshots, page sizes, page order, and overall visual style.
- Rebuild body text, captions, tables, and formulas from scratch in LaTeX. Final production must be native LaTeX composition plus original PDF-derived figure assets.
- Translate visible body text, captions, table text, form labels, callouts, and figure-internal labels.
- Render technical/proper terms as bilingual: `中文术语 (English term)`.
- Extract/crop figures and graphical chart assets from the original PDF, edit labels with controlled masks/overlays, and insert those assets into the LaTeX source.
- Never use a whole-page source PDF as the translated page background.
- Never represent translation results, QA results, or worker deliverables as JSON only. Success is proven by buildable LaTeX, used assets, compiled PDFs, page PNGs, per-page QA records, and concise notes.

## Coordinator Workflow

1. Copy input PDFs into `tmp/pdfs/<job>/inputs/`.
2. Read `references/translation-layout-rules.md` and any approved project-local sample reference before production starts.
3. Render source pages and extract block/asset helper manifests.
4. Split each PDF into disjoint continuous page ranges sized for the available worker capacity. Target six non-empty logical shards per PDF when page count allows.
5. Assign each worker or sequential pass one page range.
6. Require each worker to return a self-contained LaTeX segment project, complete assets, `segment.pdf`, source page PNGs, pass 1 PNGs, pass 2 PNGs, pass 1/2 per-page QA reports, and a completion note.
7. Reject incomplete segments and rerun or reassign them. Do not silently replace worker-local production or QA.
8. Merge only segments that passed worker-local QA pass 1 and pass 2 with one translated PNG and one QA report record per assigned page.
9. Start independent QA pass 3 after all translation workers or sequential shard passes finish and the document is merged.
10. Start independent QA pass 4 after pass 3 fixes are closed.
11. Deliver final PDFs only after all four page-level render passes exist, every page has individual pass evidence and a per-page QA record, and no defects remain.

The coordinator may inspect artifacts and spot-check routing decisions. It must not become the only page-by-page translator or visual reviewer unless the runtime has no worker capability; in that fallback, keep shard-local artifacts and the same QA gates.

If a worker returns only multi-page contact sheets, gallery screenshots, or a paragraph-level summary, the coordinator must mark the pass incomplete and send the work back for individual page evidence.

## Translation Worker Workflow

Each worker owns one page range and must complete the full local loop:

1. Read only its work package: source PDF, source page PNGs, block/asset helper manifests, style reference, and scripts.
2. Translate every visible body/caption/table/figure label in its range into Simplified Chinese with bilingual technical/proper terms.
3. Extract or crop original figure/chart assets from its range and create masked bilingual figure assets as needed.
4. Write complete page-range LaTeX from scratch: text, headings, formulas, tables, captions, figure placement, and footnotes.
5. Build its own `segment.pdf` from that LaTeX.
6. Render every assigned page to one flat PNG per page.
7. Perform visual QA pass 1 page by page against the original source PNGs. Patch LaTeX/assets/layout, rebuild, rerender affected pages, and write a per-page pass 1 QA report.
8. Perform visual QA pass 2 page by page. Patch/rebuild/rerender until no defects remain, and write a per-page pass 2 QA report.
9. Return the complete LaTeX project, figure assets, compiled segment PDF, pass 1 PNGs, pass 2 PNGs, pass 1/2 per-page QA reports, and a concise completion note.

LaTeX source references images with `\includegraphics{...}`; the compiled PDF embeds those image bytes. Workers must return both the LaTeX project and every referenced asset, plus `segment.pdf` as proof that the project builds.

## Independent QA Passes

After all translation workers complete and the coordinator merges the document:

- Pass 3 workers inspect the merged final PDF page by page, render pages themselves or use the merged render folder, and compare against source page PNGs.
- Pass 3 workers must not inherit translation-worker context when the runtime supports isolated workers. Without isolation, reset context as much as possible and review from rendered artifacts only.
- On any defect, including `minor`, the QA worker directly edits the responsible segment's `latex/segment.tex` and assets, rebuilds that segment, rerenders affected pages, and asks the coordinator to remerge.
- Pass 4 is acceptance QA. Any remaining defect, including `minor`, blocks delivery and must be fixed before final delivery.

Do not create extra repair workers for pass 3/4 defects. The QA worker that finds a defect owns the direct fix, rebuild, and rerender loop for its assigned pages.

QA workers must return per-page QA reports for their assigned pages. A QA worker report that summarizes multiple pages without one record per page is incomplete and must be rejected.

## Sharding

Prefer continuous page ranges sized to saturate available workers:

- Target six non-empty disjoint page ranges per PDF when page count and worker capacity allow.
- For 1-5 page PDFs, use one shard per page instead of creating empty shards.
- With fewer than six workers, queue six logical shards or reduce only when page count is too small.
- Dense tables/equations/landscape pages should be shorter ranges by moving neighboring easier pages into other ranges.
- Multi-PDF jobs should shard each PDF independently and dispatch across all PDFs to fill worker capacity.

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
  qa/pass_1_pages.json
  qa/pass_2_pages.json
  build.log
```

Required properties:

- `latex/segment.tex` is the source of truth for the full page range and must compile without coordinator rewriting.
- `assets/figures/` and `assets/masks/` contain only assets referenced by `segment.tex`.
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

Use bundled scripts as low-level helpers. Workers may call them directly.

Extract text blocks for worker context and page sharding:

```bash
python scripts/extract_pdf_blocks.py input.pdf --doc-id mydoc --output manifests/mydoc.json --chunk-dir chunks --pages-per-chunk 8
```

Extract original figure/chart assets or exact page-region crops:

```bash
python scripts/extract_pdf_assets.py input.pdf --out-dir segments/mydoc/001-008/assets --dpi 300
python scripts/extract_pdf_assets.py input.pdf --out-dir segments/mydoc/001-008/assets --clips clips.json --dpi 300
```

Compile a segment LaTeX project. The script runs XeLaTeX twice, writes `segment.pdf`, captures `build.log`, and fails on missing output:

```bash
python scripts/compile_segment_latex.py segments/mydoc/001-008/latex/segment.tex --output-pdf segments/mydoc/001-008/segment.pdf
```

Render source pages or translated pages to flat page PNGs for QA. The `--flat-pages` flag is mandatory for QA passes; the script name includes `contact_sheets` for legacy reasons, but QA output must be one PNG per page:

```bash
python scripts/render_contact_sheets.py input.pdf --out-dir segments/mydoc/001-008/source --dpi 150 --page-from 1 --page-to 8 --flat-pages
python scripts/render_contact_sheets.py segments/mydoc/001-008/segment.pdf --out-dir segments/mydoc/001-008/pass_1 --dpi 150 --flat-pages --page-number-offset 0
```

For segment PDFs that start after page 1, set `--page-number-offset` to `start_page - 1` so rendered PNG filenames use absolute page numbers.

If a render command produces a single image containing more than one PDF page, that output is an index/contact sheet only and is invalid for QA evidence. Rerun the render with `--flat-pages` before inspection.

Merge completed segment PDFs:

```bash
python scripts/merge_segment_pdfs.py --segments-dir segments/mydoc --output-pdf output/pdf/mydoc_zh.pdf
```

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

## Style Reference

Read `references/translation-layout-rules.md` before the first production pass. If a project provides approved bilingual sample pages in `assets/` or a user-supplied reference folder, inspect those samples first and treat them as the style anchor.

Some local installations may include a private approved P5 sample set under `assets/p5-sample/` with matching notes under `references/p5-sample-comparison.md`. Public releases intentionally do not bundle those private/copyrighted sample PDFs or PNGs. If the sample set is absent, use the public style rules or user-supplied approved samples; do not fail because `assets/p5-sample/` is missing.

The default style pattern is:

- keep headers and footers visually consistent with the source and untranslated unless requested otherwise;
- preserve original figures and charts, adding bilingual labels with controlled masks or adjacent overlays;
- rebuild tables and formulas as native LaTeX;
- translate captions and body text into Chinese while keeping technical/proper terms bilingual;
- compare rendered translated pages against source page images after every pass.

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
- Do not write Chinese LaTeX through shell here-strings or tools with uncertain encoding. Write UTF-8 files directly and compile/read them as UTF-8.

## Failure Gates

- A segment without buildable `latex/segment.tex`, complete assets, `segment.pdf`, source PNGs, pass 1 PNGs, pass 2 PNGs, and pass 1/2 per-page QA reports is not mergeable.
- Missing assets referenced by LaTeX block merge.
- Any page missing pass 1 or pass 2 PNGs blocks merge.
- Any pass 1 or pass 2 QA report missing one record per assigned page blocks merge.
- Any pass 1 or pass 2 evidence image that contains more than one PDF page blocks merge.
- Translation workers or sequential shard passes must finish before independent QA pass 3 starts.
- Pass 3 and pass 4 must be independent of the translation pass whenever the runtime supports that separation.
- Any pass 3 or pass 4 QA report missing one record per absolute page assigned to that QA worker blocks delivery.
- Any pass 3 or pass 4 evidence image that contains more than one PDF page blocks delivery.
- QA workers directly modify LaTeX/assets and rebuild/rerender when they find any defects.
- Any open defect, including `minor`, blocks delivery.
