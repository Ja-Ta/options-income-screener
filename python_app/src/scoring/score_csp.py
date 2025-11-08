"""
Cash-Secured Puts scoring algorithm for the Options Income Screener.

Calculates comprehensive scores for CSP picks based on multiple factors.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import Dict, Any, List
from ..constants import (
    CSP_SCORING_WEIGHTS,
    THETA_OPTIMAL_RANGE, GAMMA_LOW_THRESHOLD, GAMMA_HIGH_THRESHOLD,
    VEGA_HIGH_THRESHOLD, VEGA_LOW_THRESHOLD
)
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


def csp_score(
    iv_rank: float,
    roi_30d: float,
    margin_of_safety: float,
    trend_stability: float,
    theta: float = 0.0,
    gamma: float = 0.0,
    vega: float = 0.0,
    additional_factors: Dict[str, Any] = None
) -> float:
    """
    Calculate comprehensive score for a cash-secured put pick.

    Formula:
    Score = w1*IV_Rank + w2*ROI + w3*Margin + w4*Stability + w5*Theta + w6*Gamma + w7*Vega

    Args:
        iv_rank: IV Rank percentage (0-100)
        roi_30d: 30-day ROI as decimal (e.g., 0.012 for 1.2%)
        margin_of_safety: How far OTM as decimal (e.g., 0.08 for 8%)
        trend_stability: Trend consistency score (0 to 1)
        theta: Theta (time decay per day, as absolute value)
        gamma: Gamma (delta change per $1 stock move)
        vega: Vega (price change per 1% IV change)
        additional_factors: Optional dict with extra scoring factors

    Returns:
        float: Final score (0 to 1, higher is better)
    """
    weights = CSP_SCORING_WEIGHTS
    additional_factors = additional_factors or {}

    # Normalize components
    # IV Rank: 0-100 scale
    iv_component = normalize_metric(iv_rank, 0, 100, 55, 15) * weights['iv_rank']

    # ROI: normalize assuming 0-2.5% monthly is typical range for CSP
    roi_component = normalize_metric(roi_30d * 100, 0, 2.5, 1.2, 0.4) * weights['roi_30d']

    # Margin of Safety: normalize assuming 0-15% is typical
    margin_component = normalize_metric(margin_of_safety * 100, 0, 15, 7.5, 3) * weights['margin_of_safety']

    # Trend Stability: already 0-1
    stability_component = trend_stability * weights['trend_stability']

    # Theta: normalize assuming 0.03-0.25 range, optimal 0.05-0.15
    theta_abs = abs(theta)
    theta_optimal_min, theta_optimal_max = THETA_OPTIMAL_RANGE
    if theta_optimal_min <= theta_abs <= theta_optimal_max:
        theta_component = 1.0 * weights['theta']
    elif theta_abs < theta_optimal_min:
        theta_component = (theta_abs / theta_optimal_min) * weights['theta']
    else:
        theta_component = max(0.3, 1.0 - (theta_abs - theta_optimal_max) / 0.15) * weights['theta']

    # Gamma: prefer low gamma (more stable), penalize high gamma
    if gamma <= GAMMA_LOW_THRESHOLD:
        gamma_component = 1.0 * weights['gamma']
    elif gamma <= GAMMA_HIGH_THRESHOLD:
        gamma_component = 0.7 * weights['gamma']
    else:
        gamma_component = 0.3 * weights['gamma']

    # Vega: match to IV environment (same as CC logic)
    if iv_rank > 70 and vega > VEGA_HIGH_THRESHOLD:
        vega_component = 1.0 * weights['vega']  # High vega in high IV = excellent
    elif iv_rank > 70 and vega > VEGA_LOW_THRESHOLD:
        vega_component = 0.8 * weights['vega']
    elif iv_rank < 30 and vega < VEGA_LOW_THRESHOLD:
        vega_component = 0.9 * weights['vega']  # Low vega in low IV = good stability
    else:
        vega_component = 0.6 * weights['vega']  # Moderate match

    # Calculate base score
    base_score = (iv_component + roi_component + margin_component + stability_component +
                  theta_component + gamma_component + vega_component)

    # Apply adjustments
    final_score = base_score

    # Additional factors from pick data
    if additional_factors:
        # Bonus for being in uptrend
        if additional_factors.get('in_uptrend', False):
            final_score *= 1.08

        # Bonus for high liquidity
        if additional_factors.get('oi', 0) > 2000:
            final_score *= 1.05

        # Penalty for wide spread
        if additional_factors.get('spread_pct', 0) > 0.07:
            final_score *= 0.95

        # Bonus for high IV percentile
        if additional_factors.get('iv_percentile', 0) > 80:
            final_score *= 1.03

        # Penalty for too close to spot
        if margin_of_safety < 0.05:
            final_score *= 0.92

        # Bonus for strong support level nearby
        if additional_factors.get('near_support', False):
            final_score *= 1.04

        # Earnings proximity penalty (same as CC)
        earnings_days_until = additional_factors.get('earnings_days_until', 999)
        if earnings_days_until < 7:
            # Severe penalty for earnings within 7 days (high risk)
            final_score *= 0.50
        elif earnings_days_until < 14:
            # Strong penalty for earnings 7-14 days out
            final_score *= 0.70
        elif earnings_days_until < 21:
            # Moderate penalty for earnings 14-21 days out
            final_score *= 0.85
        elif earnings_days_until < 30:
            # Light penalty for earnings 21-30 days out
            final_score *= 0.93

    # Ensure score stays in bounds
    return max(0.0, min(1.0, final_score))


def score_csp_pick(pick: Dict[str, Any]) -> float:
    """
    Score a cash-secured put pick using all available data.

    Args:
        pick: Complete pick dictionary from screener

    Returns:
        float: Score between 0 and 1
    """
    # Extract main scoring inputs
    iv_rank = pick.get('iv_rank', 50)
    roi_30d = pick.get('roi_30d', 0.01)
    margin_of_safety = pick.get('margin_of_safety', 0.07)
    trend_stability = pick.get('trend_stability', 0.5)

    # Extract Greeks
    theta = pick.get('theta', 0.0)
    gamma = pick.get('gamma', 0.0)
    vega = pick.get('vega', 0.0)

    # Check if near support
    strike = pick.get('strike', 0)
    support_level = pick.get('support_level', 0)
    near_support = False
    if support_level and strike:
        # Consider "near support" if strike is within 2% of support
        near_support = abs(strike - support_level) / support_level < 0.02

    # Prepare additional factors
    additional = {
        'in_uptrend': pick.get('in_uptrend', False),
        'oi': pick.get('oi', 0),
        'spread_pct': pick.get('spread_pct', 0),
        'iv_percentile': pick.get('iv_percentile', 50),
        'near_support': near_support,
        'earnings_days_until': pick.get('earnings_days_until', 999),
        'hv_60': pick.get('hv_60', 0),
        'volume': pick.get('volume', 0)
    }

    # Calculate score
    score = csp_score(
        iv_rank=iv_rank,
        roi_30d=roi_30d,
        margin_of_safety=margin_of_safety,
        trend_stability=trend_stability,
        theta=theta,
        gamma=gamma,
        vega=vega,
        additional_factors=additional
    )

    return score


def rank_csp_picks(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score and rank multiple cash-secured put picks.

    Args:
        picks: List of pick dictionaries from screener

    Returns:
        List[Dict]: Picks with scores added, sorted by score descending
    """
    # Score each pick
    for pick in picks:
        pick['score'] = score_csp_pick(pick)

    # Sort by score (highest first)
    picks.sort(key=lambda x: x['score'], reverse=True)

    # Add rank
    for i, pick in enumerate(picks, 1):
        pick['rank'] = i

    return picks


def explain_csp_score(pick: Dict[str, Any]) -> str:
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
    margin_of_safety = pick.get('margin_of_safety', 0.07)
    trend_stability = pick.get('trend_stability', 0.5)

    explanation = f"Score: {score:.2f}\n"
    explanation += f"Components:\n"

    # IV Rank assessment
    explanation += f"  • IV Rank ({iv_rank:.0f}%): "
    if iv_rank > 70:
        explanation += "Excellent volatility premium\n"
    elif iv_rank > 55:
        explanation += "Good volatility environment\n"
    else:
        explanation += "Adequate volatility\n"

    # ROI assessment
    explanation += f"  • ROI ({roi_30d:.2%}/month): "
    if roi_30d > 0.018:
        explanation += "Outstanding returns\n"
    elif roi_30d > 0.012:
        explanation += "Strong returns\n"
    else:
        explanation += "Acceptable returns\n"

    # Margin of safety assessment
    explanation += f"  • Margin ({margin_of_safety:.1%} OTM): "
    if margin_of_safety > 0.10:
        explanation += "Excellent safety buffer\n"
    elif margin_of_safety > 0.07:
        explanation += "Good downside protection\n"
    elif margin_of_safety > 0.05:
        explanation += "Adequate protection\n"
    else:
        explanation += "Limited protection\n"

    # Trend stability assessment
    explanation += f"  • Stability ({trend_stability:.1f}): "
    if trend_stability > 0.7:
        explanation += "Very stable trend\n"
    elif trend_stability > 0.5:
        explanation += "Moderate stability\n"
    else:
        explanation += "Volatile price action\n"

    # Add bonuses/warnings
    if pick.get('in_uptrend'):
        explanation += "  • Bonus: Stock in uptrend\n"
    if pick.get('oi', 0) > 2000:
        explanation += "  • Bonus: Excellent liquidity\n"
    if margin_of_safety < 0.05:
        explanation += "  • Warning: Close to spot price\n"

    # Earnings warnings
    earnings_days = pick.get('earnings_days_until', 999)
    if earnings_days < 7:
        explanation += "  • ⚠️ SEVERE: Earnings in <7 days (-50%)\n"
    elif earnings_days < 14:
        explanation += "  • ⚠️ WARNING: Earnings in 7-14 days (-30%)\n"
    elif earnings_days < 21:
        explanation += "  • ⚠️ Caution: Earnings in 14-21 days (-15%)\n"
    elif earnings_days < 30:
        explanation += "  • ⚠️ Note: Earnings in 21-30 days (-7%)\n"

    return explanation


def compare_csp_picks(pick1: Dict[str, Any], pick2: Dict[str, Any]) -> str:
    """
    Compare two CSP picks and explain differences.

    Args:
        pick1: First pick dictionary
        pick2: Second pick dictionary

    Returns:
        str: Comparison explanation
    """
    score1 = pick1.get('score', 0)
    score2 = pick2.get('score', 0)

    comparison = f"Comparing {pick1['symbol']} vs {pick2['symbol']}:\n"
    comparison += f"  {pick1['symbol']}: Score {score1:.2f}\n"
    comparison += f"  {pick2['symbol']}: Score {score2:.2f}\n\n"

    # Compare key metrics
    comparison += "Key differences:\n"

    # IV Rank
    iv_diff = pick1['iv_rank'] - pick2['iv_rank']
    if abs(iv_diff) > 10:
        winner = pick1['symbol'] if iv_diff > 0 else pick2['symbol']
        comparison += f"  • IV Rank: {winner} has {abs(iv_diff):.0f}% higher IV\n"

    # ROI
    roi_diff = pick1['roi_30d'] - pick2['roi_30d']
    if abs(roi_diff) > 0.002:
        winner = pick1['symbol'] if roi_diff > 0 else pick2['symbol']
        comparison += f"  • ROI: {winner} offers {abs(roi_diff):.2%} better returns\n"

    # Margin of safety
    margin_diff = pick1['margin_of_safety'] - pick2['margin_of_safety']
    if abs(margin_diff) > 0.02:
        winner = pick1['symbol'] if margin_diff > 0 else pick2['symbol']
        comparison += f"  • Safety: {winner} is {abs(margin_diff):.1%} further OTM\n"

    # Overall winner
    if score1 > score2:
        comparison += f"\nRecommendation: {pick1['symbol']} (higher overall score)"
    elif score2 > score1:
        comparison += f"\nRecommendation: {pick2['symbol']} (higher overall score)"
    else:
        comparison += f"\nRecommendation: Both equally attractive"

    return comparison