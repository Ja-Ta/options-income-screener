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


def trend_strength(close: float, sma20: Optional[float], sma50: Optional[float],
                   sma200: Optional[float] = None, rsi: Optional[float] = None,
                   prices: Optional[List[float]] = None) -> float:
    """
    Calculate comprehensive trend strength from -1 (strong downtrend) to +1 (strong uptrend).

    Methodology:
    - Price vs SMAs: Where is price relative to 20/50/200 SMAs? (40% weight)
    - SMA alignment: Are SMAs in bullish (20>50>200) or bearish order? (30% weight)
    - RSI momentum: Is momentum bullish (>50) or bearish (<50)? (20% weight)
    - Recent price action: Short-term trend direction (10% weight)

    Args:
        close: Current close price
        sma20: 20-day SMA
        sma50: 50-day SMA
        sma200: 200-day SMA (optional)
        rsi: Current RSI value (optional)
        prices: Historical price list for momentum calc (optional)

    Returns:
        float: Trend strength score (-1 to 1)
    """
    if close <= 0 or sma20 is None or sma50 is None:
        return 0.0

    components = []

    # Component 1: Price position relative to SMAs (40% weight)
    price_score = 0
    if close > sma20:
        price_score += 0.33
    if close > sma50:
        price_score += 0.33
    if sma200 and close > sma200:
        price_score += 0.34
    elif not sma200:
        price_score += 0.17  # Partial credit if no 200 SMA

    # Convert to -1 to +1 scale
    price_component = (price_score - 0.5) * 2
    components.append(price_component * 0.40)

    # Component 2: SMA alignment (30% weight)
    alignment_score = 0
    if sma20 > sma50:
        alignment_score += 0.5
    if sma200 and sma50 > sma200:
        alignment_score += 0.5
    elif not sma200:
        alignment_score += 0.25  # Partial credit

    alignment_component = (alignment_score - 0.5) * 2
    components.append(alignment_component * 0.30)

    # Component 3: RSI momentum (20% weight)
    if rsi is not None:
        # RSI 50 = neutral, >70 = overbought, <30 = oversold
        rsi_component = (rsi - 50) / 50
        rsi_component = max(-1, min(1, rsi_component))
        components.append(rsi_component * 0.20)
    else:
        # Use SMA difference as proxy
        sma_diff = safe_divide(sma20 - sma50, close, 0.0)
        proxy_component = max(-1, min(1, sma_diff * 10))
        components.append(proxy_component * 0.20)

    # Component 4: Recent price momentum (10% weight)
    if prices and len(prices) >= 10:
        recent_avg = sum(prices[-5:]) / 5
        previous_avg = sum(prices[-10:-5]) / 5
        momentum = safe_divide(recent_avg - previous_avg, previous_avg, 0.0)
        momentum_component = max(-1, min(1, momentum * 10))
        components.append(momentum_component * 0.10)
    else:
        components.append(0 * 0.10)

    # Calculate weighted trend strength
    return sum(components)


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


def calculate_atr(highs: List[float], lows: List[float],
                  closes: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Average True Range (volatility measure).

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of close prices
        period: ATR period (default 14)

    Returns:
        ATR value or None if insufficient data
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None

    # Calculate true range for each period
    true_ranges = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        true_ranges.append(max(high_low, high_close, low_close))

    # Average the last 'period' true ranges
    if len(true_ranges) >= period:
        return sum(true_ranges[-period:]) / period

    return None


def trend_stability(prices: List[float],
                   highs: Optional[List[float]] = None,
                   lows: Optional[List[float]] = None,
                   current_price: Optional[float] = None) -> float:
    """
    Calculate trend stability/consistency from 0 (volatile) to 1 (stable).

    Methodology:
    - Price volatility: Lower volatility = more stable (40% weight)
    - Directional consistency: Consistent direction = stable (30% weight)
    - ATR relative to price: Lower relative ATR = stable (30% weight)

    Args:
        prices: Historical close prices (most recent last)
        highs: Optional historical high prices
        lows: Optional historical low prices
        current_price: Current stock price (uses last price if None)

    Returns:
        Stability score from 0 to 1
    """
    if len(prices) < 20:
        return 0.5  # Default if insufficient data

    if current_price is None:
        current_price = prices[-1]

    components = []

    # Component 1: Price volatility (40% weight)
    # Calculate coefficient of variation (std dev / mean)
    recent_prices = prices[-20:]
    mean_price = sum(recent_prices) / len(recent_prices)
    variance = sum((p - mean_price) ** 2 for p in recent_prices) / len(recent_prices)
    std_dev = variance ** 0.5
    cv = safe_divide(std_dev, mean_price, 0.0)

    # Lower CV = more stable
    # CV > 0.10 = unstable (0), CV < 0.02 = very stable (1)
    volatility_score = max(0, 1 - (cv / 0.10))
    components.append(volatility_score * 0.40)

    # Component 2: Directional consistency (30% weight)
    # Count how many days moved in the dominant direction
    if len(prices) >= 20:
        recent_changes = [prices[i] - prices[i-1] for i in range(-19, 0)]
        up_days = sum(1 for c in recent_changes if c > 0)
        down_days = sum(1 for c in recent_changes if c < 0)

        # High consistency means most days move in same direction
        consistency = abs(up_days - down_days) / len(recent_changes)
        components.append(consistency * 0.30)
    else:
        components.append(0.15)  # Default moderate

    # Component 3: ATR relative to price (30% weight)
    if highs and lows and len(highs) >= 20 and len(lows) >= 20:
        atr = calculate_atr(highs, lows, prices, period=14)
        if atr:
            # ATR as % of price
            atr_pct = safe_divide(atr, current_price, 0.0)
            # Lower ATR% = more stable
            # ATR% > 5% = unstable (0), ATR% < 1% = very stable (1)
            atr_score = max(0, 1 - (atr_pct / 0.05))
            components.append(atr_score * 0.30)
        else:
            components.append(0.15)  # Default moderate
    else:
        # If no ATR data, use return volatility as proxy
        if len(prices) >= 20:
            returns = calculate_returns(prices[-20:])
            if returns:
                ret_vol = calculate_volatility(returns, annualize=False)
                vol_score = max(0, 1 - (ret_vol / 0.05))
                components.append(vol_score * 0.30)
            else:
                components.append(0.15)
        else:
            components.append(0.15)

    # Calculate weighted stability
    return sum(components)


def trend_consistency(prices: List[float], period: int = 20) -> float:
    """
    Measure trend consistency (how smooth the trend is).

    DEPRECATED: Use trend_stability() instead for more comprehensive analysis.

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
    Compute all technical features for a symbol using enhanced calculations.

    Args:
        price_data: Dict with price history and current values
                   Should contain: prices, highs (optional), lows (optional), close

    Returns:
        Dict with all computed technical features
    """
    prices = price_data.get("prices", price_data.get("price_history", []))
    highs = price_data.get("highs", None)
    lows = price_data.get("lows", None)
    close = price_data.get("close", prices[-1] if prices else 0)

    if not prices:
        return {}

    # Compute SMAs
    smas = compute_smas(prices)

    # Compute historical volatilities
    hvs = compute_hvs(prices)

    # Compute RSI
    rsi_value = calculate_rsi(prices)

    # Compute enhanced trend strength (uses RSI and all SMAs)
    trend_str = trend_strength(
        close=close,
        sma20=smas["sma20"],
        sma50=smas["sma50"],
        sma200=smas["sma200"],
        rsi=rsi_value,
        prices=prices
    )

    # Compute enhanced trend stability (uses ATR if available)
    trend_stab = trend_stability(
        prices=prices,
        highs=highs,
        lows=lows,
        current_price=close
    )

    # Compute additional indicators
    features = {
        **smas,
        **hvs,
        "rsi": rsi_value,
        "trend_strength": trend_str,
        "trend_stability": trend_stab,
        "in_uptrend": is_uptrend(smas["sma20"], smas["sma50"], smas["sma200"]),
        "below_200sma": not is_above_support(close, smas["sma200"]),
        "above_support": is_above_support(close, smas["sma200"]),
        "momentum_score": momentum_score(close, smas["sma20"], smas["sma50"]),
        "trend_consistency": trend_consistency(prices)  # Kept for compatibility
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
