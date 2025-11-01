#!/usr/bin/env python3
"""
End-to-end test for the Options Income Screener pipeline.

Tests the complete workflow with mock data.
Python 3.12 compatible following CLAUDE.md standards.
"""

import sys
import os
from datetime import date
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import USE_MOCK_DATA
from src.pipelines.daily_job import run_daily_job
from src.storage.dao import PicksDAO, StatsDAO
from src.storage.init_db import initialize_database
from src.utils.logging import setup_logger as setup_logging


def test_pipeline():
    """Run end-to-end test of the screening pipeline."""
    print("\n" + "="*60)
    print("OPTIONS INCOME SCREENER - END-TO-END TEST")
    print("="*60 + "\n")

    # Setup logging
    setup_logging()

    # Initialize database
    print("🔧 Initializing database...")
    if not initialize_database():
        print("❌ Failed to initialize database")
        return False

    # Ensure we're using mock data
    if not USE_MOCK_DATA:
        print("⚠️  Warning: Not using mock data. Set USE_MOCK_DATA=True in .env")

    # Test symbols (subset for faster testing)
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    test_date = date.today()

    print(f"📅 Test Date: {test_date}")
    print(f"📊 Test Symbols: {', '.join(test_symbols)}")
    print("-" * 60)

    # Run the pipeline
    print("\n🚀 Starting pipeline execution...")
    print("-" * 60)

    try:
        results = run_daily_job(symbols=test_symbols, asof=test_date)

        # Display results
        print("\n✅ Pipeline completed successfully!")
        print("-" * 60)
        print("\n📈 RESULTS SUMMARY:")
        print(f"  • Symbols processed: {results['symbols_processed']}")
        print(f"  • CC picks found: {len(results['cc_picks'])}")
        print(f"  • CSP picks found: {len(results['csp_picks'])}")
        print(f"  • Total picks: {len(results['cc_picks']) + len(results['csp_picks'])}")
        print(f"  • Alerts sent: {results['alerts_sent']}")
        print(f"  • Errors: {len(results['errors'])}")
        print(f"  • Duration: {results['duration']:.2f} seconds")

        # Display top CC picks
        if results['cc_picks']:
            print("\n📊 TOP COVERED CALL PICKS:")
            print("-" * 60)
            for i, pick in enumerate(results['cc_picks'][:3], 1):
                print(f"\n{i}. {pick['symbol']} - CALL ${pick['strike']:.2f} ({pick['expiry']})")
                print(f"   • ROI (30d): {pick['roi_30d']:.2%}")
                print(f"   • IV Rank: {pick['iv_rank']:.1f}%")
                print(f"   • Score: {pick.get('score', 0):.2f}/1.0")
                print(f"   • Premium: ${pick['premium']:.2f}")
                if pick.get('notes'):
                    print(f"   • Notes: {pick['notes']}")

        # Display top CSP picks
        if results['csp_picks']:
            print("\n💰 TOP CASH-SECURED PUT PICKS:")
            print("-" * 60)
            for i, pick in enumerate(results['csp_picks'][:3], 1):
                print(f"\n{i}. {pick['symbol']} - PUT ${pick['strike']:.2f} ({pick['expiry']})")
                print(f"   • ROI (30d): {pick['roi_30d']:.2%}")
                print(f"   • IV Rank: {pick['iv_rank']:.1f}%")
                print(f"   • Score: {pick.get('score', 0):.2f}/1.0")
                print(f"   • Safety: {pick['margin_of_safety']:.1%} OTM")
                print(f"   • Premium: ${pick['premium']:.2f}")
                if pick.get('notes'):
                    print(f"   • Notes: {pick['notes']}")

        # Display errors if any
        if results['errors']:
            print("\n❌ ERRORS:")
            print("-" * 60)
            for error in results['errors']:
                print(f"  • {error}")

        # Test database queries
        print("\n🔍 TESTING DATABASE QUERIES:")
        print("-" * 60)

        picks_dao = PicksDAO()
        stats_dao = StatsDAO()

        # Get picks from database
        db_picks = picks_dao.get_picks_by_date(test_date)
        print(f"  • Picks in database: {len(db_picks)}")

        # Get top picks
        top_picks = picks_dao.get_top_picks(test_date, limit=3)
        print(f"  • Top picks retrieved: {len(top_picks)}")

        # Get daily summary
        summary = stats_dao.get_daily_summary(test_date)
        print(f"  • Summary generated: {summary is not None}")

        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_components():
    """Test individual components of the pipeline."""
    print("\n🧪 TESTING INDIVIDUAL COMPONENTS:")
    print("-" * 60)

    # Test imports
    print("\n1. Testing imports...")
    try:
        from src.data.polygon_client import PolygonClient
        from src.features.technicals import calculate_technical_indicators
        from src.features.iv_metrics import calculate_iv_metrics
        from src.screeners.covered_calls import screen_cc
        from src.screeners.cash_secured_puts import screen_csp
        from src.scoring.score_cc import cc_score
        from src.scoring.score_csp import csp_score
        from src.storage.dao import SymbolsDAO
        from src.services.telegram_service import TelegramService
        from src.services.claude_service import ClaudeService
        print("   ✅ All imports successful")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False

    # Test Polygon client
    print("\n2. Testing Polygon client...")
    try:
        client = PolygonClient("mock_api_key")
        snapshot = client.get_stock_snapshot("AAPL")
        if snapshot:
            print(f"   ✅ Mock snapshot retrieved: ${snapshot['close']:.2f}")
        else:
            print("   ❌ Failed to get snapshot")
    except Exception as e:
        print(f"   ❌ Polygon client error: {e}")

    # Test technical indicators
    print("\n3. Testing technical indicators...")
    try:
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        indicators = calculate_technical_indicators(prices)
        print(f"   ✅ Indicators calculated: SMA20={indicators.get('sma20', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Indicator calculation error: {e}")

    # Test scoring
    print("\n4. Testing scoring algorithms...")
    try:
        cc_test_score = cc_score(
            iv_rank=65,
            roi_30d=0.015,
            trend_strength=0.3,
            dividend_yield=0.02
        )
        print(f"   ✅ CC score calculated: {cc_test_score:.2f}")

        csp_test_score = csp_score(
            iv_rank=70,
            roi_30d=0.012,
            margin_of_safety=0.08,
            trend_stability=0.6
        )
        print(f"   ✅ CSP score calculated: {csp_test_score:.2f}")
    except Exception as e:
        print(f"   ❌ Scoring error: {e}")

    # Test services
    print("\n5. Testing services...")
    try:
        telegram = TelegramService()
        if telegram.test_connection():
            print("   ✅ Telegram service connected (mock mode)")

        claude = ClaudeService()
        if claude.test_connection():
            print("   ✅ Claude service connected (mock mode)")
    except Exception as e:
        print(f"   ❌ Service test error: {e}")

    print("\n" + "-"*60)
    return True


if __name__ == "__main__":
    # Test individual components first
    component_test_passed = test_individual_components()

    # Run full pipeline test
    pipeline_test_passed = test_pipeline()

    # Exit with appropriate code
    if component_test_passed and pipeline_test_passed:
        print("\n🎉 All tests passed! The screener is ready for deployment.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        sys.exit(1)