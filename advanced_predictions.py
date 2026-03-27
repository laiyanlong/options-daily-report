"""
Advanced Predictions & Backtest Module — v5.0
Options flow signals, correlation shift, theta decay, expected move accuracy, full backtest.
"""
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm


# ============================================================
# Helpers
# ============================================================

def _get_current_price(tk) -> float:
    """Extract current price from a yfinance Ticker object."""
    info = tk.info
    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose", 0)
    )
    return float(price)


def _bs_price(S: float, K: float, T: float, sigma: float,
              r: float = 0.05, option_type: str = "put") -> float:
    """Black-Scholes option price.

    Args:
        S: Spot price.
        K: Strike price.
        T: Time to expiration in years.
        sigma: Volatility (decimal, e.g. 0.35 for 35%).
        r: Risk-free rate (decimal).
        option_type: "put" or "call".

    Returns:
        Theoretical option price.
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    if option_type == "call":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return max(price, 0.0)


# ============================================================
# Model 6: Expected Move Accuracy Tracker
# ============================================================

def expected_move_accuracy(symbol: str, lookback_weeks: int = 12) -> dict | None:
    """Track how accurate the options market's expected move has been.

    The "volatility risk premium" = implied vol consistently overestimates
    actual moves.  This quantifies that edge for options sellers.

    Returns:
        {"symbol": str, "weeks_analyzed": int,
         "times_within_expected": int, "accuracy_pct": float,
         "avg_overestimate_pct": float,
         "seller_edge_pct": float,
         "weekly_results": list[dict],
         "current_expected_move_pct": float,
         "adjusted_expected_move_pct": float}
    """
    try:
        tk = yf.Ticker(symbol)

        # Fetch enough weekly data
        weeks_needed = lookback_weeks + 4  # buffer
        hist = tk.history(period=f"{weeks_needed * 7}d")
        if hist.empty or len(hist) < 20:
            return None

        # Also fetch 1-year daily data for HV calculation
        hist_daily = tk.history(period="1y")
        if hist_daily.empty or len(hist_daily) < 60:
            return None

        # Calculate annualized HV from daily returns (30-day rolling)
        daily_returns = hist_daily["Close"].pct_change().dropna()
        rolling_hv = daily_returns.rolling(window=30).std() * np.sqrt(252)
        rolling_hv = rolling_hv.dropna()

        if len(rolling_hv) < lookback_weeks:
            return None

        # Resample to weekly OHLC
        weekly = hist.resample("W-FRI").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        }).dropna()

        if len(weekly) < lookback_weeks + 1:
            return None

        # For each completed week, compare actual move vs expected move
        weekly_results: list[dict] = []
        times_within = 0
        overestimates: list[float] = []

        # Use the last lookback_weeks completed weeks (exclude current partial week)
        analysis_weeks = weekly.iloc[-(lookback_weeks + 1):-1]

        # Build a mapping from date to the nearest rolling HV value
        hv_series = rolling_hv.copy()

        for i in range(len(analysis_weeks)):
            row = analysis_weeks.iloc[i]
            week_open = float(row["Open"])
            week_close = float(row["Close"])

            if week_open <= 0:
                continue

            # Actual weekly move (absolute)
            actual_move_pct = abs(week_close - week_open) / week_open * 100.0

            # Expected weekly move: use HV at the start of the week / sqrt(52)
            week_date = analysis_weeks.index[i]
            # Find nearest HV value on or before the week start
            hv_before = hv_series[hv_series.index <= week_date]
            if hv_before.empty:
                continue
            annualized_hv = float(hv_before.iloc[-1])
            expected_weekly_pct = annualized_hv / math.sqrt(52) * 100.0

            if expected_weekly_pct <= 0:
                continue

            within = actual_move_pct <= expected_weekly_pct
            if within:
                times_within += 1

            overestimate = expected_weekly_pct - actual_move_pct
            overestimates.append(overestimate)

            weekly_results.append({
                "week_ending": str(week_date.date()),
                "actual_move_pct": round(actual_move_pct, 2),
                "expected_move_pct": round(expected_weekly_pct, 2),
                "within_expected": within,
                "overestimate_pct": round(overestimate, 2),
            })

        if not weekly_results:
            return None

        weeks_analyzed = len(weekly_results)
        accuracy_pct = times_within / weeks_analyzed * 100.0
        avg_overestimate = float(np.mean(overestimates))
        seller_edge = avg_overestimate  # positive = sellers win on average

        # Current expected move
        current_hv = float(rolling_hv.iloc[-1])
        current_expected_pct = current_hv / math.sqrt(52) * 100.0

        # Adjusted expected move (remove historical overestimate)
        adjustment_factor = max(0.0, 1.0 - avg_overestimate / current_expected_pct) if current_expected_pct > 0 else 1.0
        adjusted_expected_pct = current_expected_pct * adjustment_factor

        return {
            "symbol": symbol,
            "weeks_analyzed": weeks_analyzed,
            "times_within_expected": times_within,
            "accuracy_pct": round(accuracy_pct, 1),
            "avg_overestimate_pct": round(avg_overestimate, 2),
            "seller_edge_pct": round(seller_edge, 2),
            "weekly_results": weekly_results,
            "current_expected_move_pct": round(current_expected_pct, 2),
            "adjusted_expected_move_pct": round(adjusted_expected_pct, 2),
        }
    except Exception:
        return None


# ============================================================
# Model 7: Options Flow Signal Score
# ============================================================

def flow_signal_score(tk) -> dict | None:
    """Score options flow signals for directional bias.

    Returns:
        {"symbol": str, "flow_score": float (-100 to 100),
         "direction": "Bullish"|"Bearish"|"Neutral",
         "signals": list[dict],
         "call_volume_ratio": float,
         "put_volume_ratio": float,
         "smart_money_indicator": str,
         "confidence": float}
    """
    try:
        expiries = tk.options
        if not expiries:
            return None

        chain = tk.option_chain(expiries[0])
        calls = chain.calls
        puts = chain.puts

        if calls.empty or puts.empty:
            return None

        current_price = _get_current_price(tk)
        if current_price <= 0:
            return None

        symbol = tk.ticker

        # --- Volume analysis ---
        call_vol = int(calls["volume"].fillna(0).sum())
        put_vol = int(puts["volume"].fillna(0).sum())
        call_oi = int(calls["openInterest"].fillna(0).sum())
        put_oi = int(puts["openInterest"].fillna(0).sum())

        total_vol = call_vol + put_vol
        if total_vol == 0:
            return None

        # Call/put volume split (0.5 = balanced)
        call_share = call_vol / total_vol

        signals: list[dict] = []
        score = 0.0

        # Signal 1: Call vs Put volume dominance (-30 to +30)
        vol_signal = (call_share - 0.5) * 60.0  # maps 0->-30, 0.5->0, 1->+30
        score += vol_signal
        signals.append({
            "name": "Volume Dominance",
            "value": round(vol_signal, 1),
            "detail": f"Call share: {call_share:.1%}",
        })

        # Signal 2: Volume/OI ratio — aggressive new positioning (-20 to +20)
        call_vol_oi = call_vol / call_oi if call_oi > 0 else 0.0
        put_vol_oi = put_vol / put_oi if put_oi > 0 else 0.0

        # High call vol/oi = aggressive call buying = bullish
        # High put vol/oi = aggressive put buying = bearish
        aggression_signal = 0.0
        if call_vol_oi > 3.0:
            aggression_signal += min((call_vol_oi - 3.0) * 5.0, 20.0)
        if put_vol_oi > 3.0:
            aggression_signal -= min((put_vol_oi - 3.0) * 5.0, 20.0)
        score += aggression_signal
        signals.append({
            "name": "Aggression (Vol/OI)",
            "value": round(aggression_signal, 1),
            "detail": f"Call V/OI: {call_vol_oi:.1f}, Put V/OI: {put_vol_oi:.1f}",
        })

        # Signal 3: OTM call vs OTM put activity (-25 to +25)
        otm_calls = calls[calls["strike"] > current_price * 1.02]
        otm_puts = puts[puts["strike"] < current_price * 0.98]
        otm_call_vol = int(otm_calls["volume"].fillna(0).sum())
        otm_put_vol = int(otm_puts["volume"].fillna(0).sum())
        otm_total = otm_call_vol + otm_put_vol

        otm_signal = 0.0
        if otm_total > 0:
            otm_call_share = otm_call_vol / otm_total
            otm_signal = (otm_call_share - 0.5) * 50.0  # -25 to +25
        score += otm_signal
        signals.append({
            "name": "OTM Flow",
            "value": round(otm_signal, 1),
            "detail": f"OTM Call Vol: {otm_call_vol}, OTM Put Vol: {otm_put_vol}",
        })

        # Signal 4: Smart money — large OTM positions with high premium (-25 to +25)
        # Look for strikes with high dollar volume (volume * lastPrice)
        smart_signal = 0.0
        smart_detail = "No large OTM flow detected"

        for label, df, direction, otm_filter in [
            ("call", calls, 1.0, calls["strike"] > current_price * 1.05),
            ("put", puts, -1.0, puts["strike"] < current_price * 0.95),
        ]:
            otm_df = df[otm_filter].copy()
            if otm_df.empty:
                continue
            otm_df = otm_df.copy()
            otm_df["dollar_volume"] = (
                otm_df["volume"].fillna(0) * otm_df["lastPrice"].fillna(0)
            )
            large_flow = otm_df[otm_df["dollar_volume"] > 100_000]
            if not large_flow.empty:
                total_dollar = float(large_flow["dollar_volume"].sum())
                contribution = min(total_dollar / 1_000_000 * 25.0, 25.0) * direction
                smart_signal += contribution
                smart_detail = f"Large {label} flow: ${total_dollar:,.0f}"

        score += smart_signal
        signals.append({
            "name": "Smart Money Flow",
            "value": round(smart_signal, 1),
            "detail": smart_detail,
        })

        # Clamp score to [-100, 100]
        score = max(-100.0, min(100.0, score))

        # Determine direction
        if score > 20:
            direction = "Bullish"
        elif score < -20:
            direction = "Bearish"
        else:
            direction = "Neutral"

        # Confidence based on total volume and signal agreement
        signal_values = [s["value"] for s in signals]
        signs = [1 if v > 0 else (-1 if v < 0 else 0) for v in signal_values]
        agreement = abs(sum(signs)) / max(len(signs), 1)
        volume_factor = min(total_vol / 10_000, 1.0)  # higher volume = more confidence
        confidence = (agreement * 0.6 + volume_factor * 0.4) * 100.0

        # Smart money indicator
        if abs(smart_signal) > 10:
            smart_money = "Bullish Institutional" if smart_signal > 0 else "Bearish Institutional"
        else:
            smart_money = "No Clear Signal"

        # Volume ratios (vs simple benchmark: use OI as proxy for "average")
        call_volume_ratio = call_vol / max(call_oi / 20, 1)  # rough daily avg proxy
        put_volume_ratio = put_vol / max(put_oi / 20, 1)

        return {
            "symbol": symbol,
            "flow_score": round(score, 1),
            "direction": direction,
            "signals": signals,
            "call_volume_ratio": round(call_volume_ratio, 2),
            "put_volume_ratio": round(put_volume_ratio, 2),
            "smart_money_indicator": smart_money,
            "confidence": round(confidence, 1),
        }
    except Exception:
        return None


# ============================================================
# Model 8: Correlation Regime Shift Detector
# ============================================================

def detect_correlation_shift(tickers: list[str], lookback: int = 60) -> dict | None:
    """Detect if cross-asset correlations are shifting (rising = risk).

    Returns:
        {"current_avg_correlation": float,
         "historical_avg_correlation": float,
         "correlation_zscore": float,
         "regime": "normal"|"elevated"|"crisis",
         "trend": "rising"|"falling"|"stable",
         "rolling_30d": list[float],
         "dates": list[str],
         "risk_alert": bool,
         "recommendation": str}
    """
    try:
        if len(tickers) < 2:
            return None

        # Fetch 1 year of daily prices for all tickers
        data = yf.download(tickers, period="1y", progress=False)
        if data.empty:
            return None

        # Handle multi-level columns from yf.download
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]

        if closes.shape[1] < 2:
            return None

        # Calculate daily returns
        returns = closes.pct_change().dropna()
        if len(returns) < lookback:
            return None

        n_assets = returns.shape[1]

        # Calculate rolling 30-day average pairwise correlation
        window = 30
        rolling_corrs: list[float] = []
        rolling_dates: list[str] = []

        for end_idx in range(window, len(returns) + 1):
            window_returns = returns.iloc[end_idx - window:end_idx]
            corr_matrix = window_returns.corr()

            # Extract upper triangle (exclude diagonal)
            mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
            pairwise = corr_matrix.values[mask]
            # Filter out NaN values
            pairwise = pairwise[~np.isnan(pairwise)]

            if len(pairwise) > 0:
                avg_corr = float(np.mean(pairwise))
                rolling_corrs.append(avg_corr)
                rolling_dates.append(str(returns.index[end_idx - 1].date()))

        if len(rolling_corrs) < 30:
            return None

        rolling_arr = np.array(rolling_corrs)
        current_corr = rolling_arr[-1]
        historical_mean = float(np.mean(rolling_arr))
        historical_std = float(np.std(rolling_arr))

        # Z-score
        if historical_std > 0:
            z_score = (current_corr - historical_mean) / historical_std
        else:
            z_score = 0.0

        # Regime classification
        if z_score > 2.0:
            regime = "crisis"
        elif z_score > 1.0:
            regime = "elevated"
        else:
            regime = "normal"

        # Trend: compare last 10 observations vs previous 10
        if len(rolling_arr) >= 20:
            recent = float(np.mean(rolling_arr[-10:]))
            previous = float(np.mean(rolling_arr[-20:-10]))
            diff = recent - previous
            if diff > 0.03:
                trend = "rising"
            elif diff < -0.03:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Risk alert
        risk_alert = z_score > 1.5

        # Recommendation
        if regime == "crisis":
            recommendation = (
                "Correlations at crisis levels — reduce position sizes by 50%, "
                "avoid new premium sales, consider hedging with index puts."
            )
        elif regime == "elevated":
            recommendation = (
                "Elevated correlations — reduce position sizes by 25%, "
                "widen strikes on new trades, increase cash allocation."
            )
        elif trend == "rising":
            recommendation = (
                "Correlations trending up — monitor closely, consider "
                "tightening stops and reducing portfolio delta."
            )
        else:
            recommendation = (
                "Correlation regime normal — proceed with standard "
                "position sizing and strategy allocation."
            )

        return {
            "current_avg_correlation": round(current_corr, 4),
            "historical_avg_correlation": round(historical_mean, 4),
            "correlation_zscore": round(z_score, 2),
            "regime": regime,
            "trend": trend,
            "rolling_30d": [round(v, 4) for v in rolling_corrs],
            "dates": rolling_dates,
            "risk_alert": risk_alert,
            "recommendation": recommendation,
        }
    except Exception:
        return None


# ============================================================
# Model 9: Theta Decay Curve & Optimal Exit
# ============================================================

def optimal_theta_exit(strike: float, current_price: float, premium: float,
                       days_to_exp: int, iv_pct: float,
                       option_type: str = "put") -> dict | None:
    """Model theta decay curve and find optimal exit point.

    Returns:
        {"decay_curve": list[dict],
         "optimal_exit_dte": int,
         "optimal_exit_pct": float,
         "current_theta_capture_pct": float,
         "risk_reward_by_dte": list[dict],
         "recommendation": str}
    """
    try:
        if (strike <= 0 or current_price <= 0 or premium <= 0
                or days_to_exp <= 0 or iv_pct <= 0):
            return None

        sigma = iv_pct / 100.0
        r = 0.05

        decay_curve: list[dict] = []
        risk_reward: list[dict] = []

        prev_value = premium
        best_rr_dte = days_to_exp
        best_rr = 0.0

        for dte in range(days_to_exp, -1, -1):
            T = dte / 365.0
            theo_value = _bs_price(current_price, strike, T, sigma, r, option_type)
            theta_captured_pct = (premium - theo_value) / premium * 100.0 if premium > 0 else 0.0
            theta_captured_pct = max(0.0, min(100.0, theta_captured_pct))

            decay_curve.append({
                "dte": dte,
                "theoretical_value": round(theo_value, 4),
                "theta_captured_pct": round(theta_captured_pct, 2),
            })

            # Risk/reward: theta captured vs remaining gamma risk
            # Gamma risk increases as we approach expiry (especially < 7 DTE)
            if dte > 0:
                # Gamma risk proxy: inversely proportional to sqrt(DTE)
                gamma_risk = 1.0 / math.sqrt(dte) if dte > 0 else 10.0
                rr = theta_captured_pct / (gamma_risk * 100.0) if gamma_risk > 0 else 0.0

                risk_reward.append({
                    "dte": dte,
                    "theta_captured_pct": round(theta_captured_pct, 2),
                    "gamma_risk_score": round(gamma_risk, 4),
                    "risk_reward_ratio": round(rr, 4),
                })

                if rr > best_rr:
                    best_rr = rr
                    best_rr_dte = dte

            prev_value = theo_value

        # Find optimal exit: where marginal theta capture rate starts declining
        # Look at the rate of theta capture per day
        optimal_dte = best_rr_dte
        optimal_pct = 0.0

        for entry in decay_curve:
            if entry["dte"] == optimal_dte:
                optimal_pct = entry["theta_captured_pct"]
                break

        # Current theta capture (at current DTE)
        current_capture = decay_curve[0]["theta_captured_pct"] if decay_curve else 0.0

        # Build recommendation
        if optimal_dte >= days_to_exp:
            recommendation = (
                f"Hold position — optimal exit not yet reached. "
                f"Current theta capture: {current_capture:.1f}%."
            )
        elif optimal_dte <= 0:
            recommendation = (
                f"Close immediately — past optimal exit point. "
                f"Gamma risk outweighs remaining theta."
            )
        else:
            recommendation = (
                f"Close at DTE {optimal_dte} for {optimal_pct:.1f}% of max profit. "
                f"After DTE {optimal_dte}, gamma risk accelerates faster than theta capture."
            )

        return {
            "decay_curve": decay_curve,
            "optimal_exit_dte": optimal_dte,
            "optimal_exit_pct": round(optimal_pct, 2),
            "current_theta_capture_pct": round(current_capture, 2),
            "risk_reward_by_dte": risk_reward,
            "recommendation": recommendation,
        }
    except Exception:
        return None


# ============================================================
# BACKTEST RUNNER
# ============================================================

def _simulate_premium(stock_price: float, strike: float, hv: float,
                      dte: int = 7) -> float:
    """Estimate option premium using Black-Scholes with historical vol."""
    T = dte / 365.0
    sigma = hv if hv > 0 else 0.30
    return _bs_price(stock_price, strike, T, sigma, 0.05, "put")


def _iv_zscore_at(daily_returns: pd.Series, idx: int,
                  window: int = 30, lookback: int = 252) -> float:
    """Calculate IV z-score (using HV proxy) at a specific index."""
    if idx < lookback:
        return 0.0
    recent_vol = daily_returns.iloc[idx - window:idx].std() * np.sqrt(252)
    hist_vols = []
    for j in range(lookback, idx):
        hv = daily_returns.iloc[j - window:j].std() * np.sqrt(252)
        hist_vols.append(hv)
    if not hist_vols or np.std(hist_vols) == 0:
        return 0.0
    return (recent_vol - np.mean(hist_vols)) / np.std(hist_vols)


def run_full_backtest(tickers: list[str] | None = None,
                      period: str = "6mo") -> dict:
    """Run comprehensive backtest of all models against historical data.

    For each ticker, for each trading day in the period:
    1. Calculate what each model would have recommended
    2. Simulate the trade outcome (7-day put sale)
    3. Track cumulative P&L and statistics

    Returns:
        Full backtest results with baseline and filtered strategy performance.
    """
    if tickers is None:
        tickers = ["TSLA", "AMZN", "NVDA"]

    all_trades: list[dict] = []

    for symbol in tickers:
        try:
            # Fetch extended history (need lookback buffer for indicators)
            tk = yf.Ticker(symbol)
            hist = tk.history(period="1y")
            if hist.empty or len(hist) < 100:
                # Try with less data
                hist = tk.history(period=period)
                if hist.empty or len(hist) < 30:
                    continue

            prices = hist["Close"].values
            dates = hist.index
            daily_returns = pd.Series(prices).pct_change().dropna()

            # Determine backtest window based on period
            if period == "6mo":
                bt_start = max(126, len(prices) - 126)
            elif period == "3mo":
                bt_start = max(63, len(prices) - 63)
            else:
                bt_start = max(126, len(prices) - 126)

            # Ensure we have enough lookback for indicators
            bt_start = max(bt_start, 60)

            for i in range(bt_start, len(prices) - 7):
                entry_price = float(prices[i])
                entry_date = str(dates[i].date())

                # 5% OTM put strike
                strike = round(entry_price * 0.95, 2)

                # Calculate HV at entry for premium estimation
                if i >= 30:
                    recent_returns = daily_returns.iloc[i - 30:i]
                    hv = float(recent_returns.std() * np.sqrt(252))
                else:
                    hv = 0.30

                # Simulate premium received
                premium = _simulate_premium(entry_price, strike, hv, dte=7)
                if premium <= 0:
                    premium = entry_price * 0.003  # fallback: ~0.3% of stock price

                # Check outcome after 7 days
                exit_price = float(prices[i + 7])
                if exit_price >= strike:
                    # Put expires worthless — full premium kept
                    pnl = premium
                    win = True
                else:
                    # Put assigned — loss is (strike - exit_price) minus premium
                    pnl = premium - (strike - exit_price)
                    win = False

                # Calculate model signals at entry time
                # IV z-score
                iv_z = _iv_zscore_at(daily_returns, i, window=30, lookback=min(252, i))

                # Simple trend direction: 20-day vs 50-day MA
                if i >= 50:
                    ma20 = float(np.mean(prices[i - 20:i]))
                    ma50 = float(np.mean(prices[i - 50:i]))
                    direction_bullish = ma20 > ma50
                else:
                    direction_bullish = True

                # Regime: use recent volatility as proxy
                if i >= 60:
                    recent_hv = float(daily_returns.iloc[i - 30:i].std() * np.sqrt(252))
                    hist_hv = float(daily_returns.iloc[:i].std() * np.sqrt(252))
                    hv_ratio = recent_hv / hist_hv if hist_hv > 0 else 1.0
                else:
                    hv_ratio = 1.0

                # Composite ML-like score (higher = better trade)
                ml_score = 50.0
                if iv_z > 0.5:
                    ml_score += 15  # elevated IV is good for sellers
                if iv_z > 1.0:
                    ml_score += 10
                if direction_bullish:
                    ml_score += 15  # bullish trend good for put sellers
                if hv_ratio < 1.2:
                    ml_score += 10  # non-elevated regime

                # Position size multiplier based on regime
                if hv_ratio > 1.5:
                    pos_mult = 0.5  # crisis — half size
                elif hv_ratio > 1.2:
                    pos_mult = 0.75  # elevated — reduced
                else:
                    pos_mult = 1.0  # normal

                all_trades.append({
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 2),
                    "strike": strike,
                    "premium": round(premium, 4),
                    "exit_price": round(exit_price, 2),
                    "pnl": round(pnl, 4),
                    "win": win,
                    "iv_zscore": round(iv_z, 2),
                    "direction_bullish": direction_bullish,
                    "hv_ratio": round(hv_ratio, 2),
                    "ml_score": round(ml_score, 1),
                    "pos_mult": pos_mult,
                })
        except Exception:
            continue

    if not all_trades:
        return {
            "period": period,
            "tickers": tickers,
            "total_trading_days": 0,
            "baseline": _empty_strategy(),
            "with_iv_reversion": _empty_strategy(),
            "with_regime_filter": _empty_strategy(),
            "with_direction_filter": _empty_strategy(),
            "with_ml_score": _empty_strategy(),
            "combined_all": _empty_strategy(),
            "detailed_results": [],
        }

    trades_df = pd.DataFrame(all_trades)

    # --- Baseline: all trades, no filter ---
    baseline = _calc_strategy_stats(trades_df)

    # --- With IV reversion filter: skip when IV z-score < -0.5 (IV too low) ---
    iv_filtered = trades_df[trades_df["iv_zscore"] >= -0.5].copy()
    with_iv = _calc_strategy_stats(iv_filtered)
    with_iv["improvement"] = _compare_to_baseline(baseline, with_iv)

    # --- With regime filter: adjust P&L by position size multiplier ---
    regime_df = trades_df.copy()
    regime_df["pnl"] = regime_df["pnl"] * regime_df["pos_mult"]
    with_regime = _calc_strategy_stats(regime_df)
    with_regime["improvement"] = _compare_to_baseline(baseline, with_regime)

    # --- With direction filter: only sell puts when bullish ---
    dir_filtered = trades_df[trades_df["direction_bullish"]].copy()
    with_dir = _calc_strategy_stats(dir_filtered)
    with_dir["improvement"] = _compare_to_baseline(baseline, with_dir)

    # --- With ML score filter: only trade when score > 60 ---
    ml_filtered = trades_df[trades_df["ml_score"] > 60].copy()
    with_ml = _calc_strategy_stats(ml_filtered)
    with_ml["improvement"] = _compare_to_baseline(baseline, with_ml)

    # --- Combined: all filters ---
    combined = trades_df[
        (trades_df["iv_zscore"] >= -0.5)
        & (trades_df["direction_bullish"])
        & (trades_df["ml_score"] > 60)
    ].copy()
    combined["pnl"] = combined["pnl"] * combined["pos_mult"]
    combined_stats = _calc_strategy_stats(combined)
    combined_stats["improvement"] = _compare_to_baseline(baseline, combined_stats)

    return {
        "period": period,
        "tickers": tickers,
        "total_trading_days": len(trades_df),
        "baseline": baseline,
        "with_iv_reversion": with_iv,
        "with_regime_filter": with_regime,
        "with_direction_filter": with_dir,
        "with_ml_score": with_ml,
        "combined_all": combined_stats,
        "detailed_results": all_trades,
    }


def _empty_strategy() -> dict:
    """Return an empty strategy result dict."""
    return {
        "trades": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "sharpe": 0.0,
    }


def _calc_strategy_stats(df: pd.DataFrame) -> dict:
    """Calculate strategy statistics from a DataFrame of trades."""
    if df.empty:
        return _empty_strategy()

    trades = len(df)
    wins = int(df["win"].sum())
    win_rate = wins / trades * 100.0
    total_pnl = float(df["pnl"].sum())

    # Sharpe ratio (annualized, assuming ~252 trading days / 7 = ~36 trade periods)
    pnl_series = df["pnl"].values
    if len(pnl_series) > 1 and np.std(pnl_series) > 0:
        sharpe = float(np.mean(pnl_series) / np.std(pnl_series) * np.sqrt(36))
    else:
        sharpe = 0.0

    return {
        "trades": trades,
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "sharpe": round(sharpe, 2),
    }


def _compare_to_baseline(baseline: dict, strategy: dict) -> str:
    """Generate a comparison string vs baseline."""
    parts = []

    # Win rate comparison
    wr_diff = strategy["win_rate"] - baseline["win_rate"]
    if wr_diff != 0:
        parts.append(f"Win rate {'+'if wr_diff > 0 else ''}{wr_diff:.1f}%")

    # P&L comparison
    if baseline["total_pnl"] != 0:
        pnl_change = (
            (strategy["total_pnl"] - baseline["total_pnl"])
            / abs(baseline["total_pnl"]) * 100
        )
        parts.append(f"P&L {'+'if pnl_change > 0 else ''}{pnl_change:.1f}%")
    else:
        pnl_diff = strategy["total_pnl"]
        parts.append(f"P&L {'+'if pnl_diff > 0 else ''}{pnl_diff:.2f}")

    # Sharpe comparison
    sharpe_diff = strategy["sharpe"] - baseline["sharpe"]
    parts.append(f"Sharpe {'+'if sharpe_diff > 0 else ''}{sharpe_diff:.2f}")

    # Trade count reduction
    if baseline["trades"] > 0:
        trade_pct = strategy["trades"] / baseline["trades"] * 100
        parts.append(f"Trades: {strategy['trades']}/{baseline['trades']} ({trade_pct:.0f}%)")

    return ", ".join(parts)


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    import json

    print("Running full backtest... (this may take 1-2 minutes)")
    results = run_full_backtest(["TSLA", "AMZN", "NVDA"], "6mo")

    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    for strategy_name in [
        "baseline", "with_iv_reversion", "with_regime_filter",
        "with_direction_filter", "with_ml_score", "combined_all",
    ]:
        s = results[strategy_name]
        print(f"\n{strategy_name}:")
        print(
            f"  Trades: {s['trades']}, Win Rate: {s['win_rate']:.1f}%, "
            f"P&L: ${s['total_pnl']:.2f}, Sharpe: {s['sharpe']:.2f}"
        )
        if "improvement" in s:
            print(f"  vs Baseline: {s['improvement']}")

    # Save results
    output = Path(__file__).parent / "backtest_results.json"
    # Convert to serializable format
    serializable = {k: v for k, v in results.items() if k != "detailed_results"}
    output.write_text(json.dumps(serializable, indent=2))
    print(f"\nResults saved to {output}")
