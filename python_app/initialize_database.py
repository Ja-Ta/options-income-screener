#!/usr/bin/env python3
"""
Initialize the database with required tables.
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def initialize_database():
    """Create all required database tables."""
    print("\n" + "="*60)
    print("DATABASE INITIALIZATION")
    print("="*60)

    # Create data directory if it doesn't exist
    data_dir = Path("python_app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n✅ Data directory: {data_dir.absolute()}")

    # Database path
    db_path = data_dir / "screener.db"
    print(f"📁 Database path: {db_path.absolute()}")

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    # Create tables
    print("\n🔨 Creating tables...")

    # 1. Symbols table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            last_seen DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ Created 'symbols' table")

    # 2. Daily prices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL NOT NULL,
            volume REAL,
            sma_20 REAL,
            sma_50 REAL,
            sma_200 REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
    ''')
    print("  ✅ Created 'daily_prices' table")

    # 3. Options chains table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS options_chains (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            contract_type TEXT NOT NULL,
            strike REAL NOT NULL,
            expiry DATE NOT NULL,
            bid REAL,
            ask REAL,
            mid REAL,
            volume INTEGER,
            open_interest INTEGER,
            implied_volatility REAL,
            delta REAL,
            gamma REAL,
            theta REAL,
            vega REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ Created 'options_chains' table")

    # 4. Picks table (main results)
    # Drop existing table if it has wrong schema
    cursor.execute('DROP TABLE IF EXISTS picks')
    cursor.execute('''
        CREATE TABLE picks (
            id INTEGER PRIMARY KEY,
            date DATE NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            strike REAL NOT NULL,
            expiry DATE NOT NULL,
            premium REAL NOT NULL,
            stock_price REAL,
            roi_30d REAL,
            annualized_return REAL,
            iv_rank REAL,
            score REAL,
            rationale TEXT,
            trend TEXT,
            earnings_days INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ Created 'picks' table")

    # 5. Run history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY,
            run_date DATE NOT NULL,
            symbols_processed INTEGER,
            cc_picks INTEGER,
            csp_picks INTEGER,
            alerts_sent INTEGER,
            duration_seconds REAL,
            status TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ Created 'run_history' table")

    # Create view for backward compatibility
    cursor.execute('''
        CREATE VIEW IF NOT EXISTS picks_view AS
        SELECT *, date as asof FROM picks
    ''')
    print("  ✅ Created 'picks_view' for compatibility")

    # Create indexes for performance
    print("\n📊 Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_picks_date ON picks(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_picks_symbol ON picks(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_picks_strategy ON picks(strategy)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_picks_score ON picks(score DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date)')
    print("  ✅ Created performance indexes")

    # Insert some test symbols
    print("\n📝 Inserting initial symbols...")
    test_symbols = [
        ('SPY', 'SPDR S&P 500 ETF Trust', 'ETF', 'Large Cap'),
        ('QQQ', 'Invesco QQQ Trust', 'ETF', 'Tech'),
        ('AAPL', 'Apple Inc', 'Technology', 'Consumer Electronics'),
        ('MSFT', 'Microsoft Corporation', 'Technology', 'Software'),
        ('GOOGL', 'Alphabet Inc', 'Technology', 'Internet'),
        ('TSLA', 'Tesla Inc', 'Consumer Cyclical', 'Auto Manufacturers'),
        ('AMZN', 'Amazon.com Inc', 'Technology', 'E-Commerce'),
        ('META', 'Meta Platforms Inc', 'Technology', 'Social Media'),
        ('NVDA', 'NVIDIA Corporation', 'Technology', 'Semiconductors'),
        ('AMD', 'Advanced Micro Devices', 'Technology', 'Semiconductors')
    ]

    for symbol, name, sector, industry in test_symbols:
        cursor.execute('''
            INSERT OR IGNORE INTO symbols (symbol, name, sector, industry, last_seen)
            VALUES (?, ?, ?, ?, date('now'))
        ''', (symbol, name, sector, industry))

    print(f"  ✅ Inserted {len(test_symbols)} symbols")

    # Commit changes
    conn.commit()
    conn.close()

    # Verify database
    print("\n✅ Database initialized successfully!")
    print(f"   Location: {db_path.absolute()}")
    print(f"   Size: {db_path.stat().st_size:,} bytes")

    # Also create the Node.js expected location
    node_db_dir = Path("data")
    node_db_dir.mkdir(exist_ok=True)
    node_db_path = node_db_dir / "screener.db"

    if not node_db_path.exists():
        print("\n🔄 Creating symlink for Node.js...")
        try:
            import shutil
            shutil.copy2(str(db_path), str(node_db_path))
            print(f"   ✅ Database copied to: {node_db_path.absolute()}")
        except Exception as e:
            print(f"   ⚠️ Could not copy database: {e}")

    print("\n" + "="*60)
    print("DATABASE READY!")
    print("="*60)

if __name__ == "__main__":
    initialize_database()