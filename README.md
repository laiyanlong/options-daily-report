# Options Daily Report — Data

**Read in:** [English](README.md) · [繁體中文](README.zh-TW.md)

[![Schema Check](https://github.com/laiyanlong/options-daily-report/actions/workflows/schema-check.yml/badge.svg)](https://github.com/laiyanlong/options-daily-report/actions/workflows/schema-check.yml)
[![Guard — no Python](https://github.com/laiyanlong/options-daily-report/actions/workflows/guard-no-python.yml/badge.svg)](https://github.com/laiyanlong/options-daily-report/actions/workflows/guard-no-python.yml)
[![Licence: CC BY-NC 4.0](https://img.shields.io/badge/Licence-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

Published output data for the **Options** mobile app.

This repository contains only the **generated artifacts** of our options analysis
pipeline. The analysis engine itself is proprietary and not open-source.

## Contents

```
reports/
  YYYY-MM-DD.md                 — Daily strategy reports (markdown)
  weekly_summary_YYYY-MM-DD.md  — Weekly review + next-week outlook

dashboard/
  data.json                     — Latest aggregate dashboard payload
  weekly_summary.json           — Latest weekly summary payload
  index.html                    — Static dashboard viewer (GitHub Pages)
```

## Update schedule

| File | Cadence | Time (UTC) |
|------|---------|------------|
| `reports/YYYY-MM-DD.md` | Weekdays | 13:20 |
| `reports/weekly_summary_*.md` | Sundays | 18:00 |
| `dashboard/*.json` | After each daily/weekly run | 13:25 / 18:05 |

## Licence

### Data & reports — **CC BY-NC 4.0**

You may view, share, and reference the published reports for **personal,
non-commercial** use with attribution to `options.laiyanlong.dev`.
Commercial redistribution, resale, or use for training AI/ML models
requires a separate written licence.

### Analysis source code — **Proprietary (All Rights Reserved)**

The source code that generates these reports is maintained in a private
repository and is not licensed for public use. The methodology (Black-Scholes
modelling, CP scoring, OI clustering, timing signals, AI commentary pipeline)
is proprietary.

## Disclaimer

Reports are **educational** and for **informational purposes only**. They do
not constitute investment advice, a solicitation to buy or sell securities,
or a recommendation to employ any specific strategy. Options trading carries
substantial risk of loss. Consult a licensed financial advisor before making
any investment decision.

## Get the app

Options mobile app (iOS) — currently in private beta. Coming to the
App Store soon.

---

© 2026 Yan Long Lai. All rights reserved.
