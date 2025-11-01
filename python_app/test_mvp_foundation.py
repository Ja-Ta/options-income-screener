#!/usr/bin/env python3
"""
Test script to verify MVP foundation components.

Tests the basic data flow and ensures all modules are working.
Run from project root: python3 python_app/test_mvp_foundation.py
"""

import sys
import os
from datetime import date
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from config import POLYGON_API_KEY, DB_URL
        from constants import MIN_PRICE, CC_MIN_IVR, USE_MOCK_DATA
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_polygon_client():
    """Test Polygon client with mock data."""
    print("\nTesting Polygon client...")
    try:
        from data.polygon_client import PolygonClient
        from utils.dates import get_today_market

        client = PolygonClient("mock_api_key")

        # Test universe loading
        symbols = client.get_universe()
        print(f"  Loaded {len(symbols)} symbols: {symbols}")

        # Test price data
        asof = get_today_market()
        prices = client.get_daily_prices(symbols[:2], asof)
        print(f"  Got prices for {len(prices)} symbols")

        # Test option chain
        if symbols:
            chain = client.get_option_chain(symbols[0], asof)
            print(f"  Got {len(chain)} option contracts for {symbols[0]}")

            # Check contract structure
            if chain:
                contract = chain[0]
                required_fields = ['symbol', 'strike', 'expiry', 'side', 'delta', 'iv', 'bid', 'ask']
                has_fields = all(field in contract for field in required_fields)
                print(f"  Contract has required fields: {has_fields}")

        print("✅ Polygon client working")
        return True
    except Exception as e:
        print(f"❌ Polygon client error: {e}")
        return False


def test_technical_indicators():
    """Test technical indicator calculations."""
    print("\nTesting technical indicators...")
    try:
        from features.technicals import compute_technical_features
        from data.polygon_client import PolygonClient
        from utils.dates import get_today_market

        client = PolygonClient("mock_api_key")
        symbols = client.get_universe()
        asof = get_today_market()

        if symbols:
            prices_data = client.get_daily_prices([symbols[0]], asof)
            if prices_data:
                price_data = list(prices_data.values())[0]
                features = compute_technical_features(price_data)

                print(f"  Calculated features for {symbols[0]}:")
                print(f"    SMA20: {features.get('sma20', 'N/A'):.2f}" if features.get('sma20') else "    SMA20: N/A")
                print(f"    HV20: {features.get('hv_20', 'N/A'):.2%}" if features.get('hv_20') else "    HV20: N/A")
                print(f"    Trend Strength: {features.get('trend_strength', 'N/A'):.2f}")
                print(f"    Above Support: {features.get('above_support', 'N/A')}")

        print("✅ Technical indicators working")
        return True
    except Exception as e:
        print(f"❌ Technical indicators error: {e}")
        return False


def test_iv_metrics():
    """Test IV metrics calculations."""
    print("\nTesting IV metrics...")
    try:
        from features.iv_metrics import calculate_iv_metrics
        from data.polygon_client import PolygonClient
        from utils.dates import get_today_market

        client = PolygonClient("mock_api_key")
        symbols = client.get_universe()
        asof = get_today_market()

        if symbols:
            chain = client.get_option_chain(symbols[0], asof)
            prices_data = client.get_daily_prices([symbols[0]], asof)

            if chain and prices_data:
                spot_price = list(prices_data.values())[0]['close']
                iv_data = calculate_iv_metrics(chain, spot_price)

                print(f"  IV Metrics for {symbols[0]}:")
                print(f"    Current IV: {iv_data['iv_current']:.2%}")
                print(f"    IV Rank: {iv_data['iv_rank']:.1f}%")
                print(f"    IV Percentile: {iv_data['iv_percentile']:.1f}%")

        print("✅ IV metrics working")
        return True
    except Exception as e:
        print(f"❌ IV metrics error: {e}")
        return False


def test_database():
    """Test database connection."""
    print("\nTesting database...")
    try:
        import sqlite3

        conn = sqlite3.connect("data/screener.db")
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['symbols', 'prices', 'options', 'iv_metrics', 'picks', 'rationales', 'alerts']
        all_present = all(table in tables for table in expected_tables)

        print(f"  Found {len(tables)} tables")
        print(f"  All required tables present: {all_present}")

        conn.close()
        print("✅ Database working")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Options Income Screener - MVP Foundation Test")
    print("=" * 60)

    # Initialize logging
    from utils.logging import initialize_logging
    initialize_logging(debug=True)

    tests = [
        test_imports,
        test_polygon_client,
        test_technical_indicators,
        test_iv_metrics,
        test_database
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Passed: {sum(results)}/{len(results)}")
    print(f"  Status: {'✅ All tests passed!' if all(results) else '❌ Some tests failed'}")
    print("=" * 60)

    if all(results):
        print("\n🎉 MVP foundation is ready!")
        print("\nNext steps to complete the MVP:")
        print("  1. Implement screening logic (covered_calls.py, cash_secured_puts.py)")
        print("  2. Implement scoring algorithms (score_cc.py, score_csp.py)")
        print("  3. Implement storage DAO layer")
        print("  4. Implement service stubs (Telegram, Claude)")
        print("  5. Implement daily job orchestration")
        print("  6. Complete Node.js API endpoints")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())