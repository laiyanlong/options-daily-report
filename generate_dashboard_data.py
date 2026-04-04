"""
Generate dashboard/data.json for the Live Backtest Dashboard.
Reads from SQLite database (reports/history.db) and historical reports.
"""
import json
import sqlite3
import os
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import yfinance as yf

# Path to the SQLite database managed by data_backtest.py
DB_PATH = Path(__file__).resolve().parent.parent / "reports" / "history.db"


# ============================================================
# Sample data generator (used when DB is empty or missing)
# ============================================================
def generate_sample_data() -> dict:
    """Generate realistic sample data for dashboard demo."""
    random.seed(42)
    np.random.seed(42)

    tickers = ["TSLA", "AMZN", "NVDA"]
    strategies = ["sell_put", "sell_call"]
    today = datetime.now()

    trades: list[dict] = []
    trade_id = 1

    for ticker in tickers:
        # Assign a base price per ticker for realism
        base_prices = {"TSLA": 250.0, "AMZN": 185.0, "NVDA": 130.0}
        base_price = base_prices.get(ticker, 200.0)

        for strategy in strategies:
            # Win rates differ by strategy
            win_prob = 0.75 if strategy == "sell_put" else 0.70
            num_trades = random.randint(8, 12)

            for i in range(num_trades):
                # Spread trades over the last 60 trading days
                days_ago = random.randint(5, 60)
                entry_date = today - timedelta(days=days_ago)
                # Expiry 7-30 days after entry
                dte = random.choice([7, 14, 21, 30])
                expiry_date = entry_date + timedelta(days=dte)

                # Only backtest expired trades
                if expiry_date >= today:
                    continue

                # Random price movement
                price_at_entry = base_price * (1 + random.uniform(-0.08, 0.08))
                if strategy == "sell_put":
                    otm_pct = random.uniform(0.03, 0.08)
                    strike = round(price_at_entry * (1 - otm_pct), 2)
                else:
                    otm_pct = random.uniform(0.03, 0.08)
                    strike = round(price_at_entry * (1 + otm_pct), 2)

                premium = round(random.uniform(0.8, 4.5), 2)

                # Determine win/loss
                is_win = random.random() < win_prob
                if strategy == "sell_put":
                    if is_win:
                        expiry_price = round(strike + random.uniform(1, 20), 2)
                        pnl = premium
                    else:
                        breach = random.uniform(1, 15)
                        expiry_price = round(strike - breach, 2)
                        pnl = round(premium - breach, 2)
                else:  # sell_call
                    if is_win:
                        expiry_price = round(strike - random.uniform(1, 20), 2)
                        pnl = premium
                    else:
                        breach = random.uniform(1, 15)
                        expiry_price = round(strike + breach, 2)
                        pnl = round(premium - breach, 2)

                result = "win" if pnl >= 0 else "loss"

                # Calculate return percentage (per contract, capital = strike * 100)
                capital = strike * 100
                return_pct = round((pnl / (capital / 100)) * 100, 2) if capital > 0 else 0.0

                trades.append({
                    "id": trade_id,
                    "symbol": ticker,
                    "strategy": strategy,
                    "entry_date": entry_date.strftime("%Y-%m-%d"),
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "strike": strike,
                    "premium": premium,
                    "expiry_price": expiry_price,
                    "profit_loss": round(pnl, 2),
                    "result": result,
                    "return_pct": return_pct,
                })
                trade_id += 1

    # Also add a few iron condor sample trades
    for ticker in tickers:
        base_price = {"TSLA": 250.0, "AMZN": 185.0, "NVDA": 130.0}.get(ticker, 200.0)
        num_ic = random.randint(3, 5)
        for i in range(num_ic):
            days_ago = random.randint(10, 55)
            entry_date = today - timedelta(days=days_ago)
            dte = random.choice([14, 21, 30])
            expiry_date = entry_date + timedelta(days=dte)
            if expiry_date >= today:
                continue

            price_at_entry = base_price * (1 + random.uniform(-0.05, 0.05))
            short_put = round(price_at_entry * 0.93, 2)
            short_call = round(price_at_entry * 1.07, 2)
            premium = round(random.uniform(1.5, 5.0), 2)

            is_win = random.random() < 0.68
            if is_win:
                expiry_price = round(random.uniform(short_put + 1, short_call - 1), 2)
                pnl = premium
            else:
                # Breached one side
                if random.random() < 0.5:
                    breach = random.uniform(1, 10)
                    expiry_price = round(short_put - breach, 2)
                    pnl = round(premium - breach, 2)
                else:
                    breach = random.uniform(1, 10)
                    expiry_price = round(short_call + breach, 2)
                    pnl = round(premium - breach, 2)

            result = "win" if pnl >= 0 else "loss"
            capital = (short_call - short_put) * 100
            return_pct = round((pnl / (capital / 100)) * 100, 2) if capital > 0 else 0.0

            trades.append({
                "id": trade_id,
                "symbol": ticker,
                "strategy": "iron_condor",
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "strike": short_put,  # primary strike for display
                "premium": premium,
                "expiry_price": expiry_price,
                "profit_loss": round(pnl, 2),
                "result": result,
                "return_pct": return_pct,
                "short_put_strike": short_put,
                "short_call_strike": short_call,
            })
            trade_id += 1

    # Sort by entry_date
    trades.sort(key=lambda t: t["entry_date"])

    return _build_dashboard_payload(trades)


# ============================================================
# Core: build dashboard JSON payload from a list of trades
# ============================================================
def _build_dashboard_payload(trades: list[dict]) -> dict:
    """Build the full dashboard data.json structure from backtested trades."""
    if not trades:
        return _empty_payload()

    # --- Summary statistics ---
    total = len(trades)
    wins = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = n_wins / total * 100 if total > 0 else 0.0

    pnl_values = [t["profit_loss"] for t in trades]
    avg_return = sum(pnl_values) / total if total > 0 else 0.0

    total_profit = sum(t["profit_loss"] for t in wins)
    total_loss_abs = abs(sum(t["profit_loss"] for t in losses))
    profit_factor = total_profit / total_loss_abs if total_loss_abs > 0 else 999.99

    # Max drawdown from cumulative P&L
    cumulative = []
    running = 0.0
    for t in trades:
        running += t["profit_loss"]
        cumulative.append(running)
    peak = cumulative[0]
    max_drawdown = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_drawdown:
            max_drawdown = dd

    # Sharpe ratio (using per-trade returns as proxy for daily returns)
    returns_arr = np.array(pnl_values)
    if len(returns_arr) > 1 and np.std(returns_arr) > 0:
        sharpe = float(np.mean(returns_arr) / np.std(returns_arr) * np.sqrt(252))
    else:
        sharpe = 0.0

    # Sortino ratio (only downside deviation)
    downside = returns_arr[returns_arr < 0]
    if len(downside) > 1:
        downside_std = float(np.std(downside))
        sortino = float(np.mean(returns_arr) / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
    else:
        sortino = 0.0

    avg_win = float(np.mean([t["profit_loss"] for t in wins])) if wins else 0.0
    avg_loss = float(np.mean([t["profit_loss"] for t in losses])) if losses else 0.0

    summary = {
        "total_trades": total,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate": round(win_rate, 1),
        "avg_return": round(avg_return, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "total_pnl": round(sum(pnl_values), 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
    }

    # --- Cumulative P&L by strategy (format: {dates: [], sell_put: [], ...}) ---
    strategy_names = sorted(set(t["strategy"] for t in trades))
    # Collect all unique dates
    all_dates = sorted(set(t["entry_date"] for t in trades))

    # Build per-strategy cumulative P&L aligned to all_dates
    strat_running: dict[str, float] = {s: 0.0 for s in strategy_names}
    strat_pnl_by_date: dict[str, dict[str, float]] = {}
    for d in all_dates:
        for s in strategy_names:
            day_pnl = sum(t["profit_loss"] for t in trades if t["entry_date"] == d and t["strategy"] == s)
            strat_running[s] += day_pnl
        strat_pnl_by_date[d] = {s: round(strat_running[s], 2) for s in strategy_names}

    cumulative_pnl: dict = {"dates": all_dates}
    for s in strategy_names:
        cumulative_pnl[s] = [strat_pnl_by_date[d][s] for d in all_dates]

    # --- Monthly returns (format: {months: [], "Sell Put": [], ...}) ---
    monthly_by_strat: dict[str, dict[str, float]] = {s: {} for s in strategy_names}
    for t in trades:
        month_key = t["entry_date"][:7]
        s = t["strategy"]
        monthly_by_strat[s][month_key] = monthly_by_strat[s].get(month_key, 0.0) + t["profit_loss"]

    all_months = sorted(set(t["entry_date"][:7] for t in trades))
    monthly_returns: dict = {"months": all_months}
    for s in strategy_names:
        monthly_returns[s] = [round(monthly_by_strat[s].get(m, 0.0), 2) for m in all_months]

    # --- Per-ticker stats ---
    ticker_names = sorted(set(t["symbol"] for t in trades))
    ticker_stats: dict[str, dict] = {}
    for ticker in ticker_names:
        tk_trades = [t for t in trades if t["symbol"] == ticker]
        tk_wins = [t for t in tk_trades if t["result"] == "win"]
        tk_total = len(tk_trades)
        ticker_stats[ticker] = {
            "trades": tk_total,
            "wins": len(tk_wins),
            "losses": tk_total - len(tk_wins),
            "win_rate": round(len(tk_wins) / tk_total * 100, 1) if tk_total > 0 else 0.0,
            "total_pnl": round(sum(t["profit_loss"] for t in tk_trades), 2),
            "avg_return": round(sum(t["profit_loss"] for t in tk_trades) / tk_total, 2) if tk_total > 0 else 0.0,
        }

    # --- Per-strategy stats ---
    strategy_stats: dict[str, dict] = {}
    for strat in strategy_names:
        st_trades = [t for t in trades if t["strategy"] == strat]
        st_wins = [t for t in st_trades if t["result"] == "win"]
        st_total = len(st_trades)
        strategy_stats[strat] = {
            "trades": st_total,
            "wins": len(st_wins),
            "losses": st_total - len(st_wins),
            "win_rate": round(len(st_wins) / st_total * 100, 1) if st_total > 0 else 0.0,
            "total_pnl": round(sum(t["profit_loss"] for t in st_trades), 2),
            "avg_return": round(sum(t["profit_loss"] for t in st_trades) / st_total, 2) if st_total > 0 else 0.0,
        }

    # --- Recent trades (last 20, mapped to dashboard keys) ---
    sorted_recent = sorted(trades, key=lambda t: t["entry_date"], reverse=True)[:20]
    recent_trades = [
        {
            "date": t["entry_date"],
            "symbol": t["symbol"],
            "strategy": t["strategy"],
            "strike": t["strike"],
            "premium": t["premium"],
            "expiry": t["expiry_date"],
            "result": t["result"],
            "pnl": t["profit_loss"],
        }
        for t in sorted_recent
    ]

    return {
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "summary": summary,
        "cumulative_pnl": cumulative_pnl,
        "monthly_returns": monthly_returns,
        "ticker_stats": ticker_stats,
        "strategy_stats": strategy_stats,
        "recent_trades": recent_trades,
    }


def _empty_payload() -> dict:
    """Return an empty dashboard payload with zeroed-out fields."""
    return {
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "avg_return": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0,
            "sharpe_ratio": 0.0, "sortino_ratio": 0.0, "total_pnl": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0,
        },
        "cumulative_pnl": {"dates": [], "sell_put": [], "sell_call": [], "iron_condor": []},
        "monthly_returns": {"months": []},
        "ticker_stats": {},
        "strategy_stats": {},
        "recent_trades": [],
    }


# ============================================================
# Read trades from database and backtest expired ones
# ============================================================
def _fetch_and_backtest_trades() -> list[dict]:
    """Read all trades from the SQLite DB and backtest expired ones.

    Returns a list of trade dicts with backtest results (P&L, result, etc.).
    """
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Fetch only truly expired trades (expiry strictly before today)
    cur.execute("""
        SELECT id, date, symbol, strategy, strike, premium_bid, iv, delta,
               cp_score, pop, expiry_date
        FROM trades
        WHERE expiry_date IS NOT NULL AND expiry_date < ?
        ORDER BY date
    """, (today_str,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    trades: list[dict] = []

    # Cache yfinance price lookups to reduce API calls
    price_cache: dict[str, dict[str, float]] = {}

    for row in rows:
        symbol = row["symbol"]
        strategy = row["strategy"]
        strike = row["strike"]
        premium = row["premium_bid"] or 0.0
        entry_date = row["date"]
        expiry_date = row["expiry_date"]

        # Fetch expiry price (with caching)
        expiry_price = _get_expiry_price(symbol, expiry_date, price_cache)
        if expiry_price is None:
            continue

        # Determine win/loss and P&L
        if strategy == "sell_put":
            if expiry_price >= strike:
                pnl = premium
                result = "win"
            else:
                pnl = premium - (strike - expiry_price)
                result = "loss" if pnl < 0 else "win"
        elif strategy == "sell_call":
            if expiry_price <= strike:
                pnl = premium
                result = "win"
            else:
                pnl = premium - (expiry_price - strike)
                result = "loss" if pnl < 0 else "win"
        elif strategy == "iron_condor":
            # For iron condor, we'd need short_put and short_call strikes
            # The DB only stores a single strike, so treat it as premium capture
            pnl = premium
            result = "win"
        else:
            pnl = premium
            result = "win"

        # Return percentage
        capital = strike * 100 if strike > 0 else 1.0
        return_pct = round((pnl / (capital / 100)) * 100, 2) if capital > 0 else 0.0

        trades.append({
            "id": row["id"],
            "symbol": symbol,
            "strategy": strategy,
            "entry_date": entry_date,
            "expiry_date": expiry_date,
            "strike": strike,
            "premium": premium,
            "expiry_price": round(expiry_price, 2),
            "profit_loss": round(pnl, 2),
            "result": result,
            "return_pct": return_pct,
        })

    return trades


def _get_expiry_price(
    symbol: str,
    expiry_date: str,
    cache: dict[str, dict[str, float]],
) -> Optional[float]:
    """Fetch the closing price at or near the expiry date.

    Uses a cache dict to avoid redundant yfinance API calls for
    the same symbol/date combination.
    """
    cache_key = f"{symbol}_{expiry_date}"
    if cache_key in cache:
        return cache[cache_key].get("price")

    try:
        exp_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
        start = exp_dt - timedelta(days=3)
        end = exp_dt + timedelta(days=3)

        tk = yf.Ticker(symbol)
        hist = tk.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
        )

        if hist.empty:
            cache[cache_key] = {"price": None}
            return None

        # Normalize timezone
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index

        valid = hist[hist.index <= exp_dt]
        if valid.empty:
            price = float(hist["Close"].iloc[0])
        else:
            price = float(valid["Close"].iloc[-1])

        cache[cache_key] = {"price": price}
        return price
    except Exception as e:
        print(f"[dashboard] Error fetching price for {symbol} at {expiry_date}: {e}")
        cache[cache_key] = {"price": None}
        return None


# ============================================================
# Main entry point
# ============================================================
def generate_dashboard_data() -> dict:
    """Generate the full dashboard data payload.

    Reads from the SQLite database and backtests expired trades.
    Falls back to sample data if the DB is empty or missing.

    Returns:
        Dict matching the dashboard data.json schema.
    """
    trades = _fetch_and_backtest_trades()

    # Need at least 10 backtested trades across multiple days for meaningful stats
    unique_dates = set(t["entry_date"] for t in trades) if trades else set()
    if trades and len(trades) >= 10 and len(unique_dates) >= 3:
        print(f"[dashboard] Found {len(trades)} expired trades across {len(unique_dates)} days.")
        return _build_dashboard_payload(trades)
    else:
        reason = f"only {len(trades)} trades across {len(unique_dates)} days" if trades else "no expired trades yet"
        print(f"[dashboard] Insufficient real data ({reason}) — using sample data for demo.")
        return generate_sample_data()


def _fetch_live_prices(tickers: list[str] = None) -> list[dict]:
    """Fetch current stock prices via yfinance (server-side, no CORS issues)."""
    if tickers is None:
        tickers = ["TSLA", "AMZN", "NVDA", "SPY"]
    prices = []
    for sym in tickers:
        try:
            tk = yf.Ticker(sym)
            info = tk.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
            prev = info.get("previousClose") or info.get("regularMarketPreviousClose", price)
            change = price - prev if prev else 0
            change_pct = (change / prev * 100) if prev else 0

            # Get intraday data for mini chart
            hist = tk.history(period="1d", interval="5m")
            intraday_prices = hist["Close"].dropna().tolist()[-50:] if not hist.empty else []
            intraday_times = [t.strftime("%H:%M") for t in hist.index[-50:]] if not hist.empty else []

            prices.append({
                "symbol": sym,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "high": round(info.get("regularMarketDayHigh", info.get("dayHigh", 0)) or 0, 2),
                "low": round(info.get("regularMarketDayLow", info.get("dayLow", 0)) or 0, 2),
                "volume": info.get("regularMarketVolume", info.get("volume", 0)) or 0,
                "market_state": info.get("marketState", "CLOSED"),
                "intraday_prices": [round(p, 2) for p in intraday_prices],
                "intraday_times": intraday_times,
            })
        except Exception as e:
            print(f"  Warning: failed to fetch {sym}: {e}")
    return prices


def _fetch_strike_comparison(tickers: list[str] = None) -> list[dict]:
    """Fetch current options chain and build strike comparison data."""
    if tickers is None:
        tickers = ["TSLA", "AMZN", "NVDA"]
    strikes = []
    for sym in tickers:
        try:
            tk = yf.Ticker(sym)
            info = tk.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            if not price:
                continue

            expiries = tk.options
            # Skip expiries < 5 DTE
            valid_expiries = []
            for exp in expiries:
                dte = (datetime.strptime(exp, "%Y-%m-%d") - datetime.now()).days
                if dte >= 5:
                    valid_expiries.append(exp)
                if len(valid_expiries) >= 3:
                    break

            for exp in valid_expiries:
                chain = tk.option_chain(exp)
                dte = (datetime.strptime(exp, "%Y-%m-%d") - datetime.now()).days

                # Sell Puts: 5-10% OTM
                for pct in [5, 7, 10]:
                    target = price * (1 - pct / 100)
                    puts = chain.puts
                    if puts.empty:
                        continue
                    closest_idx = (puts["strike"] - target).abs().idxmin()
                    row = puts.loc[closest_idx]
                    bid = float(row.get("bid", 0) or 0)
                    if bid < 1.0 or bid > 7.0:
                        continue
                    iv = float(row.get("impliedVolatility", 0) or 0) * 100
                    strike_val = float(row["strike"])
                    otm = round((strike_val - price) / price * 100, 1)
                    ann = round(bid / strike_val * 365 / max(dte, 1) * 100, 1) if strike_val > 0 else 0

                    strikes.append({
                        "symbol": sym,
                        "strategy": "sell_put",
                        "strike": round(strike_val, 2),
                        "premium": round(bid, 2),
                        "iv": round(iv, 1),
                        "otm_pct": otm,
                        "dte": dte,
                        "expiry": exp,
                        "annualized": ann,
                    })
        except Exception as e:
            print(f"  Warning: failed to get options for {sym}: {e}")
    return strikes


def _fetch_options_matrix(symbol: str = "TSLA") -> dict:
    """Fetch options chain for a symbol and build a full matrix: same expiry, multiple strikes."""
    import math
    from scipy.stats import norm

    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        if not price:
            return {}

        r = 0.05  # risk-free rate

        expiries = tk.options
        result = {"price": round(price, 2), "expiries": []}

        for exp in expiries:
            dte = (datetime.strptime(exp, "%Y-%m-%d") - datetime.now()).days
            if dte < 5 or dte > 60:
                continue

            chain = tk.option_chain(exp)

            # --- Puts matrix ---
            puts = chain.puts
            if puts.empty:
                continue

            # Filter: 3-15% OTM, bid >= $0.50
            otm_puts = puts[
                (puts["strike"] >= price * 0.85)
                & (puts["strike"] <= price * 0.97)
                & (puts["bid"] >= 0.50)
            ].copy()

            if otm_puts.empty:
                continue

            put_rows = []
            for _, row in otm_puts.iterrows():
                strike = float(row["strike"])
                bid = float(row.get("bid", 0) or 0)
                ask = float(row.get("ask", 0) or 0)
                iv = float(row.get("impliedVolatility", 0) or 0) * 100
                oi = int(row.get("openInterest", 0) or 0)
                vol = int(row.get("volume", 0) or 0)
                otm_pct = round((strike - price) / price * 100, 2)
                mid = round((bid + ask) / 2, 2) if ask > 0 else bid
                spread_pct = round((ask - bid) / mid * 100, 1) if mid > 0 else 999

                # Annualized return
                ann = round(bid / strike * 365 / max(dte, 1) * 100, 1) if strike > 0 else 0

                # POP via Black-Scholes
                pop = 50.0
                try:
                    if iv > 0 and dte > 0:
                        T = dte / 365.0
                        sigma = iv / 100.0
                        d2 = (math.log(price / strike) + (r - 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                        pop = round(norm.cdf(d2) * 100, 1)
                except Exception:
                    pass

                # Delta estimate
                delta = 0.0
                try:
                    if iv > 0 and dte > 0:
                        T = dte / 365.0
                        sigma = iv / 100.0
                        d1 = (math.log(price / strike) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                        delta = round(norm.cdf(d1) - 1, 4)
                except Exception:
                    pass

                # Spread quality
                if spread_pct < 5:
                    spread_q = "Excellent"
                elif spread_pct < 10:
                    spread_q = "Good"
                elif spread_pct < 20:
                    spread_q = "Fair"
                else:
                    spread_q = "Poor"

                put_rows.append({
                    "strike": round(strike, 2),
                    "otm_pct": otm_pct,
                    "bid": round(bid, 2),
                    "ask": round(ask, 2),
                    "mid": mid,
                    "spread_pct": spread_pct,
                    "spread_quality": spread_q,
                    "iv": round(iv, 1),
                    "delta": delta,
                    "volume": vol,
                    "oi": oi,
                    "annualized": ann,
                    "pop": pop,
                })

            # Sort by strike descending (closest to ATM first)
            put_rows.sort(key=lambda x: x["strike"], reverse=True)

            # --- Calls matrix ---
            calls = chain.calls
            otm_calls = calls[
                (calls["strike"] >= price * 1.03)
                & (calls["strike"] <= price * 1.15)
                & (calls["bid"] >= 0.50)
            ].copy() if not calls.empty else puts.iloc[:0]

            call_rows = []
            for _, row in otm_calls.iterrows():
                strike = float(row["strike"])
                bid = float(row.get("bid", 0) or 0)
                ask = float(row.get("ask", 0) or 0)
                iv = float(row.get("impliedVolatility", 0) or 0) * 100
                oi = int(row.get("openInterest", 0) or 0)
                vol = int(row.get("volume", 0) or 0)
                otm_pct = round((strike - price) / price * 100, 2)
                mid = round((bid + ask) / 2, 2) if ask > 0 else bid
                spread_pct = round((ask - bid) / mid * 100, 1) if mid > 0 else 999
                ann = round(bid / strike * 365 / max(dte, 1) * 100, 1) if strike > 0 else 0

                pop = 50.0
                try:
                    if iv > 0 and dte > 0:
                        T = dte / 365.0
                        sigma = iv / 100.0
                        d2 = (math.log(price / strike) + (r - 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                        pop = round((1 - norm.cdf(d2)) * 100, 1)
                except Exception:
                    pass

                delta = 0.0
                try:
                    if iv > 0 and dte > 0:
                        T = dte / 365.0
                        sigma = iv / 100.0
                        d1 = (math.log(price / strike) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                        delta = round(norm.cdf(d1), 4)
                except Exception:
                    pass

                if spread_pct < 5:
                    spread_q = "Excellent"
                elif spread_pct < 10:
                    spread_q = "Good"
                elif spread_pct < 20:
                    spread_q = "Fair"
                else:
                    spread_q = "Poor"

                call_rows.append({
                    "strike": round(strike, 2),
                    "otm_pct": otm_pct,
                    "bid": round(bid, 2),
                    "ask": round(ask, 2),
                    "mid": mid,
                    "spread_pct": spread_pct,
                    "spread_quality": spread_q,
                    "iv": round(iv, 1),
                    "delta": delta,
                    "volume": vol,
                    "oi": oi,
                    "annualized": ann,
                    "pop": pop,
                })

            call_rows.sort(key=lambda x: x["strike"])

            result["expiries"].append({
                "date": exp,
                "dte": dte,
                "puts": put_rows,
                "calls": call_rows,
            })

            if len(result["expiries"]) >= 5:
                break

        return result
    except Exception as e:
        print(f"  Warning: {symbol} matrix failed: {e}")
        return {}


if __name__ == "__main__":
    data = generate_dashboard_data()

    # Add live prices (server-side fetch, no CORS)
    print("\nFetching live prices...")
    data["live_prices"] = _fetch_live_prices()
    for p in data["live_prices"]:
        sign = "+" if p["change"] >= 0 else ""
        print(f"  {p['symbol']}: ${p['price']} ({sign}{p['change_pct']:.2f}%)")

    # Add strike comparison from live options chain
    print("\nFetching strike comparison data...")
    data["strike_comparison"] = _fetch_strike_comparison()
    print(f"  {len(data['strike_comparison'])} strike entries")

    # Options Matrix for all tickers
    print("\nFetching options matrices...")
    options_matrices = {}
    for sym in ["TSLA", "AMZN", "NVDA"]:
        print(f"  Fetching {sym}...")
        matrix = _fetch_options_matrix(sym)
        if matrix and matrix.get("expiries"):
            options_matrices[sym] = matrix
            total_puts = sum(len(e["puts"]) for e in matrix["expiries"])
            total_calls = sum(len(e["calls"]) for e in matrix["expiries"])
            print(f"    ${matrix['price']}: {len(matrix['expiries'])} expiries, {total_puts} puts, {total_calls} calls")
        else:
            print(f"    No data")
    data["options_matrices"] = options_matrices
    # Keep tsla_matrix for backward compatibility
    data["tsla_matrix"] = options_matrices.get("TSLA", {})

    output = Path(__file__).parent / "data.json"
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nDashboard data written to {output}")
    print(f"Total trades: {data['summary']['total_trades']}")
    print(f"Win rate: {data['summary']['win_rate']:.1f}%")
