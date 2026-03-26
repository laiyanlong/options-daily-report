"""
Options Intelligence Module — v1.2
Advanced options analytics: P/C ratio, max pain, unusual activity,
expected move, probability of profit, bid-ask quality.
"""
import math
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import norm


def put_call_ratio(tk) -> dict | None:
    """Calculate put/call ratio from the nearest expiry's full options chain.

    Returns:
        {"volume_ratio": float, "oi_ratio": float, "signal": str,
         "call_volume": int, "put_volume": int, "call_oi": int, "put_oi": int}
    Signal: ratio < 0.7 = "Bullish", 0.7-1.0 = "Neutral-Bullish",
            1.0-1.3 = "Neutral-Bearish", > 1.3 = "Bearish"
    """
    try:
        expiries = tk.options
        if not expiries:
            return None

        chain = tk.option_chain(expiries[0])
        calls = chain.calls
        puts = chain.puts

        call_volume = int(calls["volume"].sum()) if "volume" in calls.columns else 0
        put_volume = int(puts["volume"].sum()) if "volume" in puts.columns else 0
        call_oi = int(calls["openInterest"].sum()) if "openInterest" in calls.columns else 0
        put_oi = int(puts["openInterest"].sum()) if "openInterest" in puts.columns else 0

        # Calculate ratios, handle division by zero
        volume_ratio = put_volume / call_volume if call_volume > 0 else float("inf")
        oi_ratio = put_oi / call_oi if call_oi > 0 else float("inf")

        # Determine signal based on volume ratio
        if volume_ratio < 0.7:
            signal = "Bullish"
        elif volume_ratio < 1.0:
            signal = "Neutral-Bullish"
        elif volume_ratio < 1.3:
            signal = "Neutral-Bearish"
        else:
            signal = "Bearish"

        return {
            "volume_ratio": round(volume_ratio, 3),
            "oi_ratio": round(oi_ratio, 3),
            "signal": signal,
            "call_volume": call_volume,
            "put_volume": put_volume,
            "call_oi": call_oi,
            "put_oi": put_oi,
        }
    except Exception:
        return None


def max_pain(tk) -> dict | None:
    """Calculate max pain price for nearest expiry.

    Max pain is the strike price where total pain (loss) for all option
    holders is minimized — i.e., where option sellers profit the most.

    Returns:
        {"max_pain_price": float, "current_price": float,
         "distance_pct": float, "direction": str}
    direction: "above" if price > max_pain, "below" otherwise
    """
    try:
        expiries = tk.options
        if not expiries:
            return None

        chain = tk.option_chain(expiries[0])
        calls = chain.calls
        puts = chain.puts

        # Build lookup of OI by strike for calls and puts
        call_oi_map = dict(zip(calls["strike"], calls["openInterest"].fillna(0)))
        put_oi_map = dict(zip(puts["strike"], puts["openInterest"].fillna(0)))

        # Collect all unique strikes
        all_strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
        if not all_strikes:
            return None

        # For each candidate expiry price, calculate total pain
        min_pain = float("inf")
        pain_strike = all_strikes[0]

        for s in all_strikes:
            total_pain = 0.0

            # Pain for call holders: each call with strike K loses max(0, S - K) * OI
            for k, oi in call_oi_map.items():
                total_pain += max(0.0, s - k) * oi

            # Pain for put holders: each put with strike K loses max(0, K - S) * OI
            for k, oi in put_oi_map.items():
                total_pain += max(0.0, k - s) * oi

            if total_pain < min_pain:
                min_pain = total_pain
                pain_strike = s

        # Current price
        info = tk.info
        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose", 0)
        )
        if current_price <= 0:
            return None

        distance_pct = (current_price - pain_strike) / pain_strike * 100
        direction = "above" if current_price > pain_strike else "below"

        return {
            "max_pain_price": round(pain_strike, 2),
            "current_price": round(current_price, 2),
            "distance_pct": round(distance_pct, 2),
            "direction": direction,
        }
    except Exception:
        return None


def unusual_activity(tk) -> list[dict] | None:
    """Detect unusual options activity (high volume/OI ratio).

    Scans the nearest 2 expiries for strikes where daily volume exceeds
    2x open interest — a classic signal of large or speculative positioning.

    Returns list of:
        {"strike": float, "type": "call"|"put", "volume": int, "oi": int,
         "vol_oi_ratio": float, "iv": float, "expiry": str}
    Filtered to vol/oi > 2.0, sorted by vol_oi_ratio descending, top 5.
    """
    try:
        expiries = tk.options
        if not expiries:
            return None

        unusual = []
        scan_expiries = list(expiries[:2])

        for exp in scan_expiries:
            chain = tk.option_chain(exp)

            for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
                if df.empty:
                    continue

                for _, row in df.iterrows():
                    volume = int(row.get("volume", 0) or 0)
                    oi = int(row.get("openInterest", 0) or 0)

                    if oi <= 0 or volume <= 0:
                        continue

                    ratio = volume / oi
                    if ratio > 2.0:
                        iv = float(row.get("impliedVolatility", 0) or 0) * 100
                        unusual.append({
                            "strike": float(row["strike"]),
                            "type": opt_type,
                            "volume": volume,
                            "oi": oi,
                            "vol_oi_ratio": round(ratio, 2),
                            "iv": round(iv, 1),
                            "expiry": exp,
                        })

        if not unusual:
            return None

        # Sort by vol/oi ratio descending, return top 5
        unusual.sort(key=lambda x: x["vol_oi_ratio"], reverse=True)
        return unusual[:5]
    except Exception:
        return None


def expected_move(tk) -> dict | None:
    """Calculate expected move from ATM straddle price.

    The ATM straddle (call bid + put bid at the strike nearest the current
    price) approximates the market's implied 1-sigma move for that expiry.

    Returns:
        {"expected_move_pct": float, "expected_move_dollar": float,
         "upper_bound": float, "lower_bound": float,
         "current_price": float, "days_to_expiry": int}
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

        # Current price
        info = tk.info
        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose", 0)
        )
        if current_price <= 0:
            return None

        # Find ATM strike (closest to current price)
        all_strikes = sorted(calls["strike"].tolist())
        if not all_strikes:
            return None
        atm_strike = min(all_strikes, key=lambda s: abs(s - current_price))

        # Get ATM call and put bids
        call_row = calls[calls["strike"] == atm_strike]
        put_row = puts[puts["strike"] == atm_strike]

        if call_row.empty or put_row.empty:
            return None

        call_bid = float(call_row.iloc[0].get("bid", 0) or 0)
        put_bid = float(put_row.iloc[0].get("bid", 0) or 0)

        # Expected move = straddle price
        em_dollar = call_bid + put_bid
        if em_dollar <= 0:
            return None

        em_pct = em_dollar / current_price * 100

        # Days to expiry
        exp_dt = datetime.strptime(expiries[0], "%Y-%m-%d")
        days_to_expiry = max((exp_dt - datetime.now()).days, 1)

        return {
            "expected_move_pct": round(em_pct, 2),
            "expected_move_dollar": round(em_dollar, 2),
            "upper_bound": round(current_price + em_dollar, 2),
            "lower_bound": round(current_price - em_dollar, 2),
            "current_price": round(current_price, 2),
            "days_to_expiry": days_to_expiry,
        }
    except Exception:
        return None


def probability_of_profit(
    strike: float,
    current_price: float,
    days: int,
    iv_pct: float,
    option_type: str = "put",
) -> float:
    """Calculate probability of profit for selling an option.

    Uses Black-Scholes d2 and the cumulative normal distribution.
    - Sell Put POP  = N(d2) — probability stock stays above strike
    - Sell Call POP = 1 - N(d2) — probability stock stays below strike

    Args:
        strike: Option strike price.
        current_price: Current underlying price.
        days: Days to expiration.
        iv_pct: Implied volatility as a percentage (e.g. 35 for 35%).
        option_type: "put" or "call".

    Returns:
        Probability as percentage (0-100), or 0.0 on failure.
    """
    try:
        if strike <= 0 or current_price <= 0 or days <= 0 or iv_pct <= 0:
            return 0.0

        r = 0.05  # 5% risk-free rate
        T = days / 365.0
        sigma = iv_pct / 100.0
        sqrt_T = math.sqrt(T)

        d2 = (math.log(current_price / strike) + (r - 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)

        if option_type == "put":
            # Sell put profits when stock stays above strike
            pop = norm.cdf(d2) * 100.0
        else:
            # Sell call profits when stock stays below strike
            pop = (1.0 - norm.cdf(d2)) * 100.0

        return round(pop, 2)
    except Exception:
        return 0.0


def spread_quality(entries: list[dict]) -> list[dict]:
    """Evaluate bid-ask spread quality for option entries.

    A tighter spread means lower friction when entering or exiting a
    position — critical for short-premium strategies.

    Args:
        entries: list of dicts with 'strike', 'bid', 'ask' keys.

    Returns list of:
        {"strike": float, "bid": float, "ask": float,
         "spread": float, "spread_pct": float, "quality": str}
    quality: spread_pct < 5% = "Excellent", 5-10% = "Good",
             10-20% = "Fair", > 20% = "Poor"
    """
    try:
        if not entries:
            return []

        results = []
        for e in entries:
            bid = float(e.get("bid", 0) or 0)
            ask = float(e.get("ask", 0) or 0)
            strike = float(e.get("strike", 0) or 0)

            spread = ask - bid
            mid = (bid + ask) / 2.0

            if mid > 0:
                spread_pct = spread / mid * 100.0
            elif ask > 0:
                # If bid is 0 but ask > 0, spread is effectively 200%
                spread_pct = 200.0
            else:
                spread_pct = 0.0

            if spread_pct < 5:
                quality = "Excellent"
            elif spread_pct < 10:
                quality = "Good"
            elif spread_pct < 20:
                quality = "Fair"
            else:
                quality = "Poor"

            results.append({
                "strike": strike,
                "bid": bid,
                "ask": ask,
                "spread": round(spread, 4),
                "spread_pct": round(spread_pct, 2),
                "quality": quality,
            })

        return results
    except Exception:
        return []
