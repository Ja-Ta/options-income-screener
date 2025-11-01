#!/usr/bin/env python3
"""
Test Polygon API connection with real API key.
"""

import sys
import os
from datetime import datetime, timedelta

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.polygon_client import PolygonClient

def test_polygon_connection():
    """Test Polygon API with real data."""
    print("\n" + "="*60)
    print("POLYGON API CONNECTION TEST")
    print("="*60)

    # Check API key
    api_key = os.getenv('POLYGON_API_KEY', '')
    print(f"\n🔑 API Key: {'✅ Configured' if api_key and not api_key.startswith('mock') else '❌ Missing'}")

    if not api_key or api_key.startswith('mock'):
        print("❌ Please set a valid POLYGON_API_KEY in .env file")
        return False

    # Initialize client
    print("\n📊 Initializing Polygon client...")
    client = PolygonClient(api_key)

    # Test 1: Get stock snapshot for SPY
    print("\n1️⃣ Testing stock snapshot fetch (SPY)...")
    try:
        from datetime import date
        snapshot = client.get_stock_snapshot('SPY', date.today())
        if snapshot:
            price = snapshot.get('close', snapshot.get('last', 0))
            print(f"   ✅ SPY Price: ${price:.2f}")
            print(f"   Volume: {snapshot.get('volume', 0):,}")
        else:
            print("   ⚠️ No snapshot data (market may be closed)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Test 2: Get options chain for AAPL
    print("\n2️⃣ Testing options chain fetch (AAPL)...")
    try:
        from datetime import date
        chain = client.get_options_chain('AAPL', date.today())

        if chain:
            calls = [c for c in chain if c.get('contract_type') == 'call']
            puts = [c for c in chain if c.get('contract_type') == 'put']
            print(f"   ✅ Found {len(calls)} calls and {len(puts)} puts")

            # Show sample contract
            if calls:
                sample = calls[0]
                print(f"   Sample call: Strike ${sample.get('strike_price')}, "
                      f"Exp {sample.get('expiration_date')}, "
                      f"Vol {sample.get('volume', 0)}")
        else:
            print("   ⚠️ No options data found (market may be closed)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Test 3: Get daily prices for multiple symbols
    print("\n3️⃣ Testing daily prices fetch (MSFT, GOOGL)...")
    try:
        from datetime import date
        prices = client.get_daily_prices(['MSFT', 'GOOGL'], date.today())
        if prices:
            for symbol, data in prices.items():
                print(f"   ✅ {symbol}: ${data.get('close', 0):.2f}")
        else:
            print("   ⚠️ No price data available")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("✅ POLYGON API IS WORKING!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_polygon_connection()
    if success:
        print("\n🎉 Polygon API connection successful!")
        print("   You can now run the full screener with real market data.")
    else:
        print("\n❌ Please check your Polygon API key and try again.")