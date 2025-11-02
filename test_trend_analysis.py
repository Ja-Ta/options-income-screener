#!/usr/bin/env python3
"""
Test script for trend analysis integration.
Tests historical data fetching and technical indicator calculations.
"""

import os
import sys
from dotenv import load_dotenv

# Add python_app to path
sys.path.insert(0, '/home/oisadm/development/options-income-screener/python_app')

from src.data.real_options_fetcher import RealOptionsFetcher
from src.features.technicals import compute_technical_features
from src.constants import HISTORICAL_DAYS_TO_FETCH

# Load environment
load_dotenv()

def test_trend_analysis(symbol: str = 'AAPL'):
    """Test trend analysis for a single symbol."""
    print(f"\n{'='*60}")
    print(f"Testing Trend Analysis for {symbol}")
    print(f"{'='*60}\n")

    # Initialize fetcher
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("ERROR: POLYGON_API_KEY not found in environment")
        return

    fetcher = RealOptionsFetcher(api_key)

    # Test 1: Fetch stock price
    print(f"1. Fetching current stock price for {symbol}...")
    stock_price = fetcher.get_stock_price(symbol)
    if stock_price:
        print(f"   ✓ Stock price: ${stock_price:.2f}\n")
    else:
        print(f"   ✗ Failed to fetch stock price\n")
        return

    # Test 2: Fetch historical price data
    print(f"2. Fetching {HISTORICAL_DAYS_TO_FETCH} days of historical data...")
    historical_data = fetcher.get_historical_prices(symbol, days=HISTORICAL_DAYS_TO_FETCH)

    if not historical_data:
        print(f"   ✗ Failed to fetch historical data\n")
        return

    bars = len(historical_data.get('prices', []))
    print(f"   ✓ Fetched {bars} bars of historical data")

    if bars < 200:
        print(f"   ⚠ Warning: Only {bars} bars (need 200+ for SMA200)")
    print()

    # Test 3: Compute technical features
    print(f"3. Computing technical features...")
    price_data = {
        'close': stock_price,
        'prices': historical_data['prices'],
        'highs': historical_data.get('highs'),
        'lows': historical_data.get('lows')
    }

    technical_features = compute_technical_features(price_data)

    if not technical_features:
        print(f"   ✗ Failed to compute technical features\n")
        return

    print(f"   ✓ Technical features computed successfully\n")

    # Test 4: Display results
    print(f"4. Technical Analysis Results:")
    print(f"   {'─'*55}")

    # SMAs
    print(f"\n   Simple Moving Averages:")
    sma20 = technical_features.get('sma20')
    sma50 = technical_features.get('sma50')
    sma200 = technical_features.get('sma200')

    print(f"     SMA 20:  ${sma20:>8.2f}" if sma20 else "     SMA 20:  N/A")
    print(f"     SMA 50:  ${sma50:>8.2f}" if sma50 else "     SMA 50:  N/A")
    print(f"     SMA 200: ${sma200:>8.2f}" if sma200 else "     SMA 200: N/A (insufficient data)")
    print(f"     Current: ${stock_price:>8.2f}")

    # Volatility
    print(f"\n   Historical Volatility:")
    print(f"     HV 20:   {technical_features.get('hv_20', 0):>8.2%}")
    print(f"     HV 60:   {technical_features.get('hv_60', 0):>8.2%}")

    # RSI
    rsi = technical_features.get('rsi')
    if rsi:
        print(f"\n   Momentum:")
        print(f"     RSI:     {rsi:>8.1f}")
        if rsi > 70:
            print(f"              (Overbought)")
        elif rsi < 30:
            print(f"              (Oversold)")
        else:
            print(f"              (Neutral)")

    # Trend Strength
    trend_strength = technical_features.get('trend_strength', 0)
    print(f"\n   Trend Strength: {trend_strength:>6.2f}")
    if trend_strength > 0.5:
        print(f"                   (Strong Uptrend)")
    elif trend_strength > 0:
        print(f"                   (Weak Uptrend)")
    elif trend_strength > -0.5:
        print(f"                   (Weak Downtrend)")
    else:
        print(f"                   (Strong Downtrend)")

    # Trend Stability
    trend_stability = technical_features.get('trend_stability', 0)
    print(f"\n   Trend Stability: {trend_stability:>5.2f}")
    if trend_stability > 0.7:
        print(f"                    (Very Stable)")
    elif trend_stability > 0.4:
        print(f"                    (Moderately Stable)")
    else:
        print(f"                    (Volatile)")

    # Boolean Indicators
    print(f"\n   Trend Indicators:")
    print(f"     In Uptrend:        {technical_features.get('in_uptrend', False)}")
    print(f"     Above 200 SMA:     {technical_features.get('above_support', False)}")
    print(f"     Below 200 SMA:     {technical_features.get('below_200sma', False)}")

    # Momentum Score
    momentum = technical_features.get('momentum_score', 0)
    print(f"\n   Momentum Score: {momentum:>6.2f}")

    print(f"\n   {'─'*55}\n")
    print(f"✓ All tests passed for {symbol}\n")


if __name__ == "__main__":
    # Test with multiple symbols
    test_symbols = ['AAPL', 'NBIS', 'HOOD']

    for symbol in test_symbols:
        try:
            test_trend_analysis(symbol)
        except Exception as e:
            print(f"\n✗ Error testing {symbol}: {e}\n")

    print(f"\n{'='*60}")
    print("Trend Analysis Testing Complete")
    print(f"{'='*60}\n")
