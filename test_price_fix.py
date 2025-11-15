#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'python_app')

from src.data.real_options_fetcher import RealOptionsFetcher
from src.features.technicals import calculate_chaikin_money_flow

api_key = os.getenv('POLYGON_API_KEY')
fetcher = RealOptionsFetcher(api_key)

print("Testing historical price fix...")
result = fetcher.get_historical_prices('SPY', days=60)

if result:
    print(f'✅ SUCCESS! Fetched {len(result["prices"])} bars')
    print(f'   Price range: ${result["prices"][0]:.2f} - ${result["prices"][-1]:.2f}')
    print(f'   Volumes available: {len(result["volumes"])} days')

    # Test CMF calculation
    cmf = calculate_chaikin_money_flow(
        result['highs'], result['lows'], result['prices'], result['volumes'], period=20
    )
    if cmf is not None:
        print(f'   ✅ CMF (20-day): {cmf:+.3f}')
        print(f'\n🎉 FIX SUCCESSFUL - CMF calculation working!')
    else:
        print('   ❌ CMF calculation failed')
else:
    print('❌ FAILED: No data returned')
