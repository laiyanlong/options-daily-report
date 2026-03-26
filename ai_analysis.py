"""
AI-powered market commentary using Google Gemini API.
Generates qualitative analysis to complement the quantitative options report.
"""

import os
from datetime import datetime

import yfinance as yf

# Gemini API is optional — skip gracefully if not available
try:
    from google import genai

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


def get_market_context(tickers: list[str]) -> str:
    """Fetch news headlines and analyst recommendations for each ticker."""
    sections = []

    for symbol in tickers:
        tk = yf.Ticker(symbol)
        parts = [f"### {symbol}"]

        # Recent news
        try:
            news = tk.news or []
            headlines = []
            for item in news[:5]:
                content = item.get("content", {})
                title = content.get("title", "")
                summary = content.get("summary", "")
                pub = content.get("pubDate", "")
                if title:
                    headlines.append(f"- [{pub[:10]}] {title}")
                    if summary:
                        headlines.append(f"  {summary[:200]}")
            if headlines:
                parts.append("**Recent News:**")
                parts.extend(headlines)
        except Exception:
            parts.append("**News:** unavailable")

        # Analyst recommendations
        try:
            recs = tk.recommendations
            if recs is not None and not recs.empty:
                latest = recs.iloc[0]
                parts.append(
                    f"**Analyst Consensus:** "
                    f"Strong Buy={latest.get('strongBuy', 0)}, "
                    f"Buy={latest.get('buy', 0)}, "
                    f"Hold={latest.get('hold', 0)}, "
                    f"Sell={latest.get('sell', 0)}, "
                    f"Strong Sell={latest.get('strongSell', 0)}"
                )
        except Exception:
            pass

        # Key stats
        try:
            info = tk.info
            stats = []
            if info.get("forwardPE"):
                stats.append(f"Forward P/E: {info['forwardPE']:.1f}")
            if info.get("trailingPE"):
                stats.append(f"Trailing P/E: {info['trailingPE']:.1f}")
            if info.get("fiftyTwoWeekHigh"):
                stats.append(f"52W High: ${info['fiftyTwoWeekHigh']:.2f}")
            if info.get("fiftyTwoWeekLow"):
                stats.append(f"52W Low: ${info['fiftyTwoWeekLow']:.2f}")
            if info.get("marketCap"):
                cap_b = info["marketCap"] / 1e9
                stats.append(f"Market Cap: ${cap_b:.0f}B")
            if stats:
                parts.append(f"**Key Stats:** {' | '.join(stats)}")
        except Exception:
            pass

        sections.append("\n".join(parts))

    return "\n\n".join(sections)


def generate_ai_commentary(quant_report: str, tickers: list[str], lang: str = "zh") -> str:
    """Generate AI market commentary using Google Gemini API.

    Args:
        quant_report: The quantitative report content.
        tickers: List of stock tickers.
        lang: "zh" for Traditional Chinese, "en" for English.

    Returns the commentary string, or an error message if unavailable.
    """
    if not HAS_GENAI:
        return _fallback_message("google-genai package not installed")

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return _fallback_message("GEMINI_API_KEY not set")

    # Fetch market context
    print("  Fetching market context for AI analysis...")
    market_context = get_market_context(tickers)

    # Build prompt based on language
    today = datetime.now().strftime("%Y-%m-%d")

    if lang == "en":
        prompt = f"""You are a professional options strategy analyst specializing in selling strategies (Sell Put / Sell Call).
Today is {today}.

Below is today's quantitative analysis report and market information. Please provide professional market commentary based on this data.

## Quantitative Report (Black-Scholes Model)
{quant_report[-6000:]}

## Market News & Analyst Ratings
{market_context}

Please analyze using this structure:

### 📰 Today's Market Highlights
For each ticker, analyze the 2-3 most important news items and their impact on stock price and options strategies.

### 📊 Bull/Bear Outlook
For each ticker, provide a short-term (1-2 weeks) outlook with rationale. Use "Bullish / Neutral / Bearish".

### 🎯 Strategy Recommendations
1. Based on current market conditions, is Sell Put or Sell Call more suitable? Why?
2. Recommend one optimal trade per ticker (include strike and expiry preference)
3. When should the strategy be stopped or adjusted?

### ⚠️ Risk Events This Week
List major events that could impact these tickers (earnings, Fed, CPI, geopolitics, etc.).

### 💡 Additional Observations
Any noteworthy points not covered by the quantitative report (unusual options activity, sector rotation, macro trends, etc.).

Notes:
- Stay objective, avoid excessive optimism or pessimism
- Reference specific numbers from the report (IV, CP score, annualized return, etc.)
- End with a disclaimer"""
    else:
        prompt = f"""你是專業的選擇權策略分析師，精通賣方策略（Sell Put / Sell Call）。
今天是 {today}。

以下是今日的量化分析報告和市場資訊。請根據這些數據，用繁體中文提供專業的市場解讀。

## 量化分析報告（Black-Scholes 模型）
{quant_report[-6000:]}

## 市場新聞與分析師評級
{market_context}

請按照以下結構分析：

### 📰 今日市場重點
針對每檔標的，分析最重要的 2-3 則新聞對股價和選擇權策略的影響。

### 📊 多空判斷
對每檔標的給出短線（1-2 週）的多空判斷，並說明理由。用「偏多 / 中性 / 偏空」表示。

### 🎯 策略建議
1. 根據當前市場環境，Sell Put 還是 Sell Call 更適合？為什麼？
2. 每檔標的各推薦一個最佳的操作（含 strike 偏好和到期日偏好）
3. 如果市場環境改變，什麼時候應該停止或調整策略？

### ⚠️ 本週風險事件
列出本週可能影響這些標的的重大事件（財報、Fed、CPI、地緣政治等）。

### 💡 額外觀察
任何值得注意但量化報告沒有覆蓋的觀點（如選擇權異常活動、板塊輪動、宏觀趨勢等）。

注意：
- 保持客觀，不要過度樂觀或悲觀
- 具體引用報告中的數字（IV、CP 評分、年化報酬率等）
- 最後加上免責聲明"""

    print("  Calling Gemini API...")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return _fallback_message(f"Gemini API error: {e}")


def _fallback_message(reason: str) -> str:
    """Return a fallback message when AI analysis is unavailable."""
    return (
        f"> ⚠️ AI 市場解讀暫時無法使用（{reason}）\n"
        "> 請設定 `GEMINI_API_KEY` 環境變數以啟用此功能。\n"
        "> 量化分析報告仍然完整可用。"
    )
