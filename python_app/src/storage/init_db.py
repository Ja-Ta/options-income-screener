"""
Database initialization for the Options Income Screener.

Creates all necessary tables and indexes.
Python 3.12 compatible following CLAUDE.md standards.
"""

from .database import get_database
from ..utils.logging import get_logger


def initialize_database():
    """Create all database tables and indexes if they don't exist."""
    logger = get_logger()
    db = get_database()

    # Create tables
    schema_sql = """
    -- Symbols table
    CREATE TABLE IF NOT EXISTS symbols (
      symbol TEXT PRIMARY KEY,
      name TEXT,
      sector TEXT,
      is_active INTEGER DEFAULT 1,
      last_seen DATE
    );

    -- Prices table
    CREATE TABLE IF NOT EXISTS prices (
      symbol TEXT,
      asof DATE,
      close REAL,
      volume INTEGER,
      sma20 REAL,
      sma50 REAL,
      sma200 REAL,
      hv_20 REAL,
      hv_60 REAL,
      PRIMARY KEY (symbol, asof)
    );

    -- Options table
    CREATE TABLE IF NOT EXISTS options (
      symbol TEXT,
      asof DATE,
      expiry DATE,
      side TEXT CHECK(side IN ('call','put')),
      strike REAL,
      bid REAL,
      ask REAL,
      mid REAL,
      delta REAL,
      iv REAL,
      oi INTEGER,
      vol INTEGER,
      dte INTEGER,
      PRIMARY KEY (symbol, asof, expiry, side, strike)
    );

    -- IV metrics table
    CREATE TABLE IF NOT EXISTS iv_metrics (
      symbol TEXT,
      asof DATE,
      iv_rank REAL,
      iv_percentile REAL,
      PRIMARY KEY (symbol, asof)
    );

    -- Earnings table
    CREATE TABLE IF NOT EXISTS earnings (
      symbol TEXT,
      earnings_date DATE,
      confirmed INTEGER
    );

    -- Picks table
    CREATE TABLE IF NOT EXISTS picks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      asof DATE,
      symbol TEXT,
      strategy TEXT CHECK(strategy IN ('CC','CSP')),
      selected_option TEXT,
      strike REAL,
      expiry DATE,
      premium REAL,
      roi_30d REAL,
      iv_rank REAL,
      score REAL,
      notes TEXT
    );

    -- Rationales table
    CREATE TABLE IF NOT EXISTS rationales (
      pick_id INTEGER,
      summary TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (pick_id) REFERENCES picks(id)
    );

    -- Alerts table
    CREATE TABLE IF NOT EXISTS alerts (
      pick_id INTEGER,
      channel TEXT,
      status TEXT,
      sent_at DATETIME,
      error TEXT
    );
    """

    # Create indexes
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_prices_asof ON prices(asof);
    CREATE INDEX IF NOT EXISTS idx_options_symbol_asof ON options(symbol, asof);
    CREATE INDEX IF NOT EXISTS idx_picks_asof ON picks(asof);
    """

    try:
        # Execute schema creation
        with db.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.executescript(index_sql)
            conn.commit()

        logger.info("Database tables and indexes created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


if __name__ == "__main__":
    # Initialize database when run directly
    from ..utils.logging import setup_logger
    setup_logger()
    if initialize_database():
        print("✅ Database initialized successfully")
    else:
        print("❌ Database initialization failed")