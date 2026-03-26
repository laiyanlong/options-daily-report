<div align="center">

# Options Daily Report

**Automated daily options strategy analysis for US equities**

Quantitative Sell Put / Sell Call analysis powered by Black-Scholes + AI market commentary via Google Gemini

[![Daily Report](https://github.com/laiyanlong/options-daily-report/actions/workflows/daily-report.yml/badge.svg)](https://github.com/laiyanlong/options-daily-report/actions/workflows/daily-report.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](#overview) | [繁體中文](#概覽)

</div>

---

## Overview

Options Daily Report is a fully automated pipeline that generates institutional-grade options selling strategy reports every trading day. It combines **quantitative analysis** (Black-Scholes pricing, Greeks, CP scoring) with **AI-powered market commentary** (Google Gemini) to deliver actionable insights for Sell Put and Sell Call strategies.

### Latest Report

> [View latest report](reports/)

### Key Features

- **Quantitative Analysis** — Black-Scholes model for options pricing with full Greeks (Delta, Gamma, Theta, Vega)
- **CP Scoring System** — Proprietary composite score ranking trades by annualized return, safety margin, delta risk, and theta efficiency
- **AI Market Commentary** — Google Gemini analyzes news, analyst ratings, and macro conditions to provide qualitative insights
- **Multi-Ticker Support** — Tracks TSLA, AMZN, NVDA (configurable)
- **Automated Pipeline** — GitHub Actions runs daily at 6:00 AM PT on trading days
- **Email Delivery** — Reports auto-delivered to your inbox with summary and GitHub link
- **Bilingual** — Supports Traditional Chinese (default) and English reports

### Covered Tickers

| Ticker | Company | Sector |
|--------|---------|--------|
| TSLA | Tesla, Inc. | EV / AI / Energy |
| AMZN | Amazon.com, Inc. | Cloud / E-commerce |
| NVDA | NVIDIA Corporation | AI / Semiconductors |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  GitHub Actions (Cron)               │
│                  Daily @ 6:00 AM PT                  │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │   generate_report.py    │
          │                         │
          │  1. Fetch market data   │◄── yfinance API
          │  2. Options chain data  │
          │  3. Black-Scholes calc  │◄── scipy / numpy
          │  4. Greeks & CP score   │
          │  5. Trend comparison    │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │    ai_analysis.py       │
          │                         │
          │  1. Fetch news/ratings  │◄── yfinance API
          │  2. Build context       │
          │  3. Call Gemini API     │◄── Google Gemini 2.5 Flash
          │  4. Market commentary   │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │      Output Pipeline     │
          │                         │
          │  • Markdown report      │──► reports/YYYY-MM-DD.md
          │  • Git commit & push    │──► GitHub repository
          │  • Email notification   │──► Gmail SMTP
          └─────────────────────────┘
```

---

## Report Structure

Each daily report contains:

| Section | Description |
|---------|-------------|
| **Market Overview** | Current price, daily change, average IV, price history |
| **Sell Put Table** | OTM 5%-10% puts with bid/ask, Greeks, IV, annualized return, CP score |
| **Sell Call Table** | OTM 5%-10% calls with same metrics |
| **Historical Trend** | Price trend comparison (1d, 3d, 5d, 7d) with suitability signal |
| **Best Strategy** | Top-ranked Sell Put and Sell Call per ticker |
| **Cross-Ticker Ranking** | All tickers ranked by CP score |
| **AI Market Commentary** | News analysis, bull/bear outlook, strategy recommendations, risk events |

### CP Score Formula

```
CP = annualized_return × 0.30
   + safety_margin     × 0.25
   + (1 - |delta|)     × 0.25
   + theta_efficiency   × 0.20
```

Higher CP = better risk-adjusted trade. The ★ marker highlights the best CP trade per expiry.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [Google Gemini API key](https://aistudio.google.com/) (free tier, optional)
- Gmail App Password (for email delivery)

### Local Setup

```bash
# Clone
git clone https://github.com/laiyanlong/options-daily-report.git
cd options-daily-report

# Install dependencies
pip install -r requirements.txt

# Run (without AI — works without API key)
python generate_report.py

# Run with AI commentary
GEMINI_API_KEY=your_key python generate_report.py

# Run with date override
REPORT_DATE=2026-03-24 python generate_report.py

# Run in English
REPORT_LANG=en python generate_report.py
```

### GitHub Actions Setup

1. **Fork this repository**

2. **Set GitHub Secrets** (`Settings > Secrets and variables > Actions`):

   | Secret | Required | Description |
   |--------|----------|-------------|
   | `GEMINI_API_KEY` | Optional | Google Gemini API key ([get one free](https://aistudio.google.com/)) |
   | `EMAIL_PASSWORD` | Optional | Gmail App Password for email delivery |

3. **Trigger manually**: `Actions > Daily Options Report > Run workflow`

4. **Or wait for auto-run**: Every trading day at 6:00 AM PT (1:00 PM UTC)

### Workflow Parameters

When triggering manually, you can customize:

| Parameter | Default | Options |
|-----------|---------|---------|
| `report_date` | today | Any `YYYY-MM-DD` date |
| `report_lang` | `zh` | `zh` (繁體中文) or `en` (English) |

---

## Configuration

Edit `generate_report.py` to customize:

```python
TICKERS = ["TSLA", "AMZN", "NVDA"]   # Add/remove tickers
OTM_PCTS = [5, 6, 7, 8, 9, 10]       # OTM percentage range
NUM_EXPIRIES = 3                       # Number of expiry dates to analyze
RISK_FREE_RATE = 5.0                   # Annual risk-free rate (%)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `REPORT_DATE` | today | Override report date |
| `REPORT_LANG` | `zh` | Report language (`zh` / `en`) |

---

## Cost

| Component | Cost |
|-----------|------|
| GitHub Actions | Free (public repo) |
| yfinance data | Free |
| Google Gemini API | Free (250 req/day on free tier) |
| **Total** | **$0/month** |

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Python 3.12](https://python.org) | Runtime |
| [yfinance](https://github.com/ranaroussi/yfinance) | Market data & options chains |
| [scipy](https://scipy.org) | Black-Scholes pricing (normal distribution) |
| [numpy](https://numpy.org) | Numerical computation |
| [pandas](https://pandas.pydata.org) | Data manipulation |
| [google-genai](https://github.com/googleapis/python-genai) | Gemini AI market commentary |
| [GitHub Actions](https://github.com/features/actions) | CI/CD automation |

---

## Project Structure

```
options-daily-report/
├── .github/
│   └── workflows/
│       └── daily-report.yml    # GitHub Actions workflow
├── reports/                     # Generated daily reports
│   ├── README.md               # Report index
│   ├── 2026-03-25.md
│   └── 2026-03-26.md
├── generate_report.py           # Main report generator (quantitative)
├── ai_analysis.py               # AI market commentary (Gemini)
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
└── README.md                    # This file
```

---

## Disclaimer

This project generates reports for **educational and research purposes only**. Nothing in these reports constitutes financial advice. Options trading involves significant risk of loss. Always consult qualified financial professionals before making investment decisions. Past performance does not guarantee future results.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

---

<div align="center">

# 選擇權每日報告

**美股選擇權賣方策略自動化分析**

Black-Scholes 量化分析 + Google Gemini AI 市場解讀

</div>

## 概覽

Options Daily Report 是一個全自動化的選擇權分析管線，每個交易日自動產生機構級的賣方策略報告。結合 **量化分析**（Black-Scholes 定價、Greeks、CP 評分）和 **AI 市場解讀**（Google Gemini），為 Sell Put 和 Sell Call 策略提供可操作的分析。

### 主要功能

- **量化分析** — Black-Scholes 模型計算選擇權定價，完整 Greeks（Delta, Gamma, Theta, Vega）
- **CP 評分系統** — 綜合年化報酬率、安全邊際、Delta 風險、Theta 效率的複合評分
- **AI 市場解讀** — Google Gemini 分析新聞、分析師評級和宏觀環境，提供定性分析
- **多標的支援** — 追蹤 TSLA、AMZN、NVDA（可自訂）
- **全自動管線** — GitHub Actions 每個交易日 PT 6:00 AM 自動執行
- **Email 通知** — 報告自動寄送到信箱
- **雙語支援** — 支援繁體中文（預設）和英文報告

### 快速開始

```bash
# 安裝
git clone https://github.com/laiyanlong/options-daily-report.git
cd options-daily-report
pip install -r requirements.txt

# 執行（無 AI — 不需 API key）
python generate_report.py

# 執行（含 AI 解讀）
GEMINI_API_KEY=your_key python generate_report.py

# 指定日期
REPORT_DATE=2026-03-24 python generate_report.py

# 英文報告
REPORT_LANG=en python generate_report.py
```

### GitHub Actions 設定

1. Fork 此 repo
2. 到 `Settings > Secrets` 設定：
   - `GEMINI_API_KEY`（可選）— Google Gemini API key
   - `EMAIL_PASSWORD`（可選）— Gmail 應用程式密碼
3. 手動觸發：`Actions > Daily Options Report > Run workflow`
4. 或等自動執行：每個交易日 PT 6:00 AM

### 手動觸發參數

| 參數 | 預設值 | 選項 |
|------|--------|------|
| `report_date` | 今天 | 任意 `YYYY-MM-DD` |
| `report_lang` | `zh` | `zh`（繁體中文）或 `en`（English）|

### 費用

完全免費 — GitHub Actions 免費、yfinance 免費、Gemini API 免費 tier（每天 250 次）。

---

<div align="center">

**[View Reports](reports/) · [Report Issue](https://github.com/laiyanlong/options-daily-report/issues)**

</div>
