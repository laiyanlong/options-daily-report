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

### v2.1 — Data & Backtesting
- [ ] Historical report database — SQLite/DuckDB to store all past reports for trend queries
- [ ] Backtest engine — compare past CP-recommended trades vs actual outcomes (win rate, avg P&L)
- [ ] Rolling performance dashboard — track strategy P&L over 30/60/90 days
- [ ] IV vs HV divergence — alert when implied vol significantly exceeds realized vol (selling opportunity)
- [ ] Correlation matrix — show correlation between tracked tickers to avoid concentrated risk
- [ ] Greeks portfolio aggregation — if holding multiple positions, show net portfolio Greeks
- [ ] Trade journal export — CSV/Excel export of all recommended trades with outcomes
- [ ] Strategy win rate statistics — track historical accuracy of each strategy type

### v3.0 — Smart Automation
- [ ] Web dashboard — Streamlit/Gradio app for interactive exploration and filtering
- [ ] Multiple AI providers — OpenAI GPT-4o, Claude Sonnet, Ollama (local LLM)
- [ ] Portfolio tracking — input your positions, get personalized daily adjustments
- [ ] Smart alerts — push notification when IV Rank >80%, or CP score >80, or earnings approaching
- [ ] Options flow integration — aggregate unusual flow data from public sources
- [ ] Sector rotation signals — track sector ETF options flow to identify rotation trends
- [ ] Fed/macro event calendar — auto-flag FOMC, CPI, NFP dates with historical IV impact
- [ ] Watchlist management — save/load custom ticker watchlists with notes
- [ ] Multi-timeframe analysis — combine weekly, monthly, and quarterly expiration views
- [ ] Auto-roll suggestions — detect expiring positions and recommend optimal roll timing

### v3.1 — Advanced Risk Management
- [ ] Portfolio-level Greeks aggregation — net Delta, Gamma, Theta, Vega across all open positions
- [ ] Value at Risk (VaR) calculation — daily and weekly VaR using historical simulation
- [ ] Correlation-adjusted position sizing — reduce size when adding correlated underlyings
- [ ] Margin optimization across strategies — estimate margin impact before entering trades
- [ ] Scenario analysis (what-if price moves ±5%, ±10%) — project P&L under various market conditions
- [ ] Tail risk assessment using historical drawdowns — stress test portfolio against 2020/2022 events
- [ ] Beta-weighted Delta — normalize all positions to SPY-equivalent Delta exposure
- [ ] Buying power utilization tracking — monitor capital efficiency across strategies

### v4.0 — Social & Community
- [ ] Reddit r/options sentiment analysis — NLP-based sentiment scoring from top posts and comments
- [ ] StockTwits integration — real-time sentiment feed for tracked tickers
- [ ] Community strategy sharing platform — publish and subscribe to other users' strategy configs
- [ ] Leaderboard for strategy performance — anonymized ranking by risk-adjusted returns
- [ ] User portfolio import/export — support for broker CSV formats (IBKR, Schwab, TD)
- [ ] Discord bot with interactive commands — query reports, get alerts, run quick analysis via slash commands
- [ ] Collaborative watchlists — shared ticker lists with team annotations
- [ ] Strategy marketplace — browse and clone proven strategy configurations

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

### v2.1 — 數據與回測
- [ ] 歷史報告資料庫 — 使用 SQLite/DuckDB 儲存所有歷史報告，支援趨勢查詢
- [ ] 回測引擎 — 比較過去 CP 推薦交易與實際結果（勝率、平均損益）
- [ ] 滾動績效儀表板 — 追蹤 30/60/90 天策略損益表現
- [ ] IV vs HV 背離警報 — 當隱含波動率顯著超過實際波動率時發出賣方機會提醒
- [ ] 相關性矩陣 — 顯示追蹤標的間的相關性，避免部位過度集中
- [ ] 投資組合希臘字母匯總 — 持有多個部位時顯示淨組合希臘字母
- [ ] 交易日誌匯出 — 所有推薦交易及結果可匯出為 CSV/Excel
- [ ] 策略勝率統計 — 追蹤各策略類型的歷史準確率

### v3.0 — 智慧自動化
- [ ] 網頁儀表板 — 使用 Streamlit/Gradio 建構互動式瀏覽與篩選介面
- [ ] 多 AI 供應商 — 支援 OpenAI GPT-4o、Claude Sonnet、Ollama（本地 LLM）
- [ ] 投資組合追蹤 — 輸入現有部位，取得每日個人化調整建議
- [ ] 智慧警報 — IV Rank 超過 80%、CP 評分超過 80、財報逼近時推播通知
- [ ] 選擇權資金流整合 — 匯整公開來源的異常資金流數據
- [ ] 板塊輪動訊號 — 追蹤產業 ETF 選擇權資金流以識別輪動趨勢
- [ ] Fed／總經事件日曆 — 自動標記 FOMC、CPI、非農等日期及歷史 IV 影響
- [ ] 觀察清單管理 — 儲存與載入自訂標的清單及備註
- [ ] 多時間框架分析 — 整合週到期、月到期、季到期的綜合視角
- [ ] 自動轉倉建議 — 偵測即將到期部位並推薦最佳轉倉時機

### v3.1 — 進階風險管理
- [ ] 投資組合層級希臘字母匯總 — 所有未平倉部位的淨 Delta、Gamma、Theta、Vega
- [ ] 風險值（VaR）計算 — 使用歷史模擬法計算日/週 VaR
- [ ] 相關性調整部位大小 — 新增相關性高的標的時自動縮減部位
- [ ] 跨策略保證金最佳化 — 進場前預估保證金影響
- [ ] 情境分析（假設股價 ±5%、±10%） — 在各種市場狀況下預測損益
- [ ] 尾部風險評估 — 以 2020/2022 等歷史回撤數據壓力測試投資組合
- [ ] Beta 加權 Delta — 將所有部位正規化為 SPY 等價 Delta 曝險
- [ ] 購買力使用率追蹤 — 監控跨策略的資金使用效率

### v4.0 — 社群互動
- [ ] Reddit r/options 情緒分析 — 基於 NLP 從熱門貼文與留言計算情緒分數
- [ ] StockTwits 整合 — 追蹤標的即時情緒動態
- [ ] 社群策略分享平台 — 發布與訂閱其他使用者的策略配置
- [ ] 策略績效排行榜 — 依風險調整報酬匿名排名
- [ ] 使用者投資組合匯入/匯出 — 支援券商 CSV 格式（IBKR、Schwab、TD）
- [ ] Discord 機器人 — 透過斜線指令查詢報告、接收警報、快速分析
- [ ] 協作觀察清單 — 共享標的清單並附加團隊註記
- [ ] 策略市集 — 瀏覽並複製經驗證的策略配置

### 登月計畫
- [ ] RAG 智慧分析 — AI 參照所有歷史報告進行趨勢脈絡分析與模式辨識
- [ ] 券商 API 串接（IBKR/Schwab） — 從報告推薦直接一鍵下單
- [ ] 暗池數據整合 — 從 FINRA 及交易所取得法人資金流訊號
- [ ] 社群策略外掛 — 使用者貢獻分析模組，提供 Plugin API
- [ ] 行動應用程式 — React Native App 含推播通知及快速交易功能
- [ ] 多來源社群情緒評分 — 整合 Reddit/X/StockTwits 多平台情緒
- [ ] Gamma 曝險（GEX）計算 — 從造市商避險推估支撐/壓力位
- [ ] 選擇權市場微結構分析 — 分析掛單簿深度與隱性流動性
- [ ] 機器學習履約價選擇 — 用歷史數據訓練模型最佳化履約價與到期日選取
- [ ] 即時串流儀表板 — 以 WebSocket 在盤中即時更新
- [ ] 語音助理整合 — 透過 Siri Shortcuts 問「今天最佳 Sell Put 是什麼？」
- [ ] 加密貨幣選擇權支援 — 將分析延伸至 Deribit 的 BTC/ETH 選擇權

---

想參與開發？請參閱 [CONTRIBUTING.md](CONTRIBUTING.md) 或 [建立 Issue](https://github.com/laiyanlong/options-daily-report/issues)！
