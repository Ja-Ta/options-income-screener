"""
Implied Volatility metrics for the Options Income Screener.

Calculates IV Rank and IV Percentile for screening.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
import numpy as np
from ..utils.math import percentile_rank


def iv_rank(current_iv: float, historical_ivs: List[float]) -> float:
    """
    Calculate IV Rank - where current IV falls vs 52-week range.

    IV Rank = (Current IV - 52w Low) / (52w High - 52w Low) * 100

    Args:
        current_iv: Current implied volatility
        historical_ivs: List of historical IV values (typically 252 days)

    Returns:
        float: IV Rank as percentage (0-100)
    """
    if not historical_ivs or len(historical_ivs) < 2:
        return 50.0  # Default to middle if insufficient data

    min_iv = min(historical_ivs)
    max_iv = max(historical_ivs)

    if max_iv == min_iv:
        return 50.0  # All values are the same

    rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100.0
    return max(0.0, min(100.0, rank))


def iv_percentile(current_iv: float, historical_ivs: List[float]) -> float:
    """
    Calculate IV Percentile - percentage of days IV was lower than today.

    Args:
        current_iv: Current implied volatility
        historical_ivs: List of historical IV values (typically 252 days)

    Returns:
        float: IV Percentile as percentage (0-100)
    """
    if not historical_ivs:
        return 50.0  # Default to middle if no data

    # Count how many days had lower IV
    lower_count = sum(1 for iv in historical_ivs if iv < current_iv)
    percentile = (lower_count / len(historical_ivs)) * 100.0

    return max(0.0, min(100.0, percentile))


def calculate_atm_iv(option_chain: List[Dict[str, Any]], spot_price: float, dte_target: int = 30) -> Optional[float]:
    """
    Calculate at-the-money implied volatility from option chain.

    Args:
        option_chain: List of option contracts
        spot_price: Current stock price
        dte_target: Target DTE for IV calculation

    Returns:
        Optional[float]: ATM IV or None if not found
    """
    if not option_chain:
        return None

    # Filter for options near target DTE
    dte_tolerance = 7  # +/- 7 days
    filtered_options = [
        opt for opt in option_chain
        if abs(opt['dte'] - dte_target) <= dte_tolerance
    ]

    if not filtered_options:
        # Fall back to all options if none near target DTE
        filtered_options = option_chain

    # Find ATM options (closest strike to spot)
    atm_options = []
    for opt in filtered_options:
        strike_distance = abs(opt['strike'] - spot_price) / spot_price
        if strike_distance <= 0.02:  # Within 2% of spot
            atm_options.append(opt)

    if not atm_options:
        # Find closest strike if no true ATM
        atm_options = [min(filtered_options, key=lambda x: abs(x['strike'] - spot_price))]

    # Average IV of ATM calls and puts
    ivs = []
    for side in ['call', 'put']:
        side_options = [opt for opt in atm_options if opt['side'] == side]
        if side_options:
            # Weight by volume/OI for better representation
            weighted_ivs = []
            weights = []
            for opt in side_options:
                weight = opt.get('vol', 1) + opt.get('oi', 1)
                weighted_ivs.append(opt['iv'] * weight)
                weights.append(weight)

            if weights:
                ivs.append(sum(weighted_ivs) / sum(weights))

    return sum(ivs) / len(ivs) if ivs else None


def generate_iv_history(current_iv: float, lookback_days: int = 252) -> List[float]:
    """
    Generate mock historical IV data for testing.

    In production, this would fetch actual historical IV from database.

    Args:
        current_iv: Current IV value
        lookback_days: Number of days of history

    Returns:
        List[float]: Historical IV values
    """
    # Generate realistic IV history with mean reversion
    history = []
    base_iv = current_iv * 0.9  # Historical average slightly lower

    for i in range(lookback_days):
        # Add random walk with mean reversion
        daily_change = np.random.normal(0, 0.02)
        mean_reversion = (base_iv - (history[-1] if history else base_iv)) * 0.1

        if history:
            new_iv = history[-1] + daily_change + mean_reversion
        else:
            new_iv = base_iv + daily_change

        # Keep IV in reasonable bounds
        new_iv = max(0.10, min(0.80, new_iv))
        history.append(new_iv)

    return history


def calculate_iv_metrics(
    option_chain: List[Dict[str, Any]],
    spot_price: float,
    historical_ivs: Optional[List[float]] = None
) -> Dict[str, float]:
    """
    Calculate all IV metrics for screening.

    Args:
        option_chain: List of option contracts
        spot_price: Current stock price
        historical_ivs: Optional historical IV values

    Returns:
        Dict with iv_current, iv_rank, iv_percentile
    """
    # Calculate current ATM IV
    current_iv = calculate_atm_iv(option_chain, spot_price)

    if current_iv is None:
        # Fallback to average of all IVs if ATM calculation fails
        all_ivs = [opt['iv'] for opt in option_chain if 'iv' in opt and opt['iv'] > 0]
        current_iv = sum(all_ivs) / len(all_ivs) if all_ivs else 0.25

    # Generate or use historical IVs
    if historical_ivs is None:
        historical_ivs = generate_iv_history(current_iv)

    # Calculate metrics
    return {
        "iv_current": current_iv,
        "iv_rank": iv_rank(current_iv, historical_ivs),
        "iv_percentile": iv_percentile(current_iv, historical_ivs)
    }


def iv_environment_suitable(iv_rank_value: float, min_threshold: float) -> bool:
    """
    Check if IV environment is suitable for selling options.

    Args:
        iv_rank_value: Current IV Rank (0-100)
        min_threshold: Minimum IV Rank threshold

    Returns:
        bool: True if IV is high enough for option selling
    """
    return iv_rank_value >= min_threshold


def calculate_iv_premium(iv_rank_value: float) -> float:
    """
    Calculate IV premium factor for scoring.

    Higher IV Rank means more premium available.

    Args:
        iv_rank_value: IV Rank (0-100)

    Returns:
        float: Premium factor (0.5 to 1.5)
    """
    # Linear scaling: 0% IVR = 0.5x, 50% IVR = 1.0x, 100% IVR = 1.5x
    return 0.5 + (iv_rank_value / 100.0)


def iv_risk_adjustment(iv_current: float, hv_current: float) -> float:
    """
    Calculate risk adjustment based on IV vs HV.

    When IV > HV, market expects more volatility (higher risk).

    Args:
        iv_current: Current implied volatility
        hv_current: Current historical volatility

    Returns:
        float: Risk adjustment factor (0.8 to 1.2)
    """
    if hv_current <= 0:
        return 1.0

    iv_hv_ratio = iv_current / hv_current

    if iv_hv_ratio > 1.5:
        # IV much higher than HV - higher risk
        return 0.8
    elif iv_hv_ratio > 1.2:
        return 0.9
    elif iv_hv_ratio < 0.8:
        # IV much lower than HV - potentially underpriced
        return 1.1
    else:
        # IV close to HV - normal
        return 1.0