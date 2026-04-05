"""
Optimal Timing Strategy Module
Analyzes historical intraday and weekly patterns to find the best time to trade options.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


# ============================================================
# 1. Intraday Timing Analysis
# ============================================================
def analyze_intraday_patterns(symbol: str, lookback_days: int = 30) -> dict | None:
    """Analyze which time of day options premiums are cheapest/most expensive.

    Uses 30-minute intraday bars to determine when volatility (and thus IV)
    is highest or lowest during the trading day.

    Key findings from research:
    - First 30 min after open: highest volatility, widest spreads, worst for buyers
    - 10:00-11:00 AM ET: volatility settles, IV often drops -> good for sellers
    - 2:00-3:00 PM ET: "power hour" before close, IV can spike
    - Last 15 min: rapid theta decay, good for closing positions

    Returns dict with intraday timing data, or None on failure.
    """
    try:
        # yfinance 30m interval supports max ~60 days lookback
        period = f"{min(lookback_days, 59)}d"
        df = yf.download(symbol, period=period, interval="30m", progress=False)

        if df.empty or len(df) < 20:
            return None

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Calculate per-bar range as pct of close: (High - Low) / Close
        df["range_pct"] = (df["High"] - df["Low"]) / df["Close"] * 100

        # Extract hour:minute label from index (ET timezone assumed by yfinance)
        df["time_label"] = df.index.strftime("%H:%M")

        # Group by time-of-day and compute average range
        hourly = df.groupby("time_label").agg(
            avg_range_pct=("range_pct", "mean"),
            avg_volume=("Volume", "mean"),
            count=("range_pct", "count"),
        ).reset_index()

        # Filter to regular trading hours only (09:30 - 16:00 ET)
        trading_hours = hourly[
            (hourly["time_label"] >= "09:30") & (hourly["time_label"] < "16:00")
        ].copy()

        if trading_hours.empty:
            return None

        trading_hours = trading_hours.sort_values("time_label")

        # Highest vol time -> best to sell (premium is richest)
        best_sell_row = trading_hours.loc[trading_hours["avg_range_pct"].idxmax()]
        # Lowest vol time -> best to buy (premium is cheapest)
        best_buy_row = trading_hours.loc[trading_hours["avg_range_pct"].idxmin()]
        # Worst sell time = lowest vol (least premium)
        worst_sell_row = best_buy_row

        # Build 30-min window labels
        def _window(t: str) -> str:
            h, m = int(t[:2]), int(t[3:])
            end_m = m + 30
            end_h = h
            if end_m >= 60:
                end_m -= 60
                end_h += 1
            return f"{t}-{end_h:02d}:{end_m:02d} ET"

        # Build volatility-by-hour list
        volatility_by_hour = [
            {"hour": row["time_label"], "avg_move_pct": round(row["avg_range_pct"], 3)}
            for _, row in trading_hours.iterrows()
        ]

        # Use avg_range_pct as proxy for IV pattern
        intraday_iv_pattern = [
            {"hour": row["time_label"], "avg_iv_pct": round(row["avg_range_pct"] * 100, 1)}
            for _, row in trading_hours.iterrows()
        ]

        # Confidence based on data quantity
        total_bars = int(trading_hours["count"].sum())
        confidence = min(1.0, total_bars / 500)

        best_sell_time = _window(str(best_sell_row["time_label"]))
        best_buy_time = _window(str(best_buy_row["time_label"]))
        worst_sell_time = _window(str(worst_sell_row["time_label"]))

        recommendation = (
            f"Sell options near {best_sell_time} when intraday volatility peaks "
            f"(avg range {best_sell_row['avg_range_pct']:.2f}%). "
            f"Buy options near {best_buy_time} when volatility is lowest "
            f"(avg range {best_buy_row['avg_range_pct']:.2f}%)."
        )

        return {
            "symbol": symbol,
            "best_time_to_sell": best_sell_time,
            "worst_time_to_sell": worst_sell_time,
            "best_time_to_buy": best_buy_time,
            "intraday_iv_pattern": intraday_iv_pattern,
            "volatility_by_hour": volatility_by_hour,
            "recommendation": recommendation,
            "confidence": round(confidence, 2),
        }

    except Exception as e:
        print(f"  [timing] Intraday analysis failed for {symbol}: {e}")
        return None


# ============================================================
# 2. Day of Week Analysis
# ============================================================
def analyze_weekly_patterns(symbol: str, lookback_weeks: int = 52) -> dict | None:
    """Analyze which day of the week is best for options trading.

    Key research findings:
    - Monday: often gap up/down from weekend news, IV elevated
    - Tuesday: typically lowest IV of the week
    - Wednesday: FOMC decisions (8x per year) can spike IV
    - Thursday: common weekly expiry day, theta accelerates
    - Friday: weekly options expire, max theta decay

    Returns dict with weekly pattern data, or None on failure.
    """
    try:
        period = f"{lookback_weeks * 7}d"
        df = yf.download(symbol, period=period, interval="1d", progress=False)

        if df.empty or len(df) < 30:
            return None

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Calculate daily metrics
        df["daily_range"] = (df["High"] - df["Low"]) / df["Close"] * 100
        df["daily_return"] = df["Close"].pct_change() * 100
        df["day_of_week"] = df.index.dayofweek  # 0=Monday ... 4=Friday

        # Drop NaN rows
        df = df.dropna(subset=["daily_return"])

        day_names = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday"}

        daily_stats = []
        for dow in range(5):
            subset = df[df["day_of_week"] == dow]
            if subset.empty:
                continue

            avg_return = float(subset["daily_return"].mean())
            avg_range = float(subset["daily_range"].mean())
            avg_volume = float(subset["Volume"].mean())
            # Close-to-close volatility (std of daily returns, annualized)
            cc_vol = float(subset["daily_return"].std()) * np.sqrt(252)

            daily_stats.append({
                "day": day_names[dow],
                "day_of_week": dow,
                "avg_return": round(avg_return, 3),
                "avg_range": round(avg_range, 3),
                "avg_volume": round(avg_volume, 0),
                "annualized_vol": round(cc_vol, 2),
                "count": len(subset),
            })

        if not daily_stats:
            return None

        # Best day to sell = highest avg range (most premium)
        best_sell_day = max(daily_stats, key=lambda d: d["avg_range"])
        # Best day to buy = lowest avg range (cheapest premium)
        best_buy_day = min(daily_stats, key=lambda d: d["avg_range"])
        # Worst day = highest absolute avg return (most directional risk)
        worst_day = max(daily_stats, key=lambda d: abs(d["avg_return"]))

        # Theta decay proxy: approximation using day-of-week position
        # Later in the week = more theta decay for weeklies
        theta_decay_by_day = []
        for d in daily_stats:
            # Theta effect increases as week progresses (for weekly options)
            theta_factor = -0.1 * (1 + d["day_of_week"] * 0.5)
            theta_decay_by_day.append({
                "day": d["day"],
                "avg_theta_effect": round(theta_factor, 2),
            })

        recommendation = (
            f"Best day to sell options: {best_sell_day['day']} "
            f"(avg range {best_sell_day['avg_range']:.2f}%, highest IV proxy). "
            f"Best day to buy: {best_buy_day['day']} "
            f"(avg range {best_buy_day['avg_range']:.2f}%, lowest IV proxy)."
        )

        return {
            "symbol": symbol,
            "best_day_to_sell": best_sell_day["day"],
            "best_day_to_buy": best_buy_day["day"],
            "worst_day": worst_day["day"],
            "daily_stats": daily_stats,
            "theta_decay_by_day": theta_decay_by_day,
            "recommendation": recommendation,
        }

    except Exception as e:
        print(f"  [timing] Weekly analysis failed for {symbol}: {e}")
        return None


# ============================================================
# 3. Event-Based Timing
# ============================================================
def analyze_event_timing(symbol: str) -> dict | None:
    """Analyze how events (earnings, FOMC, CPI) affect optimal timing.

    Checks upcoming earnings dates from yfinance and macro events
    from smart_automation.MACRO_EVENTS_2026 to advise on pre/post-event
    strategies.

    Returns dict with event-based timing data, or None on failure.
    """
    try:
        tk = yf.Ticker(symbol)
        today = datetime.now().date()

        # --- Next earnings date ---
        next_earnings = None
        try:
            cal = tk.calendar
            if cal is not None and not cal.empty:
                if hasattr(cal, "columns") and len(cal.columns) > 0:
                    earn_date = pd.Timestamp(cal.columns[0])
                    next_earnings = earn_date.to_pydatetime().date()
        except Exception:
            pass

        # --- Macro events from smart_automation ---
        macro_events = []
        try:
            from smart_automation import MACRO_EVENTS_2026
            cutoff = today + timedelta(days=30)
            for evt in MACRO_EVENTS_2026:
                evt_date = datetime.strptime(evt["date"], "%Y-%m-%d").date()
                if today <= evt_date <= cutoff:
                    days_until = (evt_date - today).days
                    macro_events.append({
                        "type": evt["event"],
                        "date": evt["date"],
                        "days_until": days_until,
                        "impact": evt["impact"],
                    })
            macro_events.sort(key=lambda e: e["days_until"])
        except Exception:
            pass

        # --- Determine next event (earnings or macro, whichever is sooner) ---
        next_event = None
        if next_earnings:
            days_to_earn = (next_earnings - today).days
            if days_to_earn >= 0:
                next_event = {
                    "type": "Earnings",
                    "date": next_earnings.strftime("%Y-%m-%d"),
                    "days_until": days_to_earn,
                    "expected_iv_impact": "IV typically rises 20-50% pre-earnings",
                }
        if macro_events:
            first_macro = macro_events[0]
            if next_event is None or first_macro["days_until"] < next_event["days_until"]:
                next_event = {
                    "type": first_macro["type"],
                    "date": first_macro["date"],
                    "days_until": first_macro["days_until"],
                    "expected_iv_impact": f"{first_macro['impact']} impact event",
                }

        # --- Historical earnings IV behavior (approximate) ---
        # Fetch 1 year of data to see volatility patterns
        historical_event_impacts = []
        try:
            hist = tk.history(period="1y")
            if not hist.empty and len(hist) > 60:
                # Flatten multi-level columns if present
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                daily_returns = hist["Close"].pct_change().dropna()
                vol_30d = daily_returns.rolling(30).std() * np.sqrt(252) * 100
                vol_30d = vol_30d.dropna()

                if len(vol_30d) > 0:
                    avg_vol = float(vol_30d.mean())
                    max_vol = float(vol_30d.max())
                    min_vol = float(vol_30d.min())
                    historical_event_impacts.append({
                        "metric": "30d rolling HV",
                        "avg": round(avg_vol, 1),
                        "max": round(max_vol, 1),
                        "min": round(min_vol, 1),
                    })
        except Exception:
            pass

        # --- Strategy recommendations ---
        pre_event_strategy = "No upcoming events detected"
        post_event_strategy = "Monitor for IV crush opportunities"
        current_recommendation = "NEUTRAL"

        if next_event:
            days = next_event["days_until"]
            evt_type = next_event["type"]

            if evt_type == "Earnings":
                if 5 <= days <= 14:
                    pre_event_strategy = (
                        f"Sell options 5-7 days before earnings to capture IV premium. "
                        f"IV crush after earnings typically drops IV by 30-60%."
                    )
                    current_recommendation = "SELL options to capture pre-earnings IV"
                elif days <= 4:
                    pre_event_strategy = (
                        f"Earnings in {days} days — IV is near peak. "
                        f"Consider selling straddles/strangles for IV crush."
                    )
                    current_recommendation = "SELL premium (IV crush imminent)"
                elif days <= 30:
                    pre_event_strategy = (
                        f"Earnings in {days} days — IV building slowly. "
                        f"Wait until 5-7 days before for optimal sell timing."
                    )
                    current_recommendation = f"WAIT until ~{days - 7} days from now"
                else:
                    pre_event_strategy = "Earnings too far out to affect current timing."

                post_event_strategy = (
                    "After earnings: if IV drops >30%, consider buying options "
                    "for directional plays at cheaper premiums."
                )
            else:
                # Macro event (FOMC, CPI, NFP)
                if days <= 3:
                    pre_event_strategy = (
                        f"{evt_type} in {days} days — expect elevated IV. "
                        f"Good time to sell premium ahead of the event."
                    )
                    current_recommendation = "SELL premium ahead of macro event"
                elif days <= 7:
                    pre_event_strategy = (
                        f"{evt_type} in {days} days — IV may start rising. "
                        f"Position early for premium selling."
                    )
                    current_recommendation = "POSITION for macro event premium"
                else:
                    pre_event_strategy = f"{evt_type} in {days} days — no immediate action needed."

        return {
            "symbol": symbol,
            "next_event": next_event,
            "pre_event_strategy": pre_event_strategy,
            "post_event_strategy": post_event_strategy,
            "historical_event_impacts": historical_event_impacts,
            "upcoming_macro_events": macro_events[:5],
            "current_recommendation": current_recommendation,
        }

    except Exception as e:
        print(f"  [timing] Event analysis failed for {symbol}: {e}")
        return None


# ============================================================
# 4. Comprehensive Timing Recommendation
# ============================================================
def get_timing_recommendation(symbol: str) -> dict | None:
    """Combine all timing analyses into a single actionable recommendation.

    Calls analyze_intraday_patterns, analyze_weekly_patterns, and
    analyze_event_timing, then synthesizes a combined score and action.

    Returns dict with overall recommendation, or None on failure.
    """
    try:
        intraday = analyze_intraday_patterns(symbol)
        weekly = analyze_weekly_patterns(symbol)
        event = analyze_event_timing(symbol)

        now = datetime.now()
        today_dow = now.strftime("%A")
        current_time = now.strftime("%H:%M")

        # --- Intraday component ---
        intraday_info = {"best_time": "N/A", "reason": "Insufficient intraday data"}
        if intraday:
            intraday_info = {
                "best_time": intraday["best_time_to_sell"],
                "worst_time": intraday["worst_time_to_sell"],
                "best_buy_time": intraday["best_time_to_buy"],
                "reason": intraday["recommendation"],
                "confidence": intraday["confidence"],
            }

        # --- Weekly component ---
        weekly_info = {"best_day": "N/A", "reason": "Insufficient weekly data"}
        if weekly:
            weekly_info = {
                "best_day": weekly["best_day_to_sell"],
                "best_buy_day": weekly["best_day_to_buy"],
                "worst_day": weekly["worst_day"],
                "reason": weekly["recommendation"],
                "daily_stats": weekly["daily_stats"],
            }

        # --- Event component ---
        event_info = {"next_event": "None detected", "strategy": "No event-specific action"}
        if event and event["next_event"]:
            evt = event["next_event"]
            event_info = {
                "next_event": f"{evt['type']} on {evt['date']} ({evt['days_until']}d away)",
                "strategy": event["pre_event_strategy"],
                "current_recommendation": event["current_recommendation"],
            }

        # --- Combined score (0-100) ---
        # Higher = more favorable to trade now
        score = 50.0  # base neutral

        # Intraday: +10 if within best sell window, -10 if within worst
        if intraday:
            best_hour = intraday["best_time_to_sell"].split("-")[0].strip()[:5]
            worst_hour = intraday["worst_time_to_sell"].split("-")[0].strip()[:5]
            if current_time >= best_hour and current_time < _add_30min(best_hour):
                score += 15
            elif current_time >= worst_hour and current_time < _add_30min(worst_hour):
                score -= 15

        # Weekly: +10 if today is best sell day, -10 if worst
        if weekly:
            if today_dow == weekly["best_day_to_sell"]:
                score += 12
            elif today_dow == weekly["worst_day"]:
                score -= 10
            if today_dow == weekly["best_day_to_buy"]:
                score -= 5  # slightly less favorable for selling

        # Event: boost if pre-event window, penalize if too close
        if event and event["next_event"]:
            days_to_event = event["next_event"]["days_until"]
            if 3 <= days_to_event <= 7:
                score += 15  # optimal pre-event sell window
            elif days_to_event <= 2:
                score -= 5  # too close, high gamma risk
            elif 7 < days_to_event <= 14:
                score += 5  # building IV, OK

        score = max(0.0, min(100.0, score))

        # --- Determine action ---
        action = "NEUTRAL"
        wait_until = None

        if score >= 70:
            action = "SELL_NOW"
        elif score >= 55:
            action = "SELL_NOW"
        elif score <= 30:
            action = "WAIT"
            # Suggest when to act
            if weekly:
                wait_until = f"{weekly['best_day_to_sell']}"
                if intraday:
                    best_t = intraday["best_time_to_sell"].split("-")[0].strip()
                    wait_until += f" {best_t}"
        elif score <= 45:
            action = "WAIT"
            if weekly:
                wait_until = weekly["best_day_to_sell"]

        # Override with BUY_NOW only if event timing says so
        if event and event.get("current_recommendation", "").startswith("WAIT"):
            action = "WAIT"
            wait_until = event["current_recommendation"].replace("WAIT until ", "")

        # --- Overall recommendation text ---
        parts = []
        if action == "SELL_NOW":
            parts.append(f"Conditions are favorable to sell {symbol} options now (score: {score:.0f}/100).")
        elif action == "WAIT":
            parts.append(f"Consider waiting for better timing (score: {score:.0f}/100).")
            if wait_until:
                parts.append(f"Suggested window: {wait_until}.")
        else:
            parts.append(f"Neutral conditions for {symbol} options (score: {score:.0f}/100).")

        if event and event["next_event"]:
            parts.append(
                f"Next event: {event['next_event']['type']} "
                f"in {event['next_event']['days_until']} days."
            )

        overall = " ".join(parts)

        return {
            "symbol": symbol,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_recommendation": overall,
            "intraday": intraday_info,
            "weekly": weekly_info,
            "event": event_info,
            "combined_score": round(score, 1),
            "action": action,
            "wait_until": wait_until,
        }

    except Exception as e:
        print(f"  [timing] Combined recommendation failed for {symbol}: {e}")
        return None


def _add_30min(time_str: str) -> str:
    """Add 30 minutes to a HH:MM time string."""
    try:
        h, m = int(time_str[:2]), int(time_str[3:])
        m += 30
        if m >= 60:
            m -= 60
            h += 1
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "16:00"


# ============================================================
# 5. Report Section Generator
# ============================================================
def generate_timing_section(tickers: list[str]) -> str:
    """Generate markdown section for the daily report.

    Produces a complete timing analysis section including:
    - Best time to trade today (intraday)
    - Weekly patterns
    - Upcoming event watch

    Args:
        tickers: List of stock symbols to analyze.

    Returns:
        Markdown-formatted string, or empty string on total failure.
    """
    try:
        now = datetime.now()
        today_dow = now.strftime("%A")

        recommendations = {}
        for sym in tickers:
            rec = get_timing_recommendation(sym)
            if rec:
                recommendations[sym] = rec

        if not recommendations:
            return ""

        lines = []
        lines.append("## ⏰ Optimal Timing Analysis")
        lines.append("")

        # --- Best Time to Trade Today ---
        lines.append("### Best Time to Trade Today")
        lines.append("")
        lines.append("| Ticker | Best Sell Time | Best Buy Time | Current Action |")
        lines.append("|--------|---------------|---------------|----------------|")

        for sym, rec in recommendations.items():
            best_sell = rec["intraday"].get("best_time", "N/A")
            best_buy = rec["intraday"].get("best_buy_time", "N/A")
            action = rec["action"]

            # Format action with wait info
            if action == "WAIT" and rec.get("wait_until"):
                action_str = f"WAIT until {rec['wait_until']}"
            elif action == "SELL_NOW":
                action_str = "SELL NOW"
            elif action == "BUY_NOW":
                action_str = "BUY NOW"
            else:
                action_str = "NEUTRAL"

            lines.append(f"| {sym} | {best_sell} | {best_buy} | {action_str} |")

        lines.append("")

        # --- Weekly Pattern ---
        lines.append("### Weekly Pattern")
        lines.append("")

        # Aggregate best days across tickers
        sell_days = {}
        buy_days = {}
        for sym, rec in recommendations.items():
            w = rec.get("weekly", {})
            sd = w.get("best_day")
            bd = w.get("best_buy_day")
            if sd:
                sell_days[sd] = sell_days.get(sd, 0) + 1
            if bd:
                buy_days[bd] = buy_days.get(bd, 0) + 1

        if sell_days:
            top_sell_day = max(sell_days, key=sell_days.get)
            lines.append(f"- **Best day to sell**: {top_sell_day} (most volatile, richest premiums)")
        if buy_days:
            top_buy_day = max(buy_days, key=buy_days.get)
            lines.append(f"- **Best day to buy**: {top_buy_day} (least volatile, cheapest premiums)")

        # Per-ticker weekly detail
        for sym, rec in recommendations.items():
            w = rec.get("weekly", {})
            stats = w.get("daily_stats", [])
            if stats:
                # Find today's stats
                today_stat = next((s for s in stats if s["day"] == today_dow), None)
                if today_stat:
                    lines.append(
                        f"- **{sym}** today ({today_dow}): "
                        f"avg range {today_stat['avg_range']:.2f}%, "
                        f"annualized vol {today_stat.get('annualized_vol', 0):.1f}%"
                    )

        lines.append(f"- **Today is {today_dow}**: ", )

        # Add day-specific note
        day_notes = {
            "Monday": "Weekend gap risk — IV typically elevated, good for selling premium",
            "Tuesday": "Typically lowest IV of the week — good for buying options",
            "Wednesday": "Watch for FOMC — can spike IV significantly",
            "Thursday": "Weekly expiry setup — theta accelerating for weekly options",
            "Friday": "Weekly options expire — maximum theta decay, last chance to close weeklies",
        }
        lines[-1] += day_notes.get(today_dow, "Standard trading day")

        lines.append("")

        # --- Event Watch ---
        lines.append("### Event Watch")
        lines.append("")

        has_events = False
        for sym, rec in recommendations.items():
            evt = rec.get("event", {})
            next_evt = evt.get("next_event", "None detected")
            strategy = evt.get("strategy", "")

            if next_evt and next_evt != "None detected":
                lines.append(f"- **{sym}**: {next_evt}")
                if strategy:
                    lines.append(f"  - Strategy: {strategy}")
                has_events = True

        if not has_events:
            lines.append("- No significant events in the next 30 days")

        lines.append("")

        # --- Score Summary ---
        lines.append("### Timing Scores")
        lines.append("")
        lines.append("| Ticker | Score | Action | Recommendation |")
        lines.append("|--------|-------|--------|----------------|")

        for sym, rec in recommendations.items():
            score = rec["combined_score"]
            action = rec["action"]
            overall = rec["overall_recommendation"]
            # Truncate long recommendations for the table
            if len(overall) > 80:
                overall = overall[:77] + "..."
            lines.append(f"| {sym} | {score:.0f}/100 | {action} | {overall} |")

        lines.append("")

        return "\n".join(lines)

    except Exception as e:
        print(f"  [timing] Section generation failed: {e}")
        return ""


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Optimal Timing Strategy — Standalone Test")
    print("=" * 60)

    test_tickers = ["TSLA", "AMZN", "NVDA"]

    for sym in test_tickers:
        print(f"\n--- {sym} ---")
        rec = get_timing_recommendation(sym)
        if rec:
            print(f"  Score: {rec['combined_score']}/100")
            print(f"  Action: {rec['action']}")
            print(f"  Recommendation: {rec['overall_recommendation']}")
            print(f"  Intraday best sell: {rec['intraday'].get('best_time', 'N/A')}")
            print(f"  Weekly best day: {rec['weekly'].get('best_day', 'N/A')}")
            print(f"  Event: {rec['event'].get('next_event', 'None')}")
        else:
            print("  No recommendation available.")

    print("\n" + "=" * 60)
    section = generate_timing_section(test_tickers)
    if section:
        print(section)
    else:
        print("No timing section generated.")
