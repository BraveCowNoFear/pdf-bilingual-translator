# PDF Bilingual Translator

[English](./README.md) | [简体中文](./README.zh-CN.md)

`pdf-bilingual-translator` 是一个 agent skill，用于把 PDF 翻译成排版精良的简体中文，同时保留原文版式、图片、表格、公式、页眉页脚和页序。它兼容 Codex 的 skill 目录结构，但工作流本身不绑定 Codex，也可以给 Claude Code、OpenCode/OpenClaw 或任何能读取 `SKILL.md` 并运行本地脚本的 agent 环境使用。

核心思路是严格重建：用 LaTeX 原生重排正文、表格和公式，复用从原 PDF 提取/裁切的图像资产，逐页渲染，再做视觉 QA 后交付。

## 仓库内容

- `SKILL.md`：coordinator、worker、artifact、QA 工作流
- `scripts/extract_pdf_blocks.py`：提取 PDF 文本块清单和分页 chunk
- `scripts/extract_pdf_assets.py`：提取嵌入图片和精确页面区域裁切
- `scripts/compile_segment_latex.py`：稳定编译 XeLaTeX segment
- `scripts/render_contact_sheets.py`：渲染页面 PNG 和 contact sheet
- `scripts/merge_segment_pdfs.py`：按页序合并 segment PDF
- `references/translation-layout-rules.md`：公开版版式与 QA 规则
- `agents/openai.yaml`：Codex UI 元数据
- `AGENTS.md` 和 `CLAUDE.md`：其他 agent 环境的薄适配入口

公开仓库不会附带私有或可能有版权的样例 PDF/PNG。实际项目中可以把你自己的已授权双语样例页作为项目本地参考。

## 安装

把仓库 clone 或复制到你的 agent runtime 的 skills 目录。

Codex on Windows:

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $HOME ".codex\skills" }
git clone https://github.com/BraveCowNoFear/pdf-bilingual-translator.git (Join-Path $skills "pdf-bilingual-translator")
```

通用 Unix-like 目录：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/BraveCowNoFear/pdf-bilingual-translator.git "${CODEX_HOME:-$HOME/.codex}/skills/pdf-bilingual-translator"
```

Claude Code、OpenCode、OpenClaw 或其他基于文件系统的 agent 环境，可以把本仓库放到对应 runtime 加载 skill/custom instruction 的目录。`AGENTS.md` 和 `CLAUDE.md` 是薄适配入口，最终都指向 `SKILL.md`。

## 依赖

- Python 3.10+
- PyMuPDF 和 Pillow：

```bash
python -m pip install -r requirements.txt
```

- TeX Live、MacTeX 或 MiKTeX 提供的 XeLaTeX
- 可输出简体中文的 CJK LaTeX 环境

内置脚本只在本地运行，不会调用外部网络服务。

## Runtime 模型

这个 skill 用中性的角色名适配不同 agent：

- `coordinator`：分配任务、准备原文渲染和 manifest、合并 segment PDF，并决定是否交付。
- `worker`：可以是 subagent、独立线程、任务 runner，也可以是顺序执行的一个页码分片。
- `QA worker`：独立逐页审查和修复 pass。

如果 runtime 支持 subagent，就并行分片；如果不支持，就顺序处理同样的分片，但保持 artifact contract 和 QA gate 不变。

## 快速脚本示例

在 skill 根目录运行：

```bash
python scripts/extract_pdf_blocks.py input.pdf --doc-id mydoc --output manifests/mydoc.json --chunk-dir chunks --pages-per-chunk 8
python scripts/extract_pdf_assets.py input.pdf --out-dir segments/mydoc/001-008/assets --clips clips.json --dpi 300
python scripts/compile_segment_latex.py segments/mydoc/001-008/latex/segment.tex --output-pdf segments/mydoc/001-008/segment.pdf
python scripts/render_contact_sheets.py segments/mydoc/001-008/segment.pdf --out-dir segments/mydoc/001-008/pass_1 --dpi 150 --flat-pages
python scripts/merge_segment_pdfs.py --segments-dir segments/mydoc --output-pdf output/pdf/mydoc_zh.pdf
```

## 建议 GitHub Topics

`codex-skill`, `agent-skill`, `pdf-translation`, `latex`, `bilingual`, `simplified-chinese`, `visual-qa`, `pymupdf`

## 许可证

MIT，见 `LICENSE`。
