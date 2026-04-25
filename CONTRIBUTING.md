# Contributing

Thanks for your interest in **options-daily-report**.

This repository is a **public, data-only archive** of generated artifacts
from a private options analysis engine. That shape constrains what we
accept — please read below before opening a PR.

## This repo is auto-generated

Daily and weekly reports, `dashboard/*.json`, and the reports index are
written by scheduled GitHub Actions in the private engine repo and pushed
here via a fine-grained PAT. **Manual edits to those files will be
silently overwritten on the next pipeline run.**

Full scope list: [`.claude/memory/scope.md`](./.claude/memory/scope.md).

## What we welcome

- **README typo fixes** (`README.md`, `README.zh-TW.md`)
- **README translations** into new languages (please also wire the
  language switcher line at the top of each README)
- **`dashboard/index.html` improvements** — accessibility, mobile
  layout, performance, minor visual polish
- **Bug reports for data quality issues** (bad price, missing field,
  schema drift) — file an issue rather than editing a report
- **Feature requests** via GitHub Issues

## What is out of scope

| Path | Why rejected |
|---|---|
| `*.py`, `requirements*.txt`, `pyproject.toml`, `setup.py` | Python source belongs in the private engine repo. CI blocks this via `.github/workflows/guard-no-python.yml`. |
| `reports/**` | Auto-generated; edit the engine instead. |
| `dashboard/data.json`, `dashboard/weekly_summary.json`, `dashboard/manifest.json` | Auto-generated each run. |
| `dashboard/ai_commentary/**` | Auto-generated each run. |
| `schemas/*.schema.json` | Coordinated releases only — changes ripple into the mobile app. See [`schemas/VERSIONING.md`](./schemas/VERSIONING.md) and [`docs/COMPAT.md`](./docs/COMPAT.md). |

If you want to contribute to the analysis engine (CP scoring, Greeks,
timing signals, AI commentary pipeline, etc.), note that the code is
proprietary and not open-source.

## Opening a pull request

1. Fork, branch, commit, push — the usual flow
2. Keep the diff small and surgical — don't reformat unrelated code
3. For README changes touching both languages, update both files so the
   language switcher stays symmetrical
4. For `index.html` changes, verify manually against
   `https://laiyanlong.github.io/options-daily-report/dashboard/` first
5. CI runs:
   - `guard-no-python.yml` — rejects any Python file
   - `schema-check.yml` — validates `schemas/*.schema.json`
   - `contract-test.yml` — verifies `dashboard/*.json` still matches schema

## Filing an issue

Use one of the templates under [`.github/ISSUE_TEMPLATE/`](./.github/ISSUE_TEMPLATE):

- **Bug report** — for data quality issues and dashboard bugs
- **Feature request** — for new dashboard views, schema additions, etc.

## Code of conduct

Be excellent to each other. Technical disagreements are welcome;
personal attacks are not.

## Licence

Contributions are accepted under the licence of the file you are editing:
- `README*.md`, `dashboard/index.html`, `schemas/*`: CC BY-NC 4.0
- All new contributions inherit the file's existing licence unless the PR
  description says otherwise

See [`LICENSE`](./LICENSE) for details.
