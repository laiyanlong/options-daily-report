"""
Model Verdict —综合 9 个模型的评价和结论
Generates a unified verdict section for the daily report.
"""

import numpy as np
import yfinance as yf


def generate_model_verdict(tickers: list[str], all_results: list) -> str:
    """Generate comprehensive model verdict combining all 9 models.

    Returns markdown string to append to the report.
    """
    try:
        lines = []
        lines.append("## 🧠 模型綜合評價")
        lines.append("")

        # ── 1. Market Regime ──
        regime_data = _get_regime()
        if regime_data:
            regime = regime_data["regime"]
            emoji = {"low_vol": "🟢", "normal": "🟡", "high_vol": "🟠", "crisis": "🔴"}.get(regime, "⚪")
            lines.append(f"### 市場環境")
            lines.append("")
            lines.append(f"| 指標 | 數值 |")
            lines.append(f"|------|------|")
            lines.append(f"| 環境判定 | {emoji} **{regime.upper().replace('_', ' ')}** |")
            lines.append(f"| VIX | {regime_data.get('vix', 'N/A')} |")
            lines.append(f"| HV20 | {regime_data['hv20']:.1f}% |")
            lines.append(f"| 部位建議 | {regime_data['position_size_multiplier']:.0%} 正常大小 |")
            lines.append(f"| 推薦策略 | {', '.join(regime_data['recommended_strategies'][:3])} |")
            lines.append("")

        # ── 2. Per-ticker verdicts ──
        lines.append("### 各標的模型信號")
        lines.append("")
        lines.append("| 標的 | IV 信號 | IV Z-Score | 方向 | 方向信心 | 賣方邊際 | 綜合建議 |")
        lines.append("|------|---------|-----------|------|---------|---------|---------|")

        ticker_verdicts = []
        for result in all_results:
            symbol = result["symbol"]
            v = _analyze_ticker_models(symbol, result)
            ticker_verdicts.append(v)

            action_emoji = {"🟢 適合賣方": "🟢", "🟡 可做但謹慎": "🟡", "🔴 暫停賣方": "🔴"}.get(v["verdict"], "⚪")
            lines.append(
                f"| **{symbol}** "
                f"| {v['iv_signal']} "
                f"| {v['iv_zscore']} "
                f"| {v['direction']} "
                f"| {v['direction_confidence']} "
                f"| {v['seller_edge']} "
                f"| {v['verdict']} |"
            )
        lines.append("")

        # ── 3. Correlation risk ──
        corr_data = _get_correlation(tickers)
        if corr_data:
            lines.append("### 相關性風險")
            lines.append("")
            regime_icon = {"normal": "🟢", "elevated": "🟡", "crisis": "🔴"}.get(corr_data["regime"], "⚪")
            lines.append(f"| 指標 | 數值 |")
            lines.append(f"|------|------|")
            lines.append(f"| 平均相關性 | {corr_data['current_avg_correlation']:.2f}（歷史 {corr_data['historical_avg_correlation']:.2f}）|")
            lines.append(f"| 狀態 | {regime_icon} {corr_data['regime'].upper()} / {corr_data['trend']} |")
            lines.append(f"| 建議 | {corr_data['recommendation']} |")
            lines.append("")

        # ── 4. Final Verdict ──
        lines.append("### 🎯 今日綜合結論")
        lines.append("")

        # Count signals
        bullish_count = sum(1 for v in ticker_verdicts if "適合" in v["verdict"])
        caution_count = sum(1 for v in ticker_verdicts if "謹慎" in v["verdict"])
        stop_count = sum(1 for v in ticker_verdicts if "暫停" in v["verdict"])

        # Overall verdict
        if regime_data and regime_data["regime"] == "crisis":
            overall = "🔴 **全面暫停** — 危機模式，所有賣方策略暫停"
            action_lines = [
                "- 🛑 不建議任何裸賣方策略",
                "- 現金為王，等待波動回歸正常",
                "- 如果必須交易，僅做極遠 OTM 的 Iron Condor",
            ]
        elif stop_count >= len(ticker_verdicts) * 0.6:
            overall = "🔴 **大幅減碼** — 多數標的不適合賣方"
            action_lines = [
                "- 🛑 暫停裸 Sell Put / Sell Call",
                f"- 部位減至 {regime_data['position_size_multiplier']:.0%}" if regime_data else "- 部位減半",
                "- 改用 Iron Condor 或 Vertical Spread（定義風險）",
                "- 等待 IV z-score 回到正值再恢復",
            ]
        elif caution_count >= len(ticker_verdicts) * 0.5:
            overall = "🟡 **謹慎操作** — 可做但需控制風險"
            action_lines = [
                "- 🟡 可以小部位進場",
                "- 優先選擇 IV 信號為 Sell 的標的",
                "- 使用 spread 策略限制最大損失",
                "- 設定嚴格停損（2x premium）",
            ]
        else:
            overall = "🟢 **正常操作** — 適合賣方策略"
            action_lines = [
                "- ✅ 正常部位大小",
                "- 優先選擇 CP 評分最高的交易",
                "- Sell Put（看多標的）/ Sell Call（看空標的）",
            ]

        lines.append(f"**{overall}**")
        lines.append("")
        for al in action_lines:
            lines.append(al)
        lines.append("")

        # Best and worst ticker
        if ticker_verdicts:
            best = max(ticker_verdicts, key=lambda v: v["score"])
            worst = min(ticker_verdicts, key=lambda v: v["score"])
            lines.append(f"- **最適合交易**：{best['symbol']}（綜合分數 {best['score']:.0f}/100）")
            lines.append(f"- **最不適合交易**：{worst['symbol']}（綜合分數 {worst['score']:.0f}/100）")
            lines.append("")

        # Specific trade suggestion if any ticker is tradeable
        tradeable = [v for v in ticker_verdicts if "暫停" not in v["verdict"]]
        if tradeable:
            lines.append("**建議交易：**")
            lines.append("")
            for v in tradeable:
                lines.append(f"- **{v['symbol']}**: {v['suggested_trade']}")
            lines.append("")

        lines.append("> *以上為 9 個量化模型的綜合判斷，僅供參考，不構成投資建議。*")
        lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"> ⚠️ 模型綜合評價暫時無法產生（{e}）\n"


def _get_regime() -> dict | None:
    """Get volatility regime."""
    try:
        from ml_models import classify_volatility_regime
        return classify_volatility_regime()
    except Exception:
        return None


def _get_correlation(tickers: list[str]) -> dict | None:
    """Get correlation analysis."""
    try:
        from advanced_predictions import detect_correlation_shift
        return detect_correlation_shift(tickers)
    except Exception:
        return None


def _analyze_ticker_models(symbol: str, result: dict) -> dict:
    """Run all models for a single ticker and produce a unified verdict."""
    score = 50.0  # start neutral
    iv_signal = "N/A"
    iv_zscore = "N/A"
    direction = "N/A"
    direction_conf = "N/A"
    seller_edge = "N/A"
    suggested_trade = ""

    price = result["price"]

    # Get current IV proxy
    try:
        all_ivs = []
        for exp in result["expiries"]:
            for e in exp["sell_puts"] + exp["sell_calls"]:
                if e["iv"] > 0:
                    all_ivs.append(e["iv"])
        avg_iv = sum(all_ivs) / len(all_ivs) if all_ivs else 30.0
    except Exception:
        avg_iv = 30.0

    # IV Mean Reversion
    try:
        from ml_models import iv_mean_reversion
        m = iv_mean_reversion(symbol, avg_iv)
        if m:
            iv_signal = m["signal"]
            iv_zscore = f"{m['iv_zscore']:.2f}"
            if m["iv_zscore"] > 1.0:
                score += 20  # strong sell signal = great for sellers
            elif m["iv_zscore"] > 0.5:
                score += 10
            elif m["iv_zscore"] < -1.0:
                score -= 20  # IV too low
            elif m["iv_zscore"] < -0.5:
                score -= 10
    except Exception:
        pass

    # Price Direction
    try:
        from ml_models import predict_price_direction
        d = predict_price_direction(symbol)
        if d:
            direction = d["direction"]
            direction_conf = f"{d['confidence']:.0f}%"
            if d["direction"] == "Bullish":
                score += 15  # good for sell put
            elif d["direction"] == "Bearish" and d["confidence"] > 60:
                score -= 15  # bad for sell put
    except Exception:
        pass

    # Expected Move Accuracy (seller edge)
    try:
        from advanced_predictions import expected_move_accuracy
        e = expected_move_accuracy(symbol, 12)
        if e:
            seller_edge = f"{e['seller_edge_pct']:.2f}%"
            if e["seller_edge_pct"] > 2.0:
                score += 10
            elif e["seller_edge_pct"] < 0:
                score -= 10
    except Exception:
        pass

    # Clamp score
    score = max(0, min(100, score))

    # Determine verdict
    if score >= 65:
        verdict = "🟢 適合賣方"
        if direction == "Bullish":
            suggested_trade = f"Sell Put 5% OTM (~${price * 0.95:.0f}), 偏好近月到期"
        else:
            suggested_trade = f"Iron Condor（Put ${price * 0.93:.0f} / Call ${price * 1.07:.0f}）"
    elif score >= 40:
        verdict = "🟡 可做但謹慎"
        suggested_trade = f"Bull Put Spread（Sell ${price * 0.95:.0f} / Buy ${price * 0.90:.0f}），定義風險"
    else:
        verdict = "🔴 暫停賣方"
        suggested_trade = "暫停，等待 IV 回升或方向明確"

    return {
        "symbol": symbol,
        "score": score,
        "iv_signal": iv_signal,
        "iv_zscore": iv_zscore,
        "direction": direction,
        "direction_confidence": direction_conf,
        "seller_edge": seller_edge,
        "verdict": verdict,
        "suggested_trade": suggested_trade,
    }
