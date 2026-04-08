"""
Daily Options Strategy Report Generator
Generates Sell Put / Sell Call analysis for configured stock tickers.
Output: reports/YYYY-MM-DD.md
"""

import math
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm

# ============================================================
# Configuration
# ============================================================
# Tickers: override via TICKERS env var (comma-separated) or default list
_tickers_env = os.environ.get("TICKERS", "").strip()
TICKERS = [t.strip().upper() for t in _tickers_env.split(",") if t.strip()] if _tickers_env else ["TSLA", "AMZN", "NVDA"]

OTM_PCTS = [5, 6, 7, 8, 9, 10]
NUM_EXPIRIES = 4
MIN_DTE = 5           # Minimum 5 days to expiry (skip 0-4 DTE)
MIN_PREMIUM = 1.00    # Minimum $1.00 bid to include in analysis
MAX_PREMIUM = 7.00    # Maximum $7.00 bid (filter out deep ITM)
RISK_FREE_RATE = 5.0  # annual %
HISTORY_DAYS = [1, 3, 5, 7]

# Report language: "zh" (繁體中文) or "en" (English)
REPORT_LANG = os.environ.get("REPORT_LANG", "zh")

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ============================================================
# Data fetching
# ============================================================
def fetch_ticker_data(symbol: str) -> dict:
    """Fetch price, options chain, and historical data for a ticker."""
    tk = yf.Ticker(symbol)

    # Current price
    info = tk.info
    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose", current_price)
    change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0

    # Historical prices for trend comparison
    hist = tk.history(period="10d")
    history_prices = {}
    if not hist.empty:
        for d in HISTORY_DAYS:
            idx = -1 - d
            if abs(idx) <= len(hist):
                history_prices[f"{d}d"] = float(hist["Close"].iloc[idx])
            else:
                history_prices[f"{d}d"] = None

    # Options chains for nearest N expiries
    try:
        all_expiries = tk.options
    except Exception:
        all_expiries = []

    # Filter expiries: skip those with fewer than MIN_DTE days
    from datetime import datetime as _dt
    _today = _dt.now()
    expiries = []
    for exp_str in all_expiries:
        try:
            exp_dt = _dt.strptime(exp_str, "%Y-%m-%d")
            dte = (exp_dt - _today).days
            if dte >= MIN_DTE:
                expiries.append(exp_str)
            if len(expiries) >= NUM_EXPIRIES:
                break
        except Exception:
            continue
    chains = {}
    for exp in expiries:
        try:
            chain = tk.option_chain(exp)
            chains[exp] = {"calls": chain.calls, "puts": chain.puts}
        except Exception:
            continue

    # --- IV Percentile Rank ---
    iv_percentile = None
    try:
        hist_1y = tk.history(period="1y")
        if not hist_1y.empty and len(hist_1y) > 30:
            daily_returns = hist_1y["Close"].pct_change().dropna()
            rolling_vol = daily_returns.rolling(window=30).std() * np.sqrt(252) * 100  # annualized %
            rolling_vol = rolling_vol.dropna()
            if len(rolling_vol) > 0:
                min_hv = float(rolling_vol.min())
                max_hv = float(rolling_vol.max())
                if max_hv > min_hv:
                    # current_avg_IV will be computed later; store hist vol stats for now
                    iv_percentile = {"min_hv": min_hv, "max_hv": max_hv}
    except Exception:
        pass

    # --- Earnings Calendar Auto-Detection ---
    next_earnings = None
    try:
        cal = tk.calendar
        if cal is not None and not cal.empty:
            # tk.calendar is a DataFrame; earnings date is in the columns or index
            # Common format: columns are dates, or there's an "Earnings Date" row
            if hasattr(cal, 'columns') and len(cal.columns) > 0:
                # Calendar columns are typically the next earnings date(s)
                earn_date = pd.Timestamp(cal.columns[0])
                next_earnings = earn_date.to_pydatetime()
    except Exception:
        pass

    # --- v1.2 Options Intelligence ---
    pc_ratio = None
    max_pain_data = None
    unusual = None
    exp_move = None
    try:
        from options_intelligence import put_call_ratio, max_pain, unusual_activity, expected_move
        pc_ratio = put_call_ratio(tk)
        max_pain_data = max_pain(tk)
        unusual = unusual_activity(tk)
        exp_move = expected_move(tk)
    except Exception:
        pass

    # --- GEX ---
    gex_data = None
    try:
        from options_intelligence import gamma_exposure
        gex_data = gamma_exposure(tk)
    except Exception:
        pass

    # --- v2.0 Multi-Strategy ---
    multi_strat = None
    try:
        from multi_strategy import iron_condor, vertical_spread, strangle_straddle, wheel_strategy, calendar_spread
        first_exp = expiries[0] if expiries else None
        if first_exp and first_exp in chains:
            puts_df = chains[first_exp]["puts"]
            calls_df = chains[first_exp]["calls"]
            days = max((datetime.strptime(first_exp, "%Y-%m-%d") - datetime.now()).days, 1)
            multi_strat = {
                "iron_condor": iron_condor(puts_df, calls_df, current_price, days),
                "bull_put": vertical_spread(puts_df, current_price, days, "bull_put"),
                "bear_call": vertical_spread(calls_df, current_price, days, "bear_call"),
                "strangle_straddle": strangle_straddle(puts_df, calls_df, current_price, days),
                "wheel": wheel_strategy(puts_df, current_price, days),
                "calendar": calendar_spread(tk, current_price),
            }
    except Exception:
        pass

    return {
        "symbol": symbol,
        "price": current_price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "history": history_prices,
        "expiries": expiries,
        "chains": chains,
        "iv_percentile_data": iv_percentile,
        "next_earnings": next_earnings,
        "pc_ratio": pc_ratio,
        "max_pain": max_pain_data,
        "unusual_activity": unusual,
        "expected_move": exp_move,
        "multi_strategy": multi_strat,
        "gex": gex_data,
    }


# ============================================================
# Greeks calculation
# ============================================================
def calc_greeks(
    spot: float,
    strike: float,
    days_to_exp: int,
    iv_pct: float,
    option_type: str = "call",
) -> dict:
    """Calculate Greeks using Black-Scholes (scipy)."""
    if days_to_exp <= 0 or iv_pct <= 0 or strike <= 0 or spot <= 0:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    try:
        T = days_to_exp / 365.0
        r = RISK_FREE_RATE / 100.0
        sigma = iv_pct / 100.0
        sqrt_T = math.sqrt(T)

        d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        gamma = round(norm.pdf(d1) / (spot * sigma * sqrt_T), 4)
        vega = round(spot * norm.pdf(d1) * sqrt_T / 100, 4)  # per 1% move

        if option_type == "put":
            delta = round(norm.cdf(d1) - 1, 4)
            theta = round((-spot * norm.pdf(d1) * sigma / (2 * sqrt_T)
                          + r * strike * math.exp(-r * T) * norm.cdf(-d2)) / 365, 4)
        else:
            delta = round(norm.cdf(d1), 4)
            theta = round((-spot * norm.pdf(d1) * sigma / (2 * sqrt_T)
                          - r * strike * math.exp(-r * T) * norm.cdf(d2)) / 365, 4)

        return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}
    except Exception:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}


# ============================================================
# Find closest strike to target OTM%
# ============================================================
def find_closest_strike(strikes: list, target: float) -> float:
    """Find the strike price closest to target value."""
    if not strikes:
        return 0
    return min(strikes, key=lambda s: abs(s - target))


# ============================================================
# CP score calculation
# ============================================================
def calc_cp_score(annualized_return: float, otm_pct: float, delta: float, theta: float, premium: float) -> float:
    """
    CP score formula:
    CP = annualized_return × 0.30
       + safety_margin_score × 0.25
       + (1 - |delta|) × 0.25
       + theta_efficiency × 0.20
    """
    # Normalize annualized return (cap at 200% for scoring)
    ret_score = min(annualized_return, 200) / 200 * 100

    # Safety margin: higher OTM% = safer
    safety_score = min(otm_pct, 10) / 10 * 100

    # Delta score: lower |delta| = lower assignment risk
    delta_score = (1 - min(abs(delta), 1)) * 100

    # Theta efficiency: higher |theta|/premium = better time decay capture
    if premium > 0:
        theta_eff = min(abs(theta) / premium, 1) * 100
    else:
        theta_eff = 0

    return round(ret_score * 0.30 + safety_score * 0.25 + delta_score * 0.25 + theta_eff * 0.20, 1)


# ============================================================
# Analyze one ticker
# ============================================================
def analyze_ticker(data: dict) -> dict:
    """Analyze Sell Put and Sell Call for a single ticker."""
    symbol = data["symbol"]
    price = data["price"]
    results = {"symbol": symbol, "price": price, "data": data, "expiries": []}

    for exp_date in data["expiries"]:
        if exp_date not in data["chains"]:
            continue

        chain = data["chains"][exp_date]
        exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
        days_to_exp = max((exp_dt - datetime.now()).days, 1)

        puts_df = chain["puts"]
        calls_df = chain["calls"]

        all_put_strikes = sorted(puts_df["strike"].tolist()) if not puts_df.empty else []
        all_call_strikes = sorted(calls_df["strike"].tolist()) if not calls_df.empty else []

        # --- Sell Put analysis (OTM 5%~10% below current price) ---
        sell_puts = []
        for pct in OTM_PCTS:
            target_strike = price * (1 - pct / 100)
            strike = find_closest_strike(all_put_strikes, target_strike)
            if strike == 0:
                continue

            row = puts_df[puts_df["strike"] == strike]
            if row.empty:
                continue
            row = row.iloc[0]

            bid = float(row.get("bid", 0) or 0)
            ask = float(row.get("ask", 0) or 0)
            iv = float(row.get("impliedVolatility", 0) or 0) * 100
            actual_otm = round((strike - price) / price * 100, 2)

            # Skip options with premium outside investable range
            if bid < MIN_PREMIUM or bid > MAX_PREMIUM:
                continue

            greeks = calc_greeks(price, strike, days_to_exp, iv, "put")
            annualized = (bid / strike * 365 / days_to_exp * 100) if strike > 0 and bid > 0 else 0
            cp = calc_cp_score(annualized, abs(actual_otm), greeks["delta"], greeks["theta"], bid)

            sell_puts.append({
                "otm_pct": actual_otm,
                "target_pct": -pct,
                "strike": strike,
                "bid": bid,
                "ask": ask,
                "iv": iv,
                "annualized": round(annualized, 1),
                "cp": cp,
                "days": days_to_exp,
                **greeks,
            })

        # --- Sell Call analysis (OTM 5%~10% above current price) ---
        sell_calls = []
        for pct in OTM_PCTS:
            target_strike = price * (1 + pct / 100)
            strike = find_closest_strike(all_call_strikes, target_strike)
            if strike == 0:
                continue

            row = calls_df[calls_df["strike"] == strike]
            if row.empty:
                continue
            row = row.iloc[0]

            bid = float(row.get("bid", 0) or 0)
            ask = float(row.get("ask", 0) or 0)
            iv = float(row.get("impliedVolatility", 0) or 0) * 100
            actual_otm = round((strike - price) / price * 100, 2)

            # Skip options with premium outside investable range
            if bid < MIN_PREMIUM or bid > MAX_PREMIUM:
                continue

            greeks = calc_greeks(price, strike, days_to_exp, iv, "call")
            annualized = (bid / strike * 365 / days_to_exp * 100) if strike > 0 and bid > 0 else 0
            cp = calc_cp_score(annualized, actual_otm, greeks["delta"], greeks["theta"], bid)

            sell_calls.append({
                "otm_pct": actual_otm,
                "target_pct": pct,
                "strike": strike,
                "bid": bid,
                "ask": ask,
                "iv": iv,
                "annualized": round(annualized, 1),
                "cp": cp,
                "days": days_to_exp,
                **greeks,
            })

        results["expiries"].append({
            "date": exp_date,
            "days": days_to_exp,
            "sell_puts": sell_puts,
            "sell_calls": sell_calls,
        })

    return results


# ============================================================
# Markdown report generation
# ============================================================
def fmt(val, prefix="", suffix="", decimals=2) -> str:
    """Format a numeric value for display."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    if isinstance(val, float):
        return f"{prefix}{val:.{decimals}f}{suffix}"
    return f"{prefix}{val}{suffix}"


def generate_options_table(entries: list, best_cp_strike: float) -> str:
    """Generate markdown table for Sell Put or Sell Call entries."""
    lines = []
    lines.append("| OTM% | Strike | 權利金(Bid) | 權利金(Ask) | Delta | Gamma | Theta | Vega | IV | 年化報酬率 | CP評分 | 推薦 |")
    lines.append("|------|--------|-------------|-------------|-------|-------|-------|------|----|-----------|--------|------|")

    for e in entries:
        star = "★" if e["strike"] == best_cp_strike else ""
        lines.append(
            f"| {e['otm_pct']:+.1f}% "
            f"| ${e['strike']:.2f} "
            f"| ${e['bid']:.2f} "
            f"| ${e['ask']:.2f} "
            f"| {e['delta']:.4f} "
            f"| {e['gamma']:.4f} "
            f"| {e['theta']:.4f} "
            f"| {e['vega']:.4f} "
            f"| {e['iv']:.1f}% "
            f"| {e['annualized']:.1f}% "
            f"| {e['cp']:.1f} "
            f"| {star} |"
        )
    return "\n".join(lines)


def generate_history_table(entries: list, data: dict, option_type: str) -> str:
    """Generate historical trend comparison for top CP entries."""
    if not entries:
        return "_無數據_"

    # Sort by CP and take top 2
    top = sorted(entries, key=lambda x: x["cp"], reverse=True)[:2]
    history = data["history"]

    lines = []
    lines.append("| Strike | 今日權利金 | 1d前股價 | 3d前股價 | 5d前股價 | 7d前股價 | 趨勢 | 現在適合賣？ |")
    lines.append("|--------|-----------|---------|---------|---------|---------|------|-------------|")

    for e in top:
        prices = []
        for d in HISTORY_DAYS:
            key = f"{d}d"
            p = history.get(key)
            prices.append(f"${p:.2f}" if p else "N/A")

        # Determine trend based on price movement relative to strike
        current = data["price"]
        p7d = history.get("7d")
        if p7d:
            if option_type == "put":
                # For sell put: price going up = safer = good to sell
                trend = "↑漲" if current > p7d else "↓跌"
                suitable = "✅ 適合" if current > p7d else "⚠️ 觀望"
            else:
                # For sell call: price going down = safer = good to sell
                trend = "↑漲" if current > p7d else "↓跌"
                suitable = "⚠️ 觀望" if current > p7d else "✅ 適合"
        else:
            trend = "—"
            suitable = "—"

        lines.append(
            f"| ${e['strike']:.2f} "
            f"| ${e['bid']:.2f} "
            f"| {prices[0]} "
            f"| {prices[1]} "
            f"| {prices[2]} "
            f"| {prices[3]} "
            f"| {trend} "
            f"| {suitable} |"
        )

    return "\n".join(lines)


def generate_ticker_report(result: dict) -> str:
    """Generate full markdown section for one ticker."""
    data = result["data"]
    symbol = result["symbol"]
    price = result["price"]
    change = data["change_pct"]

    # Collect average IV across all expiries
    all_ivs = []
    for exp in result["expiries"]:
        for e in exp["sell_puts"] + exp["sell_calls"]:
            if e["iv"] > 0:
                all_ivs.append(e["iv"])
    avg_iv = sum(all_ivs) / len(all_ivs) if all_ivs else 0

    if avg_iv > 60:
        iv_level = "偏高 🔴"
    elif avg_iv > 35:
        iv_level = "正常 🟡"
    else:
        iv_level = "偏低 🟢"

    # --- IV Percentile Rank ---
    iv_rank_str = ""
    try:
        iv_pct_data = data.get("iv_percentile_data")
        if iv_pct_data and avg_iv > 0:
            min_hv = iv_pct_data["min_hv"]
            max_hv = iv_pct_data["max_hv"]
            iv_pct_val = (avg_iv - min_hv) / (max_hv - min_hv) * 100
            iv_pct_val = max(0.0, min(100.0, iv_pct_val))
            if iv_pct_val < 25:
                iv_rank_label = "偏低 🟢"
            elif iv_pct_val <= 75:
                iv_rank_label = "正常 🟡"
            else:
                iv_rank_label = "偏高 🔴"
            iv_rank_str = f"IV Rank: {iv_pct_val:.0f}% ({iv_rank_label})"
    except Exception:
        pass

    lines = []
    lines.append(f"## {symbol}")
    lines.append("")
    lines.append("### 一、市場概況")
    lines.append("")
    lines.append(f"| 項目 | 數值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 現價 | **${price:.2f}** |")
    lines.append(f"| 昨日漲跌 | {change:+.2f}% |")
    lines.append(f"| 平均 IV | {avg_iv:.1f}% ({iv_level}) |")
    if iv_rank_str:
        lines.append(f"| IV Percentile | {iv_rank_str} |")
    lines.append("")

    # --- Earnings Warning Banner ---
    try:
        next_earnings = data.get("next_earnings")
        if next_earnings:
            days_until = (next_earnings - datetime.now()).days
            if 0 <= days_until <= 14:
                earn_date_str = next_earnings.strftime("%Y-%m-%d")
                lines.append(f"> ⚠️ **財報警告**：{symbol} 將於 {earn_date_str} 發布財報（剩餘 {days_until} 天）。IV 可能大幅波動，賣方策略需謹慎。")
                lines.append("")
    except Exception:
        pass

    # --- v1.2 Options Intelligence Section ---
    try:
        pc_ratio = data.get("pc_ratio")
        max_pain_data = data.get("max_pain")
        exp_move = data.get("expected_move")
        unusual = data.get("unusual_activity")

        has_intel = pc_ratio or max_pain_data or exp_move or unusual
        if has_intel:
            lines.append("### 選擇權情報")
            lines.append("")
            lines.append("| 指標 | 數值 |")
            lines.append("|------|------|")

            if pc_ratio:
                lines.append(f"| Put/Call Volume Ratio | {pc_ratio['volume_ratio']:.2f} ({pc_ratio['signal']}) |")
                lines.append(f"| Put/Call OI Ratio | {pc_ratio['oi_ratio']:.2f} |")

            if max_pain_data:
                lines.append(f"| Max Pain | ${max_pain_data['max_pain_price']:.2f} ({max_pain_data['direction']} {max_pain_data['distance_pct']:.1f}%) |")

            if exp_move:
                lines.append(f"| Expected Move | ±${exp_move['expected_move_dollar']:.2f} (±{exp_move['expected_move_pct']:.1f}%) |")
                lines.append(f"| Expected Range | ${exp_move['lower_bound']:.2f} - ${exp_move['upper_bound']:.2f} |")

            lines.append("")

            if unusual:
                lines.append("**異常選擇權活動**")
                lines.append("")
                lines.append("| Type | Strike | Volume | OI | Vol/OI | IV |")
                lines.append("|------|--------|--------|-----|--------|-----|")
                for u in unusual:
                    iv_str = f"{u['iv']:.1f}%" if u.get("iv") is not None else "N/A"
                    lines.append(
                        f"| {u['type']} "
                        f"| ${u['strike']:.2f} "
                        f"| {u['volume']:,} "
                        f"| {u['oi']:,} "
                        f"| {u['vol_oi_ratio']:.1f} "
                        f"| {iv_str} |"
                    )
                lines.append("")
    except Exception:
        pass

    # --- GEX Section ---
    try:
        gex_data = data.get("gex")
        if gex_data:
            total_gex = gex_data.get("total_gex", 0)
            gex_flip = gex_data.get("gex_flip_point")
            support = gex_data.get("key_support")
            resistance = gex_data.get("key_resistance")

            lines.append("**Gamma Exposure (GEX)**")
            lines.append("")
            lines.append("| 項目 | 數值 |")
            lines.append("|------|------|")
            lines.append(f"| Total GEX | {total_gex:,.0f} |")
            lines.append(f"| GEX Flip Point | {f'${gex_flip:.2f}' if gex_flip is not None else 'N/A'} |")
            lines.append(f"| Key Support (GEX) | {f'${support:.2f}' if support is not None else 'N/A'} |")
            lines.append(f"| Key Resistance (GEX) | {f'${resistance:.2f}' if resistance is not None else 'N/A'} |")
            lines.append("")
    except Exception:
        pass

    # History prices
    hist = data["history"]
    if hist:
        lines.append("**近期價格走勢**")
        lines.append("")
        cols = " | ".join([f"{d}d前: ${hist[f'{d}d']:.2f}" if hist.get(f"{d}d") else f"{d}d前: N/A" for d in HISTORY_DAYS])
        lines.append(f"| {cols} |")
        lines.append("")

    # Per-expiry tables
    lines.append("### 二、【核心表格】Sell Put vs Sell Call 權利金比較（5%~10% OTM）")
    lines.append("")

    all_puts = []
    all_calls = []

    for exp in result["expiries"]:
        lines.append(f"#### 到期日：{exp['date']}（剩餘 {exp['days']} 天）")
        lines.append("")

        # Best CP for this expiry
        best_put_strike = max(exp["sell_puts"], key=lambda x: x["cp"])["strike"] if exp["sell_puts"] else 0
        best_call_strike = max(exp["sell_calls"], key=lambda x: x["cp"])["strike"] if exp["sell_calls"] else 0

        lines.append("**Sell Put（現價下方 5%~10%）**")
        lines.append("")
        lines.append(generate_options_table(exp["sell_puts"], best_put_strike))
        lines.append("")

        lines.append("**Sell Call（現價上方 5%~10%）**")
        lines.append("")
        lines.append(generate_options_table(exp["sell_calls"], best_call_strike))
        lines.append("")

        all_puts.extend(exp["sell_puts"])
        all_calls.extend(exp["sell_calls"])

    # History comparison
    lines.append("### 三、歷史權利金趨勢比較")
    lines.append("")
    lines.append("**Sell Put 歷史趨勢**")
    lines.append("")
    lines.append(generate_history_table(all_puts, data, "put"))
    lines.append("")
    lines.append("**Sell Call 歷史趨勢**")
    lines.append("")
    lines.append(generate_history_table(all_calls, data, "call"))
    lines.append("")

    # Best strategy summary
    best_put = max(all_puts, key=lambda x: x["cp"]) if all_puts else None
    best_call = max(all_calls, key=lambda x: x["cp"]) if all_calls else None

    lines.append("### 四、最佳策略總結")
    lines.append("")
    if best_put:
        exp_date = [e["date"] for e in result["expiries"] for p in e["sell_puts"] if p["strike"] == best_put["strike"]]
        exp_str = exp_date[0] if exp_date else "N/A"
        lines.append(f"- **Sell Put 最佳**：Strike ${best_put['strike']:.2f}（{best_put['otm_pct']:+.1f}% OTM）| 到期 {exp_str} | 年化 {best_put['annualized']:.1f}% | CP {best_put['cp']:.1f}")
    if best_call:
        exp_date = [e["date"] for e in result["expiries"] for c in e["sell_calls"] if c["strike"] == best_call["strike"]]
        exp_str = exp_date[0] if exp_date else "N/A"
        lines.append(f"- **Sell Call 最佳**：Strike ${best_call['strike']:.2f}（{best_call['otm_pct']:+.1f}% OTM）| 到期 {exp_str} | 年化 {best_call['annualized']:.1f}% | CP {best_call['cp']:.1f}")

    if best_put and best_call:
        if best_put["cp"] > best_call["cp"]:
            lines.append(f"- **推薦**：Sell Put 較划算（CP {best_put['cp']:.1f} > {best_call['cp']:.1f}）")
        else:
            lines.append(f"- **推薦**：Sell Call 較划算（CP {best_call['cp']:.1f} > {best_put['cp']:.1f}）")

    # --- v1.2 Trade Quality Analysis ---
    try:
        from options_intelligence import probability_of_profit, spread_quality

        lines.append("")
        lines.append("### 五、交易品質分析")
        lines.append("")

        # POP for top 3 puts and calls
        top_puts = sorted(all_puts, key=lambda x: x["cp"], reverse=True)[:3]
        top_calls = sorted(all_calls, key=lambda x: x["cp"], reverse=True)[:3]

        if top_puts or top_calls:
            lines.append("**獲利機率 (POP)**")
            lines.append("")
            lines.append("| 策略 | Strike | OTM% | CP | POP |")
            lines.append("|------|--------|------|-----|-----|")

            for e in top_puts:
                try:
                    pop = probability_of_profit(e["strike"], price, e["days"], e["iv"], "put")
                    pop_str = f"{pop:.1f}%"
                except Exception:
                    pop_str = "N/A"
                lines.append(f"| Sell Put | ${e['strike']:.2f} | {e['otm_pct']:+.1f}% | {e['cp']:.1f} | {pop_str} |")

            for e in top_calls:
                try:
                    pop = probability_of_profit(e["strike"], price, e["days"], e["iv"], "call")
                    pop_str = f"{pop:.1f}%"
                except Exception:
                    pop_str = "N/A"
                lines.append(f"| Sell Call | ${e['strike']:.2f} | {e['otm_pct']:+.1f}% | {e['cp']:.1f} | {pop_str} |")

            lines.append("")

        # Spread quality for top 3 trades
        top_all = sorted(all_puts + all_calls, key=lambda x: x["cp"], reverse=True)[:3]
        if top_all:
            try:
                sq = spread_quality(top_all)
                if sq:
                    lines.append("**Bid-Ask Spread 品質**")
                    lines.append("")
                    lines.append("| Strike | Spread% | 品質 |")
                    lines.append("|--------|---------|------|")
                    for s in sq:
                        lines.append(f"| ${s['strike']:.2f} | {s['spread_pct']:.1f}% | {s['quality']} |")
                    lines.append("")
            except Exception:
                pass
    except Exception:
        pass

    # --- v2.0 Multi-Strategy Analysis ---
    try:
        ms = data.get("multi_strategy")
        if ms:
            lines.append("")
            lines.append("### 六、多腳策略分析")
            lines.append("")

            # Iron Condor
            ic = ms.get("iron_condor")
            if ic:
                lines.append("**Iron Condor（鐵兀鷹）**")
                lines.append("")
                lines.append("| 項目 | 數值 |")
                lines.append("|------|------|")
                lines.append(f"| Short Put | ${ic.get('short_put', 0):.2f} |")
                lines.append(f"| Long Put | ${ic.get('long_put', 0):.2f} |")
                lines.append(f"| Short Call | ${ic.get('short_call', 0):.2f} |")
                lines.append(f"| Long Call | ${ic.get('long_call', 0):.2f} |")
                lines.append(f"| Net Credit | ${ic.get('net_credit', 0):.2f} |")
                lines.append(f"| Max Profit | ${ic.get('max_profit', 0):.2f} |")
                lines.append(f"| Max Loss | ${ic.get('max_loss', 0):.2f} |")
                max_loss = ic.get('max_loss', 0)
                max_profit = ic.get('max_profit', 0)
                rr = f"1:{max_loss / max_profit:.1f}" if max_profit > 0 else "N/A"
                lines.append(f"| Risk/Reward | {rr} |")
                be_low = ic.get('breakeven_low', 0)
                be_high = ic.get('breakeven_high', 0)
                lines.append(f"| Breakeven | ${be_low:.2f} - ${be_high:.2f} |")
                pop_val = ic.get('pop', 0)
                lines.append(f"| POP | {pop_val:.1f}% |")
                lines.append("")

            # Vertical Spreads (Bull Put + Bear Call)
            bp = ms.get("bull_put")
            bc = ms.get("bear_call")
            if bp or bc:
                lines.append("**Vertical Spreads（垂直價差）**")
                lines.append("")
                lines.append("| 項目 | Bull Put Spread | Bear Call Spread |")
                lines.append("|------|----------------|-----------------|")

                def _vs(d, key, fmt_str="${:.2f}"):
                    if d and key in d:
                        return fmt_str.format(d[key])
                    return "N/A"

                lines.append(f"| Short Strike | {_vs(bp, 'short_strike')} | {_vs(bc, 'short_strike')} |")
                lines.append(f"| Long Strike | {_vs(bp, 'long_strike')} | {_vs(bc, 'long_strike')} |")
                lines.append(f"| Net Credit | {_vs(bp, 'net_credit')} | {_vs(bc, 'net_credit')} |")
                lines.append(f"| Max Profit | {_vs(bp, 'max_profit')} | {_vs(bc, 'max_profit')} |")
                lines.append(f"| Max Loss | {_vs(bp, 'max_loss')} | {_vs(bc, 'max_loss')} |")
                lines.append(f"| Breakeven | {_vs(bp, 'breakeven')} | {_vs(bc, 'breakeven')} |")
                lines.append(f"| POP | {_vs(bp, 'pop', '{:.1f}%')} | {_vs(bc, 'pop', '{:.1f}%')} |")
                lines.append("")

            # Strangle/Straddle
            ss = ms.get("strangle_straddle")
            if ss:
                lines.append("**Strangle / Straddle（勒式 / 跨式）**")
                lines.append("")
                lines.append("| 項目 | Straddle | Strangle |")
                lines.append("|------|----------|----------|")
                strad = ss.get("straddle", {})
                strang = ss.get("strangle", {})
                lines.append(f"| Put Strike | {_vs(strad, 'put_strike')} | {_vs(strang, 'put_strike')} |")
                lines.append(f"| Call Strike | {_vs(strad, 'call_strike')} | {_vs(strang, 'call_strike')} |")
                lines.append(f"| Total Credit | {_vs(strad, 'total_credit')} | {_vs(strang, 'total_credit')} |")
                lines.append(f"| Breakeven Low | {_vs(strad, 'breakeven_low')} | {_vs(strang, 'breakeven_low')} |")
                lines.append(f"| Breakeven High | {_vs(strad, 'breakeven_high')} | {_vs(strang, 'breakeven_high')} |")
                lines.append(f"| POP | {_vs(strad, 'pop', '{:.1f}%')} | {_vs(strang, 'pop', '{:.1f}%')} |")
                lines.append("")

            # Wheel Strategy
            wh = ms.get("wheel")
            if wh:
                lines.append("**Wheel Strategy（轉輪策略）進場分析**")
                lines.append("")
                lines.append("| 項目 | 數值 |")
                lines.append("|------|------|")
                lines.append(f"| Entry Put Strike | ${wh.get('strike', 0):.2f} |")
                lines.append(f"| Put Premium | ${wh.get('premium', 0):.2f} |")
                lines.append(f"| Cost Basis if Assigned | ${wh.get('cost_basis', 0):.2f} |")
                lines.append(f"| Annualized Yield | {wh.get('annualized_yield', 0):.1f}% |")
                lines.append(f"| Breakeven | ${wh.get('breakeven', 0):.2f} |")
                lines.append(f"| Days to Expiry | {wh.get('days', 0)} |")
                lines.append("")

            # Calendar Spread
            cal = ms.get("calendar")
            if cal and cal.get("opportunity"):
                lines.append("**Calendar Spread（日曆價差）**")
                lines.append("")
                lines.append("| 項目 | 數值 |")
                lines.append("|------|------|")
                lines.append(f"| Strike | ${cal.get('strike', 0):.2f} |")
                lines.append(f"| Front Month IV | {cal.get('front_iv', 0):.1f}% |")
                lines.append(f"| Back Month IV | {cal.get('back_iv', 0):.1f}% |")
                lines.append(f"| IV Difference | {cal.get('iv_diff', 0):.1f}% |")
                lines.append(f"| Net Debit | ${cal.get('net_debit', 0):.2f} |")
                lines.append("")

            # Position Sizing
            try:
                from multi_strategy import position_sizing
                # Use best put or call max_loss for sizing reference
                ref_max_loss = 0
                if ic and ic.get("max_loss", 0) > 0:
                    ref_max_loss = ic["max_loss"]
                elif bp and bp.get("max_loss", 0) > 0:
                    ref_max_loss = bp["max_loss"]
                if ref_max_loss > 0:
                    ps = position_sizing(price, 5000, ref_max_loss)
                    if ps:
                        lines.append("**Position Sizing（部位大小建議）**")
                        lines.append("")
                        lines.append("| 項目 | 數值 |")
                        lines.append("|------|------|")
                        lines.append(f"| Max Risk Budget | $5,000 |")
                        lines.append(f"| Strategy Max Loss/Contract | ${ref_max_loss:.2f} |")
                        lines.append(f"| Recommended Contracts | {ps.get('contracts', 0)} |")
                        lines.append(f"| Total Risk | ${ps.get('total_risk', 0):.2f} |")
                        lines.append(f"| Capital Required | ${ps.get('capital_required', 0):,.2f} |")
                        lines.append("")
            except Exception:
                pass
    except Exception:
        pass

    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def generate_final_summary(all_results: list) -> str:
    """Generate cross-ticker comparison and final recommendation."""
    lines = []
    lines.append("## 最終總結：三檔股票大比拼")
    lines.append("")

    # Collect best entries across all tickers
    all_best_puts = []
    all_best_calls = []

    for r in all_results:
        all_puts = [p for exp in r["expiries"] for p in exp["sell_puts"]]
        all_calls = [c for exp in r["expiries"] for c in exp["sell_calls"]]

        if all_puts:
            best = max(all_puts, key=lambda x: x["cp"])
            best["_symbol"] = r["symbol"]
            exp_date = [e["date"] for e in r["expiries"] for p in e["sell_puts"] if p["strike"] == best["strike"]]
            best["_exp"] = exp_date[0] if exp_date else "N/A"
            all_best_puts.append(best)

        if all_calls:
            best = max(all_calls, key=lambda x: x["cp"])
            best["_symbol"] = r["symbol"]
            exp_date = [e["date"] for e in r["expiries"] for c in e["sell_calls"] if c["strike"] == best["strike"]]
            best["_exp"] = exp_date[0] if exp_date else "N/A"
            all_best_calls.append(best)

    # Sell Put ranking
    all_best_puts.sort(key=lambda x: x["cp"], reverse=True)
    lines.append("### 🏆 今日最佳 Sell Put 標的")
    lines.append("")
    lines.append("| 排名 | 股票 | Strike | OTM% | 到期日 | 權利金 | 年化報酬率 | CP評分 |")
    lines.append("|------|------|--------|------|--------|--------|-----------|--------|")
    for i, e in enumerate(all_best_puts, 1):
        lines.append(
            f"| {i} | **{e['_symbol']}** | ${e['strike']:.2f} | {e['otm_pct']:+.1f}% "
            f"| {e['_exp']} | ${e['bid']:.2f} | {e['annualized']:.1f}% | **{e['cp']:.1f}** |"
        )
    lines.append("")

    # Sell Call ranking
    all_best_calls.sort(key=lambda x: x["cp"], reverse=True)
    lines.append("### 🏆 今日最佳 Sell Call 標的")
    lines.append("")
    lines.append("| 排名 | 股票 | Strike | OTM% | 到期日 | 權利金 | 年化報酬率 | CP評分 |")
    lines.append("|------|------|--------|------|--------|--------|-----------|--------|")
    for i, e in enumerate(all_best_calls, 1):
        lines.append(
            f"| {i} | **{e['_symbol']}** | ${e['strike']:.2f} | {e['otm_pct']:+.1f}% "
            f"| {e['_exp']} | ${e['bid']:.2f} | {e['annualized']:.1f}% | **{e['cp']:.1f}** |"
        )
    lines.append("")

    # Overall recommendation
    lines.append("### 📊 綜合分析")
    lines.append("")

    # Find highest IV ticker
    iv_data = []
    for r in all_results:
        ivs = [e["iv"] for exp in r["expiries"] for e in exp["sell_puts"] + exp["sell_calls"] if e["iv"] > 0]
        avg = sum(ivs) / len(ivs) if ivs else 0
        iv_data.append((r["symbol"], avg))
    iv_data.sort(key=lambda x: x[1], reverse=True)

    if iv_data:
        lines.append(f"- **IV 最高**：{iv_data[0][0]}（{iv_data[0][1]:.1f}%）— 權利金最肥美，適合賣方策略")
        lines.append(f"- **IV 最低**：{iv_data[-1][0]}（{iv_data[-1][1]:.1f}%）— 權利金較薄")

    # Best single trade
    all_entries = all_best_puts + all_best_calls
    if all_entries:
        top = max(all_entries, key=lambda x: x["cp"])
        trade_type = "Sell Put" if top in all_best_puts else "Sell Call"
        lines.append(f"- **如果只能選一筆交易**：**{top['_symbol']} {trade_type}** Strike ${top['strike']:.2f}（{top['otm_pct']:+.1f}% OTM）| 年化 {top['annualized']:.1f}% | CP {top['cp']:.1f}")

    lines.append("")

    # --- v1.2 Options Intelligence Overview ---
    try:
        intel_rows = []
        for r in all_results:
            d = r["data"]
            symbol = r["symbol"]
            pc = d.get("pc_ratio")
            mp = d.get("max_pain")
            em = d.get("expected_move")
            intel_rows.append({"symbol": symbol, "pc": pc, "mp": mp, "em": em})

        has_any_intel = any(row["pc"] or row["mp"] or row["em"] for row in intel_rows)
        if has_any_intel:
            lines.append("### 📡 選擇權情報總覽")
            lines.append("")

            # P/C Ratio comparison
            pc_rows = [row for row in intel_rows if row["pc"]]
            if pc_rows:
                lines.append("**Put/Call Ratio 比較**")
                lines.append("")
                lines.append("| 股票 | Volume Ratio | OI Ratio | 訊號 |")
                lines.append("|------|-------------|----------|------|")
                for row in pc_rows:
                    pc = row["pc"]
                    lines.append(f"| {row['symbol']} | {pc['volume_ratio']:.2f} | {pc['oi_ratio']:.2f} | {pc['signal']} |")
                lines.append("")

            # Max Pain comparison
            mp_rows = [row for row in intel_rows if row["mp"]]
            if mp_rows:
                lines.append("**Max Pain 比較**")
                lines.append("")
                lines.append("| 股票 | Max Pain | 現價 | 方向 | 距離 |")
                lines.append("|------|----------|------|------|------|")
                for row in mp_rows:
                    mp = row["mp"]
                    lines.append(f"| {row['symbol']} | ${mp['max_pain_price']:.2f} | ${mp['current_price']:.2f} | {mp['direction']} | {mp['distance_pct']:.1f}% |")
                lines.append("")

            # Expected Move comparison
            em_rows = [row for row in intel_rows if row["em"]]
            if em_rows:
                lines.append("**Expected Move 比較**")
                lines.append("")
                lines.append("| 股票 | Expected Move | 預期範圍 |")
                lines.append("|------|--------------|----------|")
                for row in em_rows:
                    em = row["em"]
                    lines.append(f"| {row['symbol']} | ±${em['expected_move_dollar']:.2f} (±{em['expected_move_pct']:.1f}%) | ${em['lower_bound']:.2f} - ${em['upper_bound']:.2f} |")
                lines.append("")
    except Exception:
        pass

    # --- v2.1 IV/HV Divergence ---
    try:
        from data_backtest import iv_hv_divergence
        lines.append("### 📊 IV vs HV 分析")
        lines.append("")
        lines.append("| 股票 | 當前 IV | HV 30d | IV/HV Ratio | 訊號 |")
        lines.append("|------|--------|--------|-------------|------|")
        for r in all_results:
            ivs = [e["iv"] for exp in r["expiries"] for e in exp["sell_puts"] + exp["sell_calls"] if e["iv"] > 0]
            avg_iv = sum(ivs) / len(ivs) if ivs else 0
            div = iv_hv_divergence(r["symbol"], avg_iv)
            if div:
                lines.append(f"| {r['symbol']} | {div['current_iv']:.1f}% | {div['hv_30d']:.1f}% | {div['iv_hv_ratio']:.2f} | {div['signal']} |")
        lines.append("")
    except Exception:
        pass

    # --- v2.1 Correlation Matrix ---
    try:
        from data_backtest import correlation_matrix
        symbols = [r["symbol"] for r in all_results]
        corr = correlation_matrix(symbols)
        if corr:
            lines.append("### 🔗 標的相關性矩陣")
            lines.append("")
            lines.append(f"**多元化評分**：{corr['diversification_score']:.2f}（越高越分散）")
            lines.append("")
            header = "| | " + " | ".join(symbols) + " |"
            sep = "|---|" + "|".join(["---"] * len(symbols)) + "|"
            lines.append(header)
            lines.append(sep)
            for s1 in symbols:
                row = f"| **{s1}** |"
                for s2 in symbols:
                    val = corr["matrix"].get(s1, {}).get(s2, 0)
                    row += f" {val:.2f} |"
                lines.append(row)
            if corr.get("high_corr_pairs"):
                lines.append("")
                pairs_str = ", ".join([f"{p[0]}/{p[1]}({p[2]:.2f})" for p in corr["high_corr_pairs"]])
                lines.append(f"⚠️ **高相關性**：{pairs_str}")
            lines.append("")
    except Exception:
        pass

    # --- v3.0 Macro Events ---
    try:
        from smart_automation import get_upcoming_events, get_event_impact_warning
        events = get_upcoming_events(7)
        if events:
            lines.append("### 📅 本週總經事件")
            lines.append("")
            lines.append("| 日期 | 事件 | 影響程度 |")
            lines.append("|------|------|----------|")
            for ev in events:
                lines.append(f"| {ev['date']} | {ev['event']} | {ev['impact']} |")
            lines.append("")
        warning = get_event_impact_warning(datetime.now().strftime("%Y-%m-%d"))
        if warning:
            lines.append(f"> {warning}")
            lines.append("")
    except Exception:
        pass

    # --- v3.0 Smart Alerts ---
    try:
        from smart_automation import check_alerts
        tickers_data = [{"symbol": r["symbol"], "data": r["data"], "expiries": r["expiries"]} for r in all_results]
        alerts = check_alerts(tickers_data)
        if alerts:
            lines.append("### 🚨 智慧警報")
            lines.append("")
            for a in alerts[:8]:
                icon = "🔴" if a["severity"] == "high" else "🟡" if a["severity"] == "medium" else "🟢"
                lines.append(f"- {icon} **{a['ticker']}** — {a['message']}")
            lines.append("")
    except Exception:
        pass

    # --- v3.1 Risk Summary ---
    try:
        from risk_management import calculate_var, scenario_analysis
        symbols = [r["symbol"] for r in all_results]
        var_result = calculate_var(symbols)
        if var_result:
            lines.append("### 🛡️ 風險評估")
            lines.append("")
            lines.append(f"- **1 日 VaR (95%)**：${var_result['var_1day']:,.0f}（基於 $100K 組合）")
            lines.append(f"- **1 週 VaR**：${var_result['var_1week']:,.0f}")
            lines.append(f"- **CVaR（條件風險）**：${var_result['cvar']:,.0f}")
            lines.append(f"- **最大單日損失（1年）**：{var_result['worst_day']:.1f}%")
            lines.append("")
    except Exception:
        pass

    lines.append("### ⚠️ 風險提示")
    lines.append("")
    lines.append("- 以上分析基於歷史數據和 Black-Scholes 模型，實際交易請考慮流動性和 bid-ask spread")
    lines.append("- 請注意近期是否有財報、Fed 會議、CPI 等重大事件")
    lines.append("- 高 IV 代表市場預期大波動，賣方策略雖然權利金高但風險也高")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================
def main():
    # Support date override via env var or CLI arg
    date_override = os.environ.get("REPORT_DATE", "").strip()
    if len(sys.argv) > 1 and sys.argv[1].strip():
        date_override = sys.argv[1].strip()
    today = date_override if date_override else datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{today}.md"

    print(f"=== Options Daily Report {today} ===")
    print(f"Tickers: {', '.join(TICKERS)}")
    print(f"Language: {REPORT_LANG}")
    if date_override:
        print(f"Date override: {date_override} (options data is current snapshot)")
    print()

    # Fetch and analyze all tickers
    all_results = []
    for symbol in TICKERS:
        print(f"Fetching {symbol}...")
        try:
            data = fetch_ticker_data(symbol)
            print(f"  Price: ${data['price']:.2f} ({data['change_pct']:+.2f}%)")
            print(f"  Expiries: {data['expiries']}")

            result = analyze_ticker(data)
            all_results.append(result)
            print(f"  Analysis complete.")
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    if not all_results:
        print("ERROR: No data fetched for any ticker.")
        sys.exit(1)

    # Build report
    print("\nGenerating report...")
    report_lines = []
    report_lines.append(f"# 📊 每日選擇權策略報告 — {today}")
    report_lines.append("")
    report_lines.append(f"**產生時間**：{datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    report_lines.append(f"**分析標的**：{', '.join(TICKERS)}")
    report_lines.append(f"**分析範圍**：Sell Put / Sell Call, OTM 5%~10%, DTE ≥ {MIN_DTE} 天, 權利金 ${MIN_PREMIUM:.2f}-${MAX_PREMIUM:.2f}")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    for result in all_results:
        report_lines.append(generate_ticker_report(result))

    report_lines.append(generate_final_summary(all_results))

    # Model verdict — comprehensive 9-model analysis
    try:
        from model_verdict import generate_model_verdict

        print("\nGenerating model verdict...")
        verdict_section = generate_model_verdict(TICKERS, all_results)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append(verdict_section)
        print("  Model verdict added.")
    except Exception as e:
        print(f"  Model verdict skipped: {e}")

    # Optimal timing analysis
    try:
        from timing_strategy import generate_timing_section

        print("\nGenerating timing analysis...")
        timing_section = generate_timing_section(TICKERS)
        if timing_section:
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")
            report_lines.append(timing_section)
            print("  Timing analysis added.")
    except Exception as e:
        print(f"  Timing analysis skipped: {e}")

    # OI distribution analysis
    try:
        from oi_distribution import generate_oi_section

        print("\nGenerating OI distribution analysis...")
        oi_section = generate_oi_section(TICKERS)
        if oi_section:
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")
            report_lines.append(oi_section)
            print("  OI distribution added.")
    except Exception as e:
        print(f"  OI distribution skipped: {e}")

    # AI market commentary (optional, requires GEMINI_API_KEY)
    try:
        from ai_analysis import generate_ai_commentary

        print("\nGenerating AI market commentary...")
        quant_report = "\n".join(report_lines)
        ai_commentary = generate_ai_commentary(quant_report, TICKERS, lang=REPORT_LANG)
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## 🤖 AI 市場解讀（Gemini）")
        report_lines.append("")
        report_lines.append(ai_commentary)
        report_lines.append("")
        report_lines.append("> *以上 AI 分析由 Gemini (Google) 自動產生，僅供參考，不構成投資建議。*")
        report_lines.append("")
        print("  AI commentary added.")
    except Exception as e:
        print(f"  AI commentary skipped: {e}")

    # Write report
    report_content = "\n".join(report_lines)
    report_path.write_text(report_content, encoding="utf-8")
    print(f"Report saved to {report_path}")

    # Update reports/README.md
    readme_path = REPORTS_DIR / "README.md"
    if readme_path.exists():
        existing = readme_path.read_text(encoding="utf-8")
    else:
        existing = "# 📊 報告索引\n\n| 日期 | 連結 |\n|------|------|\n"

    new_entry = f"| {today} | [{today} 每日選擇權策略報告]({today}.md) |"
    # Insert after table header
    lines = existing.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("|---"):
            insert_idx = i + 1
            break
    if insert_idx:
        lines.insert(insert_idx, new_entry)
    readme_path.write_text("\n".join(lines), encoding="utf-8")

    # Update root README.md
    root_readme = Path(__file__).parent / "README.md"
    if root_readme.exists():
        content = root_readme.read_text(encoding="utf-8")
        content = content.replace(
            "> 尚未產生報告",
            f"> 📅 最新報告：[{today}](reports/{today}.md)"
        )
        # Also update if there's already a latest report link
        import re
        content = re.sub(
            r"> 📅 最新報告：\[.*?\]\(reports/.*?\)",
            f"> 📅 最新報告：[{today}](reports/{today}.md)",
            content,
        )
        root_readme.write_text(content, encoding="utf-8")

    # Interactive HTML report (optional, requires plotly)
    try:
        from html_report import generate_html_report

        print("\nGenerating interactive HTML report...")
        html_path = generate_html_report(all_results, today, REPORTS_DIR)
        print(f"  HTML report saved to {html_path}")
    except Exception as e:
        print(f"  HTML report skipped: {e}")

    # Telegram notification (optional, requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
    try:
        from telegram_notify import send_telegram_summary

        report_url = f"https://github.com/laiyanlong/options-daily-report/blob/main/reports/{today}.md"
        print("\nSending Telegram notification...")
        send_telegram_summary(report_content, report_url, TICKERS)
    except Exception as e:
        print(f"  Telegram notification skipped: {e}")

    # v2.1: Save to database and export trade journal
    try:
        from data_backtest import save_trade_recommendations, export_trade_journal, export_daily_summary_csv

        print("\nSaving to historical database...")
        save_trade_recommendations(today, TICKERS, all_results)
        print("  Database updated.")

        print("Exporting trade journal...")
        journal_path = export_trade_journal(today, all_results, REPORTS_DIR)
        if journal_path:
            print(f"  Trade journal: {journal_path}")

        export_daily_summary_csv(today, all_results, REPORTS_DIR)
    except Exception as e:
        print(f"  Data export skipped: {e}")

    # Output summary for the agent
    print("\n=== SUMMARY ===")
    print(f"Report: {report_path}")
    print(f"GitHub URL: https://github.com/laiyanlong/options-daily-report/blob/main/reports/{today}.md")

    # Print the final summary to stdout for the agent to include in its response
    print("\n" + generate_final_summary(all_results))


if __name__ == "__main__":
    main()
