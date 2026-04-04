# DappGo Options App — Design Document

**Date**: 2026-03-29
**Status**: Approved — Ready for Implementation
**Author**: Yan Long Lai + Claude Opus 4.6

---

## 1. Overview / 概覽

A cross-platform mobile + desktop app for options strategy analysis and backtesting. Built with React Native / Expo, running on iOS, iPadOS, and macOS. All calculations run locally on-device — no server required for core features.

跨平台選擇權策略分析和回測 App。使用 React Native / Expo 開發，支援 iOS、iPadOS 和 macOS。所有核心計算在裝置本地執行，不需要伺服器。

---

## 2. Design Decisions / 設計決策

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Target users | Self-use first, architecture ready for SaaS | Start personal, commercialize later |
| Tech stack | React Native / Expo | Existing React/TS experience, cross-platform, large ecosystem |
| Data source | GitHub static + free stock API, minimal cloud | Zero server cost, offline capable |
| Computation | Client-side (TypeScript) | No server dependency, instant results |
| Navigation | 5-tab bottom navigation | iOS standard UX, easy to extend |
| Backtest UX | Simple + Advanced mode toggle | Beginner-friendly + power-user capable |
| Theme | Dark default + auto Light/Dark switch | Finance app convention, Apple compliance |
| State management | Zustand | Lightweight, already used in pbp-dashboard |
| Local database | expo-sqlite | Free, built-in, offline capable |
| Charting | Victory Native or react-native-charts | Best React Native chart libraries |

---

## 3. Architecture / 架構

```
┌─────────────────────────────────────────────────┐
│              React Native / Expo App             │
│         (iOS + iPadOS + macOS Catalyst)          │
├─────────────────────────────────────────────────┤
│  UI Layer (React Native + Expo Router)           │
│  ┌─────┬────────┬────────┬────────┬──────────┐  │
│  │Dash │Reports │Backtest│Matrix  │Settings  │  │
│  │board│        │        │        │          │  │
│  └─────┴────────┴────────┴────────┴──────────┘  │
├─────────────────────────────────────────────────┤
│  Calculation Engine (TypeScript, local)           │
│  • Black-Scholes / Greeks                        │
│  • CP Score / POP                                │
│  • Backtest Engine                               │
│  • IV Mean Reversion / Regime Detection          │
│  • Model Scoring                                 │
├─────────────────────────────────────────────────┤
│  Data Layer                                      │
│  • GitHub API → Reports / Historical Data        │
│  • Stock Price API → Live Quotes                 │
│  • Local SQLite → Cache / Backtest Results       │
│  • Zustand Store → App State                     │
├─────────────────────────────────────────────────┤
│  Minimal Cloud (only when needed)                │
│  • AI Commentary → Gemini API (key stored local) │
│  • Future SaaS → FastAPI (add when commercial)   │
└─────────────────────────────────────────────────┘
```

### Data Flow

```
GitHub API (reports/*.md, data.json)
     │
     ▼
  Parser ──→ SQLite Cache ──→ Zustand Store ──→ UI Components
     │                              │
     │                        Calculation Engine
     │                         (BS, Greeks, POP,
Stock API ──→ Live Quotes ──→   Backtest, IV, etc)
(Alpha Vantage)                     │
                                    ▼
                              Results → Charts / Tables
```

### Client-Side Computation Feasibility

| Calculation | Feasible on Device? | Notes |
|-------------|-------------------|-------|
| Black-Scholes / Greeks | ✅ Yes | Pure math, JS native |
| CP Score / POP | ✅ Yes | Pure formula |
| Backtest (historical) | ✅ Yes | JSON data + local computation |
| IV Mean Reversion | ✅ Yes | Statistics, no Python needed |
| Volatility Regime | ✅ Yes | Threshold classification |
| Direction Prediction | ✅ Yes | Technical indicators in JS |
| Live stock price | ⚠️ Need API | Alpha Vantage free (25 req/day) |
| ML model inference | ⚠️ Depends | Simple models via ONNX.js |
| AI commentary | ❌ Need cloud | Gemini API key required |

---

## 4. Tab Design / 頁面設計

### Tab 1: Dashboard — 首頁概覽

**Purpose**: At-a-glance market overview + model verdict + today's top picks

**Sections:**
1. **Live Price Cards** — TSLA, AMZN, NVDA, SPY with mini sparklines
   - Data source: GitHub data.json or Stock API
   - Shows: price, change %, intraday sparkline

2. **Model Verdict Banner** — Unified signal from all 9 models
   - Market regime (🟢🟡🟠🔴) + VIX + position size recommendation
   - Per-ticker: IV signal, direction, confidence, composite score
   - Source: local calculation engine

3. **Today's Top Picks** — 1-2 best trades from latest report
   - Shows: symbol, strategy, strike, premium, POP, annualized return
   - Tap to view detail or add to backtest

**Interactions:**
- Pull-to-refresh updates data
- Tap price card → jump to that ticker's Matrix tab
- Tap top pick → jump to Report detail or Backtest

---

### Tab 2: Reports — 報告瀏覽

**Purpose**: Browse and search daily reports with smart filtering

**List View:**
- Each report card shows: date, per-ticker summary (price, IV rank, model rating, best trade)
- Filter by: ticker (All/TSLA/AMZN/NVDA) + date range (week/month/all)
- Search: keyword search within report content
- Sorted by date descending (newest first)

**Detail View** (tap a report card):
- Segmented tabs: Overview | Options | Strategy | Model | AI Commentary
- Renders parsed markdown sections from `reports/YYYY-MM-DD.md`
- Key interaction: **tap any trade to add to Backtest watchlist** (cross-tab)

**Data Flow:**
```
GitHub API → GET /repos/{owner}/{repo}/contents/reports/
          → Parse markdown → Display
          → Cache in SQLite (offline access)
```

---

### Tab 3: Backtest — 回測

**Purpose**: Validate strategies against historical data

**Simple Mode** (default):
```
Select: Ticker → Strategy → OTM% (slider 3-15%) → Period (3mo/6mo/1y/2y)
Action: [▶ Run Backtest]
```
- One ticker, one strategy, quick validation
- Results: win rate, total P&L, Sharpe, MaxDD, P&L curve chart

**Advanced Mode** (toggle):
```
Portfolio of positions:
  + Add manually (ticker, strategy, strike, expiry)
  + Import from Reports tab (bookmarked trades)
  
Compare all positions side-by-side:
  - Multi-line P&L curves on same chart
  - Comparison table: WR, P&L, Sharpe, MaxDD, POP, Star Rating
  - AI recommendation: "Best Pick" with reasoning
```

**Results Section:**
- Interactive P&L curve chart (Plotly-like, multi-line)
- Comparison table with star rating system
- Highlight: Best Sharpe, Lowest MaxDD, Highest POP
- Actions: Save to SQLite, Export CSV, Share screenshot

**Backtest Engine (local computation):**
```typescript
interface BacktestInput {
  symbol: string;
  strategy: 'sell_put' | 'sell_call' | 'iron_condor' | 'bull_put_spread';
  strike: number;
  otmPct?: number;  // alternative to specific strike
  period: '3mo' | '6mo' | '1y' | '2y';
  holdingDays: number;  // default 7
}

interface BacktestResult {
  trades: number;
  wins: number;
  winRate: number;
  totalPnl: number;
  sharpe: number;
  maxDrawdown: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  pnlCurve: { date: string; pnl: number }[];
}
```

---

### Tab 4: Matrix — 選擇權 Strike 比較

**Purpose**: Compare different strikes for same expiry, find best CP value

**Controls:**
- Ticker selector: [TSLA ▼] with current price
- Expiry tabs: [4/10] [4/17] [4/24] [5/1] ...
- Type tabs: [Sell Put] [Sell Call]

**Chart Section:**
- Three-axis chart (same as dashboard TSLA Matrix):
  - Bars: Premium (Bid) per strike — gold highlight for best
  - Green line: IV %
  - Purple line: POP %

**Swipeable Strike Cards** (mobile):
- Each card shows one strike with full metrics:
  - Strike, OTM%, Bid, Ask, Spread%, IV, Delta, Volume, OI
  - Annualized Return, POP, Star Rating (★★★★★)
- Color-coded rating: green (★★★★+), gold (★★★), red (★★)
- Actions per card: [Backtest] [Compare ☑]

**iPad/Mac**: Cards shown as grid (no swipe needed)

**Quick Compare** (bottom sheet):
- Check 2-3 cards → instant comparison summary
- "A has X% more POP but Y% less annualized return"
- [Compare Selected → Backtest] sends to Tab 3

**Data Source:**
- Live: Stock API → option chain data → local BS calculation
- Cached: GitHub data.json (tsla_matrix section)

---

### Tab 5: Settings — 設定

**Sections:**
1. **Profile**: GitHub username, report repo name
2. **Tickers**: Manage tracked ticker list (add/remove)
3. **API Keys**: Gemini key, Alpha Vantage key (stored in device Keychain)
4. **Appearance**: Theme (Dark/Light/Auto), Language (繁中/EN)
5. **Notifications**: Daily report ready, high CP alert, IV spike alert
6. **Data**: Cache size, backtest history count, clear cache, export all data
7. **About**: App version, DappGo branding, link to website

**Future Commercial Hooks:**
- "Upgrade to Pro" banner (locked features)
- Account login (when SaaS ready)
- Subscription management

---

## 5. Project Structure / 專案結構

```
dappgo-options-app/
├── app/                        # Expo Router pages
│   ├── (tabs)/
│   │   ├── _layout.tsx         # Tab Navigator
│   │   ├── index.tsx           # Tab 1: Dashboard
│   │   ├── reports.tsx         # Tab 2: Reports list
│   │   ├── backtest.tsx        # Tab 3: Backtest
│   │   ├── matrix.tsx          # Tab 4: Matrix
│   │   └── settings.tsx        # Tab 5: Settings
│   ├── report/[date].tsx       # Report Detail page
│   └── backtest/result.tsx     # Backtest Result page
│
├── src/
│   ├── engine/                 # Local Calculation Engine (CORE IP)
│   │   ├── black-scholes.ts    # BS pricing + Greeks
│   │   ├── backtest.ts         # Backtest engine
│   │   ├── cp-score.ts         # CP scoring system
│   │   ├── iv-analysis.ts      # IV Mean Reversion + z-score
│   │   ├── regime.ts           # Volatility Regime classifier
│   │   ├── direction.ts        # Price Direction predictor
│   │   ├── pop.ts              # Probability of Profit
│   │   ├── expected-move.ts    # Expected Move calculator
│   │   └── model-verdict.ts    # Unified 9-model verdict
│   │
│   ├── data/                   # Data Layer
│   │   ├── github-api.ts       # GitHub API: read reports
│   │   ├── stock-api.ts        # Stock price API (Alpha Vantage)
│   │   ├── sqlite.ts           # Local SQLite operations
│   │   ├── cache.ts            # Cache strategy (TTL, invalidation)
│   │   └── parser.ts           # Markdown report parser
│   │
│   ├── store/                  # Zustand State Management
│   │   ├── app-store.ts        # Global state (tickers, prices)
│   │   ├── backtest-store.ts   # Backtest portfolio + results
│   │   └── settings-store.ts   # User settings (persisted)
│   │
│   ├── components/             # Shared Components
│   │   ├── charts/             # Chart components
│   │   │   ├── SparkLine.tsx   # Mini price sparkline
│   │   │   ├── PnLCurve.tsx    # P&L line chart
│   │   │   ├── MatrixChart.tsx # 3-axis matrix chart
│   │   │   └── StrikeCard.tsx  # Swipeable strike card
│   │   ├── ui/                 # Base UI components
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── TabButton.tsx
│   │   │   ├── Slider.tsx
│   │   │   └── StarRating.tsx
│   │   └── trade/              # Trade-specific components
│   │       ├── VerdictBanner.tsx    # Model verdict display
│   │       ├── TradeRow.tsx         # Single trade row
│   │       ├── CompareTable.tsx     # Side-by-side comparison
│   │       └── ReportCard.tsx       # Report list item
│   │
│   ├── theme/                  # Theming
│   │   ├── colors.ts           # Dark/Light color palettes
│   │   ├── typography.ts       # Font scales
│   │   └── spacing.ts          # Layout spacing
│   │
│   └── utils/                  # Utilities
│       ├── format.ts           # Number/date formatting
│       ├── constants.ts        # App constants
│       └── types.ts            # Shared TypeScript types
│
├── assets/                     # Images, fonts, icons
├── app.json                    # Expo config
├── tsconfig.json
├── package.json
└── README.md
```

---

## 6. Tech Stack & Dependencies / 技術棧

| Category | Package | Purpose | Cost |
|----------|---------|---------|------|
| Framework | Expo SDK 54 | Cross-platform runtime | Free |
| UI Framework | React Native 0.81 | Native UI components | Free |
| Navigation | Expo Router | File-based routing | Free |
| State | Zustand | Global state management | Free |
| Database | expo-sqlite | Local data storage | Free |
| Charts | Victory Native / react-native-svg | Interactive charts | Free |
| HTTP | axios or fetch | API calls | Free |
| Markdown | react-native-markdown-display | Render reports | Free |
| Keychain | expo-secure-store | API key storage | Free |
| Theme | React Native built-in | Dark/Light mode | Free |
| **Total** | | | **$0** |

Only paid item: Apple Developer Account ($99/year) — only needed for App Store submission.

---

## 7. Data Sources / 數據來源

### Static Data (from GitHub)
```
GET https://api.github.com/repos/laiyanlong/options-daily-report/contents/reports/
GET https://api.github.com/repos/laiyanlong/options-daily-report/contents/dashboard/data.json

Rate limit: 60 req/hr (unauthenticated), 5000 req/hr (with token)
Strategy: Cache aggressively in SQLite, refresh on pull-to-refresh
```

### Live Stock Prices
```
Alpha Vantage (free tier):
GET https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=TSLA&apikey=KEY

Rate limit: 25 req/day (free), 75 req/min (paid $49.99/mo)
Strategy: Cache quotes for 5 minutes, use GitHub data.json as fallback
```

### Options Chain Data
```
Option 1: Parse from GitHub reports (already in data.json tsla_matrix)
Option 2: Alpha Vantage options endpoint (paid tier)
Option 3: Add yfinance fetch to dashboard workflow, save to data.json
```

---

## 8. Offline Strategy / 離線策略

The app should work fully offline with cached data:

| Feature | Online | Offline |
|---------|--------|---------|
| Dashboard | Live prices + latest report | Cached prices + last report |
| Reports | Fetch new from GitHub | Browse cached reports |
| Backtest | Full functionality | Full functionality (uses cached data) |
| Matrix | Live options chain | Last cached chain |
| Settings | Sync | Full functionality |

**Cache Policy:**
- Reports: cache indefinitely (they don't change)
- Prices: cache 5 min (online), use last known (offline)
- Options chain: cache 1 hour
- Backtest results: persist forever in SQLite

---

## 9. Commercial Architecture / 商業化架構

### Free (Personal) Version
- All 5 tabs fully functional
- 3 default tickers (TSLA, AMZN, NVDA)
- Simple backtest mode
- Local calculation engine

### Future Pro Version (Upgrade Hooks)
| Feature | Free | Pro |
|---------|------|-----|
| Tickers | 3 | Unlimited |
| Backtest mode | Simple only | Simple + Advanced |
| Matrix comparison | 2 strikes | Unlimited |
| AI Commentary | None | Gemini-powered |
| Push Notifications | None | Daily report + alerts |
| Export | None | CSV + Screenshot |
| Historical data | 3 months | 2 years |
| ML Models | Basic scoring | Full 9-model suite |

### SaaS Transition Path
```
Current:  App → GitHub API + Local Engine
Future:   App → FastAPI Backend → PostgreSQL
                     ↓
              Auth + Subscription + Multi-user
```

Only change needed: add `src/data/api-client.ts` that wraps FastAPI endpoints, toggle between local and cloud engine based on subscription status.

---

## 10. Implementation Phases / 實作階段

### Phase 1: Foundation (Week 1-2)
- [ ] Expo project setup + Expo Router tabs
- [ ] Theme system (dark/light)
- [ ] GitHub API integration + report parser
- [ ] SQLite setup + cache layer
- [ ] Zustand stores

### Phase 2: Dashboard + Reports (Week 2-3)
- [ ] Dashboard: price cards + model verdict + top picks
- [ ] Reports: list view with filters + detail view
- [ ] Markdown rendering

### Phase 3: Calculation Engine (Week 3-4)
- [ ] Port Black-Scholes / Greeks to TypeScript
- [ ] Port CP Score / POP
- [ ] Port IV analysis + regime detection
- [ ] Port model verdict logic

### Phase 4: Backtest (Week 4-5)
- [ ] Simple mode UI + engine
- [ ] Advanced mode UI + multi-position compare
- [ ] Results visualization (P&L curve, comparison table)
- [ ] Save/export functionality

### Phase 5: Matrix (Week 5-6)
- [ ] Options chain display
- [ ] Three-axis chart
- [ ] Swipeable strike cards
- [ ] Quick compare + send to backtest

### Phase 6: Polish (Week 6-7)
- [ ] Settings page
- [ ] Offline support
- [ ] iPad/Mac layout optimization
- [ ] Performance optimization
- [ ] App icon + splash screen

### Phase 7: Release (Week 7-8)
- [ ] TestFlight beta testing
- [ ] Bug fixes
- [ ] App Store submission (if desired)

---

## 11. Key Principles / 核心原則

1. **Client-first**: All computation on device. Server is optional.
2. **Offline-capable**: App works without internet using cached data.
3. **YAGNI**: Build only what's needed now. Commercial features are hooks, not implementations.
4. **Maintainable**: Clear separation: engine / data / store / UI.
5. **Testable**: Engine module has zero UI dependency — pure functions, unit testable.
6. **Brandable**: DappGo branding throughout, ready for commercial skin.

---

*Document approved. Ready for implementation when needed.*
