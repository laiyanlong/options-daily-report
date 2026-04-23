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
