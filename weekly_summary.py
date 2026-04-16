"""
Weekly Options Strategy Summary Report
Aggregates Mon-Fri trade journals + daily_summary.csv into:
  - reports/weekly_summary_YYYY-MM-DD.md  (human-readable markdown)
  - data/weekly_summary.json              (structured data for the app)

Usage:
    python weekly_summary.py [--date YYYY-MM-DD] [--tickers TSLA,AMZN,NVDA]

Runs automatically on Saturdays via GitHub Actions.
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

# ============================================================
# Paths
# ============================================================
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "dashboard"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ============================================================
# Helpers
# ============================================================

def _parse_pct(value: Any) -> float | None:
    """Convert '43.6%' or 43.6 to float 43.6. Returns None on failure."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        s = str(value).strip().replace("%", "")
        return float(s)
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> float | None:
    """Return float or None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _week_range(week_ending: date) -> tuple[date, date]:
    """Return (monday, friday) for the week ending on the given date."""
    # week_ending is Saturday; Monday is 5 days before
    friday = week_ending - timedelta(days=1)
    monday = friday - timedelta(days=4)
    return monday, friday


def _iso_week(d: date) -> str:
    """Return 'YYYY-WNN' ISO week string."""
    return f"{d.year}-W{d.isocalendar()[1]:02d}"


# ============================================================
# Step 1 – Load this week's trade journals
# ============================================================

def load_week_journals(monday: date, friday: date) -> pd.DataFrame:
    """Load all trade_journal_YYYY-MM-DD.csv files between monday and friday."""
    frames: list[pd.DataFrame] = []
    current = monday
    while current <= friday:
        path = REPORTS_DIR / f"trade_journal_{current.isoformat()}.csv"
        if path.exists():
            try:
                df = pd.read_csv(path)
                frames.append(df)
            except Exception as exc:
                print(f"  [warn] Could not read {path}: {exc}")
        current += timedelta(days=1)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    # Normalise column names (strip whitespace)
    combined.columns = [c.strip() for c in combined.columns]
    return combined


def load_daily_summary(monday: date, friday: date) -> pd.DataFrame:
    """Load daily_summary.csv and filter to this week's rows."""
    path = REPORTS_DIR / "daily_summary.csv"
    if not path.exists():
        print(f"  [warn] daily_summary.csv not found at {path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
        mask = (df["Date"] >= monday) & (df["Date"] <= friday)
        return df[mask].copy()
    except Exception as exc:
        print(f"  [warn] Could not read daily_summary.csv: {exc}")
        return pd.DataFrame()


# ============================================================
# Step 2 – Fetch current prices via yfinance
# ============================================================

def fetch_current_prices(tickers: list[str]) -> dict[str, float]:
    """Return {ticker: current_price} using yfinance."""
    prices: dict[str, float] = {}
    for symbol in tickers:
        try:
            tk = yf.Ticker(symbol)
            info = tk.info
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if price:
                prices[symbol] = float(price)
        except Exception as exc:
            print(f"  [warn] Could not fetch price for {symbol}: {exc}")
    return prices


def fetch_week_prices(tickers: list[str], monday: date, friday: date) -> dict[str, dict[str, float | None]]:
    """
    Return {ticker: {"start": monday_open, "end": friday_close}}
    using yfinance history. Falls back to None if data unavailable.
    """
    result: dict[str, dict[str, float | None]] = {}
    # Fetch a bit wider window to handle non-trading days
    start_str = (monday - timedelta(days=2)).isoformat()
    end_str = (friday + timedelta(days=2)).isoformat()

    for symbol in tickers:
        result[symbol] = {"start": None, "end": None}
        try:
            tk = yf.Ticker(symbol)
            hist = tk.history(start=start_str, end=end_str)
            if hist.empty:
                continue
            hist.index = pd.to_datetime(hist.index).date
            # Monday open: earliest trading day >= monday
            week_rows = hist[hist.index >= monday]
            if not week_rows.empty:
                result[symbol]["start"] = float(week_rows.iloc[0]["Open"])
            # Friday close: latest trading day <= friday
            week_rows_end = hist[hist.index <= friday]
            if not week_rows_end.empty:
                result[symbol]["end"] = float(week_rows_end.iloc[-1]["Close"])
        except Exception as exc:
            print(f"  [warn] Could not fetch week prices for {symbol}: {exc}")

    return result


# ============================================================
# Step 3 – Per-ticker aggregation
# ============================================================

def aggregate_ticker(
    symbol: str,
    journals: pd.DataFrame,
    daily_summary: pd.DataFrame,
    current_price: float | None,
    week_prices: dict[str, float | None],
) -> dict:
    """Compute all weekly metrics for a single ticker."""

    # --- Filter to this ticker ---
    tj = journals[journals["Symbol"] == symbol].copy() if not journals.empty else pd.DataFrame()
    ds = daily_summary[daily_summary["Symbol"] == symbol].copy() if not daily_summary.empty else pd.DataFrame()

    # --- Price change ---
    price_start = week_prices.get("start")
    price_end = week_prices.get("end")
    if price_start and price_end and price_start > 0:
        price_change_pct = round((price_end - price_start) / price_start * 100, 2)
    else:
        price_change_pct = None

    # --- IV trend from daily_summary ---
    iv_avg = iv_min = iv_max = None
    iv_trend = "unknown"
    if not ds.empty and "Avg IV" in ds.columns:
        iv_vals = ds["Avg IV"].apply(_parse_pct).dropna()
        if len(iv_vals) >= 1:
            iv_avg = round(float(iv_vals.mean()), 1)
            iv_min = round(float(iv_vals.min()), 1)
            iv_max = round(float(iv_vals.max()), 1)
        if len(iv_vals) >= 2:
            # Compare first half vs second half
            mid = len(iv_vals) // 2
            if iv_vals.iloc[-1] > iv_vals.iloc[0] * 1.02:
                iv_trend = "rising"
            elif iv_vals.iloc[-1] < iv_vals.iloc[0] * 0.98:
                iv_trend = "falling"
            else:
                iv_trend = "stable"

    # --- P/C ratio trend ---
    pc_avg = None
    if not ds.empty and "PC Ratio" in ds.columns:
        pc_vals = ds["PC Ratio"].apply(_safe_float).dropna()
        if len(pc_vals) >= 1:
            pc_avg = round(float(pc_vals.mean()), 2)

    # --- Recommendation counts ---
    total_recs = len(tj)
    sell_put_count = int((tj["Strategy"] == "Sell Put").sum()) if not tj.empty else 0
    sell_call_count = int((tj["Strategy"] == "Sell Call").sum()) if not tj.empty else 0

    # --- Best trade (highest CP Score) ---
    best_trade: dict | None = None
    if not tj.empty and "CP Score" in tj.columns:
        tj_scored = tj[tj["CP Score"].apply(_safe_float).notna()].copy()
        if not tj_scored.empty:
            tj_scored["_score"] = tj_scored["CP Score"].apply(_safe_float)
            best_row = tj_scored.loc[tj_scored["_score"].idxmax()]
            best_trade = {
                "strategy": str(best_row.get("Strategy", "")),
                "strike": _safe_float(best_row.get("Strike")),
                "cp_score": round(float(best_row["_score"]), 1),
                "annualized": str(best_row.get("Annualized Return", "")),
                "expiry": str(best_row.get("Expiry", "")),
            }

    # --- Accuracy evaluation ---
    # For each recommended trade, check if current price vs strike means the option expired worthless
    profitable = 0
    evaluated = 0
    if not tj.empty and current_price is not None:
        for _, row in tj.iterrows():
            strategy = str(row.get("Strategy", ""))
            strike = _safe_float(row.get("Strike"))
            if strike is None:
                continue
            evaluated += 1
            # Sell Put: profitable if current_price > strike (put expires worthless)
            # Sell Call: profitable if current_price < strike (call expires worthless)
            if strategy == "Sell Put" and current_price > strike:
                profitable += 1
            elif strategy == "Sell Call" and current_price < strike:
                profitable += 1

    accuracy_score = round(profitable / evaluated * 100, 1) if evaluated > 0 else None

    # --- Next-week outlook (simple scoring model) ---
    outlook = _compute_outlook(
        symbol=symbol,
        price_change_pct=price_change_pct,
        iv_trend=iv_trend,
        iv_avg=iv_avg,
        pc_avg=pc_avg,
        sell_put_ratio=sell_put_count / max(total_recs, 1),
    )

    return {
        "price_start": price_start,
        "price_end": price_end,
        "price_change_pct": price_change_pct,
        "iv_avg": iv_avg,
        "iv_min": iv_min,
        "iv_max": iv_max,
        "iv_trend": iv_trend,
        "pc_ratio_avg": pc_avg,
        "recommendations_count": total_recs,
        "sell_put_count": sell_put_count,
        "sell_call_count": sell_call_count,
        "best_trade": best_trade,
        "accuracy": {
            "total": evaluated,
            "profitable": profitable,
            "score": accuracy_score,
        },
        "next_week_outlook": outlook,
    }


def _compute_outlook(
    symbol: str,
    price_change_pct: float | None,
    iv_trend: str,
    iv_avg: float | None,
    pc_avg: float | None,
    sell_put_ratio: float,
) -> dict:
    """
    Simple bullish/neutral/bearish scoring per ticker.
    Score range: 1 (strong bear) to 10 (strong bull), 5 = neutral.
    """
    score = 5.0
    reasons: list[str] = []

    # Price momentum
    if price_change_pct is not None:
        if price_change_pct > 3:
            score += 1.5
            reasons.append(f"本週上漲 {price_change_pct:.1f}%，動能偏多")
        elif price_change_pct > 0:
            score += 0.5
            reasons.append(f"本週小幅上漲 {price_change_pct:.1f}%")
        elif price_change_pct < -3:
            score -= 1.5
            reasons.append(f"本週下跌 {price_change_pct:.1f}%，動能偏空")
        else:
            score -= 0.5
            reasons.append(f"本週小幅下跌 {price_change_pct:.1f}%")

    # IV trend (rising IV often signals fear/bearish, falling = complacency/bullish)
    if iv_trend == "rising":
        score -= 0.5
        reasons.append("IV 上升，市場不安情緒升溫")
    elif iv_trend == "falling":
        score += 0.5
        reasons.append("IV 下降，市場情緒趨穩")

    # P/C ratio (>1 = more puts = bearish sentiment; <0.7 = bullish)
    if pc_avg is not None:
        if pc_avg > 1.2:
            score -= 1.0
            reasons.append(f"P/C 比 {pc_avg:.2f} 偏高，市場偏向防禦")
        elif pc_avg > 1.0:
            score -= 0.5
            reasons.append(f"P/C 比 {pc_avg:.2f} 略高")
        elif pc_avg < 0.7:
            score += 0.5
            reasons.append(f"P/C 比 {pc_avg:.2f} 偏低，市場偏樂觀")

    # Sell Put dominance suggests analysts lean bullish
    if sell_put_ratio > 0.7:
        score += 0.3
        reasons.append("本週 Sell Put 建議為主，分析師偏多")
    elif sell_put_ratio < 0.3:
        score -= 0.3
        reasons.append("本週 Sell Call 建議為主，分析師偏空")

    # Clamp score to 1-10
    score = max(1.0, min(10.0, score))
    confidence = round(score, 1)

    if score >= 6.5:
        direction = "bullish"
        direction_zh = "偏多"
    elif score <= 3.5:
        direction = "bearish"
        direction_zh = "偏空"
    else:
        direction = "neutral"
        direction_zh = "中性"

    reasoning = "；".join(reasons) if reasons else "資料不足，維持中性"
    reasoning_full = f"{direction_zh}（信心 {confidence}/10）：{reasoning}"

    return {
        "direction": direction,
        "confidence": confidence,
        "reasoning": reasoning_full,
    }


# ============================================================
# Step 4 – Main aggregation entry point
# ============================================================

def generate_weekly_summary(
    tickers: list[str],
    week_ending_date: date,
) -> dict:
    """
    Main function: loads data, aggregates, returns the JSON-serialisable dict.
    Also writes reports/weekly_summary_YYYY-MM-DD.md and data/weekly_summary.json.
    """
    monday, friday = _week_range(week_ending_date)
    print(f"Weekly summary: {monday} – {friday} (week ending {week_ending_date})")

    # Load data
    print("Loading trade journals...")
    journals = load_week_journals(monday, friday)
    print(f"  Loaded {len(journals)} rows from trade journals")

    print("Loading daily summary...")
    daily_summary = load_daily_summary(monday, friday)
    print(f"  Loaded {len(daily_summary)} rows from daily_summary.csv")

    # Determine tickers from data if none provided
    if not tickers:
        if not journals.empty and "Symbol" in journals.columns:
            tickers = sorted(journals["Symbol"].unique().tolist())
        elif not daily_summary.empty and "Symbol" in daily_summary.columns:
            tickers = sorted(daily_summary["Symbol"].unique().tolist())
        else:
            tickers = ["TSLA", "AMZN", "NVDA"]
    print(f"Tickers: {tickers}")

    # Fetch prices
    print("Fetching current prices...")
    current_prices = fetch_current_prices(tickers)

    print("Fetching week open/close prices...")
    all_week_prices = fetch_week_prices(tickers, monday, friday)

    # Aggregate per ticker
    ticker_data: dict[str, dict] = {}
    for symbol in tickers:
        print(f"  Aggregating {symbol}...")
        ticker_data[symbol] = aggregate_ticker(
            symbol=symbol,
            journals=journals,
            daily_summary=daily_summary,
            current_price=current_prices.get(symbol),
            week_prices=all_week_prices.get(symbol, {}),
        )

    # Overall scores
    all_accuracy = [
        t["accuracy"]["score"]
        for t in ticker_data.values()
        if t["accuracy"]["score"] is not None
    ]
    overall_accuracy = round(sum(all_accuracy) / len(all_accuracy), 1) if all_accuracy else None

    confidence_scores = [t["next_week_outlook"]["confidence"] for t in ticker_data.values()]
    overall_score = round(sum(confidence_scores) / len(confidence_scores) * 10, 1) if confidence_scores else None

    result = {
        "week_ending": week_ending_date.isoformat(),
        "week_start": monday.isoformat(),
        "week_end": friday.isoformat(),
        "iso_week": _iso_week(week_ending_date),
        "tickers": ticker_data,
        "overall_score": overall_score,
        "overall_accuracy": overall_accuracy,
        "generated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # Write JSON
    json_path = DATA_DIR / "weekly_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"JSON written: {json_path}")

    # Write markdown
    md_path = REPORTS_DIR / f"weekly_summary_{week_ending_date.isoformat()}.md"
    _write_markdown(result, md_path, monday, friday)
    print(f"Markdown written: {md_path}")

    return result


# ============================================================
# Step 5 – Markdown report generation
# ============================================================

def _direction_badge(direction: str) -> str:
    mapping = {"bullish": "偏多", "bearish": "偏空", "neutral": "中性"}
    return mapping.get(direction, direction)


def _iv_trend_label(trend: str) -> str:
    mapping = {"rising": "上升", "falling": "下降", "stable": "穩定", "unknown": "未知"}
    return mapping.get(trend, trend)


def _write_markdown(data: dict, path: Path, monday: date, friday: date) -> None:
    iso_week = data["iso_week"]
    week_ending = data["week_ending"]
    tickers = data["tickers"]
    overall_accuracy = data.get("overall_accuracy")
    overall_score = data.get("overall_score")
    generated_at = data.get("generated_at", "")

    lines: list[str] = []

    lines += [
        f"# 選擇權週報 {iso_week}",
        "",
        f"> **分析期間**：{monday} ~ {friday}　｜　**報告日期**：{week_ending}",
        f"> **自動產生於**：{generated_at[:16].replace('T', ' ')} UTC",
        "",
        "---",
        "",
        "## 本週總覽",
        "",
    ]

    # Overall stats table
    lines += [
        "| 指標 | 數值 |",
        "|------|------|",
        f"| 分析標的 | {', '.join(tickers.keys())} |",
        f"| 整體準確率 | {f'{overall_accuracy:.1f}%' if overall_accuracy is not None else 'N/A'} |",
        f"| 整體展望信心分數 | {f'{overall_score:.1f}/100' if overall_score is not None else 'N/A'} |",
        "",
        "---",
        "",
    ]

    # Per-ticker sections
    for symbol, td in tickers.items():
        lines.append(f"## {symbol}")
        lines.append("")

        # Price table
        price_start = td.get("price_start")
        price_end = td.get("price_end")
        change_pct = td.get("price_change_pct")
        change_str = f"{change_pct:+.2f}%" if change_pct is not None else "N/A"
        change_arrow = "" if change_pct is None else ("▲" if change_pct >= 0 else "▼")

        lines += [
            "### 價格走勢",
            "",
            "| 項目 | 數值 |",
            "|------|------|",
            f"| 週初開盤 | {'${:.2f}'.format(price_start) if price_start else 'N/A'} |",
            f"| 週末收盤 | {'${:.2f}'.format(price_end) if price_end else 'N/A'} |",
            f"| 週漲跌幅 | {change_arrow} {change_str} |",
            "",
        ]

        # IV
        iv_avg = td.get("iv_avg")
        iv_min = td.get("iv_min")
        iv_max = td.get("iv_max")
        iv_trend = td.get("iv_trend", "unknown")
        lines += [
            "### 波動率（IV）",
            "",
            "| 項目 | 數值 |",
            "|------|------|",
            f"| 週平均 IV | {f'{iv_avg:.1f}%' if iv_avg is not None else 'N/A'} |",
            f"| IV 區間 | {f'{iv_min:.1f}% ~ {iv_max:.1f}%' if iv_min is not None else 'N/A'} |",
            f"| IV 趨勢 | {_iv_trend_label(iv_trend)} |",
        ]
        if td.get("pc_ratio_avg") is not None:
            lines.append(f"| P/C Ratio 週均 | {td['pc_ratio_avg']:.2f} |")
        lines.append("")

        # Recommendations
        total_recs = td.get("recommendations_count", 0)
        sell_put = td.get("sell_put_count", 0)
        sell_call = td.get("sell_call_count", 0)
        lines += [
            "### 本週建議統計",
            "",
            "| 項目 | 數值 |",
            "|------|------|",
            f"| 總建議數 | {total_recs} |",
            f"| Sell Put 建議 | {sell_put} |",
            f"| Sell Call 建議 | {sell_call} |",
            "",
        ]

        # Best trade
        best = td.get("best_trade")
        if best:
            lines += [
                "### 本週最佳交易",
                "",
                "| 項目 | 數值 |",
                "|------|------|",
                f"| 策略 | {best.get('strategy', 'N/A')} |",
                f"| 履約價 | {best.get('strike', 'N/A')} |",
                f"| CP Score | {best.get('cp_score', 'N/A')} |",
                f"| 年化報酬 | {best.get('annualized', 'N/A')} |",
                f"| 到期日 | {best.get('expiry', 'N/A')} |",
                "",
            ]

        # Accuracy
        acc = td.get("accuracy", {})
        acc_total = acc.get("total", 0)
        acc_profit = acc.get("profitable", 0)
        acc_score = acc.get("score")
        lines += [
            "### 建議準確率評估",
            "",
            f"基於當前價格對照履約價評估：共 {acc_total} 筆建議，"
            f"其中 {acc_profit} 筆對賣方有利。",
            "",
            f"**週準確率：{f'{acc_score:.1f}%' if acc_score is not None else 'N/A（資料不足）'}**",
            "",
        ]

        # Outlook
        outlook = td.get("next_week_outlook", {})
        direction = outlook.get("direction", "neutral")
        confidence = outlook.get("confidence", 5)
        reasoning = outlook.get("reasoning", "")
        lines += [
            "### 下週展望",
            "",
            f"**方向：{_direction_badge(direction)}** ｜ 信心分數：{confidence}/10",
            "",
            f"{reasoning}",
            "",
            "---",
            "",
        ]

    # Footer
    lines += [
        "## 免責聲明",
        "",
        "本報告由自動化程式產生，僅供參考，不構成投資建議。",
        "選擇權交易具有高度風險，請自行評估風險承受能力。",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================
# CLI Entry point
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly options summary report")
    parser.add_argument(
        "--date",
        default="",
        help="Week-ending date (Saturday) in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--tickers",
        default=os.environ.get("TICKERS", ""),
        help="Comma-separated tickers, e.g. TSLA,AMZN,NVDA",
    )
    args = parser.parse_args()

    # Resolve date
    if args.date:
        try:
            week_ending = date.fromisoformat(args.date)
        except ValueError:
            print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        week_ending = date.today()

    # Resolve tickers
    tickers: list[str] = []
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    result = generate_weekly_summary(tickers=tickers, week_ending_date=week_ending)

    # Print summary to stdout
    print("\n=== Weekly Summary ===")
    print(f"Week: {result['week_start']} ~ {result['week_end']}")
    print(f"Overall accuracy: {result.get('overall_accuracy')}%")
    print(f"Overall outlook score: {result.get('overall_score')}/100")
    for symbol, td in result["tickers"].items():
        outlook = td.get("next_week_outlook", {})
        print(
            f"  {symbol}: {_direction_badge(outlook.get('direction', 'neutral'))} "
            f"(confidence {outlook.get('confidence', 'N/A')}/10), "
            f"accuracy {td['accuracy'].get('score', 'N/A')}%"
        )


if __name__ == "__main__":
    main()
