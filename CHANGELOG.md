# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/), adheres to [Semantic Versioning](https://semver.org/).

## [5.0.0] - 2026-03-27

### Added
- 9 ML/quantitative prediction models (ml_models.py, advanced_predictions.py)
- ML Strike Selector — multi-factor scoring for optimal strike selection
- Volatility Regime Classifier — low/normal/high/crisis market detection
- IV Mean Reversion — z-score based IV direction prediction
- Earnings IV Crush Predictor — historical crush database per ticker
- Price Direction Predictor — technical signal aggregation
- Expected Move Accuracy Tracker — quantify volatility risk premium
- Options Flow Signal Score — directional bias from volume analysis
- Correlation Regime Shift Detector — portfolio risk monitoring
- Theta Decay Curve — optimal exit timing model
- Full 6-month backtest runner with multi-strategy comparison

## [4.0.0] - 2026-03-26

### Added
- Live Backtest Dashboard (GitHub Pages) with Plotly charts
- Live stock prices with auto-refresh (60s interval) and intraday charts
- Reddit sentiment analysis (public JSON API)
- Portfolio import/export (CSV, IBKR/Schwab formats)
- Strategy sharing and marketplace
- Discord bot message formatter
- Collaborative watchlists with annotations
- Leaderboard system

## [3.1.0] - 2026-03-26

### Added
- Portfolio-level Greeks aggregation
- Value at Risk (VaR) — historical simulation
- Scenario analysis (price moves ±1% to ±10%)
- Beta-weighted Delta (SPY-equivalent)
- Buying power utilization tracking
- Correlation-adjusted position sizing

## [3.0.0] - 2026-03-26

### Added
- Smart alerts engine (IV rank, CP score, P/C ratio, earnings)
- Macro event calendar (FOMC, CPI, NFP, Triple Witching 2026)
- Watchlist management (JSON save/load)
- Multi-timeframe analysis (weekly/monthly/quarterly)
- Auto-roll suggestions for expiring positions

## [2.1.0] - 2026-03-26

### Added
- SQLite historical database for trades and metrics
- Backtest engine with win/loss tracking
- IV vs HV divergence analysis
- Correlation matrix with diversification scoring
- Trade journal CSV export
- Strategy win rate statistics

## [2.0.0] - 2026-03-26

### Added
- Iron Condor analysis with P&L calculations
- Vertical Spreads (Bull Put / Bear Call)
- Short Strangle & Straddle
- Wheel Strategy tracker
- Calendar Spread (front vs back month IV)
- Risk-defined position sizing

## [1.2.0] - 2026-03-26

### Added
- Put/Call ratio tracking with bullish/bearish signal
- Max Pain calculation from full options chain
- Unusual options activity detection (volume/OI > 2x)
- Expected Move from ATM straddle pricing
- Probability of Profit (POP) per trade
- Bid-Ask spread quality rating
- Gamma Exposure (GEX) for support/resistance levels

## [1.1.0] - 2026-03-26

### Added
- Interactive HTML report with Plotly charts
- Earnings calendar auto-detection (14-day warning)
- IV Percentile Rank (vs 52-week range)
- Telegram notification integration
- Docker support (Dockerfile + docker-compose)
- Test suite (40 unit tests) with CI

## [1.0.0] - 2026-03-25

### Added
- Initial release
- Black-Scholes quantitative analysis with full Greeks
- CP scoring system for trade ranking
- AI market commentary (Google Gemini)
- Daily automated pipeline (GitHub Actions)
- Email delivery
- Bilingual support (zh/en)
- Dynamic ticker list
- Date override for backfill
