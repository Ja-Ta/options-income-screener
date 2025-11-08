#!/usr/bin/env python3
"""
Quick test script for earnings integration.
Tests the full pipeline with a small subset of symbols.
"""

import os
import sys
sys.path.insert(0, 'python_app/src')

from dotenv import load_dotenv
from pipelines.daily_job import ProductionPipeline

load_dotenv()
api_key = os.getenv('POLYGON_API_KEY')

# Test with 3 symbols including NVDA (has earnings in 11 days)
test_symbols = ['NVDA', 'AAPL', 'SPY']

print("="*80)
print("EARNINGS INTEGRATION TEST")
print("="*80)
print(f"Testing symbols: {test_symbols}")
print(f"NVDA has confirmed earnings on 2025-11-19 (11 days from today)")
print("Expected: NVDA picks should have significantly reduced scores")
print("="*80)
print()

pipeline = ProductionPipeline(api_key=api_key, symbols=test_symbols, max_retries=2)
results = pipeline.run()

print('\n' + '='*80)
print('TEST RESULTS')
print('='*80)
print(f'Symbols attempted: {results["stats"]["symbols_attempted"]}')
print(f'Symbols succeeded: {results["stats"]["symbols_succeeded"]}')
print(f'Total picks: {results["stats"]["total_picks"]}')
print(f'CC picks: {results["stats"]["cc_picks"]}')
print(f'CSP picks: {results["stats"]["csp_picks"]}')
print(f'Errors: {len(results["stats"]["errors"])}')

if results['cc_picks']:
    print(f'\n📈 Top CC Picks (sorted by score):')
    for pick in results['cc_picks'][:5]:
        earnings_info = f"{pick.get('earnings_days_until', 999)} days" if pick.get('earnings_days_until') != 999 else "No data"
        print(f'  {pick["symbol"]:6s} @ ${pick["strike"]:7.2f} | Score: {pick["score"]:.3f} | Earnings: {earnings_info}')

if results['csp_picks']:
    print(f'\n💰 Top CSP Picks (sorted by score):')
    for pick in results['csp_picks'][:5]:
        earnings_info = f"{pick.get('earnings_days_until', 999)} days" if pick.get('earnings_days_until') != 999 else "No data"
        print(f'  {pick["symbol"]:6s} @ ${pick["strike"]:7.2f} | Score: {pick["score"]:.3f} | Earnings: {earnings_info}')

print('\n' + '='*80)
print('EARNINGS PENALTY VALIDATION')
print('='*80)

# Check if NVDA picks have appropriate penalties
nvda_picks = [p for p in (results['cc_picks'] + results['csp_picks']) if p['symbol'] == 'NVDA']
if nvda_picks:
    nvda_pick = nvda_picks[0]
    earnings_days = nvda_pick.get('earnings_days_until', 999)
    print(f"NVDA earnings in {earnings_days} days")
    if earnings_days < 14:
        print("✅ EXPECTED: Strong penalty applied (earnings <14 days)")
        print(f"   Penalty applied: 30% reduction (0.70x multiplier)")
    else:
        print("⚠️  UNEXPECTED: No strong penalty (earnings >14 days)")
else:
    print("⚠️  WARNING: No NVDA picks found")

print('='*80)
