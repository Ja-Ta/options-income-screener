#!/usr/bin/env python3
"""
Real options data fetcher using Massive.com Options API (formerly Polygon.io).
Uses proper options endpoints for Options Advanced account.
"""

import os
import time
import requests
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealOptionsFetcher:
    """Fetches real options data from Massive.com Options API (formerly Polygon.io)."""

    def __init__(self, api_key: str):
        """Initialize with Massive API key (Polygon API keys still work)."""
        self.api_key = api_key
        self.base_url = "https://api.massive.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}'
        })

    def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price using previous day's close."""
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
        params = {"apiKey": self.api_key}

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Stock API call for {symbol}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    price = data['results'][0]['c']  # Close price
                    logger.info(f"{symbol} stock price: ${price:.2f}")
                    return price
            else:
                logger.error(f"Stock price error for {symbol}: {response.text}")
        except Exception as e:
            logger.error(f"Error fetching stock price for {symbol}: {e}")

        return None

    def get_historical_prices(self, symbol: str, days: int = 250) -> Optional[Dict]:
        """
        Get historical OHLC price data for a symbol.
        Uses /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to} endpoint.

        Args:
            symbol: Stock symbol
            days: Number of calendar days to fetch (default 250 to ensure 200+ trading days)

        Returns:
            Dict with lists of close, high, low prices (most recent last), or None if error
        """
        # Calculate date range
        to_date = date.today() - timedelta(days=1)  # Yesterday
        from_date = to_date - timedelta(days=days)

        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{from_date.isoformat()}/{to_date.isoformat()}"
        params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc", "limit": 5000}

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Historical prices API call for {symbol}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    results = data['results']

                    # Extract OHLC arrays
                    closes = [bar['c'] for bar in results]
                    highs = [bar['h'] for bar in results]
                    lows = [bar['l'] for bar in results]
                    volumes = [bar['v'] for bar in results]

                    logger.info(f"{symbol} historical data: {len(closes)} bars fetched")

                    return {
                        'symbol': symbol,
                        'prices': closes,  # Close prices
                        'highs': highs,
                        'lows': lows,
                        'volumes': volumes,
                        'bars': len(closes)
                    }
                else:
                    logger.warning(f"No historical data found for {symbol}")
            else:
                logger.error(f"Historical prices error for {symbol}: {response.text}")
        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {e}")

        return None

    def list_options_contracts(self, symbol: str, contract_type: str = "call",
                              expiry_gte: str = None, expiry_lte: str = None,
                              strike_gte: float = None, strike_lte: float = None) -> List[Dict]:
        """
        List options contracts for a symbol.
        Uses /v3/reference/options/contracts endpoint.
        """
        url = f"{self.base_url}/v3/reference/options/contracts"

        params = {
            "underlying_ticker": symbol,
            "contract_type": contract_type,
            "expired": "false",
            "limit": 250,
            "apiKey": self.api_key
        }

        # Add date filters
        if expiry_gte:
            params["expiration_date.gte"] = expiry_gte
        if expiry_lte:
            params["expiration_date.lte"] = expiry_lte

        # Add strike filters
        if strike_gte:
            params["strike_price.gte"] = strike_gte
        if strike_lte:
            params["strike_price.lte"] = strike_lte

        contracts = []

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Options contracts API call for {symbol} {contract_type}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    contracts = data['results']
                    logger.info(f"Found {len(contracts)} {contract_type} contracts for {symbol}")
                else:
                    logger.warning(f"No contracts found for {symbol} {contract_type}")
            else:
                logger.error(f"Options contracts error: {response.text}")

        except Exception as e:
            logger.error(f"Error listing options contracts: {e}")

        return contracts

    def get_option_quote(self, option_ticker: str) -> Optional[Dict]:
        """
        Get quote for a specific option contract.
        Uses /v3/quotes/{optionsTicker} endpoint.
        """
        url = f"{self.base_url}/v3/quotes/{option_ticker}"
        params = {"apiKey": self.api_key}

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Option quote API call for {option_ticker}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    quote = data['results'][0]
                    logger.info(f"{option_ticker} - Bid: ${quote.get('bid', 0):.2f}, Ask: ${quote.get('ask', 0):.2f}")
                    return quote
            else:
                logger.error(f"Option quote error: {response.text}")

        except Exception as e:
            logger.error(f"Error getting option quote: {e}")

        return None

    def estimate_option_price(self, stock_price: float, strike: float,
                            iv: float, dte: int, option_type: str) -> float:
        """
        Estimate option price using Black-Scholes approximation.
        Useful when market is closed and bid/ask are 0.
        """
        try:
            import math

            # Simple approximation based on moneyness and IV
            moneyness = abs(stock_price - strike) / stock_price
            time_factor = math.sqrt(dte / 365)

            # Base premium calculation
            if option_type == "call":
                intrinsic = max(0, stock_price - strike)
            else:
                intrinsic = max(0, strike - stock_price)

            # Time value approximation
            time_value = stock_price * iv * time_factor * 0.4

            # Adjust for moneyness
            if moneyness < 0.02:  # ATM
                premium = intrinsic + time_value
            elif moneyness < 0.05:  # Slightly OTM
                premium = intrinsic + time_value * 0.7
            else:  # Further OTM
                premium = intrinsic + time_value * 0.4

            return max(0.01, premium)

        except Exception as e:
            logger.error(f"Error estimating price: {e}")
            return 0.01

    def get_option_snapshot(self, underlying: str, option_ticker: str) -> Optional[Dict]:
        """
        Get option snapshot with Greeks and IV.
        Uses /v3/snapshot/options/{underlyingAsset}/{optionContract} endpoint.
        """
        url = f"{self.base_url}/v3/snapshot/options/{underlying}/{option_ticker}"
        params = {"apiKey": self.api_key}

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Option snapshot API call for {option_ticker}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    snapshot = data['results']

                    # Log Greeks if available
                    if 'greeks' in snapshot:
                        greeks = snapshot['greeks']
                        logger.info(f"{option_ticker} Greeks - Delta: {greeks.get('delta')}, IV: {snapshot.get('implied_volatility')}")

                    return snapshot
            else:
                logger.error(f"Option snapshot error: {response.text}")

        except Exception as e:
            logger.error(f"Error getting option snapshot: {e}")

        return None

    def find_covered_call_candidates(self, symbol: str, stock_price: float,
                                    days_to_expiry_min: int = 30,
                                    days_to_expiry_max: int = 45) -> List[Dict]:
        """Find suitable covered call candidates."""
        today = date.today()
        expiry_min = today + timedelta(days=days_to_expiry_min)
        expiry_max = today + timedelta(days=days_to_expiry_max)

        # Look for OTM calls (2-5% above current price)
        strike_min = stock_price * 1.02
        strike_max = stock_price * 1.05

        # List contracts
        contracts = self.list_options_contracts(
            symbol=symbol,
            contract_type="call",
            expiry_gte=expiry_min.isoformat(),
            expiry_lte=expiry_max.isoformat(),
            strike_gte=strike_min,
            strike_lte=strike_max
        )

        candidates = []

        # Process up to 20 contracts (no rate limiting needed with Options Advanced)
        for contract in contracts[:20]:
            ticker = contract['ticker']

            # Get quote
            quote = self.get_option_quote(ticker)
            if not quote:
                continue

            # Get snapshot for Greeks and IV
            snapshot = self.get_option_snapshot(symbol, ticker)

            # Calculate metrics
            bid = quote.get('bid', 0)
            ask = quote.get('ask', 0)
            mid = (bid + ask) / 2 if bid and ask else 0

            # If market is closed (bid/ask are 0), estimate price
            if mid == 0 and snapshot and 'implied_volatility' in snapshot:
                strike = contract['strike_price']
                expiry = contract['expiration_date']
                dte = (datetime.strptime(expiry, '%Y-%m-%d').date() - today).days
                iv = snapshot.get('implied_volatility', 0.25)

                # Estimate price using Black-Scholes approximation
                mid = self.estimate_option_price(stock_price, strike, iv, dte, "call")
                logger.info(f"Estimated price for {ticker}: ${mid:.2f} (IV: {iv:.2%})")

            if mid > 0:
                strike = contract['strike_price']
                expiry = contract['expiration_date']
                dte = (datetime.strptime(expiry, '%Y-%m-%d').date() - today).days

                roi_30d = (mid / stock_price) * (30 / dte) if dte > 0 else 0
                annualized = roi_30d * 12

                candidate = {
                    'symbol': symbol,
                    'ticker': ticker,
                    'strike': strike,
                    'expiry': expiry,
                    'dte': dte,
                    'bid': bid,
                    'ask': ask,
                    'mid': mid,
                    'stock_price': stock_price,
                    'roi_30d': roi_30d,
                    'annualized_return': annualized,
                    'moneyness': (strike - stock_price) / stock_price
                }

                # Add Greeks if available
                if snapshot and 'greeks' in snapshot:
                    candidate['delta'] = snapshot['greeks'].get('delta')
                    candidate['theta'] = snapshot['greeks'].get('theta')
                    candidate['gamma'] = snapshot['greeks'].get('gamma')
                    candidate['vega'] = snapshot['greeks'].get('vega')
                    candidate['iv'] = snapshot.get('implied_volatility')

                candidates.append(candidate)

        return candidates

    def get_earnings_date(self, symbol: str) -> Optional[Dict]:
        """
        Get next earnings date for a symbol using Massive.com Benzinga Earnings API.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with earnings info: {
                'symbol': str,
                'date': str (YYYY-MM-DD),
                'date_status': str ('confirmed' or 'projected'),
                'fiscal_period': str (e.g., 'Q1', 'Q2'),
                'fiscal_year': int,
                'estimated_eps': float (optional),
                'days_until': int (days from today)
            }
            Returns None if no earnings found or API error
        """
        today = date.today()
        # Look ahead 90 days for next earnings
        to_date = today + timedelta(days=90)

        url = f"{self.base_url}/benzinga/v1/earnings"
        params = {
            "ticker": symbol,
            "date.gte": today.isoformat(),
            "date.lte": to_date.isoformat(),
            "limit": 1,
            "order": "asc",
            "sort": "date",
            "apiKey": self.api_key
        }

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Earnings API call for {symbol}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    earnings = data['results'][0]
                    earnings_date = earnings.get('date')

                    if earnings_date:
                        # Parse earnings date
                        earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                        days_until = (earnings_dt - today).days

                        result = {
                            'symbol': symbol,
                            'date': earnings_date,
                            'date_status': earnings.get('date_status', 'unknown'),
                            'fiscal_period': earnings.get('fiscal_period', 'N/A'),
                            'fiscal_year': earnings.get('fiscal_year'),
                            'estimated_eps': earnings.get('estimated_eps'),
                            'days_until': days_until
                        }

                        logger.info(f"{symbol} next earnings: {earnings_date} ({days_until} days, {result['date_status']})")
                        return result
                else:
                    logger.info(f"No upcoming earnings found for {symbol} in next 90 days")
            else:
                logger.warning(f"Earnings API error for {symbol}: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error fetching earnings for {symbol}: {e}")

        return None

    def get_dividend_yield(self, symbol: str, stock_price: float) -> Optional[Dict]:
        """
        Get dividend yield for a symbol using Massive.com Dividends API.

        Args:
            symbol: Stock symbol
            stock_price: Current stock price (for yield calculation)

        Returns:
            Dict with dividend info: {
                'symbol': str,
                'annual_dividend': float,
                'dividend_yield': float (as decimal, e.g., 0.0447 for 4.47%),
                'cash_amount': float,
                'frequency': int (4=quarterly, 12=monthly, etc.),
                'ex_dividend_date': str (YYYY-MM-DD),
                'pay_date': str (YYYY-MM-DD),
                'dividend_type': str
            }
            Returns None if no dividend data or API error
        """
        url = f"{self.base_url}/v3/reference/dividends"
        params = {
            "ticker": symbol,
            "limit": 1,
            "apiKey": self.api_key
        }

        try:
            response = self.session.get(url, params=params)
            logger.info(f"Dividend API call for {symbol}: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    dividend = data['results'][0]

                    cash_amount = dividend.get('cash_amount', 0)
                    frequency = dividend.get('frequency', 0)

                    # Calculate annual dividend
                    annual_dividend = cash_amount * frequency

                    # Calculate yield
                    dividend_yield = (annual_dividend / stock_price) if stock_price > 0 else 0

                    result = {
                        'symbol': symbol,
                        'annual_dividend': annual_dividend,
                        'dividend_yield': dividend_yield,
                        'cash_amount': cash_amount,
                        'frequency': frequency,
                        'ex_dividend_date': dividend.get('ex_dividend_date'),
                        'pay_date': dividend.get('pay_date'),
                        'dividend_type': dividend.get('dividend_type')
                    }

                    logger.info(f"{symbol} dividend: ${annual_dividend:.2f}/yr ({dividend_yield*100:.2f}% yield, {frequency}x/yr)")
                    return result
                else:
                    logger.info(f"No dividend data found for {symbol}")
            else:
                logger.warning(f"Dividend API error for {symbol}: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error fetching dividend for {symbol}: {e}")

        return None

    def find_cash_secured_put_candidates(self, symbol: str, stock_price: float,
                                        days_to_expiry_min: int = 30,
                                        days_to_expiry_max: int = 45) -> List[Dict]:
        """Find suitable cash-secured put candidates."""
        today = date.today()
        expiry_min = today + timedelta(days=days_to_expiry_min)
        expiry_max = today + timedelta(days=days_to_expiry_max)

        # Look for OTM puts (2-5% below current price)
        strike_min = stock_price * 0.95
        strike_max = stock_price * 0.98

        # List contracts
        contracts = self.list_options_contracts(
            symbol=symbol,
            contract_type="put",
            expiry_gte=expiry_min.isoformat(),
            expiry_lte=expiry_max.isoformat(),
            strike_gte=strike_min,
            strike_lte=strike_max
        )

        candidates = []

        # Process up to 20 contracts (no rate limiting needed with Options Advanced)
        for contract in contracts[:20]:
            ticker = contract['ticker']

            # Get quote
            quote = self.get_option_quote(ticker)
            if not quote:
                continue

            # Get snapshot for Greeks and IV
            snapshot = self.get_option_snapshot(symbol, ticker)

            # Calculate metrics
            bid = quote.get('bid', 0)
            ask = quote.get('ask', 0)
            mid = (bid + ask) / 2 if bid and ask else 0

            # If market is closed (bid/ask are 0), estimate price
            if mid == 0 and snapshot and 'implied_volatility' in snapshot:
                strike = contract['strike_price']
                expiry = contract['expiration_date']
                dte = (datetime.strptime(expiry, '%Y-%m-%d').date() - today).days
                iv = snapshot.get('implied_volatility', 0.25)

                # Estimate price using Black-Scholes approximation
                mid = self.estimate_option_price(stock_price, strike, iv, dte, "put")
                logger.info(f"Estimated price for {ticker}: ${mid:.2f} (IV: {iv:.2%})")

            if mid > 0:
                strike = contract['strike_price']
                expiry = contract['expiration_date']
                dte = (datetime.strptime(expiry, '%Y-%m-%d').date() - today).days

                roi_30d = (mid / strike) * (30 / dte) if dte > 0 else 0
                annualized = roi_30d * 12

                candidate = {
                    'symbol': symbol,
                    'ticker': ticker,
                    'strike': strike,
                    'expiry': expiry,
                    'dte': dte,
                    'bid': bid,
                    'ask': ask,
                    'mid': mid,
                    'stock_price': stock_price,
                    'roi_30d': roi_30d,
                    'annualized_return': annualized,
                    'moneyness': (stock_price - strike) / stock_price
                }

                # Add Greeks if available
                if snapshot and 'greeks' in snapshot:
                    candidate['delta'] = snapshot['greeks'].get('delta')
                    candidate['theta'] = snapshot['greeks'].get('theta')
                    candidate['gamma'] = snapshot['greeks'].get('gamma')
                    candidate['vega'] = snapshot['greeks'].get('vega')
                    candidate['iv'] = snapshot.get('implied_volatility')

                candidates.append(candidate)

        return candidates


def test_earnings():
    """Test earnings data fetching."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.error("No POLYGON_API_KEY found (Massive.com API key)")
        return

    fetcher = RealOptionsFetcher(api_key)

    # Test with multiple symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'SPY', 'NVDA']

    logger.info(f"\n{'='*60}")
    logger.info("Testing Earnings Data Fetching")
    logger.info(f"{'='*60}\n")

    for symbol in test_symbols:
        earnings = fetcher.get_earnings_date(symbol)
        if earnings:
            logger.info(f"✅ {symbol}:")
            logger.info(f"   Date: {earnings['date']} ({earnings['days_until']} days)")
            logger.info(f"   Status: {earnings['date_status']}")
            logger.info(f"   Period: {earnings['fiscal_period']} {earnings['fiscal_year']}")
            if earnings.get('estimated_eps'):
                logger.info(f"   Est. EPS: ${earnings['estimated_eps']:.2f}")
        else:
            logger.warning(f"❌ {symbol}: No earnings data found")
        logger.info("")

    logger.info(f"{'='*60}")
    logger.info("✅ Earnings test complete!")
    logger.info(f"{'='*60}\n")


def test_dividends():
    """Test dividend data fetching."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.error("No POLYGON_API_KEY found (Massive.com API key)")
        return

    fetcher = RealOptionsFetcher(api_key)

    # Test with multiple symbols including high-dividend stocks
    test_symbols = ['AAPL', 'T', 'KO', 'PFE', 'INTC', 'SPY']

    logger.info(f"\n{'='*60}")
    logger.info("Testing Dividend Data Fetching")
    logger.info(f"{'='*60}\n")

    for symbol in test_symbols:
        # Get stock price first
        stock_price = fetcher.get_stock_price(symbol)
        if not stock_price:
            logger.warning(f"❌ {symbol}: Could not get stock price")
            continue

        # Get dividend data
        dividend = fetcher.get_dividend_yield(symbol, stock_price)
        if dividend:
            logger.info(f"✅ {symbol}:")
            logger.info(f"   Stock Price: ${stock_price:.2f}")
            logger.info(f"   Dividend: ${dividend['cash_amount']:.3f} x {dividend['frequency']}/yr = ${dividend['annual_dividend']:.2f}/yr")
            logger.info(f"   Yield: {dividend['dividend_yield']*100:.2f}%")
            logger.info(f"   Ex-Date: {dividend['ex_dividend_date']}")
            logger.info(f"   Type: {dividend['dividend_type']}")
        else:
            logger.info(f"ℹ️  {symbol}: No dividend (likely non-dividend paying stock)")
        logger.info("")

    logger.info(f"{'='*60}")
    logger.info("✅ Dividend test complete!")
    logger.info(f"{'='*60}\n")


def test_real_options():
    """Test real options fetching."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.error("No POLYGON_API_KEY found (Massive.com API key)")
        return

    fetcher = RealOptionsFetcher(api_key)

    # Test with SPY
    symbol = 'SPY'
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing real options data for {symbol}")
    logger.info(f"{'='*60}\n")

    # Get stock price
    stock_price = fetcher.get_stock_price(symbol)
    if not stock_price:
        logger.error(f"Could not get stock price for {symbol}")
        return

    logger.info(f"\n📊 {symbol} Stock Price: ${stock_price:.2f}\n")

    # Find covered calls
    logger.info("🔍 Finding Covered Call candidates...")
    cc_candidates = fetcher.find_covered_call_candidates(symbol, stock_price)

    if cc_candidates:
        logger.info(f"\n📈 Top Covered Calls for {symbol}:")
        for i, cc in enumerate(cc_candidates[:3], 1):
            logger.info(f"{i}. Strike: ${cc['strike']:.2f}, Expiry: {cc['expiry']}")
            logger.info(f"   Premium: ${cc['mid']:.2f} (Bid: ${cc['bid']:.2f}, Ask: ${cc['ask']:.2f})")
            logger.info(f"   ROI (30d): {cc['roi_30d']:.2%}, Annual: {cc['annualized_return']:.1%}")
            if cc.get('iv'):
                logger.info(f"   IV: {cc['iv']:.2%}, Delta: {cc.get('delta', 'N/A')}")
            logger.info("")

    # Find cash-secured puts
    logger.info("🔍 Finding Cash-Secured Put candidates...")
    csp_candidates = fetcher.find_cash_secured_put_candidates(symbol, stock_price)

    if csp_candidates:
        logger.info(f"\n💰 Top Cash-Secured Puts for {symbol}:")
        for i, csp in enumerate(csp_candidates[:3], 1):
            logger.info(f"{i}. Strike: ${csp['strike']:.2f}, Expiry: {csp['expiry']}")
            logger.info(f"   Premium: ${csp['mid']:.2f} (Bid: ${csp['bid']:.2f}, Ask: ${csp['ask']:.2f})")
            logger.info(f"   ROI (30d): {csp['roi_30d']:.2%}, Annual: {csp['annualized_return']:.1%}")
            if csp.get('iv'):
                logger.info(f"   IV: {csp['iv']:.2%}, Delta: {csp.get('delta', 'N/A')}")
            logger.info("")

    logger.info(f"\n{'='*60}")
    logger.info("✅ Real options test complete!")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test-earnings':
        test_earnings()
    elif len(sys.argv) > 1 and sys.argv[1] == '--test-dividends':
        test_dividends()
    else:
        test_real_options()