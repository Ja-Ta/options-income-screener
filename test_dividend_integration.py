#!/usr/bin/env python3
"""
Quick test script for dividend integration.
Tests with a small subset of symbols including high-dividend stocks.
"""

import os
import sys
sys.path.insert(0, 'python_app/src')

from dotenv import load_dotenv
from pipelines.daily_job import ProductionPipeline

load_dotenv()
api_key = os.getenv('POLYGON_API_KEY')

# Test with 3 symbols: high dividend (PFE), medium (KO), low (AAPL)
test_symbols = ['PFE', 'KO', 'AAPL']

print("="*80)
print("DIVIDEND INTEGRATION TEST")
print("="*80)
print(f"Testing symbols: {test_symbols}")
print("Expected yields:")
print("  PFE:  ~7.04% (should boost CC score significantly)")
print("  KO:   ~2.89% (should boost CC score moderately)")
print("  AAPL: ~0.39% (minimal boost to CC score)")
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

if results['cc_picks']:
    print(f'\n📈 CC Picks with Dividend Data:')
    for pick in results['cc_picks'][:10]:
        div_yield = pick.get('dividend_yield', 0) * 100
        print(f'  {pick["symbol"]:6s} @ ${pick["strike"]:7.2f} | Score: {pick["score"]:.3f} | Div: {div_yield:.2f}%')

print('\n' + '='*80)
print('DIVIDEND IMPACT VALIDATION')
print('='*80)

# Group picks by symbol to compare
cc_by_symbol = {}
for pick in results['cc_picks']:
    symbol = pick['symbol']
    if symbol not in cc_by_symbol:
        cc_by_symbol[symbol] = []
    cc_by_symbol[symbol].append(pick)

for symbol in test_symbols:
    if symbol in cc_by_symbol:
        picks = cc_by_symbol[symbol]
        if picks:
            avg_score = sum(p['score'] for p in picks) / len(picks)
            div_yield = picks[0].get('dividend_yield', 0) * 100
            print(f"{symbol}: {len(picks)} CC picks, Avg Score: {avg_score:.3f}, Div Yield: {div_yield:.2f}%")

print('='*80)
