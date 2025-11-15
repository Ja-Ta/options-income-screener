"""
Two-Step Sentiment Filter

Implements the contrarian screening methodology from "Generate Thousands in Cash
on Your Stocks Before Buying or Selling Them":

Step 1: Filter for EXTREME sentiment (>90th percentile)
Step 2: Filter for DIVERGENT price action (sentiment vs money flow mismatch)

Result: 10-20 symbols with highest contrarian opportunity potential.

Author: Options Income Screener v2.7
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from ..data.sentiment_aggregator import SentimentMetrics

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Configuration for sentiment filtering."""

    # Step 1: Sentiment extreme thresholds
    sentiment_percentile_cutoff: int = 85  # Consider extremes above/below this percentile

    # Step 2: CMF divergence thresholds
    cmf_divergence_threshold: float = 0.1  # Minimum CMF magnitude for divergence

    # Put/Call ratio extremes (from book)
    putcall_extreme_high: float = 1.5  # High P/C = excessive pessimism
    putcall_extreme_low: float = 0.7   # Low P/C = excessive optimism

    # Output limits
    max_symbols_to_screen: int = 20  # Maximum symbols to return for screening
    min_data_quality: str = 'partial'  # Minimum data quality required

    # Enable/disable filter
    enabled: bool = True


class SentimentFilter:
    """
    Filters symbol universe based on sentiment extremes and price divergence.

    Implements two-step contrarian methodology:
    1. Identify symbols with extreme crowd sentiment
    2. Find those showing opposite smart money behavior
    """

    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Initialize sentiment filter.

        Args:
            config: FilterConfig object (uses defaults if None)
        """
        self.config = config or FilterConfig()
        logger.info(f"SentimentFilter initialized with config: {self.config}")

    def apply_two_step_filter(
        self,
        sentiment_metrics: Dict[str, SentimentMetrics]
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        Apply two-step sentiment filter to symbol universe.

        Args:
            sentiment_metrics: Dictionary mapping symbol to SentimentMetrics

        Returns:
            Tuple of:
            - List of filtered symbols (10-20 top candidates)
            - Dictionary mapping symbol to filter reason (for logging)

        Example:
            >>> filtered_symbols, reasons = filter.apply_two_step_filter(metrics)
            >>> print(f"Filtered to {len(filtered_symbols)} symbols")
            >>> for symbol in filtered_symbols:
            ...     print(f"  {symbol}: {reasons[symbol]}")
        """
        if not self.config.enabled:
            logger.info("Sentiment filter disabled - returning all symbols")
            return list(sentiment_metrics.keys()), {}

        logger.info(f"Applying two-step sentiment filter to {len(sentiment_metrics)} symbols")

        # Filter Step 1: Extreme sentiment
        step1_symbols = self._filter_step1_extreme_sentiment(sentiment_metrics)
        logger.info(f"Step 1 (extreme sentiment): {len(step1_symbols)} symbols pass")

        # Filter Step 2: Divergent price action
        step2_symbols, reasons = self._filter_step2_divergent_action(
            sentiment_metrics,
            step1_symbols
        )
        logger.info(f"Step 2 (divergent action): {len(step2_symbols)} symbols pass")

        # Limit to max symbols
        if len(step2_symbols) > self.config.max_symbols_to_screen:
            logger.info(
                f"Limiting from {len(step2_symbols)} to "
                f"{self.config.max_symbols_to_screen} symbols"
            )
            step2_symbols = self._rank_and_limit(
                sentiment_metrics,
                step2_symbols,
                self.config.max_symbols_to_screen
            )

        logger.info(
            f"Two-step filter complete: {len(step2_symbols)} symbols selected "
            f"for detailed screening"
        )

        return step2_symbols, reasons

    def _filter_step1_extreme_sentiment(
        self,
        sentiment_metrics: Dict[str, SentimentMetrics]
    ) -> List[str]:
        """
        Step 1: Filter for symbols with extreme sentiment.

        Extreme sentiment defined as:
        - Sentiment rank > cutoff percentile (e.g., >85th = extremely positive)
        - Sentiment rank < (100 - cutoff) percentile (e.g., <15th = extremely negative)
        - OR explicit extreme flags from sentiment aggregator

        Args:
            sentiment_metrics: Dictionary of sentiment data

        Returns:
            List of symbols with extreme sentiment
        """
        extreme_symbols = []
        cutoff = self.config.sentiment_percentile_cutoff

        for symbol, metrics in sentiment_metrics.items():
            # Skip insufficient data
            if metrics.data_quality == 'insufficient':
                continue

            # Check 1: Percentile rank extremes
            if metrics.sentiment_rank >= cutoff or metrics.sentiment_rank <= (100 - cutoff):
                extreme_symbols.append(symbol)
                logger.debug(
                    f"{symbol}: Extreme sentiment - {metrics.sentiment_rank}th percentile"
                )
                continue

            # Check 2: Explicit extreme sentiment flag
            if metrics.sentiment_extreme in ['negative', 'positive']:
                extreme_symbols.append(symbol)
                logger.debug(
                    f"{symbol}: Extreme sentiment flag - {metrics.sentiment_extreme}"
                )
                continue

            # Check 3: Put/Call ratio extremes (direct threshold check)
            if metrics.put_call_ratio_volume:
                pc_ratio = metrics.put_call_ratio_volume
                if pc_ratio >= self.config.putcall_extreme_high or \
                   pc_ratio <= self.config.putcall_extreme_low:
                    extreme_symbols.append(symbol)
                    logger.debug(
                        f"{symbol}: Extreme P/C ratio - {pc_ratio:.2f}"
                    )
                    continue

        return extreme_symbols

    def _filter_step2_divergent_action(
        self,
        sentiment_metrics: Dict[str, SentimentMetrics],
        step1_symbols: List[str]
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        Step 2: Filter for divergent price action (sentiment vs money flow).

        Divergence defined as:
        - Negative sentiment (high P/C) + Positive CMF (accumulation) = LONG opportunity
        - Positive sentiment (low P/C) + Negative CMF (distribution) = SHORT opportunity

        This is the KEY to contrarian edge: Crowd is wrong, smart money knows it.

        Args:
            sentiment_metrics: Dictionary of sentiment data
            step1_symbols: Symbols that passed Step 1

        Returns:
            Tuple of:
            - List of symbols with divergent action
            - Dictionary mapping symbol to divergence reason
        """
        divergent_symbols = []
        reasons = {}

        for symbol in step1_symbols:
            metrics = sentiment_metrics[symbol]

            # Need both CMF and P/C ratio for divergence check
            if metrics.cmf_20 is None or metrics.put_call_ratio_volume is None:
                logger.debug(f"{symbol}: Skipping - missing CMF or P/C data")
                continue

            cmf = metrics.cmf_20
            pc_ratio = metrics.put_call_ratio_volume

            # Divergence Type 1: Bearish sentiment + Bullish money flow
            # High P/C (>1.5) + Positive CMF (>0.1) = Crowd fearful, smart money buying
            if pc_ratio >= self.config.putcall_extreme_high and \
               cmf >= self.config.cmf_divergence_threshold:
                divergent_symbols.append(symbol)
                reasons[symbol] = (
                    f"LONG - Excessive pessimism (P/C {pc_ratio:.2f}) "
                    f"+ Accumulation (CMF {cmf:+.3f})"
                )
                logger.info(f"✓ {symbol}: {reasons[symbol]}")
                continue

            # Divergence Type 2: Bullish sentiment + Bearish money flow
            # Low P/C (<0.7) + Negative CMF (<-0.1) = Crowd greedy, smart money selling
            if pc_ratio <= self.config.putcall_extreme_low and \
               cmf <= -self.config.cmf_divergence_threshold:
                divergent_symbols.append(symbol)
                reasons[symbol] = (
                    f"SHORT - Excessive optimism (P/C {pc_ratio:.2f}) "
                    f"+ Distribution (CMF {cmf:+.3f})"
                )
                logger.info(f"✓ {symbol}: {reasons[symbol]}")
                continue

            # Divergence Type 3: Moderate divergence (less extreme but still notable)
            # Relax thresholds slightly for secondary opportunities
            if (pc_ratio >= 1.2 and cmf >= 0.05) or \
               (pc_ratio <= 0.9 and cmf <= -0.05):
                divergent_symbols.append(symbol)
                reasons[symbol] = (
                    f"MODERATE - P/C {pc_ratio:.2f}, CMF {cmf:+.3f}"
                )
                logger.debug(f"✓ {symbol}: {reasons[symbol]}")
                continue

        return divergent_symbols, reasons

    def _rank_and_limit(
        self,
        sentiment_metrics: Dict[str, SentimentMetrics],
        symbols: List[str],
        limit: int
    ) -> List[str]:
        """
        Rank symbols by sentiment strength and limit to top N.

        Ranking criteria (in order):
        1. Contrarian signal strength (long/short signals prioritized)
        2. Sentiment extremeness (distance from neutral)
        3. Data quality (complete > partial)

        Args:
            sentiment_metrics: Dictionary of sentiment data
            symbols: List of symbols to rank
            limit: Maximum number to return

        Returns:
            Top N symbols ranked by opportunity strength
        """
        # Calculate composite ranking score for each symbol
        scored_symbols = []

        for symbol in symbols:
            metrics = sentiment_metrics[symbol]
            score = 0.0

            # Component 1: Contrarian signal (highest weight)
            if metrics.contrarian_signal in ['long', 'short']:
                score += 50.0

            # Component 2: Sentiment extremeness
            # Distance from neutral (0.5)
            extremeness = abs(metrics.sentiment_score - 0.5)
            score += extremeness * 30.0

            # Component 3: P/C ratio divergence magnitude
            if metrics.put_call_ratio_volume:
                pc_ratio = metrics.put_call_ratio_volume
                if pc_ratio >= 1.5:
                    score += (pc_ratio - 1.5) * 10.0
                elif pc_ratio <= 0.7:
                    score += (0.7 - pc_ratio) * 10.0

            # Component 4: CMF magnitude
            if metrics.cmf_20:
                score += abs(metrics.cmf_20) * 10.0

            # Component 5: Data quality bonus
            if metrics.data_quality == 'complete':
                score += 5.0

            scored_symbols.append((symbol, score))

        # Sort by score descending
        scored_symbols.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        top_symbols = [symbol for symbol, score in scored_symbols[:limit]]

        # Log ranking
        logger.info(f"Top {limit} symbols by sentiment opportunity:")
        for i, (symbol, score) in enumerate(scored_symbols[:limit], 1):
            metrics = sentiment_metrics[symbol]
            pc_str = f"{metrics.put_call_ratio_volume:.2f}" if metrics.put_call_ratio_volume else "N/A"
            cmf_str = f"{metrics.cmf_20:+.3f}" if metrics.cmf_20 else "N/A"
            logger.info(
                f"  {i}. {symbol}: score={score:.1f}, "
                f"signal={metrics.contrarian_signal}, "
                f"P/C={pc_str}, CMF={cmf_str}"
            )

        return top_symbols

    def get_filter_statistics(
        self,
        sentiment_metrics: Dict[str, SentimentMetrics],
        filtered_symbols: List[str]
    ) -> Dict[str, any]:
        """
        Calculate statistics about filter results.

        Args:
            sentiment_metrics: Full universe sentiment data
            filtered_symbols: Symbols that passed filter

        Returns:
            Dictionary with filter statistics
        """
        total_symbols = len(sentiment_metrics)
        passed_symbols = len(filtered_symbols)

        # Count by signal type
        long_signals = sum(
            1 for s in filtered_symbols
            if sentiment_metrics[s].contrarian_signal == 'long'
        )
        short_signals = sum(
            1 for s in filtered_symbols
            if sentiment_metrics[s].contrarian_signal == 'short'
        )

        # Count by sentiment extreme
        negative_sentiment = sum(
            1 for s in filtered_symbols
            if sentiment_metrics[s].sentiment_extreme == 'negative'
        )
        positive_sentiment = sum(
            1 for s in filtered_symbols
            if sentiment_metrics[s].sentiment_extreme == 'positive'
        )

        return {
            'total_symbols_analyzed': total_symbols,
            'symbols_passed_filter': passed_symbols,
            'filter_rate_pct': (passed_symbols / total_symbols * 100) if total_symbols > 0 else 0,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'negative_sentiment_count': negative_sentiment,
            'positive_sentiment_count': positive_sentiment
        }


def example_usage():
    """Example usage of SentimentFilter."""
    from ..data.sentiment_aggregator import SentimentMetrics

    print("\n" + "="*60)
    print("Two-Step Sentiment Filter Example")
    print("="*60)

    # Create mock sentiment data
    mock_metrics = {
        # Symbol with LONG opportunity (high P/C + positive CMF)
        'GME': SentimentMetrics(
            symbol='GME',
            put_call_ratio_volume=2.1,
            cmf_20=0.15,
            sentiment_score=0.25,
            sentiment_extreme='negative',
            sentiment_rank=12,
            contrarian_signal='long',
            data_quality='complete'
        ),

        # Symbol with SHORT opportunity (low P/C + negative CMF)
        'TSLA': SentimentMetrics(
            symbol='TSLA',
            put_call_ratio_volume=0.5,
            cmf_20=-0.12,
            sentiment_score=0.78,
            sentiment_extreme='positive',
            sentiment_rank=88,
            contrarian_signal='short',
            data_quality='complete'
        ),

        # Symbol with extreme sentiment but NO divergence (skip)
        'AAPL': SentimentMetrics(
            symbol='AAPL',
            put_call_ratio_volume=1.8,
            cmf_20=-0.08,  # Negative CMF aligns with sentiment, no divergence
            sentiment_score=0.35,
            sentiment_extreme='negative',
            sentiment_rank=20,
            contrarian_signal='none',
            data_quality='complete'
        ),

        # Neutral symbol (filtered out)
        'SPY': SentimentMetrics(
            symbol='SPY',
            put_call_ratio_volume=1.0,
            cmf_20=0.02,
            sentiment_score=0.50,
            sentiment_extreme='neutral',
            sentiment_rank=50,
            contrarian_signal='none',
            data_quality='complete'
        )
    }

    # Apply filter
    filter_obj = SentimentFilter()
    filtered, reasons = filter_obj.apply_two_step_filter(mock_metrics)

    print(f"\nFilter Results:")
    print(f"  Input symbols: {len(mock_metrics)}")
    print(f"  Output symbols: {len(filtered)}")
    print(f"\nFiltered symbols:")
    for symbol in filtered:
        print(f"  ✓ {symbol}: {reasons.get(symbol, 'N/A')}")

    # Get statistics
    stats = filter_obj.get_filter_statistics(mock_metrics, filtered)
    print(f"\nFilter Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    example_usage()
