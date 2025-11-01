"""
Cash-Secured Puts screening logic for the Options Income Screener.

Identifies profitable put options to sell backed by cash reserves.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import Dict, Any, List, Optional
from datetime import date
from ..constants import (
    MIN_PRICE, MIN_OPTION_OI, MIN_OPTION_VOLUME, MAX_SPREAD_PCT,
    CSP_DELTA_RANGE, CSP_DTE_RANGE, CSP_MIN_IVR, MAX_HV_60,
    CSP_ANNUALIZED_TARGET, EARNINGS_EXCLUSION_DAYS
)
from ..utils.math import (
    safe_divide, calculate_roi, annualize_return,
    calculate_spread_percentage, calculate_margin_of_safety
)
from ..utils.dates import is_near_earnings, calculate_dte
from ..utils.logging import get_logger, log_screening_result


def select_csp_contract(
    options_chain: List[Dict[str, Any]],
    spot_price: float,
    delta_range: tuple[float, float] = CSP_DELTA_RANGE,
    dte_range: tuple[int, int] = CSP_DTE_RANGE
) -> Optional[Dict[str, Any]]:
    """
    Select the optimal put contract for cash-secured put strategy.

    Args:
        options_chain: List of option contracts
        spot_price: Current stock price
        delta_range: Acceptable delta range for puts (negative values)
        dte_range: Acceptable DTE range

    Returns:
        Optional[Dict]: Best put contract or None if no suitable contract
    """
    logger = get_logger()

    # Filter for puts only
    puts = [opt for opt in options_chain if opt['side'] == 'put']

    if not puts:
        logger.debug("No put options available")
        return None

    # Apply filters
    min_delta, max_delta = delta_range  # Note: these are negative for puts
    min_dte, max_dte = dte_range

    suitable_puts = []
    for put in puts:
        # Check DTE
        if not (min_dte <= put['dte'] <= max_dte):
            continue

        # Check delta (negative for puts, so we need to handle the comparison correctly)
        # For puts: -0.30 to -0.25 means we want delta between -0.30 and -0.25
        put_delta = abs(put['delta'])  # Convert to positive for easier comparison
        if not (min_delta <= put_delta <= max_delta):
            continue

        # Check liquidity
        if put.get('oi', 0) < MIN_OPTION_OI:
            continue
        if put.get('vol', 0) < MIN_OPTION_VOLUME:
            continue

        # Check spread
        spread = calculate_spread_percentage(put['bid'], put['ask'])
        if spread > MAX_SPREAD_PCT:
            continue

        # Calculate ROI for this contract
        premium = put['mid']
        strike = put['strike']
        roi_period = calculate_roi(premium, strike, put['dte'])  # ROI based on strike for CSP
        roi_annual = annualize_return(roi_period, put['dte'])

        # Calculate margin of safety (how far OTM)
        margin_of_safety = calculate_margin_of_safety(spot_price, strike)

        put['roi_period'] = roi_period
        put['roi_annual'] = roi_annual
        put['spread_pct'] = spread
        put['margin_of_safety'] = margin_of_safety

        suitable_puts.append(put)

    if not suitable_puts:
        logger.debug("No suitable put contracts after filtering")
        return None

    # Select best contract (balance of ROI and safety)
    # Score = 70% ROI + 30% margin of safety
    def score_put(put):
        roi_score = put['roi_annual'] / 0.30  # Normalize to 0-1 assuming 30% max
        safety_score = put['margin_of_safety'] / 0.15  # Normalize to 0-1 assuming 15% max
        return 0.7 * roi_score + 0.3 * safety_score

    best_put = max(suitable_puts, key=score_put)

    logger.debug(f"Selected put: Strike={best_put['strike']}, "
                f"Delta={best_put['delta']:.2f}, "
                f"ROI={best_put['roi_annual']:.2%}, "
                f"Safety={best_put['margin_of_safety']:.2%}")

    return best_put


def screen_csp(
    symbol: str,
    price_data: Dict[str, Any],
    options_chain: List[Dict[str, Any]],
    iv_metrics: Dict[str, float],
    earnings_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Screen a symbol for cash-secured put opportunities.

    Args:
        symbol: Stock symbol
        price_data: Price and technical data
        options_chain: Option chain data
        iv_metrics: IV rank and percentile
        earnings_date: Next earnings date

    Returns:
        Optional[Dict]: Screened pick with all details or None if filtered out
    """
    logger = get_logger()

    # Extract key data
    spot_price = price_data['close']
    sma20 = price_data.get('sma20')
    sma50 = price_data.get('sma50')
    sma200 = price_data.get('sma200')
    hv_60 = price_data.get('hv_60', 0)
    iv_rank = iv_metrics.get('iv_rank', 0)
    trend_stability = price_data.get('trend_consistency', 0.5)

    # Pre-screening filters

    # 1. Price filter
    if spot_price < MIN_PRICE:
        log_screening_result(symbol, "CSP", "failed - price too low")
        return None

    # 2. IV environment filter (higher requirement for CSP)
    if iv_rank < CSP_MIN_IVR:
        log_screening_result(symbol, "CSP", f"failed - IV rank {iv_rank:.1f}% < {CSP_MIN_IVR}%")
        return None

    # 3. Volatility sanity check
    if hv_60 > MAX_HV_60:
        log_screening_result(symbol, "CSP", f"failed - HV60 {hv_60:.2%} too high")
        return None

    # 4. Earnings exclusion (strict for CSP)
    if is_near_earnings(earnings_date, exclusion_days=EARNINGS_EXCLUSION_DAYS):
        log_screening_result(symbol, "CSP", "failed - earnings too close")
        return None

    # 5. Trend assessment (not exclusion, but affects scoring)
    in_uptrend = False
    if sma20 and sma50 and sma200:
        in_uptrend = sma20 > sma50 > sma200

    support_level = sma200 if sma200 else sma50 if sma50 else None

    # Select optimal contract
    best_contract = select_csp_contract(options_chain, spot_price)

    if not best_contract:
        log_screening_result(symbol, "CSP", "failed - no suitable contracts")
        return None

    # Check if ROI meets target
    if best_contract['roi_annual'] < CSP_ANNUALIZED_TARGET:
        log_screening_result(symbol, "CSP",
                           f"failed - ROI {best_contract['roi_annual']:.2%} < "
                           f"target {CSP_ANNUALIZED_TARGET:.2%}")
        return None

    # Build pick result
    pick = {
        'symbol': symbol,
        'strategy': 'CSP',
        'spot_price': spot_price,
        'strike': best_contract['strike'],
        'expiry': best_contract['expiry'],
        'dte': best_contract['dte'],
        'side': 'put',
        'delta': best_contract['delta'],
        'iv': best_contract['iv'],
        'bid': best_contract['bid'],
        'ask': best_contract['ask'],
        'mid': best_contract['mid'],
        'premium': best_contract['mid'],
        'oi': best_contract['oi'],
        'volume': best_contract['vol'],
        'spread_pct': best_contract['spread_pct'],
        'roi_period': best_contract['roi_period'],
        'roi_30d': best_contract['roi_period'] * (30.0 / best_contract['dte']),
        'roi_annual': best_contract['roi_annual'],
        'margin_of_safety': best_contract['margin_of_safety'],
        'iv_rank': iv_rank,
        'iv_percentile': iv_metrics.get('iv_percentile', 0),
        'hv_20': price_data.get('hv_20', 0),
        'hv_60': hv_60,
        'sma20': sma20,
        'sma50': sma50,
        'sma200': sma200,
        'in_uptrend': in_uptrend,
        'support_level': support_level,
        'trend_stability': trend_stability,
        'trend_strength': price_data.get('trend_strength', 0),
        'selected_option': f"PUT {best_contract['strike']} {best_contract['expiry']}",
        'notes': []
    }

    # Add notes based on conditions
    if pick['margin_of_safety'] > 0.10:
        pick['notes'].append(f"✅ {pick['margin_of_safety']:.1%} OTM")
    elif pick['margin_of_safety'] > 0.05:
        pick['notes'].append(f"⚠️ Only {pick['margin_of_safety']:.1%} OTM")

    if iv_rank > 70:
        pick['notes'].append("🔥 High IV rank")
    if pick['roi_annual'] > 0.18:
        pick['notes'].append("💰 Excellent ROI")
    if pick['oi'] > 1000:
        pick['notes'].append("💧 High liquidity")
    if in_uptrend:
        pick['notes'].append("📈 Uptrend")
    if trend_stability > 0.7:
        pick['notes'].append("🎯 Stable trend")

    # Warning notes
    if pick['spread_pct'] > 0.05:
        pick['notes'].append(f"⚠️ Wide spread {pick['spread_pct']:.1%}")
    if not in_uptrend:
        pick['notes'].append("📉 Not in uptrend")

    pick['notes'] = '; '.join(pick['notes']) if pick['notes'] else "Standard setup"

    log_screening_result(symbol, "CSP", "passed")

    return pick


def screen_multiple_csp(
    symbols_data: Dict[str, Dict[str, Any]],
    options_chains: Dict[str, List[Dict[str, Any]]],
    iv_metrics_data: Dict[str, Dict[str, float]],
    earnings_dates: Dict[str, Optional[date]] = None
) -> List[Dict[str, Any]]:
    """
    Screen multiple symbols for cash-secured put opportunities.

    Args:
        symbols_data: Dict of symbol -> price/technical data
        options_chains: Dict of symbol -> option chain
        iv_metrics_data: Dict of symbol -> IV metrics
        earnings_dates: Dict of symbol -> earnings date

    Returns:
        List[Dict]: List of screened picks, sorted by score
    """
    picks = []
    earnings_dates = earnings_dates or {}

    for symbol, price_data in symbols_data.items():
        if symbol not in options_chains:
            continue
        if symbol not in iv_metrics_data:
            continue

        pick = screen_csp(
            symbol,
            price_data,
            options_chains[symbol],
            iv_metrics_data[symbol],
            earnings_dates.get(symbol)
        )

        if pick:
            picks.append(pick)

    # Sort by combined score (ROI and margin of safety)
    picks.sort(key=lambda x: x['roi_annual'] * 0.7 + x.get('margin_of_safety', 0) * 3.0, reverse=True)

    return picks