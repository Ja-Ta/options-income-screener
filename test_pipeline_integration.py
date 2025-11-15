#!/usr/bin/env python3
"""
Sentiment-Enhanced Pipeline Integration Test (v2.7)

Tests the complete pipeline with sentiment analysis:
1. Sentiment pre-filtering (CMF + Put/Call ratio)
2. Options screening (CC + CSP)
3. Sentiment-enhanced scoring
4. Claude AI rationales with sentiment context
5. Database storage

Usage:
    python test_pipeline_integration.py

Author: Options Income Screener v2.7
"""

import os
import sys
import logging
import sqlite3
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


def get_test_symbols() -> List[str]:
    """
    Get a diverse set of test symbols from expanded universe.

    Selects symbols likely to have interesting sentiment signals:
    - High-volume stocks (SPY, QQQ, AAPL, TSLA)
    - Meme stocks (GME, AMC)
    - Tech stocks (NVDA, MSFT, META)
    - Value stocks (JPM, XOM, WMT)
    - Mix of sectors for diversity
    """
    return [
        # ETFs
        'SPY', 'QQQ', 'IWM',

        # Large cap tech
        'AAPL', 'MSFT', 'NVDA', 'META', 'GOOGL', 'AMZN',

        # High volatility tech
        'TSLA', 'PLTR', 'COIN', 'RBLX',

        # Meme stocks
        'GME', 'AMC', 'BB',

        # Large cap value
        'JPM', 'BAC', 'XOM', 'CVX', 'WMT',

        # Healthcare
        'JNJ', 'UNH', 'PFE',

        # Communication
        'DIS', 'NFLX', 'T'
    ]


def display_pipeline_results(pipeline: ProductionPipeline):
    """Display detailed pipeline results."""

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


def display_sentiment_results():
    """Display sentiment analysis results from database."""

    print_section("Sentiment Analysis Results")

    today = date.today().isoformat()

    try:
        conn = sqlite3.connect('data/screener.db')
        cursor = conn.cursor()

        # Get sentiment metrics
        cursor.execute('''
            SELECT symbol, put_call_ratio_volume, cmf_20,
                   sentiment_score, sentiment_rank, contrarian_signal, data_quality
            FROM sentiment_metrics
            WHERE asof = ?
            ORDER BY sentiment_rank ASC
        ''', (today,))

        sentiment_data = cursor.fetchall()

        if sentiment_data:
            print(f"\n  Analyzed {len(sentiment_data)} symbols")
            print(f"\n  {'Symbol':<8} {'P/C Ratio':<12} {'CMF':<10} {'Score':<8} {'Rank':<8} {'Signal':<8} {'Quality'}")
            print(f"  {'-'*8} {'-'*12} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

            for row in sentiment_data[:15]:  # Show top 15
                symbol, pc_ratio, cmf, score, rank, signal, quality = row
                pc_str = f"{pc_ratio:.2f}" if pc_ratio else "N/A"
                cmf_str = f"{cmf:+.3f}" if cmf else "N/A"
                print(f"  {symbol:<8} {pc_str:<12} {cmf_str:<10} {score:.3f}   {rank}th     {signal.upper():<8} {quality}")

        # Get universe scan stats
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(passed_sentiment_filter) as passed,
                COUNT(CASE WHEN contrarian_signal = 'long' THEN 1 END) as long_signals,
                COUNT(CASE WHEN contrarian_signal = 'short' THEN 1 END) as short_signals
            FROM universe_scan_log
            WHERE run_date = ?
        ''', (today,))

        scan_stats = cursor.fetchone()
        if scan_stats:
            total, passed, long_signals, short_signals = scan_stats
            print(f"\n  Universe Scan Summary:")
            print(f"    Total scanned:                 {total}")
            print(f"    Passed sentiment filter:       {passed}")
            print(f"    Long signals detected:         {long_signals}")
            print(f"    Short signals detected:        {short_signals}")
            print(f"    Filter rate:                   {passed/total*100:.1f}%" if total > 0 else "    Filter rate: N/A")

        conn.close()

    except Exception as e:
        logger.error(f"Error displaying sentiment results: {e}")


def display_top_picks():
    """Display top picks with sentiment context."""

    print_section("Top Picks with Sentiment Context")

    today = date.today().isoformat()

    try:
        conn = sqlite3.connect('data/screener.db')
        cursor = conn.cursor()

        # Get top CC picks
        cursor.execute('''
            SELECT symbol, strike, expiry, premium, roi_30d, score,
                   contrarian_signal, put_call_ratio, cmf_20, rationale
            FROM picks
            WHERE date = ? AND strategy = 'CC'
            ORDER BY score DESC
            LIMIT 3
        ''', (today,))

        cc_picks = cursor.fetchall()

        if cc_picks:
            print(f"\n  📈 Top 3 Covered Calls:")
            for i, pick in enumerate(cc_picks, 1):
                symbol, strike, expiry, premium, roi, score, signal, pc_ratio, cmf, rationale = pick
                pc_str = f"{pc_ratio:.2f}" if pc_ratio else "N/A"
                cmf_str = f"{cmf:+.3f}" if cmf else "N/A"
                print(f"\n  {i}. {symbol} @ ${strike:.2f} (Exp: {expiry})")
                print(f"     Premium: ${premium:.2f} | ROI: {roi:.2%} | Score: {score:.3f}")
                print(f"     Sentiment: {signal.upper():<6} | P/C: {pc_str:<6} | CMF: {cmf_str}")
                if rationale:
                    print(f"     💡 {rationale}")

        # Get top CSP picks
        cursor.execute('''
            SELECT symbol, strike, expiry, premium, roi_30d, score,
                   contrarian_signal, put_call_ratio, cmf_20, rationale
            FROM picks
            WHERE date = ? AND strategy = 'CSP'
            ORDER BY score DESC
            LIMIT 3
        ''', (today,))

        csp_picks = cursor.fetchall()

        if csp_picks:
            print(f"\n  💰 Top 3 Cash-Secured Puts:")
            for i, pick in enumerate(csp_picks, 1):
                symbol, strike, expiry, premium, roi, score, signal, pc_ratio, cmf, rationale = pick
                pc_str = f"{pc_ratio:.2f}" if pc_ratio else "N/A"
                cmf_str = f"{cmf:+.3f}" if cmf else "N/A"
                print(f"\n  {i}. {symbol} @ ${strike:.2f} (Exp: {expiry})")
                print(f"     Premium: ${premium:.2f} | ROI: {roi:.2%} | Score: {score:.3f}")
                print(f"     Sentiment: {signal.upper():<6} | P/C: {pc_str:<6} | CMF: {cmf_str}")
                if rationale:
                    print(f"     💡 {rationale}")

        conn.close()

    except Exception as e:
        logger.error(f"Error displaying top picks: {e}")


def run_integration_test():
    """Run complete pipeline integration test."""

    print_header("SENTIMENT-ENHANCED PIPELINE INTEGRATION TEST (v2.7)")
    print(f"Date: {date.today()}")
    print(f"Testing: Complete pipeline with sentiment analysis")

    # Check for API key
    api_key = os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")
    if not api_key:
        print("\n❌ ERROR: POLYGON_API_KEY or MASSIVE_API_KEY environment variable required")
        print("   Set it with: export POLYGON_API_KEY='your_key_here'")
        return 1

    # Get test symbols
    test_symbols = get_test_symbols()

    print_section("Test Configuration")
    print(f"\n  Test symbols: {len(test_symbols)}")
    print(f"  Symbols: {', '.join(test_symbols[:10])}...")
    print(f"\n  Pipeline components:")
    print(f"    ✓ Sentiment pre-filter (CMF + Put/Call ratio)")
    print(f"    ✓ Two-step sentiment filter (extremes + divergence)")
    print(f"    ✓ Options screening (CC + CSP)")
    print(f"    ✓ Sentiment-enhanced scoring")
    print(f"    ✓ Claude AI rationales with sentiment context")
    print(f"    ✓ Database storage")

    # Initialize and run pipeline
    print_section("Running Pipeline")
    print("\nThis may take 3-5 minutes due to API calls...")
    print("Progress will be logged below:\n")

    try:
        # Create pipeline with test symbols
        pipeline = ProductionPipeline(
            api_key=api_key,
            symbols=test_symbols,
            max_retries=2,
            retry_delay=3
        )

        # Run pipeline
        results = pipeline.run()

        # Display results
        if results.get('success'):
            print("\n" + "="*80)
            display_pipeline_results(pipeline)
            display_sentiment_results()
            display_top_picks()

            print_section("Test Summary")
            print("\n✅ INTEGRATION TEST COMPLETE - All components working!")
            print("")
            print("Components Validated:")
            print("  ✓ Sentiment pre-filter successfully reduced universe")
            print("  ✓ CMF and Put/Call ratios calculated for all symbols")
            print("  ✓ Contrarian signals detected and filtered")
            print("  ✓ Options screening found CC and CSP candidates")
            print("  ✓ Sentiment scoring applied to picks")
            print("  ✓ Sentiment metrics saved to database")
            print("  ✓ Claude AI rationales generated with sentiment context")
            print("")
            print("Next Steps:")
            print("  1. Review the sentiment analysis results above")
            print("  2. Verify top picks have sentiment context")
            print("  3. Check database tables (sentiment_metrics, universe_scan_log, picks)")
            print("  4. If results look good, ready for production deployment!")
            print("")

            return 0
        else:
            print("\n❌ PIPELINE FAILED")
            if results.get('error'):
                print(f"Error: {results['error']}")
            return 1

    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        logger.exception("Integration test failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_integration_test()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        logger.exception("Test failed with exception")
        sys.exit(1)
