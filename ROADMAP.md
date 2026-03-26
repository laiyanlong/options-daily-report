# Roadmap

Current status and future plans for Options Daily Report.

## v1.0 — Foundation

- [x] Black-Scholes quantitative analysis
- [x] Full Greeks (Delta, Gamma, Theta, Vega)
- [x] CP scoring system
- [x] AI market commentary (Google Gemini)
- [x] Daily automated pipeline (GitHub Actions)
- [x] Email delivery
- [x] Bilingual support (zh/en)
- [x] Dynamic ticker list
- [x] Date override for backfill

## v1.1 — Enhanced Analytics

- [x] **Interactive HTML report** with Plotly charts (Price History, IV Smile, CP Comparison, Delta Heatmap)
- [x] **Earnings calendar** auto-detection and 14-day warning banner
- [x] **IV percentile rank** (vs 52-week historical volatility range)
- [x] **Telegram notification** integration (summary push via Bot API)
- [x] **Docker support** for self-hosted deployment (Dockerfile + docker-compose)
- [x] **Test suite** — 32 unit tests with GitHub Actions CI

## v1.2 — Options Intelligence

- [x] **Put/Call ratio tracking** — volume & OI ratio with bullish/bearish signal per ticker
- [x] **Max Pain calculation** — max pain price from full options chain, distance from current price
- [x] **Unusual options activity** — detect high volume/OI ratio strikes, flag smart money flow
- [x] **Expected Move calculation** — ATM straddle price for weekly expected range
- [x] **Probability of Profit (POP)** — Black-Scholes based POP for each recommended trade
- [x] **Bid-Ask spread quality** — rate spreads as Excellent/Good/Fair/Poor, flag wide spreads

## v2.0 — Multi-Strategy

- [ ] **Iron Condor analysis** — combine Sell Put + Sell Call into defined-risk spreads with P&L charts
- [ ] **Vertical Spread analysis** — Bull Put Spread / Bear Call Spread with max loss/gain calculations
- [ ] **Strangle/Straddle analysis** — ATM and OTM straddle/strangle pricing with breakeven levels
- [ ] **Wheel Strategy tracker** — track Sell Put → assignment → Sell Call cycle, calculate running yield
- [ ] **Calendar Spread analysis** — front-month vs back-month IV comparison for time spread opportunities
- [ ] **Risk-defined position sizing** — auto-calculate position size based on account size and max risk %

## v2.1 — Data & Backtesting

- [ ] **Historical report database** — SQLite/DuckDB to store all past reports for trend queries
- [ ] **Backtest engine** — compare past CP-recommended trades vs actual outcomes (win rate, avg P&L)
- [ ] **Rolling performance dashboard** — track strategy P&L over 30/60/90 days
- [ ] **IV vs HV divergence** — alert when implied vol significantly exceeds realized vol (selling opportunity)
- [ ] **Correlation matrix** — show correlation between tracked tickers to avoid concentrated risk
- [ ] **Greeks portfolio aggregation** — if holding multiple positions, show net portfolio Greeks

## v3.0 — Smart Automation

- [ ] **Web dashboard** — Streamlit/Gradio app for interactive exploration and filtering
- [ ] **Multiple AI providers** — OpenAI GPT-4o, Claude Sonnet, Ollama (local LLM)
- [ ] **Portfolio tracking** — input your positions, get personalized daily adjustments
- [ ] **Smart alerts** — push notification when IV Rank >80%, or CP score >80, or earnings approaching
- [ ] **Options flow integration** — aggregate unusual flow data from public sources
- [ ] **Sector rotation signals** — track sector ETF options flow to identify rotation trends
- [ ] **Fed/macro event calendar** — auto-flag FOMC, CPI, NFP dates with historical IV impact

## Moonshot Ideas

- [ ] RAG-powered analysis — AI references all past reports for trend context
- [ ] Broker API integration (IBKR/Schwab) — one-click order execution from report
- [ ] Dark pool data integration — institutional flow signals
- [ ] Community strategy plugins — user-contributed analysis modules
- [ ] Mobile app — React Native app with push notifications
- [ ] Social sentiment scoring — Reddit/X/StockTwits sentiment for each ticker
- [ ] Gamma exposure (GEX) calculation — predict support/resistance from dealer hedging

---

Want to work on something? Check [CONTRIBUTING.md](CONTRIBUTING.md) or [open an issue](https://github.com/laiyanlong/options-daily-report/issues)!
