# Project context for Claude Code

You are working on **options-daily-report** — the **public data repository**
for the Options mobile app.

## What this repo is

A read-mostly archive of **generated artifacts**:
- `reports/YYYY-MM-DD.md` — daily options strategy reports (markdown)
- `reports/weekly_summary_YYYY-MM-DD.md` — weekly summaries
- `dashboard/data.json` — aggregate payload consumed by the mobile app
- `dashboard/weekly_summary.json` — weekly summary payload
- `dashboard/index.html` — static web viewer (GitHub Pages)

## What this repo is NOT

- **Not** a place for Python source code. The analysis engine lives in a
  separate private repo.
- **Not** a place for workflows that generate data. Those live in the
  private repo and push outputs here via a fine-grained PAT.
- **Not** for contributors modifying reports. Reports are auto-generated.

## What contributors CAN help with

- Fixing typos or formatting in README / LICENSE
- Improving `dashboard/index.html` (the static viewer)
- Reporting data quality issues (bad price, missing field, etc.)
- Translating the README to other languages
- Suggesting features via GitHub Issues

See [`.claude/memory/contributing.md`](./.claude/memory/contributing.md) for
the full contributor guide.

## Before committing

- **Never** add Python source files — those belong in the private engine repo
- **Never** modify files in `reports/` or `dashboard/*.json` by hand — they
  get overwritten on the next pipeline run
- Changes to `dashboard/index.html` are welcome
- Changes to `README.md` and `LICENSE` should go through a PR

## Language

User's primary language is 繁體中文. Respond in 繁體中文 unless the user
writes in English. Code / docs in English.


## DappGo Stocks family

This repo is part of the **DappGo Stocks** family. The coordination repo
[`dappgo-stocks-meta`](https://github.com/laiyanlong/dappgo-stocks-meta)
holds:

- [STACK.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/STACK.md) — TLDR of all 12 repos at a glance
- [CLAUDE.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/CLAUDE.md) — entry point for fresh Claude Code sessions
- [docs/ARCHITECTURE.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/ARCHITECTURE.md) — full data flow diagram
- [docs/CONVENTIONS.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/CONVENTIONS.md) — TS / Python / commit / a11y standards
- [docs/UI_DESIGN_SYSTEM.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/UI_DESIGN_SYSTEM.md) — design tokens + sync rules
- [docs/LAYOUT_PATTERNS.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/LAYOUT_PATTERNS.md) — standard screen patterns (loading/error/empty/refresh)
- [docs/WORKFLOW.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/WORKFLOW.md) — multi-repo task recipes
- [docs/INTEGRATION_STRATEGY.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/INTEGRATION_STRATEGY.md) — 5-rung migration ladder for shared code
- [docs/RELEASE.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/RELEASE.md) — release runbook
- [docs/ONBOARDING.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/ONBOARDING.md) — new dev box setup
- [docs/DEPENDENCY_FLOW.md](https://github.com/laiyanlong/dappgo-stocks-meta/blob/main/docs/DEPENDENCY_FLOW.md) — "when changing X, what else needs updating"

Cross-repo scripts at `~/git/dappgo-stocks-meta/scripts/` (status-all,
pull-all, verify-apps, deploy-mobile, run-engines, sync-shared, sync-ui,
drift-check, clone-all).
