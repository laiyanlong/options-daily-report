"""
Smart Automation Module — v3.0
Alerts, macro calendar, watchlist, multi-timeframe, auto-roll suggestions.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf


# ============================================================
# 1. Smart Alerts Engine
# ============================================================

_DEFAULT_THRESHOLDS = {
    "iv_rank_high": 80,
    "iv_rank_low": 20,
    "cp_score_high": 75,
    "pc_ratio_bearish": 1.3,
    "earnings_days": 7,
    "expected_move_high": 5.0,
}


def check_alerts(tickers_data: list[dict], thresholds: dict = None) -> list[dict]:
    """Check for alert conditions across all tickers.

    Args:
        tickers_data: List of analyzed ticker dicts (output of analyze_ticker).
            Each dict should contain keys like "symbol", "price", "data" where
            "data" holds raw fetch results including "iv_percentile_data",
            "pc_ratio", "next_earnings", "expected_move", and "expiries"
            with nested CP scores.
        thresholds: Override default alert thresholds. Keys:
            iv_rank_high, iv_rank_low, cp_score_high,
            pc_ratio_bearish, earnings_days, expected_move_high.

    Returns:
        List of alert dicts: {"ticker": str, "alert_type": str,
        "severity": "high"|"medium"|"low", "message": str, "value": float}
    """
    try:
        th = {**_DEFAULT_THRESHOLDS, **(thresholds or {})}
        alerts: list[dict] = []

        for ticker_result in tickers_data:
            symbol = ticker_result.get("symbol", "UNKNOWN")
            data = ticker_result.get("data", {})

            # --- IV rank extremes ---
            iv_data = data.get("iv_percentile_data")
            if iv_data and isinstance(iv_data, dict):
                # Compute a simple IV rank from the stored min/max HV
                min_hv = iv_data.get("min_hv", 0)
                max_hv = iv_data.get("max_hv", 0)
                if max_hv > min_hv:
                    # Use midpoint of current ATM IV as proxy (from first expiry)
                    current_iv = _extract_avg_iv(ticker_result)
                    if current_iv is not None:
                        iv_rank = (current_iv - min_hv) / (max_hv - min_hv) * 100
                        if iv_rank >= th["iv_rank_high"]:
                            alerts.append({
                                "ticker": symbol,
                                "alert_type": "iv_rank_high",
                                "severity": "high",
                                "message": f"{symbol} IV Rank at {iv_rank:.0f}% — premium selling opportunity",
                                "value": round(iv_rank, 1),
                            })
                        elif iv_rank <= th["iv_rank_low"]:
                            alerts.append({
                                "ticker": symbol,
                                "alert_type": "iv_rank_low",
                                "severity": "medium",
                                "message": f"{symbol} IV Rank at {iv_rank:.0f}% — low premium, consider buying strategies",
                                "value": round(iv_rank, 1),
                            })

            # --- High CP score opportunities ---
            for expiry_info in ticker_result.get("expiries", []):
                for entry in expiry_info.get("sell_puts", []) + expiry_info.get("sell_calls", []):
                    if entry.get("cp", 0) >= th["cp_score_high"]:
                        alerts.append({
                            "ticker": symbol,
                            "alert_type": "cp_score_high",
                            "severity": "high",
                            "message": (
                                f"{symbol} strike ${entry['strike']:.2f} "
                                f"CP={entry['cp']:.1f} — top-tier opportunity"
                            ),
                            "value": entry["cp"],
                        })

            # --- Bearish P/C ratio ---
            pc = data.get("pc_ratio")
            if pc and isinstance(pc, dict):
                vol_ratio = pc.get("volume_ratio", 0)
                if isinstance(vol_ratio, (int, float)) and vol_ratio >= th["pc_ratio_bearish"]:
                    alerts.append({
                        "ticker": symbol,
                        "alert_type": "pc_ratio_bearish",
                        "severity": "medium",
                        "message": f"{symbol} P/C ratio {vol_ratio:.2f} — bearish sentiment detected",
                        "value": round(vol_ratio, 3),
                    })

            # --- Approaching earnings ---
            next_earn = data.get("next_earnings")
            if next_earn:
                if isinstance(next_earn, str):
                    next_earn = datetime.strptime(next_earn, "%Y-%m-%d")
                if isinstance(next_earn, datetime):
                    days_until = (next_earn - datetime.now()).days
                    if 0 <= days_until <= th["earnings_days"]:
                        alerts.append({
                            "ticker": symbol,
                            "alert_type": "earnings_approaching",
                            "severity": "high",
                            "message": (
                                f"{symbol} earnings in {days_until} day(s) — "
                                f"avoid naked positions or hedge"
                            ),
                            "value": float(days_until),
                        })

            # --- Large expected move ---
            exp_move = data.get("expected_move")
            if exp_move and isinstance(exp_move, dict):
                move_pct = exp_move.get("move_pct", 0)
                if isinstance(move_pct, (int, float)) and move_pct >= th["expected_move_high"]:
                    alerts.append({
                        "ticker": symbol,
                        "alert_type": "expected_move_high",
                        "severity": "medium",
                        "message": (
                            f"{symbol} expected move {move_pct:.1f}% — "
                            f"high volatility, widen strikes or reduce size"
                        ),
                        "value": round(move_pct, 1),
                    })

        return alerts
    except Exception:
        return []


def _extract_avg_iv(ticker_result: dict) -> float | None:
    """Extract average IV from the first expiry's option entries."""
    try:
        for expiry_info in ticker_result.get("expiries", []):
            entries = expiry_info.get("sell_puts", []) + expiry_info.get("sell_calls", [])
            ivs = [e["iv"] for e in entries if e.get("iv", 0) > 0]
            if ivs:
                return sum(ivs) / len(ivs)
        return None
    except Exception:
        return None


# ============================================================
# 2. Macro Event Calendar
# ============================================================

MACRO_EVENTS_2026 = [
    # FOMC Meetings
    {"date": "2026-01-29", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-03-19", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-05-06", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-06-17", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-07-29", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-09-16", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-10-28", "event": "FOMC Meeting", "impact": "High"},
    {"date": "2026-12-16", "event": "FOMC Meeting", "impact": "High"},
    # CPI Releases (monthly, ~10th-15th)
    {"date": "2026-01-14", "event": "CPI Release", "impact": "High"},
    {"date": "2026-02-12", "event": "CPI Release", "impact": "High"},
    {"date": "2026-03-11", "event": "CPI Release", "impact": "High"},
    {"date": "2026-04-10", "event": "CPI Release", "impact": "High"},
    {"date": "2026-05-13", "event": "CPI Release", "impact": "High"},
    {"date": "2026-06-11", "event": "CPI Release", "impact": "High"},
    # Non-Farm Payrolls (first Friday of each month)
    {"date": "2026-01-02", "event": "Non-Farm Payrolls", "impact": "High"},
    {"date": "2026-02-06", "event": "Non-Farm Payrolls", "impact": "High"},
    {"date": "2026-03-06", "event": "Non-Farm Payrolls", "impact": "High"},
    {"date": "2026-04-03", "event": "Non-Farm Payrolls", "impact": "High"},
    {"date": "2026-05-01", "event": "Non-Farm Payrolls", "impact": "High"},
    {"date": "2026-06-05", "event": "Non-Farm Payrolls", "impact": "High"},
    # Triple Witching (3rd Friday of Mar, Jun, Sep, Dec)
    {"date": "2026-03-20", "event": "Triple Witching", "impact": "Medium"},
    {"date": "2026-06-19", "event": "Triple Witching", "impact": "Medium"},
    {"date": "2026-09-18", "event": "Triple Witching", "impact": "Medium"},
    {"date": "2026-12-18", "event": "Triple Witching", "impact": "Medium"},
]


def get_upcoming_events(days_ahead: int = 7) -> list[dict]:
    """Get macro events within the next N days.

    Args:
        days_ahead: Number of days to look ahead (default 7).

    Returns:
        List of event dicts sorted by date, each containing
        "date", "event", "impact", and "days_until" (int).
    """
    try:
        today = datetime.now().date()
        cutoff = today + timedelta(days=days_ahead)
        upcoming: list[dict] = []

        for evt in MACRO_EVENTS_2026:
            evt_date = datetime.strptime(evt["date"], "%Y-%m-%d").date()
            if today <= evt_date <= cutoff:
                upcoming.append({
                    **evt,
                    "days_until": (evt_date - today).days,
                })

        return sorted(upcoming, key=lambda e: e["days_until"])
    except Exception:
        return []


def get_event_impact_warning(report_date: str) -> str | None:
    """Generate warning text if high-impact events are within 3 days.

    Args:
        report_date: Date string in "YYYY-MM-DD" format.

    Returns:
        Warning message string or None if no high-impact events are near.
    """
    try:
        base = datetime.strptime(report_date, "%Y-%m-%d").date()
        window = timedelta(days=3)
        warnings: list[str] = []

        for evt in MACRO_EVENTS_2026:
            if evt["impact"] != "High":
                continue
            evt_date = datetime.strptime(evt["date"], "%Y-%m-%d").date()
            diff = (evt_date - base).days
            if 0 <= diff <= window.days:
                label = "TODAY" if diff == 0 else f"in {diff}d"
                warnings.append(f"{evt['event']} ({label})")

        if warnings:
            header = "WARNING: High-impact macro events approaching"
            return f"{header} — {', '.join(warnings)}"
        return None
    except Exception:
        return None


# ============================================================
# 3. Watchlist Management
# ============================================================

WATCHLIST_PATH = Path(__file__).parent / "config" / "watchlists.json"


def _ensure_config_dir() -> None:
    """Create the config directory if it does not exist."""
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_all_watchlists() -> dict:
    """Load the entire watchlists JSON file."""
    try:
        if WATCHLIST_PATH.exists():
            return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        return {}
    except Exception:
        return {}


def _save_all_watchlists(data: dict) -> None:
    """Persist the full watchlists dict to disk."""
    _ensure_config_dir()
    WATCHLIST_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_watchlist(name: str = "default") -> list[str]:
    """Load a named watchlist.

    Args:
        name: Watchlist name (default "default").

    Returns:
        List of ticker symbols. Empty list if watchlist not found.
    """
    try:
        all_wl = _load_all_watchlists()
        entry = all_wl.get(name, {})
        tickers = entry.get("tickers", []) if isinstance(entry, dict) else []
        return [t.upper() for t in tickers]
    except Exception:
        return []


def save_watchlist(name: str, tickers: list[str], notes: str = "") -> None:
    """Save a named watchlist.

    Args:
        name: Watchlist name.
        tickers: List of ticker symbols.
        notes: Optional description / notes for the watchlist.
    """
    try:
        all_wl = _load_all_watchlists()
        all_wl[name] = {
            "tickers": [t.strip().upper() for t in tickers],
            "notes": notes,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_all_watchlists(all_wl)
    except Exception:
        pass


def list_watchlists() -> list[dict]:
    """List all saved watchlists.

    Returns:
        List of dicts: {"name": str, "tickers": list[str],
                        "notes": str, "updated": str}
    """
    try:
        all_wl = _load_all_watchlists()
        result: list[dict] = []
        for name, entry in all_wl.items():
            if isinstance(entry, dict):
                result.append({
                    "name": name,
                    "tickers": entry.get("tickers", []),
                    "notes": entry.get("notes", ""),
                    "updated": entry.get("updated", ""),
                })
        return result
    except Exception:
        return []


# ============================================================
# 4. Multi-Timeframe Analysis
# ============================================================

def multi_timeframe_view(tk, price: float) -> dict | None:
    """Analyze options across weekly, monthly, and quarterly expirations.

    Examines the IV term structure by comparing ATM implied volatility
    at different expiration horizons.

    Args:
        tk: yfinance Ticker object.
        price: Current underlying price.

    Returns:
        {"weekly": {"expiry": str, "atm_iv": float, "best_put_cp": float},
         "monthly": {"expiry": str, "atm_iv": float, "best_put_cp": float},
         "quarterly": {"expiry": str, "atm_iv": float, "best_put_cp": float},
         "term_structure": "contango"|"backwardation"|"flat",
         "recommendation": str}
        or None on failure.
    """
    try:
        all_expiries = tk.options
        if not all_expiries:
            return None

        today = datetime.now()
        buckets = {
            "weekly": {"min_days": 0, "max_days": 10, "expiry": None},
            "monthly": {"min_days": 20, "max_days": 45, "expiry": None},
            "quarterly": {"min_days": 75, "max_days": 120, "expiry": None},
        }

        # Assign each expiry to the best-matching bucket
        for exp_str in all_expiries:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
            dte = (exp_date - today).days
            for bname, binfo in buckets.items():
                if binfo["min_days"] <= dte <= binfo["max_days"]:
                    # Pick the closest to midpoint of the range
                    mid = (binfo["min_days"] + binfo["max_days"]) / 2
                    if binfo["expiry"] is None:
                        binfo["expiry"] = exp_str
                        binfo["dte"] = dte
                    elif abs(dte - mid) < abs(binfo["dte"] - mid):
                        binfo["expiry"] = exp_str
                        binfo["dte"] = dte

        result = {}
        iv_values: list[tuple[int, float]] = []  # (dte, iv) for term structure

        for bname, binfo in buckets.items():
            exp_str = binfo.get("expiry")
            if not exp_str:
                result[bname] = None
                continue

            chain = tk.option_chain(exp_str)
            puts = chain.puts

            # ATM IV: closest strike to current price
            if puts.empty:
                result[bname] = None
                continue

            atm_idx = (puts["strike"] - price).abs().idxmin()
            atm_row = puts.loc[atm_idx]
            atm_iv = float(atm_row.get("impliedVolatility", 0) or 0) * 100

            # Best put CP in this expiry (OTM 5-10%)
            dte = binfo.get("dte", 1) or 1
            best_cp = 0.0
            for _, row in puts.iterrows():
                strike = float(row["strike"])
                otm_pct = (price - strike) / price * 100
                if 4 <= otm_pct <= 11:
                    bid = float(row.get("bid", 0) or 0)
                    if bid > 0 and strike > 0:
                        annualized = bid / strike * 365 / max(dte, 1) * 100
                        # Simplified CP estimate
                        cp = min(annualized, 200) / 200 * 30 + min(otm_pct, 10) / 10 * 25
                        best_cp = max(best_cp, round(cp, 1))

            result[bname] = {
                "expiry": exp_str,
                "atm_iv": round(atm_iv, 1),
                "best_put_cp": best_cp,
            }

            if atm_iv > 0:
                iv_values.append((dte, atm_iv))

        # Determine term structure
        if len(iv_values) >= 2:
            iv_values.sort(key=lambda x: x[0])
            first_iv = iv_values[0][1]
            last_iv = iv_values[-1][1]
            diff_pct = (last_iv - first_iv) / first_iv * 100 if first_iv > 0 else 0
            if diff_pct > 5:
                term_structure = "contango"
            elif diff_pct < -5:
                term_structure = "backwardation"
            else:
                term_structure = "flat"
        else:
            term_structure = "flat"

        result["term_structure"] = term_structure

        # Recommendation based on term structure
        if term_structure == "backwardation":
            result["recommendation"] = (
                "IV term structure in backwardation — near-term IV elevated. "
                "Prefer selling short-dated options for higher premium."
            )
        elif term_structure == "contango":
            result["recommendation"] = (
                "IV term structure in contango (normal). "
                "Consider selling monthly or quarterly expirations for smoother decay."
            )
        else:
            result["recommendation"] = (
                "IV term structure is flat. "
                "No strong edge from timing; use standard DTE selection."
            )

        return result
    except Exception:
        return None


# ============================================================
# 5. Auto-Roll Suggestions
# ============================================================

def suggest_rolls(positions: list[dict], current_prices: dict) -> list[dict]:
    """Suggest roll actions for expiring or challenged positions.

    Args:
        positions: List of position dicts, each containing:
            {"symbol": str, "strike": float, "expiry": str (YYYY-MM-DD),
             "type": "put"|"call", "premium_received": float}
        current_prices: Dict mapping symbol -> current market price.

    Returns:
        List of suggestion dicts:
            {"symbol": str, "action": "roll_out"|"close"|"let_expire",
             "reason": str, "suggested_new_expiry": str,
             "suggested_new_strike": float, "estimated_credit": float}
    """
    try:
        suggestions: list[dict] = []
        today = datetime.now()

        for pos in positions:
            symbol = pos.get("symbol", "")
            strike = pos.get("strike", 0)
            expiry_str = pos.get("expiry", "")
            opt_type = pos.get("type", "put")
            premium_received = pos.get("premium_received", 0)

            current_price = current_prices.get(symbol)
            if not current_price or not expiry_str:
                continue

            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            dte = (expiry_date - today).days

            # Determine if position is ITM
            if opt_type == "put":
                itm = current_price < strike
                otm_pct = (strike - current_price) / current_price * 100 if current_price > 0 else 0
            else:
                itm = current_price > strike
                otm_pct = (current_price - strike) / current_price * 100 if current_price > 0 else 0

            # New expiry: roll out ~30 days
            new_expiry_date = expiry_date + timedelta(days=30)
            new_expiry_str = new_expiry_date.strftime("%Y-%m-%d")

            # Case 1: Near expiration and OTM (profitable) — roll out for more premium
            if dte <= 7 and not itm:
                # Estimate new credit as fraction of original premium (rough)
                est_credit = round(premium_received * 0.3, 2)
                suggestions.append({
                    "symbol": symbol,
                    "action": "roll_out",
                    "reason": (
                        f"Only {dte}d to expiry, OTM by {abs(otm_pct):.1f}%. "
                        f"Roll out to capture additional premium."
                    ),
                    "suggested_new_expiry": new_expiry_str,
                    "suggested_new_strike": strike,
                    "estimated_credit": est_credit,
                })

            # Case 2: ITM and losing — suggest closing or rolling defensively
            elif itm and dte <= 14:
                if opt_type == "put":
                    new_strike = round(strike * 0.97, 2)  # Roll down
                else:
                    new_strike = round(strike * 1.03, 2)  # Roll up
                suggestions.append({
                    "symbol": symbol,
                    "action": "roll_out",
                    "reason": (
                        f"Position is ITM (price=${current_price:.2f} vs "
                        f"strike=${strike:.2f}). Roll {'down' if opt_type == 'put' else 'up'} "
                        f"and out to reduce assignment risk."
                    ),
                    "suggested_new_expiry": new_expiry_str,
                    "suggested_new_strike": new_strike,
                    "estimated_credit": 0.0,  # May require debit
                })

            # Case 3: Deep ITM with significant time left — close to limit losses
            elif itm and abs(otm_pct) > 5:
                suggestions.append({
                    "symbol": symbol,
                    "action": "close",
                    "reason": (
                        f"Deep ITM by {abs(otm_pct):.1f}% with {dte}d remaining. "
                        f"Consider closing to limit further losses."
                    ),
                    "suggested_new_expiry": "",
                    "suggested_new_strike": 0.0,
                    "estimated_credit": 0.0,
                })

            # Case 4: Far from expiry, OTM, safe — let it ride
            elif not itm and dte > 14:
                suggestions.append({
                    "symbol": symbol,
                    "action": "let_expire",
                    "reason": (
                        f"OTM by {abs(otm_pct):.1f}% with {dte}d remaining. "
                        f"Position is on track; no action needed."
                    ),
                    "suggested_new_expiry": "",
                    "suggested_new_strike": 0.0,
                    "estimated_credit": 0.0,
                })

            # Case 5: Near expiration and close to the money
            elif dte <= 7 and abs(otm_pct) < 2:
                suggestions.append({
                    "symbol": symbol,
                    "action": "close",
                    "reason": (
                        f"Near-the-money ({otm_pct:+.1f}%) with only {dte}d left. "
                        f"Close to avoid gamma risk and potential assignment."
                    ),
                    "suggested_new_expiry": "",
                    "suggested_new_strike": 0.0,
                    "estimated_credit": 0.0,
                })

        return suggestions
    except Exception:
        return []
