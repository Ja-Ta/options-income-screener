#!/usr/bin/env python3
"""
Test Polygon API with free tier endpoints.
"""

import os
import sys
from datetime import datetime, timedelta
import requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_polygon_free_tier():
    """Test Polygon API with free tier compatible endpoints."""
    print("\n" + "="*60)
    print("POLYGON API FREE TIER TEST")
    print("="*60)

    api_key = os.getenv('POLYGON_API_KEY', '')
    if not api_key or api_key.startswith('mock'):
        print("❌ Please set a valid POLYGON_API_KEY in .env file")
        return False

    print(f"\n🔑 API Key: Configured")

    # Test 1: Ticker Details (Free tier)
    print("\n1️⃣ Testing ticker details (AAPL)...")
    url = f"https://api.polygon.io/v3/reference/tickers/AAPL?apiKey={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'OK':
            ticker = data.get('results', {})
            print(f"   ✅ AAPL Details:")
            print(f"      Name: {ticker.get('name', 'N/A')}")
            print(f"      Type: {ticker.get('type', 'N/A')}")
            print(f"      Market Cap: {ticker.get('market_cap', 'N/A')}")
        else:
            print(f"   ❌ Error: {data.get('message', 'Unknown error')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")

    # Test 2: Previous Close (Free tier - delayed data)
    print("\n2️⃣ Testing previous close (SPY)...")
    url = f"https://api.polygon.io/v2/aggs/ticker/SPY/prev?apiKey={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'OK':
            results = data.get('results', [])
            if results:
                bar = results[0]
                print(f"   ✅ SPY Previous Close:")
                print(f"      Date: {datetime.fromtimestamp(bar['t']/1000).strftime('%Y-%m-%d')}")
                print(f"      Close: ${bar['c']:.2f}")
                print(f"      Volume: {bar['v']:,}")
            else:
                print("   ⚠️ No data available")
        else:
            print(f"   ❌ Error: {data.get('message', 'Unknown error')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")

    # Test 3: Aggregates (Free tier - limited history)
    print("\n3️⃣ Testing aggregates (MSFT - last 5 days)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    url = f"https://api.polygon.io/v2/aggs/ticker/MSFT/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}?apiKey={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'OK':
            results = data.get('results', [])
            print(f"   ✅ MSFT Recent Data ({len(results)} days):")
            for bar in results[-3:]:  # Show last 3 days
                date = datetime.fromtimestamp(bar['t']/1000).strftime('%Y-%m-%d')
                print(f"      {date}: ${bar['c']:.2f} (Vol: {bar['v']:,})")
        else:
            print(f"   ❌ Error: {data.get('message', 'Unknown error')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")

    # Test 4: Options Contracts (if available)
    print("\n4️⃣ Testing options contracts list (AAPL)...")
    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker=AAPL&limit=5&apiKey={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'OK':
            results = data.get('results', [])
            if results:
                print(f"   ✅ Found {len(results)} option contracts")
                for contract in results[:2]:  # Show first 2
                    print(f"      {contract.get('ticker', 'N/A')}")
            else:
                print("   ⚠️ No options data (may require higher tier)")
        elif "NOT_AUTHORIZED" in str(data.get('status')):
            print("   ⚠️ Options data requires higher tier subscription")
        else:
            print(f"   ❌ Error: {data.get('message', 'Unknown error')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")

    print("\n" + "="*60)
    print("POLYGON API TEST COMPLETE")
    print("="*60)
    print("\nNOTE: Your API tier may have limitations:")
    print("• Free tier: 5 API calls/minute, delayed data")
    print("• Starter: Real-time stocks, no options")
    print("• Developer+: Includes options data")
    print("\nFor full functionality, you may need to upgrade at:")
    print("https://polygon.io/pricing")

    return True

if __name__ == "__main__":
    test_polygon_free_tier()