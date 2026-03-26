"""Send report summary to Telegram."""
import os
import urllib.request
import urllib.parse
import json
from datetime import date


def send_telegram_summary(report_content: str, report_url: str, tickers: list[str]) -> bool:
    """Send report summary to Telegram. Returns True if sent."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return False

    # Extract the summary section
    summary = _extract_summary(report_content)
    if not summary:
        summary = "(No summary section found in report.)"

    # Build the message
    today = date.today().strftime("%Y-%m-%d")
    ticker_str = ", ".join(tickers) if tickers else "N/A"
    message = (
        f"*Options Daily Report — {today}*\n"
        f"Tickers: `{ticker_str}`\n\n"
        f"{summary}\n\n"
        f"[Full Report]({report_url})"
    )

    # Truncate to Telegram's 4096 char limit (leave room for safety)
    if len(message) > 4000:
        message = message[:3997] + "..."

    # Send via Telegram Bot API
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print("Telegram notification sent successfully.")
                return True
            else:
                print(f"Telegram API returned status {resp.status}.")
                return False
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False


def _extract_summary(content: str) -> str:
    """Extract the summary section from the report markdown."""
    marker = "## 最終總結"
    idx = content.find(marker)
    if idx == -1:
        return ""

    # Start after the header line
    section = content[idx + len(marker):]

    # End at next "---" separator or end of content
    end_idx = section.find("\n---")
    if end_idx != -1:
        section = section[:end_idx]

    return section.strip()
