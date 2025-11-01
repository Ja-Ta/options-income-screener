"""
Date utilities for the Options Income Screener.

Handles market calendar, trading days, and date calculations.
Python 3.12 compatible following CLAUDE.md standards.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
import pytz


def get_market_tz() -> pytz.timezone:
    """
    Get the market timezone object.

    Returns:
        pytz.timezone: Market timezone (America/New_York)
    """
    return pytz.timezone('America/New_York')


def get_today_market() -> date:
    """
    Get today's date in market timezone.

    Returns:
        date: Today's date in market timezone
    """
    tz = get_market_tz()
    now = datetime.now(tz)
    return now.date()


def is_trading_day(check_date: date) -> bool:
    """
    Check if a date is a trading day (simplified - weekdays only).

    Args:
        check_date: Date to check

    Returns:
        bool: True if trading day (Mon-Fri), False if weekend

    Note:
        This is simplified. Real implementation would check holidays.
    """
    return check_date.weekday() < 5  # Monday=0, Friday=4


def get_next_trading_day(from_date: date) -> date:
    """
    Get the next trading day from a given date.

    Args:
        from_date: Starting date

    Returns:
        date: Next trading day
    """
    next_day = from_date + timedelta(days=1)
    while not is_trading_day(next_day):
        next_day += timedelta(days=1)
    return next_day


def get_previous_trading_day(from_date: date) -> date:
    """
    Get the previous trading day from a given date.

    Args:
        from_date: Starting date

    Returns:
        date: Previous trading day
    """
    prev_day = from_date - timedelta(days=1)
    while not is_trading_day(prev_day):
        prev_day -= timedelta(days=1)
    return prev_day


def calculate_dte(expiry_date: date, from_date: Optional[date] = None) -> int:
    """
    Calculate days to expiration.

    Args:
        expiry_date: Option expiration date
        from_date: Reference date (default: today)

    Returns:
        int: Days to expiration
    """
    if from_date is None:
        from_date = get_today_market()

    delta = expiry_date - from_date
    return max(0, delta.days)


def get_expiry_candidates(
    from_date: Optional[date] = None,
    dte_range: tuple[int, int] = (30, 45)
) -> List[date]:
    """
    Get potential expiration dates within DTE range.

    Args:
        from_date: Reference date (default: today)
        dte_range: (min_dte, max_dte) tuple

    Returns:
        List[date]: Fridays within the DTE range (typical monthly expiries)
    """
    if from_date is None:
        from_date = get_today_market()

    min_dte, max_dte = dte_range
    start_date = from_date + timedelta(days=min_dte)
    end_date = from_date + timedelta(days=max_dte)

    candidates = []
    current = start_date

    while current <= end_date:
        # Options typically expire on Fridays
        if current.weekday() == 4:  # Friday
            candidates.append(current)
        current += timedelta(days=1)

    return candidates


def days_until_earnings(earnings_date: Optional[date], from_date: Optional[date] = None) -> Optional[int]:
    """
    Calculate days until earnings announcement.

    Args:
        earnings_date: Earnings announcement date
        from_date: Reference date (default: today)

    Returns:
        Optional[int]: Days until earnings (negative if past), None if no earnings date
    """
    if earnings_date is None:
        return None

    if from_date is None:
        from_date = get_today_market()

    delta = earnings_date - from_date
    return delta.days


def is_near_earnings(
    earnings_date: Optional[date],
    exclusion_days: int = 10,
    from_date: Optional[date] = None
) -> bool:
    """
    Check if current date is too close to earnings.

    Args:
        earnings_date: Earnings announcement date
        exclusion_days: Days before/after earnings to exclude
        from_date: Reference date (default: today)

    Returns:
        bool: True if within exclusion window, False otherwise
    """
    days_until = days_until_earnings(earnings_date, from_date)

    if days_until is None:
        return False

    return abs(days_until) <= exclusion_days


def format_date_for_display(d: date) -> str:
    """
    Format date for display in alerts and UI.

    Args:
        d: Date to format

    Returns:
        str: Formatted date string (YYYY-MM-DD)
    """
    return d.strftime('%Y-%m-%d')


def parse_date_string(date_str: str) -> date:
    """
    Parse date string to date object.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        date: Parsed date object
    """
    return datetime.strptime(date_str, '%Y-%m-%d').date()