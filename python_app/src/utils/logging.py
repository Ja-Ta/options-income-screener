"""
Logging utilities for the Options Income Screener.

Provides consistent logging configuration across the application.
Python 3.12 compatible following CLAUDE.md standards.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "screener",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional log file path
        format_string: Optional custom format string

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers = []

    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "screener") -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def log_execution_time(func):
    """
    Decorator to log function execution time.

    Args:
        func: Function to decorate

    Returns:
        Wrapped function with timing
    """
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = datetime.now()

        logger.debug(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Completed {func.__name__} in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Failed {func.__name__} after {elapsed:.2f}s: {str(e)}")
            raise

    return wrapper


def log_api_call(service: str, endpoint: str, params: dict = None):
    """
    Log an API call for tracking.

    Args:
        service: API service name (e.g., "Polygon", "Claude")
        endpoint: API endpoint being called
        params: Optional parameters being sent
    """
    logger = get_logger()
    if params:
        logger.debug(f"API Call - {service}: {endpoint} with params: {params}")
    else:
        logger.debug(f"API Call - {service}: {endpoint}")


def log_error(error: Exception, context: str = ""):
    """
    Log an error with context.

    Args:
        error: Exception that occurred
        context: Additional context about where/why error occurred
    """
    logger = get_logger()
    if context:
        logger.error(f"{context}: {type(error).__name__}: {str(error)}")
    else:
        logger.error(f"{type(error).__name__}: {str(error)}")


def log_screening_result(symbol: str, strategy: str, result: str):
    """
    Log screening results for audit trail.

    Args:
        symbol: Stock symbol
        strategy: Strategy type (CC or CSP)
        result: Screening result (passed/failed/error)
    """
    logger = get_logger()
    logger.info(f"Screening - {symbol} {strategy}: {result}")


def log_pick(symbol: str, strategy: str, score: float, roi: float):
    """
    Log a successful pick.

    Args:
        symbol: Stock symbol
        strategy: Strategy type (CC or CSP)
        score: Calculated score
        roi: ROI (30-day)
    """
    logger = get_logger()
    logger.info(f"Pick - {symbol} {strategy}: Score={score:.2f}, ROI={roi:.2%}")


def log_alert(channel: str, status: str, message: str = ""):
    """
    Log alert delivery status.

    Args:
        channel: Alert channel (Telegram, etc.)
        status: Delivery status (sent/failed)
        message: Optional status message
    """
    logger = get_logger()
    if message:
        logger.info(f"Alert - {channel}: {status} - {message}")
    else:
        logger.info(f"Alert - {channel}: {status}")


def create_daily_log_file() -> str:
    """
    Create a daily log file path.

    Returns:
        str: Path to daily log file
    """
    today = datetime.now().strftime('%Y%m%d')
    return f"data/logs/screener_{today}.log"


def initialize_logging(debug: bool = False):
    """
    Initialize logging for the application.

    Args:
        debug: Whether to enable debug logging
    """
    level = logging.DEBUG if debug else logging.INFO
    log_file = create_daily_log_file()

    # Setup main logger
    setup_logger(
        name="screener",
        level=level,
        log_file=log_file
    )

    # Setup specialized loggers
    setup_logger(
        name="screener.api",
        level=level,
        log_file=log_file
    )

    setup_logger(
        name="screener.db",
        level=level,
        log_file=log_file
    )

    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Options Income Screener - Session Started")
    logger.info(f"Log Level: {'DEBUG' if debug else 'INFO'}")
    logger.info("=" * 60)