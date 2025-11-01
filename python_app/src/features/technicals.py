"""
Technical indicators for the Options Income Screener.

Provides SMA, volatility, and trend calculations.
Python 3.12 compatible following CLAUDE.md standards.
"""

import numpy as np
from typing import List, Optional, Dict, Any
from ..utils.math import safe_divide, calculate_returns, calculate_volatility


def sma(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of prices (most recent last)
        period: Period for SMA calculation

    Returns:
        Optional[float]: SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None

    return sum(prices[-period:]) / period


def compute_smas(prices: List[float]) -> Dict[str, Optional[float]]:
    """
    Compute standard SMA values (20, 50, 200).

    Args:
        prices: List of prices (most recent last)

    Returns:
        Dict with sma20, sma50, sma200 values
    """
    return {
        "sma20": sma(prices, 20),
        "sma50": sma(prices, 50),
        "sma200": sma(prices, 200)
    }


def hist_vol(prices: List[float], period: int, annualize: bool = True) -> Optional[float]:
    """
    Calculate historical volatility from price series.

    Args:
        prices: List of prices (most recent last)
        period: Look-back period for volatility calculation
        annualize: Whether to annualize the volatility

    Returns:
        Optional[float]: Historical volatility or None if insufficient data
    """
    if len(prices) < period + 1:
        return None

    # Get prices for the period
    period_prices = prices[-(period + 1):]

    # Calculate returns
    returns = calculate_returns(period_prices)

    # Calculate volatility
    return calculate_volatility(returns, annualize)


def compute_hvs(prices: List[float]) -> Dict[str, Optional[float]]:
    """
    Compute standard historical volatility values (20, 60 day).

    Args:
        prices: List of prices (most recent last)

    Returns:
        Dict with hv_20, hv_60 values
    """
    return {
        "hv_20": hist_vol(prices, 20),
        "hv_60": hist_vol(prices, 60)
    }


def trend_strength(close: float, sma20: Optional[float], sma50: Optional[float]) -> float:
    """
    Calculate normalized trend strength.

    Args:
        close: Current close price
        sma20: 20-day SMA
        sma50: 50-day SMA

    Returns:
        float: Trend strength score (-1 to 1)
    """
    if close <= 0 or sma20 is None or sma50 is None:
        return 0.0

    # Normalize the SMA difference relative to price
    sma_diff = safe_divide(sma20 - sma50, close, 0.0)

    # Cap at reasonable bounds (-1 to 1)
    return max(-1.0, min(1.0, sma_diff * 10))


def is_uptrend(sma20: Optional[float], sma50: Optional[float], sma200: Optional[float]) -> bool:
    """
    Determine if stock is in an uptrend.

    Args:
        sma20: 20-day SMA
        sma50: 50-day SMA
        sma200: 200-day SMA

    Returns:
        bool: True if in uptrend (20 > 50 > 200)
    """
    if sma20 is None or sma50 is None or sma200 is None:
        return False

    return sma20 > sma50 > sma200


def is_above_support(close: float, sma200: Optional[float]) -> bool:
    """
    Check if price is above major support (200 SMA).

    Args:
        close: Current close price
        sma200: 200-day SMA

    Returns:
        bool: True if above 200 SMA
    """
    if sma200 is None:
        return True  # Assume okay if no data

    return close >= sma200


def momentum_score(close: float, sma20: Optional[float], sma50: Optional[float]) -> float:
    """
    Calculate momentum score based on price vs SMAs.

    Args:
        close: Current close price
        sma20: 20-day SMA
        sma50: 50-day SMA

    Returns:
        float: Momentum score (0 to 1)
    """
    score = 0.0
    count = 0

    if sma20 is not None:
        if close > sma20:
            score += 0.5
        count += 0.5

    if sma50 is not None:
        if close > sma50:
            score += 0.5
        count += 0.5

    if count == 0:
        return 0.5  # Neutral if no data

    return score / count


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index.

    Args:
        prices: List of prices (most recent last)
        period: RSI period (default 14)

    Returns:
        Optional[float]: RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        return None

    # Calculate price changes
    changes = []
    for i in range(1, len(prices)):
        changes.append(prices[i] - prices[i-1])

    # Separate gains and losses
    gains = [max(0, c) for c in changes[-period:]]
    losses = [abs(min(0, c)) for c in changes[-period:]]

    # Calculate average gain and loss
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0  # Max RSI if no losses

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def trend_consistency(prices: List[float], period: int = 20) -> float:
    """
    Measure trend consistency (how smooth the trend is).

    Args:
        prices: List of prices (most recent last)
        period: Look-back period

    Returns:
        float: Consistency score (0 to 1, higher is more consistent)
    """
    if len(prices) < period:
        return 0.5

    recent_prices = prices[-period:]
    returns = calculate_returns(recent_prices)

    if not returns:
        return 0.5

    # Count positive vs negative returns
    positive_returns = sum(1 for r in returns if r > 0)
    consistency = abs(positive_returns - len(returns) / 2) / (len(returns) / 2)

    return min(1.0, consistency)


def compute_technical_features(price_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute all technical features for a symbol.

    Args:
        price_data: Dict with price history and current values

    Returns:
        Dict with all computed technical features
    """
    prices = price_data.get("price_history", [])
    close = price_data.get("close", 0)

    # Compute SMAs
    smas = compute_smas(prices)

    # Compute historical volatilities
    hvs = compute_hvs(prices)

    # Compute additional indicators
    features = {
        **smas,
        **hvs,
        "trend_strength": trend_strength(close, smas["sma20"], smas["sma50"]),
        "is_uptrend": is_uptrend(smas["sma20"], smas["sma50"], smas["sma200"]),
        "above_support": is_above_support(close, smas["sma200"]),
        "momentum_score": momentum_score(close, smas["sma20"], smas["sma50"]),
        "rsi": calculate_rsi(prices),
        "trend_consistency": trend_consistency(prices)
    }

    return features

# Alias for compatibility with different naming conventions
def calculate_technical_indicators(prices: List[float]) -> Dict[str, Any]:
    """
    Calculate technical indicators from price list.
    
    Alias for compute_technical_features for backward compatibility.
    """
    # Create a minimal price_data dict from the prices list
    if not prices:
        return {}
    
    price_data = {
        "close": prices[-1] if prices else None,
        "prices": prices
    }
    
    # Compute all technical features
    features = compute_technical_features(price_data)
    
    # Also compute SMAs and HVs directly from prices
    smas = compute_smas(prices)
    hvs = compute_hvs(prices)
    
    # Merge all results
    features.update(smas)
    features.update(hvs)
    
    return features
