"""
Multi-Strategy Analysis Module — v2.0
Iron Condor, Vertical Spreads, Strangles, Wheel Strategy, Calendar Spreads, Position Sizing.
"""
import math
from datetime import datetime

import pandas as pd
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_closest_strike(df: pd.DataFrame, target: float) -> pd.Series | None:
    """Return the row in *df* whose strike is closest to *target*."""
    if df.empty:
        return None
    idx = (df["strike"] - target).abs().idxmin()
    return df.loc[idx]


def _safe_bid(row) -> float:
    """Extract bid price from a DataFrame row, defaulting to 0."""
    return float(row.get("bid", 0) or 0)


def _safe_ask(row) -> float:
    """Extract ask price from a DataFrame row, defaulting to 0."""
    return float(row.get("ask", 0) or 0)


def _safe_iv(row) -> float:
    """Extract implied volatility (as decimal) from a DataFrame row."""
    return float(row.get("impliedVolatility", 0) or 0)


def _safe_delta_estimate(strike: float, price: float, iv: float, days: int,
                         option_type: str = "put") -> float:
    """Estimate delta via Black-Scholes d1.

    Returns approximate |delta| for the given option type.
    """
    try:
        if strike <= 0 or price <= 0 or days <= 0 or iv <= 0:
            return 0.0
        r = 0.05
        T = days / 365.0
        sqrt_T = math.sqrt(T)
        d1 = (math.log(price / strike) + (r + 0.5 * iv ** 2) * T) / (iv * sqrt_T)
        if option_type == "call":
            return abs(norm.cdf(d1))
        else:
            return abs(norm.cdf(d1) - 1)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Function 1 — Iron Condor
# ---------------------------------------------------------------------------

def iron_condor(puts_df: pd.DataFrame, calls_df: pd.DataFrame,
                price: float, days_to_exp: int) -> dict | None:
    """Find optimal Iron Condor (sell put + buy lower put + sell call + buy higher call).

    Strategy: Sell 5% OTM put, Buy 10% OTM put, Sell 5% OTM call, Buy 10% OTM call.

    Returns:
        {"short_put": float, "long_put": float, "short_call": float, "long_call": float,
         "max_profit": float, "max_loss": float, "breakeven_low": float, "breakeven_high": float,
         "risk_reward": float, "width": float, "net_credit": float, "pop": float}
    """
    try:
        if puts_df.empty or calls_df.empty or price <= 0 or days_to_exp <= 0:
            return None

        # Target strikes
        short_put_target = price * 0.95   # 5% OTM put
        long_put_target = price * 0.90    # 10% OTM put
        short_call_target = price * 1.05  # 5% OTM call
        long_call_target = price * 1.10   # 10% OTM call

        # Find closest strikes
        sp_row = _find_closest_strike(puts_df, short_put_target)
        lp_row = _find_closest_strike(puts_df, long_put_target)
        sc_row = _find_closest_strike(calls_df, short_call_target)
        lc_row = _find_closest_strike(calls_df, long_call_target)

        if sp_row is None or lp_row is None or sc_row is None or lc_row is None:
            return None

        short_put = float(sp_row["strike"])
        long_put = float(lp_row["strike"])
        short_call = float(sc_row["strike"])
        long_call = float(lc_row["strike"])

        # Ensure correct ordering: long_put < short_put < short_call < long_call
        if not (long_put < short_put < short_call < long_call):
            return None

        # Net credit = (short put bid + short call bid) - (long put ask + long call ask)
        net_credit = (
            (_safe_bid(sp_row) + _safe_bid(sc_row))
            - (_safe_ask(lp_row) + _safe_ask(lc_row))
        )

        if net_credit <= 0:
            return None

        # Width of each spread (use the wider of the two sides)
        put_width = short_put - long_put
        call_width = long_call - short_call
        width = max(put_width, call_width)

        # Max profit = net credit, Max loss = width - net credit
        max_profit = net_credit
        max_loss = width - net_credit
        if max_loss <= 0:
            return None

        # Breakevens
        breakeven_low = short_put - net_credit
        breakeven_high = short_call + net_credit

        # Risk/reward ratio
        risk_reward = round(max_profit / max_loss, 3)

        # POP estimate: 1 - (net_credit / width)
        pop = (1.0 - (net_credit / width)) * 100.0

        return {
            "short_put": round(short_put, 2),
            "long_put": round(long_put, 2),
            "short_call": round(short_call, 2),
            "long_call": round(long_call, 2),
            "max_profit": round(max_profit, 2),
            "max_loss": round(max_loss, 2),
            "breakeven_low": round(breakeven_low, 2),
            "breakeven_high": round(breakeven_high, 2),
            "risk_reward": risk_reward,
            "width": round(width, 2),
            "net_credit": round(net_credit, 2),
            "pop": round(pop, 2),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Function 2 — Vertical Spread
# ---------------------------------------------------------------------------

def vertical_spread(options_df: pd.DataFrame, price: float, days_to_exp: int,
                    spread_type: str = "bull_put") -> dict | None:
    """Analyze vertical spread strategies.

    spread_type: "bull_put" (sell higher put, buy lower put)
                 or "bear_call" (sell lower call, buy higher call)

    Returns:
        {"short_strike": float, "long_strike": float, "net_credit": float,
         "max_profit": float, "max_loss": float, "breakeven": float,
         "risk_reward": float, "pop": float, "width": float}
    """
    try:
        if options_df.empty or price <= 0 or days_to_exp <= 0:
            return None

        if spread_type == "bull_put":
            # Sell 5% OTM put, buy 10% OTM put
            short_target = price * 0.95
            long_target = price * 0.90
        elif spread_type == "bear_call":
            # Sell 5% OTM call, buy 10% OTM call
            short_target = price * 1.05
            long_target = price * 1.10
        else:
            return None

        short_row = _find_closest_strike(options_df, short_target)
        long_row = _find_closest_strike(options_df, long_target)

        if short_row is None or long_row is None:
            return None

        short_strike = float(short_row["strike"])
        long_strike = float(long_row["strike"])

        # Validate ordering
        if spread_type == "bull_put" and long_strike >= short_strike:
            return None
        if spread_type == "bear_call" and long_strike <= short_strike:
            return None

        # Net credit = short leg bid - long leg ask
        net_credit = _safe_bid(short_row) - _safe_ask(long_row)
        if net_credit <= 0:
            return None

        width = abs(short_strike - long_strike)
        max_profit = net_credit
        max_loss = width - net_credit
        if max_loss <= 0:
            return None

        # Breakeven
        if spread_type == "bull_put":
            breakeven = short_strike - net_credit
        else:
            breakeven = short_strike + net_credit

        risk_reward = round(max_profit / max_loss, 3)

        # POP estimate
        pop = (1.0 - (net_credit / width)) * 100.0

        return {
            "short_strike": round(short_strike, 2),
            "long_strike": round(long_strike, 2),
            "net_credit": round(net_credit, 2),
            "max_profit": round(max_profit, 2),
            "max_loss": round(max_loss, 2),
            "breakeven": round(breakeven, 2),
            "risk_reward": risk_reward,
            "pop": round(pop, 2),
            "width": round(width, 2),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Function 3 — Strangle / Straddle
# ---------------------------------------------------------------------------

def strangle_straddle(puts_df: pd.DataFrame, calls_df: pd.DataFrame,
                      price: float, days_to_exp: int) -> dict | None:
    """Analyze Short Strangle and Short Straddle.

    Returns:
        {"straddle": {"strike": float, "credit": float, "breakeven_low": float,
                      "breakeven_high": float, "max_profit": float},
         "strangle": {"put_strike": float, "call_strike": float, "credit": float,
                      "breakeven_low": float, "breakeven_high": float, "max_profit": float}}
    """
    try:
        if puts_df.empty or calls_df.empty or price <= 0 or days_to_exp <= 0:
            return None

        # --- Straddle: sell ATM put + ATM call at same strike ---
        atm_put_row = _find_closest_strike(puts_df, price)
        atm_call_row = _find_closest_strike(calls_df, price)

        if atm_put_row is None or atm_call_row is None:
            return None

        # Use the same ATM strike (prefer the put side for consistency)
        atm_strike = float(atm_put_row["strike"])
        # Re-fetch call at exact same strike if available
        exact_call = calls_df[calls_df["strike"] == atm_strike]
        if not exact_call.empty:
            atm_call_row = exact_call.iloc[0]
        else:
            # Fall back to the closest call strike
            atm_call_row = _find_closest_strike(calls_df, atm_strike)
            atm_strike = float(atm_call_row["strike"]) if atm_call_row is not None else atm_strike

        straddle_credit = _safe_bid(atm_put_row) + _safe_bid(atm_call_row)

        straddle = {
            "strike": round(atm_strike, 2),
            "credit": round(straddle_credit, 2),
            "breakeven_low": round(atm_strike - straddle_credit, 2),
            "breakeven_high": round(atm_strike + straddle_credit, 2),
            "max_profit": round(straddle_credit, 2),
        }

        # --- Strangle: sell 5% OTM put + 5% OTM call ---
        otm_put_row = _find_closest_strike(puts_df, price * 0.95)
        otm_call_row = _find_closest_strike(calls_df, price * 1.05)

        if otm_put_row is None or otm_call_row is None:
            return None

        put_strike = float(otm_put_row["strike"])
        call_strike = float(otm_call_row["strike"])
        strangle_credit = _safe_bid(otm_put_row) + _safe_bid(otm_call_row)

        strangle = {
            "put_strike": round(put_strike, 2),
            "call_strike": round(call_strike, 2),
            "credit": round(strangle_credit, 2),
            "breakeven_low": round(put_strike - strangle_credit, 2),
            "breakeven_high": round(call_strike + strangle_credit, 2),
            "max_profit": round(strangle_credit, 2),
        }

        return {"straddle": straddle, "strangle": strangle}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Function 4 — Wheel Strategy
# ---------------------------------------------------------------------------

def wheel_strategy(puts_df: pd.DataFrame, price: float,
                   days_to_exp: int) -> dict | None:
    """Analyze Wheel Strategy entry point (Sell Put to potentially get assigned).

    Returns:
        {"entry_strike": float, "premium": float, "effective_cost_basis": float,
         "discount_pct": float, "annualized_yield": float,
         "break_even": float, "assignment_probability": float}
    """
    try:
        if puts_df.empty or price <= 0 or days_to_exp <= 0:
            return None

        # Pick ~5% OTM put
        target_strike = price * 0.95
        row = _find_closest_strike(puts_df, target_strike)
        if row is None:
            return None

        strike = float(row["strike"])
        premium = _safe_bid(row)
        if premium <= 0:
            return None

        # Effective cost basis = strike - premium received
        effective_cost_basis = strike - premium

        # Discount from current price
        discount_pct = (price - effective_cost_basis) / price * 100.0

        # Annualized yield = (premium / strike) * (365 / days) * 100
        annualized_yield = (premium / strike) * (365.0 / days_to_exp) * 100.0

        # Assignment probability estimated via |delta|
        iv = _safe_iv(row)
        delta = _safe_delta_estimate(strike, price, iv, days_to_exp, option_type="put")
        assignment_probability = delta * 100.0

        return {
            "entry_strike": round(strike, 2),
            "premium": round(premium, 2),
            "effective_cost_basis": round(effective_cost_basis, 2),
            "discount_pct": round(discount_pct, 2),
            "annualized_yield": round(annualized_yield, 2),
            "break_even": round(effective_cost_basis, 2),
            "assignment_probability": round(assignment_probability, 2),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Function 5 — Calendar Spread
# ---------------------------------------------------------------------------

def calendar_spread(tk, price: float) -> dict | None:
    """Compare front-month vs back-month IV for calendar spread opportunities.

    Returns:
        {"front_expiry": str, "back_expiry": str, "front_iv": float, "back_iv": float,
         "iv_difference": float, "opportunity": str, "atm_strike": float}
    """
    try:
        expiries = tk.options
        if not expiries or len(expiries) < 2:
            return None

        front_expiry = expiries[0]
        back_expiry = expiries[1]

        front_chain = tk.option_chain(front_expiry)
        back_chain = tk.option_chain(back_expiry)

        front_calls = front_chain.calls
        back_calls = back_chain.calls

        if front_calls.empty or back_calls.empty:
            return None

        # Find ATM strike for front month
        atm_row_front = _find_closest_strike(front_calls, price)
        if atm_row_front is None:
            return None
        atm_strike = float(atm_row_front["strike"])

        # Get IV at ATM strike for both months
        front_iv = _safe_iv(atm_row_front) * 100.0  # convert to percentage

        back_atm = back_calls[back_calls["strike"] == atm_strike]
        if back_atm.empty:
            # Fall back to closest strike in back month
            back_row = _find_closest_strike(back_calls, atm_strike)
            if back_row is None:
                return None
            back_iv = _safe_iv(back_row) * 100.0
        else:
            back_iv = _safe_iv(back_atm.iloc[0]) * 100.0

        if front_iv <= 0 and back_iv <= 0:
            return None

        iv_difference = front_iv - back_iv

        # Determine opportunity
        if iv_difference > 0:
            opportunity = "Sell Front / Buy Back"
        elif iv_difference < 0:
            opportunity = "Buy Front / Sell Back"
        else:
            opportunity = "No clear opportunity"

        return {
            "front_expiry": front_expiry,
            "back_expiry": back_expiry,
            "front_iv": round(front_iv, 2),
            "back_iv": round(back_iv, 2),
            "iv_difference": round(iv_difference, 2),
            "opportunity": opportunity,
            "atm_strike": round(atm_strike, 2),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Function 6 — Position Sizing
# ---------------------------------------------------------------------------

def position_sizing(price: float, max_risk_dollars: float = 5000,
                    strategy_max_loss: float = 500) -> dict:
    """Calculate position size based on risk management.

    Returns:
        {"contracts": int, "total_risk": float, "risk_pct_of_capital": float,
         "margin_required": float, "capital_needed": float}
    """
    try:
        if strategy_max_loss <= 0 or price <= 0:
            return {
                "contracts": 0,
                "total_risk": 0.0,
                "risk_pct_of_capital": 0.0,
                "margin_required": 0.0,
                "capital_needed": 0.0,
            }

        # Number of contracts: floor(max_risk / max_loss_per_contract)
        contracts = max(1, math.floor(max_risk_dollars / strategy_max_loss))

        # Total risk for this position
        total_risk = contracts * strategy_max_loss

        # Risk as percentage of total capital (assume capital = max_risk_dollars * 10)
        assumed_capital = max_risk_dollars * 10
        risk_pct = (total_risk / assumed_capital) * 100.0

        # Margin required: ~20% of underlying * 100 shares * contracts (naked options)
        margin_required = 0.20 * price * 100 * contracts

        # Capital needed: margin + total risk buffer
        capital_needed = margin_required + total_risk

        return {
            "contracts": contracts,
            "total_risk": round(total_risk, 2),
            "risk_pct_of_capital": round(risk_pct, 2),
            "margin_required": round(margin_required, 2),
            "capital_needed": round(capital_needed, 2),
        }
    except Exception:
        return {
            "contracts": 0,
            "total_risk": 0.0,
            "risk_pct_of_capital": 0.0,
            "margin_required": 0.0,
            "capital_needed": 0.0,
        }
