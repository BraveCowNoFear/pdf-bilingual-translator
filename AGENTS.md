# Agent Runtime Adapter

When an agent runtime reads this repository as project instructions, treat `SKILL.md` as the authoritative workflow.

- Resolve bundled scripts and references relative to this repository root.
- Create translation job workspaces outside the repository or under ignored output folders such as `tmp/`, `segments/`, `merged/`, and `output/`.
- Use delegated workers when the runtime supports them. If it does not, process page shards sequentially while preserving the same artifact contract and QA gates.
- Do not call third-party translation services unless the user explicitly approves.
