"""
Sentiment Aggregator Module

Combines multiple sentiment metrics (CMF, Put/Call ratio, short interest) to identify
contrarian trading opportunities. Implements the two-step screening methodology from
"Generate Thousands in Cash on Your Stocks Before Buying or Selling Them".

Author: Options Income Screener v2.7
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import date
from dataclasses import dataclass
import statistics

from .real_options_fetcher import RealOptionsFetcher
from ..features.technicals import calculate_chaikin_money_flow

logger = logging.getLogger(__name__)


@dataclass
class SentimentMetrics:
    """Container for all sentiment metrics for a symbol."""
    symbol: str

    # Put/Call ratio metrics
    put_call_ratio_volume: Optional[float] = None
    put_call_ratio_oi: Optional[float] = None

    # Chaikin Money Flow
    cmf_20: Optional[float] = None

    # Short interest (placeholder for future implementation)
    days_to_cover: Optional[float] = None
    short_pct_float: Optional[float] = None

    # Derived sentiment indicators
    sentiment_extreme: str = 'neutral'  # 'negative', 'positive', 'neutral'
    contrarian_signal: str = 'none'     # 'long', 'short', 'none'
    sentiment_score: float = 0.5         # 0 = extremely negative, 1 = extremely positive
    sentiment_rank: int = 50             # Percentile rank (0-100)

    # Metadata
    as_of_date: Optional[date] = None
    data_quality: str = 'complete'       # 'complete', 'partial', 'insufficient'


class SentimentAggregator:
    """
    Aggregates sentiment data from multiple sources and calculates composite scores.

    Implements contrarian methodology:
    - High put/call ratio + accumulation (positive CMF) = Contrarian LONG
    - Low put/call ratio + distribution (negative CMF) = Contrarian SHORT
    """

    def __init__(self, options_fetcher: RealOptionsFetcher):
        """
        Initialize sentiment aggregator.

        Args:
            options_fetcher: RealOptionsFetcher instance for market data
        """
        self.fetcher = options_fetcher
        logger.info("SentimentAggregator initialized")

    def fetch_sentiment_metrics(
        self,
        symbol: str,
        price_data: Optional[Dict] = None
    ) -> SentimentMetrics:
        """
        Fetch all sentiment metrics for a single symbol.

        Args:
            symbol: Stock ticker symbol
            price_data: Optional dict with historical price data
                       {prices, highs, lows, volumes} - if not provided, will fetch

        Returns:
            SentimentMetrics object with all available data
        """
        logger.info(f"Fetching sentiment metrics for {symbol}")

        metrics = SentimentMetrics(
            symbol=symbol,
            as_of_date=date.today()
        )

        # Fetch price data if not provided
        if not price_data:
            price_data = self.fetcher.get_historical_prices(symbol, days=60)

        # Calculate CMF (Chaikin Money Flow)
        if price_data and all(k in price_data for k in ['highs', 'lows', 'prices', 'volumes']):
            try:
                cmf = calculate_chaikin_money_flow(
                    highs=price_data['highs'],
                    lows=price_data['lows'],
                    closes=price_data['prices'],
                    volumes=price_data['volumes'],
                    period=20
                )
                metrics.cmf_20 = cmf
                logger.info(f"{symbol} CMF(20): {cmf:.3f}" if cmf else f"{symbol} CMF: N/A")
            except Exception as e:
                logger.error(f"Error calculating CMF for {symbol}: {e}")

        # Fetch Put/Call ratio
        try:
            pc_data = self.fetcher.get_putcall_ratio(symbol, expiry_range_days=60)
            if pc_data:
                metrics.put_call_ratio_volume = pc_data.get('put_call_ratio_volume')
                metrics.put_call_ratio_oi = pc_data.get('put_call_ratio_oi')
                logger.info(
                    f"{symbol} P/C Ratio: {metrics.put_call_ratio_volume:.2f} (volume)"
                    if metrics.put_call_ratio_volume else f"{symbol} P/C Ratio: N/A"
                )
        except Exception as e:
            logger.error(f"Error fetching P/C ratio for {symbol}: {e}")

        # Short interest - placeholder (not implemented yet)
        # TODO: Integrate when short interest API selected
        metrics.days_to_cover = None
        metrics.short_pct_float = None

        # Assess data quality
        metrics.data_quality = self._assess_data_quality(metrics)

        # Calculate composite sentiment score and signals
        self._calculate_sentiment_score(metrics)

        return metrics

    def fetch_sentiment_metrics_batch(
        self,
        symbols: List[str],
        use_cache: bool = True
    ) -> Dict[str, SentimentMetrics]:
        """
        Fetch sentiment metrics for multiple symbols in batch.

        Args:
            symbols: List of stock ticker symbols
            use_cache: Whether to use cached price data (future enhancement)

        Returns:
            Dictionary mapping symbol to SentimentMetrics
        """
        logger.info(f"Fetching sentiment metrics for {len(symbols)} symbols")

        results = {}

        for i, symbol in enumerate(symbols, 1):
            logger.info(f"Processing {symbol} ({i}/{len(symbols)})")

            try:
                metrics = self.fetch_sentiment_metrics(symbol)
                results[symbol] = metrics
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                # Create empty metrics for failed symbols
                results[symbol] = SentimentMetrics(
                    symbol=symbol,
                    as_of_date=date.today(),
                    data_quality='insufficient'
                )

        # Calculate sentiment ranks across universe
        self._calculate_sentiment_ranks(results)

        logger.info(
            f"Batch sentiment fetch complete: {len(results)}/{len(symbols)} processed"
        )

        return results

    def _assess_data_quality(self, metrics: SentimentMetrics) -> str:
        """
        Assess quality of sentiment data.

        Args:
            metrics: SentimentMetrics object

        Returns:
            'complete', 'partial', or 'insufficient'
        """
        available_metrics = 0
        total_metrics = 2  # CMF and P/C ratio (excluding short interest for now)

        if metrics.cmf_20 is not None:
            available_metrics += 1

        if metrics.put_call_ratio_volume is not None:
            available_metrics += 1

        if available_metrics == total_metrics:
            return 'complete'
        elif available_metrics > 0:
            return 'partial'
        else:
            return 'insufficient'

    def _calculate_sentiment_score(self, metrics: SentimentMetrics) -> None:
        """
        Calculate composite sentiment score and determine signals.

        Updates metrics object in-place with:
        - sentiment_score: 0 (extremely negative) to 1 (extremely positive)
        - sentiment_extreme: 'negative', 'positive', or 'neutral'
        - contrarian_signal: 'long', 'short', or 'none'

        Methodology:
        - High P/C ratio (>1.5) = negative sentiment (crowd pessimistic)
        - Low P/C ratio (<0.7) = positive sentiment (crowd optimistic)
        - Positive CMF (>0.1) = accumulation (smart money buying)
        - Negative CMF (<-0.1) = distribution (smart money selling)
        - Contrarian opportunity = crowd wrong + smart money divergent
        """
        # Start with neutral
        sentiment_components = []

        # Component 1: Put/Call Ratio (50% weight when available)
        if metrics.put_call_ratio_volume is not None:
            pc_ratio = metrics.put_call_ratio_volume

            # Convert P/C ratio to 0-1 scale
            # >1.5 = 0 (extremely negative), <0.7 = 1 (extremely positive)
            if pc_ratio >= 1.5:
                pc_score = max(0, 1 - (pc_ratio - 1.5) / 1.0)  # Scale down from 1.5
            elif pc_ratio <= 0.7:
                pc_score = min(1, 0.7 / pc_ratio)  # Scale up from 0.7
            else:
                # Between 0.7 and 1.5 = neutral range
                pc_score = 0.5 + (1.0 - pc_ratio) / 1.6

            sentiment_components.append(('pc_ratio', pc_score, 0.5))

        # Component 2: Chaikin Money Flow (50% weight when available)
        if metrics.cmf_20 is not None:
            cmf = metrics.cmf_20

            # Convert CMF (-1 to +1) to 0-1 scale
            # Positive CMF = accumulation = score closer to 0 (negative sentiment + buying = contrarian)
            # Negative CMF = distribution = score closer to 1 (positive sentiment + selling = contrarian)
            # We INVERT this because we want to identify where smart money disagrees with crowd
            cmf_score = 0.5 - (cmf * 0.5)  # Invert: +1 CMF → 0, -1 CMF → 1

            sentiment_components.append(('cmf', cmf_score, 0.5))

        # Calculate weighted sentiment score
        if sentiment_components:
            total_weight = sum(weight for _, _, weight in sentiment_components)
            weighted_sum = sum(score * weight for _, score, weight in sentiment_components)
            metrics.sentiment_score = weighted_sum / total_weight
        else:
            metrics.sentiment_score = 0.5  # Neutral if no data

        # Determine sentiment extreme
        if metrics.sentiment_score <= 0.3:
            metrics.sentiment_extreme = 'negative'  # Crowd is pessimistic
        elif metrics.sentiment_score >= 0.7:
            metrics.sentiment_extreme = 'positive'  # Crowd is optimistic
        else:
            metrics.sentiment_extreme = 'neutral'

        # Determine contrarian signal (requires BOTH sentiment extreme AND divergent price action)
        metrics.contrarian_signal = self._determine_contrarian_signal(metrics)

    def _determine_contrarian_signal(self, metrics: SentimentMetrics) -> str:
        """
        Determine contrarian trading signal based on sentiment + price divergence.

        Book's Two-Step Process:
        Step 1: Identify extreme sentiment
        Step 2: Find divergent price action (CMF opposite to sentiment)

        Returns:
            'long', 'short', or 'none'
        """
        # Need both P/C ratio and CMF for contrarian signals
        if metrics.put_call_ratio_volume is None or metrics.cmf_20 is None:
            return 'none'

        pc_ratio = metrics.put_call_ratio_volume
        cmf = metrics.cmf_20

        # LONG Signal: Excessive pessimism (high P/C) + Accumulation (positive CMF)
        # Interpretation: Crowd is bearish but smart money is buying = contrarian buy
        if pc_ratio > 1.5 and cmf > 0.1:
            logger.info(
                f"{metrics.symbol}: LONG signal - "
                f"P/C ratio {pc_ratio:.2f} (pessimistic) + CMF {cmf:.3f} (accumulation)"
            )
            return 'long'

        # SHORT Signal: Excessive optimism (low P/C) + Distribution (negative CMF)
        # Interpretation: Crowd is bullish but smart money is selling = contrarian sell
        if pc_ratio < 0.7 and cmf < -0.1:
            logger.info(
                f"{metrics.symbol}: SHORT signal - "
                f"P/C ratio {pc_ratio:.2f} (optimistic) + CMF {cmf:.3f} (distribution)"
            )
            return 'short'

        return 'none'

    def _calculate_sentiment_ranks(
        self,
        metrics_dict: Dict[str, SentimentMetrics]
    ) -> None:
        """
        Calculate percentile ranks for sentiment scores across universe.

        Updates metrics objects in-place with sentiment_rank (0-100 percentile).
        """
        # Extract sentiment scores
        scores = [
            m.sentiment_score for m in metrics_dict.values()
            if m.data_quality != 'insufficient'
        ]

        if not scores:
            logger.warning("No valid sentiment scores to rank")
            return

        # Calculate percentile for each symbol
        for symbol, metrics in metrics_dict.items():
            if metrics.data_quality == 'insufficient':
                metrics.sentiment_rank = 50  # Default to median
                continue

            # Count how many scores are below this one
            below_count = sum(1 for s in scores if s < metrics.sentiment_score)
            percentile = int((below_count / len(scores)) * 100)

            metrics.sentiment_rank = percentile

            logger.debug(
                f"{symbol} sentiment rank: {percentile}th percentile "
                f"(score: {metrics.sentiment_score:.3f})"
            )


def example_usage():
    """Example usage of SentimentAggregator."""
    import os
    from .real_options_fetcher import RealOptionsFetcher

    # Initialize
    api_key = os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")
    if not api_key:
        print("Error: POLYGON_API_KEY or MASSIVE_API_KEY required")
        return

    fetcher = RealOptionsFetcher(api_key)
    aggregator = SentimentAggregator(fetcher)

    # Example 1: Single symbol
    print("\n" + "="*60)
    print("Example 1: Fetch sentiment for single symbol")
    print("="*60)

    symbol = "GME"
    metrics = aggregator.fetch_sentiment_metrics(symbol)

    print(f"\n{symbol} Sentiment Analysis:")
    print(f"  Put/Call Ratio: {metrics.put_call_ratio_volume:.2f}" if metrics.put_call_ratio_volume else "  Put/Call Ratio: N/A")
    print(f"  CMF (20-day): {metrics.cmf_20:.3f}" if metrics.cmf_20 else "  CMF: N/A")
    print(f"  Sentiment Score: {metrics.sentiment_score:.3f} (0=bearish, 1=bullish)")
    print(f"  Sentiment Extreme: {metrics.sentiment_extreme}")
    print(f"  Contrarian Signal: {metrics.contrarian_signal.upper()}")
    print(f"  Data Quality: {metrics.data_quality}")

    # Example 2: Batch symbols
    print("\n" + "="*60)
    print("Example 2: Batch sentiment analysis")
    print("="*60)

    symbols = ["AAPL", "TSLA", "GME", "AMC", "SPY"]
    results = aggregator.fetch_sentiment_metrics_batch(symbols)

    print(f"\nTop Contrarian Opportunities:")
    print(f"{'Symbol':<8} {'P/C Ratio':<12} {'CMF':<10} {'Signal':<10} {'Rank':<8}")
    print("-" * 60)

    for symbol in symbols:
        m = results[symbol]
        pc_str = f"{m.put_call_ratio_volume:.2f}" if m.put_call_ratio_volume else "N/A"
        cmf_str = f"{m.cmf_20:+.3f}" if m.cmf_20 else "N/A"

        print(
            f"{symbol:<8} {pc_str:<12} {cmf_str:<10} "
            f"{m.contrarian_signal.upper():<10} {m.sentiment_rank}th"
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    example_usage()
