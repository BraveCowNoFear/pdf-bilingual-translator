# P5 Sample Comparison

Use this sample set as the style anchor for future PDF translation tasks that require preserved figures, native LaTeX tables/formulas, and bilingual technical terms.

Files:

- `../assets/p5-sample/p5_sample_reference_6_pages.pdf` - combined reference: original p18, translated p18, original p26, translated p26, original p37, translated p37.
- `../assets/p5-sample/original_prepwork_p18.pdf` and `../assets/p5-sample/translated_prepwork_p18_preserve_figure.pdf` - figure-heavy page pair.
- `../assets/p5-sample/original_prepwork_p26.pdf` and `../assets/p5-sample/translated_prepwork_p26_table.pdf` - table-heavy page pair.
- `../assets/p5-sample/original_prepwork_p37.pdf` and `../assets/p5-sample/translated_prepwork_p37_formula.pdf` - formula-heavy page pair.
- `../assets/p5-sample/p18_sample_preserve_figure.tex`, `../assets/p5-sample/p26_table_sample.tex`, and `../assets/p5-sample/p37_formula_sample.tex` - hand-tuned LaTeX sources.
- PNG previews with matching filenames live beside the PDFs.

Observed requirements from the approved sample set:

- Keep headers and footers unchanged from the source page. Do not translate them unless the user explicitly asks.
- Do not use a whole-page PDF background for translated pages.
- Do not redraw figures. Preserve original figure imagery and overlay Chinese labels only where needed.
- Rebuild translatable tables as LaTeX tables, not screenshots.
- Rebuild formulas as explicit LaTeX math, not copied PDF glyphs.
- Translate captions and body text into Chinese while keeping technical/proper terms bilingual.
- Use page-by-page visual QA after rendering, not only text extraction checks.
