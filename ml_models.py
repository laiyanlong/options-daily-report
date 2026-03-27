"""
ML Models & Quantitative Predictions — v5.0
Strike selection, volatility regime, IV mean reversion, earnings crush, price direction.
"""
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm


# ============================================================
# Helper: fetch historical data with caching
# ============================================================
_hist_cache: dict[str, tuple[datetime, pd.DataFrame]] = {}
_CACHE_TTL = timedelta(minutes=30)


def _fetch_history(symbol: str, period: str = "1y") -> pd.DataFrame | None:
    """Fetch historical price data via yfinance with simple in-memory cache.

    Returns DataFrame with OHLCV columns, or None on failure.
    """
    cache_key = f"{symbol}_{period}"
    now = datetime.now()
    if cache_key in _hist_cache:
        ts, df = _hist_cache[cache_key]
        if now - ts < _CACHE_TTL:
            return df

    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period=period)
        if df is not None and not df.empty:
            _hist_cache[cache_key] = (now, df)
            return df
    except Exception:
        pass
    return None


def _annualized_hv(close_series: pd.Series, window: int = 20) -> pd.Series:
    """Calculate rolling annualized historical volatility from a close-price series."""
    returns = close_series.pct_change().dropna()
    rolling_std = returns.rolling(window=window).std()
    return rolling_std * np.sqrt(252) * 100  # annualized percentage


# ============================================================
# Model 1: ML Strike Selector (Scoring Model)
# ============================================================
def ml_strike_score(
    symbol: str,
    strike: float,
    current_price: float,
    days_to_exp: int,
    iv: float,
    delta: float,
    cp_score: float,
    option_type: str = "put",
) -> dict | None:
    """Score a strike using a multi-factor weighted model (no external ML needed).

    Factors and weights:
        1. IV Rank percentile (20%) — prefer selling when IV is high
        2. OTM safety (20%) — further OTM = safer
        3. CP score (15%) — existing quality metric from generate_report
        4. Historical win probability (15%) — based on actual past price moves
        5. Theta efficiency (10%) — decay rate relative to premium
        6. Volume/liquidity proxy (10%) — prefer liquid strikes
        7. Trend alignment (10%) — sell puts in uptrends, calls in downtrends

    Args:
        symbol: Ticker symbol (e.g. "TSLA").
        strike: Option strike price.
        current_price: Current underlying price.
        days_to_exp: Days until expiration.
        iv: Implied volatility as a percentage (e.g. 35 for 35%).
        delta: Option delta (absolute value, e.g. 0.20).
        cp_score: Composite quality score from existing analysis (0-100 scale).
        option_type: "put" or "call".

    Returns:
        {"ml_score": float (0-100), "factors": dict, "recommendation": str,
         "confidence": float}
        or None on failure.
    """
    try:
        if strike <= 0 or current_price <= 0 or days_to_exp <= 0 or iv <= 0:
            return None

        # ----------------------------------------------------------
        # Factor 1: IV Rank (20%) — higher IV rank = better for selling
        # ----------------------------------------------------------
        hist = _fetch_history(symbol, "1y")
        iv_rank_score = 50.0  # default mid-range
        if hist is not None and len(hist) > 60:
            hv_series = _annualized_hv(hist["Close"], window=30).dropna()
            if len(hv_series) > 0:
                min_hv = float(hv_series.min())
                max_hv = float(hv_series.max())
                if max_hv > min_hv:
                    iv_rank = (iv - min_hv) / (max_hv - min_hv) * 100.0
                    iv_rank_score = float(np.clip(iv_rank, 0, 100))

        # ----------------------------------------------------------
        # Factor 2: OTM Safety (20%) — distance from current price
        # ----------------------------------------------------------
        if option_type == "put":
            otm_pct = (current_price - strike) / current_price * 100.0
        else:
            otm_pct = (strike - current_price) / current_price * 100.0

        # Score: 0% OTM = 0 points, 5% OTM = 50 points, 10%+ OTM = 100 points
        otm_score = float(np.clip(otm_pct * 10.0, 0, 100))

        # ----------------------------------------------------------
        # Factor 3: CP Score (15%) — pass-through from existing metric
        # ----------------------------------------------------------
        cp_factor = float(np.clip(cp_score, 0, 100))

        # ----------------------------------------------------------
        # Factor 4: Historical Win Probability (15%)
        # ----------------------------------------------------------
        win_score = 50.0
        if hist is not None and len(hist) > 60:
            recent_closes = hist["Close"].iloc[-60:]
            if option_type == "put":
                # Count days price stayed above the strike
                wins = int((recent_closes > strike).sum())
            else:
                # Count days price stayed below the strike
                wins = int((recent_closes < strike).sum())
            win_score = wins / len(recent_closes) * 100.0

        # ----------------------------------------------------------
        # Factor 5: Theta Efficiency (10%)
        # ----------------------------------------------------------
        # Approximate daily theta decay relative to option premium
        # Higher delta (closer to ATM) = more premium but more risk
        # Sweet spot: delta 0.15-0.30 for selling
        abs_delta = abs(delta)
        if 0.10 <= abs_delta <= 0.35:
            theta_score = 80.0 + (0.25 - abs(abs_delta - 0.20)) * 200.0
        elif abs_delta < 0.10:
            theta_score = 40.0  # too far OTM, minimal premium
        else:
            theta_score = max(0.0, 60.0 - (abs_delta - 0.35) * 200.0)
        theta_score = float(np.clip(theta_score, 0, 100))

        # ----------------------------------------------------------
        # Factor 6: Liquidity Proxy (10%)
        # ----------------------------------------------------------
        # Use delta as proxy: ATM options are more liquid
        # Delta 0.3-0.5 = most liquid, score 100
        # Delta < 0.05 or > 0.8 = less liquid
        if 0.15 <= abs_delta <= 0.50:
            liquidity_score = 80.0 + (0.30 - abs(abs_delta - 0.30)) * 133.0
        else:
            liquidity_score = max(20.0, 100.0 - abs(abs_delta - 0.30) * 200.0)
        liquidity_score = float(np.clip(liquidity_score, 0, 100))

        # ----------------------------------------------------------
        # Factor 7: Trend Alignment (10%)
        # ----------------------------------------------------------
        trend_score = 50.0  # neutral default
        if hist is not None and len(hist) >= 20:
            recent = hist["Close"].iloc[-30:]
            ma20 = float(recent.iloc[-20:].mean())
            last_price = float(recent.iloc[-1])
            trend_up = last_price > ma20

            if option_type == "put" and trend_up:
                # Selling puts in uptrend — aligned
                trend_pct = (last_price - ma20) / ma20 * 100.0
                trend_score = min(100.0, 60.0 + trend_pct * 10.0)
            elif option_type == "call" and not trend_up:
                # Selling calls in downtrend — aligned
                trend_pct = (ma20 - last_price) / ma20 * 100.0
                trend_score = min(100.0, 60.0 + trend_pct * 10.0)
            elif option_type == "put" and not trend_up:
                trend_score = 30.0  # counter-trend
            else:
                trend_score = 30.0

        # ----------------------------------------------------------
        # Weighted combination
        # ----------------------------------------------------------
        weights = {
            "iv_rank": 0.20,
            "otm_safety": 0.20,
            "cp_score": 0.15,
            "historical_win": 0.15,
            "theta_efficiency": 0.10,
            "liquidity": 0.10,
            "trend_alignment": 0.10,
        }
        factors = {
            "iv_rank": round(iv_rank_score, 1),
            "otm_safety": round(otm_score, 1),
            "cp_score": round(cp_factor, 1),
            "historical_win": round(win_score, 1),
            "theta_efficiency": round(theta_score, 1),
            "liquidity": round(liquidity_score, 1),
            "trend_alignment": round(trend_score, 1),
        }

        ml_score = sum(factors[k] * weights[k] for k in weights)
        ml_score = float(np.clip(ml_score, 0, 100))

        # Recommendation
        if ml_score >= 75:
            recommendation = "Strong"
        elif ml_score >= 50:
            recommendation = "Moderate"
        elif ml_score >= 30:
            recommendation = "Weak"
        else:
            recommendation = "Avoid"

        # Confidence: based on agreement among top factors
        factor_values = list(factors.values())
        factor_std = float(np.std(factor_values))
        # Lower std = higher agreement = higher confidence
        confidence = float(np.clip(100.0 - factor_std, 30, 95))

        return {
            "ml_score": round(ml_score, 1),
            "factors": factors,
            "recommendation": recommendation,
            "confidence": round(confidence, 1),
        }
    except Exception:
        return None


# ============================================================
# Model 2: Volatility Regime Classifier
# ============================================================
def classify_volatility_regime(symbol: str = "SPY") -> dict | None:
    """Classify current market volatility regime.

    Regimes:
        - "low_vol":  HV20 < 12% and VIX < 15 — steady market, pure sell strategies
        - "normal":   HV20 12-20% and VIX 15-22 — standard selling, balanced approach
        - "high_vol": HV20 20-35% or VIX 22-35 — use defined-risk (IC/spreads)
        - "crisis":   HV20 > 35% or VIX > 35 — reduce exposure, only far OTM

    Returns:
        {"regime": str, "hv20": float, "hv60": float, "vix": float | None,
         "regime_score": float (0-100, higher = more volatile),
         "recommended_strategies": list[str],
         "position_size_multiplier": float (0.25 to 1.0),
         "description": str}
        or None on failure.
    """
    try:
        # Fetch SPY (or given symbol) 90-day history
        hist = _fetch_history(symbol, "6mo")
        if hist is None or len(hist) < 60:
            return None

        close = hist["Close"]
        returns = close.pct_change().dropna()

        # Calculate HV20 and HV60 (annualized)
        if len(returns) < 20:
            return None
        hv20 = float(returns.iloc[-20:].std() * np.sqrt(252) * 100)
        hv60 = float(returns.iloc[-60:].std() * np.sqrt(252) * 100) if len(returns) >= 60 else hv20

        # Try to fetch VIX
        vix = None
        try:
            vix_tk = yf.Ticker("^VIX")
            vix_info = vix_tk.info
            vix = (
                vix_info.get("regularMarketPrice")
                or vix_info.get("previousClose")
            )
            if vix is not None:
                vix = float(vix)
        except Exception:
            pass

        # Classify regime
        # Use both HV20 and VIX; if VIX unavailable, rely on HV20 only
        effective_vix = vix if vix is not None else hv20

        if hv20 > 35 or effective_vix > 35:
            regime = "crisis"
        elif hv20 > 20 or effective_vix > 22:
            regime = "high_vol"
        elif hv20 > 12 or effective_vix > 15:
            regime = "normal"
        else:
            regime = "low_vol"

        # Regime score: 0 = dead calm, 100 = extreme volatility
        # Scale HV20 from 0-50% to 0-100 score
        regime_score = float(np.clip(hv20 / 50.0 * 100.0, 0, 100))

        # Strategies and position sizing per regime
        strategy_map = {
            "low_vol": {
                "strategies": [
                    "Naked puts (CSP)",
                    "Naked calls (covered)",
                    "Short strangles",
                    "Short straddles",
                    "Calendar spreads (sell near-term vol)",
                ],
                "multiplier": 1.0,
                "description": (
                    "Low volatility environment — premiums are thin but wins "
                    "are consistent. Favour naked selling with wider strikes. "
                    "Consider selling ATM for maximum theta."
                ),
            },
            "normal": {
                "strategies": [
                    "Cash-secured puts",
                    "Covered calls",
                    "Iron condors",
                    "Short strangles (defined risk)",
                    "Wheel strategy",
                ],
                "multiplier": 0.8,
                "description": (
                    "Normal volatility — the bread-and-butter environment for "
                    "premium sellers. Standard 30-45 DTE, 1-SD strikes. "
                    "Balance naked and defined-risk positions."
                ),
            },
            "high_vol": {
                "strategies": [
                    "Iron condors (wide wings)",
                    "Bull put spreads",
                    "Bear call spreads",
                    "Jade lizards",
                    "Ratio spreads",
                ],
                "multiplier": 0.5,
                "description": (
                    "Elevated volatility — premiums are rich but risk is real. "
                    "Use defined-risk strategies only. Go further OTM (2+ SD). "
                    "Reduce total portfolio delta."
                ),
            },
            "crisis": {
                "strategies": [
                    "Far OTM credit spreads only",
                    "Protective puts (hedging)",
                    "VIX call spreads (hedge)",
                    "Small iron condors (very wide)",
                    "Cash — reduce exposure",
                ],
                "multiplier": 0.25,
                "description": (
                    "Crisis-level volatility — capital preservation is priority. "
                    "Only sell very far OTM with defined risk. "
                    "Consider raising cash and waiting for vol to subside."
                ),
            },
        }

        regime_info = strategy_map[regime]

        return {
            "regime": regime,
            "hv20": round(hv20, 2),
            "hv60": round(hv60, 2),
            "vix": round(vix, 2) if vix is not None else None,
            "regime_score": round(regime_score, 1),
            "recommended_strategies": regime_info["strategies"],
            "position_size_multiplier": regime_info["multiplier"],
            "description": regime_info["description"],
        }
    except Exception:
        return None


# ============================================================
# Model 3: IV Mean Reversion Signal
# ============================================================
def iv_mean_reversion(symbol: str, current_iv: float) -> dict | None:
    """IV mean reversion analysis — predict whether IV will rise or fall.

    Uses 1 year of rolling 30-day historical volatility as an IV proxy to
    determine where current IV sits relative to its historical distribution.

    Args:
        symbol: Ticker symbol.
        current_iv: Current implied volatility as percentage (e.g. 35 for 35%).

    Returns:
        {"symbol": str, "current_iv": float,
         "iv_mean_1y": float, "iv_std_1y": float,
         "iv_zscore": float, "iv_percentile": float,
         "upper_band": float, "lower_band": float,
         "signal": "Strong Sell"|"Sell"|"Neutral"|"Buy"|"Strong Buy",
         "expected_iv_move": float,
         "days_to_revert": int,
         "confidence": float}
        or None on failure.

    Signal interpretation (from premium-seller perspective):
        - "Strong Sell" (z > 1.5): IV is very high and likely to fall — great for sellers
        - "Sell" (z > 0.5): IV is above average — favourable for selling
        - "Neutral" (-0.5 < z < 0.5): IV near mean — no strong edge
        - "Buy" (z < -0.5): IV is low — avoid selling premium
        - "Strong Buy" (z < -1.5): IV very low — worst time to sell
    """
    try:
        if current_iv <= 0:
            return None

        hist = _fetch_history(symbol, "2y")
        if hist is None or len(hist) < 120:
            return None

        # Calculate rolling 30-day HV as IV proxy
        hv_series = _annualized_hv(hist["Close"], window=30).dropna()
        if len(hv_series) < 60:
            return None

        iv_mean = float(hv_series.mean())
        iv_std = float(hv_series.std())

        if iv_std <= 0:
            return None

        # Z-score of current IV vs historical distribution
        z_score = (current_iv - iv_mean) / iv_std

        # Percentile: what fraction of historical HV was below current IV
        iv_percentile = float((hv_series < current_iv).sum() / len(hv_series) * 100.0)

        # Bands: mean +/- 1.5 standard deviations
        upper_band = iv_mean + 1.5 * iv_std
        lower_band = max(iv_mean - 1.5 * iv_std, 1.0)  # IV can't go below ~1%

        # Signal based on z-score
        if z_score > 1.5:
            signal = "Strong Sell"
        elif z_score > 0.5:
            signal = "Sell"
        elif z_score > -0.5:
            signal = "Neutral"
        elif z_score > -1.5:
            signal = "Buy"
        else:
            signal = "Strong Buy"

        # Expected IV move: reversion towards the mean
        expected_iv_move = iv_mean - current_iv  # negative if IV expected to fall

        # Days to revert: estimate from historical data
        # Look at past episodes with similar z-scores and measure reversion time
        days_to_revert = _estimate_reversion_days(hv_series, z_score, iv_mean, iv_std)

        # Confidence: stronger at extremes, weaker near mean
        abs_z = abs(z_score)
        if abs_z > 2.0:
            confidence = 85.0
        elif abs_z > 1.5:
            confidence = 75.0
        elif abs_z > 1.0:
            confidence = 60.0
        elif abs_z > 0.5:
            confidence = 45.0
        else:
            confidence = 30.0

        # Adjust confidence based on sample consistency
        # Check: what % of past extreme episodes did revert?
        reversion_rate = _historical_reversion_rate(hv_series, iv_mean, iv_std, z_score)
        confidence = confidence * 0.7 + reversion_rate * 0.3

        return {
            "symbol": symbol,
            "current_iv": round(current_iv, 2),
            "iv_mean_1y": round(iv_mean, 2),
            "iv_std_1y": round(iv_std, 2),
            "iv_zscore": round(z_score, 2),
            "iv_percentile": round(iv_percentile, 1),
            "upper_band": round(upper_band, 2),
            "lower_band": round(lower_band, 2),
            "signal": signal,
            "expected_iv_move": round(expected_iv_move, 2),
            "days_to_revert": days_to_revert,
            "confidence": round(float(np.clip(confidence, 20, 95)), 1),
        }
    except Exception:
        return None


def _estimate_reversion_days(
    hv_series: pd.Series, z_score: float, mean: float, std: float
) -> int:
    """Estimate how many trading days it takes for IV to revert from a similar z-score.

    Looks at historical episodes where z-score was in a similar range and measures
    how long it took to cross back to within 0.5 std of the mean.
    """
    try:
        z_series = (hv_series - mean) / std
        reversion_days_list: list[int] = []

        # Define the z-score bucket: +/- 0.3 around current z
        z_low = z_score - 0.3
        z_high = z_score + 0.3

        i = 0
        values = z_series.values
        while i < len(values) - 1:
            if z_low <= values[i] <= z_high:
                # Found a similar episode; count days until z crosses 0.5 threshold
                for j in range(i + 1, len(values)):
                    if abs(values[j]) < 0.5:
                        reversion_days_list.append(j - i)
                        i = j  # skip ahead to avoid double-counting
                        break
                else:
                    # Never reverted in this window
                    pass
            i += 1

        if reversion_days_list:
            return int(np.median(reversion_days_list))
        else:
            # Fallback: rough estimate — higher z takes longer
            return max(5, int(abs(z_score) * 15))
    except Exception:
        return 20  # fallback default


def _historical_reversion_rate(
    hv_series: pd.Series, mean: float, std: float, z_score: float
) -> float:
    """Calculate what percentage of past similar-z episodes reverted within 30 days.

    Returns a value 0-100 representing reversion reliability.
    """
    try:
        z_series = (hv_series - mean) / std
        z_low = z_score - 0.5
        z_high = z_score + 0.5

        total_episodes = 0
        reverted = 0
        values = z_series.values

        i = 0
        while i < len(values) - 30:
            if z_low <= values[i] <= z_high:
                total_episodes += 1
                # Check if it reverted within 30 days
                future_30 = values[i + 1 : i + 31]
                if any(abs(v) < 0.5 for v in future_30):
                    reverted += 1
                i += 30  # skip to avoid overlap
            else:
                i += 1

        if total_episodes == 0:
            return 50.0  # no data, neutral confidence
        return reverted / total_episodes * 100.0
    except Exception:
        return 50.0


# ============================================================
# Model 4: Earnings IV Crush Predictor
# ============================================================
def predict_earnings_crush(symbol: str) -> dict | None:
    """Predict IV crush after earnings based on historical patterns.

    Analyses past earnings events to estimate how much implied volatility
    typically drops after the announcement.

    Returns:
        {"symbol": str, "next_earnings": str | None,
         "days_to_earnings": int,
         "historical_crushes": list[dict],
         "avg_crush_pct": float,
         "median_crush_pct": float,
         "crush_std": float,
         "predicted_crush_range": {"low": float, "high": float},
         "pre_earnings_iv_bump_pct": float,
         "optimal_entry_days_before": int,
         "recommendation": str}
        or None on failure.
    """
    try:
        tk = yf.Ticker(symbol)

        # Get next earnings date
        next_earnings_date = None
        try:
            cal = tk.calendar
            if cal is not None and not cal.empty:
                if hasattr(cal, "columns") and len(cal.columns) > 0:
                    earn_date = pd.Timestamp(cal.columns[0])
                    next_earnings_date = earn_date.to_pydatetime()
        except Exception:
            pass

        # Fetch 2 years of history for crush analysis
        hist = _fetch_history(symbol, "2y")
        if hist is None or len(hist) < 200:
            return None

        close = hist["Close"]
        hv_series = _annualized_hv(close, window=10).dropna()  # shorter window for earnings sensitivity
        if len(hv_series) < 60:
            return None

        # Get past earnings dates
        past_earnings: list[datetime] = []
        try:
            # yfinance earnings_dates returns upcoming and past dates
            earn_df = tk.earnings_dates
            if earn_df is not None and not earn_df.empty:
                for dt_idx in earn_df.index:
                    edate = pd.Timestamp(dt_idx).to_pydatetime().replace(tzinfo=None)
                    # Only use past dates within our history window
                    if edate < datetime.now() and edate > datetime.now() - timedelta(days=730):
                        past_earnings.append(edate)
        except Exception:
            pass

        # If no earnings dates found, try quarterly estimation
        if not past_earnings:
            # Fallback: look for HV spikes as proxy for earnings events
            # Detect peaks in HV (z-score > 1.5)
            hv_mean = float(hv_series.mean())
            hv_std = float(hv_series.std())
            if hv_std > 0:
                z_scores = (hv_series - hv_mean) / hv_std
                spike_dates = z_scores[z_scores > 1.5].index
                # Group spikes that are within 5 days of each other
                grouped: list[datetime] = []
                for dt in spike_dates:
                    dt_naive = dt.to_pydatetime().replace(tzinfo=None) if hasattr(dt, 'to_pydatetime') else dt
                    if not grouped or (dt_naive - grouped[-1]).days > 30:
                        grouped.append(dt_naive)
                past_earnings = grouped

        if not past_earnings:
            # Still no data — return minimal result
            return {
                "symbol": symbol,
                "next_earnings": next_earnings_date.strftime("%Y-%m-%d") if next_earnings_date else None,
                "days_to_earnings": (next_earnings_date - datetime.now()).days if next_earnings_date else -1,
                "historical_crushes": [],
                "avg_crush_pct": 0.0,
                "median_crush_pct": 0.0,
                "crush_std": 0.0,
                "predicted_crush_range": {"low": 0.0, "high": 0.0},
                "pre_earnings_iv_bump_pct": 0.0,
                "optimal_entry_days_before": 5,
                "recommendation": "Insufficient data — cannot estimate crush.",
            }

        # Analyse each past earnings event
        historical_crushes: list[dict] = []
        pre_earnings_bumps: list[float] = []

        for earn_date in sorted(past_earnings)[-8:]:  # last 8 quarters max
            try:
                # Find the nearest trading day index
                hist_dates = close.index
                # Convert to tz-naive for comparison
                hist_dates_naive = hist_dates.tz_localize(None) if hist_dates.tz else hist_dates

                # HV 5 trading days before earnings
                mask_before = hist_dates_naive <= pd.Timestamp(earn_date)
                if mask_before.sum() < 10:
                    continue
                before_idx = mask_before.sum() - 1
                start_before = max(0, before_idx - 4)

                # HV 5 trading days after earnings
                mask_after = hist_dates_naive > pd.Timestamp(earn_date)
                if mask_after.sum() < 5:
                    continue
                after_start = before_idx + 1

                # Calculate HV in windows
                returns = close.pct_change().dropna()
                returns_before = returns.iloc[start_before:before_idx + 1]
                returns_after = returns.iloc[after_start:after_start + 5]

                if len(returns_before) < 3 or len(returns_after) < 3:
                    continue

                hv_before = float(returns_before.std() * np.sqrt(252) * 100)
                hv_after = float(returns_after.std() * np.sqrt(252) * 100)

                if hv_before <= 0:
                    continue

                crush_pct = (hv_before - hv_after) / hv_before * 100.0

                # Pre-earnings bump: compare HV 10 days before to HV 20 days before
                if before_idx >= 20:
                    returns_early = returns.iloc[before_idx - 19:before_idx - 9]
                    returns_late = returns.iloc[before_idx - 9:before_idx + 1]
                    if len(returns_early) >= 5 and len(returns_late) >= 5:
                        hv_early = float(returns_early.std() * np.sqrt(252) * 100)
                        hv_late = float(returns_late.std() * np.sqrt(252) * 100)
                        if hv_early > 0:
                            bump = (hv_late - hv_early) / hv_early * 100.0
                            pre_earnings_bumps.append(bump)

                historical_crushes.append({
                    "date": earn_date.strftime("%Y-%m-%d"),
                    "hv_before": round(hv_before, 2),
                    "hv_after": round(hv_after, 2),
                    "crush_pct": round(crush_pct, 2),
                })
            except Exception:
                continue

        # Aggregate crush statistics
        if historical_crushes:
            crush_values = [c["crush_pct"] for c in historical_crushes]
            avg_crush = float(np.mean(crush_values))
            median_crush = float(np.median(crush_values))
            crush_std = float(np.std(crush_values))
        else:
            avg_crush = 0.0
            median_crush = 0.0
            crush_std = 0.0

        # Predicted range: mean +/- 1 std
        predicted_low = avg_crush - crush_std
        predicted_high = avg_crush + crush_std

        # Pre-earnings bump
        pre_bump = float(np.mean(pre_earnings_bumps)) if pre_earnings_bumps else 0.0

        # Optimal entry: typically 1-3 days before earnings when IV is peaking
        # If pre-bump is large, enter earlier to capture more premium
        if pre_bump > 20:
            optimal_entry = 3
        elif pre_bump > 10:
            optimal_entry = 2
        else:
            optimal_entry = 1

        # Days to next earnings
        days_to_earnings = -1
        if next_earnings_date:
            days_to_earnings = (next_earnings_date - datetime.now()).days

        # Recommendation
        if not historical_crushes:
            recommendation = "Insufficient data — cannot reliably predict crush."
        elif median_crush > 30 and crush_std < 20:
            recommendation = (
                f"High-confidence crush trade. Median crush {median_crush:.0f}% with "
                f"low variance. Sell straddle/strangle {optimal_entry} day(s) before earnings."
            )
        elif median_crush > 15:
            recommendation = (
                f"Moderate crush expected ({median_crush:.0f}%). "
                f"Consider selling iron condor to limit risk. "
                f"Enter {optimal_entry} day(s) before earnings."
            )
        elif median_crush > 0:
            recommendation = (
                f"Mild crush ({median_crush:.0f}%). Edge is thin — "
                "only trade if IV percentile is above 70."
            )
        else:
            recommendation = (
                "Historical data shows IV did NOT consistently crush after earnings. "
                "Avoid earnings crush plays for this symbol."
            )

        return {
            "symbol": symbol,
            "next_earnings": next_earnings_date.strftime("%Y-%m-%d") if next_earnings_date else None,
            "days_to_earnings": days_to_earnings,
            "historical_crushes": historical_crushes,
            "avg_crush_pct": round(avg_crush, 2),
            "median_crush_pct": round(median_crush, 2),
            "crush_std": round(crush_std, 2),
            "predicted_crush_range": {
                "low": round(predicted_low, 2),
                "high": round(predicted_high, 2),
            },
            "pre_earnings_iv_bump_pct": round(pre_bump, 2),
            "optimal_entry_days_before": optimal_entry,
            "recommendation": recommendation,
        }
    except Exception:
        return None


# ============================================================
# Model 5: Price Direction Predictor
# ============================================================
def predict_price_direction(symbol: str, horizon_days: int = 10) -> dict | None:
    """Short-term price direction prediction using technical signals.

    Does NOT predict exact price — estimates the probability of up vs down
    over the given horizon using a consensus of technical indicators.

    Args:
        symbol: Ticker symbol.
        horizon_days: Prediction horizon in trading days (default 10).

    Returns:
        {"symbol": str, "horizon_days": int,
         "bullish_signals": list[str], "bearish_signals": list[str],
         "signal_score": float (-100 to +100, positive = bullish),
         "direction": "Bullish"|"Neutral"|"Bearish",
         "confidence": float (0-100),
         "factors": {
             "trend_ma20": str, "trend_ma50": str,
             "rsi": float, "rsi_signal": str,
             "macd_signal": str,
             "price_vs_52w": float,
             "recent_momentum_5d": float,
             "volume_trend": str
         }}
        or None on failure.
    """
    try:
        hist = _fetch_history(symbol, "1y")
        if hist is None or len(hist) < 200:
            # Try shorter period
            hist = _fetch_history(symbol, "6mo")
            if hist is None or len(hist) < 60:
                return None

        close = hist["Close"]
        volume = hist["Volume"]
        last_price = float(close.iloc[-1])

        bullish: list[str] = []
        bearish: list[str] = []
        score = 0.0

        # ----------------------------------------------------------
        # Factor 1: Price vs 20-day MA (+/- 15 points)
        # ----------------------------------------------------------
        ma20 = float(close.iloc[-20:].mean()) if len(close) >= 20 else last_price
        if last_price > ma20:
            trend_ma20 = "Above"
            pct_above = (last_price - ma20) / ma20 * 100
            pts = min(15.0, 10.0 + pct_above)
            score += pts
            bullish.append(f"Price {pct_above:.1f}% above 20-day MA")
        else:
            trend_ma20 = "Below"
            pct_below = (ma20 - last_price) / ma20 * 100
            pts = min(15.0, 10.0 + pct_below)
            score -= pts
            bearish.append(f"Price {pct_below:.1f}% below 20-day MA")

        # ----------------------------------------------------------
        # Factor 2: Price vs 50-day MA (+/- 15 points)
        # ----------------------------------------------------------
        if len(close) >= 50:
            ma50 = float(close.iloc[-50:].mean())
            if last_price > ma50:
                trend_ma50 = "Above"
                pct_above = (last_price - ma50) / ma50 * 100
                pts = min(15.0, 10.0 + pct_above * 0.5)
                score += pts
                bullish.append(f"Price above 50-day MA (+{pct_above:.1f}%)")
            else:
                trend_ma50 = "Below"
                pct_below = (ma50 - last_price) / ma50 * 100
                pts = min(15.0, 10.0 + pct_below * 0.5)
                score -= pts
                bearish.append(f"Price below 50-day MA (-{pct_below:.1f}%)")
        else:
            trend_ma50 = "N/A"

        # ----------------------------------------------------------
        # Factor 3: RSI(14) (+/- 20 points)
        # ----------------------------------------------------------
        rsi_val = _calculate_rsi(close, period=14)
        if rsi_val is not None:
            if rsi_val > 70:
                rsi_signal = "Overbought"
                score -= 15.0 + min(5.0, (rsi_val - 70) * 0.5)
                bearish.append(f"RSI overbought at {rsi_val:.1f}")
            elif rsi_val > 60:
                rsi_signal = "Bullish"
                score += 10.0
                bullish.append(f"RSI bullish at {rsi_val:.1f}")
            elif rsi_val < 30:
                rsi_signal = "Oversold"
                score += 15.0 + min(5.0, (30 - rsi_val) * 0.5)
                bullish.append(f"RSI oversold at {rsi_val:.1f} (bounce likely)")
            elif rsi_val < 40:
                rsi_signal = "Bearish"
                score -= 10.0
                bearish.append(f"RSI weak at {rsi_val:.1f}")
            else:
                rsi_signal = "Neutral"
        else:
            rsi_val = 50.0
            rsi_signal = "N/A"

        # ----------------------------------------------------------
        # Factor 4: MACD Signal (+/- 15 points)
        # ----------------------------------------------------------
        macd_sig = _calculate_macd_signal(close)
        if macd_sig == "Bullish Crossover":
            score += 15.0
            bullish.append("MACD bullish crossover")
        elif macd_sig == "Bullish":
            score += 10.0
            bullish.append("MACD above signal line")
        elif macd_sig == "Bearish Crossover":
            score -= 15.0
            bearish.append("MACD bearish crossover")
        elif macd_sig == "Bearish":
            score -= 10.0
            bearish.append("MACD below signal line")

        # ----------------------------------------------------------
        # Factor 5: Position vs 52-week range (+/- 10 points)
        # ----------------------------------------------------------
        if len(close) >= 252:
            high_52w = float(close.iloc[-252:].max())
            low_52w = float(close.iloc[-252:].min())
        else:
            high_52w = float(close.max())
            low_52w = float(close.min())

        if high_52w > low_52w:
            price_vs_52w = (last_price - low_52w) / (high_52w - low_52w) * 100.0
        else:
            price_vs_52w = 50.0

        if price_vs_52w > 90:
            score -= 5.0
            bearish.append(f"Near 52-week high ({price_vs_52w:.0f}th percentile)")
        elif price_vs_52w > 70:
            score += 5.0
            bullish.append(f"Strong position in 52-week range ({price_vs_52w:.0f}%)")
        elif price_vs_52w < 10:
            score += 5.0
            bullish.append(f"Near 52-week low — potential bounce ({price_vs_52w:.0f}%)")
        elif price_vs_52w < 30:
            score -= 5.0
            bearish.append(f"Weak position in 52-week range ({price_vs_52w:.0f}%)")

        # ----------------------------------------------------------
        # Factor 6: 5-day Momentum (+/- 15 points)
        # ----------------------------------------------------------
        if len(close) >= 6:
            momentum_5d = (float(close.iloc[-1]) - float(close.iloc[-6])) / float(close.iloc[-6]) * 100.0
        else:
            momentum_5d = 0.0

        if momentum_5d > 3:
            score += 12.0
            bullish.append(f"Strong 5-day momentum: +{momentum_5d:.1f}%")
        elif momentum_5d > 1:
            score += 6.0
            bullish.append(f"Positive 5-day momentum: +{momentum_5d:.1f}%")
        elif momentum_5d < -3:
            score -= 12.0
            bearish.append(f"Weak 5-day momentum: {momentum_5d:.1f}%")
        elif momentum_5d < -1:
            score -= 6.0
            bearish.append(f"Negative 5-day momentum: {momentum_5d:.1f}%")

        # ----------------------------------------------------------
        # Factor 7: Volume Trend (+/- 10 points)
        # ----------------------------------------------------------
        if len(volume) >= 20:
            avg_vol_20 = float(volume.iloc[-20:].mean())
            avg_vol_5 = float(volume.iloc[-5:].mean())
            if avg_vol_20 > 0:
                vol_ratio = avg_vol_5 / avg_vol_20
                if vol_ratio > 1.3:
                    volume_trend = "Increasing"
                    # Volume increase in direction of trend is confirming
                    if momentum_5d > 0:
                        score += 10.0
                        bullish.append("Rising volume confirms uptrend")
                    else:
                        score -= 10.0
                        bearish.append("Rising volume confirms downtrend")
                elif vol_ratio < 0.7:
                    volume_trend = "Decreasing"
                    # Decreasing volume suggests weakening trend
                    if momentum_5d > 0:
                        score -= 3.0
                        bearish.append("Declining volume weakens uptrend")
                    else:
                        score += 3.0
                        bullish.append("Declining volume weakens downtrend")
                else:
                    volume_trend = "Normal"
            else:
                volume_trend = "N/A"
        else:
            volume_trend = "N/A"

        # ----------------------------------------------------------
        # Final scoring
        # ----------------------------------------------------------
        score = float(np.clip(score, -100, 100))

        if score > 20:
            direction = "Bullish"
        elif score < -20:
            direction = "Bearish"
        else:
            direction = "Neutral"

        # Confidence: based on signal agreement
        total_signals = len(bullish) + len(bearish)
        if total_signals > 0:
            agreement = abs(len(bullish) - len(bearish)) / total_signals
        else:
            agreement = 0.0

        # Also factor in score magnitude
        score_magnitude = abs(score) / 100.0
        confidence = (agreement * 50.0 + score_magnitude * 50.0)
        confidence = float(np.clip(confidence, 15, 90))

        return {
            "symbol": symbol,
            "horizon_days": horizon_days,
            "bullish_signals": bullish,
            "bearish_signals": bearish,
            "signal_score": round(score, 1),
            "direction": direction,
            "confidence": round(confidence, 1),
            "factors": {
                "trend_ma20": trend_ma20,
                "trend_ma50": trend_ma50,
                "rsi": round(rsi_val, 1),
                "rsi_signal": rsi_signal,
                "macd_signal": macd_sig,
                "price_vs_52w": round(price_vs_52w, 1),
                "recent_momentum_5d": round(momentum_5d, 2),
                "volume_trend": volume_trend,
            },
        }
    except Exception:
        return None


# ============================================================
# Technical indicator helpers
# ============================================================
def _calculate_rsi(close: pd.Series, period: int = 14) -> float | None:
    """Calculate RSI (Relative Strength Index).

    RSI = 100 - 100 / (1 + RS)
    where RS = avg_gain / avg_loss over `period` days.
    """
    try:
        if len(close) < period + 1:
            return None

        delta = close.diff().dropna()
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta.where(delta < 0, 0.0))

        # Use exponential weighted mean (Wilder's smoothing)
        avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period).mean()
        avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period).mean()

        last_gain = float(avg_gain.iloc[-1])
        last_loss = float(avg_loss.iloc[-1])

        if last_loss == 0:
            return 100.0
        rs = last_gain / last_loss
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return rsi
    except Exception:
        return None


def _calculate_macd_signal(close: pd.Series) -> str:
    """Calculate MACD and return signal string.

    MACD = EMA(12) - EMA(26)
    Signal = EMA(9) of MACD
    Histogram = MACD - Signal

    Returns one of: "Bullish Crossover", "Bullish", "Bearish Crossover",
                    "Bearish", "Neutral"
    """
    try:
        if len(close) < 35:
            return "Neutral"

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        current_hist = float(histogram.iloc[-1])
        prev_hist = float(histogram.iloc[-2])

        # Crossover detection
        if prev_hist < 0 and current_hist >= 0:
            return "Bullish Crossover"
        elif prev_hist > 0 and current_hist <= 0:
            return "Bearish Crossover"
        elif current_hist > 0:
            return "Bullish"
        elif current_hist < 0:
            return "Bearish"
        else:
            return "Neutral"
    except Exception:
        return "Neutral"
