import os

POLYGON_API_KEY   = os.getenv("POLYGON_API_KEY", "")
DB_URL            = os.getenv("DATABASE_URL", "sqlite:///data/screener.db")
MARKET_TZ         = os.getenv("MARKET_TIMEZONE", "America/New_York")
RUN_HOUR          = int(os.getenv("SCREENER_RUN_HOUR", "18"))
UNIVERSE_FILE     = os.getenv("UNIVERSE_FILE", "python_app/src/data/universe.csv")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
