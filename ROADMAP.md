# Roadmap

Current status and future plans for Options Daily Report.

## Current (v1.0)

- [x] Black-Scholes quantitative analysis
- [x] Full Greeks (Delta, Gamma, Theta, Vega)
- [x] CP scoring system
- [x] AI market commentary (Google Gemini)
- [x] Daily automated pipeline (GitHub Actions)
- [x] Email delivery
- [x] Bilingual support (zh/en)
- [x] Dynamic ticker list
- [x] Date override for backfill

## v1.1 — Completed!

- [x] **Interactive HTML report** with Plotly charts (Price History, IV Smile, CP Comparison, Delta Heatmap)
- [x] **Earnings calendar** auto-detection and 14-day warning banner
- [x] **IV percentile rank** (vs 52-week historical volatility range)
- [x] **Telegram notification** integration (summary push via Bot API)
- [x] **Docker support** for self-hosted deployment (Dockerfile + docker-compose)

## Future (v2.0)

- [ ] **Multi-strategy support** — Iron Condors, Vertical Spreads, Strangles
- [ ] **Historical backtest** — track recommended trade outcomes
- [ ] **Web dashboard** — Streamlit app for interactive exploration
- [ ] **Multiple AI providers** — OpenAI, Claude, Ollama
- [ ] **Portfolio tracking** — input your positions, get personalized recommendations
- [ ] **Alerts system** — push notification when IV spikes or opportunities arise

## Moonshot Ideas

- [ ] RAG-powered analysis referencing all past reports
- [ ] Broker API integration (IBKR) for one-click execution
- [ ] Options flow / dark pool data integration
- [ ] Community-contributed strategy plugins

---

Want to work on something? Check [CONTRIBUTING.md](CONTRIBUTING.md) or [open an issue](https://github.com/laiyanlong/options-daily-report/issues)!
