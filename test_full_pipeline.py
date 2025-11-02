#!/usr/bin/env python3
"""
Full pipeline test with trend analysis integration.
Tests the complete daily screening workflow with real API data.
"""

import os
import sys
import time
from datetime import date
from dotenv import load_dotenv

# Add python_app to path
sys.path.insert(0, '/home/oisadm/development/options-income-screener/python_app')

from src.pipelines.daily_job import ProductionPipeline

# Load environment
load_dotenv()

def test_full_pipeline():
    """Run full pipeline test with small universe."""
    print("\n" + "="*70)
    print("FULL PIPELINE TEST - Trend Analysis Integration")
    print("="*70 + "\n")

    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("ERROR: POLYGON_API_KEY not found in environment")
        return

    # Test with small universe (3 symbols for speed)
    test_symbols = ['AAPL', 'NBIS', 'HOOD']

    print(f"Testing with {len(test_symbols)} symbols: {', '.join(test_symbols)}")
    print(f"Date: {date.today()}")
    print()

    # Initialize pipeline
    print("1. Initializing pipeline...")
    pipeline = ProductionPipeline(
        api_key=api_key,
        symbols=test_symbols,
        max_retries=2,
        retry_delay=3
    )
    print("   ✓ Pipeline initialized\n")

    # Run screening
    print("2. Running screening workflow...")
    start_time = time.time()

    try:
        all_picks = []

        for symbol in test_symbols:
            print(f"\n   Screening {symbol}...")
            result = pipeline.screen_symbol_with_retry(symbol)

            cc_picks = result.get('cc_picks', [])
            csp_picks = result.get('csp_picks', [])

            all_picks.extend(cc_picks)
            all_picks.extend(csp_picks)

            print(f"     → {len(cc_picks)} CC picks, {len(csp_picks)} CSP picks")

            # Display top pick details if available
            if cc_picks:
                top_cc = cc_picks[0]
                print(f"     → Top CC: ${top_cc['strike']:.0f} strike, "
                      f"score={top_cc.get('score', 0):.4f}, "
                      f"trend_strength={top_cc.get('trend_strength', 0):.2f}, "
                      f"trend={top_cc.get('trend', 'N/A')}")

            if csp_picks:
                top_csp = csp_picks[0]
                print(f"     → Top CSP: ${top_csp['strike']:.0f} strike, "
                      f"score={top_csp.get('score', 0):.4f}, "
                      f"trend_stability={top_csp.get('trend_stability', 0):.2f}, "
                      f"in_uptrend={top_csp.get('in_uptrend', False)}")

        elapsed = time.time() - start_time

        print(f"\n   ✓ Screening complete in {elapsed:.1f} seconds")
        print(f"   ✓ Total picks generated: {len(all_picks)}")

    except Exception as e:
        print(f"\n   ✗ Screening failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Analyze results
    print("\n3. Analyzing results...")

    cc_picks = [p for p in all_picks if p.get('strategy') == 'CC']
    csp_picks = [p for p in all_picks if p.get('strategy') == 'CSP']

    print(f"   → CC picks:  {len(cc_picks)}")
    print(f"   → CSP picks: {len(csp_picks)}")

    if not all_picks:
        print("\n   ⚠ No picks generated - this may indicate an issue")
        return

    # Check trend analysis integration
    print("\n4. Verifying trend analysis integration...")

    trend_fields_present = {
        'trend_strength': 0,
        'trend_stability': 0,
        'trend': 0,
        'in_uptrend': 0,
        'below_200sma': 0
    }

    for pick in all_picks:
        if 'trend_strength' in pick and pick['trend_strength'] != 0:
            trend_fields_present['trend_strength'] += 1
        if 'trend_stability' in pick:
            trend_fields_present['trend_stability'] += 1
        if 'trend' in pick and pick['trend'] != 'neutral':
            trend_fields_present['trend'] += 1
        if 'in_uptrend' in pick:
            trend_fields_present['in_uptrend'] += 1
        if 'below_200sma' in pick:
            trend_fields_present['below_200sma'] += 1

    print(f"   → trend_strength populated: {trend_fields_present['trend_strength']}/{len(all_picks)}")
    print(f"   → trend_stability populated: {trend_fields_present['trend_stability']}/{len(all_picks)}")
    print(f"   → trend classification: {trend_fields_present['trend']}/{len(all_picks)} non-neutral")
    print(f"   → in_uptrend field: {trend_fields_present['in_uptrend']}/{len(all_picks)}")
    print(f"   → below_200sma field: {trend_fields_present['below_200sma']}/{len(all_picks)}")

    # Display top 5 picks by strategy
    print("\n5. Top Picks Summary:")
    print("   " + "-"*66)

    print("\n   TOP 3 COVERED CALLS:")
    cc_sorted = sorted(cc_picks, key=lambda x: x.get('score', 0), reverse=True)[:3]
    for i, pick in enumerate(cc_sorted, 1):
        print(f"\n   {i}. {pick['symbol']} ${pick['strike']:.0f} Call "
              f"(Exp: {pick.get('expiry', 'N/A')})")
        print(f"      Score:          {pick.get('score', 0):.4f}")
        print(f"      Premium:        ${pick.get('premium', 0):.2f}")
        print(f"      ROI (30d):      {pick.get('roi_30d', 0):.2%}")
        print(f"      Delta:          {pick.get('delta', 0):.3f}")
        print(f"      Theta:          {pick.get('theta', 0):.4f}")
        print(f"      IV Rank:        {pick.get('iv_rank', 0):.1f}%")
        print(f"      Trend Strength: {pick.get('trend_strength', 0):+.2f} ({pick.get('trend', 'N/A')})")
        print(f"      Below 200 SMA:  {pick.get('below_200sma', False)}")

    print("\n   TOP 3 CASH-SECURED PUTS:")
    csp_sorted = sorted(csp_picks, key=lambda x: x.get('score', 0), reverse=True)[:3]
    for i, pick in enumerate(csp_sorted, 1):
        print(f"\n   {i}. {pick['symbol']} ${pick['strike']:.0f} Put "
              f"(Exp: {pick.get('expiry', 'N/A')})")
        print(f"      Score:            {pick.get('score', 0):.4f}")
        print(f"      Premium:          ${pick.get('premium', 0):.2f}")
        print(f"      ROI (30d):        {pick.get('roi_30d', 0):.2%}")
        print(f"      Delta:            {pick.get('delta', 0):.3f}")
        print(f"      Theta:            {pick.get('theta', 0):.4f}")
        print(f"      IV Rank:          {pick.get('iv_rank', 0):.1f}%")
        print(f"      Margin of Safety: {pick.get('margin_of_safety', 0):.2%}")
        print(f"      Trend Stability:  {pick.get('trend_stability', 0):.2f}")
        print(f"      In Uptrend:       {pick.get('in_uptrend', False)}")

    # Final validation
    print("\n6. Validation Summary:")
    print("   " + "-"*66)

    checks = {
        'Picks generated': len(all_picks) > 0,
        'Scores calculated': all(p.get('score', 0) > 0 for p in all_picks),
        'Greeks present': all(p.get('delta') is not None for p in all_picks),
        'Trend analysis active': trend_fields_present['trend_strength'] > 0,
        'Trend classification': trend_fields_present['trend'] > 0,
        'Pipeline completes': True
    }

    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"   {status} {check}")

    all_passed = all(checks.values())

    print("\n" + "="*70)
    if all_passed:
        print("✓ PIPELINE TEST PASSED - All systems operational")
    else:
        print("✗ PIPELINE TEST FAILED - Issues detected")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
