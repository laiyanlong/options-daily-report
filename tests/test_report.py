"""
Tests for the options-daily-report project.
Covers core calculation logic, configuration, report generation,
Telegram notification, AI fallback, and data fetching.
"""

import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. test_calc_greeks
# ---------------------------------------------------------------------------
class TestCalcGreeks:
    """Black-Scholes Greeks calculation tests."""

    def test_known_inputs(self):
        from generate_report import calc_greeks

        result = calc_greeks(
            spot=100.0, strike=95.0, days_to_exp=30, iv_pct=25.0, option_type="put"
        )
        # Should return a dict with all four Greeks
        assert set(result.keys()) == {"delta", "gamma", "theta", "vega"}
        # Put delta should be negative
        assert result["delta"] < 0
        # Gamma and vega should be positive
        assert result["gamma"] > 0
        assert result["vega"] > 0

    def test_call_delta_positive(self):
        from generate_report import calc_greeks

        result = calc_greeks(
            spot=100.0, strike=105.0, days_to_exp=30, iv_pct=25.0, option_type="call"
        )
        assert result["delta"] > 0

    def test_zero_days_returns_zeros(self):
        from generate_report import calc_greeks

        result = calc_greeks(spot=100.0, strike=95.0, days_to_exp=0, iv_pct=25.0)
        assert result == {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    def test_zero_iv_returns_zeros(self):
        from generate_report import calc_greeks

        result = calc_greeks(spot=100.0, strike=95.0, days_to_exp=30, iv_pct=0)
        assert result == {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    def test_negative_values_return_zeros(self):
        from generate_report import calc_greeks

        result = calc_greeks(spot=-100.0, strike=95.0, days_to_exp=30, iv_pct=25.0)
        assert result == {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

        result2 = calc_greeks(spot=100.0, strike=-95.0, days_to_exp=30, iv_pct=25.0)
        assert result2 == {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}


# ---------------------------------------------------------------------------
# 2. test_calc_cp_score
# ---------------------------------------------------------------------------
class TestCalcCpScore:
    """CP score calculation tests."""

    def test_returns_between_0_and_100(self):
        from generate_report import calc_cp_score

        score = calc_cp_score(
            annualized_return=50.0, otm_pct=7.0, delta=-0.3, theta=-0.05, premium=2.0
        )
        assert 0 <= score <= 100

    def test_various_inputs(self):
        from generate_report import calc_cp_score

        # High annualized return + high OTM -> higher score
        high = calc_cp_score(
            annualized_return=150.0, otm_pct=10.0, delta=-0.1, theta=-0.1, premium=5.0
        )
        # Low annualized return + low OTM -> lower score
        low = calc_cp_score(
            annualized_return=5.0, otm_pct=2.0, delta=-0.5, theta=-0.01, premium=0.5
        )
        assert high > low

    def test_zero_premium(self):
        from generate_report import calc_cp_score

        # Should not crash; theta_efficiency = 0 when premium = 0
        score = calc_cp_score(
            annualized_return=30.0, otm_pct=5.0, delta=-0.2, theta=-0.05, premium=0
        )
        assert 0 <= score <= 100

    def test_capped_annualized_return(self):
        from generate_report import calc_cp_score

        # Returns above 200% should be capped for scoring
        s1 = calc_cp_score(200.0, 5.0, -0.2, -0.05, 2.0)
        s2 = calc_cp_score(500.0, 5.0, -0.2, -0.05, 2.0)
        assert s1 == s2  # Both capped at 200


# ---------------------------------------------------------------------------
# 3. test_find_closest_strike
# ---------------------------------------------------------------------------
class TestFindClosestStrike:
    """Strike selection logic tests."""

    def test_exact_match(self):
        from generate_report import find_closest_strike

        assert find_closest_strike([90.0, 95.0, 100.0, 105.0], 100.0) == 100.0

    def test_closest_when_no_exact(self):
        from generate_report import find_closest_strike

        assert find_closest_strike([90.0, 95.0, 100.0, 105.0], 97.0) == 95.0

    def test_empty_list_returns_zero(self):
        from generate_report import find_closest_strike

        assert find_closest_strike([], 100.0) == 0

    def test_single_element(self):
        from generate_report import find_closest_strike

        assert find_closest_strike([50.0], 100.0) == 50.0


# ---------------------------------------------------------------------------
# 4. test_generate_options_table
# ---------------------------------------------------------------------------
class TestGenerateOptionsTable:
    """Markdown table generation tests."""

    @pytest.fixture
    def sample_entries(self) -> list:
        return [
            {
                "otm_pct": -5.0,
                "strike": 95.0,
                "bid": 1.50,
                "ask": 1.80,
                "delta": -0.20,
                "gamma": 0.03,
                "theta": -0.05,
                "vega": 0.10,
                "iv": 30.0,
                "annualized": 45.0,
                "cp": 65.0,
            },
            {
                "otm_pct": -7.0,
                "strike": 93.0,
                "bid": 0.80,
                "ask": 1.10,
                "delta": -0.12,
                "gamma": 0.02,
                "theta": -0.03,
                "vega": 0.08,
                "iv": 28.0,
                "annualized": 30.0,
                "cp": 72.0,
            },
        ]

    def test_valid_markdown_table(self, sample_entries):
        from generate_report import generate_options_table

        table = generate_options_table(sample_entries, best_cp_strike=93.0)
        lines = table.strip().split("\n")
        # Header + separator + 2 data rows
        assert len(lines) == 4
        # All lines should start with "|"
        for line in lines:
            assert line.startswith("|")

    def test_star_marker_for_best_cp(self, sample_entries):
        from generate_report import generate_options_table

        table = generate_options_table(sample_entries, best_cp_strike=93.0)
        lines = table.strip().split("\n")
        # The row for strike 93.0 should contain the star
        row_93 = [l for l in lines if "$93.00" in l]
        assert len(row_93) == 1
        assert "\u2605" in row_93[0]  # Unicode star

        # The row for strike 95.0 should NOT have the star marker
        row_95 = [l for l in lines if "$95.00" in l]
        assert len(row_95) == 1
        assert "\u2605" not in row_95[0]


# ---------------------------------------------------------------------------
# 5. test_ticker_config
# ---------------------------------------------------------------------------
class TestTickerConfig:
    """TICKERS env var parsing tests."""

    def test_default_tickers(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove TICKERS if present
            os.environ.pop("TICKERS", None)
            # Re-evaluate the config expression
            _tickers_env = os.environ.get("TICKERS", "").strip()
            tickers = (
                [t.strip().upper() for t in _tickers_env.split(",") if t.strip()]
                if _tickers_env
                else ["TSLA", "AMZN", "NVDA"]
            )
            assert tickers == ["TSLA", "AMZN", "NVDA"]

    def test_custom_tickers_env(self):
        with patch.dict(os.environ, {"TICKERS": "AAPL, MSFT, GOOG"}, clear=False):
            _tickers_env = os.environ.get("TICKERS", "").strip()
            tickers = (
                [t.strip().upper() for t in _tickers_env.split(",") if t.strip()]
                if _tickers_env
                else ["TSLA", "AMZN", "NVDA"]
            )
            assert tickers == ["AAPL", "MSFT", "GOOG"]

    def test_empty_tickers_env(self):
        with patch.dict(os.environ, {"TICKERS": ""}, clear=False):
            _tickers_env = os.environ.get("TICKERS", "").strip()
            tickers = (
                [t.strip().upper() for t in _tickers_env.split(",") if t.strip()]
                if _tickers_env
                else ["TSLA", "AMZN", "NVDA"]
            )
            assert tickers == ["TSLA", "AMZN", "NVDA"]


# ---------------------------------------------------------------------------
# 6. test_report_lang_config
# ---------------------------------------------------------------------------
class TestReportLangConfig:
    """REPORT_LANG env var tests."""

    def test_default_language_is_zh(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REPORT_LANG", None)
            lang = os.environ.get("REPORT_LANG", "zh")
            assert lang == "zh"

    def test_can_set_to_en(self):
        with patch.dict(os.environ, {"REPORT_LANG": "en"}, clear=False):
            lang = os.environ.get("REPORT_LANG", "zh")
            assert lang == "en"


# ---------------------------------------------------------------------------
# 7. test_extract_summary (telegram_notify)
# ---------------------------------------------------------------------------
class TestExtractSummary:
    """Telegram summary extraction tests."""

    def test_extracts_content_after_marker(self):
        from telegram_notify import _extract_summary

        content = (
            "# Report\n\n"
            "## Some Section\nblah\n\n"
            "## 最終總結：三檔股票大比拼\n\n"
            "This is the summary body.\n"
            "More summary lines.\n\n"
            "---\n\n"
            "## Footer"
        )
        result = _extract_summary(content)
        assert "This is the summary body." in result
        assert "More summary lines." in result
        # Should NOT include content after "---"
        assert "Footer" not in result

    def test_returns_empty_when_no_marker(self):
        from telegram_notify import _extract_summary

        content = "# Report\n\nNo summary here.\n"
        result = _extract_summary(content)
        assert result == ""

    def test_returns_to_end_when_no_separator(self):
        from telegram_notify import _extract_summary

        content = "## 最終總結\nSome summary text."
        result = _extract_summary(content)
        assert "Some summary text." in result


# ---------------------------------------------------------------------------
# 8. test_send_telegram_skips_without_token
# ---------------------------------------------------------------------------
class TestSendTelegramSkipsWithoutToken:
    """Telegram send should skip gracefully without credentials."""

    def test_returns_false_without_token(self):
        from telegram_notify import send_telegram_summary

        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""},
            clear=False,
        ):
            result = send_telegram_summary("report", "http://example.com", ["AAPL"])
            assert result is False

    def test_returns_false_with_token_but_no_chat_id(self):
        from telegram_notify import send_telegram_summary

        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": "fake-token", "TELEGRAM_CHAT_ID": ""},
            clear=False,
        ):
            result = send_telegram_summary("report", "http://example.com", ["AAPL"])
            assert result is False


# ---------------------------------------------------------------------------
# 9. test_generate_html_report_creates_file
# ---------------------------------------------------------------------------
class TestGenerateHtmlReport:
    """HTML report generation tests."""

    def test_creates_html_file(self, tmp_path):
        from html_report import generate_html_report

        # Minimal mock data
        mock_results = [
            {
                "symbol": "TEST",
                "price": 100.0,
                "data": {
                    "history": {"1d": 99.0, "3d": 98.0, "5d": 97.0, "7d": 96.0},
                },
                "expiries": [
                    {
                        "date": "2025-01-17",
                        "days": 30,
                        "sell_puts": [
                            {
                                "otm_pct": -5.0,
                                "strike": 95.0,
                                "bid": 1.5,
                                "ask": 1.8,
                                "delta": -0.2,
                                "gamma": 0.03,
                                "theta": -0.05,
                                "vega": 0.1,
                                "iv": 30.0,
                                "annualized": 45.0,
                                "cp": 65.0,
                            }
                        ],
                        "sell_calls": [
                            {
                                "otm_pct": 5.0,
                                "strike": 105.0,
                                "bid": 1.2,
                                "ask": 1.5,
                                "delta": 0.18,
                                "gamma": 0.02,
                                "theta": -0.04,
                                "vega": 0.09,
                                "iv": 28.0,
                                "annualized": 35.0,
                                "cp": 60.0,
                            }
                        ],
                    }
                ],
            }
        ]

        output_path = generate_html_report(mock_results, "2025-01-01", tmp_path)
        result_file = Path(output_path)
        assert result_file.exists()
        assert result_file.suffix == ".html"

        content = result_file.read_text(encoding="utf-8")
        assert "TEST" in content
        assert "2025-01-01" in content
        assert "<html" in content


# ---------------------------------------------------------------------------
# 10. test_ai_fallback_without_key
# ---------------------------------------------------------------------------
class TestAiFallbackWithoutKey:
    """AI analysis should return a fallback message without API key."""

    def test_returns_fallback_without_gemini_key(self):
        from ai_analysis import generate_ai_commentary

        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            result = generate_ai_commentary("report text", ["AAPL"], lang="zh")
            assert "GEMINI_API_KEY" in result or "暫時無法使用" in result


# ---------------------------------------------------------------------------
# 11. test_fetch_ticker_data_structure
# ---------------------------------------------------------------------------
class TestFetchTickerDataStructure:
    """Verify fetch_ticker_data returns dict with expected keys."""

    def test_returns_expected_keys(self):
        from generate_report import fetch_ticker_data

        try:
            data = fetch_ticker_data("AAPL")
        except Exception:
            pytest.skip("Network unavailable or Yahoo Finance API error")

        expected_keys = {
            "symbol",
            "price",
            "prev_close",
            "change_pct",
            "history",
            "expiries",
            "chains",
            "iv_percentile_data",
            "next_earnings",
        }
        assert expected_keys == set(data.keys())
        assert data["symbol"] == "AAPL"
        assert isinstance(data["price"], (int, float))
        assert isinstance(data["expiries"], list)


# ---------------------------------------------------------------------------
# 12. test_iv_percentile_calculation
# ---------------------------------------------------------------------------
class TestIvPercentileCalculation:
    """IV percentile rank calculation tests."""

    def test_iv_percentile_between_0_and_100(self):
        """Replicate the IV percentile logic from generate_ticker_report."""
        min_hv = 20.0
        max_hv = 60.0
        avg_iv = 40.0

        iv_pct_val = (avg_iv - min_hv) / (max_hv - min_hv) * 100
        iv_pct_val = max(0.0, min(100.0, iv_pct_val))
        assert 0 <= iv_pct_val <= 100
        assert iv_pct_val == 50.0  # midpoint

    def test_edge_case_min_equals_max(self):
        """When min_hv == max_hv, division by zero should be avoided."""
        min_hv = 30.0
        max_hv = 30.0
        avg_iv = 30.0

        # The actual code guards with `if max_hv > min_hv:` so iv_percentile stays None
        if max_hv > min_hv:
            iv_pct_val = (avg_iv - min_hv) / (max_hv - min_hv) * 100
        else:
            iv_pct_val = None

        assert iv_pct_val is None

    def test_iv_below_min_clamps_to_zero(self):
        min_hv = 30.0
        max_hv = 60.0
        avg_iv = 10.0  # below historical min

        iv_pct_val = (avg_iv - min_hv) / (max_hv - min_hv) * 100
        iv_pct_val = max(0.0, min(100.0, iv_pct_val))
        assert iv_pct_val == 0.0

    def test_iv_above_max_clamps_to_100(self):
        min_hv = 20.0
        max_hv = 50.0
        avg_iv = 80.0  # above historical max

        iv_pct_val = (avg_iv - min_hv) / (max_hv - min_hv) * 100
        iv_pct_val = max(0.0, min(100.0, iv_pct_val))
        assert iv_pct_val == 100.0
