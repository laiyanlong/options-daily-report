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
NUM_EXPIRIES = 3
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

    expiries = list(all_expiries[:NUM_EXPIRIES])
    chains = {}
    for exp in expiries:
        try:
            chain = tk.option_chain(exp)
            chains[exp] = {"calls": chain.calls, "puts": chain.puts}
        except Exception:
            continue

    return {
        "symbol": symbol,
        "price": current_price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "history": history_prices,
        "expiries": expiries,
        "chains": chains,
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
    lines.append("")

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
    report_lines.append(f"**分析範圍**：Sell Put / Sell Call, OTM 5%~10%, 最近 {NUM_EXPIRIES} 個到期日")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    for result in all_results:
        report_lines.append(generate_ticker_report(result))

    report_lines.append(generate_final_summary(all_results))

    # AI market commentary (optional, requires ANTHROPIC_API_KEY)
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

    # Output summary for the agent
    print("\n=== SUMMARY ===")
    print(f"Report: {report_path}")
    print(f"GitHub URL: https://github.com/laiyanlong/options-daily-report/blob/main/reports/{today}.md")

    # Print the final summary to stdout for the agent to include in its response
    print("\n" + generate_final_summary(all_results))


if __name__ == "__main__":
    main()
