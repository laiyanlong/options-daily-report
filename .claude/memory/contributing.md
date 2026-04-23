# Contributing to options-daily-report

This is a data repository, not an engine. Here's what you can help with
and how.

## What we welcome

| Type | Examples |
|---|---|
| Bug reports | "data.json is missing `live_prices` today" / "report for 2026-04-22 has a broken table" |
| Documentation | README typos, translation, clarification of licensing |
| Dashboard viewer | Improvements to `dashboard/index.html` — accessibility, dark mode, mobile layout |
| Feature suggestions | New data fields, additional tickers, export formats — file an issue |

## What we don't accept

- PRs adding Python code → belongs in the private engine repo
- Manual edits to `reports/*.md` or `dashboard/*.json` → auto-regenerated
- Unauthorized forks for commercial redistribution → violates CC BY-NC

## Pull request checklist

- [ ] Changes are limited to: `README.md`, `LICENSE`, `dashboard/index.html`, `.claude/`, `.gitignore`
- [ ] Commit message uses conventional prefix (`docs:`, `fix:`, `style:`, `feat:`)
- [ ] One logical change per PR
- [ ] README changes: preview renders correctly
- [ ] Dashboard changes: tested on GitHub Pages preview

## Issue templates

**Data quality issue:**
```
Date of affected report: YYYY-MM-DD
Field or section: e.g. dashboard/data.json → timing.TSLA.action
Expected: …
Actual: …
Impact on your use case: …
```

**Feature request:**
```
Problem: what's painful today?
Proposed addition: new field in data.json / new report section / …
Why this repo (vs your own fork): …
```

## Licensing reminder

All data contributions become CC BY-NC 4.0. All code contributions (e.g.,
`dashboard/index.html`) become proprietary upon merge. By opening a PR
you agree to assign copyright to the repo owner.
