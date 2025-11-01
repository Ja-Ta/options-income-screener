#!/usr/bin/env python3
"""
Test the Options Income Screener with real API data.
"""

import sys
import os
from datetime import date
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pipelines.daily_job import run_daily_job
from src.services.telegram_service import TelegramService
from src.services.claude_service import ClaudeService
from src.utils.logging import setup_logger

def test_services():
    """Test API connections before running pipeline."""
    print("\n" + "="*60)
    print("TESTING API CONNECTIONS")
    print("="*60)

    # Test Telegram
    print("\n📱 Testing Telegram Bot...")
    telegram = TelegramService()
    if telegram.test_connection():
        print("✅ Telegram bot connected successfully!")
        # Send a test message
        if telegram.send_message("🚀 Options Income Screener initialized and ready!"):
            print("✅ Test message sent to Telegram!")
    else:
        print("❌ Telegram connection failed")

    # Test Claude
    print("\n🤖 Testing Claude AI...")
    claude = ClaudeService()
    if claude.test_connection():
        print("✅ Claude AI connected successfully!")
    else:
        print("❌ Claude AI connection failed")

    return True

def run_test():
    """Run a test with real data."""
    print("\n" + "="*60)
    print("OPTIONS INCOME SCREENER - PRODUCTION TEST")
    print("="*60)

    setup_logger()

    # Test with a smaller set of liquid symbols
    test_symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'TSLA']
    print(f"\n📊 Testing with symbols: {', '.join(test_symbols)}")
    print(f"📅 Date: {date.today()}")
    print("-"*60)

    # Test services first
    if not test_services():
        print("\n⚠️ Some services failed to connect")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return

    print("\n🚀 Running screening pipeline with real data...")
    print("-"*60)

    try:
        results = run_daily_job(symbols=test_symbols)

        print("\n✅ Pipeline completed successfully!")
        print("-"*60)

        print("\n📊 RESULTS:")
        print(f"  • Symbols processed: {results['symbols_processed']}")
        print(f"  • CC picks: {len(results['cc_picks'])}")
        print(f"  • CSP picks: {len(results['csp_picks'])}")
        print(f"  • Alerts sent: {results['alerts_sent']}")
        print(f"  • Duration: {results['duration']:.2f} seconds")

        # Show top picks
        if results['cc_picks']:
            print("\n📈 TOP COVERED CALLS:")
            for pick in results['cc_picks'][:3]:
                print(f"  • {pick['symbol']}: ${pick['strike']} ({pick['expiry']})")
                print(f"    ROI: {pick['roi_30d']:.2%}, IVR: {pick['iv_rank']:.0f}%, Score: {pick.get('score', 0):.2f}")

        if results['csp_picks']:
            print("\n💰 TOP CASH-SECURED PUTS:")
            for pick in results['csp_picks'][:3]:
                print(f"  • {pick['symbol']}: ${pick['strike']} ({pick['expiry']})")
                print(f"    ROI: {pick['roi_30d']:.2%}, IVR: {pick['iv_rank']:.0f}%, Score: {pick.get('score', 0):.2f}")

        print("\n" + "="*60)
        print("✅ PRODUCTION TEST COMPLETED!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    # Check environment
    polygon_key = os.getenv('POLYGON_API_KEY', '')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')

    print("🔑 API Keys Status:")
    print(f"  • Polygon: {'✅ Configured' if polygon_key and not polygon_key.startswith('mock') else '❌ Missing'}")
    print(f"  • Telegram: {'✅ Configured' if telegram_token and not telegram_token.startswith('mock') else '❌ Missing'}")
    print(f"  • Anthropic: {'✅ Configured' if anthropic_key and not anthropic_key.startswith('mock') else '❌ Missing'}")

    if run_test():
        print("\n🎉 System is ready for production use!")
        print("   Run 'python3.12 src/pipelines/daily_job.py' for full screening")
    else:
        print("\n⚠️ Please check the errors above")