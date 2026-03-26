"""
Advanced Risk Management Module — v3.1
Portfolio Greeks, VaR, correlation sizing, scenario analysis, tail risk.
"""
import math

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm


# ============================================================
# 1. Portfolio Greeks Aggregation
# ============================================================

def portfolio_greeks(positions: list[dict]) -> dict | None:
    """Calculate net portfolio Greeks.

    Aggregates Greeks across all positions, accounting for long/short
    direction and contract multiplier (100 shares per contract).

    Args:
        positions: List of position dicts, each containing:
            {"symbol": str, "contracts": int, "delta": float, "gamma": float,
             "theta": float, "vega": float, "price": float,
             "side": "short"|"long"}

    Returns:
        {"net_delta": float, "net_gamma": float, "net_theta": float,
         "net_vega": float, "delta_dollars": float,
         "daily_theta_income": float, "gamma_risk_1pct": float,
         "vega_risk_1vol": float}
        or None on failure.
    """
    try:
        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0
        delta_dollars = 0.0
        daily_theta = 0.0
        gamma_risk = 0.0
        vega_risk = 0.0

        for pos in positions:
            contracts = pos.get("contracts", 0)
            side_mult = -1.0 if pos.get("side") == "short" else 1.0
            multiplier = contracts * side_mult

            d = pos.get("delta", 0) * multiplier
            g = pos.get("gamma", 0) * multiplier
            t = pos.get("theta", 0) * multiplier
            v = pos.get("vega", 0) * multiplier
            price = pos.get("price", 0)

            net_delta += d
            net_gamma += g
            net_theta += t
            net_vega += v

            # Dollar-weighted metrics (100 shares per contract)
            delta_dollars += d * price * 100
            daily_theta += t * 100  # theta is per-share per-day
            gamma_risk += g * price * 0.01 * 100  # P&L from 1% underlying move
            vega_risk += v * 100  # P&L from 1 vol point change

        return {
            "net_delta": round(net_delta, 4),
            "net_gamma": round(net_gamma, 4),
            "net_theta": round(net_theta, 4),
            "net_vega": round(net_vega, 4),
            "delta_dollars": round(delta_dollars, 2),
            "daily_theta_income": round(daily_theta, 2),
            "gamma_risk_1pct": round(gamma_risk, 2),
            "vega_risk_1vol": round(vega_risk, 2),
        }
    except Exception:
        return None


# ============================================================
# 2. Value at Risk (VaR)
# ============================================================

def calculate_var(
    tickers: list[str],
    portfolio_value: float = 100000,
    confidence: float = 0.95,
    days: int = 1,
) -> dict | None:
    """Calculate portfolio VaR using historical simulation.

    Downloads 1 year of daily returns for the given tickers (equal-weighted)
    and computes the historical VaR at the specified confidence level.

    Args:
        tickers: List of ticker symbols in the portfolio.
        portfolio_value: Total portfolio value in dollars.
        confidence: Confidence level (e.g. 0.95 for 95% VaR).
        days: Holding period in days.

    Returns:
        {"var_1day": float, "var_1week": float, "var_pct": float,
         "cvar": float, "worst_day": float, "best_day": float,
         "lookback_days": int}
        or None on failure.
    """
    try:
        # Fetch 1 year of daily close prices
        prices_df = yf.download(tickers, period="1y", progress=False)["Close"]
        if isinstance(prices_df, pd.Series):
            prices_df = prices_df.to_frame()

        prices_df = prices_df.dropna(how="all")
        if prices_df.empty or len(prices_df) < 30:
            return None

        # Equal-weighted portfolio returns
        daily_returns = prices_df.pct_change().dropna()
        portfolio_returns = daily_returns.mean(axis=1)  # equal weight across tickers
        lookback = len(portfolio_returns)

        # Historical VaR: the (1-confidence) percentile of returns
        var_pct_1day = float(np.percentile(portfolio_returns, (1 - confidence) * 100))
        var_1day = abs(var_pct_1day * portfolio_value)

        # Scale to 1-week using square-root-of-time rule
        var_1week = var_1day * math.sqrt(5)

        # Conditional VaR (Expected Shortfall): average of returns below VaR
        tail_returns = portfolio_returns[portfolio_returns <= var_pct_1day]
        cvar_pct = float(tail_returns.mean()) if len(tail_returns) > 0 else var_pct_1day
        cvar = abs(cvar_pct * portfolio_value)

        worst_day = float(portfolio_returns.min()) * 100
        best_day = float(portfolio_returns.max()) * 100

        return {
            "var_1day": round(var_1day, 2),
            "var_1week": round(var_1week, 2),
            "var_pct": round(abs(var_pct_1day) * 100, 2),
            "cvar": round(cvar, 2),
            "worst_day": round(worst_day, 2),
            "best_day": round(best_day, 2),
            "lookback_days": lookback,
        }
    except Exception:
        return None


# ============================================================
# 3. Correlation-Adjusted Sizing
# ============================================================

def correlation_adjusted_size(
    tickers: list[str],
    base_contracts: dict,
    max_portfolio_delta: float = 500,
) -> dict:
    """Adjust position sizes based on inter-ticker correlation.

    Highly correlated tickers get reduced sizing to avoid concentration.
    Uses 6-month daily returns for correlation estimation.

    Args:
        tickers: List of ticker symbols.
        base_contracts: Dict mapping ticker -> desired number of contracts.
        max_portfolio_delta: Maximum aggregate portfolio delta.

    Returns:
        {"adjusted_contracts": dict[str, int],
         "correlation_matrix": dict,
         "portfolio_beta": float,
         "diversification_benefit": float}
    """
    try:
        if not tickers or not base_contracts:
            return {
                "adjusted_contracts": base_contracts or {},
                "correlation_matrix": {},
                "portfolio_beta": 0.0,
                "diversification_benefit": 0.0,
            }

        # Fetch 6 months of prices
        all_tickers = list(set(tickers + ["SPY"]))
        prices = yf.download(all_tickers, period="6mo", progress=False)["Close"]
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()
        prices = prices.dropna(how="all")

        returns = prices.pct_change().dropna()

        # Correlation matrix (only for requested tickers)
        available = [t for t in tickers if t in returns.columns]
        if not available:
            return {
                "adjusted_contracts": base_contracts,
                "correlation_matrix": {},
                "portfolio_beta": 0.0,
                "diversification_benefit": 0.0,
            }

        corr_matrix = returns[available].corr()
        corr_dict = {
            t: {t2: round(corr_matrix.loc[t, t2], 3) for t2 in available}
            for t in available
        }

        # Adjust contracts: penalize highly correlated positions
        adjusted: dict[str, int] = {}
        for ticker in available:
            base = base_contracts.get(ticker, 0)
            # Average pairwise correlation with other held tickers
            others = [t2 for t2 in available if t2 != ticker]
            if others:
                avg_corr = float(
                    np.mean([abs(corr_matrix.loc[ticker, t2]) for t2 in others])
                )
                # Reduce size proportionally to correlation (high corr = more reduction)
                # Scale: corr=0 -> 1.0x, corr=1.0 -> 0.5x
                scale_factor = 1.0 - 0.5 * avg_corr
            else:
                scale_factor = 1.0
            adjusted[ticker] = max(1, round(base * scale_factor))

        # Portfolio beta vs SPY
        portfolio_beta = 0.0
        if "SPY" in returns.columns:
            spy_var = float(returns["SPY"].var())
            if spy_var > 0:
                betas = []
                for t in available:
                    cov = float(returns[[t, "SPY"]].cov().loc[t, "SPY"])
                    betas.append(cov / spy_var)
                portfolio_beta = round(float(np.mean(betas)), 3)

        # Diversification benefit: ratio of portfolio vol to avg individual vol
        if len(available) >= 2:
            individual_vols = [float(returns[t].std()) for t in available]
            avg_vol = float(np.mean(individual_vols))
            portfolio_vol = float(returns[available].mean(axis=1).std())
            div_benefit = round(
                (1 - portfolio_vol / avg_vol) * 100 if avg_vol > 0 else 0, 1
            )
        else:
            div_benefit = 0.0

        return {
            "adjusted_contracts": adjusted,
            "correlation_matrix": corr_dict,
            "portfolio_beta": portfolio_beta,
            "diversification_benefit": div_benefit,
        }
    except Exception:
        return {
            "adjusted_contracts": base_contracts or {},
            "correlation_matrix": {},
            "portfolio_beta": 0.0,
            "diversification_benefit": 0.0,
        }


# ============================================================
# 4. Scenario Analysis
# ============================================================

def scenario_analysis(
    positions: list[dict],
    scenarios: list[float] = None,
) -> list[dict]:
    """Project P&L under various price move scenarios.

    Uses delta-gamma approximation:
        P&L ~ delta * dS + 0.5 * gamma * dS^2

    Args:
        positions: List of position dicts, each containing:
            {"symbol": str, "contracts": int, "delta": float, "gamma": float,
             "price": float, "side": "short"|"long"}
        scenarios: List of percentage moves to simulate.
            Default: [-10, -5, -3, -1, 0, 1, 3, 5, 10]

    Returns:
        List of dicts: {"move_pct": float, "estimated_pnl": float,
                        "new_portfolio_value": float}
    """
    try:
        if scenarios is None:
            scenarios = [-10, -5, -3, -1, 0, 1, 3, 5, 10]

        # Calculate current portfolio value from positions
        total_value = 0.0
        for pos in positions:
            price = pos.get("price", 0)
            contracts = pos.get("contracts", 0)
            total_value += price * contracts * 100

        results: list[dict] = []
        for move_pct in sorted(scenarios):
            total_pnl = 0.0
            for pos in positions:
                price = pos.get("price", 0)
                contracts = pos.get("contracts", 0)
                delta = pos.get("delta", 0)
                gamma = pos.get("gamma", 0)
                side_mult = -1.0 if pos.get("side") == "short" else 1.0

                # Dollar move in the underlying
                ds = price * (move_pct / 100)

                # Delta-gamma P&L approximation (per share)
                pnl_per_share = (delta * ds + 0.5 * gamma * ds ** 2) * side_mult
                pnl = pnl_per_share * contracts * 100
                total_pnl += pnl

            results.append({
                "move_pct": move_pct,
                "estimated_pnl": round(total_pnl, 2),
                "new_portfolio_value": round(total_value + total_pnl, 2),
            })

        return results
    except Exception:
        return []


# ============================================================
# 5. Tail Risk Assessment
# ============================================================

# Historical crash benchmarks (approximate peak-to-trough % drops)
_HISTORICAL_CRASHES = {
    "covid_crash_2020": {"start": "2020-02-19", "end": "2020-03-23", "label": "COVID Crash (2020)"},
    "bear_2022": {"start": "2022-01-03", "end": "2022-10-12", "label": "2022 Bear Market"},
}


def tail_risk_assessment(tickers: list[str]) -> dict | None:
    """Assess tail risk using historical extreme events.

    Downloads 2 years of data to compute worst-case drawdowns, then
    simulates the impact of historical crashes on the current portfolio.

    Args:
        tickers: List of ticker symbols.

    Returns:
        {"max_daily_loss_1y": float, "max_weekly_loss_1y": float,
         "covid_crash_impact": float, "2022_bear_impact": float,
         "current_risk_level": "low"|"medium"|"high",
         "stress_test_results": list[dict]}
        or None on failure.
    """
    try:
        prices = yf.download(tickers, period="2y", progress=False)["Close"]
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()
        prices = prices.dropna(how="all")
        if prices.empty or len(prices) < 30:
            return None

        # Equal-weighted portfolio
        portfolio = prices.mean(axis=1)
        daily_returns = portfolio.pct_change().dropna()

        # Recent 1-year stats
        one_year_ago = portfolio.index[-1] - pd.DateOffset(years=1)
        recent_returns = daily_returns[daily_returns.index >= one_year_ago]

        max_daily_loss = float(recent_returns.min()) * 100 if len(recent_returns) > 0 else 0
        weekly_returns = recent_returns.rolling(5).sum().dropna()
        max_weekly_loss = float(weekly_returns.min()) * 100 if len(weekly_returns) > 0 else 0

        # Stress test against historical crashes
        stress_results: list[dict] = []
        crash_impacts: dict[str, float] = {}

        for crash_key, crash_info in _HISTORICAL_CRASHES.items():
            try:
                crash_prices = yf.download(
                    tickers,
                    start=crash_info["start"],
                    end=crash_info["end"],
                    progress=False,
                )["Close"]
                if isinstance(crash_prices, pd.Series):
                    crash_prices = crash_prices.to_frame()
                crash_prices = crash_prices.dropna(how="all")

                if not crash_prices.empty and len(crash_prices) > 1:
                    crash_portfolio = crash_prices.mean(axis=1)
                    peak = float(crash_portfolio.iloc[0])
                    trough = float(crash_portfolio.min())
                    drawdown = ((trough - peak) / peak) * 100 if peak > 0 else 0
                else:
                    drawdown = 0
            except Exception:
                drawdown = 0

            crash_impacts[crash_key] = round(drawdown, 2)
            stress_results.append({
                "event": crash_info["label"],
                "drawdown_pct": round(drawdown, 2),
                "period": f"{crash_info['start']} to {crash_info['end']}",
            })

        # Current risk level based on recent volatility
        recent_vol = float(recent_returns.std()) * math.sqrt(252) * 100 if len(recent_returns) > 0 else 0
        if recent_vol > 35:
            risk_level = "high"
        elif recent_vol > 20:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "max_daily_loss_1y": round(max_daily_loss, 2),
            "max_weekly_loss_1y": round(max_weekly_loss, 2),
            "covid_crash_impact": crash_impacts.get("covid_crash_2020", 0),
            "2022_bear_impact": crash_impacts.get("bear_2022", 0),
            "current_risk_level": risk_level,
            "stress_test_results": stress_results,
        }
    except Exception:
        return None


# ============================================================
# 6. Beta-Weighted Delta
# ============================================================

def beta_weighted_delta(
    positions: list[dict],
    benchmark: str = "SPY",
) -> dict | None:
    """Normalize all positions to SPY-equivalent delta.

    Calculates each ticker's beta vs the benchmark and adjusts
    deltas to a common denominator for portfolio-level comparison.

    Args:
        positions: List of position dicts, each containing:
            {"symbol": str, "contracts": int, "delta": float,
             "price": float, "side": "short"|"long"}
        benchmark: Benchmark ticker for beta calculation (default "SPY").

    Returns:
        {"positions": list[dict with "beta", "beta_adjusted_delta"],
         "total_spy_equivalent_delta": float,
         "portfolio_beta": float}
        or None on failure.
    """
    try:
        # Collect unique symbols
        symbols = list({pos["symbol"] for pos in positions if pos.get("symbol")})
        all_tickers = list(set(symbols + [benchmark]))

        prices = yf.download(all_tickers, period="1y", progress=False)["Close"]
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()
        prices = prices.dropna(how="all")
        returns = prices.pct_change().dropna()

        if benchmark not in returns.columns:
            return None

        bench_var = float(returns[benchmark].var())
        bench_price = float(prices[benchmark].iloc[-1]) if benchmark in prices.columns else 1.0

        # Calculate beta for each symbol
        betas: dict[str, float] = {}
        for sym in symbols:
            if sym in returns.columns and bench_var > 0:
                cov = float(returns[[sym, benchmark]].cov().loc[sym, benchmark])
                betas[sym] = round(cov / bench_var, 3)
            else:
                betas[sym] = 1.0  # Default beta if data unavailable

        # Compute beta-adjusted delta for each position
        result_positions: list[dict] = []
        total_spy_delta = 0.0
        weighted_betas: list[float] = []

        for pos in positions:
            symbol = pos.get("symbol", "")
            contracts = pos.get("contracts", 0)
            delta = pos.get("delta", 0)
            price = pos.get("price", 0)
            side_mult = -1.0 if pos.get("side") == "short" else 1.0

            beta = betas.get(symbol, 1.0)
            # Beta-adjusted delta: delta * beta * (ticker_price / benchmark_price)
            price_ratio = price / bench_price if bench_price > 0 else 1.0
            adj_delta = delta * side_mult * contracts * beta * price_ratio

            result_positions.append({
                **pos,
                "beta": beta,
                "beta_adjusted_delta": round(adj_delta, 4),
            })
            total_spy_delta += adj_delta
            weighted_betas.append(beta)

        portfolio_beta = round(float(np.mean(weighted_betas)), 3) if weighted_betas else 0.0

        return {
            "positions": result_positions,
            "total_spy_equivalent_delta": round(total_spy_delta, 4),
            "portfolio_beta": portfolio_beta,
        }
    except Exception:
        return None


# ============================================================
# 7. Buying Power Tracking
# ============================================================

def buying_power_estimate(
    positions: list[dict],
    account_value: float = 100000,
) -> dict:
    """Estimate buying power utilization.

    Calculates approximate margin requirements for common option
    position types (naked puts, spreads) and reports utilization.

    Args:
        positions: List of position dicts, each containing:
            {"symbol": str, "contracts": int, "strike": float,
             "price": float, "premium": float,
             "type": "naked_put"|"naked_call"|"spread",
             "spread_width": float (for spreads only)}
        account_value: Total account value in dollars.

    Returns:
        {"total_margin_used": float, "buying_power_remaining": float,
         "utilization_pct": float, "per_position": list[dict],
         "status": "healthy"|"warning"|"danger"}
    """
    try:
        per_position: list[dict] = []
        total_margin = 0.0

        for pos in positions:
            symbol = pos.get("symbol", "")
            contracts = pos.get("contracts", 0)
            strike = pos.get("strike", 0)
            underlying_price = pos.get("price", 0)
            premium = pos.get("premium", 0)
            pos_type = pos.get("type", "naked_put")
            spread_width = pos.get("spread_width", 0)

            if pos_type == "naked_put":
                # Naked put margin: 20% of underlying - OTM amount + premium
                otm_amount = max(strike - underlying_price, 0) if underlying_price > strike else 0
                margin_per = (
                    0.20 * underlying_price - otm_amount + premium
                ) * 100  # per contract
                margin_per = max(margin_per, premium * 100)  # minimum is the premium
            elif pos_type == "naked_call":
                # Naked call margin: similar to put but with call OTM logic
                otm_amount = max(underlying_price - strike, 0) if underlying_price < strike else 0
                margin_per = (
                    0.20 * underlying_price - otm_amount + premium
                ) * 100
                margin_per = max(margin_per, premium * 100)
            elif pos_type == "spread":
                # Spread margin: width of spread * 100
                margin_per = spread_width * 100
            else:
                # Default: conservative naked put estimate
                margin_per = 0.20 * underlying_price * 100

            position_margin = margin_per * contracts
            total_margin += position_margin

            per_position.append({
                "symbol": symbol,
                "type": pos_type,
                "contracts": contracts,
                "margin_required": round(position_margin, 2),
            })

        remaining = account_value - total_margin
        utilization = (total_margin / account_value * 100) if account_value > 0 else 0

        # Status thresholds
        if utilization >= 75:
            status = "danger"
        elif utilization >= 50:
            status = "warning"
        else:
            status = "healthy"

        return {
            "total_margin_used": round(total_margin, 2),
            "buying_power_remaining": round(remaining, 2),
            "utilization_pct": round(utilization, 1),
            "per_position": per_position,
            "status": status,
        }
    except Exception:
        return {
            "total_margin_used": 0.0,
            "buying_power_remaining": account_value,
            "utilization_pct": 0.0,
            "per_position": [],
            "status": "healthy",
        }
