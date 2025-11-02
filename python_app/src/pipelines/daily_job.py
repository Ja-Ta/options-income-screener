"""
Daily job pipeline for the Options Income Screener.

Orchestrates the complete screening workflow using real Polygon data.
Python 3.12 compatible following CLAUDE.md standards.
"""

import time
import os
import sys
import csv
import sqlite3
import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ..data.real_options_fetcher import RealOptionsFetcher
from ..services.telegram_service import TelegramService
from ..services.claude_service import ClaudeService
from ..services.monitoring_service import MonitoringService
from ..scoring.score_cc import score_cc_pick
from ..scoring.score_csp import score_csp_pick
from ..features.technicals import compute_technical_features
from ..constants import HISTORICAL_DAYS_TO_FETCH


# Configure logging
logger = logging.getLogger(__name__)


class ProductionPipeline:
    """
    Production-ready pipeline for daily options screening.

    Integrates real Massive.com API data (formerly Polygon) with error handling,
    retry logic, and comprehensive logging.
    """

    @staticmethod
    def load_universe_symbols(universe_file: str = "python_app/src/data/universe.csv") -> List[str]:
        """
        Load symbols from universe CSV file.

        Args:
            universe_file: Path to universe CSV file (relative to project root)

        Returns:
            List of symbol strings
        """
        symbols = []
        try:
            with open(universe_file, 'r') as f:
                reader = csv.DictReader(f)
                symbols = [row['symbol'] for row in reader]
            logger.info(f"Loaded {len(symbols)} symbols from {universe_file}")
        except FileNotFoundError:
            logger.error(f"Universe file not found: {universe_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading universe file: {e}")
            raise

        return symbols

    def __init__(
        self,
        api_key: str,
        symbols: List[str] = None,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize the production pipeline.

        Args:
            api_key: Massive.com API key (Polygon API keys still work)
            symbols: List of symbols to screen (defaults to production symbols)
            max_retries: Maximum number of retries for API failures
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Load symbols from universe.csv or use provided symbols
        self.symbols = symbols or self.load_universe_symbols()

        # Initialize services
        self.fetcher = RealOptionsFetcher(api_key)
        self.telegram = TelegramService()
        self.claude = ClaudeService()
        self.monitoring = MonitoringService()

        # Database paths (unified - run from project root)
        self.python_db_path = "data/screener.db"
        self.node_db_path = "data/screener.db"

        # Run tracking
        self.run_id = None

        # Statistics
        self.stats = {
            'symbols_attempted': 0,
            'symbols_succeeded': 0,
            'symbols_failed': 0,
            'total_picks': 0,
            'cc_picks': 0,
            'csp_picks': 0,
            'api_calls': 0,
            'errors': []
        }

    def calculate_score(self, option: Dict, strategy: str) -> float:
        """
        Calculate composite score for an option using Greek-enhanced scoring.

        Args:
            option: Option data dictionary with Greeks (delta, theta, gamma, vega)
            strategy: "CC" or "CSP"

        Returns:
            Composite score (0-1)
        """
        if strategy == 'CC':
            return score_cc_pick(option)
        else:
            return score_csp_pick(option)

    def screen_symbol_with_retry(self, symbol: str) -> Dict:
        """
        Screen a single symbol with retry logic.

        Args:
            symbol: Stock symbol to screen

        Returns:
            Dictionary with cc_picks and csp_picks
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Screening {symbol} (attempt {attempt + 1}/{self.max_retries})...")

                # Get stock price
                stock_price = self.fetcher.get_stock_price(symbol)
                if not stock_price:
                    logger.warning(f"Could not get stock price for {symbol}")
                    return {'symbol': symbol, 'cc_picks': [], 'csp_picks': []}

                self.stats['api_calls'] += 1

                # Fetch historical price data for trend analysis
                historical_data = self.fetcher.get_historical_prices(symbol, days=HISTORICAL_DAYS_TO_FETCH)
                technical_features = {}

                if historical_data and len(historical_data.get('prices', [])) >= 200:
                    # Compute technical features including trend indicators
                    price_data = {
                        'close': stock_price,
                        'prices': historical_data['prices'],
                        'highs': historical_data.get('highs'),
                        'lows': historical_data.get('lows')
                    }
                    technical_features = compute_technical_features(price_data)
                    self.stats['api_calls'] += 1
                    logger.info(f"  {symbol} technical features: trend_strength={technical_features.get('trend_strength', 0):.2f}, trend_stability={technical_features.get('trend_stability', 0.5):.2f}")
                else:
                    logger.warning(f"  Insufficient historical data for {symbol}, using default values")
                    # Use default/placeholder values
                    technical_features = {
                        'trend_strength': 0,
                        'trend_stability': 0.5,
                        'in_uptrend': False,
                        'below_200sma': False,
                        'above_support': True,
                        'sma20': stock_price,
                        'sma50': stock_price,
                        'sma200': stock_price
                    }

                # Find covered calls
                cc_candidates = self.fetcher.find_covered_call_candidates(symbol, stock_price)
                cc_picks = []

                for candidate in cc_candidates:
                    if candidate['mid'] > 0:
                        candidate['strategy'] = 'CC'
                        candidate['premium'] = candidate['mid']

                        # Add fields required by scoring function
                        candidate['iv_rank'] = candidate.get('iv', 0) * 100  # Convert IV to rank (0-100)
                        candidate['trend_strength'] = technical_features.get('trend_strength', 0)
                        candidate['dividend_yield'] = 0  # Placeholder (can be added later via API)
                        candidate['below_200sma'] = technical_features.get('below_200sma', False)

                        # Determine trend classification
                        ts = candidate['trend_strength']
                        if ts > 0.5:
                            candidate['trend'] = 'uptrend'
                        elif ts < -0.5:
                            candidate['trend'] = 'downtrend'
                        else:
                            candidate['trend'] = 'neutral'

                        candidate['score'] = self.calculate_score(candidate, 'CC')
                        candidate['earnings_days'] = 45  # Placeholder (can be added later via earnings API)
                        cc_picks.append(candidate)

                self.stats['api_calls'] += len(cc_candidates)

                # Find cash-secured puts
                csp_candidates = self.fetcher.find_cash_secured_put_candidates(symbol, stock_price)
                csp_picks = []

                for candidate in csp_candidates:
                    if candidate['mid'] > 0:
                        candidate['strategy'] = 'CSP'
                        candidate['premium'] = candidate['mid']

                        # Add fields required by scoring function
                        candidate['iv_rank'] = candidate.get('iv', 0) * 100  # Convert IV to rank (0-100)
                        candidate['margin_of_safety'] = (stock_price - candidate['strike']) / stock_price if stock_price > 0 else 0
                        candidate['trend_stability'] = technical_features.get('trend_stability', 0.5)
                        candidate['in_uptrend'] = technical_features.get('in_uptrend', False)

                        # Determine trend classification
                        ts = technical_features.get('trend_strength', 0)
                        if ts > 0.5:
                            candidate['trend'] = 'uptrend'
                        elif ts < -0.5:
                            candidate['trend'] = 'downtrend'
                        else:
                            candidate['trend'] = 'neutral'

                        candidate['score'] = self.calculate_score(candidate, 'CSP')
                        candidate['earnings_days'] = 45  # Placeholder (can be added later via earnings API)
                        csp_picks.append(candidate)

                self.stats['api_calls'] += len(csp_candidates)

                # Sort by score
                cc_picks.sort(key=lambda x: x['score'], reverse=True)
                csp_picks.sort(key=lambda x: x['score'], reverse=True)

                logger.info(f"  Found {len(cc_picks)} CC and {len(csp_picks)} CSP candidates for {symbol}")

                return {
                    'symbol': symbol,
                    'cc_picks': cc_picks[:2],  # Top 2 of each
                    'csp_picks': csp_picks[:2]
                }

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")

                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All retries exhausted for {symbol}")
                    self.stats['errors'].append(f"{symbol}: {str(e)}")
                    return {'symbol': symbol, 'cc_picks': [], 'csp_picks': []}

        return {'symbol': symbol, 'cc_picks': [], 'csp_picks': []}

    def save_picks_to_db(self, all_picks: List[Dict]) -> tuple[int, List[Dict]]:
        """
        Save picks to both Python and Node.js databases.

        Args:
            all_picks: List of all picks

        Returns:
            Tuple of (number_saved, picks_with_ids)
        """
        if not all_picks:
            return 0, []

        today = date.today()
        inserted = 0
        picks_with_ids = []

        try:
            # Save to Python database
            conn = sqlite3.connect(self.python_db_path)
            cursor = conn.cursor()

            # Clear today's picks
            cursor.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

            for pick in all_picks:
                try:
                    # Calculate IV rank
                    iv_rank = min(pick.get('iv', 0.5) * 100, 100) if pick.get('iv') else 50

                    cursor.execute('''
                        INSERT INTO picks (
                            date, asof, symbol, strategy, strike, expiry,
                            premium, stock_price, roi_30d, annualized_return,
                            iv_rank, score, trend, earnings_days
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        today.isoformat(), today.isoformat(),
                        pick['symbol'], pick['strategy'],
                        pick['strike'], pick['expiry'],
                        pick['premium'], pick['stock_price'],
                        pick['roi_30d'], pick['annualized_return'],
                        iv_rank, pick['score'],
                        pick['trend'], pick['earnings_days']
                    ))

                    pick_id = cursor.lastrowid
                    pick_copy = pick.copy()
                    pick_copy['id'] = pick_id
                    pick_copy['spot_price'] = pick['stock_price']
                    pick_copy['iv_rank'] = iv_rank
                    picks_with_ids.append(pick_copy)
                    inserted += 1

                except Exception as e:
                    logger.error(f"Error inserting pick: {e}")

            conn.commit()
            conn.close()

            logger.info(f"Saved {inserted} picks to Python database")

            # Sync to Node.js database
            try:
                conn2 = sqlite3.connect(self.node_db_path)
                cursor2 = conn2.cursor()
                cursor2.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

                for pick in all_picks:
                    try:
                        iv_rank = min(pick.get('iv', 0.5) * 100, 100) if pick.get('iv') else 50

                        cursor2.execute('''
                            INSERT INTO picks (
                                date, asof, symbol, strategy, strike, expiry,
                                premium, stock_price, roi_30d, annualized_return,
                                iv_rank, score, trend, earnings_days
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            today.isoformat(), today.isoformat(),
                            pick['symbol'], pick['strategy'],
                            pick['strike'], pick['expiry'],
                            pick['premium'], pick['stock_price'],
                            pick['roi_30d'], pick['annualized_return'],
                            iv_rank, pick['score'],
                            pick['trend'], pick['earnings_days']
                        ))
                    except Exception as e:
                        logger.error(f"Error syncing pick to Node DB: {e}")

                conn2.commit()
                conn2.close()
                logger.info(f"Synced {inserted} picks to Node.js database")

            except Exception as e:
                logger.error(f"Error syncing to Node database: {e}")
                # Continue even if sync fails

        except Exception as e:
            logger.error(f"Error saving to Python database: {e}")
            self.stats['errors'].append(f"Database error: {str(e)}")

        return inserted, picks_with_ids

    def generate_and_save_rationales(self, picks: List[Dict]) -> int:
        """
        Generate Claude AI rationales for top picks and save to database.

        Args:
            picks: List of picks with IDs

        Returns:
            Number of rationales generated
        """
        if not picks:
            return 0

        try:
            # Take top 5 picks for rationale generation to manage API costs
            top_picks = sorted(picks, key=lambda x: x.get('score', 0), reverse=True)[:5]

            logger.info(f"Generating AI rationales for top {len(top_picks)} picks...")

            # Add required fields for Claude service
            for pick in top_picks:
                # Ensure trend_strength exists (should already be calculated during screening)
                if 'trend_strength' not in pick:
                    # Fallback based on trend classification if not already present
                    if pick.get('trend') == 'uptrend':
                        pick['trend_strength'] = 0.6
                    elif pick.get('trend') == 'neutral':
                        pick['trend_strength'] = 0
                    else:
                        pick['trend_strength'] = -0.4

                # Add other fields Claude expects (fallbacks if not present)
                if 'below_200sma' not in pick:
                    pick['below_200sma'] = False  # Simplified fallback
                if 'margin_of_safety' not in pick:
                    pick['margin_of_safety'] = abs(pick['stock_price'] - pick['strike']) / pick['stock_price']

            # Generate rationales
            rationales = self.claude.generate_batch_rationales(top_picks)

            if rationales:
                logger.info(f"Generated {len(rationales)} rationales")

                # Save rationales to database
                conn = sqlite3.connect(self.python_db_path)
                cursor = conn.cursor()

                for pick_id, rationale_text in rationales.items():
                    try:
                        # Update pick with rationale
                        cursor.execute('''
                            UPDATE picks
                            SET rationale = ?
                            WHERE id = ?
                        ''', (rationale_text, pick_id))

                        # Delete existing rationales for this pick to prevent duplicates
                        cursor.execute('''
                            DELETE FROM rationales WHERE pick_id = ?
                        ''', (pick_id,))

                        # Insert new rationale
                        cursor.execute('''
                            INSERT INTO rationales (pick_id, summary, created_at)
                            VALUES (?, ?, datetime('now'))
                        ''', (pick_id, rationale_text))

                        logger.debug(f"Saved rationale for pick {pick_id} ({rationale_text[:50]}...)")
                    except Exception as e:
                        logger.error(f"Error saving rationale for pick {pick_id}: {e}")

                conn.commit()
                conn.close()
                logger.info(f"Saved {len(rationales)} rationales to database")
                return len(rationales)

        except Exception as e:
            logger.error(f"Error generating rationales: {e}")
            self.stats['errors'].append(f"Claude API error: {str(e)}")

        return 0

    def send_alerts(self, cc_picks: List[Dict], csp_picks: List[Dict]) -> bool:
        """
        Send alerts via Telegram with AI rationales.

        Args:
            cc_picks: List of CC picks
            csp_picks: List of CSP picks

        Returns:
            True if alert sent successfully
        """
        if not cc_picks and not csp_picks:
            return False

        try:
            # Get rationales from database
            conn = sqlite3.connect(self.python_db_path)
            cursor = conn.cursor()
            rationales_map = {}

            try:
                cursor.execute('''
                    SELECT id, rationale FROM picks
                    WHERE date = ? AND rationale IS NOT NULL
                ''', (date.today().isoformat(),))

                for row in cursor.fetchall():
                    rationales_map[row[0]] = row[1]
            finally:
                conn.close()

            # Format message
            message = f"🎯 **Daily Options Screening Results**\n"
            message += f"📅 {date.today()}\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

            if cc_picks:
                message += f"📈 **Top Covered Calls ({len(cc_picks)})**\n"
                for pick in cc_picks[:3]:
                    message += f"\n• **{pick['symbol']}** @ ${pick['strike']:.2f}\n"
                    message += f"  Premium: ${pick.get('premium', 0):.2f} | ROI: {pick.get('roi_30d', 0):.1%}\n"
                    if pick.get('iv'):
                        message += f"  IV: {pick['iv']:.1%} | Score: {pick.get('score', 0):.2f}\n"

                    # Add rationale if available
                    if pick.get('id') and pick['id'] in rationales_map:
                        rationale = rationales_map[pick['id']]
                        if len(rationale) > 150:
                            rationale = rationale[:147] + "..."
                        message += f"  💡 {rationale}\n"
                message += "\n"

            if csp_picks:
                message += f"💰 **Top Cash-Secured Puts ({len(csp_picks)})**\n"
                for pick in csp_picks[:3]:
                    message += f"\n• **{pick['symbol']}** @ ${pick['strike']:.2f}\n"
                    message += f"  Premium: ${pick.get('premium', 0):.2f} | ROI: {pick.get('roi_30d', 0):.1%}\n"
                    if pick.get('iv'):
                        message += f"  IV: {pick['iv']:.1%} | Score: {pick.get('score', 0):.2f}\n"

                    # Add rationale if available
                    if pick.get('id') and pick['id'] in rationales_map:
                        rationale = rationales_map[pick['id']]
                        if len(rationale) > 150:
                            rationale = rationale[:147] + "..."
                        message += f"  💡 {rationale}\n"

            message += f"\n📊 Dashboard: http://157.245.214.224:3000"
            message += f"\n🤖 AI rationales powered by Claude"

            # Send message
            return self.telegram.send_message(message)

        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
            self.stats['errors'].append(f"Telegram error: {str(e)}")
            return False

    def run(self) -> Dict[str, Any]:
        """
        Execute the complete production pipeline.

        Returns:
            Dictionary with pipeline results and statistics
        """
        start_time = time.time()

        # Record pipeline start in monitoring
        self.run_id = self.monitoring.record_pipeline_start()

        logger.info("="*60)
        logger.info("PRODUCTION OPTIONS SCREENING PIPELINE")
        logger.info("="*60)
        logger.info(f"Date: {date.today()}")
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Screening {len(self.symbols)} symbols")
        logger.info("-"*60)

        all_picks = []

        # Screen each symbol
        for symbol in self.symbols:
            self.stats['symbols_attempted'] += 1

            try:
                result = self.screen_symbol_with_retry(symbol)

                if result['cc_picks'] or result['csp_picks']:
                    self.stats['symbols_succeeded'] += 1
                    all_picks.extend(result['cc_picks'])
                    all_picks.extend(result['csp_picks'])
                else:
                    self.stats['symbols_failed'] += 1

                # Minimal delay for API politeness (no rate limits with Options Advanced)
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Fatal error screening {symbol}: {e}")
                self.stats['symbols_failed'] += 1
                self.stats['errors'].append(f"{symbol}: {str(e)}")

        # Sort all picks by score
        all_picks.sort(key=lambda x: x['score'], reverse=True)

        # Separate by strategy
        cc_picks = [p for p in all_picks if p['strategy'] == 'CC']
        csp_picks = [p for p in all_picks if p['strategy'] == 'CSP']

        self.stats['total_picks'] = len(all_picks)
        self.stats['cc_picks'] = len(cc_picks)
        self.stats['csp_picks'] = len(csp_picks)

        logger.info(f"\nFound {len(cc_picks)} CC and {len(csp_picks)} CSP picks")

        # Save to database
        picks_with_ids = []
        if all_picks:
            logger.info("\nSaving to database...")
            saved, picks_with_ids = self.save_picks_to_db(all_picks)
            logger.info(f"Saved {saved} picks")

            # Generate AI rationales for top picks
            rationales_count = self.generate_and_save_rationales(picks_with_ids)
            logger.info(f"Generated {rationales_count} AI rationales")

            # Send alerts
            logger.info("\nSending alerts...")
            if self.send_alerts(cc_picks, csp_picks):
                logger.info("Telegram alert sent successfully")
            else:
                logger.warning("Failed to send Telegram alert")

        # Calculate duration
        duration = time.time() - start_time
        self.stats['duration'] = duration

        # Print summary
        logger.info("\n" + "="*60)
        logger.info("PIPELINE SUMMARY")
        logger.info("="*60)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Symbols attempted: {self.stats['symbols_attempted']}")
        logger.info(f"Symbols succeeded: {self.stats['symbols_succeeded']}")
        logger.info(f"Symbols failed: {self.stats['symbols_failed']}")
        logger.info(f"Total picks: {self.stats['total_picks']}")
        logger.info(f"CC picks: {self.stats['cc_picks']}")
        logger.info(f"CSP picks: {self.stats['csp_picks']}")
        logger.info(f"API calls: {self.stats['api_calls']}")

        if self.stats['errors']:
            logger.warning(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                logger.warning(f"  - {error}")

        logger.info("="*60)
        logger.info("PIPELINE COMPLETE")
        logger.info("="*60)

        # Determine pipeline status
        pipeline_success = self.stats['symbols_failed'] < self.stats['symbols_attempted']
        if pipeline_success and self.stats['symbols_succeeded'] > 0:
            status = 'success'
        elif self.stats['symbols_succeeded'] > 0:
            status = 'partial'
        else:
            status = 'failed'

        # Record pipeline completion in monitoring
        error_message = None
        if self.stats['errors']:
            error_message = f"{len(self.stats['errors'])} errors occurred"

        self.monitoring.record_pipeline_completion(
            run_id=self.run_id,
            status=status,
            stats=self.stats,
            error_message=error_message
        )

        return {
            'success': pipeline_success,
            'run_id': self.run_id,
            'stats': self.stats,
            'cc_picks': cc_picks,
            'csp_picks': csp_picks
        }


def run_daily_job(
    symbols: List[str] = None,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Dict[str, Any]:
    """
    Main entry point for daily job execution.

    Args:
        symbols: Optional list of symbols to screen (defaults to production symbols)
        max_retries: Maximum number of retries for API failures (default: 3)
        retry_delay: Delay between retries in seconds (default: 5)

    Returns:
        Pipeline execution results
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.error("No POLYGON_API_KEY found in environment")
        return {
            'success': False,
            'error': 'Missing POLYGON_API_KEY',
            'stats': {}
        }

    try:
        # Create and run pipeline
        pipeline = ProductionPipeline(
            api_key=api_key,
            symbols=symbols,
            max_retries=max_retries,
            retry_delay=retry_delay
        )

        return pipeline.run()

    except Exception as e:
        logger.error(f"Pipeline fatal error: {e}")

        # Try to send error notification
        try:
            telegram = TelegramService()
            telegram.send_message(
                f"❌ **Pipeline Fatal Error**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 {datetime.now()}\n"
                f"⚠️ Error: {str(e)}\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
        except:
            pass  # Fail silently if Telegram also fails

        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


# Legacy support
def run_daily(asof: date = None):
    """Legacy function name for backward compatibility."""
    return run_daily_job()


if __name__ == "__main__":
    # Run production pipeline
    results = run_daily_job()

    if results.get('success'):
        print(f"\n✅ Pipeline completed successfully!")
        print(f"Total picks: {results['stats']['total_picks']}")
        print(f"CC picks: {results['stats']['cc_picks']}")
        print(f"CSP picks: {results['stats']['csp_picks']}")
    else:
        print(f"\n❌ Pipeline failed!")
        if 'error' in results:
            print(f"Error: {results['error']}")
        sys.exit(1)
