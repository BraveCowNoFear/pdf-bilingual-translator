# Claude Code Adapter

Use `SKILL.md` as the source of truth for this skill.

Claude Code can map the skill's neutral roles as follows:

- `coordinator`: the current Claude Code session.
- `worker`: a delegated agent/thread when available, targeting six translation workers per PDF when practical, or a sequential logical page-range pass.
- `QA worker`: an independent review/fix pass from rendered pages and source pages.

Keep job artifacts outside the repository or under ignored output folders. Resolve helper scripts from `scripts/` and layout guidance from `references/translation-layout-rules.md`. Every QA pass must use flat per-page PNG evidence and per-page QA records; contact sheets do not count as QA evidence.
