"""
Interactive HTML Report Generator using Plotly.
Generates charts for price history, IV smile, CP scores, and Greeks heatmaps.
"""

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _build_price_history_chart(result: dict) -> go.Figure:
    """Build a line chart of recent prices for a single ticker."""
    symbol = result["symbol"]
    price = result["price"]
    data = result["data"]
    history = data.get("history", {})

    # Build x/y from history keys (7d, 5d, 3d, 1d) + current
    day_labels = ["7d ago", "5d ago", "3d ago", "1d ago", "Now"]
    day_keys = ["7d", "5d", "3d", "1d"]

    prices = []
    for k in day_keys:
        prices.append(history.get(k))
    prices.append(price)

    # Filter out None values while keeping alignment
    x_vals = []
    y_vals = []
    for label, p in zip(day_labels, prices):
        if p is not None:
            x_vals.append(label)
            y_vals.append(p)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="lines+markers",
        name=symbol,
        line=dict(width=3),
        marker=dict(size=8),
    ))

    # Highlight current price
    if price is not None:
        fig.add_trace(go.Scatter(
            x=["Now"],
            y=[price],
            mode="markers+text",
            text=[f"${price:.2f}"],
            textposition="top center",
            marker=dict(size=14, color="gold", symbol="star"),
            name="Current Price",
            showlegend=False,
        ))

    fig.update_layout(
        title=f"{symbol} - Recent Price History",
        xaxis_title="Time",
        yaxis_title="Price ($)",
        template="plotly_dark",
        height=400,
    )
    return fig


def _build_iv_smile_chart(result: dict) -> go.Figure | None:
    """Build IV smile chart for the first expiry of a ticker."""
    if not result["expiries"]:
        return None

    symbol = result["symbol"]
    first_expiry = result["expiries"][0]
    exp_date = first_expiry["date"]

    put_strikes = [e["strike"] for e in first_expiry["sell_puts"] if e["iv"] > 0]
    put_ivs = [e["iv"] for e in first_expiry["sell_puts"] if e["iv"] > 0]
    call_strikes = [e["strike"] for e in first_expiry["sell_calls"] if e["iv"] > 0]
    call_ivs = [e["iv"] for e in first_expiry["sell_calls"] if e["iv"] > 0]

    if not put_strikes and not call_strikes:
        return None

    fig = go.Figure()
    if put_strikes:
        fig.add_trace(go.Scatter(
            x=put_strikes,
            y=put_ivs,
            mode="lines+markers",
            name="Puts",
            line=dict(color="#EF553B", width=2),
            marker=dict(size=7),
        ))
    if call_strikes:
        fig.add_trace(go.Scatter(
            x=call_strikes,
            y=call_ivs,
            mode="lines+markers",
            name="Calls",
            line=dict(color="#636EFA", width=2),
            marker=dict(size=7),
        ))

    # Add current price vertical line
    price = result["price"]
    fig.add_vline(
        x=price,
        line_dash="dash",
        line_color="gold",
        annotation_text=f"Price ${price:.2f}",
        annotation_position="top",
    )

    fig.update_layout(
        title=f"{symbol} - IV Smile (Expiry: {exp_date})",
        xaxis_title="Strike ($)",
        yaxis_title="Implied Volatility (%)",
        template="plotly_dark",
        height=400,
    )
    return fig


def _build_cp_comparison_chart(all_results: list) -> go.Figure | None:
    """Build grouped bar chart comparing best CP scores across tickers."""
    symbols = []
    best_put_cps = []
    best_call_cps = []

    for r in all_results:
        all_puts = [p for exp in r["expiries"] for p in exp["sell_puts"]]
        all_calls = [c for exp in r["expiries"] for c in exp["sell_calls"]]

        best_put_cp = max((p["cp"] for p in all_puts), default=0)
        best_call_cp = max((c["cp"] for c in all_calls), default=0)

        symbols.append(r["symbol"])
        best_put_cps.append(best_put_cp)
        best_call_cps.append(best_call_cp)

    if not symbols:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Sell Put",
        x=symbols,
        y=best_put_cps,
        marker_color="#EF553B",
        text=[f"{v:.1f}" for v in best_put_cps],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        name="Sell Call",
        x=symbols,
        y=best_call_cps,
        marker_color="#636EFA",
        text=[f"{v:.1f}" for v in best_call_cps],
        textposition="auto",
    ))

    fig.update_layout(
        title="Best CP Score Comparison: Sell Put vs Sell Call",
        xaxis_title="Ticker",
        yaxis_title="CP Score",
        barmode="group",
        template="plotly_dark",
        height=400,
    )
    return fig


def _build_greeks_heatmap(result: dict) -> go.Figure | None:
    """Build delta heatmap across strikes for first expiry."""
    if not result["expiries"]:
        return None

    symbol = result["symbol"]
    first_expiry = result["expiries"][0]
    exp_date = first_expiry["date"]

    puts = first_expiry["sell_puts"]
    calls = first_expiry["sell_calls"]

    if not puts and not calls:
        return None

    # Collect all strikes and build delta matrix
    all_strikes = sorted(set(
        [e["strike"] for e in puts] + [e["strike"] for e in calls]
    ))

    put_deltas = {}
    for e in puts:
        put_deltas[e["strike"]] = e["delta"]

    call_deltas = {}
    for e in calls:
        call_deltas[e["strike"]] = e["delta"]

    z_data = []
    row_labels = ["Put Delta", "Call Delta"]

    put_row = [put_deltas.get(s, None) for s in all_strikes]
    call_row = [call_deltas.get(s, None) for s in all_strikes]
    z_data = [put_row, call_row]

    strike_labels = [f"${s:.0f}" for s in all_strikes]

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=strike_labels,
        y=row_labels,
        colorscale="RdBu_r",
        zmid=0,
        text=[[f"{v:.4f}" if v is not None else "" for v in row] for row in z_data],
        texttemplate="%{text}",
        hovertemplate="Strike: %{x}<br>Type: %{y}<br>Delta: %{z:.4f}<extra></extra>",
        colorbar=dict(title="Delta"),
    ))

    fig.update_layout(
        title=f"{symbol} - Delta Heatmap (Expiry: {exp_date})",
        xaxis_title="Strike",
        yaxis_title="Option Type",
        template="plotly_dark",
        height=350,
    )
    return fig


def generate_html_report(all_results: list, report_date: str, reports_dir: Path) -> str:
    """Generate interactive HTML report. Returns the file path."""
    html_parts = []

    # HTML header
    html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Daily Report - {report_date}</title>
    <style>
        body {{
            background-color: #1a1a2e;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px 40px;
        }}
        h1 {{
            text-align: center;
            color: #f5c542;
            border-bottom: 2px solid #f5c542;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #82b1ff;
            margin-top: 40px;
            border-left: 4px solid #82b1ff;
            padding-left: 12px;
        }}
        .chart-container {{
            margin: 20px 0;
            background-color: #16213e;
            border-radius: 8px;
            padding: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #888;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <h1>Options Daily Report - {report_date}</h1>
""")

    # 1. Price History Charts (one per ticker)
    for result in all_results:
        symbol = result["symbol"]
        fig = _build_price_history_chart(result)
        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
        html_parts.append(f'    <h2>{symbol} - Price History</h2>')
        html_parts.append(f'    <div class="chart-container">{chart_html}</div>')

    # 2. IV Smile Charts (one per ticker, first expiry)
    for result in all_results:
        symbol = result["symbol"]
        fig = _build_iv_smile_chart(result)
        if fig is not None:
            chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
            html_parts.append(f'    <h2>{symbol} - IV Smile</h2>')
            html_parts.append(f'    <div class="chart-container">{chart_html}</div>')

    # 3. CP Score Comparison (combined)
    fig = _build_cp_comparison_chart(all_results)
    if fig is not None:
        chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
        html_parts.append('    <h2>CP Score Comparison - All Tickers</h2>')
        html_parts.append(f'    <div class="chart-container">{chart_html}</div>')

    # 4. Greeks Heatmaps (one per ticker, first expiry)
    for result in all_results:
        symbol = result["symbol"]
        fig = _build_greeks_heatmap(result)
        if fig is not None:
            chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
            html_parts.append(f'    <h2>{symbol} - Delta Heatmap</h2>')
            html_parts.append(f'    <div class="chart-container">{chart_html}</div>')

    # Footer
    html_parts.append("""
    <div class="footer">
        Generated by Options Daily Report | Data from Yahoo Finance | Charts by Plotly
    </div>
</body>
</html>""")

    # Write file
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / f"{report_date}.html"
    output_path.write_text("\n".join(html_parts), encoding="utf-8")

    return str(output_path)
