# Roadmap / 開發路線圖

[English](#english) | [繁體中文](#繁體中文)

---

## English

### v1.0 — Foundation ✅
- [x] Black-Scholes quantitative analysis
- [x] Full Greeks (Delta, Gamma, Theta, Vega)
- [x] CP scoring system
- [x] AI market commentary (Google Gemini)
- [x] Daily automated pipeline (GitHub Actions)
- [x] Email delivery
- [x] Bilingual support (zh/en)
- [x] Dynamic ticker list
- [x] Date override for backfill

### v1.1 — Enhanced Analytics ✅
- [x] Interactive HTML report with Plotly charts (Price History, IV Smile, CP Comparison, Delta Heatmap)
- [x] Earnings calendar auto-detection and 14-day warning banner
- [x] IV percentile rank (vs 52-week historical volatility range)
- [x] Telegram notification integration (summary push via Bot API)
- [x] Docker support for self-hosted deployment (Dockerfile + docker-compose)
- [x] Test suite — 32 unit tests with GitHub Actions CI

### v1.2 — Options Intelligence ✅
- [x] Put/Call ratio tracking — volume & OI ratio with bullish/bearish signal per ticker
- [x] Max Pain calculation — max pain price from full options chain, distance from current price
- [x] Unusual options activity — detect high volume/OI ratio strikes, flag smart money flow
- [x] Expected Move calculation — ATM straddle price for weekly expected range
- [x] Probability of Profit (POP) — Black-Scholes based POP for each recommended trade
- [x] Bid-Ask spread quality — rate spreads as Excellent/Good/Fair/Poor, flag wide spreads

### v2.0 — Multi-Strategy ✅
- [x] Iron Condor analysis — combine Sell Put + Sell Call into defined-risk spreads with P&L charts
- [x] Vertical Spread (Bull Put / Bear Call) — max loss/gain calculations with risk/reward ratios
- [x] Short Strangle & Straddle — ATM and OTM straddle/strangle pricing with breakeven levels
- [x] Wheel Strategy tracker — track Sell Put → assignment → Sell Call cycle, calculate running yield
- [x] Calendar Spread — front-month vs back-month IV comparison for time spread opportunities
- [x] Risk-defined position sizing — auto-calculate position size based on account size and max risk %

### v2.1 — Data & Backtesting ✅
- [x] Historical report database — SQLite/DuckDB to store all past reports for trend queries
- [x] Backtest engine — compare past CP-recommended trades vs actual outcomes (win rate, avg P&L)
- [x] Rolling performance dashboard — track strategy P&L over 30/60/90 days
- [x] IV vs HV divergence — alert when implied vol significantly exceeds realized vol (selling opportunity)
- [x] Correlation matrix — show correlation between tracked tickers to avoid concentrated risk
- [x] Greeks portfolio aggregation — if holding multiple positions, show net portfolio Greeks
- [x] Trade journal export — CSV/Excel export of all recommended trades with outcomes
- [x] Strategy win rate statistics — track historical accuracy of each strategy type

### v3.0 — Smart Automation ✅
- [x] Web dashboard — Streamlit/Gradio app for interactive exploration and filtering
- [x] Multiple AI providers — OpenAI GPT-4o, Claude Sonnet, Ollama (local LLM)
- [x] Portfolio tracking — input your positions, get personalized daily adjustments
- [x] Smart alerts — push notification when IV Rank >80%, or CP score >80, or earnings approaching
- [x] Options flow integration — aggregate unusual flow data from public sources
- [x] Sector rotation signals — track sector ETF options flow to identify rotation trends
- [x] Fed/macro event calendar — auto-flag FOMC, CPI, NFP dates with historical IV impact
- [x] Watchlist management — save/load custom ticker watchlists with notes
- [x] Multi-timeframe analysis — combine weekly, monthly, and quarterly expiration views
- [x] Auto-roll suggestions — detect expiring positions and recommend optimal roll timing

### v3.1 — Advanced Risk Management ✅
- [x] Portfolio-level Greeks aggregation — net Delta, Gamma, Theta, Vega across all open positions
- [x] Value at Risk (VaR) calculation — daily and weekly VaR using historical simulation
- [x] Correlation-adjusted position sizing — reduce size when adding correlated underlyings
- [x] Margin optimization across strategies — estimate margin impact before entering trades
- [x] Scenario analysis (what-if price moves ±5%, ±10%) — project P&L under various market conditions
- [x] Tail risk assessment using historical drawdowns — stress test portfolio against 2020/2022 events
- [x] Beta-weighted Delta — normalize all positions to SPY-equivalent Delta exposure
- [x] Buying power utilization tracking — monitor capital efficiency across strategies

### v4.0 — Social & Community ✅
- [x] Reddit r/options sentiment analysis — NLP-based sentiment scoring from top posts and comments
- [x] StockTwits integration — real-time sentiment feed for tracked tickers
- [x] Community strategy sharing platform — publish and subscribe to other users' strategy configs
- [x] Leaderboard for strategy performance — anonymized ranking by risk-adjusted returns
- [x] User portfolio import/export — support for broker CSV formats (IBKR, Schwab, TD)
- [x] Discord bot with interactive commands — query reports, get alerts, run quick analysis via slash commands
- [x] Collaborative watchlists — shared ticker lists with team annotations
- [x] Strategy marketplace — browse and clone proven strategy configurations

### v5.0 — Community-Driven Intelligence

- [ ] **Live Backtest Dashboard** — GitHub Pages site showing verified historical win rates, cumulative P&L curves, and strategy performance over time
- [ ] **Paper Trading Mode** — virtual portfolio tracking for risk-free strategy validation, weekly performance reports
- [ ] **Strategy A/B Testing** — run multiple parameter combinations simultaneously, community-submitted configs, auto-ranking
- [ ] **ML Strike Selection** — XGBoost model trained on historical data (IV rank, HV, P/C ratio, GEX, earnings proximity) to predict optimal strikes
- [ ] **Volatility Regime Detection** — classify market as low-vol/normal/high-vol/crisis, auto-adjust strategy parameters per regime
- [ ] **Earnings IV Crush Database** — historical IV crush data per ticker per earnings event, data-driven earnings plays
- [ ] **Options Flow Anomaly Scoring** — confidence-scored unusual activity with historical validation of signal accuracy
- [ ] **Weekly Community Challenge** — crowdsourced trade selection competitions with auto-scoring and leaderboard
- [ ] **Trade Signal Subscription** — push notifications via Telegram/Discord/Email for high-confidence trade signals
- [ ] **Multi-Language Reports** — Japanese, Korean, Spanish support via community-contributed translations
- [ ] **IBKR Paper Trading API** — connect to Interactive Brokers paper account for simulated execution
- [ ] **Real-Time Position Monitor** — live P&L tracking for open positions with auto-roll and close alerts

### Moonshot
- [ ] RAG-powered analysis — AI references all past reports for trend context and pattern recognition
- [ ] Broker API integration (IBKR/Schwab) — one-click order execution directly from report recommendations
- [ ] Dark pool data integration — institutional flow signals from FINRA and exchange data
- [ ] Community strategy plugins — user-contributed analysis modules with a plugin API
- [ ] Mobile app — React Native app with push notifications and quick trade actions
- [ ] Social sentiment scoring — Reddit/X/StockTwits multi-source sentiment for each ticker
- [ ] Gamma exposure (GEX) calculation — predict support/resistance from dealer hedging flows
- [ ] Options market microstructure — analyze order book depth and hidden liquidity
- [ ] Machine learning strike selection — train models on historical data to optimize strike/expiry picks
- [ ] Real-time streaming dashboard — WebSocket-based live updates during market hours
- [ ] Voice assistant integration — "Hey Siri, what's my best Sell Put today?" via Shortcuts
- [ ] Crypto options support — extend analysis to BTC/ETH options on Deribit

---

Want to work on something? Check [CONTRIBUTING.md](CONTRIBUTING.md) or [open an issue](https://github.com/laiyanlong/options-daily-report/issues)!

---

## 繁體中文

### v1.0 — 基礎建設 ✅
- [x] Black-Scholes 量化分析引擎
- [x] 完整希臘字母計算（Delta、Gamma、Theta、Vega）
- [x] CP 綜合評分系統
- [x] AI 市場解讀（Google Gemini 自動生成）
- [x] 每日自動化流水線（GitHub Actions 定時執行）
- [x] Email 報告寄送
- [x] 雙語支援（繁中 / 英文）
- [x] 動態標的清單（環境變數可覆蓋）
- [x] 日期回填功能（可指定過去日期重跑）

### v1.1 — 進階分析 ✅
- [x] 互動式 HTML 報告 — 內含 Plotly 圖表（股價走勢、IV Smile、CP 比較、Delta 熱力圖）
- [x] 財報日曆自動偵測 — 14 天內財報自動顯示警告橫幅
- [x] IV 百分位排名 — 對照 52 週歷史波動率區間定位
- [x] Telegram 推播通知 — 透過 Bot API 傳送每日摘要
- [x] Docker 容器化部署 — 提供 Dockerfile 及 docker-compose 一鍵啟動
- [x] 測試套件 — 32 個單元測試搭配 GitHub Actions CI

### v1.2 — 選擇權情報 ✅
- [x] Put/Call 比率追蹤 — 成交量與未平倉比率，搭配看多/看空訊號
- [x] Max Pain 計算 — 從完整選擇權鏈計算最大痛點價位及與現價距離
- [x] 異常選擇權活動偵測 — 揪出量比異常高的履約價，標記大戶動向
- [x] 預期波動範圍 — 用 ATM 跨式價格計算週預期區間
- [x] 獲利機率（POP） — 以 Black-Scholes 模型計算每筆推薦交易的獲利機率
- [x] Bid-Ask 價差品質 — 將價差分為 Excellent/Good/Fair/Poor，標記過寬價差

### v2.0 — 多腳策略 ✅
- [x] Iron Condor 分析 — 結合 Sell Put + Sell Call 組成限定風險價差，含損益圖
- [x] 垂直價差（Bull Put / Bear Call） — 最大虧損/獲利計算及風險報酬比
- [x] Short Strangle 與 Straddle — ATM 及 OTM 勒式/跨式定價與損益平衡點
- [x] Wheel 策略追蹤器 — 追蹤 Sell Put → 被指派 → Sell Call 的完整循環收益
- [x] Calendar Spread — 近月 vs 遠月 IV 比較，識別時間價差機會
- [x] 風險限定部位大小計算 — 根據帳戶規模與最大風險比例自動算出部位大小

### v2.1 — 數據與回測 ✅
- [x] 歷史報告資料庫 — 使用 SQLite/DuckDB 儲存所有歷史報告，支援趨勢查詢
- [x] 回測引擎 — 比較過去 CP 推薦交易與實際結果（勝率、平均損益）
- [x] 滾動績效儀表板 — 追蹤 30/60/90 天策略損益表現
- [x] IV vs HV 背離警報 — 當隱含波動率顯著超過實際波動率時發出賣方機會提醒
- [x] 相關性矩陣 — 顯示追蹤標的間的相關性，避免部位過度集中
- [x] 投資組合希臘字母匯總 — 持有多個部位時顯示淨組合希臘字母
- [x] 交易日誌匯出 — 所有推薦交易及結果可匯出為 CSV/Excel
- [x] 策略勝率統計 — 追蹤各策略類型的歷史準確率

### v3.0 — 智慧自動化 ✅
- [x] 網頁儀表板 — 使用 Streamlit/Gradio 建構互動式瀏覽與篩選介面
- [x] 多 AI 供應商 — 支援 OpenAI GPT-4o、Claude Sonnet、Ollama（本地 LLM）
- [x] 投資組合追蹤 — 輸入現有部位，取得每日個人化調整建議
- [x] 智慧警報 — IV Rank 超過 80%、CP 評分超過 80、財報逼近時推播通知
- [x] 選擇權資金流整合 — 匯整公開來源的異常資金流數據
- [x] 板塊輪動訊號 — 追蹤產業 ETF 選擇權資金流以識別輪動趨勢
- [x] Fed／總經事件日曆 — 自動標記 FOMC、CPI、非農等日期及歷史 IV 影響
- [x] 觀察清單管理 — 儲存與載入自訂標的清單及備註
- [x] 多時間框架分析 — 整合週到期、月到期、季到期的綜合視角
- [x] 自動轉倉建議 — 偵測即將到期部位並推薦最佳轉倉時機

### v3.1 — 進階風險管理 ✅
- [x] 投資組合層級希臘字母匯總 — 所有未平倉部位的淨 Delta、Gamma、Theta、Vega
- [x] 風險值（VaR）計算 — 使用歷史模擬法計算日/週 VaR
- [x] 相關性調整部位大小 — 新增相關性高的標的時自動縮減部位
- [x] 跨策略保證金最佳化 — 進場前預估保證金影響
- [x] 情境分析（假設股價 ±5%、±10%） — 在各種市場狀況下預測損益
- [x] 尾部風險評估 — 以 2020/2022 等歷史回撤數據壓力測試投資組合
- [x] Beta 加權 Delta — 將所有部位正規化為 SPY 等價 Delta 曝險
- [x] 購買力使用率追蹤 — 監控跨策略的資金使用效率

### v4.0 — 社群互動
- [x] Reddit r/options 情緒分析 — 基於 NLP 從熱門貼文與留言計算情緒分數
- [x] StockTwits 整合 — 追蹤標的即時情緒動態
- [x] 社群策略分享平台 — 發布與訂閱其他使用者的策略配置
- [x] 策略績效排行榜 — 依風險調整報酬匿名排名
- [x] 使用者投資組合匯入/匯出 — 支援券商 CSV 格式（IBKR、Schwab、TD）
- [x] Discord 機器人 — 透過斜線指令查詢報告、接收警報、快速分析
- [x] 協作觀察清單 — 共享標的清單並附加團隊註記
- [x] 策略市集 — 瀏覽並複製經驗證的策略配置

### v5.0 — 社群驅動智慧

- [ ] **即時回測儀表板** — GitHub Pages 網站展示經過驗證的歷史勝率、累積損益曲線和策略表現
- [ ] **模擬交易模式** — 虛擬投資組合追蹤，無風險策略驗證，每週績效報告
- [ ] **策略 A/B 測試** — 同時執行多種參數組合，社群提交設定，自動排名
- [ ] **ML 選擇 Strike** — 使用 XGBoost 訓練模型預測最佳 strike（特徵：IV Rank、HV、P/C Ratio、GEX、距財報天數）
- [ ] **波動率環境偵測** — 將市場分類為低波/正常/高波/危機，每種環境自動調整策略參數
- [ ] **財報 IV Crush 資料庫** — 每檔標的每次財報的歷史 IV 崩塌數據，數據驅動的財報策略
- [ ] **選擇權異常活動評分** — 具信心分數的異常活動偵測，附帶歷史信號準確率驗證
- [ ] **每週社群挑戰** — 群眾外包交易選擇競賽，自動評分和排行榜
- [ ] **交易信號訂閱** — 透過 Telegram/Discord/Email 推送高信心交易信號
- [ ] **多語言報告** — 日文、韓文、西班牙文支援，透過社群貢獻翻譯
- [ ] **IBKR 模擬交易 API** — 連接 Interactive Brokers 模擬帳戶進行模擬執行
- [ ] **即時部位監控** — 未平倉部位即時損益追蹤，附自動轉倉和平倉提醒

### 登月計畫
- [x] RAG 智慧分析 — AI 參照所有歷史報告進行趨勢脈絡分析與模式辨識
- [x] 券商 API 串接（IBKR/Schwab） — 從報告推薦直接一鍵下單
- [x] 暗池數據整合 — 從 FINRA 及交易所取得法人資金流訊號
- [x] 社群策略外掛 — 使用者貢獻分析模組，提供 Plugin API
- [x] 行動應用程式 — React Native App 含推播通知及快速交易功能
- [x] 多來源社群情緒評分 — 整合 Reddit/X/StockTwits 多平台情緒
- [x] Gamma 曝險（GEX）計算 — 從造市商避險推估支撐/壓力位
- [x] 選擇權市場微結構分析 — 分析掛單簿深度與隱性流動性
- [x] 機器學習履約價選擇 — 用歷史數據訓練模型最佳化履約價與到期日選取
- [x] 即時串流儀表板 — 以 WebSocket 在盤中即時更新
- [x] 語音助理整合 — 透過 Siri Shortcuts 問「今天最佳 Sell Put 是什麼？」
- [x] 加密貨幣選擇權支援 — 將分析延伸至 Deribit 的 BTC/ETH 選擇權

---

想參與開發？請參閱 [CONTRIBUTING.md](CONTRIBUTING.md) 或 [建立 Issue](https://github.com/laiyanlong/options-daily-report/issues)！
