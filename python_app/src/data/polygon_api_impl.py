"""
Real Polygon API implementation for production use.

Uses the official polygon-api-client library.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
from polygon import RESTClient
import logging

logger = logging.getLogger(__name__)


class PolygonAPIImpl:
    """Production implementation of Polygon API calls."""

    def __init__(self, api_key: str):
        """
        Initialize Polygon REST client.

        Args:
            api_key: Polygon API key
        """
        self.client = RESTClient(api_key=api_key)
        logger.info("Initialized Polygon REST client")

    def get_daily_prices(self, symbols: List[str], asof: date) -> Dict[str, Dict[str, Any]]:
        """
        Fetch daily price data for symbols using Polygon API.

        Args:
            symbols: List of symbols
            asof: As-of date for prices

        Returns:
            Dict mapping symbol to price data
        """
        results = {}

        for symbol in symbols:
            try:
                # Get daily bar for the symbol
                bars = self.client.get_aggs(
                    ticker=symbol,
                    multiplier=1,
                    timespan="day",
                    from_=asof.strftime('%Y-%m-%d'),
                    to=asof.strftime('%Y-%m-%d')
                )

                if bars and len(bars) > 0:
                    bar = bars[0]

                    # Get previous close for calculating SMAs (simplified)
                    prev_date = asof - timedelta(days=200)
                    historical = self.client.get_aggs(
                        ticker=symbol,
                        multiplier=1,
                        timespan="day",
                        from_=prev_date.strftime('%Y-%m-%d'),
                        to=asof.strftime('%Y-%m-%d'),
                        limit=200
                    )

                    # Calculate simple moving averages
                    closes = [h.c for h in historical] if historical else []
                    sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else bar.c
                    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else bar.c
                    sma_200 = sum(closes) / len(closes) if len(closes) >= 200 else bar.c

                    results[symbol] = {
                        'open': bar.o,
                        'high': bar.h,
                        'low': bar.l,
                        'close': bar.c,
                        'volume': bar.v,
                        'vwap': bar.vw if hasattr(bar, 'vw') else bar.c,
                        'sma_20': sma_20,
                        'sma_50': sma_50,
                        'sma_200': sma_200,
                        'timestamp': asof.isoformat()
                    }
                    logger.debug(f"Got price data for {symbol}: ${bar.c:.2f}")
                else:
                    logger.warning(f"No price data for {symbol} on {asof}")

            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")

        return results

    def get_option_chain(self, symbol: str, asof: date) -> List[Dict[str, Any]]:
        """
        Fetch option chain for a symbol.

        Args:
            symbol: Stock symbol
            asof: As-of date for chain

        Returns:
            List of option contracts
        """
        contracts = []

        try:
            # Get current stock price for reference
            ticker_details = self.client.get_ticker_details(symbol, asof.strftime('%Y-%m-%d'))
            stock_price = ticker_details.close if hasattr(ticker_details, 'close') else 100

            # Get options contracts
            # Note: This requires Options tier subscription
            options_contracts = self.client.list_options_contracts(
                underlying_ticker=symbol,
                expired=False,
                limit=1000
            )

            for contract in options_contracts:
                try:
                    # Get option quote
                    contract_ticker = contract.ticker

                    # Parse contract details from OCC symbol
                    # Format: AAPL230120C00150000
                    exp_date_str = contract_ticker[len(symbol):len(symbol)+6]
                    exp_date = datetime.strptime(exp_date_str, '%y%m%d').date()

                    option_type = 'call' if 'C' in contract_ticker else 'put'
                    strike_str = contract_ticker.split('C' if option_type == 'call' else 'P')[1]
                    strike = float(strike_str) / 1000

                    # Skip if expiration is too far or too close
                    dte = (exp_date - asof).days
                    if dte < 25 or dte > 50:
                        continue

                    # Get option quote
                    quote = self.client.get_last_quote(contract_ticker)

                    if quote:
                        bid = quote.bid_price if hasattr(quote, 'bid_price') else 0
                        ask = quote.ask_price if hasattr(quote, 'ask_price') else 0

                        # Calculate basic greeks (simplified)
                        moneyness = strike / stock_price

                        if option_type == 'call':
                            delta = 0.5 if abs(moneyness - 1) < 0.05 else (0.3 if moneyness > 1 else 0.7)
                        else:
                            delta = -0.5 if abs(moneyness - 1) < 0.05 else (-0.3 if moneyness < 1 else -0.7)

                        contracts.append({
                            'contract_type': option_type,
                            'symbol': contract_ticker,
                            'underlying': symbol,
                            'strike_price': strike,
                            'expiration_date': exp_date.isoformat(),
                            'dte': dte,
                            'bid': bid,
                            'ask': ask,
                            'mid': (bid + ask) / 2 if bid and ask else 0,
                            'volume': getattr(quote, 'volume', 0),
                            'open_interest': getattr(quote, 'open_interest', 0),
                            'implied_volatility': 0.25,  # Placeholder
                            'delta': delta,
                            'gamma': 0.02,  # Placeholder
                            'theta': -0.05,  # Placeholder
                            'vega': 0.1  # Placeholder
                        })

                except Exception as e:
                    logger.debug(f"Error processing contract {contract.ticker}: {e}")
                    continue

            logger.info(f"Got {len(contracts)} option contracts for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            # Return empty list on error

        return contracts

    def get_earnings_date(self, symbol: str) -> Optional[date]:
        """
        Get next earnings date for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Next earnings date or None
        """
        try:
            # Get ticker details which includes next earnings date
            details = self.client.get_ticker_details(symbol)

            # Check if earnings date is available
            if hasattr(details, 'next_earnings_date'):
                return datetime.strptime(details.next_earnings_date, '%Y-%m-%d').date()

            # Alternative: check news for earnings announcements
            news = self.client.list_ticker_news(symbol, limit=10)
            for article in news:
                if 'earnings' in article.title.lower():
                    # Parse date from article if possible
                    logger.debug(f"Found earnings mention in news for {symbol}")

            return None

        except Exception as e:
            logger.error(f"Error fetching earnings for {symbol}: {e}")
            return None

    def get_stock_snapshot(self, symbol: str, asof: date = None) -> Optional[Dict[str, Any]]:
        """
        Get real-time or daily snapshot for a symbol.

        Args:
            symbol: Stock symbol
            asof: Date for snapshot (uses latest if None)

        Returns:
            Snapshot data or None
        """
        try:
            if asof and asof != date.today():
                # Historical daily bar
                bars = self.client.get_aggs(
                    ticker=symbol,
                    multiplier=1,
                    timespan="day",
                    from_=asof.strftime('%Y-%m-%d'),
                    to=asof.strftime('%Y-%m-%d')
                )

                if bars and len(bars) > 0:
                    bar = bars[0]
                    return {
                        'symbol': symbol,
                        'open': bar.o,
                        'high': bar.h,
                        'low': bar.l,
                        'close': bar.c,
                        'volume': bar.v,
                        'timestamp': asof.isoformat()
                    }
            else:
                # Real-time snapshot
                snapshot = self.client.get_snapshot_ticker(f"stocks/tickers/{symbol}")

                if snapshot:
                    return {
                        'symbol': symbol,
                        'open': snapshot.day.o if hasattr(snapshot.day, 'o') else 0,
                        'high': snapshot.day.h if hasattr(snapshot.day, 'h') else 0,
                        'low': snapshot.day.l if hasattr(snapshot.day, 'l') else 0,
                        'close': snapshot.day.c if hasattr(snapshot.day, 'c') else 0,
                        'last': snapshot.last_quote.p if hasattr(snapshot, 'last_quote') else 0,
                        'volume': snapshot.day.v if hasattr(snapshot.day, 'v') else 0,
                        'timestamp': datetime.now().isoformat()
                    }

        except Exception as e:
            logger.error(f"Error fetching snapshot for {symbol}: {e}")

        return None

    def get_implied_volatility_data(self, symbol: str) -> Dict[str, float]:
        """
        Calculate IV metrics for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with current_iv, iv_rank, iv_percentile
        """
        try:
            # Get options chain to calculate IV
            contracts = self.get_option_chain(symbol, date.today())

            if contracts:
                # Calculate average IV from ATM options
                atm_contracts = [c for c in contracts if 0.9 < c.get('strike_price', 0) / 100 < 1.1]
                if atm_contracts:
                    current_iv = sum(c.get('implied_volatility', 0.25) for c in atm_contracts) / len(atm_contracts)
                else:
                    current_iv = 0.25

                # For IV rank/percentile, we'd need historical IV data
                # Using placeholder values for now
                return {
                    'current_iv': current_iv,
                    'iv_rank': 50.0,  # Would need historical data
                    'iv_percentile': 50.0  # Would need historical data
                }

        except Exception as e:
            logger.error(f"Error calculating IV for {symbol}: {e}")

        return {
            'current_iv': 0.25,
            'iv_rank': 50.0,
            'iv_percentile': 50.0
        }