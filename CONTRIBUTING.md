# Contributing to Options Daily Report

Thank you for your interest in contributing! This project is open to everyone, whether you're fixing a typo, adding a new feature, or proposing a whole new analysis module.

[English](#how-to-contribute) | [繁體中文](#如何貢獻)

---

## How to Contribute

### Quick Start

```bash
# 1. Fork & clone
gh repo fork laiyanlong/options-daily-report --clone
cd options-daily-report

# 2. Create a branch
git checkout -b feature/your-feature-name

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run locally (no API key needed for basic testing)
python generate_report.py

# 5. Run with AI (optional)
GEMINI_API_KEY=your_key python generate_report.py

# 6. Commit & push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name

# 7. Open a Pull Request on GitHub
```

### What Can I Work On?

Check the [Issues](https://github.com/laiyanlong/options-daily-report/issues) page. Look for labels:

| Label | Description |
|-------|-------------|
| `good first issue` | Great for newcomers — clear scope, limited code changes |
| `help wanted` | We'd love community help on these |
| `enhancement` | New features or improvements |
| `bug` | Something isn't working |
| `documentation` | Docs improvements |

No matching issue? Feel free to [open one](https://github.com/laiyanlong/options-daily-report/issues/new/choose) to discuss your idea first.

### Feature Ideas We'd Love to See

Here are some areas where contributions would be especially valuable:

#### Analysis & Strategy
- [ ] **Iron Condor / Spread strategies** — extend beyond naked Sell Put/Call
- [ ] **Earnings calendar integration** — auto-flag tickers with upcoming earnings
- [ ] **Sector ETF analysis** — add SPY, QQQ, XLK sector-level options
- [ ] **Historical backtest** — compare recommended trades vs actual outcomes
- [ ] **Risk-adjusted metrics** — Sharpe ratio, max drawdown for strategies

#### Data & Visualization
- [ ] **Interactive HTML report** — charts instead of markdown tables
- [ ] **Plotly/matplotlib charts** — IV surface, P&L diagrams, Greeks heatmaps
- [ ] **Dashboard web app** — Streamlit or Gradio UI for exploring reports
- [ ] **Historical trend DB** — SQLite/DuckDB to store and query past reports

#### Infrastructure
- [ ] **Telegram/Discord bot** — push reports to chat channels
- [ ] **Configurable alerts** — notify when IV spikes or CP score exceeds threshold
- [ ] **Multi-broker integration** — connect to IBKR/TD Ameritrade for live execution
- [ ] **Docker support** — containerize for self-hosted deployment

#### AI & Intelligence
- [ ] **Multiple AI providers** — OpenAI, Claude, local LLMs (Ollama)
- [ ] **RAG with past reports** — AI references historical reports for trend analysis
- [ ] **Sentiment analysis** — social media / Reddit sentiment scoring
- [ ] **Earnings transcript analysis** — AI summarizes earnings calls

### Development Guidelines

#### Code Style
- Python 3.12+
- Use type hints for function signatures
- Keep functions focused — one function, one responsibility
- Use f-strings for formatting

#### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add iron condor strategy analysis
fix: correct delta calculation for deep ITM options
docs: add Japanese translation to README
refactor: extract Greeks calculation into separate module
```

#### Pull Request Checklist
- [ ] Code runs locally with `python generate_report.py`
- [ ] No hardcoded API keys or secrets
- [ ] Updated README if adding new features or config options
- [ ] Added comments for complex logic
- [ ] Tested with at least one ticker

#### Project Structure
```
options-daily-report/
├── generate_report.py    # Main entry — quantitative analysis
├── ai_analysis.py        # AI commentary module
├── requirements.txt      # Dependencies
├── reports/              # Generated reports (auto-committed)
└── .github/
    └── workflows/        # CI/CD
```

When adding a new module, keep it in a separate `.py` file and import it in `generate_report.py` with a `try/except` block for graceful degradation:

```python
try:
    from your_module import your_function
    # use it
except Exception as e:
    print(f"Module skipped: {e}")
```

### Review Process

1. Open a PR with a clear description of what and why
2. Maintainer reviews within 48 hours
3. Address feedback if any
4. Merge!

We value all contributions equally — a docs fix is just as welcome as a new feature.

---

## 如何貢獻

### 快速開始

```bash
# 1. Fork 並 clone
gh repo fork laiyanlong/options-daily-report --clone
cd options-daily-report

# 2. 建立分支
git checkout -b feature/your-feature-name

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 本地執行（不需要 API key）
python generate_report.py

# 5. 提交 Pull Request
git add . && git commit -m "feat: 你的功能描述"
git push origin feature/your-feature-name
```

### 我可以做什麼？

查看 [Issues](https://github.com/laiyanlong/options-daily-report/issues) 頁面，特別是標有 `good first issue` 和 `help wanted` 的議題。

### 我們特別歡迎的貢獻方向

#### 分析與策略
- Iron Condor / Spread 策略分析
- 財報日曆自動整合
- 歷史回測功能
- 板塊 ETF 分析

#### 資料與視覺化
- 互動式 HTML 報告（含圖表）
- Streamlit/Gradio 儀表板
- 歷史數據庫（SQLite/DuckDB）

#### 基礎建設
- Telegram/Discord 推送
- Docker 容器化
- 多券商 API 整合

#### AI 增強
- 多 AI 供應商支援（OpenAI、Claude、本地 LLM）
- 基於歷史報告的 RAG 分析
- 社群情緒分析

### 開發規範
- Python 3.12+，使用 type hints
- Commit message 遵循 Conventional Commits
- PR 前請確認本地可正常執行
- 不要提交 API key 或任何密鑰

---

## Questions?

Open an [issue](https://github.com/laiyanlong/options-daily-report/issues) or start a [discussion](https://github.com/laiyanlong/options-daily-report/discussions). We're happy to help!
