# Claude Code Adapter

Use `SKILL.md` as the source of truth for this skill.

Claude Code can map the skill's neutral roles as follows:

- `coordinator`: the current Claude Code session.
- `worker`: a delegated agent/thread when available, or a sequential page-range pass.
- `QA worker`: an independent review/fix pass from rendered pages and source pages.

Keep job artifacts outside the repository or under ignored output folders. Resolve helper scripts from `scripts/` and layout guidance from `references/translation-layout-rules.md`.
