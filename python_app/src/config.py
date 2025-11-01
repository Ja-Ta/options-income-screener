"""
Configuration for the Options Income Screener.

Loads settings from environment variables with sensible defaults.
Python 3.12 compatible following CLAUDE.md standards.
"""

import os
from pathlib import Path

# API Keys
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "mock_api_key")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "mock_claude_key")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_telegram_token")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Database
DB_URL = os.getenv("DATABASE_URL", "data/screener.db")
MARKET_TZ = os.getenv("MARKET_TIMEZONE", "America/New_York")

# Screening schedule
RUN_HOUR = int(os.getenv("SCREENER_RUN_HOUR", "18"))
UNIVERSE_FILE = os.getenv("UNIVERSE_FILE", "python_app/src/data/universe.csv")

# Feature flags
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
CC_ENABLED = os.getenv("CC_ENABLED", "true").lower() == "true"
CSP_ENABLED = os.getenv("CSP_ENABLED", "true").lower() == "true"
CLAUDE_ENABLED = os.getenv("CLAUDE_ENABLED", "true").lower() == "true"
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"

# Default symbols for testing
DEFAULT_SYMBOLS = os.getenv("DEFAULT_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,TSLA,SPY,QQQ,IWM,DIA,META").split(",")

# Alert settings
MAX_PICKS_TO_ALERT = int(os.getenv("MAX_PICKS_TO_ALERT", "10"))
