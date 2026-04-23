# Improve `dashboard/index.html`

The static HTML viewer at `dashboard/index.html` is the one bit of actual
code contributors can freely improve.

## What it does

Served via GitHub Pages at https://laiyanlong.github.io/options-daily-report/.
Loads `dashboard/data.json` client-side and renders a simple viewer for
users who don't use the mobile app.

## Typical improvements that get accepted

- Dark mode toggle
- Better mobile responsive layout
- Accessibility (ARIA labels, keyboard nav, color contrast)
- Performance (lazy loading, image optimization)
- i18n (add language selector, at least en / zh)
- Chart improvements — we use no chart libs today; contributors could add
  Chart.js or ApexCharts for prices/OI visualizations

## Not accepted

- Rewrites to React / Vue / Svelte (keep it vanilla for zero build step)
- Adding external tracking scripts
- Calling APIs other than `./data.json` (same-origin only)

## How to test locally

```bash
cd dashboard && python3 -m http.server 8000
# open http://localhost:8000
```

## PR guidelines

- Single file change preferred (`dashboard/index.html`)
- No external dependencies unless absolutely necessary
- Preserve current URL contracts (hash routing if any)
- Screenshot before/after in the PR description
