"""
Polygon API client with mock data support for testing.

Provides market data and option chains for screening.
Python 3.12 compatible following CLAUDE.md standards.
"""

import csv
import random
import requests
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..constants import USE_MOCK_DATA, CC_DTE_RANGE, CSP_DTE_RANGE
from ..utils.dates import get_expiry_candidates, calculate_dte
from ..utils.logging import get_logger, log_api_call


class PolygonClient:
    """
    Client for Polygon.io API with mock data fallback.

    In mock mode, generates realistic test data for development.
    In production mode, would make actual API calls to Polygon.
    """

    def __init__(self, api_key: str):
        """
        Initialize Polygon client.

        Args:
            api_key: Polygon API key (ignored in mock mode)
        """
        self.api_key = api_key
        self.logger = get_logger("screener.api")
        self.use_mock = USE_MOCK_DATA or api_key.startswith("mock_")

        if self.use_mock:
            self.logger.info("Polygon client initialized in MOCK mode")
        else:
            self.logger.info("Polygon client initialized in PRODUCTION mode")
            self.session = requests.Session()
            # Add retry logic here in production

    def get_universe(self) -> List[str]:
        """
        Load universe of symbols from CSV file.

        Returns:
            List[str]: List of symbols to screen
        """
        universe_file = Path("python_app/src/data/universe.csv")
        symbols = []

        try:
            with open(universe_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbols.append(row['symbol'])

            self.logger.info(f"Loaded {len(symbols)} symbols from universe")
            return symbols

        except Exception as e:
            self.logger.error(f"Failed to load universe: {e}")
            # Return default symbols as fallback
            return ["AAPL", "MSFT", "SPY"]

    def get_daily_prices(self, symbols: List[str], asof: date) -> Dict[str, Dict[str, Any]]:
        """
        Fetch daily price data for symbols.

        Args:
            symbols: List of symbols
            asof: As-of date for prices

        Returns:
            Dict mapping symbol to price data including close, volume, SMAs
        """
        log_api_call("Polygon", "daily_prices", {"symbols": len(symbols), "date": str(asof)})

        if self.use_mock:
            return self._mock_daily_prices(symbols, asof)

        # Production implementation would call Polygon API here
        raise NotImplementedError("Production Polygon API not yet implemented")

    def get_option_chain(self, symbol: str, asof: date) -> List[Dict[str, Any]]:
        """
        Fetch option chain for a symbol.

        Args:
            symbol: Stock symbol
            asof: As-of date for chain

        Returns:
            List of option contracts with greeks and pricing
        """
        log_api_call("Polygon", "option_chain", {"symbol": symbol, "date": str(asof)})

        if self.use_mock:
            return self._mock_option_chain(symbol, asof)

        # Production implementation would call Polygon API here
        raise NotImplementedError("Production Polygon API not yet implemented")

    def get_earnings(self, symbol: str) -> Optional[date]:
        """
        Get earnings date for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Optional[date]: Earnings date if available
        """
        log_api_call("Polygon", "earnings", {"symbol": symbol})

        if self.use_mock:
            # Mock: random earnings date 15-60 days out for 50% of symbols
            if random.random() < 0.5:
                days_ahead = random.randint(15, 60)
                return date.today() + timedelta(days=days_ahead)
            return None

        # Production implementation would call Polygon API here
        raise NotImplementedError("Production Polygon API not yet implemented")

    def _mock_daily_prices(self, symbols: List[str], asof: date) -> Dict[str, Dict[str, Any]]:
        """
        Generate mock daily price data.

        Args:
            symbols: List of symbols
            asof: As-of date

        Returns:
            Mock price data
        """
        prices = {}

        # Base prices for known symbols
        base_prices = {
            "AAPL": 180.0,
            "MSFT": 420.0,
            "SPY": 560.0,
            "QQQ": 485.0,
            "NVDA": 140.0
        }

        for symbol in symbols:
            # Get base price or generate random
            base = base_prices.get(symbol, random.uniform(50, 500))

            # Add some randomness
            close = base * random.uniform(0.95, 1.05)

            # Generate price history for SMA calculations
            price_history = []
            current_price = close
            for i in range(200):
                # Random walk backwards
                daily_change = random.uniform(-0.02, 0.02)
                current_price = current_price * (1 - daily_change)
                price_history.insert(0, current_price)

            # Calculate SMAs
            sma20 = sum(price_history[-20:]) / 20
            sma50 = sum(price_history[-50:]) / 50
            sma200 = sum(price_history[-200:]) / 200

            # Calculate historical volatility
            returns = [(price_history[i] - price_history[i-1]) / price_history[i-1]
                      for i in range(1, len(price_history))]

            hv_20 = self._calculate_hv(returns[-20:])
            hv_60 = self._calculate_hv(returns[-60:])

            prices[symbol] = {
                "symbol": symbol,
                "asof": asof,
                "close": round(close, 2),
                "volume": random.randint(1000000, 50000000),
                "sma20": round(sma20, 2),
                "sma50": round(sma50, 2),
                "sma200": round(sma200, 2),
                "hv_20": round(hv_20, 4),
                "hv_60": round(hv_60, 4),
                "price_history": price_history  # For IV calculations
            }

        return prices

    def _mock_option_chain(self, symbol: str, asof: date) -> List[Dict[str, Any]]:
        """
        Generate mock option chain data.

        Args:
            symbol: Stock symbol
            asof: As-of date

        Returns:
            Mock option chain
        """
        chain = []

        # Get mock stock price (would normally come from prices data)
        base_prices = {"AAPL": 180.0, "MSFT": 420.0, "SPY": 560.0, "QQQ": 485.0, "NVDA": 140.0}
        stock_price = base_prices.get(symbol, 100.0)

        # Get expiry dates in DTE range
        expiries = get_expiry_candidates(asof, (25, 50))

        for expiry in expiries:
            dte = calculate_dte(expiry, asof)

            # Generate strikes around current price
            strike_increment = 1.0 if stock_price < 100 else 5.0
            num_strikes = 10  # 5 above, 5 below

            for i in range(-5, 6):
                strike = round(stock_price + (i * strike_increment), 0)

                # Generate calls
                call_delta = self._calculate_mock_delta("call", stock_price, strike, dte)
                call_iv = random.uniform(0.15, 0.45)  # 15-45% IV
                call_premium = self._calculate_mock_premium("call", stock_price, strike, call_iv, dte)

                chain.append({
                    "symbol": symbol,
                    "asof": asof,
                    "expiry": expiry,
                    "side": "call",
                    "strike": strike,
                    "bid": round(call_premium * 0.98, 2),
                    "ask": round(call_premium * 1.02, 2),
                    "mid": round(call_premium, 2),
                    "delta": round(call_delta, 3),
                    "iv": round(call_iv, 4),
                    "oi": random.randint(100, 5000),
                    "vol": random.randint(50, 2000),
                    "dte": dte
                })

                # Generate puts
                put_delta = self._calculate_mock_delta("put", stock_price, strike, dte)
                put_iv = random.uniform(0.20, 0.50)  # Slightly higher IV for puts
                put_premium = self._calculate_mock_premium("put", stock_price, strike, put_iv, dte)

                chain.append({
                    "symbol": symbol,
                    "asof": asof,
                    "expiry": expiry,
                    "side": "put",
                    "strike": strike,
                    "bid": round(put_premium * 0.98, 2),
                    "ask": round(put_premium * 1.02, 2),
                    "mid": round(put_premium, 2),
                    "delta": round(put_delta, 3),
                    "iv": round(put_iv, 4),
                    "oi": random.randint(100, 5000),
                    "vol": random.randint(50, 2000),
                    "dte": dte
                })

        return chain

    def _calculate_hv(self, returns: List[float]) -> float:
        """Calculate annualized historical volatility."""
        import numpy as np
        if not returns:
            return 0.25  # Default 25% volatility
        std = np.std(returns)
        return std * np.sqrt(252)  # Annualize

    def _calculate_mock_delta(self, side: str, spot: float, strike: float, dte: int) -> float:
        """Calculate approximate delta for mock options."""
        moneyness = (spot - strike) / spot
        time_factor = dte / 365.0

        if side == "call":
            # Rough approximation of call delta
            if moneyness > 0.1:  # ITM
                delta = 0.5 + min(0.45, moneyness * 2)
            elif moneyness < -0.1:  # OTM
                delta = 0.5 + max(-0.45, moneyness * 2)
            else:  # ATM
                delta = 0.5 + moneyness

            # Adjust for time
            delta = delta * (1 - 0.1 * (1 - time_factor))
            return max(0.01, min(0.99, delta))

        else:  # put
            # Rough approximation of put delta
            if strike > spot * 1.1:  # Deep ITM
                delta = -0.9 + min(0.4, moneyness)
            elif strike < spot * 0.9:  # Deep OTM
                delta = -0.1 + max(-0.4, moneyness)
            else:  # Near ATM
                delta = -0.5 + moneyness

            # Adjust for time
            delta = delta * (1 - 0.1 * (1 - time_factor))
            return max(-0.99, min(-0.01, delta))

    def _calculate_mock_premium(self, side: str, spot: float, strike: float, iv: float, dte: int) -> float:
        """Calculate approximate option premium for mock data."""
        time_value = (dte / 365.0) ** 0.5
        vol_component = spot * iv * time_value * 0.4  # Simplified Black-Scholes approximation

        if side == "call":
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)

        # Add time value based on how close to ATM
        moneyness = abs(spot - strike) / spot
        atm_premium = vol_component * (1 - moneyness * 2)

        premium = intrinsic + max(0.01, atm_premium)
        return round(premium, 2)