"""
Data & Backtesting Module — v2.1
Historical database, backtesting, IV/HV divergence, correlation, portfolio Greeks, trade journal.
"""
import json
import csv
import os
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf


# ============================================================
# Configuration
# ============================================================
DB_PATH = Path(__file__).parent / "reports" / "history.db"


# ============================================================
# 1. Historical Report Database
# ============================================================
def init_db() -> sqlite3.Connection:
    """Initialize SQLite database for historical data.

    Creates the reports directory and tables if they don't exist.
    Returns an open connection to the database.
    """
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                strike REAL NOT NULL,
                premium_bid REAL,
                iv REAL,
                delta REAL,
                cp_score REAL,
                pop REAL,
                expiry_date TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL,
                avg_iv REAL,
                iv_percentile REAL,
                pc_ratio REAL,
                max_pain REAL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS strategy_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL UNIQUE,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                avg_return REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                last_updated TEXT
            )
        """)

        conn.commit()
        return conn
    except Exception as e:
        raise RuntimeError(f"Failed to initialize database: {e}") from e


def save_trade_recommendations(report_date: str, tickers: list[str], all_results: list) -> None:
    """Save today's recommended trades to the database.

    Args:
        report_date: Date string in YYYY-MM-DD format.
        tickers: List of ticker symbols.
        all_results: List of result dicts from analyze_ticker(), each containing
                     'symbol', 'price', 'data', and 'expiries' with sell_puts/sell_calls.
    """
    try:
        conn = init_db()
        cur = conn.cursor()

        for result in all_results:
            symbol = result.get("symbol", "")
            for expiry_info in result.get("expiries", []):
                exp_date = expiry_info.get("date", "")

                # Save sell put trades
                for entry in expiry_info.get("sell_puts", []):
                    cur.execute("""
                        INSERT INTO trades (date, symbol, strategy, strike, premium_bid,
                                            iv, delta, cp_score, pop, expiry_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        report_date, symbol, "sell_put",
                        entry.get("strike", 0),
                        entry.get("bid", 0),
                        entry.get("iv", 0),
                        entry.get("delta", 0),
                        entry.get("cp", 0),
                        None,  # pop not always available
                        exp_date,
                    ))

                # Save sell call trades
                for entry in expiry_info.get("sell_calls", []):
                    cur.execute("""
                        INSERT INTO trades (date, symbol, strategy, strike, premium_bid,
                                            iv, delta, cp_score, pop, expiry_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        report_date, symbol, "sell_call",
                        entry.get("strike", 0),
                        entry.get("bid", 0),
                        entry.get("iv", 0),
                        entry.get("delta", 0),
                        entry.get("cp", 0),
                        None,
                        exp_date,
                    ))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[data_backtest] Error saving trade recommendations: {e}")


def get_historical_trades(symbol: str = None, days: int = 30) -> pd.DataFrame:
    """Retrieve historical trade recommendations.

    Args:
        symbol: Optional ticker symbol to filter by.
        days: Number of days to look back (default 30).

    Returns:
        DataFrame with columns matching the trades table schema.
    """
    try:
        conn = init_db()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        if symbol:
            query = "SELECT * FROM trades WHERE symbol = ? AND date >= ? ORDER BY date DESC"
            df = pd.read_sql_query(query, conn, params=(symbol.upper(), cutoff))
        else:
            query = "SELECT * FROM trades WHERE date >= ? ORDER BY date DESC"
            df = pd.read_sql_query(query, conn, params=(cutoff,))

        conn.close()
        return df
    except Exception as e:
        print(f"[data_backtest] Error retrieving historical trades: {e}")
        return pd.DataFrame()


# ============================================================
# 2. Backtest Engine
# ============================================================
def backtest_trade(
    symbol: str,
    entry_date: str,
    strike: float,
    premium: float,
    expiry_date: str,
    strategy: str = "sell_put",
) -> dict | None:
    """Backtest a single historical trade.

    Fetches the stock price at expiry via yfinance and computes P&L.

    Args:
        symbol: Ticker symbol.
        entry_date: Entry date (YYYY-MM-DD).
        strike: Option strike price.
        premium: Premium received (bid).
        expiry_date: Option expiry date (YYYY-MM-DD).
        strategy: One of 'sell_put', 'sell_call', 'iron_condor', etc.

    Returns:
        Dict with backtest result or None on error.
    """
    try:
        exp_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
        # Fetch price around expiry (a few extra days in case of weekend/holiday)
        start = exp_dt - timedelta(days=3)
        end = exp_dt + timedelta(days=3)

        tk = yf.Ticker(symbol)
        hist = tk.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

        if hist.empty:
            return None

        # Get the closing price closest to (but not after) the expiry date
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        valid = hist[hist.index <= exp_dt]
        if valid.empty:
            # Fall back to the earliest available price after expiry
            expiry_price = float(hist["Close"].iloc[0])
        else:
            expiry_price = float(valid["Close"].iloc[-1])

        # Calculate P&L based on strategy
        if strategy == "sell_put":
            # Win if price >= strike at expiry
            if expiry_price >= strike:
                profit_loss = premium
                result = "win"
            else:
                profit_loss = premium - (strike - expiry_price)
                result = "loss" if profit_loss < 0 else "win"
        elif strategy == "sell_call":
            # Win if price <= strike at expiry
            if expiry_price <= strike:
                profit_loss = premium
                result = "win"
            else:
                profit_loss = premium - (expiry_price - strike)
                result = "loss" if profit_loss < 0 else "win"
        else:
            # Generic: treat premium as max profit, no loss calc for complex strategies
            profit_loss = premium
            result = "win"

        # Return percentage based on capital at risk
        if strategy == "sell_put":
            capital = strike * 100  # cash-secured put
        elif strategy == "sell_call":
            capital = expiry_price * 100  # approximate
        else:
            capital = strike * 100

        return_pct = (profit_loss / (capital / 100)) * 100 if capital > 0 else 0.0

        return {
            "symbol": symbol,
            "strategy": strategy,
            "entry_date": entry_date,
            "expiry_date": expiry_date,
            "strike": strike,
            "premium": premium,
            "expiry_price": round(expiry_price, 2),
            "profit_loss": round(profit_loss, 2),
            "result": result,
            "return_pct": round(return_pct, 2),
        }
    except Exception as e:
        print(f"[data_backtest] Error backtesting {symbol}: {e}")
        return None


def calculate_strategy_stats(trades: list[dict]) -> dict:
    """Calculate win rate and statistics from backtest results.

    Args:
        trades: List of dicts from backtest_trade().

    Returns:
        Dict with aggregate statistics.
    """
    try:
        if not trades:
            return {
                "total": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                "avg_profit": 0.0, "avg_loss": 0.0, "profit_factor": 0.0,
                "max_win": 0.0, "max_loss": 0.0, "expectancy": 0.0,
            }

        wins = [t for t in trades if t.get("result") == "win"]
        losses = [t for t in trades if t.get("result") == "loss"]

        total = len(trades)
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = n_wins / total * 100 if total > 0 else 0.0

        profits = [t["profit_loss"] for t in wins]
        loss_amounts = [t["profit_loss"] for t in losses]

        avg_profit = sum(profits) / len(profits) if profits else 0.0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0.0

        total_profit = sum(profits)
        total_loss = abs(sum(loss_amounts))
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        max_win = max(profits) if profits else 0.0
        max_loss = min(loss_amounts) if loss_amounts else 0.0

        # Expectancy = (win_rate * avg_profit) + (loss_rate * avg_loss)
        loss_rate = n_losses / total if total > 0 else 0.0
        expectancy = (win_rate / 100 * avg_profit) + (loss_rate * avg_loss)

        return {
            "total": total,
            "wins": n_wins,
            "losses": n_losses,
            "win_rate": round(win_rate, 2),
            "avg_profit": round(avg_profit, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.99,
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "expectancy": round(expectancy, 2),
        }
    except Exception as e:
        print(f"[data_backtest] Error calculating strategy stats: {e}")
        return {
            "total": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "avg_profit": 0.0, "avg_loss": 0.0, "profit_factor": 0.0,
            "max_win": 0.0, "max_loss": 0.0, "expectancy": 0.0,
        }


# ============================================================
# 3. IV vs HV Divergence
# ============================================================
def iv_hv_divergence(symbol: str, current_avg_iv: float) -> dict | None:
    """Compare implied volatility vs realized (historical) volatility.

    Args:
        symbol: Ticker symbol.
        current_avg_iv: Current average IV from option chains (in %, e.g. 45.0).

    Returns:
        Dict with IV/HV comparison or None on error.
    """
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period="3mo")

        if hist.empty or len(hist) < 30:
            return None

        daily_returns = hist["Close"].pct_change().dropna()

        # 20-day historical volatility (annualized)
        hv_20d = float(daily_returns.tail(20).std() * np.sqrt(252) * 100)

        # 30-day historical volatility (annualized)
        hv_30d = float(daily_returns.tail(30).std() * np.sqrt(252) * 100)

        # IV/HV ratio
        iv_hv_ratio = current_avg_iv / hv_30d if hv_30d > 0 else 0.0

        # Divergence percentage
        divergence_pct = ((current_avg_iv - hv_30d) / hv_30d * 100) if hv_30d > 0 else 0.0

        # Signal determination
        if iv_hv_ratio > 1.2:
            signal = "IV Premium (Sell)"
            description = (
                f"IV ({current_avg_iv:.1f}%) is significantly higher than HV "
                f"({hv_30d:.1f}%). Options are overpriced — favorable for selling premium."
            )
        elif iv_hv_ratio < 0.8:
            signal = "IV Discount (Buy)"
            description = (
                f"IV ({current_avg_iv:.1f}%) is significantly lower than HV "
                f"({hv_30d:.1f}%). Options are underpriced — consider buying strategies."
            )
        else:
            signal = "Neutral"
            description = (
                f"IV ({current_avg_iv:.1f}%) is in line with HV "
                f"({hv_30d:.1f}%). No strong divergence signal."
            )

        return {
            "symbol": symbol,
            "current_iv": round(current_avg_iv, 2),
            "hv_20d": round(hv_20d, 2),
            "hv_30d": round(hv_30d, 2),
            "iv_hv_ratio": round(iv_hv_ratio, 2),
            "divergence_pct": round(divergence_pct, 2),
            "signal": signal,
            "description": description,
        }
    except Exception as e:
        print(f"[data_backtest] Error computing IV/HV divergence for {symbol}: {e}")
        return None


# ============================================================
# 4. Correlation Matrix
# ============================================================
def correlation_matrix(tickers: list[str], period: str = "3mo") -> dict | None:
    """Calculate price correlation matrix between tickers.

    Args:
        tickers: List of ticker symbols (at least 2).
        period: yfinance period string (default '3mo').

    Returns:
        Dict with correlation matrix, high-correlation pairs, and
        diversification score, or None on error.
    """
    try:
        if len(tickers) < 2:
            return None

        # Download historical closes for all tickers
        data = yf.download(tickers, period=period, progress=False)
        if data.empty:
            return None

        # Handle multi-level columns from yf.download
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data

        # Drop tickers with no data
        closes = closes.dropna(axis=1, how="all")
        if closes.shape[1] < 2:
            return None

        # Daily returns correlation
        returns = closes.pct_change().dropna()
        corr = returns.corr()

        # Convert to nested dict
        matrix = {}
        for t1 in corr.columns:
            matrix[t1] = {}
            for t2 in corr.columns:
                matrix[t1][t2] = round(float(corr.loc[t1, t2]), 4)

        # Find high-correlation pairs (|corr| > 0.7, excluding self-pairs)
        high_corr_pairs = []
        seen = set()
        for t1 in corr.columns:
            for t2 in corr.columns:
                if t1 >= t2:
                    continue
                pair_key = (t1, t2)
                if pair_key not in seen:
                    seen.add(pair_key)
                    val = float(corr.loc[t1, t2])
                    if abs(val) > 0.7:
                        high_corr_pairs.append((t1, t2, round(val, 4)))

        # Diversification score: 1 - average |correlation| (excluding diagonal)
        n = len(corr.columns)
        if n > 1:
            abs_corr_sum = 0.0
            count = 0
            for t1 in corr.columns:
                for t2 in corr.columns:
                    if t1 != t2:
                        abs_corr_sum += abs(float(corr.loc[t1, t2]))
                        count += 1
            avg_abs_corr = abs_corr_sum / count if count > 0 else 0.0
            diversification_score = round(1 - avg_abs_corr, 4)
        else:
            diversification_score = 0.0

        return {
            "matrix": matrix,
            "high_corr_pairs": high_corr_pairs,
            "diversification_score": diversification_score,
        }
    except Exception as e:
        print(f"[data_backtest] Error computing correlation matrix: {e}")
        return None


# ============================================================
# 5. Portfolio Greeks Aggregation
# ============================================================
def aggregate_portfolio_greeks(positions: list[dict]) -> dict:
    """Aggregate Greeks across multiple positions.

    Args:
        positions: List of dicts, each with keys:
            - symbol (str): Ticker symbol
            - contracts (int): Number of contracts (positive = long, negative = sold)
            - delta (float): Per-contract delta
            - gamma (float): Per-contract gamma
            - theta (float): Per-contract theta
            - vega (float): Per-contract vega
            - type ('put' | 'call'): Option type

    Returns:
        Dict with aggregated portfolio Greeks and risk summary.
    """
    try:
        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0

        for pos in positions:
            contracts = pos.get("contracts", 0)
            multiplier = 100  # standard options multiplier

            # For sold options (negative contracts), Greeks are already negated by sign
            pos_delta = pos.get("delta", 0.0) * contracts * multiplier
            pos_gamma = pos.get("gamma", 0.0) * contracts * multiplier
            pos_theta = pos.get("theta", 0.0) * contracts * multiplier
            pos_vega = pos.get("vega", 0.0) * contracts * multiplier

            net_delta += pos_delta
            net_gamma += pos_gamma
            net_theta += pos_theta
            net_vega += pos_vega

        # Delta dollars: approximate dollar move per $1 move in underlying
        delta_dollars = round(net_delta, 2)

        # Theta dollars per day
        theta_dollars_per_day = round(net_theta, 2)

        # Risk summary
        risk_parts = []
        if abs(net_delta) > 500:
            direction = "bullish" if net_delta > 0 else "bearish"
            risk_parts.append(f"High directional exposure ({direction})")
        if abs(net_gamma) > 100:
            risk_parts.append("High gamma risk — large delta swings possible")
        if net_vega > 200:
            risk_parts.append("Long volatility — benefits from IV increase")
        elif net_vega < -200:
            risk_parts.append("Short volatility — benefits from IV decrease")
        if net_theta > 0:
            risk_parts.append(f"Positive theta: earning ~${net_theta:.0f}/day from time decay")
        elif net_theta < 0:
            risk_parts.append(f"Negative theta: losing ~${abs(net_theta):.0f}/day to time decay")

        risk_summary = "; ".join(risk_parts) if risk_parts else "Portfolio Greeks within normal range"

        return {
            "net_delta": round(net_delta, 4),
            "net_gamma": round(net_gamma, 4),
            "net_theta": round(net_theta, 4),
            "net_vega": round(net_vega, 4),
            "delta_dollars": delta_dollars,
            "theta_dollars_per_day": theta_dollars_per_day,
            "risk_summary": risk_summary,
        }
    except Exception as e:
        print(f"[data_backtest] Error aggregating portfolio Greeks: {e}")
        return {
            "net_delta": 0.0, "net_gamma": 0.0, "net_theta": 0.0, "net_vega": 0.0,
            "delta_dollars": 0.0, "theta_dollars_per_day": 0.0,
            "risk_summary": "Error computing Greeks",
        }


# ============================================================
# 6. Trade Journal Export
# ============================================================
def export_trade_journal(
    report_date: str,
    all_results: list,
    output_dir: Path,
) -> str | None:
    """Export today's recommended trades as CSV.

    Args:
        report_date: Date string (YYYY-MM-DD).
        all_results: List of result dicts from analyze_ticker().
        output_dir: Directory to write the CSV file.

    Returns:
        Path to the created CSV file, or None on error.
    """
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"trade_journal_{report_date}.csv"

        rows = []
        for result in all_results:
            symbol = result.get("symbol", "")
            price = result.get("price", 0)

            for expiry_info in result.get("expiries", []):
                exp_date = expiry_info.get("date", "")
                days = expiry_info.get("days", 0)

                # Sell puts
                for entry in expiry_info.get("sell_puts", []):
                    otm_pct = entry.get("otm_pct", 0)
                    annualized = entry.get("annualized", 0)
                    bid = entry.get("bid", 0)
                    ask = entry.get("ask", 0)
                    spread_quality = "Good" if ask > 0 and (ask - bid) / ask < 0.15 else "Wide"

                    rows.append({
                        "Date": report_date,
                        "Symbol": symbol,
                        "Strategy": "Sell Put",
                        "Strike": entry.get("strike", 0),
                        "OTM%": f"{otm_pct:+.1f}%",
                        "Premium": f"{bid:.2f}",
                        "IV": f"{entry.get('iv', 0):.1f}%",
                        "Delta": f"{entry.get('delta', 0):.4f}",
                        "CP Score": entry.get("cp", 0),
                        "POP": "",
                        "Annualized Return": f"{annualized:.1f}%",
                        "Expiry": exp_date,
                        "Spread Quality": spread_quality,
                    })

                # Sell calls
                for entry in expiry_info.get("sell_calls", []):
                    otm_pct = entry.get("otm_pct", 0)
                    annualized = entry.get("annualized", 0)
                    bid = entry.get("bid", 0)
                    ask = entry.get("ask", 0)
                    spread_quality = "Good" if ask > 0 and (ask - bid) / ask < 0.15 else "Wide"

                    rows.append({
                        "Date": report_date,
                        "Symbol": symbol,
                        "Strategy": "Sell Call",
                        "Strike": entry.get("strike", 0),
                        "OTM%": f"{otm_pct:+.1f}%",
                        "Premium": f"{bid:.2f}",
                        "IV": f"{entry.get('iv', 0):.1f}%",
                        "Delta": f"{entry.get('delta', 0):.4f}",
                        "CP Score": entry.get("cp", 0),
                        "POP": "",
                        "Annualized Return": f"{annualized:.1f}%",
                        "Expiry": exp_date,
                        "Spread Quality": spread_quality,
                    })

        if not rows:
            return None

        fieldnames = [
            "Date", "Symbol", "Strategy", "Strike", "OTM%", "Premium",
            "IV", "Delta", "CP Score", "POP", "Annualized Return",
            "Expiry", "Spread Quality",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return str(filepath)
    except Exception as e:
        print(f"[data_backtest] Error exporting trade journal: {e}")
        return None


def export_daily_summary_csv(
    report_date: str,
    all_results: list,
    output_dir: Path,
) -> str | None:
    """Export daily summary metrics as CSV row (append mode).

    One row per ticker per day: date, symbol, price, iv, iv_rank, pc_ratio, max_pain.

    Args:
        report_date: Date string (YYYY-MM-DD).
        all_results: List of result dicts from analyze_ticker().
        output_dir: Directory for the CSV file.

    Returns:
        Path to the CSV file, or None on error.
    """
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "daily_summary.csv"

        fieldnames = [
            "Date", "Symbol", "Price", "Avg IV", "IV Rank", "PC Ratio", "Max Pain",
        ]

        # Check if file exists to decide on header
        write_header = not filepath.exists()

        rows = []
        for result in all_results:
            symbol = result.get("symbol", "")
            price = result.get("price", 0)
            data = result.get("data", {})

            # Compute average IV across all expiries
            all_ivs = []
            for exp in result.get("expiries", []):
                for e in exp.get("sell_puts", []) + exp.get("sell_calls", []):
                    iv_val = e.get("iv", 0)
                    if iv_val > 0:
                        all_ivs.append(iv_val)
            avg_iv = sum(all_ivs) / len(all_ivs) if all_ivs else 0

            # IV rank from data
            iv_rank = ""
            iv_pct_data = data.get("iv_percentile_data")
            if iv_pct_data and avg_iv > 0:
                min_hv = iv_pct_data.get("min_hv", 0)
                max_hv = iv_pct_data.get("max_hv", 0)
                if max_hv > min_hv:
                    iv_rank = f"{max(0, min(100, (avg_iv - min_hv) / (max_hv - min_hv) * 100)):.0f}%"

            # PC ratio and max pain from options intelligence
            pc_ratio = data.get("pc_ratio")
            pc_ratio_str = f"{pc_ratio:.2f}" if isinstance(pc_ratio, (int, float)) else ""

            max_pain_data = data.get("max_pain")
            max_pain_str = ""
            if isinstance(max_pain_data, dict):
                max_pain_str = f"{max_pain_data.get('strike', '')}"
            elif isinstance(max_pain_data, (int, float)):
                max_pain_str = f"{max_pain_data:.2f}"

            rows.append({
                "Date": report_date,
                "Symbol": symbol,
                "Price": f"{price:.2f}",
                "Avg IV": f"{avg_iv:.1f}%",
                "IV Rank": iv_rank,
                "PC Ratio": pc_ratio_str,
                "Max Pain": max_pain_str,
            })

        if not rows:
            return None

        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

        return str(filepath)
    except Exception as e:
        print(f"[data_backtest] Error exporting daily summary: {e}")
        return None


# ============================================================
# 7. Strategy Win Rate
# ============================================================
def calculate_rolling_win_rates(days: int = 90) -> dict | None:
    """Calculate rolling win rates for each strategy type.

    Reads from the database, filters by date range, and backtests each
    expired trade to determine win/loss.

    Args:
        days: Look-back window in days (default 90).

    Returns:
        Dict keyed by strategy name with trades count, win_rate, and avg_return,
        or None on error.
    """
    try:
        conn = init_db()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        # Only consider trades whose expiry_date has passed
        query = """
            SELECT * FROM trades
            WHERE date >= ? AND expiry_date IS NOT NULL AND expiry_date <= ?
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(cutoff, today))
        conn.close()

        if df.empty:
            return {}

        # Group by strategy and backtest each trade
        strategies = df["strategy"].unique()
        results = {}

        for strat in strategies:
            strat_df = df[df["strategy"] == strat]
            backtest_results = []

            for _, row in strat_df.iterrows():
                bt = backtest_trade(
                    symbol=row["symbol"],
                    entry_date=row["date"],
                    strike=row["strike"],
                    premium=row["premium_bid"],
                    expiry_date=row["expiry_date"],
                    strategy=row["strategy"],
                )
                if bt is not None:
                    backtest_results.append(bt)

            if backtest_results:
                stats = calculate_strategy_stats(backtest_results)
                results[strat] = {
                    "trades": stats["total"],
                    "win_rate": stats["win_rate"],
                    "avg_return": stats["expectancy"],
                }
            else:
                results[strat] = {
                    "trades": 0,
                    "win_rate": 0.0,
                    "avg_return": 0.0,
                }

        return results
    except Exception as e:
        print(f"[data_backtest] Error calculating rolling win rates: {e}")
        return None
