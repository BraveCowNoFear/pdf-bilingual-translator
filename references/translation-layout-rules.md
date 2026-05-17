# Translation Layout Rules

Use this reference as the default style anchor for PDF translation tasks that require preserved figures, native LaTeX tables/formulas, and bilingual technical terms.

If the user provides approved bilingual sample pages, inspect those samples first and let them override this generic guide. Public releases of this skill intentionally do not bundle private or copyrighted sample PDFs/PNGs.

## Required Layout Pattern

- Keep headers and footers unchanged from the source page. Do not translate them unless the user explicitly asks.
- Do not use a whole-page PDF background for translated pages.
- Do not redraw figures. Preserve original figure imagery and overlay Chinese labels only where needed.
- Rebuild translatable tables as LaTeX tables, not screenshots.
- Rebuild formulas as explicit LaTeX math, not copied PDF glyphs.
- Translate captions and body text into Chinese while keeping technical/proper terms bilingual.
- Use page-by-page visual QA after rendering, not only text extraction checks.

## Figure Handling

- Prefer embedded image extraction when the source PDF contains usable figure assets.
- Use page-region crops for charts, screenshots, and diagrams whose embedded assets are fragmented or unavailable.
- Preserve geometry, axis scales, colors, legends, and visual emphasis from the source.
- Mask only the English label area that must be replaced. Avoid large white or gray rectangles that cover figure content.
- Add bilingual labels as `中文 (English)` when the original label is important for traceability.

## Table Handling

- Rebuild tables as LaTeX when cells contain translatable text, formulas, units, or structured data.
- Preserve row/column grouping, notes, units, and emphasis.
- Keep numerical values unchanged unless the user explicitly asks for unit conversion.
- Use screenshot tables only for non-translatable visual tables, and document why they were kept as images.

## Formula Handling

- Rebuild formulas as explicit LaTeX math.
- Preserve variable names, equation numbers, references, and surrounding explanatory text.
- Fix extracted glyph issues before accepting a page. Private-use symbols, square boxes, replacement characters, and `????` are blocking defects.

## Visual Density

- Match the source page's approximate text density, margins, figure placement, and heading hierarchy.
- Prefer slight wording compression over tiny unreadable Chinese text.
- If a translated paragraph cannot fit safely, adjust local layout, split lines, or rebalance nearby whitespace; do not cover adjacent content.
