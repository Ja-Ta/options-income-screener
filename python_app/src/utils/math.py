"""
Mathematical utilities for the Options Income Screener.

Provides statistical and financial calculations.
Python 3.12 compatible following CLAUDE.md standards.
"""

import numpy as np
from typing import List, Optional, Tuple


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Perform safe division with zero handling.

    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if denominator is zero

    Returns:
        float: Result of division or default value
    """
    if denominator == 0 or denominator is None:
        return default
    return numerator / denominator


def zscore(value: float, mean: float, std: float) -> float:
    """
    Calculate z-score for normalization.

    Args:
        value: Value to normalize
        mean: Mean of the distribution
        std: Standard deviation of the distribution

    Returns:
        float: Z-score (0 if std is 0)
    """
    if std == 0:
        return 0.0
    return (value - mean) / std


def percentile_rank(value: float, series: List[float]) -> float:
    """
    Calculate percentile rank of a value in a series.

    Args:
        value: Value to rank
        series: List of values for comparison

    Returns:
        float: Percentile rank (0-100)
    """
    if not series:
        return 50.0

    sorted_series = sorted(series)
    count_below = sum(1 for v in sorted_series if v < value)
    count_equal = sum(1 for v in sorted_series if v == value)

    percentile = (count_below + 0.5 * count_equal) / len(series) * 100
    return min(100.0, max(0.0, percentile))


def calculate_returns(prices: List[float]) -> List[float]:
    """
    Calculate daily returns from price series.

    Args:
        prices: List of prices

    Returns:
        List[float]: Daily returns (percentage)
    """
    if len(prices) < 2:
        return []

    returns = []
    for i in range(1, len(prices)):
        ret = safe_divide(prices[i] - prices[i-1], prices[i-1], 0.0)
        returns.append(ret)

    return returns


def calculate_volatility(returns: List[float], annualize: bool = True) -> float:
    """
    Calculate historical volatility from returns.

    Args:
        returns: List of returns (as decimals, not percentages)
        annualize: Whether to annualize the volatility

    Returns:
        float: Volatility (annualized if requested)
    """
    if not returns:
        return 0.0

    std_dev = np.std(returns)

    if annualize:
        # Assuming 252 trading days per year
        return std_dev * np.sqrt(252)

    return std_dev


def calculate_roi(premium: float, capital: float, days: int = 30) -> float:
    """
    Calculate return on investment.

    Args:
        premium: Option premium collected
        capital: Capital at risk (stock price for CC, strike for CSP)
        days: Holding period in days

    Returns:
        float: ROI as decimal (e.g., 0.015 for 1.5%)
    """
    return safe_divide(premium, capital, 0.0)


def annualize_return(period_return: float, days: int) -> float:
    """
    Annualize a period return.

    Args:
        period_return: Return for the period (as decimal)
        days: Number of days in the period

    Returns:
        float: Annualized return (as decimal)
    """
    if days <= 0:
        return 0.0

    # Simple annualization: (1 + period_return)^(365/days) - 1
    # For small returns, approximation: period_return * (365/days)
    return period_return * (365.0 / days)


def calculate_spread_percentage(bid: float, ask: float) -> float:
    """
    Calculate bid-ask spread as percentage of mid price.

    Args:
        bid: Bid price
        ask: Ask price

    Returns:
        float: Spread percentage (e.g., 0.05 for 5%)
    """
    if bid <= 0 or ask <= 0:
        return 1.0  # Return high spread to filter out

    mid = (bid + ask) / 2
    spread = ask - bid

    return safe_divide(spread, mid, 1.0)


def calculate_margin_of_safety(spot: float, strike: float) -> float:
    """
    Calculate margin of safety for put options.

    Args:
        spot: Current stock price
        strike: Strike price of put option

    Returns:
        float: Margin of safety as decimal (e.g., 0.1 for 10% OTM)
    """
    return safe_divide(spot - strike, spot, 0.0)


def trend_strength(close: float, sma20: float, sma50: float) -> float:
    """
    Calculate normalized trend strength.

    Args:
        close: Current close price
        sma20: 20-day simple moving average
        sma50: 50-day simple moving average

    Returns:
        float: Trend strength score (-1 to 1)
    """
    if close <= 0:
        return 0.0

    # Normalize the SMA difference relative to price
    sma_diff = safe_divide(sma20 - sma50, close, 0.0)

    # Cap at reasonable bounds
    return max(-1.0, min(1.0, sma_diff * 10))


def calculate_trend_stability(returns: List[float], window: int = 20) -> float:
    """
    Calculate trend stability based on return consistency.

    Args:
        returns: List of daily returns
        window: Look-back window for calculation

    Returns:
        float: Stability score (0 to 1, higher is more stable)
    """
    if not returns or len(returns) < window:
        return 0.5

    recent_returns = returns[-window:]
    if not recent_returns:
        return 0.5

    # Use coefficient of variation inverse as stability metric
    mean_return = np.mean(recent_returns)
    std_return = np.std(recent_returns)

    if std_return == 0:
        return 1.0

    # Inverse coefficient of variation, bounded
    cv = abs(safe_divide(std_return, abs(mean_return) + 0.001, 10.0))
    stability = 1.0 / (1.0 + cv)

    return max(0.0, min(1.0, stability))


def round_to_strike(price: float, increment: float = 1.0) -> float:
    """
    Round price to nearest strike increment.

    Args:
        price: Price to round
        increment: Strike price increment (e.g., 1.0 for $1 strikes)

    Returns:
        float: Rounded strike price
    """
    if increment <= 0:
        return price

    return round(price / increment) * increment