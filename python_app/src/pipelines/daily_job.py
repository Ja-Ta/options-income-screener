"""
Daily job pipeline for the Options Income Screener.

Orchestrates the complete screening workflow from data ingestion to alerts.
Python 3.12 compatible following CLAUDE.md standards.
"""

import time
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from ..config import (
    POLYGON_API_KEY, DEFAULT_SYMBOLS,
    CC_ENABLED, CSP_ENABLED,
    MAX_PICKS_TO_ALERT, CLAUDE_ENABLED, TELEGRAM_ENABLED
)
from ..data.polygon_client import PolygonClient
from ..features.iv_metrics import calculate_iv_metrics
from ..features.technicals import calculate_technical_indicators
from ..screeners.covered_calls import screen_multiple_cc
from ..screeners.cash_secured_puts import screen_multiple_csp
from ..scoring.score_cc import rank_cc_picks
from ..scoring.score_csp import rank_csp_picks
from ..storage.dao import (
    SymbolsDAO, PricesDAO, OptionsDAO, IVMetricsDAO,
    EarningsDAO, PicksDAO, RationalesDAO, AlertsDAO, StatsDAO
)
from ..services.telegram_service import TelegramService
from ..services.claude_service import ClaudeService
from ..utils.logging import get_logger, setup_logger as setup_logging


class DailyPipeline:
    """Orchestrates the complete daily screening pipeline."""

    def __init__(self, symbols: List[str] = None, asof: date = None):
        """
        Initialize the daily pipeline.

        Args:
            symbols: List of symbols to screen (defaults to config)
            asof: Date to run pipeline for (defaults to today)
        """
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.asof = asof or date.today()
        self.logger = get_logger()

        # Initialize components
        self.polygon_client = PolygonClient(POLYGON_API_KEY)
        self.symbols_dao = SymbolsDAO()
        self.prices_dao = PricesDAO()
        self.options_dao = OptionsDAO()
        self.iv_dao = IVMetricsDAO()
        self.earnings_dao = EarningsDAO()
        self.picks_dao = PicksDAO()
        self.rationales_dao = RationalesDAO()
        self.alerts_dao = AlertsDAO()
        self.stats_dao = StatsDAO()

        # Services (optional)
        self.telegram_service = TelegramService() if TELEGRAM_ENABLED else None
        self.claude_service = ClaudeService() if CLAUDE_ENABLED else None

    def run(self) -> Dict[str, Any]:
        """
        Execute the complete daily pipeline.

        Returns:
            Dictionary with pipeline results and statistics
        """
        self.logger.info(f"Starting daily pipeline for {self.asof}")
        start_time = time.time()

        results = {
            'date': self.asof,
            'symbols_processed': 0,
            'cc_picks': [],
            'csp_picks': [],
            'errors': [],
            'alerts_sent': 0,
            'duration': 0
        }

        try:
            # Step 1: Fetch and store market data
            self.logger.info("Step 1: Fetching market data...")
            market_data = self._fetch_market_data()
            results['symbols_processed'] = len(market_data['symbols_data'])

            # Step 2: Calculate technical indicators and IV metrics
            self.logger.info("Step 2: Calculating indicators and metrics...")
            enriched_data = self._calculate_indicators(market_data)

            # Step 3: Run screeners
            self.logger.info("Step 3: Running option screeners...")
            screening_results = self._run_screeners(enriched_data)
            results['cc_picks'] = screening_results['cc_picks']
            results['csp_picks'] = screening_results['csp_picks']

            # Step 4: Score and rank picks
            self.logger.info("Step 4: Scoring and ranking picks...")
            ranked_picks = self._score_picks(screening_results)

            # Step 5: Save to database
            self.logger.info("Step 5: Saving picks to database...")
            pick_ids = self._save_picks(ranked_picks)

            # Step 6: Generate AI rationales (optional)
            if self.claude_service and len(pick_ids) > 0:
                self.logger.info("Step 6: Generating AI rationales...")
                self._generate_rationales(ranked_picks)

            # Step 7: Send alerts (optional)
            if self.telegram_service and len(ranked_picks['top_picks']) > 0:
                self.logger.info("Step 7: Sending Telegram alerts...")
                alerts_sent = self._send_alerts(ranked_picks['top_picks'])
                results['alerts_sent'] = alerts_sent

            # Step 8: Generate summary statistics
            self.logger.info("Step 8: Generating summary...")
            summary = self._generate_summary()
            results['summary'] = summary

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            results['errors'].append(str(e))

        # Record duration
        results['duration'] = time.time() - start_time
        self.logger.info(f"Pipeline completed in {results['duration']:.2f} seconds")

        return results

    def _fetch_market_data(self) -> Dict[str, Any]:
        """
        Fetch market data from Polygon API.

        Returns:
            Dictionary with symbols_data, options_chains, and earnings_dates
        """
        symbols_data = {}
        options_chains = {}
        earnings_dates = {}

        for symbol in self.symbols:
            try:
                # Update symbol in database
                self.symbols_dao.upsert_symbol(symbol)

                # Fetch price data (returns dict with symbol as key)
                prices = self.polygon_client.get_daily_prices([symbol], self.asof)
                if symbol in prices:
                    price_data = prices[symbol]
                    symbols_data[symbol] = price_data

                    # Store price data
                    self.prices_dao.insert_prices([{
                        'symbol': symbol,
                        'asof': self.asof,
                        'close': price_data['close'],
                        'volume': price_data.get('volume')
                    }])

                # Fetch options chain
                chain = self.polygon_client.get_option_chain(symbol, self.asof)
                if chain:
                    options_chains[symbol] = chain

                    # Store options data
                    options_to_store = []
                    for option in chain:
                        options_to_store.append({
                            'symbol': symbol,
                            'asof': self.asof,
                            'expiry': option['expiry'],
                            'side': option['side'],
                            'strike': option['strike'],
                            'bid': option['bid'],
                            'ask': option['ask'],
                            'mid': option['mid'],
                            'delta': option['delta'],
                            'iv': option['iv'],
                            'oi': option['oi'],
                            'vol': option['vol'],
                            'dte': option['dte']
                        })

                    if options_to_store:
                        self.options_dao.insert_options_chain(options_to_store)

                # Fetch earnings date (mock for now)
                earnings_date = None  # Would fetch from API
                if earnings_date:
                    earnings_dates[symbol] = earnings_date
                    self.earnings_dao.upsert_earnings_date(symbol, earnings_date)

            except Exception as e:
                self.logger.warning(f"Failed to fetch data for {symbol}: {e}")
                continue

        return {
            'symbols_data': symbols_data,
            'options_chains': options_chains,
            'earnings_dates': earnings_dates
        }

    def _calculate_indicators(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate technical indicators and IV metrics.

        Args:
            market_data: Market data from fetch step

        Returns:
            Enriched market data with indicators
        """
        enriched = market_data.copy()

        for symbol, price_data in market_data['symbols_data'].items():
            try:
                # Calculate technical indicators (mock historical data for now)
                mock_historical = [price_data['close'] * (1 + i*0.001) for i in range(-60, 1)]
                indicators = calculate_technical_indicators(mock_historical)

                # Merge indicators into price data
                enriched['symbols_data'][symbol].update(indicators)

                # Calculate IV metrics
                if symbol in market_data['options_chains']:
                    iv_metrics = calculate_iv_metrics(symbol, self.asof)
                    enriched['symbols_data'][symbol].update(iv_metrics)

                    # Store IV metrics
                    self.iv_dao.insert_iv_metrics([{
                        'symbol': symbol,
                        'asof': self.asof,
                        'iv_rank': iv_metrics['iv_rank'],
                        'iv_percentile': iv_metrics['iv_percentile']
                    }])

            except Exception as e:
                self.logger.warning(f"Failed to calculate indicators for {symbol}: {e}")
                continue

        return enriched

    def _run_screeners(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run CC and CSP screeners on enriched data.

        Args:
            enriched_data: Market data with indicators

        Returns:
            Dictionary with CC and CSP picks
        """
        cc_picks = []
        csp_picks = []

        # Prepare IV metrics data structure
        iv_metrics_data = {}
        for symbol, data in enriched_data['symbols_data'].items():
            iv_metrics_data[symbol] = {
                'iv_rank': data.get('iv_rank', 50),
                'iv_percentile': data.get('iv_percentile', 50)
            }

        # Run CC screener if enabled
        if CC_ENABLED:
            cc_picks = screen_multiple_cc(
                enriched_data['symbols_data'],
                enriched_data['options_chains'],
                iv_metrics_data,
                enriched_data.get('earnings_dates', {})
            )
            self.logger.info(f"Found {len(cc_picks)} CC picks")

        # Run CSP screener if enabled
        if CSP_ENABLED:
            csp_picks = screen_multiple_csp(
                enriched_data['symbols_data'],
                enriched_data['options_chains'],
                iv_metrics_data,
                enriched_data.get('earnings_dates', {})
            )
            self.logger.info(f"Found {len(csp_picks)} CSP picks")

        return {
            'cc_picks': cc_picks,
            'csp_picks': csp_picks
        }

    def _score_picks(self, screening_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score and rank all picks.

        Args:
            screening_results: CC and CSP picks from screeners

        Returns:
            Dictionary with ranked picks and top picks
        """
        # Score CC picks
        cc_ranked = rank_cc_picks(screening_results['cc_picks'])

        # Score CSP picks
        csp_ranked = rank_csp_picks(screening_results['csp_picks'])

        # Combine and get top picks
        all_picks = cc_ranked + csp_ranked
        all_picks.sort(key=lambda x: x.get('score', 0), reverse=True)

        # Select top picks for alerts
        top_picks = all_picks[:MAX_PICKS_TO_ALERT]

        return {
            'cc_picks': cc_ranked,
            'csp_picks': csp_ranked,
            'all_picks': all_picks,
            'top_picks': top_picks
        }

    def _save_picks(self, ranked_picks: Dict[str, Any]) -> List[int]:
        """
        Save picks to database.

        Args:
            ranked_picks: Ranked picks from scoring step

        Returns:
            List of inserted pick IDs
        """
        all_picks = ranked_picks['all_picks']

        # Add asof date to each pick
        for pick in all_picks:
            pick['asof'] = self.asof

        # Insert picks and get IDs
        pick_ids = self.picks_dao.insert_picks(all_picks)

        # Update picks with IDs for later use
        for pick, pick_id in zip(all_picks, pick_ids):
            pick['id'] = pick_id

        self.logger.info(f"Saved {len(pick_ids)} picks to database")
        return pick_ids

    def _generate_rationales(self, ranked_picks: Dict[str, Any]) -> None:
        """
        Generate AI rationales for top picks.

        Args:
            ranked_picks: Ranked picks with IDs
        """
        try:
            top_picks = ranked_picks['top_picks']
            rationales = self.claude_service.generate_batch_rationales(top_picks)

            # Save rationales to database
            for pick_id, rationale in rationales.items():
                self.rationales_dao.insert_rationale(pick_id, rationale)

            self.logger.info(f"Generated {len(rationales)} AI rationales")

        except Exception as e:
            self.logger.error(f"Failed to generate rationales: {e}")

    def _send_alerts(self, top_picks: List[Dict[str, Any]]) -> int:
        """
        Send Telegram alerts for top picks.

        Args:
            top_picks: List of top picks to alert

        Returns:
            Number of alerts sent
        """
        try:
            # Get rationales for picks
            rationales = {}
            for pick in top_picks:
                pick_id = pick.get('id')
                if pick_id:
                    rationale = self.rationales_dao.get_rationale(pick_id)
                    if rationale:
                        rationales[pick_id] = rationale

            # Send picks via Telegram
            results = self.telegram_service.send_picks(top_picks, rationales)

            # Record alerts in database
            for pick in top_picks:
                pick_id = pick.get('id')
                if pick_id and pick['symbol'] in results['sent']:
                    self.alerts_dao.mark_alert_sent(pick_id, 'telegram')

            return len(results['sent'])

        except Exception as e:
            self.logger.error(f"Failed to send alerts: {e}")
            return 0

    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate daily summary statistics.

        Returns:
            Summary dictionary
        """
        summary = self.stats_dao.get_daily_summary(self.asof)

        # Send summary via Telegram if enabled
        if self.telegram_service:
            try:
                self.telegram_service.send_daily_summary(summary)
            except Exception as e:
                self.logger.error(f"Failed to send summary: {e}")

        return summary


def run_daily_job(symbols: List[str] = None, asof: date = None) -> Dict[str, Any]:
    """
    Main entry point for daily job execution.

    Args:
        symbols: Optional list of symbols to screen
        asof: Optional date to run for (defaults to today)

    Returns:
        Pipeline execution results
    """
    setup_logging()
    pipeline = DailyPipeline(symbols, asof)
    return pipeline.run()


# Legacy support
def run_daily(asof: date = None):
    """Legacy function name for backward compatibility."""
    return run_daily_job(asof=asof)


if __name__ == "__main__":
    # Run with mock data for testing
    results = run_daily_job()
    print(f"Pipeline completed: {len(results.get('cc_picks', []))} CC picks, "
          f"{len(results.get('csp_picks', []))} CSP picks")
