# Data contract

Third-party consumers (mobile apps, terminals, dashboards) can depend on
the following shapes. Anything not documented here may change without
warning.

---

## `dashboard/data.json`

Updated every weekday ~13:25 UTC. Top-level keys:

```jsonc
{
  "last_updated": "ISO 8601 UTC timestamp",
  "summary": {
    "total_trades": int,
    "win_rate": float,        // percent, 0..100
    "sharpe_ratio": float,
    "profit_factor": float
  },
  "live_prices": [
    {
      "symbol": "TSLA",
      "price": 347.63,
      "change_pct": 0.3,
      "market_state": "OPEN" | "CLOSED" | "PRE" | "POST",
      "intraday_prices": [number, ...]     // 30-min candles
    }
  ],
  "ticker_stats": { "<SYMBOL>": { "trades": int, "win_rate": float, "total_pnl": float } },
  "options_matrices": {
    "<SYMBOL>": {
      "expiries": [
        {
          "date": "YYYY-MM-DD",
          "puts": [ { "strike": float, "bid": float, "ask": float,
                      "delta": float, "iv": float, "otm_pct": float,
                      "pop": float, "annualized": float, "cp_score": float } ],
          "calls": [ /* same shape */ ]
        }
      ]
    }
  },
  "timing": {
    "<SYMBOL>": {
      "action": "SELL_NOW" | "WAIT" | "AVOID" | "NEUTRAL",
      "combined_score": 0..100,
      "overall_recommendation": "human-readable string"
    }
  },
  "oi_distribution": {
    "<SYMBOL>": {
      "price": float,
      "expiries_analyzed": int,
      "oi_by_strike": [ { "strike": float, "call_oi": int, "put_oi": int, "net_oi": int } ],
      "key_levels": {
        "max_call_oi_strike": float,
        "max_put_oi_strike": float,
        "max_pain": float,
        "highest_volume_strike": float
      },
      "interpretation": "human-readable"
    }
  }
}
```

## `dashboard/weekly_summary.json`

Updated every Sunday ~18:05 UTC. See any actual file in `dashboard/` for
the current shape.

## `reports/YYYY-MM-DD.md`

Markdown with H2 sections per ticker (`## TSLA`, `## AMZN`, ...). Parsers
should split by H2 headings. Do not rely on unicode emoji presence in
headings — they may change.

## Stability guarantee

We aim to keep these contracts stable. Breaking changes will be announced
via the repo's Releases page and a deprecation window of at least 30 days.
