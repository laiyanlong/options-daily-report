<div align="center">

# Options Daily Report

**The most comprehensive open-source options selling strategy platform**

Quantitative analysis + AI market commentary + multi-strategy + risk management + social community

[![Daily Report](https://github.com/laiyanlong/options-daily-report/actions/workflows/daily-report.yml/badge.svg)](https://github.com/laiyanlong/options-daily-report/actions/workflows/daily-report.yml)
[![Tests](https://github.com/laiyanlong/options-daily-report/actions/workflows/tests.yml/badge.svg)](https://github.com/laiyanlong/options-daily-report/actions/workflows/tests.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub code size](https://img.shields.io/github/languages/code-size/laiyanlong/options-daily-report)](https://github.com/laiyanlong/options-daily-report)
[![GitHub issues](https://img.shields.io/github/issues/laiyanlong/options-daily-report)](https://github.com/laiyanlong/options-daily-report/issues)
[![GitHub stars](https://img.shields.io/github/stars/laiyanlong/options-daily-report)](https://github.com/laiyanlong/options-daily-report/stargazers)

[English](#overview) | [繁體中文](#概覽)

</div>

---

## Overview

Options Daily Report is a fully automated, institutional-grade options analysis platform that generates comprehensive daily reports for options selling strategies. It combines **quantitative analysis** (Black-Scholes pricing, full Greeks, CP scoring), **AI-powered market commentary** (Google Gemini), **multi-leg strategy analysis**, **backtesting**, **risk management**, and **social community features** into a single, zero-cost pipeline that runs on GitHub Actions.

### Why This Project?

- **Free forever** -- Every component is free: GitHub Actions, yfinance, Gemini API free tier. Total monthly cost: **$0**.
- **Comprehensive** -- 61 features across 9 modules, from basic Greeks to VaR, scenario analysis, Reddit sentiment, and strategy marketplace.
- **Fully automated** -- Set up once, receive daily reports via email and Telegram. No manual intervention needed.

### Latest Report

> [View latest report](reports/)

### Demo

A daily report includes sections like:

```
=== TSLA ($254.38, +1.23%) ===

Sell Put Table (Expiry: 2026-04-04, 10 days)
| OTM%  | Strike  | Bid   | Delta   | IV    | Annualized | CP Score |
|-------|---------|-------|---------|-------|------------|----------|
| -5.0% | $241.67 | $1.85 | -0.1823 | 52.3% | 27.9%      | 62.3 ★   |
| -7.0% | $236.57 | $1.12 | -0.1204 | 54.1% | 17.3%      | 55.8     |

Options Intelligence: P/C Ratio 0.82 (Neutral-Bullish) | Max Pain $250 | Expected Move ±4.2%
Multi-Strategy: Iron Condor credit $3.45 | Bull Put spread R:R 1:2.3 | Wheel yield 31.2%
Risk Assessment: VaR(95%) $2,340 | Portfolio Beta 1.42 | Tail Risk: Medium
AI Commentary: IV elevated above HV, favorable for premium selling...
```

---

## Features

### Core Analysis (v1.0 - v1.2) -- 21 features

| # | Feature | Description | Module |
|---|---------|-------------|--------|
| 1 | Black-Scholes pricing | Theoretical option pricing using the Black-Scholes model | `generate_report.py` |
| 2 | Full Greeks | Delta, Gamma, Theta, Vega for every recommended trade | `generate_report.py` |
| 3 | CP scoring system | Composite score: 30% annualized return + 25% safety margin + 25% delta risk + 20% theta efficiency | `generate_report.py` |
| 4 | OTM strike scanning | Scans 5%-10% OTM puts and calls across multiple expiries | `generate_report.py` |
| 5 | Historical trend comparison | 1d/3d/5d/7d price trend with suitability signal per strike | `generate_report.py` |
| 6 | Cross-ticker ranking | All tickers ranked by CP score in a unified leaderboard | `generate_report.py` |
| 7 | AI market commentary | Google Gemini generates qualitative analysis from news, analyst ratings, and report data | `ai_analysis.py` |
| 8 | Bilingual reports | Full support for Traditional Chinese (default) and English | `generate_report.py` |
| 9 | Dynamic ticker list | Override tickers via environment variable at runtime | `generate_report.py` |
| 10 | Date override / backfill | Generate reports for any past trading day | `generate_report.py` |
| 11 | Interactive HTML report | Plotly charts: price history, IV smile, CP comparison, delta heatmap | `html_report.py` |
| 12 | Earnings calendar | Auto-detect next earnings date with 14-day warning banner | `generate_report.py` |
| 13 | IV percentile rank | Current IV ranked against 52-week historical volatility range | `generate_report.py` |
| 14 | Telegram notifications | Daily summary push via Telegram Bot API | `telegram_notify.py` |
| 15 | Docker support | Dockerfile + docker-compose for self-hosted deployment | `Dockerfile` |
| 16 | Put/Call ratio | Volume and OI ratio with bullish/bearish signal per ticker | `options_intelligence.py` |
| 17 | Max Pain calculation | Strike where option sellers profit most, with distance from current price | `options_intelligence.py` |
| 18 | Unusual options activity | Detect high volume/OI ratio strikes flagging smart money flow | `options_intelligence.py` |
| 19 | Expected move | ATM straddle price for weekly expected range with upper/lower bounds | `options_intelligence.py` |
| 20 | Probability of Profit | Black-Scholes based POP for each Sell Put / Sell Call recommendation | `options_intelligence.py` |
| 21 | Bid-ask spread quality | Rate spreads as Excellent/Good/Fair/Poor, flag illiquid contracts | `options_intelligence.py` |

### Multi-Strategy (v2.0) -- 6 features

| # | Feature | Description | Module |
|---|---------|-------------|--------|
| 22 | Iron Condor | Sell Put + Sell Call with protective wings; max profit, max loss, breakevens, POP | `multi_strategy.py` |
| 23 | Vertical Spread | Bull Put and Bear Call spreads with risk/reward ratio and breakeven | `multi_strategy.py` |
| 24 | Short Strangle & Straddle | ATM and OTM straddle/strangle pricing with breakeven levels | `multi_strategy.py` |
| 25 | Wheel Strategy | Sell Put entry analysis: effective cost basis, discount %, annualized yield, assignment probability | `multi_strategy.py` |
| 26 | Calendar Spread | Front-month vs back-month IV comparison for time spread opportunities | `multi_strategy.py` |
| 27 | Position sizing | Auto-calculate contracts based on account size and max risk per trade | `multi_strategy.py` |

### Data & Intelligence (v2.1 - v3.0) -- 18 features

| # | Feature | Description | Module |
|---|---------|-------------|--------|
| 28 | Historical report database | SQLite database storing all past trades and daily metrics | `data_backtest.py` |
| 29 | Backtest engine | Compare past CP-recommended trades vs actual outcomes (win rate, P&L) | `data_backtest.py` |
| 30 | Rolling performance | Track strategy P&L over 30/60/90 days with win rate statistics | `data_backtest.py` |
| 31 | IV vs HV divergence | Alert when implied vol exceeds realized vol (premium selling opportunity) | `data_backtest.py` |
| 32 | Correlation matrix | Cross-ticker return correlation with diversification score | `data_backtest.py` |
| 33 | Portfolio Greeks aggregation | Net Delta, Gamma, Theta, Vega across all open positions | `data_backtest.py` |
| 34 | Trade journal export | CSV export of all recommended trades with outcomes | `data_backtest.py` |
| 35 | Daily summary CSV | Append-mode CSV tracking price, IV, IV rank, P/C ratio, max pain per day | `data_backtest.py` |
| 36 | Strategy win rate stats | Historical accuracy tracking for each strategy type | `data_backtest.py` |
| 37 | Smart alerts engine | Push notification when IV Rank >80%, CP >75, earnings approaching, or expected move >5% | `smart_automation.py` |
| 38 | Macro event calendar | FOMC, CPI, NFP, Triple Witching dates with auto-warning when events are within 3 days | `smart_automation.py` |
| 39 | Watchlist management | Save/load custom ticker watchlists with notes in JSON format | `smart_automation.py` |
| 40 | Multi-timeframe analysis | Weekly, monthly, quarterly expiration views with IV term structure (contango/backwardation) | `smart_automation.py` |
| 41 | Auto-roll suggestions | Detect expiring or challenged positions and recommend roll, close, or let-expire actions | `smart_automation.py` |
| 42 | Email delivery | Gmail SMTP auto-delivery with HTML summary and GitHub link | Workflow |
| 43 | GitHub Actions CI | Automated test suite with pytest on every push and PR | Workflow |
| 44 | Report index | Auto-generated reports/README.md listing all historical reports | `generate_report.py` |
| 45 | Cron scheduling | Weekday-only execution at 6:00 AM PT (1:00 PM UTC) | Workflow |

### Risk & Social (v3.1 - v4.0) -- 16 features

| # | Feature | Description | Module |
|---|---------|-------------|--------|
| 46 | Portfolio-level Greeks | Net Delta, Gamma, Theta, Vega with dollar-weighted metrics and risk summary | `risk_management.py` |
| 47 | Value at Risk (VaR) | Historical simulation VaR (1-day, 1-week) with Conditional VaR (Expected Shortfall) | `risk_management.py` |
| 48 | Correlation-adjusted sizing | Reduce position size when adding correlated underlyings; portfolio beta vs SPY | `risk_management.py` |
| 49 | Scenario analysis | Delta-gamma P&L projection under -10% to +10% price moves | `risk_management.py` |
| 50 | Tail risk assessment | Stress test against COVID crash (2020) and 2022 bear market drawdowns | `risk_management.py` |
| 51 | Beta-weighted Delta | Normalize all positions to SPY-equivalent delta exposure | `risk_management.py` |
| 52 | Buying power tracking | Margin estimation for naked puts, naked calls, and spreads with utilization status | `risk_management.py` |
| 53 | Reddit sentiment analysis | NLP-based bullish/bearish scoring from r/options and r/wallstreetbets posts | `social_community.py` |
| 54 | Portfolio import/export | Support for broker CSV formats (IBKR, Schwab) with auto column mapping | `social_community.py` |
| 55 | Portfolio save/load | JSON-based portfolio persistence for tracking positions across sessions | `social_community.py` |
| 56 | Strategy sharing | Export/import strategy configurations as shareable JSON files | `social_community.py` |
| 57 | Leaderboard | Ranked strategy performance by win rate, Sharpe ratio, or max drawdown | `social_community.py` |
| 58 | Discord bot integration | Format report summaries and quick analysis for Discord embeds | `social_community.py` |
| 59 | Collaborative watchlists | Shared ticker lists with per-symbol annotations from multiple contributors | `social_community.py` |
| 60 | Strategy marketplace | Publish, browse, and clone proven strategy configurations | `social_community.py` |
| 61 | Telegram summary push | Markdown-formatted daily summary with report link via Bot API | `telegram_notify.py` |

### Total: 61 features across 9 modules

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (Cron: Weekdays 6AM PT)           │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │      generate_report.py        │
              │  (Orchestrator & Core Engine)   │
              │                                │
              │  • Fetch price & options data   │◄── yfinance API
              │  • Black-Scholes Greeks         │◄── scipy / numpy
              │  • CP scoring & OTM scanning    │
              │  • Historical trend comparison  │
              │  • Earnings calendar detection  │
              │  • IV percentile rank           │
              └──┬──────┬──────┬──────┬────────┘
                 │      │      │      │
    ┌────────────▼┐ ┌───▼──────┐ ┌───▼──────────┐ ┌──▼─────────────┐
    │ ai_analysis │ │ options_ │ │ multi_       │ │ data_backtest  │
    │   .py       │ │ intelli- │ │ strategy.py  │ │   .py          │
    │             │ │ gence.py │ │              │ │                │
    │ • Gemini AI │ │ • P/C    │ │ • Iron Condor│ │ • SQLite DB    │
    │ • News      │ │ • Max    │ │ • Verticals  │ │ • Backtest     │
    │ • Analyst   │ │   Pain   │ │ • Strangle   │ │ • IV/HV        │
    │   ratings   │ │ • Unusual│ │ • Wheel      │ │ • Correlation  │
    │ • Bull/Bear │ │ • Exp.   │ │ • Calendar   │ │ • Trade journal│
    │   outlook   │ │   Move   │ │ • Position   │ │ • Win rate     │
    │             │ │ • POP    │ │   sizing     │ │   statistics   │
    └─────────────┘ │ • Spread │ └──────────────┘ └────────────────┘
                    │   quality│
                    └──────────┘
    ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐
    │ smart_       │ │ risk_        │ │ social_community.py         │
    │ automation   │ │ management   │ │                             │
    │   .py        │ │   .py        │ │ • Reddit sentiment          │
    │              │ │              │ │ • Portfolio import/export    │
    │ • Alerts     │ │ • Portfolio  │ │ • Strategy sharing          │
    │ • Macro      │ │   Greeks     │ │ • Leaderboard               │
    │   calendar   │ │ • VaR/CVaR   │ │ • Discord bot format        │
    │ • Watchlist  │ │ • Scenario   │ │ • Collaborative watchlists  │
    │ • Multi-TF   │ │ • Tail risk  │ │ • Strategy marketplace      │
    │ • Auto-roll  │ │ • Beta-delta │ │                             │
    │              │ │ • Buying     │ │                             │
    │              │ │   power      │ │                             │
    └──────────────┘ └──────────────┘ └─────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │        Output Pipeline         │
              │                                │
              │  • Markdown report  → reports/  │
              │  • HTML report      → reports/  │◄── html_report.py (Plotly)
              │  • Trade journal    → CSV       │
              │  • SQLite database  → history   │
              │  • Git commit & push            │
              │  • Email (Gmail SMTP)           │
              │  • Telegram push                │◄── telegram_notify.py
              └────────────────────────────────┘
```

---

## Report Sections

Each daily report contains the following sections:

| Section | Description |
|---------|-------------|
| **Market Overview** | Current price, daily change %, average IV, IV percentile rank, earnings warning |
| **Options Intelligence** | P/C ratio & signal, max pain price & distance, expected move range |
| **Sell Put Table** | OTM 5%-10% puts with bid/ask, full Greeks, IV, annualized return, CP score |
| **Sell Call Table** | OTM 5%-10% calls with same comprehensive metrics |
| **Historical Trend** | 1d/3d/5d/7d price trend with suitability signal per top strike |
| **Best Strategy Pick** | Top-ranked Sell Put and Sell Call per ticker with rationale |
| **Trade Quality** | Bid-ask spread quality rating, POP, unusual activity alerts |
| **Multi-Leg Strategies** | Iron Condor, Bull Put, Bear Call, Strangle, Straddle, Wheel, Calendar Spread |
| **IV/HV Analysis** | Implied vs historical volatility divergence with sell/buy signal |
| **Correlation Matrix** | Cross-ticker correlation with diversification score |
| **Macro Events** | Upcoming FOMC, CPI, NFP, Triple Witching within 7 days |
| **Smart Alerts** | IV rank extremes, high CP opportunities, bearish P/C, earnings proximity |
| **Risk Assessment** | VaR, scenario analysis, tail risk, beta-weighted delta |
| **AI Commentary** | News highlights, bull/bear outlook, strategy recommendations, risk events |

### CP Score Formula

```
CP = annualized_return × 0.30
   + safety_margin     × 0.25
   + (1 - |delta|)     × 0.25
   + theta_efficiency   × 0.20
```

Higher CP = better risk-adjusted trade. The **★** marker highlights the best CP trade per expiry.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [Google Gemini API key](https://aistudio.google.com/) (free tier, optional)
- Gmail App Password (for email delivery, optional)
- Telegram Bot Token (for Telegram push, optional)

### Local Setup

```bash
# Clone
git clone https://github.com/laiyanlong/options-daily-report.git
cd options-daily-report

# Install dependencies
pip install -r requirements.txt

# Run (without AI -- works without any API key)
python generate_report.py

# Run with AI commentary
GEMINI_API_KEY=your_key python generate_report.py

# Run with date override
REPORT_DATE=2026-03-24 python generate_report.py

# Run in English
REPORT_LANG=en python generate_report.py

# Custom tickers
TICKERS=AAPL,GOOGL,META python generate_report.py

# Combine all options
TICKERS=TSLA,AAPL REPORT_LANG=en REPORT_DATE=2026-03-24 python generate_report.py
```

### Run Tests

```bash
pytest tests/ -v
```

---

## GitHub Actions Setup

1. **Fork this repository**

2. **Set GitHub Secrets** (`Settings > Secrets and variables > Actions`):

   | Secret | Required | Description |
   |--------|----------|-------------|
   | `GEMINI_API_KEY` | Optional | Google Gemini API key ([get one free](https://aistudio.google.com/)) |
   | `EMAIL_PASSWORD` | Optional | Gmail App Password for email delivery |
   | `TELEGRAM_BOT_TOKEN` | Optional | Telegram Bot API token ([create a bot](https://core.telegram.org/bots#how-do-i-create-a-bot)) |
   | `TELEGRAM_CHAT_ID` | Optional | Telegram chat ID for notifications |

3. **Trigger manually**: `Actions > Daily Options Report > Run workflow`

4. **Or wait for auto-run**: Every trading day at 6:00 AM PT (1:00 PM UTC)

### Workflow Parameters

When triggering manually, you can customize:

| Parameter | Default | Options |
|-----------|---------|---------|
| `report_date` | today | Any `YYYY-MM-DD` date |
| `report_lang` | `zh` | `zh` (Traditional Chinese) or `en` (English) |
| `tickers` | `TSLA,AMZN,NVDA` | Comma-separated stock tickers (e.g. `TSLA,AAPL,GOOGL,META`) |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | -- | Google Gemini API key for AI commentary |
| `REPORT_DATE` | today | Override report date (`YYYY-MM-DD`) |
| `REPORT_LANG` | `zh` | Report language: `zh` (Traditional Chinese) / `en` (English) |
| `TICKERS` | `TSLA,AMZN,NVDA` | Comma-separated stock tickers |
| `TELEGRAM_BOT_TOKEN` | -- | Telegram Bot token for push notifications |
| `TELEGRAM_CHAT_ID` | -- | Telegram chat ID for notifications |
| `EMAIL_PASSWORD` | -- | Gmail App Password for email delivery |

### Report Parameters (in `generate_report.py`)

```python
TICKERS = ["TSLA", "AMZN", "NVDA"]   # Default tickers
OTM_PCTS = [5, 6, 7, 8, 9, 10]       # OTM percentage range to scan
NUM_EXPIRIES = 3                       # Number of expiry dates to analyze
RISK_FREE_RATE = 5.0                   # Annual risk-free rate (%)
HISTORY_DAYS = [1, 3, 5, 7]           # Days for trend comparison
```

### Alert Thresholds (in `smart_automation.py`)

```python
iv_rank_high = 80        # IV rank % to trigger "sell premium" alert
iv_rank_low = 20         # IV rank % to trigger "low premium" alert
cp_score_high = 75       # CP score to flag as top-tier opportunity
pc_ratio_bearish = 1.3   # P/C ratio threshold for bearish signal
earnings_days = 7        # Days before earnings to warn
expected_move_high = 5.0  # Expected move % to flag high volatility
```

---

## Docker

### Using Docker Compose

```bash
# Basic run
docker compose up

# With environment variables
GEMINI_API_KEY=your_key REPORT_LANG=en docker compose up

# With Telegram
TELEGRAM_BOT_TOKEN=your_token TELEGRAM_CHAT_ID=your_id docker compose up

# Custom tickers
TICKERS=AAPL,GOOGL,META docker compose up
```

### Using Docker Directly

```bash
# Build
docker build -t options-report .

# Run
docker run -v ./reports:/app/reports \
  -e GEMINI_API_KEY=your_key \
  -e TICKERS=TSLA,AMZN,NVDA \
  options-report
```

---

## Project Structure

```
options-daily-report/
├── .github/
│   └── workflows/
│       ├── daily-report.yml        # Daily report generation & email workflow
│       └── tests.yml               # CI: pytest on push & PR
├── config/                         # Runtime config (auto-created)
│   ├── watchlists.json             # Saved watchlists
│   ├── portfolios/                 # Saved portfolios (JSON)
│   ├── strategies/                 # Shared strategy configs
│   ├── collab_watchlists/          # Collaborative watchlists
│   ├── marketplace/                # Strategy marketplace
│   └── leaderboard.json            # Strategy leaderboard
├── reports/                        # Generated daily reports
│   ├── README.md                   # Report index
│   ├── history.db                  # SQLite historical database
│   ├── daily_summary.csv           # Append-mode daily metrics
│   ├── 2026-03-25.md               # Markdown report
│   ├── 2026-03-25.html             # Interactive HTML report
│   └── trade_journal_2026-03-25.csv# Trade journal export
├── tests/                          # Test suite (pytest)
├── generate_report.py              # Main orchestrator & core engine
├── ai_analysis.py                  # AI market commentary (Gemini)
├── options_intelligence.py         # P/C ratio, max pain, POP, unusual activity
├── multi_strategy.py               # Iron Condor, verticals, strangles, wheel, calendar
├── data_backtest.py                # Historical DB, backtest, IV/HV, correlation
├── smart_automation.py             # Alerts, macro calendar, watchlist, multi-TF, auto-roll
├── risk_management.py              # VaR, scenario analysis, tail risk, beta-delta
├── social_community.py             # Reddit sentiment, portfolio I/O, marketplace
├── html_report.py                  # Interactive Plotly HTML report generator
├── telegram_notify.py              # Telegram push notifications
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container image
├── docker-compose.yml              # Docker Compose config
├── CONTRIBUTING.md                 # Contribution guidelines
├── ROADMAP.md                      # Development roadmap
├── LICENSE                         # MIT License
└── README.md                       # This file
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Python 3.12](https://python.org) | Runtime |
| [yfinance](https://github.com/ranaroussi/yfinance) | Market data, options chains, news, analyst ratings |
| [scipy](https://scipy.org) | Black-Scholes pricing (normal distribution, CDF/PDF) |
| [numpy](https://numpy.org) | Numerical computation, volatility calculations |
| [pandas](https://pandas.pydata.org) | Data manipulation, correlation matrix, rolling statistics |
| [plotly](https://plotly.com/python/) | Interactive HTML charts (price, IV smile, heatmaps) |
| [google-genai](https://github.com/googleapis/python-genai) | Gemini AI market commentary |
| [pytest](https://pytest.org) | Test suite |
| [SQLite](https://sqlite.org) | Historical trade database |
| [GitHub Actions](https://github.com/features/actions) | CI/CD, daily automation, email delivery |
| [Docker](https://docker.com) | Containerized deployment |

---

## Cost

| Component | Cost |
|-----------|------|
| GitHub Actions | Free (public repo) |
| yfinance data | Free |
| Google Gemini API | Free (free tier: 250 req/day) |
| Telegram Bot API | Free |
| **Total** | **$0/month** |

---

## Contributing

We welcome contributions of all kinds -- bug fixes, new strategies, visualizations, documentation, and more.

- **[CONTRIBUTING.md](CONTRIBUTING.md)** -- Development guidelines, quick start, and feature ideas
- **[ROADMAP.md](ROADMAP.md)** -- Full version history and future plans
- **[Issues](https://github.com/laiyanlong/options-daily-report/issues)** -- Browse open issues or suggest features

Look for `good first issue` labels for beginner-friendly tasks.

---

## Disclaimer

This project generates reports for **educational and research purposes only**. Nothing in these reports constitutes financial advice. Options trading involves significant risk of loss, including the possibility of losing more than your initial investment. Always consult qualified financial professionals before making investment decisions. Past performance does not guarantee future results.

---

## License

This project is licensed under the MIT License -- see [LICENSE](LICENSE) for details.

---

---

<div align="center">

# 選擇權每日報告

**最全面的開源選擇權賣方策略平台**

量化分析 + AI 市場解讀 + 多腳策略 + 風險管理 + 社群互動

</div>

## 概覽

Options Daily Report 是一個全自動、機構級的選擇權分析平台，每個交易日自動產生全面的賣方策略報告。結合**量化分析**（Black-Scholes 定價、完整 Greeks、CP 評分）、**AI 市場解讀**（Google Gemini）、**多腳策略分析**、**歷史回測**、**風險管理**和**社群互動功能**，整合為一條完全免費、運行在 GitHub Actions 上的自動化管線。

### 為什麼選擇這個專案？

- **永久免費** -- GitHub Actions、yfinance、Gemini API 免費方案，月費：**$0**。
- **功能全面** -- 跨 9 個模組共 61 項功能，涵蓋基礎 Greeks 到 VaR、情境分析、Reddit 情緒、策略市集。
- **全自動執行** -- 設定一次，每日自動收到 Email 和 Telegram 報告，無需手動操作。

### 最新報告

> [查看最新報告](reports/)

---

## 功能特色

### 核心分析 (v1.0 - v1.2) -- 21 項功能

| # | 功能 | 說明 | 模組 |
|---|------|------|------|
| 1 | Black-Scholes 定價 | 使用 Black-Scholes 模型計算理論選擇權價格 | `generate_report.py` |
| 2 | 完整 Greeks | 每筆推薦交易計算 Delta、Gamma、Theta、Vega | `generate_report.py` |
| 3 | CP 綜合評分 | 30% 年化報酬 + 25% 安全邊際 + 25% Delta 風險 + 20% Theta 效率 | `generate_report.py` |
| 4 | OTM 履約價掃描 | 掃描多個到期日的 5%-10% 價外 Put 和 Call | `generate_report.py` |
| 5 | 歷史趨勢比較 | 1/3/5/7 日股價趨勢，搭配各履約價適合度判斷 | `generate_report.py` |
| 6 | 跨標的排名 | 所有標的依 CP 分數統一排行 | `generate_report.py` |
| 7 | AI 市場解讀 | Google Gemini 根據新聞、分析師評級及報告數據生成定性分析 | `ai_analysis.py` |
| 8 | 雙語支援 | 完整支援繁體中文（預設）和英文 | `generate_report.py` |
| 9 | 動態標的清單 | 可透過環境變數在執行時覆蓋追蹤標的 | `generate_report.py` |
| 10 | 日期覆蓋 / 回填 | 可產生任何過去交易日的報告 | `generate_report.py` |
| 11 | 互動式 HTML 報告 | Plotly 圖表：股價走勢、IV Smile、CP 比較、Delta 熱力圖 | `html_report.py` |
| 12 | 財報日曆 | 自動偵測下次財報日期，14 天內顯示警告橫幅 | `generate_report.py` |
| 13 | IV 百分位排名 | 當前 IV 對照 52 週歷史波動率區間定位 | `generate_report.py` |
| 14 | Telegram 推播 | 透過 Telegram Bot API 傳送每日報告摘要 | `telegram_notify.py` |
| 15 | Docker 容器化 | Dockerfile + docker-compose 一鍵自架部署 | `Dockerfile` |
| 16 | Put/Call 比率 | 成交量與未平倉比率，搭配看多/看空訊號 | `options_intelligence.py` |
| 17 | Max Pain 計算 | 計算選擇權賣方最大獲利的履約價及與現價距離 | `options_intelligence.py` |
| 18 | 異常選擇權活動 | 偵測量比異常高的履約價，標記大戶資金動向 | `options_intelligence.py` |
| 19 | 預期波動範圍 | 用 ATM 跨式價格計算週預期區間及上下界 | `options_intelligence.py` |
| 20 | 獲利機率 (POP) | 以 Black-Scholes 計算每筆 Sell Put / Sell Call 的獲利機率 | `options_intelligence.py` |
| 21 | Bid-Ask 價差品質 | 將價差評為 Excellent/Good/Fair/Poor，標記流動性不足的合約 | `options_intelligence.py` |

### 多腳策略 (v2.0) -- 6 項功能

| # | 功能 | 說明 | 模組 |
|---|------|------|------|
| 22 | Iron Condor | 賣 Put + 賣 Call 加保護翼；最大獲利、最大虧損、損益平衡、POP | `multi_strategy.py` |
| 23 | 垂直價差 | Bull Put 和 Bear Call 價差，含風險報酬比及損益平衡點 | `multi_strategy.py` |
| 24 | Short Strangle 與 Straddle | ATM 及 OTM 勒式/跨式定價與損益平衡水位 | `multi_strategy.py` |
| 25 | Wheel 策略 | Sell Put 進場分析：有效成本基礎、折扣 %、年化收益、被指派機率 | `multi_strategy.py` |
| 26 | Calendar Spread | 近月 vs 遠月 IV 比較，識別時間價差機會 | `multi_strategy.py` |
| 27 | 部位大小計算 | 依帳戶規模及每筆交易最大風險自動計算合約數 | `multi_strategy.py` |

### 數據與智慧 (v2.1 - v3.0) -- 18 項功能

| # | 功能 | 說明 | 模組 |
|---|------|------|------|
| 28 | 歷史報告資料庫 | SQLite 資料庫儲存所有歷史交易和每日指標 | `data_backtest.py` |
| 29 | 回測引擎 | 比較過去 CP 推薦交易與實際結果（勝率、損益） | `data_backtest.py` |
| 30 | 滾動績效追蹤 | 追蹤 30/60/90 天策略損益及勝率統計 | `data_backtest.py` |
| 31 | IV vs HV 背離 | 隱含波動率顯著超過實際波動率時發出賣方機會警報 | `data_backtest.py` |
| 32 | 相關性矩陣 | 跨標的報酬率相關性分析，附分散化評分 | `data_backtest.py` |
| 33 | 投組 Greeks 匯總 | 所有未平倉部位的淨 Delta、Gamma、Theta、Vega | `data_backtest.py` |
| 34 | 交易日誌匯出 | 所有推薦交易及結果匯出為 CSV | `data_backtest.py` |
| 35 | 每日摘要 CSV | 附加模式記錄每日價格、IV、IV 排名、P/C 比率、Max Pain | `data_backtest.py` |
| 36 | 策略勝率統計 | 各策略類型歷史準確率追蹤 | `data_backtest.py` |
| 37 | 智慧警報引擎 | IV Rank >80%、CP >75、財報逼近、預期波動 >5% 時推播通知 | `smart_automation.py` |
| 38 | 總經事件日曆 | FOMC、CPI、非農、三巫日日期，3 天內自動發出警告 | `smart_automation.py` |
| 39 | 觀察清單管理 | 以 JSON 格式儲存/載入自訂標的清單及備註 | `smart_automation.py` |
| 40 | 多時間框架分析 | 週/月/季到期綜合視角，IV 期限結構（正價差/逆價差） | `smart_automation.py` |
| 41 | 自動轉倉建議 | 偵測即將到期或受挑戰部位，建議轉倉、平倉或讓其到期 | `smart_automation.py` |
| 42 | Email 報告寄送 | Gmail SMTP 自動寄送含 HTML 摘要和 GitHub 連結 | Workflow |
| 43 | GitHub Actions CI | 每次 push 和 PR 自動執行 pytest 測試套件 | Workflow |
| 44 | 報告索引 | 自動產生 reports/README.md 列出所有歷史報告 | `generate_report.py` |
| 45 | 排程執行 | 僅工作日執行，PT 6:00 AM（UTC 1:00 PM） | Workflow |

### 風險與社群 (v3.1 - v4.0) -- 16 項功能

| # | 功能 | 說明 | 模組 |
|---|------|------|------|
| 46 | 投組層級 Greeks | 淨 Delta、Gamma、Theta、Vega，美元加權指標及風險摘要 | `risk_management.py` |
| 47 | 風險值 (VaR) | 歷史模擬法 VaR（1 日、1 週），含條件風險值（預期損失） | `risk_management.py` |
| 48 | 相關性調整部位 | 新增相關性高的標的時自動縮減部位；投組 Beta vs SPY | `risk_management.py` |
| 49 | 情境分析 | Delta-Gamma 損益預測：股價 -10% 至 +10% 各情境 | `risk_management.py` |
| 50 | 尾部風險評估 | 以 2020 新冠崩盤及 2022 熊市數據壓力測試投組 | `risk_management.py` |
| 51 | Beta 加權 Delta | 將所有部位正規化為 SPY 等價 Delta 曝險 | `risk_management.py` |
| 52 | 購買力追蹤 | 裸賣 Put、裸賣 Call、價差的保證金估算及使用率狀態 | `risk_management.py` |
| 53 | Reddit 情緒分析 | 從 r/options 和 r/wallstreetbets 貼文以 NLP 計算多空情緒 | `social_community.py` |
| 54 | 投組匯入/匯出 | 支援券商 CSV 格式（IBKR、Schwab），自動欄位對應 | `social_community.py` |
| 55 | 投組儲存/載入 | JSON 格式投組持久化，跨會話追蹤部位 | `social_community.py` |
| 56 | 策略分享 | 匯出/匯入策略配置為可分享的 JSON 檔案 | `social_community.py` |
| 57 | 排行榜 | 依勝率、Sharpe 比率或最大回撤排名策略績效 | `social_community.py` |
| 58 | Discord 機器人整合 | 為 Discord 嵌入格式化報告摘要及快速分析 | `social_community.py` |
| 59 | 協作觀察清單 | 共享標的清單，支援多人逐標的附加註記 | `social_community.py` |
| 60 | 策略市集 | 發布、瀏覽及複製經驗證的策略配置 | `social_community.py` |
| 61 | Telegram 摘要推播 | Markdown 格式每日摘要附報告連結，透過 Bot API 傳送 | `telegram_notify.py` |

### 總計：9 個模組，61 項功能

---

## 架構圖

```
┌──────────────────────────────────────────────────────────────────────┐
│                 GitHub Actions（排程：工作日 PT 6AM）                  │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │      generate_report.py        │
              │      （調度器 & 核心引擎）       │
              │                                │
              │  • 擷取股價與選擇權數據         │◄── yfinance API
              │  • Black-Scholes Greeks         │◄── scipy / numpy
              │  • CP 評分 & OTM 掃描           │
              │  • 歷史趨勢比較                 │
              │  • 財報日曆偵測                 │
              │  • IV 百分位排名                │
              └──┬──────┬──────┬──────┬────────┘
                 │      │      │      │
    ┌────────────▼┐ ┌───▼──────┐ ┌───▼──────────┐ ┌──▼─────────────┐
    │ ai_analysis │ │ options_ │ │ multi_       │ │ data_backtest  │
    │   .py       │ │ intelli- │ │ strategy.py  │ │   .py          │
    │             │ │ gence.py │ │              │ │                │
    │ • Gemini AI │ │ • P/C    │ │ • Iron Condor│ │ • SQLite 資料庫│
    │ • 新聞分析  │ │ • Max    │ │ • 垂直價差   │ │ • 回測引擎     │
    │ • 分析師    │ │   Pain   │ │ • 勒式/跨式  │ │ • IV/HV 背離   │
    │   評級      │ │ • 異常   │ │ • Wheel 策略 │ │ • 相關性矩陣   │
    │ • 多空判斷  │ │   活動   │ │ • Calendar   │ │ • 交易日誌     │
    │             │ │ • 預期   │ │ • 部位大小   │ │ • 勝率統計     │
    │             │ │   波動   │ │              │ │                │
    └─────────────┘ │ • POP   │ └──────────────┘ └────────────────┘
                    │ • 價差  │
                    │   品質  │
                    └──────────┘
    ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐
    │ smart_       │ │ risk_        │ │ social_community.py         │
    │ automation   │ │ management   │ │                             │
    │   .py        │ │   .py        │ │ • Reddit 情緒分析           │
    │              │ │              │ │ • 投組匯入/匯出             │
    │ • 智慧警報   │ │ • 投組       │ │ • 策略分享                  │
    │ • 總經日曆   │ │   Greeks     │ │ • 排行榜                    │
    │ • 觀察清單   │ │ • VaR/CVaR   │ │ • Discord 機器人            │
    │ • 多時間     │ │ • 情境分析   │ │ • 協作觀察清單              │
    │   框架       │ │ • 尾部風險   │ │ • 策略市集                  │
    │ • 自動轉倉   │ │ • Beta-Delta │ │                             │
    │              │ │ • 購買力     │ │                             │
    └──────────────┘ └──────────────┘ └─────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │          輸出管線              │
              │                                │
              │  • Markdown 報告 → reports/     │
              │  • HTML 報告     → reports/     │◄── html_report.py (Plotly)
              │  • 交易日誌      → CSV          │
              │  • SQLite 資料庫 → history      │
              │  • Git commit & push            │
              │  • Email（Gmail SMTP）          │
              │  • Telegram 推播               │◄── telegram_notify.py
              └────────────────────────────────┘
```

---

## 報告章節

每份日報包含以下章節：

| 章節 | 說明 |
|------|------|
| **市場概況** | 現價、漲跌幅 %、平均 IV、IV 百分位排名、財報警告 |
| **選擇權情報** | P/C 比率及訊號、Max Pain 價位及距離、預期波動範圍 |
| **Sell Put 表格** | 5%-10% 價外 Put，含 Bid/Ask、完整 Greeks、IV、年化報酬、CP 評分 |
| **Sell Call 表格** | 5%-10% 價外 Call，同樣全面的指標 |
| **歷史趨勢** | 1/3/5/7 日股價趨勢，搭配各頂級履約價適合度訊號 |
| **最佳策略** | 每檔標的排名最高的 Sell Put 和 Sell Call 及理由 |
| **交易品質** | Bid-Ask 價差品質評級、POP、異常活動警報 |
| **多腳策略** | Iron Condor、Bull Put、Bear Call、Strangle、Straddle、Wheel、Calendar Spread |
| **IV/HV 分析** | 隱含 vs 歷史波動率背離，附賣/買訊號 |
| **相關性矩陣** | 跨標的相關性及分散化評分 |
| **總經事件** | 7 天內的 FOMC、CPI、非農、三巫日 |
| **智慧警報** | IV 排名極值、高 CP 機會、看空 P/C、財報逼近 |
| **風險評估** | VaR、情境分析、尾部風險、Beta 加權 Delta |
| **AI 解讀** | 新聞重點、多空判斷、策略建議、風險事件 |

### CP 評分公式

```
CP = 年化報酬率 × 0.30
   + 安全邊際   × 0.25
   + (1 - |Delta|) × 0.25
   + Theta 效率  × 0.20
```

CP 越高 = 風險調整後交易品質越好。**★** 標記代表該到期日最佳 CP 交易。

---

## 快速開始

### 前置需求

- Python 3.12+
- [Google Gemini API key](https://aistudio.google.com/)（免費方案，選填）
- Gmail 應用程式密碼（Email 寄送，選填）
- Telegram Bot Token（Telegram 推播，選填）

### 本地安裝

```bash
# Clone
git clone https://github.com/laiyanlong/options-daily-report.git
cd options-daily-report

# 安裝依賴
pip install -r requirements.txt

# 執行（不需 AI -- 無需任何 API key）
python generate_report.py

# 含 AI 解讀
GEMINI_API_KEY=your_key python generate_report.py

# 指定日期
REPORT_DATE=2026-03-24 python generate_report.py

# 英文報告
REPORT_LANG=en python generate_report.py

# 自訂標的
TICKERS=AAPL,GOOGL,META python generate_report.py
```

### 執行測試

```bash
pytest tests/ -v
```

---

## GitHub Actions 設定

1. **Fork 此 repo**

2. **設定 GitHub Secrets**（`Settings > Secrets and variables > Actions`）：

   | Secret | 必要性 | 說明 |
   |--------|--------|------|
   | `GEMINI_API_KEY` | 選填 | Google Gemini API key（[免費申請](https://aistudio.google.com/)） |
   | `EMAIL_PASSWORD` | 選填 | Gmail 應用程式密碼 |
   | `TELEGRAM_BOT_TOKEN` | 選填 | Telegram Bot API token（[建立機器人](https://core.telegram.org/bots#how-do-i-create-a-bot)） |
   | `TELEGRAM_CHAT_ID` | 選填 | Telegram 聊天室 ID |

3. **手動觸發**：`Actions > Daily Options Report > Run workflow`

4. **或等自動執行**：每個工作日 PT 6:00 AM（UTC 1:00 PM）

### 手動觸發參數

| 參數 | 預設值 | 選項 |
|------|--------|------|
| `report_date` | 今天 | 任意 `YYYY-MM-DD` 日期 |
| `report_lang` | `zh` | `zh`（繁體中文）或 `en`（English） |
| `tickers` | `TSLA,AMZN,NVDA` | 逗號分隔的股票代號（如 `TSLA,AAPL,GOOGL,META`） |

---

## 環境變數設定

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `GEMINI_API_KEY` | -- | Google Gemini API key，啟用 AI 解讀 |
| `REPORT_DATE` | 今天 | 覆蓋報告日期（`YYYY-MM-DD`） |
| `REPORT_LANG` | `zh` | 報告語言：`zh`（繁體中文）/ `en`（English） |
| `TICKERS` | `TSLA,AMZN,NVDA` | 逗號分隔的股票代號 |
| `TELEGRAM_BOT_TOKEN` | -- | Telegram Bot token，啟用推播通知 |
| `TELEGRAM_CHAT_ID` | -- | Telegram 聊天室 ID |
| `EMAIL_PASSWORD` | -- | Gmail 應用程式密碼，啟用 Email 寄送 |

---

## Docker 部署

```bash
# 基本執行
docker compose up

# 含環境變數
GEMINI_API_KEY=your_key REPORT_LANG=en docker compose up

# 含 Telegram
TELEGRAM_BOT_TOKEN=your_token TELEGRAM_CHAT_ID=your_id docker compose up

# 自訂標的
TICKERS=AAPL,GOOGL,META docker compose up
```

---

## 費用

| 元件 | 費用 |
|------|------|
| GitHub Actions | 免費（公開 repo） |
| yfinance 數據 | 免費 |
| Google Gemini API | 免費（免費方案：每天 250 次） |
| Telegram Bot API | 免費 |
| **總計** | **$0/月** |

---

## 貢獻

歡迎各種形式的貢獻 -- 修復 bug、新增策略、改善視覺化、完善文件等。

- **[CONTRIBUTING.md](CONTRIBUTING.md)** -- 開發指南、快速開始及功能建議
- **[ROADMAP.md](ROADMAP.md)** -- 完整版本歷史及未來規劃
- **[Issues](https://github.com/laiyanlong/options-daily-report/issues)** -- 瀏覽未解議題或建議新功能

尋找 `good first issue` 標籤來入門！

---

## 免責聲明

本專案產生的報告僅供**教育與研究目的**。報告中的任何內容均不構成投資建議。選擇權交易涉及重大虧損風險，包括可能損失超過初始投資金額。在做出投資決策前，請務必諮詢合格的金融專業人士。過去的績效不保證未來的結果。

---

## 授權

本專案採用 MIT 授權條款 -- 詳見 [LICENSE](LICENSE)。

---

<div align="center">

**[查看報告](reports/) · [貢獻指南](CONTRIBUTING.md) · [開發路線圖](ROADMAP.md) · [回報問題](https://github.com/laiyanlong/options-daily-report/issues)**

</div>
