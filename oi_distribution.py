"""
Options Open Interest & Volume Distribution Analysis
Identifies where the 'crowd' is positioned — which strikes have the most activity.
Data source: yfinance options chain (free, no API key needed).
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# Minimum days to expiry — skip very short-dated expiries
_MIN_DTE = 5


def analyze_oi_distribution(symbol: str, num_expiries: int = 3) -> dict | None:
    """Analyze open interest distribution across strikes.

    Fetches the nearest ``num_expiries`` option expiries (skipping < 5 DTE),
    aggregates OI per strike, and returns concentration / key-level data.

    Returns:
        A dict with OI distribution metrics, or None on failure.
    """
    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose", 0)
        )
        if not price:
            return None

        # ── Collect valid expiries ────────────────────────────
        all_expiries = tk.options
        if not all_expiries:
            return None

        now = datetime.now()
        valid_expiries: list[str] = []
        for exp_str in all_expiries:
            try:
                dte = (datetime.strptime(exp_str, "%Y-%m-%d") - now).days
                if dte >= _MIN_DTE:
                    valid_expiries.append(exp_str)
            except ValueError:
                continue
            if len(valid_expiries) >= num_expiries:
                break

        if not valid_expiries:
            return None

        # ── Fetch chains and aggregate ────────────────────────
        all_calls: list[pd.DataFrame] = []
        all_puts: list[pd.DataFrame] = []

        for exp in valid_expiries:
            try:
                chain = tk.option_chain(exp)
                if not chain.calls.empty:
                    df = chain.calls.copy()
                    df["expiry"] = exp
                    all_calls.append(df)
                if not chain.puts.empty:
                    df = chain.puts.copy()
                    df["expiry"] = exp
                    all_puts.append(df)
            except Exception:
                continue

        if not all_calls and not all_puts:
            return None

        calls_df = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
        puts_df = pd.concat(all_puts, ignore_index=True) if all_puts else pd.DataFrame()

        # Ensure numeric columns
        for df in (calls_df, puts_df):
            if df.empty:
                continue
            for col in ("openInterest", "volume", "impliedVolatility", "strike"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # ── Aggregate OI by strike ────────────────────────────
        call_oi_by_strike = (
            calls_df.groupby("strike")
            .agg(oi=("openInterest", "sum"), volume=("volume", "sum"), iv=("impliedVolatility", "mean"))
            .reset_index()
            if not calls_df.empty
            else pd.DataFrame(columns=["strike", "oi", "volume", "iv"])
        )
        put_oi_by_strike = (
            puts_df.groupby("strike")
            .agg(oi=("openInterest", "sum"), volume=("volume", "sum"), iv=("impliedVolatility", "mean"))
            .reset_index()
            if not puts_df.empty
            else pd.DataFrame(columns=["strike", "oi", "volume", "iv"])
        )

        total_call_oi = int(call_oi_by_strike["oi"].sum())
        total_put_oi = int(put_oi_by_strike["oi"].sum())
        pc_oi_ratio = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0

        # ── Top 5 concentrations ──────────────────────────────
        def _top_strikes(df: pd.DataFrame, n: int = 5) -> list[dict]:
            if df.empty:
                return []
            top = df.nlargest(n, "oi")
            result = []
            for _, row in top.iterrows():
                strike = float(row["strike"])
                dist_pct = round((strike - price) / price * 100, 2)
                result.append({
                    "strike": strike,
                    "oi": int(row["oi"]),
                    "volume": int(row["volume"]),
                    "iv": round(float(row["iv"]) * 100, 1),
                    "distance_pct": dist_pct,
                })
            return result

        put_concentration = _top_strikes(put_oi_by_strike)
        call_concentration = _top_strikes(call_oi_by_strike)

        # ── Full OI-by-strike distribution ────────────────────
        all_strikes = sorted(
            set(call_oi_by_strike["strike"].tolist() + put_oi_by_strike["strike"].tolist())
        )
        call_lookup = dict(zip(call_oi_by_strike["strike"], call_oi_by_strike["oi"]))
        put_lookup = dict(zip(put_oi_by_strike["strike"], put_oi_by_strike["oi"]))

        oi_by_strike: list[dict] = []
        for s in all_strikes:
            c_oi = int(call_lookup.get(s, 0))
            p_oi = int(put_lookup.get(s, 0))
            oi_by_strike.append({
                "strike": float(s),
                "call_oi": c_oi,
                "put_oi": p_oi,
                "net_oi": c_oi - p_oi,
            })

        # ── Volume hotspots ───────────────────────────────────
        # Combine call + put volume, find strikes with notably high volume
        vol_records: list[dict] = []
        for _, row in calls_df.iterrows() if not calls_df.empty else []:
            vol = int(row.get("volume", 0) or 0)
            oi = int(row.get("openInterest", 0) or 0)
            if vol > 0:
                vol_records.append({
                    "strike": float(row["strike"]),
                    "type": "call",
                    "volume": vol,
                    "oi": oi,
                    "vol_oi_ratio": round(vol / oi, 2) if oi > 0 else 0.0,
                })
        for _, row in puts_df.iterrows() if not puts_df.empty else []:
            vol = int(row.get("volume", 0) or 0)
            oi = int(row.get("openInterest", 0) or 0)
            if vol > 0:
                vol_records.append({
                    "strike": float(row["strike"]),
                    "type": "put",
                    "volume": vol,
                    "oi": oi,
                    "vol_oi_ratio": round(vol / oi, 2) if oi > 0 else 0.0,
                })

        # Sort by volume descending, keep top 10
        vol_records.sort(key=lambda x: x["volume"], reverse=True)
        volume_hotspots = vol_records[:10]

        # ── Key levels ────────────────────────────────────────
        max_call_oi_strike = (
            float(call_oi_by_strike.loc[call_oi_by_strike["oi"].idxmax(), "strike"])
            if not call_oi_by_strike.empty and call_oi_by_strike["oi"].sum() > 0
            else 0.0
        )
        max_put_oi_strike = (
            float(put_oi_by_strike.loc[put_oi_by_strike["oi"].idxmax(), "strike"])
            if not put_oi_by_strike.empty and put_oi_by_strike["oi"].sum() > 0
            else 0.0
        )
        highest_vol_strike = float(volume_hotspots[0]["strike"]) if volume_hotspots else 0.0

        # Max pain: the strike where total option holder losses are maximised
        # (i.e., where the stock would cause the most options to expire worthless)
        max_pain = _calculate_max_pain(all_strikes, call_lookup, put_lookup)

        key_levels = {
            "max_call_oi_strike": max_call_oi_strike,
            "max_put_oi_strike": max_put_oi_strike,
            "max_pain": max_pain,
            "highest_volume_strike": highest_vol_strike,
        }

        # ── Interpretation ────────────────────────────────────
        interpretation = _build_interpretation(
            price, max_put_oi_strike, max_call_oi_strike,
            total_put_oi, total_call_oi, highest_vol_strike,
            put_concentration, call_concentration, volume_hotspots,
        )

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "expiries_analyzed": len(valid_expiries),
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "pc_oi_ratio": pc_oi_ratio,
            "put_concentration": put_concentration,
            "call_concentration": call_concentration,
            "oi_by_strike": oi_by_strike,
            "volume_hotspots": volume_hotspots,
            "key_levels": key_levels,
            "interpretation": interpretation,
        }

    except Exception as e:
        print(f"[oi_distribution] Error analyzing {symbol}: {e}")
        return None


def _calculate_max_pain(
    strikes: list[float],
    call_oi: dict[float, float],
    put_oi: dict[float, float],
) -> float:
    """Calculate max-pain strike (minimises total intrinsic value of all options).

    At each candidate strike, compute the total intrinsic value that option
    holders would receive.  Max pain is the strike that minimises this sum.
    """
    if not strikes:
        return 0.0

    best_strike = strikes[0]
    min_pain = float("inf")

    for s in strikes:
        total_pain = 0.0
        # Call holders' intrinsic value if stock settles at s
        for k, oi in call_oi.items():
            if s > k:
                total_pain += (s - k) * oi
        # Put holders' intrinsic value if stock settles at s
        for k, oi in put_oi.items():
            if s < k:
                total_pain += (k - s) * oi
        if total_pain < min_pain:
            min_pain = total_pain
            best_strike = s

    return float(best_strike)


def _build_interpretation(
    price: float,
    max_put_strike: float,
    max_call_strike: float,
    total_put_oi: int,
    total_call_oi: int,
    highest_vol_strike: float,
    put_conc: list[dict],
    call_conc: list[dict],
    vol_hotspots: list[dict],
) -> str:
    """Generate a concise English interpretation paragraph."""
    parts: list[str] = []

    # Put support
    if max_put_strike > 0 and put_conc:
        top_put_oi = put_conc[0]["oi"]
        oi_label = _format_oi(top_put_oi)
        dist = round((max_put_strike - price) / price * 100, 1)
        parts.append(f"Heavy put support at ${max_put_strike:,.0f} ({oi_label} OI, {dist:+.1f}%)")

    # Call resistance
    if max_call_strike > 0 and call_conc:
        top_call_oi = call_conc[0]["oi"]
        oi_label = _format_oi(top_call_oi)
        dist = round((max_call_strike - price) / price * 100, 1)
        parts.append(f"call resistance at ${max_call_strike:,.0f} ({oi_label} OI, {dist:+.1f}%)")

    # Range statement
    if max_put_strike > 0 and max_call_strike > 0:
        parts.append(
            f"Traders are positioned for the ${max_put_strike:,.0f}–${max_call_strike:,.0f} range"
        )

    # P/C ratio interpretation
    if total_call_oi > 0:
        pc = total_put_oi / total_call_oi
        if pc > 1.2:
            parts.append(f"P/C OI ratio {pc:.2f} suggests bearish hedging")
        elif pc < 0.7:
            parts.append(f"P/C OI ratio {pc:.2f} suggests bullish sentiment")

    # Volume hotspot
    if highest_vol_strike > 0 and vol_hotspots:
        top_vol = vol_hotspots[0]["volume"]
        vol_type = vol_hotspots[0]["type"]
        parts.append(
            f"Highest volume today at ${highest_vol_strike:,.0f} "
            f"({top_vol:,} {vol_type} contracts)"
        )

    return ". ".join(parts) + "." if parts else "Insufficient data for interpretation."


def _format_oi(value: int) -> str:
    """Format large OI numbers: 12450 -> '12.5K'."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


# ============================================================
# Markdown report section
# ============================================================

def generate_oi_section(tickers: list[str]) -> str:
    """Generate markdown section for the daily report.

    Returns a markdown string with OI distribution tables for each ticker,
    or an empty string if no data is available.
    """
    try:
        sections: list[str] = []
        sections.append("## 📊 Options Position Distribution")
        sections.append("")

        any_data = False
        for symbol in tickers:
            result = analyze_oi_distribution(symbol)
            if result is None:
                continue
            any_data = True
            sections.append(_format_ticker_section(result))

        if not any_data:
            return ""

        return "\n".join(sections)
    except Exception as e:
        print(f"[oi_distribution] Error generating OI section: {e}")
        return ""


def _format_ticker_section(data: dict) -> str:
    """Format a single ticker's OI distribution as markdown."""
    lines: list[str] = []
    symbol = data["symbol"]
    price = data["price"]

    lines.append(f"### {symbol} (${price:,.2f})")
    lines.append("")
    lines.append("**Where traders are positioned:**")
    lines.append("")
    lines.append("| | Strike | OI | Volume | IV | Distance |")
    lines.append("|---|---|---|---|---|---|")

    # Top 3 puts (by OI)
    for i, p in enumerate(data["put_concentration"][:3], 1):
        lines.append(
            f"| 🔴 Put #{i} "
            f"| ${p['strike']:,.0f} "
            f"| {p['oi']:,} "
            f"| {p['volume']:,} "
            f"| {p['iv']:.0f}% "
            f"| {p['distance_pct']:+.1f}% |"
        )

    # Top 3 calls (by OI)
    for i, c in enumerate(data["call_concentration"][:3], 1):
        lines.append(
            f"| 🟢 Call #{i} "
            f"| ${c['strike']:,.0f} "
            f"| {c['oi']:,} "
            f"| {c['volume']:,} "
            f"| {c['iv']:.0f}% "
            f"| {c['distance_pct']:+.1f}% |"
        )

    lines.append("")

    # Key levels
    kl = data["key_levels"]
    lines.append("**Key Levels:**")

    if kl["max_put_oi_strike"] > 0:
        dist = round((kl["max_put_oi_strike"] - price) / price * 100, 1)
        lines.append(f"- 🛡️ Support (max put OI): ${kl['max_put_oi_strike']:,.0f} ({dist:+.1f}%)")

    if kl["max_call_oi_strike"] > 0:
        dist = round((kl["max_call_oi_strike"] - price) / price * 100, 1)
        lines.append(f"- 🚧 Resistance (max call OI): ${kl['max_call_oi_strike']:,.0f} ({dist:+.1f}%)")

    if kl["highest_volume_strike"] > 0 and data["volume_hotspots"]:
        top = data["volume_hotspots"][0]
        lines.append(
            f"- 🔥 Highest volume today: ${kl['highest_volume_strike']:,.0f} "
            f"({top['volume']:,} contracts)"
        )

    if kl["max_pain"] > 0:
        dist = round((kl["max_pain"] - price) / price * 100, 1)
        lines.append(f"- 💀 Max pain: ${kl['max_pain']:,.0f} ({dist:+.1f}%)")

    lines.append("")

    # P/C ratio
    lines.append(
        f"**P/C OI Ratio:** {data['pc_oi_ratio']:.2f} "
        f"(Put OI: {data['total_put_oi']:,} / Call OI: {data['total_call_oi']:,})"
    )
    lines.append("")

    # Interpretation
    lines.append(f"**Interpretation:** {data['interpretation']}")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# CLI entry point
# ============================================================
if __name__ == "__main__":
    import json
    import sys

    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["TSLA", "AMZN", "NVDA"]

    for sym in tickers:
        print(f"\n{'='*60}")
        print(f"  {sym} — OI Distribution Analysis")
        print(f"{'='*60}")
        result = analyze_oi_distribution(sym)
        if result:
            print(f"  Price: ${result['price']:,.2f}")
            print(f"  Expiries analyzed: {result['expiries_analyzed']}")
            print(f"  P/C OI ratio: {result['pc_oi_ratio']:.2f}")
            kl = result["key_levels"]
            print(f"  Support (max put OI):  ${kl['max_put_oi_strike']:,.0f}")
            print(f"  Resistance (max call): ${kl['max_call_oi_strike']:,.0f}")
            print(f"  Max pain:              ${kl['max_pain']:,.0f}")
            print(f"\n  {result['interpretation']}")
        else:
            print("  No data available.")

    print(f"\n{'='*60}")
    print("Markdown output:")
    print(f"{'='*60}")
    md = generate_oi_section(tickers)
    if md:
        print(md)
    else:
        print("(no markdown generated)")
