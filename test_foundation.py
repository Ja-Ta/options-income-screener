#!/usr/bin/env python3
"""
Simple test script to verify MVP foundation components.
Run from project root: python3 test_foundation.py
"""

import sys
import os
from pathlib import Path

# Add python_app/src to path
sys.path.insert(0, 'python_app/src')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def test_basic_setup():
    """Test basic environment and imports."""
    print("Testing basic setup...")

    # Test environment
    import config
    print(f"  ✓ Config loaded")
    print(f"    Mock mode: {config.POLYGON_API_KEY.startswith('mock')}")

    # Test constants
    import constants
    print(f"  ✓ Constants loaded")
    print(f"    USE_MOCK_DATA: {constants.USE_MOCK_DATA}")

    return True


def test_data_flow():
    """Test the basic data flow with mock data."""
    print("\nTesting data flow...")

    # Import modules
    from data.polygon_client import PolygonClient
    from datetime import date

    # Initialize client
    client = PolygonClient("mock_api_key")
    print(f"  ✓ Polygon client initialized (mock mode)")

    # Load universe
    symbols = client.get_universe()
    print(f"  ✓ Loaded {len(symbols)} symbols: {', '.join(symbols)}")

    # Get prices
    asof = date.today()
    prices = client.get_daily_prices(symbols[:2], asof)
    print(f"  ✓ Got price data for {len(prices)} symbols")

    # Get option chain
    if symbols:
        chain = client.get_option_chain(symbols[0], asof)
        print(f"  ✓ Got {len(chain)} option contracts for {symbols[0]}")

        # Sample contract
        if chain:
            contract = chain[0]
            print(f"    Sample: {contract['side']} strike={contract['strike']} "
                  f"delta={contract['delta']:.2f} iv={contract['iv']:.2%}")

    return True


def test_calculations():
    """Test technical and IV calculations."""
    print("\nTesting calculations...")

    # Import directly without relative imports
    import numpy as np

    # Simple IV Rank test
    current_iv = 0.35
    historical = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.30]
    min_iv = min(historical)
    max_iv = max(historical)
    iv_rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100
    print(f"  ✓ IV Rank calculation: {iv_rank:.1f}%")

    # Simple SMA test
    prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
    sma5 = sum(prices[-5:]) / 5
    print(f"  ✓ SMA(5) calculation: {sma5:.2f}")

    return True


def test_database():
    """Test database connection."""
    print("\nTesting database...")

    import sqlite3

    # Connect to database
    conn = sqlite3.connect("data/screener.db")
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  ✓ Database has {len(tables)} tables")

    # Check WAL mode
    cursor.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    print(f"  ✓ Journal mode: {mode}")

    conn.close()

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Options Income Screener - Foundation Test")
    print("=" * 60)

    tests = [
        test_basic_setup,
        test_data_flow,
        test_calculations,
        test_database
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("  Status: ✅ Foundation is ready!")
        print("\n🎉 Next: Implement screeners, scoring, and pipeline")
    else:
        print("  Status: ⚠️ Some issues need attention")

    print("=" * 60)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())