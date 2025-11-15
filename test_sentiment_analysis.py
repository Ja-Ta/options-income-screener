#!/usr/bin/env python3
"""
Sentiment Analysis Test Script

Tests the complete sentiment analysis workflow:
1. Load expanded universe
2. Fetch sentiment metrics (CMF + Put/Call ratio)
3. Run sentiment aggregator
4. Apply two-step filter
5. Display results

Usage:
    python test_sentiment_analysis.py

Author: Options Income Screener v2.7
"""

import os
import sys
import logging
from datetime import date
from typing import List

# Add python_app/src to path for absolute imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'python_app'))

# Now import using package structure
from src.data.real_options_fetcher import RealOptionsFetcher
from src.data.sentiment_aggregator import SentimentAggregator, SentimentMetrics
from src.screeners.sentiment_filter import SentimentFilter, FilterConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_expanded_universe(csv_path: str) -> List[str]:
    """Load symbol list from expanded universe CSV."""
    symbols = []

    try:
        with open(csv_path, 'r') as f:
            # Skip header
            next(f)

            for line in f:
                parts = line.strip().split(',')
                if parts and parts[0]:
                    symbols.append(parts[0])

        logger.info(f"Loaded {len(symbols)} symbols from {csv_path}")
        return symbols

    except Exception as e:
        logger.error(f"Error loading universe: {e}")
        return []


def select_test_symbols(all_symbols: List[str], count: int = 10) -> List[str]:
    """
    Select diverse test symbols from universe.

    Picks a mix of:
    - High-volume options stocks (GME, AMC, TSLA)
    - Large cap tech (AAPL, MSFT)
    - Large cap value (JPM, XOM)
    - ETFs (SPY, QQQ)
    - Small cap biotech (for diversity)
    """
    # Prioritize these symbols if available
    priority_symbols = [
        'SPY',    # ETF baseline
        'QQQ',    # Tech ETF
        'AAPL',   # Large cap tech
        'TSLA',   # High vol tech
        'GME',    # Meme stock (high sentiment extremes)
        'AMC',    # Meme stock
        'JPM',    # Large cap finance
        'NVDA',   # High vol tech
        'PLTR',   # High vol tech
        'COIN'    # High vol crypto-related
    ]

    # Take available priority symbols
    test_symbols = [s for s in priority_symbols if s in all_symbols]

    # Fill remaining with other symbols if needed
    if len(test_symbols) < count:
        other_symbols = [s for s in all_symbols if s not in test_symbols]
        test_symbols.extend(other_symbols[:count - len(test_symbols)])

    return test_symbols[:count]


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


def display_sentiment_metrics(symbol: str, metrics: SentimentMetrics):
    """Display sentiment metrics for a symbol in formatted table."""
    print(f"\n{symbol}:")
    print(f"  Put/Call Ratio:      {metrics.put_call_ratio_volume:.2f}" if metrics.put_call_ratio_volume else "  Put/Call Ratio:      N/A")
    print(f"  Put Volume:          {metrics.total_put_volume:,}" if hasattr(metrics, 'total_put_volume') and metrics.total_put_volume else "")
    print(f"  Call Volume:         {metrics.total_call_volume:,}" if hasattr(metrics, 'total_call_volume') and metrics.total_call_volume else "")
    print(f"  CMF (20-day):        {metrics.cmf_20:+.3f}" if metrics.cmf_20 else "  CMF (20-day):        N/A")
    print(f"  Sentiment Score:     {metrics.sentiment_score:.3f} (0=bearish, 1=bullish)")
    print(f"  Sentiment Rank:      {metrics.sentiment_rank}th percentile")
    print(f"  Sentiment Extreme:   {metrics.sentiment_extreme.upper()}")
    print(f"  Contrarian Signal:   {metrics.contrarian_signal.upper()}")
    print(f"  Data Quality:        {metrics.data_quality}")


def run_test():
    """Run complete sentiment analysis test."""

    print_header("SENTIMENT ANALYSIS TEST - v2.7")
    print(f"Date: {date.today()}")
    print(f"Testing: CMF + Put/Call Ratio + Two-Step Filter")

    # Check for API key
    api_key = os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")
    if not api_key:
        print("\n❌ ERROR: POLYGON_API_KEY or MASSIVE_API_KEY environment variable required")
        print("   Set it with: export POLYGON_API_KEY='your_key_here'")
        return 1

    # Initialize components
    print_section("Step 1: Initialize Components")

    fetcher = RealOptionsFetcher(api_key)
    aggregator = SentimentAggregator(fetcher)
    filter_obj = SentimentFilter(FilterConfig(
        sentiment_percentile_cutoff=85,
        max_symbols_to_screen=5,  # Limit for testing
        enabled=True
    ))

    print("✓ RealOptionsFetcher initialized")
    print("✓ SentimentAggregator initialized")
    print("✓ SentimentFilter initialized (cutoff=85th percentile, max=5 symbols)")

    # Load universe
    print_section("Step 2: Load Expanded Universe")

    universe_path = os.path.join(
        os.path.dirname(__file__),
        'python_app', 'src', 'data', 'expanded_universe.csv'
    )

    all_symbols = load_expanded_universe(universe_path)
    if not all_symbols:
        print("❌ ERROR: Could not load expanded universe")
        return 1

    print(f"✓ Loaded {len(all_symbols)} symbols from expanded_universe.csv")

    # Select test symbols
    test_symbols = select_test_symbols(all_symbols, count=10)
    print(f"✓ Selected {len(test_symbols)} test symbols: {', '.join(test_symbols)}")

    # Fetch sentiment metrics
    print_section("Step 3: Fetch Sentiment Metrics (CMF + Put/Call Ratio)")
    print("This will take ~1-2 minutes due to API calls...")
    print("")

    try:
        sentiment_metrics = aggregator.fetch_sentiment_metrics_batch(test_symbols)
        print(f"\n✓ Fetched sentiment data for {len(sentiment_metrics)} symbols")
    except Exception as e:
        print(f"\n❌ ERROR fetching sentiment metrics: {e}")
        logger.exception("Sentiment fetch failed")
        return 1

    # Display individual results
    print_section("Step 4: Sentiment Analysis Results")

    for symbol in test_symbols:
        if symbol in sentiment_metrics:
            display_sentiment_metrics(symbol, sentiment_metrics[symbol])

    # Apply two-step filter
    print_section("Step 5: Apply Two-Step Sentiment Filter")

    try:
        filtered_symbols, reasons = filter_obj.apply_two_step_filter(sentiment_metrics)

        print(f"\nFilter Results:")
        print(f"  Input symbols:       {len(sentiment_metrics)}")
        print(f"  Passed filter:       {len(filtered_symbols)}")
        print(f"  Filter rate:         {len(filtered_symbols)/len(sentiment_metrics)*100:.1f}%")

        if filtered_symbols:
            print(f"\n✓ Filtered Symbols (Top Contrarian Opportunities):")
            print("")
            print(f"  {'Symbol':<8} {'Signal':<10} {'P/C Ratio':<12} {'CMF':<10} {'Rank':<8} {'Reason'}")
            print(f"  {'-'*8} {'-'*10} {'-'*12} {'-'*10} {'-'*8} {'-'*50}")

            for symbol in filtered_symbols:
                m = sentiment_metrics[symbol]
                pc_str = f"{m.put_call_ratio_volume:.2f}" if m.put_call_ratio_volume else "N/A"
                cmf_str = f"{m.cmf_20:+.3f}" if m.cmf_20 else "N/A"
                rank_str = f"{m.sentiment_rank}th"
                reason = reasons.get(symbol, "N/A")

                print(f"  {symbol:<8} {m.contrarian_signal.upper():<10} {pc_str:<12} {cmf_str:<10} {rank_str:<8} {reason}")
        else:
            print("\n⚠️  No symbols passed the two-step filter")
            print("   This is normal if test symbols don't have extreme sentiment")
            print("   Try with more symbols or adjust filter thresholds")

        # Get filter statistics
        stats = filter_obj.get_filter_statistics(sentiment_metrics, filtered_symbols)

        print(f"\n📊 Filter Statistics:")
        print(f"  Long signals:        {stats['long_signals']}")
        print(f"  Short signals:       {stats['short_signals']}")
        print(f"  Negative sentiment:  {stats['negative_sentiment_count']}")
        print(f"  Positive sentiment:  {stats['positive_sentiment_count']}")

    except Exception as e:
        print(f"\n❌ ERROR in filter step: {e}")
        logger.exception("Filter failed")
        return 1

    # Summary
    print_section("Step 6: Test Summary")

    print("\n✅ TEST COMPLETE - All components working!")
    print("")
    print("Components Validated:")
    print("  ✓ Chaikin Money Flow (CMF) calculation")
    print("  ✓ Put/Call Ratio aggregation from options data")
    print("  ✓ Sentiment score calculation and ranking")
    print("  ✓ Contrarian signal detection")
    print("  ✓ Two-step sentiment filter")
    print("")
    print("Next Steps:")
    print("  1. Review the sentiment metrics above")
    print("  2. Verify contrarian signals make sense")
    print("  3. If results look good, proceed to Phase 3 (pipeline integration)")
    print("  4. If adjustments needed, modify thresholds in FilterConfig")
    print("")

    return 0


if __name__ == "__main__":
    try:
        exit_code = run_test()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        logger.exception("Test failed with exception")
        sys.exit(1)
