"""
Covered Calls screening logic for the Options Income Screener.

Identifies profitable call options to sell against stock positions.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import Dict, Any, List, Optional
from datetime import date
from ..constants import (
    MIN_PRICE, MIN_OPTION_OI, MIN_OPTION_VOLUME, MAX_SPREAD_PCT,
    CC_DELTA_RANGE, CC_DTE_RANGE, CC_MIN_IVR, MAX_HV_60,
    CC_ANNUALIZED_TARGET, BELOW_SMA200_PENALTY
)
from ..utils.math import (
    safe_divide, calculate_roi, annualize_return,
    calculate_spread_percentage, calculate_margin_of_safety
)
from ..utils.dates import is_near_earnings, calculate_dte
from ..utils.logging import get_logger, log_screening_result


def select_cc_contract(
    options_chain: List[Dict[str, Any]],
    spot_price: float,
    delta_range: tuple[float, float] = CC_DELTA_RANGE,
    dte_range: tuple[int, int] = CC_DTE_RANGE
) -> Optional[Dict[str, Any]]:
    """
    Select the optimal call contract for covered call strategy.

    Args:
        options_chain: List of option contracts
        spot_price: Current stock price
        delta_range: Acceptable delta range for calls
        dte_range: Acceptable DTE range

    Returns:
        Optional[Dict]: Best call contract or None if no suitable contract
    """
    logger = get_logger()

    # Filter for calls only
    calls = [opt for opt in options_chain if opt['side'] == 'call']

    if not calls:
        logger.debug("No call options available")
        return None

    # Apply filters
    min_delta, max_delta = delta_range
    min_dte, max_dte = dte_range

    suitable_calls = []
    for call in calls:
        # Check DTE
        if not (min_dte <= call['dte'] <= max_dte):
            continue

        # Check delta (positive for calls)
        if not (min_delta <= call['delta'] <= max_delta):
            continue

        # Check liquidity
        if call.get('oi', 0) < MIN_OPTION_OI:
            continue
        if call.get('vol', 0) < MIN_OPTION_VOLUME:
            continue

        # Check spread
        spread = calculate_spread_percentage(call['bid'], call['ask'])
        if spread > MAX_SPREAD_PCT:
            continue

        # Calculate ROI for this contract
        premium = call['mid']
        roi_period = calculate_roi(premium, spot_price, call['dte'])
        roi_annual = annualize_return(roi_period, call['dte'])

        call['roi_period'] = roi_period
        call['roi_annual'] = roi_annual
        call['spread_pct'] = spread

        suitable_calls.append(call)

    if not suitable_calls:
        logger.debug("No suitable call contracts after filtering")
        return None

    # Select best contract (highest annualized ROI)
    best_call = max(suitable_calls, key=lambda x: x['roi_annual'])

    logger.debug(f"Selected call: Strike={best_call['strike']}, "
                f"Delta={best_call['delta']:.2f}, "
                f"ROI={best_call['roi_annual']:.2%}")

    return best_call


def screen_cc(
    symbol: str,
    price_data: Dict[str, Any],
    options_chain: List[Dict[str, Any]],
    iv_metrics: Dict[str, float],
    earnings_date: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Screen a symbol for covered call opportunities.

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

    # Pre-screening filters

    # 1. Price filter
    if spot_price < MIN_PRICE:
        log_screening_result(symbol, "CC", "failed - price too low")
        return None

    # 2. IV environment filter
    if iv_rank < CC_MIN_IVR:
        log_screening_result(symbol, "CC", f"failed - IV rank {iv_rank:.1f}% < {CC_MIN_IVR}%")
        return None

    # 3. Volatility sanity check
    if hv_60 > MAX_HV_60:
        log_screening_result(symbol, "CC", f"failed - HV60 {hv_60:.2%} too high")
        return None

    # 4. Trend filter (warning only, not exclusion)
    trend_warning = False
    if sma20 and sma50:
        if sma20 < sma50:
            trend_warning = True
            logger.debug(f"{symbol}: Warning - negative trend (SMA20 < SMA50)")

    below_200sma = False
    if sma200:
        if spot_price < sma200:
            below_200sma = True
            logger.debug(f"{symbol}: Warning - below 200 SMA")

    # 5. Earnings filter (warning for CC, not exclusion)
    near_earnings = is_near_earnings(earnings_date, exclusion_days=10)
    if near_earnings:
        logger.debug(f"{symbol}: Warning - earnings within 10 days")

    # Select optimal contract
    best_contract = select_cc_contract(options_chain, spot_price)

    if not best_contract:
        log_screening_result(symbol, "CC", "failed - no suitable contracts")
        return None

    # Check if ROI meets target
    if best_contract['roi_annual'] < CC_ANNUALIZED_TARGET:
        log_screening_result(symbol, "CC",
                           f"failed - ROI {best_contract['roi_annual']:.2%} < "
                           f"target {CC_ANNUALIZED_TARGET:.2%}")
        return None

    # Build pick result
    pick = {
        'symbol': symbol,
        'strategy': 'CC',
        'spot_price': spot_price,
        'strike': best_contract['strike'],
        'expiry': best_contract['expiry'],
        'dte': best_contract['dte'],
        'side': 'call',
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
        'iv_rank': iv_rank,
        'iv_percentile': iv_metrics.get('iv_percentile', 0),
        'hv_20': price_data.get('hv_20', 0),
        'hv_60': hv_60,
        'sma20': sma20,
        'sma50': sma50,
        'sma200': sma200,
        'trend_warning': trend_warning,
        'below_200sma': below_200sma,
        'near_earnings': near_earnings,
        'trend_strength': price_data.get('trend_strength', 0),
        'selected_option': f"CALL {best_contract['strike']} {best_contract['expiry']}",
        'notes': []
    }

    # Add warning notes
    if trend_warning:
        pick['notes'].append("⚠️ Negative trend")
    if below_200sma:
        pick['notes'].append("🟡 Below 200 SMA")
    if near_earnings:
        pick['notes'].append("📅 Earnings soon")
    if pick['spread_pct'] > 0.05:
        pick['notes'].append(f"💧 Wide spread {pick['spread_pct']:.1%}")

    # Add positive notes
    if iv_rank > 70:
        pick['notes'].append("🔥 High IV rank")
    if pick['roi_annual'] > 0.20:
        pick['notes'].append("💰 Excellent ROI")
    if pick['oi'] > 1000:
        pick['notes'].append("💧 High liquidity")

    pick['notes'] = '; '.join(pick['notes']) if pick['notes'] else "Standard setup"

    log_screening_result(symbol, "CC", "passed")

    return pick


def screen_multiple_cc(
    symbols_data: Dict[str, Dict[str, Any]],
    options_chains: Dict[str, List[Dict[str, Any]]],
    iv_metrics_data: Dict[str, Dict[str, float]],
    earnings_dates: Dict[str, Optional[date]] = None
) -> List[Dict[str, Any]]:
    """
    Screen multiple symbols for covered call opportunities.

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

        pick = screen_cc(
            symbol,
            price_data,
            options_chains[symbol],
            iv_metrics_data[symbol],
            earnings_dates.get(symbol)
        )

        if pick:
            picks.append(pick)

    # Sort by ROI (will be re-sorted by score later)
    picks.sort(key=lambda x: x['roi_annual'], reverse=True)

    return picks
