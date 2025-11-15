"""
Alpha Vantage API Client for Fundamental Data

Provides company fundamentals including shares outstanding, market cap, etc.
Note: Short interest data is NOT available via Alpha Vantage - requires separate source.

API Documentation: https://www.alphavantage.co/documentation/
"""

import os
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlphaVantageClient:
    """
    Client for Alpha Vantage API to fetch fundamental data.

    Rate Limits:
    - Free tier: 5 API requests per minute, 500 per day
    - Premium: 75 requests per minute, higher daily limits
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage client.

        Args:
            api_key: Alpha Vantage API key (or from ALPHAVANTAGE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("Alpha Vantage API key required. Set ALPHAVANTAGE_API_KEY environment variable.")

        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 12.5  # seconds (5 requests per minute for free tier)

        logger.info("AlphaVantageClient initialized")

    def _rate_limit(self):
        """Enforce rate limiting to stay within API limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make API request with rate limiting and error handling.

        Args:
            params: Query parameters for API request

        Returns:
            JSON response as dictionary

        Raises:
            requests.RequestException: If API request fails
        """
        self._rate_limit()

        params['apikey'] = self.api_key

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Check for API error messages
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                raise ValueError(f"API Error: {data['Error Message']}")

            if "Note" in data:
                # Rate limit message
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                time.sleep(60)  # Wait 1 minute before retrying
                return self._make_request(params)

            return data

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive company fundamentals.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with company fundamentals including:
            - Symbol, Name, Exchange, Currency
            - MarketCapitalization
            - SharesOutstanding
            - DividendYield, DividendPerShare
            - PERatio, PEGRatio, BookValue
            - 52WeekHigh, 52WeekLow
            - 50DayMovingAverage, 200DayMovingAverage
            - And many more fields...

        Example:
            >>> client = AlphaVantageClient()
            >>> overview = client.get_company_overview("AAPL")
            >>> print(f"Shares outstanding: {overview.get('SharesOutstanding')}")
        """
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }

        logger.info(f"Fetching company overview for {symbol}")
        data = self._make_request(params)

        return data

    def get_shares_outstanding(self, symbol: str) -> Optional[float]:
        """
        Get shares outstanding for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Shares outstanding (in millions) or None if not available
        """
        try:
            overview = self.get_company_overview(symbol)
            shares = overview.get('SharesOutstanding')

            if shares and shares != 'None':
                # Alpha Vantage returns absolute number, convert to millions
                return float(shares) / 1_000_000
            else:
                logger.warning(f"Shares outstanding not available for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Error fetching shares outstanding for {symbol}: {e}")
            return None

    def calculate_days_to_cover(
        self,
        short_interest: float,
        avg_daily_volume: float
    ) -> Optional[float]:
        """
        Calculate days to cover ratio from short interest and volume.

        Formula: Days to Cover = Short Interest / Average Daily Volume

        Args:
            short_interest: Number of shares sold short (millions)
            avg_daily_volume: Average daily trading volume (millions)

        Returns:
            Days to cover ratio, or None if calculation not possible

        Example:
            >>> days = client.calculate_days_to_cover(
            ...     short_interest=10.5,  # 10.5M shares short
            ...     avg_daily_volume=5.2   # 5.2M daily volume
            ... )
            >>> print(f"Days to cover: {days:.2f}")  # 2.02 days
        """
        if not short_interest or not avg_daily_volume or avg_daily_volume == 0:
            return None

        return short_interest / avg_daily_volume

    def get_short_interest_data(self, symbol: str) -> Dict[str, Any]:
        """
        PLACEHOLDER: Get short interest data for a symbol.

        NOTE: Alpha Vantage does NOT provide short interest data.
        This is a placeholder for future integration with:
        - FINRA (official source, updated bi-monthly)
        - Financial Modeling Prep API
        - Quandl/Nasdaq Data Link
        - Yahoo Finance (via scraping)

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with short interest metrics (mock data for now)
            {
                'symbol': str,
                'short_interest': float,  # shares short (millions)
                'short_pct_float': float,  # % of float
                'days_to_cover': float,
                'as_of_date': str,
                'source': str
            }
        """
        logger.warning(
            f"Short interest data not available via Alpha Vantage for {symbol}. "
            "Returning placeholder. Implement with FINRA/FMP API."
        )

        # TODO: Integrate actual short interest API
        # Options:
        # 1. Financial Modeling Prep: https://financialmodelingprep.com/developer/docs/
        # 2. FINRA API (if available)
        # 3. Yahoo Finance scraping (yfinance library)

        return {
            'symbol': symbol,
            'short_interest': None,
            'short_pct_float': None,
            'days_to_cover': None,
            'as_of_date': None,
            'source': 'not_implemented',
            'error': 'Short interest data requires separate API integration'
        }

    def get_batch_company_overviews(
        self,
        symbols: List[str],
        delay_between: float = 12.5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch company overviews for multiple symbols with rate limiting.

        Args:
            symbols: List of stock ticker symbols
            delay_between: Seconds to wait between requests (default: 12.5 for free tier)

        Returns:
            Dictionary mapping symbol to company overview data

        Example:
            >>> client = AlphaVantageClient()
            >>> symbols = ['AAPL', 'MSFT', 'GOOGL']
            >>> overviews = client.get_batch_company_overviews(symbols)
            >>> for symbol, data in overviews.items():
            ...     print(f"{symbol}: {data.get('MarketCapitalization')}")
        """
        results = {}

        logger.info(f"Fetching batch company overviews for {len(symbols)} symbols")

        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"Processing {symbol} ({i}/{len(symbols)})")
                results[symbol] = self.get_company_overview(symbol)

                # Additional delay between symbols to be safe
                if i < len(symbols):
                    time.sleep(delay_between)

            except Exception as e:
                logger.error(f"Error fetching overview for {symbol}: {e}")
                results[symbol] = {'error': str(e)}

        logger.info(f"Batch fetch complete: {len(results)}/{len(symbols)} successful")
        return results


def example_usage():
    """Example usage of AlphaVantageClient."""
    # Initialize client
    client = AlphaVantageClient()

    # Get company overview
    symbol = "AAPL"
    overview = client.get_company_overview(symbol)

    print(f"\n{symbol} Company Overview:")
    print(f"  Name: {overview.get('Name')}")
    print(f"  Market Cap: ${float(overview.get('MarketCapitalization', 0))/1e9:.2f}B")
    print(f"  Shares Outstanding: {float(overview.get('SharesOutstanding', 0))/1e6:.2f}M")
    print(f"  Dividend Yield: {float(overview.get('DividendYield', 0))*100:.2f}%")
    print(f"  PE Ratio: {overview.get('PERatio')}")
    print(f"  52 Week High: ${overview.get('52WeekHigh')}")
    print(f"  52 Week Low: ${overview.get('52WeekLow')}")

    # Calculate days to cover (example with mock data)
    short_interest = 10.5  # millions of shares
    avg_volume = 50.0  # millions per day
    days_to_cover = client.calculate_days_to_cover(short_interest, avg_volume)
    print(f"\nDays to Cover Calculation:")
    print(f"  Short Interest: {short_interest}M shares")
    print(f"  Avg Daily Volume: {avg_volume}M shares")
    print(f"  Days to Cover: {days_to_cover:.2f} days")


if __name__ == "__main__":
    # Run example if executed directly
    example_usage()
