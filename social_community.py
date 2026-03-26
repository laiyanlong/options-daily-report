"""
Social & Community Module — v4.0
Sentiment analysis, portfolio import/export, strategy sharing, watchlist collaboration.
"""
import json
import csv
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PORTFOLIO_DIR = Path(__file__).parent / "config" / "portfolios"
STRATEGIES_DIR = Path(__file__).parent / "config" / "strategies"
LEADERBOARD_PATH = Path(__file__).parent / "config" / "leaderboard.json"
COLLAB_DIR = Path(__file__).parent / "config" / "collab_watchlists"
MARKETPLACE_DIR = Path(__file__).parent / "config" / "marketplace"

# Sentiment keyword lists
_BULLISH_WORDS = re.compile(
    r"\b(calls?|moon|buy|long|bull|bullish|rocket|tendies|yolo|rip|pump|green|upside)\b",
    re.IGNORECASE,
)
_BEARISH_WORDS = re.compile(
    r"\b(puts?|crash|sell|short|bear|bearish|dump|drill|red|downside|tank|fade)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# 1. Reddit Sentiment (public JSON API, no auth needed)
# ---------------------------------------------------------------------------

def reddit_options_sentiment(symbol: str) -> dict | None:
    """Fetch sentiment from Reddit r/options and r/wallstreetbets.

    Uses Reddit's public JSON API (no auth required):
        reddit.com/r/{sub}/search.json?q={symbol}&sort=new&limit=10

    Returns:
        {
            "symbol": str,
            "mentions": int,
            "bullish_count": int,
            "bearish_count": int,
            "neutral_count": int,
            "sentiment_score": float (-1 to 1),
            "sentiment_label": "Bullish" | "Bearish" | "Neutral",
            "top_posts": [{"title": str, "score": int, "sentiment": str}],
        }
    """
    try:
        subreddits = ["options", "wallstreetbets"]
        all_posts: list[dict] = []

        for sub in subreddits:
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={symbol}&sort=new&limit=10&restrict_sr=on"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "options-daily-report/4.0"},
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                # Handle 429 rate limits gracefully — skip this sub
                if exc.code == 429:
                    continue
                raise
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                all_posts.append(
                    {"title": post.get("title", ""), "score": post.get("score", 0)}
                )

        if not all_posts:
            return {
                "symbol": symbol,
                "mentions": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "top_posts": [],
            }

        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        top_posts: list[dict] = []

        for post in all_posts:
            title = post["title"]
            b = len(_BULLISH_WORDS.findall(title))
            s = len(_BEARISH_WORDS.findall(title))
            if b > s:
                sentiment = "Bullish"
                bullish_count += 1
            elif s > b:
                sentiment = "Bearish"
                bearish_count += 1
            else:
                sentiment = "Neutral"
                neutral_count += 1
            top_posts.append(
                {"title": title, "score": post["score"], "sentiment": sentiment}
            )

        total = bullish_count + bearish_count + neutral_count
        score = (bullish_count - bearish_count) / total if total else 0.0

        if score > 0.1:
            label = "Bullish"
        elif score < -0.1:
            label = "Bearish"
        else:
            label = "Neutral"

        # Sort by Reddit score descending and keep top 10
        top_posts.sort(key=lambda p: p["score"], reverse=True)
        top_posts = top_posts[:10]

        return {
            "symbol": symbol,
            "mentions": len(all_posts),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "sentiment_score": round(score, 4),
            "sentiment_label": label,
            "top_posts": top_posts,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 2. Portfolio Import / Export
# ---------------------------------------------------------------------------

def import_portfolio_csv(csv_path: str) -> list[dict] | None:
    """Import positions from broker CSV format.

    Supports common formats: IBKR, Schwab, generic.
    Expected columns (case-insensitive): Symbol, Quantity, Strike, Type (Put/Call),
    Expiry, AvgCost.

    Returns:
        List of {"symbol": str, "contracts": int, "strike": float,
                 "type": "put"|"call", "expiry": str, "avg_cost": float}
    """
    try:
        positions: list[dict] = []
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            # Normalise header names to lowercase
            if reader.fieldnames is None:
                return None
            col_map: dict[str, str] = {}
            canonical = {
                "symbol": "symbol",
                "ticker": "symbol",
                "quantity": "contracts",
                "qty": "contracts",
                "contracts": "contracts",
                "strike": "strike",
                "strikeprice": "strike",
                "type": "type",
                "putcall": "type",
                "put/call": "type",
                "option_type": "type",
                "expiry": "expiry",
                "expiration": "expiry",
                "expirydate": "expiry",
                "avgcost": "avg_cost",
                "avg_cost": "avg_cost",
                "averagecost": "avg_cost",
                "cost": "avg_cost",
                "price": "avg_cost",
            }
            for name in reader.fieldnames:
                key = re.sub(r"[\s_/]", "", name).lower()
                if key in canonical:
                    col_map[name] = canonical[key]

            for row in reader:
                mapped: dict[str, str] = {}
                for orig, canon in col_map.items():
                    mapped[canon] = row[orig]

                option_type = mapped.get("type", "").strip().lower()
                if option_type not in ("put", "call"):
                    # Try first character
                    if option_type.startswith("p"):
                        option_type = "put"
                    elif option_type.startswith("c"):
                        option_type = "call"
                    else:
                        option_type = "call"

                positions.append(
                    {
                        "symbol": mapped.get("symbol", "").strip().upper(),
                        "contracts": int(float(mapped.get("contracts", "0"))),
                        "strike": float(mapped.get("strike", "0")),
                        "type": option_type,
                        "expiry": mapped.get("expiry", "").strip(),
                        "avg_cost": float(mapped.get("avg_cost", "0")),
                    }
                )
        return positions
    except Exception:
        return None


def export_portfolio_csv(positions: list[dict], output_path: str) -> str | None:
    """Export current portfolio to CSV.

    Returns the output path on success, None on failure.
    """
    try:
        fieldnames = ["symbol", "contracts", "strike", "type", "expiry", "avg_cost"]
        parent = Path(output_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for pos in positions:
                writer.writerow({k: pos.get(k, "") for k in fieldnames})
        return output_path
    except Exception:
        return None


def save_portfolio(name: str, positions: list[dict]) -> str | None:
    """Save portfolio to JSON file.

    Returns the path to the saved file, or None on failure.
    """
    try:
        PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
        path = PORTFOLIO_DIR / f"{name}.json"
        payload = {
            "name": name,
            "updated_at": datetime.now().isoformat(),
            "positions": positions,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return None


def load_portfolio(name: str = "default") -> list[dict] | None:
    """Load saved portfolio by name.

    Returns list of position dicts, or None if not found / error.
    """
    try:
        path = PORTFOLIO_DIR / f"{name}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("positions", [])
    except Exception:
        return None


def list_portfolios() -> list[str]:
    """List all saved portfolio names."""
    try:
        if not PORTFOLIO_DIR.exists():
            return []
        return sorted(p.stem for p in PORTFOLIO_DIR.glob("*.json"))
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 3. Strategy Sharing
# ---------------------------------------------------------------------------

def export_strategy_config(strategy_name: str, config: dict) -> str:
    """Export a strategy configuration as shareable JSON.

    Args:
        strategy_name: Human-readable strategy name.
        config: {"tickers": list, "otm_pcts": list, "strategy_types": list,
                 "thresholds": dict, "description": str, "author": str}

    Returns:
        Path to saved JSON file, or empty string on failure.
    """
    try:
        STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]", "_", strategy_name)
        path = STRATEGIES_DIR / f"{safe_name}.json"
        payload = {
            "strategy_name": strategy_name,
            "exported_at": datetime.now().isoformat(),
            **config,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return ""


def import_strategy_config(json_path: str) -> dict | None:
    """Import a shared strategy configuration from a JSON file."""
    try:
        path = Path(json_path)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return None


def list_strategies() -> list[dict]:
    """List all saved strategy configs.

    Returns list of {"name": str, "file": str, "exported_at": str}.
    """
    try:
        if not STRATEGIES_DIR.exists():
            return []
        results: list[dict] = []
        for p in sorted(STRATEGIES_DIR.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                results.append(
                    {
                        "name": data.get("strategy_name", p.stem),
                        "file": str(p),
                        "exported_at": data.get("exported_at", ""),
                    }
                )
            except Exception:
                continue
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 4. Leaderboard
# ---------------------------------------------------------------------------

def _load_leaderboard() -> list[dict]:
    """Internal helper to load the leaderboard file."""
    try:
        if LEADERBOARD_PATH.exists():
            return json.loads(LEADERBOARD_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_leaderboard(entries: list[dict]) -> None:
    """Internal helper to persist the leaderboard."""
    LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def update_leaderboard(strategy_name: str, stats: dict) -> None:
    """Update leaderboard with strategy performance.

    Args:
        strategy_name: Name of the strategy.
        stats: {"win_rate": float, "total_return": float, "sharpe_ratio": float,
                "max_drawdown": float, "trades": int, "period_days": int}
    """
    try:
        entries = _load_leaderboard()
        entry = {
            "strategy_name": strategy_name,
            "updated_at": datetime.now().isoformat(),
            **stats,
        }
        # Replace existing entry for same strategy, or append
        entries = [e for e in entries if e.get("strategy_name") != strategy_name]
        entries.append(entry)
        _save_leaderboard(entries)
    except Exception:
        pass


def get_leaderboard(sort_by: str = "sharpe_ratio", top_n: int = 10) -> list[dict]:
    """Get ranked leaderboard sorted by the given metric (descending).

    Valid sort keys: win_rate, total_return, sharpe_ratio, max_drawdown, trades.
    """
    try:
        entries = _load_leaderboard()
        # For max_drawdown, lower (less negative) is better — sort ascending
        reverse = sort_by != "max_drawdown"
        entries.sort(key=lambda e: e.get(sort_by, 0), reverse=reverse)
        return entries[:top_n]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 5. Discord Bot Command Generator
# ---------------------------------------------------------------------------

def generate_discord_summary(report_content: str, tickers: list[str]) -> str:
    """Format report summary for Discord embed.

    Returns a Discord-formatted message (markdown) trimmed to the 2000-char limit.
    Extracts key lines containing ticker symbols, price, IV, and strategy info.
    """
    try:
        lines = report_content.splitlines()
        header = f"**Options Daily Report** — {datetime.now().strftime('%Y-%m-%d')}\n"
        ticker_set = {t.upper() for t in tickers}

        sections: list[str] = []
        for ticker in sorted(ticker_set):
            relevant = [
                ln.strip()
                for ln in lines
                if ticker in ln.upper()
                and any(
                    kw in ln.lower()
                    for kw in ["price", "iv", "p/c", "max pain", "strategy", "pick"]
                )
            ]
            if relevant:
                block = f"__**{ticker}**__\n```\n" + "\n".join(relevant[:5]) + "\n```"
                sections.append(block)

        body = "\n".join(sections) if sections else "No significant signals detected."
        message = header + body

        # Respect Discord 2000-char limit
        if len(message) > 2000:
            message = message[:1997] + "..."
        return message
    except Exception:
        return ""


def format_quick_analysis(symbol: str, data: dict) -> str:
    """Format a quick analysis response for Discord slash commands.

    Args:
        symbol: Ticker symbol.
        data: Dict with optional keys: price, iv_rank, pc_ratio, max_pain, best_trade.

    Returns:
        Short summary string with Discord markdown formatting.
    """
    try:
        sym = symbol.upper()
        parts = [f"**{sym} Quick Analysis**"]
        if "price" in data:
            parts.append(f"Price: `${data['price']:.2f}`")
        if "iv_rank" in data:
            parts.append(f"IV Rank: `{data['iv_rank']:.1f}%`")
        if "pc_ratio" in data:
            parts.append(f"P/C Ratio: `{data['pc_ratio']:.2f}`")
        if "max_pain" in data:
            parts.append(f"Max Pain: `${data['max_pain']:.2f}`")
        if "best_trade" in data:
            parts.append(f"Best Trade: {data['best_trade']}")
        return " | ".join(parts)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 6. Collaborative Watchlists
# ---------------------------------------------------------------------------

def create_collab_watchlist(
    name: str,
    tickers: list[str],
    creator: str,
    notes: dict[str, str] | None = None,
) -> str:
    """Create a collaborative watchlist with annotations.

    Args:
        name: Watchlist name.
        tickers: List of ticker symbols.
        creator: Creator identifier.
        notes: Optional dict mapping symbol to note string,
               e.g. {"TSLA": "Watch for earnings 4/28"}.

    Returns:
        Path to watchlist file, or empty string on failure.
    """
    try:
        COLLAB_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]", "_", name)
        path = COLLAB_DIR / f"{safe_name}.json"

        annotations: dict[str, list[dict]] = {}
        if notes:
            for sym, note in notes.items():
                annotations[sym.upper()] = [
                    {
                        "note": note,
                        "author": creator,
                        "timestamp": datetime.now().isoformat(),
                    }
                ]

        payload = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "creator": creator,
            "tickers": [t.upper() for t in tickers],
            "annotations": annotations,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return ""


def add_annotation(
    watchlist_name: str, symbol: str, note: str, author: str
) -> None:
    """Add an annotation to a symbol in a collaborative watchlist."""
    try:
        safe_name = re.sub(r"[^\w\-]", "_", watchlist_name)
        path = COLLAB_DIR / f"{safe_name}.json"
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        sym = symbol.upper()
        annotations = data.setdefault("annotations", {})
        annotations.setdefault(sym, []).append(
            {
                "note": note,
                "author": author,
                "timestamp": datetime.now().isoformat(),
            }
        )
        # Ensure the symbol is in the tickers list
        if sym not in data.get("tickers", []):
            data.setdefault("tickers", []).append(sym)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_collab_watchlist(name: str) -> dict | None:
    """Get collaborative watchlist with all annotations."""
    try:
        safe_name = re.sub(r"[^\w\-]", "_", name)
        path = COLLAB_DIR / f"{safe_name}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 7. Strategy Marketplace
# ---------------------------------------------------------------------------

def publish_strategy(strategy: dict) -> str:
    """Publish a strategy to the marketplace.

    Args:
        strategy: {
            "name": str,
            "description": str,
            "author": str,
            "config": dict,
            "backtest_results": dict,
            "tags": list[str],
        }

    Returns:
        strategy_id (filename stem), or empty string on failure.
    """
    try:
        MARKETPLACE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = re.sub(r"[^\w\-]", "_", strategy.get("name", "unnamed"))
        strategy_id = f"{safe_name}_{timestamp}"
        path = MARKETPLACE_DIR / f"{strategy_id}.json"

        payload = {
            "strategy_id": strategy_id,
            "published_at": datetime.now().isoformat(),
            "rating": 0.0,
            "downloads": 0,
            **strategy,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return strategy_id
    except Exception:
        return ""


def browse_marketplace(
    tag: str | None = None, sort_by: str = "rating"
) -> list[dict]:
    """Browse available strategies in the marketplace.

    Args:
        tag: Optional tag to filter by (e.g. "iron_condor", "earnings").
        sort_by: Sort key — "rating" or "downloads".

    Returns:
        List of strategy summary dicts.
    """
    try:
        if not MARKETPLACE_DIR.exists():
            return []
        results: list[dict] = []
        for p in MARKETPLACE_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if tag and tag.lower() not in [
                    t.lower() for t in data.get("tags", [])
                ]:
                    continue
                results.append(
                    {
                        "strategy_id": data.get("strategy_id", p.stem),
                        "name": data.get("name", ""),
                        "author": data.get("author", ""),
                        "description": data.get("description", ""),
                        "tags": data.get("tags", []),
                        "rating": data.get("rating", 0.0),
                        "downloads": data.get("downloads", 0),
                        "published_at": data.get("published_at", ""),
                    }
                )
            except Exception:
                continue
        reverse = True
        results.sort(key=lambda e: e.get(sort_by, 0), reverse=reverse)
        return results
    except Exception:
        return []


def clone_strategy(strategy_id: str) -> dict | None:
    """Clone a marketplace strategy for personal use.

    Increments the download counter on the original and returns the full
    strategy config dict so the caller can save it locally.
    """
    try:
        path = MARKETPLACE_DIR / f"{strategy_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))

        # Bump download count
        data["downloads"] = data.get("downloads", 0) + 1
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Return a clean copy without marketplace metadata
        return {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "author": data.get("author", ""),
            "config": data.get("config", {}),
            "backtest_results": data.get("backtest_results", {}),
            "tags": data.get("tags", []),
            "cloned_from": strategy_id,
            "cloned_at": datetime.now().isoformat(),
        }
    except Exception:
        return None
