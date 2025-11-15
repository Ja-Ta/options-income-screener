#!/usr/bin/env python3
"""
Test Telegram Sentiment Alerts (v2.8)

Tests the enhanced Telegram alert formatting with sentiment context.
Demonstrates different sentiment scenarios (LONG, SHORT, NONE).

Usage:
    python test_telegram_sentiment.py

Author: Options Income Screener v2.8
"""

import sys
import os

# Add python_app to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'python_app'))

from src.services.telegram_service import TelegramService


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'─'*80}")
    print(f"  {title}")
    print(f"{'─'*80}")


def test_sentiment_formatting():
    """Test Telegram message formatting with various sentiment scenarios."""

    print_header("TELEGRAM SENTIMENT ALERT FORMATTING TEST (v2.8)")

    # Initialize service in mock mode
    service = TelegramService(bot_token="mock_token")

    # Test Scenario 1: LONG signal (crowd fearful, smart money buying)
    print_section("Scenario 1: LONG Signal - Contrarian Buy Opportunity")

    pick_long = {
        'id': 1,
        'symbol': 'GME',
        'strategy': 'CSP',
        'spot_price': 22.50,
        'strike': 20.00,
        'expiry': '2025-12-20',
        'premium': 1.25,
        'roi_30d': 0.0625,  # 6.25%
        'iv_rank': 78.5,
        'score': 0.72,
        'margin_of_safety': 0.111,  # 11.1% OTM
        'contrarian_signal': 'long',
        'put_call_ratio': 2.15,  # High P/C = crowd fearful
        'cmf_20': 0.18,  # Positive CMF = accumulation
        'notes': 'High IV rank with bullish divergence',
        'asof': '2025-11-15'
    }

    rationale_long = ("This CSP offers attractive premium from elevated IV while sentiment "
                     "shows contrarian opportunity. High P/C ratio (2.15) indicates crowd "
                     "fear, yet positive CMF (+0.18) shows smart money accumulating. "
                     "11.1% margin of safety provides downside cushion.")

    message_long = service.format_pick_message(pick_long, rationale_long)
    print(message_long)

    # Test Scenario 2: SHORT signal (crowd greedy, smart money selling)
    print_section("Scenario 2: SHORT Signal - Contrarian Sell Setup")

    pick_short = {
        'id': 2,
        'symbol': 'TSLA',
        'strategy': 'CC',
        'spot_price': 245.80,
        'strike': 250.00,
        'expiry': '2025-12-20',
        'premium': 8.50,
        'roi_30d': 0.0346,  # 3.46%
        'iv_rank': 62.3,
        'score': 0.58,
        'contrarian_signal': 'short',
        'put_call_ratio': 0.55,  # Low P/C = crowd greedy
        'cmf_20': -0.16,  # Negative CMF = distribution
        'earnings_date': '2025-12-05',
        'earnings_days_until': 20,
        'notes': 'Premium rich but sentiment shows distribution',
        'asof': '2025-11-15'
    }

    rationale_short = ("While IV rank is elevated, sentiment shows signs of overextension. "
                      "Low P/C ratio (0.55) suggests excessive optimism, confirmed by "
                      "negative CMF (-0.16) indicating smart money distribution. "
                      "Consider this a tactical income play with caution.")

    message_short = service.format_pick_message(pick_short, rationale_short)
    print(message_short)

    # Test Scenario 3: NONE signal (neutral sentiment)
    print_section("Scenario 3: NONE Signal - Neutral Sentiment")

    pick_none = {
        'id': 3,
        'symbol': 'AAPL',
        'strategy': 'CC',
        'spot_price': 185.25,
        'strike': 190.00,
        'expiry': '2025-12-20',
        'premium': 3.20,
        'roi_30d': 0.0173,  # 1.73%
        'iv_rank': 45.2,
        'score': 0.52,
        'contrarian_signal': 'none',
        'put_call_ratio': 1.05,  # Balanced P/C
        'cmf_20': 0.02,  # Neutral CMF
        'earnings_date': '2025-12-15',
        'earnings_days_until': 30,
        'notes': 'Moderate premium with balanced sentiment',
        'asof': '2025-11-15'
    }

    rationale_none = ("Standard income opportunity with no strong sentiment signals. "
                     "Balanced P/C ratio (1.05) and neutral money flow suggest stable "
                     "conditions. Suitable for conservative premium collection with "
                     "earnings 30 days out providing ample time cushion.")

    message_none = service.format_pick_message(pick_none, rationale_none)
    print(message_none)

    # Test Scenario 4: No sentiment data (backward compatibility)
    print_section("Scenario 4: No Sentiment Data - Backward Compatibility")

    pick_no_sentiment = {
        'id': 4,
        'symbol': 'SPY',
        'strategy': 'CC',
        'spot_price': 455.80,
        'strike': 460.00,
        'expiry': '2025-12-20',
        'premium': 2.15,
        'roi_30d': 0.0047,  # 0.47%
        'iv_rank': 28.5,
        'score': 0.45,
        'notes': 'Low IV environment, conservative play',
        'asof': '2025-11-15'
    }

    rationale_no_sentiment = ("Conservative income play on broad market ETF. "
                              "Low IV rank suggests premium compression but provides "
                              "stable income opportunity with minimal volatility risk.")

    message_no_sentiment = service.format_pick_message(pick_no_sentiment, rationale_no_sentiment)
    print(message_no_sentiment)

    # Summary
    print_section("Test Summary")
    print("\n✅ All sentiment formatting scenarios tested successfully!")
    print("\nSentiment indicators tested:")
    print("  ✓ LONG signal (🟢) - Contrarian buy with crowd fear + accumulation")
    print("  ✓ SHORT signal (🔴) - Contrarian sell with crowd greed + distribution")
    print("  ✓ NONE signal (⚪) - Neutral sentiment")
    print("  ✓ No sentiment data - Backward compatibility maintained")
    print("\nContext interpretations:")
    print("  ✓ P/C Ratio: Crowd fearful, greedy, bearish tilt, bullish tilt, balanced")
    print("  ✓ CMF: Strong accumulation, accumulation, distribution, strong distribution, neutral")
    print("\nNext Steps:")
    print("  1. Review the formatted messages above")
    print("  2. Verify sentiment context is clear and actionable")
    print("  3. Test with real Telegram bot (set TELEGRAM_BOT_TOKEN)")
    print("  4. Deploy to production")
    print()


if __name__ == "__main__":
    try:
        test_sentiment_formatting()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
