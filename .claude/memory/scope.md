# Scope of this repository

## In scope (edit freely via PR)

| Path | Purpose |
|---|---|
| `README.md` | Public documentation |
| `LICENSE` | CC BY-NC 4.0 for data + proprietary note for source |
| `dashboard/index.html` | Static web viewer (served by GitHub Pages) |
| `.gitignore` | Repo hygiene |
| `.claude/` | Claude Code context for contributors |

## Out of scope (auto-generated, do not edit by hand)

| Path | Why |
|---|---|
| `reports/YYYY-MM-DD.md` | Written by the daily-report workflow |
| `reports/weekly_summary_*.md` | Written by the weekly-summary workflow |
| `reports/README.md` | Auto-regenerated index |
| `dashboard/data.json` | Written by dashboard workflow |
| `dashboard/weekly_summary.json` | Written by weekly-summary workflow |

Any manual edit to the "out of scope" files will be silently overwritten
on the next cron run. If you have data quality issues, open an issue
instead of editing.

## What is NOT here (lives in a private repo)

- `generate_report.py`, `ai_analysis.py`, `weekly_summary.py`, and all
  other analysis source code
- The 3 GitHub Actions workflows that produce the data
- Unit tests and backtest engine

These were moved to a private repository in April 2026 for commercial
reasons. See `LICENSE` for licensing of the source code (proprietary).
