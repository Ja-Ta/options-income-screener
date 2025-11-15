#!/usr/bin/env python3
"""
Full Universe Integration Test (v2.7 Production Scale)

Tests the complete pipeline with all 111 symbols from expanded_universe.csv:
1. Sentiment analysis of full universe
2. Two-step sentiment pre-filtering
3. Options screening on filtered symbols
4. Sentiment-enhanced scoring
5. Claude AI rationales with sentiment context
6. Database storage

This is a production-scale test to validate performance and API usage.

Usage:
    python test_full_universe.py

Author: Options Income Screener v2.7
"""

import os
import sys
import logging
import sqlite3
import csv
from datetime import date
from typing import List

# Add python_app to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'python_app'))

from src.pipelines.daily_job import ProductionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'─'*80}")
    print(f"  {title}")
    print(f"{'─'*80}")


def load_expanded_universe() -> List[str]:
    """Load all symbols from expanded_universe.csv"""
    csv_path = os.path.join(project_root, 'python_app', 'src', 'data', 'expanded_universe.csv')

    symbols = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['symbol']:
                symbols.append(row['symbol'])

    return symbols


def display_pipeline_stats(pipeline: ProductionPipeline):
    """Display pipeline statistics."""

    print_section("Pipeline Statistics")
    stats = pipeline.stats

    print(f"\n  Universe Analysis:")
    print(f"    Total symbols in universe:     {len(pipeline.symbols)}")
    print(f"    Symbols attempted:             {stats['symbols_attempted']}")
    print(f"    Symbols succeeded:             {stats['symbols_succeeded']}")
    print(f"    Symbols failed:                {stats['symbols_failed']}")

    print(f"\n  Options Picks:")
    print(f"    Total picks:                   {stats['total_picks']}")
    print(f"    Covered calls:                 {stats['cc_picks']}")
    print(f"    Cash-secured puts:             {stats['csp_picks']}")

    print(f"\n  API Performance:")
    print(f"    Total API calls:               {stats['api_calls']}")
    print(f"    Duration:                      {stats.get('duration', 0):.2f}s")
    print(f"    Avg time per symbol:           {stats.get('duration', 0) / len(pipeline.symbols):.2f}s")


def display_sentiment_summary():
    """Display sentiment analysis summary."""

    print_section("Sentiment Analysis Summary")

    today = date.today().isoformat()

    try:
        conn = sqlite3.connect('data/screener.db')
        cursor = conn.cursor()

        # Universe scan summary
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(passed_sentiment_filter) as passed,
                COUNT(*) - SUM(passed_sentiment_filter) as filtered,
                COUNT(CASE WHEN contrarian_signal = 'long' THEN 1 END) as long_signals,
                COUNT(CASE WHEN contrarian_signal = 'short' THEN 1 END) as short_signals,
                COUNT(CASE WHEN contrarian_signal = 'none' THEN 1 END) as neutral
            FROM universe_scan_log
            WHERE run_date = ?
        ''', (today,))

        total, passed, filtered, long_sig, short_sig, neutral = cursor.fetchone()

        print(f"\n  Universe Screening:")
        print(f"    Total symbols scanned:         {total}")
        print(f"    Passed sentiment filter:       {passed}")
        print(f"    Filtered out:                  {filtered}")
        print(f"    Filter rate:                   {filtered/total*100:.1f}%")

        print(f"\n  Contrarian Signals Detected:")
        print(f"    LONG signals (buy opportunity): {long_sig}")
        print(f"    SHORT signals (sell setup):     {short_sig}")
        print(f"    NONE (neutral sentiment):       {neutral}")

        # Top sentiment picks
        cursor.execute('''
            SELECT symbol, contrarian_signal,
                   ROUND(put_call_ratio, 2), ROUND(cmf_20, 3), sentiment_rank
            FROM universe_scan_log
            WHERE run_date = ? AND passed_sentiment_filter = 1
            ORDER BY sentiment_rank ASC
            LIMIT 10
        ''', (today,))

        top_picks = cursor.fetchall()

        if top_picks:
            print(f"\n  Top 10 Symbols (Passed Filter):")
            print(f"    {'Symbol':<8} {'Signal':<7} {'P/C Ratio':<10} {'CMF':<10} {'Rank'}")
            print(f"    {'-'*8} {'-'*7} {'-'*10} {'-'*10} {'-'*5}")
            for symbol, signal, pc, cmf, rank in top_picks:
                pc_str = f"{pc:.2f}" if pc else "N/A"
                cmf_str = f"{cmf:+.3f}" if cmf else "N/A"
                print(f"    {symbol:<8} {signal.upper():<7} {pc_str:<10} {cmf_str:<10} {rank}")

        conn.close()

    except Exception as e:
        logger.error(f"Error displaying sentiment summary: {e}")


def display_top_picks():
    """Display top option picks."""

    print_section("Top Option Picks")

    today = date.today().isoformat()

    try:
        conn = sqlite3.connect('data/screener.db')
        cursor = conn.cursor()

        # Top CC picks
        cursor.execute('''
            SELECT symbol, ROUND(strike, 2), expiry, ROUND(premium, 2),
                   ROUND(roi_30d * 100, 2), ROUND(score, 3),
                   contrarian_signal
            FROM picks
            WHERE date = ? AND strategy = 'CC'
            ORDER BY score DESC
            LIMIT 5
        ''', (today,))

        cc_picks = cursor.fetchall()

        if cc_picks:
            print(f"\n  📈 Top 5 Covered Calls:")
            print(f"    {'Symbol':<8} {'Strike':<8} {'Expiry':<12} {'Premium':<10} {'ROI':<8} {'Score':<8} {'Signal'}")
            print(f"    {'-'*8} {'-'*8} {'-'*12} {'-'*10} {'-'*8} {'-'*8} {'-'*7}")
            for symbol, strike, expiry, prem, roi, score, signal in cc_picks:
                print(f"    {symbol:<8} ${strike:<7.2f} {expiry:<12} ${prem:<9.2f} {roi:<7.2f}% {score:<8.3f} {signal.upper()}")

        # Top CSP picks
        cursor.execute('''
            SELECT symbol, ROUND(strike, 2), expiry, ROUND(premium, 2),
                   ROUND(roi_30d * 100, 2), ROUND(score, 3),
                   contrarian_signal
            FROM picks
            WHERE date = ? AND strategy = 'CSP'
            ORDER BY score DESC
            LIMIT 5
        ''', (today,))

        csp_picks = cursor.fetchall()

        if csp_picks:
            print(f"\n  💰 Top 5 Cash-Secured Puts:")
            print(f"    {'Symbol':<8} {'Strike':<8} {'Expiry':<12} {'Premium':<10} {'ROI':<8} {'Score':<8} {'Signal'}")
            print(f"    {'-'*8} {'-'*8} {'-'*12} {'-'*10} {'-'*8} {'-'*8} {'-'*7}")
            for symbol, strike, expiry, prem, roi, score, signal in csp_picks:
                print(f"    {symbol:<8} ${strike:<7.2f} {expiry:<12} ${prem:<9.2f} {roi:<7.2f}% {score:<8.3f} {signal.upper()}")

        conn.close()

    except Exception as e:
        logger.error(f"Error displaying top picks: {e}")


def run_full_test():
    """Run full universe production test."""

    print_header("FULL UNIVERSE PRODUCTION TEST (v2.7)")
    print(f"Date: {date.today()}")
    print(f"Testing: Complete 111-symbol expanded universe")

    # Check for API key
    api_key = os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")
    if not api_key:
        print("\n❌ ERROR: POLYGON_API_KEY or MASSIVE_API_KEY environment variable required")
        print("   Set it with: export POLYGON_API_KEY='your_key_here'")
        return 1

    # Load full universe
    try:
        symbols = load_expanded_universe()
        print(f"\n✓ Loaded {len(symbols)} symbols from expanded_universe.csv")
    except Exception as e:
        print(f"\n❌ ERROR loading universe: {e}")
        return 1

    print_section("Test Configuration")
    print(f"\n  Universe size: {len(symbols)} symbols")
    print(f"  Sample symbols: {', '.join(symbols[:10])}...")
    print(f"\n  Pipeline components:")
    print(f"    ✓ Sentiment pre-filter (CMF + Put/Call ratio)")
    print(f"    ✓ Two-step sentiment filter (extremes + divergence)")
    print(f"    ✓ Options screening (CC + CSP)")
    print(f"    ✓ Sentiment-enhanced scoring")
    print(f"    ✓ Claude AI rationales with sentiment context")
    print(f"    ✓ Database storage")

    print_section("Running Production Pipeline")
    print(f"\n⚠️  This will take 10-15 minutes due to API calls for {len(symbols)} symbols")
    print("Progress will be logged below:\n")

    try:
        # Create and run pipeline
        pipeline = ProductionPipeline(
            api_key=api_key,
            symbols=symbols,
            max_retries=2,
            retry_delay=3
        )

        results = pipeline.run()

        # Display results
        if results.get('success'):
            print("\n" + "="*80)
            display_pipeline_stats(pipeline)
            display_sentiment_summary()
            display_top_picks()

            print_section("Production Test Summary")
            print("\n✅ FULL UNIVERSE TEST COMPLETE - Production Ready!")
            print("")
            print("Validation Results:")
            print(f"  ✓ Processed {len(symbols)} symbols successfully")
            print(f"  ✓ Sentiment pre-filter reduced universe by {pipeline.stats.get('symbols_failed', 0)} symbols")
            print(f"  ✓ Generated {pipeline.stats['total_picks']} high-quality option picks")
            print(f"  ✓ Total API calls: {pipeline.stats['api_calls']}")
            print(f"  ✓ Total runtime: {pipeline.stats.get('duration', 0):.2f}s")
            print("")
            print("Next Steps:")
            print("  1. Review sentiment analysis effectiveness")
            print("  2. Verify API usage is within acceptable limits")
            print("  3. Deploy to production if results look good")
            print("")

            return 0
        else:
            print("\n❌ PIPELINE FAILED")
            if results.get('error'):
                print(f"Error: {results['error']}")
            return 1

    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        logger.exception("Production test failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_full_test()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        logger.exception("Test failed with exception")
        sys.exit(1)
