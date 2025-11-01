"""
Covered Calls scoring algorithm for the Options Income Screener.

Calculates comprehensive scores for CC picks based on multiple factors.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import Dict, Any, List
from ..constants import CC_SCORING_WEIGHTS, BELOW_SMA200_PENALTY
from ..utils.math import zscore


def normalize_metric(value: float, min_val: float = 0, max_val: float = 100,
                    target: float = 50, scale: float = 15) -> float:
    """
    Normalize a metric to a 0-1 scale using z-score approach.

    Args:
        value: The metric value to normalize
        min_val: Minimum expected value
        max_val: Maximum expected value
        target: Target/mean value for z-score
        scale: Standard deviation for z-score

    Returns:
        float: Normalized value between 0 and 1
    """
    # Use z-score normalization
    z = zscore(value, target, scale)

    # Convert to 0-1 scale (assuming ±3 sigma covers most range)
    normalized = (z + 3) / 6

    # Clamp to 0-1
    return max(0.0, min(1.0, normalized))


def cc_score(
    iv_rank: float,
    roi_30d: float,
    trend_strength: float,
    dividend_yield: float = 0.0,
    below_200sma: bool = False,
    additional_factors: Dict[str, Any] = None
) -> float:
    """
    Calculate comprehensive score for a covered call pick.

    Formula:
    Base Score = w1*IV_Rank + w2*ROI + w3*Trend + w4*Dividend
    Final Score = Base Score * Penalties

    Args:
        iv_rank: IV Rank percentage (0-100)
        roi_30d: 30-day ROI as decimal (e.g., 0.015 for 1.5%)
        trend_strength: Trend strength score (-1 to 1)
        dividend_yield: Annual dividend yield as decimal
        below_200sma: Whether stock is below 200-day SMA
        additional_factors: Optional dict with extra scoring factors

    Returns:
        float: Final score (0 to 1, higher is better)
    """
    weights = CC_SCORING_WEIGHTS
    additional_factors = additional_factors or {}

    # Normalize components
    iv_component = normalize_metric(iv_rank, 0, 100, 50, 15) * weights['iv_rank']

    # ROI: normalize assuming 0-3% monthly is typical range
    roi_component = normalize_metric(roi_30d * 100, 0, 3, 1.5, 0.5) * weights['roi_30d']

    # Trend: already -1 to 1, convert to 0-1
    trend_component = (trend_strength + 1) / 2 * weights['trend_strength']

    # Dividend: normalize assuming 0-5% annual yield
    div_component = min(dividend_yield / 0.05, 1.0) * weights['dividend_yield']

    # Calculate base score
    base_score = iv_component + roi_component + trend_component + div_component

    # Apply penalties and bonuses
    final_score = base_score

    # Penalty for being below 200 SMA
    if below_200sma:
        final_score *= BELOW_SMA200_PENALTY

    # Additional factors from pick data
    if additional_factors:
        # Bonus for high liquidity
        if additional_factors.get('oi', 0) > 2000:
            final_score *= 1.05

        # Penalty for wide spread
        if additional_factors.get('spread_pct', 0) > 0.07:
            final_score *= 0.95

        # Bonus for stability
        if additional_factors.get('trend_consistency', 0) > 0.7:
            final_score *= 1.03

        # Penalty for earnings proximity
        if additional_factors.get('near_earnings', False):
            final_score *= 0.97

    # Ensure score stays in bounds
    return max(0.0, min(1.0, final_score))


def score_cc_pick(pick: Dict[str, Any]) -> float:
    """
    Score a covered call pick using all available data.

    Args:
        pick: Complete pick dictionary from screener

    Returns:
        float: Score between 0 and 1
    """
    # Extract main scoring inputs
    iv_rank = pick.get('iv_rank', 50)
    roi_30d = pick.get('roi_30d', 0.01)
    trend_strength = pick.get('trend_strength', 0)
    dividend_yield = pick.get('dividend_yield', 0)
    below_200sma = pick.get('below_200sma', False)

    # Prepare additional factors
    additional = {
        'oi': pick.get('oi', 0),
        'spread_pct': pick.get('spread_pct', 0),
        'trend_consistency': pick.get('trend_consistency', 0.5),
        'near_earnings': pick.get('near_earnings', False),
        'hv_60': pick.get('hv_60', 0),
        'volume': pick.get('volume', 0)
    }

    # Calculate score
    score = cc_score(
        iv_rank=iv_rank,
        roi_30d=roi_30d,
        trend_strength=trend_strength,
        dividend_yield=dividend_yield,
        below_200sma=below_200sma,
        additional_factors=additional
    )

    return score


def rank_cc_picks(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score and rank multiple covered call picks.

    Args:
        picks: List of pick dictionaries from screener

    Returns:
        List[Dict]: Picks with scores added, sorted by score descending
    """
    # Score each pick
    for pick in picks:
        pick['score'] = score_cc_pick(pick)

    # Sort by score (highest first)
    picks.sort(key=lambda x: x['score'], reverse=True)

    # Add rank
    for i, pick in enumerate(picks, 1):
        pick['rank'] = i

    return picks


def explain_cc_score(pick: Dict[str, Any]) -> str:
    """
    Generate human-readable explanation of score components.

    Args:
        pick: Pick dictionary with score

    Returns:
        str: Explanation of score calculation
    """
    score = pick.get('score', 0)
    iv_rank = pick.get('iv_rank', 50)
    roi_30d = pick.get('roi_30d', 0.01)
    trend_strength = pick.get('trend_strength', 0)

    explanation = f"Score: {score:.2f}\n"
    explanation += f"Components:\n"
    explanation += f"  • IV Rank ({iv_rank:.0f}%): "

    if iv_rank > 70:
        explanation += "Excellent volatility premium\n"
    elif iv_rank > 50:
        explanation += "Good volatility environment\n"
    else:
        explanation += "Moderate volatility\n"

    explanation += f"  • ROI ({roi_30d:.2%}/month): "
    if roi_30d > 0.02:
        explanation += "Outstanding returns\n"
    elif roi_30d > 0.015:
        explanation += "Strong returns\n"
    else:
        explanation += "Acceptable returns\n"

    explanation += f"  • Trend: "
    if trend_strength > 0.5:
        explanation += "Strong uptrend\n"
    elif trend_strength > 0:
        explanation += "Positive momentum\n"
    else:
        explanation += "Weak or negative trend\n"

    # Add penalties/bonuses
    if pick.get('below_200sma'):
        explanation += "  • Penalty: Below 200 SMA\n"
    if pick.get('near_earnings'):
        explanation += "  • Warning: Earnings approaching\n"
    if pick.get('oi', 0) > 2000:
        explanation += "  • Bonus: Excellent liquidity\n"

    return explanation