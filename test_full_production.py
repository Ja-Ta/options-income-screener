#!/usr/bin/env python3
"""
Full production screening test with complete 19-symbol universe.
Tests trend analysis integration with real production workflow.
"""

import os
import sys
import time
from datetime import date, datetime
from dotenv import load_dotenv

# Add python_app to path
sys.path.insert(0, '/home/oisadm/development/options-income-screener/python_app')

from src.pipelines.daily_job import ProductionPipeline

# Load environment
load_dotenv()

def test_full_production_screening():
    """Run full production screening test with all 19 symbols."""
    print("\n" + "="*80)
    print("FULL PRODUCTION SCREENING TEST - 19 Symbol Universe")
    print("="*80 + "\n")

    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("ERROR: POLYGON_API_KEY not found in environment")
        return False

    print(f"Date: {date.today()}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Initialize pipeline with full universe
    print("1. Initializing pipeline with full universe...")
    start_init = time.time()

    try:
        pipeline = ProductionPipeline(
            api_key=api_key,
            symbols=None,  # Load from universe.csv
            max_retries=3,
            retry_delay=5
        )
        init_time = time.time() - start_init
        print(f"   ✓ Pipeline initialized in {init_time:.1f}s")
        print(f"   ✓ Loaded {len(pipeline.symbols)} symbols from universe")
        print(f"   ✓ Universe: {', '.join(pipeline.symbols)}\n")
    except Exception as e:
        print(f"   ✗ Pipeline initialization failed: {e}")
        return False

    # Run full screening
    print("2. Running full production screening...")
    print("   " + "-"*76)

    start_time = time.time()
    all_picks = []
    symbol_results = {}
    trend_stats = {
        'symbols_with_data': 0,
        'uptrends': 0,
        'downtrends': 0,
        'neutral': 0,
        'avg_trend_strength': 0,
        'avg_trend_stability': 0
    }

    for i, symbol in enumerate(pipeline.symbols, 1):
        symbol_start = time.time()

        try:
            print(f"\n   [{i:2d}/{len(pipeline.symbols)}] Screening {symbol:6s}", end="", flush=True)

            result = pipeline.screen_symbol_with_retry(symbol)

            cc_picks = result.get('cc_picks', [])
            csp_picks = result.get('csp_picks', [])

            all_picks.extend(cc_picks)
            all_picks.extend(csp_picks)

            symbol_time = time.time() - symbol_start

            symbol_results[symbol] = {
                'cc_count': len(cc_picks),
                'csp_count': len(csp_picks),
                'time': symbol_time
            }

            # Collect trend statistics
            if cc_picks or csp_picks:
                sample_pick = cc_picks[0] if cc_picks else csp_picks[0]
                trend_strength = sample_pick.get('trend_strength', 0)

                if 'trend_stability' in sample_pick:
                    trend_stability = sample_pick.get('trend_stability', 0.5)
                else:
                    # For CC picks, estimate from other CSP picks
                    csp_sample = csp_picks[0] if csp_picks else None
                    trend_stability = csp_sample.get('trend_stability', 0.5) if csp_sample else 0.5

                trend = sample_pick.get('trend', 'neutral')

                trend_stats['symbols_with_data'] += 1
                trend_stats['avg_trend_strength'] += trend_strength
                trend_stats['avg_trend_stability'] += trend_stability

                if trend == 'uptrend':
                    trend_stats['uptrends'] += 1
                elif trend == 'downtrend':
                    trend_stats['downtrends'] += 1
                else:
                    trend_stats['neutral'] += 1

            print(f" → {len(cc_picks):2d} CC, {len(csp_picks):2d} CSP ({symbol_time:.1f}s)", end="")

            # Show trend for this symbol
            if cc_picks:
                ts = cc_picks[0].get('trend_strength', 0)
                trend = cc_picks[0].get('trend', 'N/A')
                print(f" | trend: {ts:+.2f} ({trend})")
            elif csp_picks:
                ts = csp_picks[0].get('trend_strength', 0)
                trend = csp_picks[0].get('trend', 'N/A')
                print(f" | trend: {ts:+.2f} ({trend})")
            else:
                print(" | no picks")

        except Exception as e:
            symbol_time = time.time() - symbol_start
            print(f" ✗ ERROR ({symbol_time:.1f}s): {str(e)[:50]}")
            symbol_results[symbol] = {
                'cc_count': 0,
                'csp_count': 0,
                'time': symbol_time,
                'error': str(e)
            }

    total_time = time.time() - start_time

    print("\n   " + "-"*76)
    print(f"   ✓ Screening complete in {total_time:.1f} seconds")
    print(f"   ✓ Total picks generated: {len(all_picks)}")

    # Calculate averages
    if trend_stats['symbols_with_data'] > 0:
        trend_stats['avg_trend_strength'] /= trend_stats['symbols_with_data']
        trend_stats['avg_trend_stability'] /= trend_stats['symbols_with_data']

    # Analyze results
    print("\n3. Screening Statistics:")
    print("   " + "-"*76)

    cc_picks = [p for p in all_picks if p.get('strategy') == 'CC']
    csp_picks = [p for p in all_picks if p.get('strategy') == 'CSP']

    print(f"\n   Picks Generated:")
    print(f"     • Total Picks:       {len(all_picks)}")
    print(f"     • Covered Calls:     {len(cc_picks)}")
    print(f"     • Cash-Secured Puts: {len(csp_picks)}")
    print(f"     • Avg per Symbol:    {len(all_picks) / len(pipeline.symbols):.1f}")

    print(f"\n   Performance:")
    print(f"     • Total Time:        {total_time:.1f}s")
    print(f"     • Avg per Symbol:    {total_time / len(pipeline.symbols):.1f}s")
    print(f"     • API Calls:         ~{len(pipeline.symbols) * 3 + len(all_picks) * 2} (estimated)")

    print(f"\n   Trend Analysis:")
    print(f"     • Symbols Analyzed:  {trend_stats['symbols_with_data']}/{len(pipeline.symbols)}")
    print(f"     • Uptrends:          {trend_stats['uptrends']} ({trend_stats['uptrends']/max(1,trend_stats['symbols_with_data'])*100:.0f}%)")
    print(f"     • Downtrends:        {trend_stats['downtrends']} ({trend_stats['downtrends']/max(1,trend_stats['symbols_with_data'])*100:.0f}%)")
    print(f"     • Neutral:           {trend_stats['neutral']} ({trend_stats['neutral']/max(1,trend_stats['symbols_with_data'])*100:.0f}%)")
    print(f"     • Avg Strength:      {trend_stats['avg_trend_strength']:+.2f}")
    print(f"     • Avg Stability:     {trend_stats['avg_trend_stability']:.2f}")

    # Verify trend integration
    print("\n4. Trend Integration Verification:")
    print("   " + "-"*76)

    trend_fields = {
        'trend_strength': 0,
        'trend_stability': 0,
        'trend': 0,
        'in_uptrend': 0,
        'below_200sma': 0
    }

    for pick in all_picks:
        if 'trend_strength' in pick:
            trend_fields['trend_strength'] += 1
        if 'trend_stability' in pick:
            trend_fields['trend_stability'] += 1
        if 'trend' in pick:
            trend_fields['trend'] += 1
        if 'in_uptrend' in pick:
            trend_fields['in_uptrend'] += 1
        if 'below_200sma' in pick:
            trend_fields['below_200sma'] += 1

    total = len(all_picks)
    print(f"\n   Field Coverage:")
    print(f"     • trend_strength:    {trend_fields['trend_strength']}/{total} ({trend_fields['trend_strength']/max(1,total)*100:.0f}%)")
    print(f"     • trend_stability:   {trend_fields['trend_stability']}/{total} ({trend_fields['trend_stability']/max(1,total)*100:.0f}%)")
    print(f"     • trend:             {trend_fields['trend']}/{total} ({trend_fields['trend']/max(1,total)*100:.0f}%)")
    print(f"     • in_uptrend:        {trend_fields['in_uptrend']}/{total} ({trend_fields['in_uptrend']/max(1,total)*100:.0f}%)")
    print(f"     • below_200sma:      {trend_fields['below_200sma']}/{total} ({trend_fields['below_200sma']/max(1,total)*100:.0f}%)")

    # Top picks
    print("\n5. Top 10 Picks (All Strategies):")
    print("   " + "-"*76)

    top_picks = sorted(all_picks, key=lambda x: x.get('score', 0), reverse=True)[:10]

    print("\n   Rank  Symbol  Strategy  Strike    Score   ROI     Trend      Greeks")
    print("   " + "-"*76)

    for i, pick in enumerate(top_picks, 1):
        symbol = pick['symbol']
        strategy = pick.get('strategy', 'N/A')
        strike = pick.get('strike', 0)
        score = pick.get('score', 0)
        roi = pick.get('roi_30d', 0)

        if strategy == 'CC':
            trend_val = pick.get('trend_strength', 0)
            trend_desc = f"{trend_val:+.2f}"
        else:
            trend_val = pick.get('trend_stability', 0)
            trend_desc = f"{trend_val:.2f}"

        delta = pick.get('delta', 0)
        theta = pick.get('theta', 0)

        print(f"   {i:2d}.   {symbol:6s}  {strategy:3s}      ${strike:5.0f}  {score:.4f}  {roi:5.2%}  {trend_desc:6s}  Δ{delta:+.2f} Θ{theta:.3f}")

    # Score distribution
    print("\n6. Score Distribution:")
    print("   " + "-"*76)

    if all_picks:
        scores = [p.get('score', 0) for p in all_picks]
        print(f"\n     • Minimum:  {min(scores):.4f}")
        print(f"     • Maximum:  {max(scores):.4f}")
        print(f"     • Average:  {sum(scores)/len(scores):.4f}")
        print(f"     • Median:   {sorted(scores)[len(scores)//2]:.4f}")

        # Score ranges
        high_scores = len([s for s in scores if s >= 0.7])
        mid_scores = len([s for s in scores if 0.5 <= s < 0.7])
        low_scores = len([s for s in scores if s < 0.5])

        print(f"\n     Score Ranges:")
        print(f"       • High (≥0.70):  {high_scores:3d} picks ({high_scores/len(scores)*100:.0f}%)")
        print(f"       • Mid (0.50-0.70): {mid_scores:3d} picks ({mid_scores/len(scores)*100:.0f}%)")
        print(f"       • Low (<0.50):   {low_scores:3d} picks ({low_scores/len(scores)*100:.0f}%)")

    # Symbol breakdown
    print("\n7. Per-Symbol Breakdown:")
    print("   " + "-"*76)
    print("\n   Symbol    CC   CSP   Total   Time    Status")
    print("   " + "-"*76)

    for symbol in pipeline.symbols:
        result = symbol_results.get(symbol, {})
        cc = result.get('cc_count', 0)
        csp = result.get('csp_count', 0)
        total = cc + csp
        time_val = result.get('time', 0)
        status = "✓" if 'error' not in result else "✗"

        print(f"   {symbol:6s}    {cc:2d}   {csp:2d}    {total:3d}    {time_val:4.1f}s   {status}")

    # Final validation
    print("\n8. Final Validation:")
    print("   " + "-"*76)

    checks = {
        'All symbols screened': len(symbol_results) == len(pipeline.symbols),
        'Picks generated': len(all_picks) > 0,
        'Sufficient picks': len(all_picks) >= 30,
        'Scores valid': all(0 <= p.get('score', 0) <= 1 for p in all_picks),
        'Greeks present': all(p.get('delta') is not None for p in all_picks),
        'Trend analysis active': trend_fields['trend_strength'] > 0,
        'Trend coverage >90%': trend_fields['trend'] / max(1, total) > 0.9,
        'Performance <60s': total_time < 60,
        'No critical errors': all('error' not in r for r in symbol_results.values())
    }

    print()
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"   {status} {check}")

    all_passed = all(checks.values())

    print("\n" + "="*80)
    if all_passed:
        print("✓ FULL PRODUCTION TEST PASSED")
        print(f"  {len(all_picks)} picks generated from {len(pipeline.symbols)} symbols in {total_time:.1f}s")
    else:
        print("⚠ FULL PRODUCTION TEST COMPLETED WITH WARNINGS")
        failed = [k for k, v in checks.items() if not v]
        print(f"  Failed checks: {', '.join(failed)}")
    print("="*80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = test_full_production_screening()
    sys.exit(0 if success else 1)
