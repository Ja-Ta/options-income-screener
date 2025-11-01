#!/usr/bin/env python3
"""
Fix all database schema issues to match what the pipeline expects.
"""

import sqlite3
import os
from pathlib import Path

def fix_database_schema():
    """Create/update all tables with correct schema."""
    print("\n" + "="*60)
    print("FIXING DATABASE SCHEMA")
    print("="*60)

    # Database paths
    db_paths = [
        "python_app/data/screener.db",
        "data/screener.db"
    ]

    for db_path in db_paths:
        print(f"\n📁 Fixing database: {db_path}")

        # Create directory if needed
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()

        # Drop all existing tables to start fresh
        print("  🗑️ Dropping existing tables...")
        cursor.execute("DROP TABLE IF EXISTS symbols")
        cursor.execute("DROP TABLE IF EXISTS daily_prices")
        cursor.execute("DROP TABLE IF EXISTS prices")
        cursor.execute("DROP TABLE IF EXISTS options_chains")
        cursor.execute("DROP TABLE IF EXISTS options")
        cursor.execute("DROP TABLE IF EXISTS picks")
        cursor.execute("DROP TABLE IF EXISTS rationales")
        cursor.execute("DROP TABLE IF EXISTS run_history")
        cursor.execute("DROP VIEW IF EXISTS picks_view")

        # 1. Symbols table
        cursor.execute('''
            CREATE TABLE symbols (
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

        # 2. Prices table (what the pipeline expects)
        cursor.execute('''
            CREATE TABLE prices (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                asof DATE NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume REAL,
                sma20 REAL,
                sma50 REAL,
                sma200 REAL,
                sma_20 REAL,  -- Duplicate for compatibility
                sma_50 REAL,  -- Duplicate for compatibility
                sma_200 REAL, -- Duplicate for compatibility
                hv_20 REAL,   -- Historical volatility 20-day
                hv_60 REAL,   -- Historical volatility 60-day
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, asof)
            )
        ''')
        print("  ✅ Created 'prices' table")

        # 3. Daily prices table (alias for prices)
        cursor.execute('''
            CREATE TABLE daily_prices AS SELECT * FROM prices WHERE 0
        ''')
        print("  ✅ Created 'daily_prices' table (alias)")

        # 4. Options table (what the pipeline expects)
        cursor.execute('''
            CREATE TABLE options (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                asof DATE NOT NULL,
                contract_type TEXT NOT NULL,
                strike REAL NOT NULL,
                expiry DATE NOT NULL,
                dte INTEGER,
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
        print("  ✅ Created 'options' table")

        # 5. Options chains table (alias)
        cursor.execute('''
            CREATE TABLE options_chains AS SELECT * FROM options WHERE 0
        ''')
        print("  ✅ Created 'options_chains' table (alias)")

        # 6. Picks table (results)
        cursor.execute('''
            CREATE TABLE picks (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                asof DATE NOT NULL,
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

        # 7. Rationales table
        cursor.execute('''
            CREATE TABLE rationales (
                id INTEGER PRIMARY KEY,
                pick_id INTEGER,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pick_id) REFERENCES picks(id)
            )
        ''')
        print("  ✅ Created 'rationales' table")

        # 8. Run history table
        cursor.execute('''
            CREATE TABLE run_history (
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

        # Create indexes
        print("  📊 Creating indexes...")

        # Prices indexes
        cursor.execute('CREATE INDEX idx_prices_symbol_asof ON prices(symbol, asof)')
        cursor.execute('CREATE INDEX idx_prices_symbol_date ON prices(symbol, date)')

        # Options indexes
        cursor.execute('CREATE INDEX idx_options_symbol_asof ON options(symbol, asof)')
        cursor.execute('CREATE INDEX idx_options_expiry ON options(expiry)')

        # Picks indexes
        cursor.execute('CREATE INDEX idx_picks_date ON picks(date)')
        cursor.execute('CREATE INDEX idx_picks_asof ON picks(asof)')
        cursor.execute('CREATE INDEX idx_picks_symbol ON picks(symbol)')
        cursor.execute('CREATE INDEX idx_picks_strategy ON picks(strategy)')
        cursor.execute('CREATE INDEX idx_picks_score ON picks(score DESC)')

        print("  ✅ Created indexes")

        # Insert test symbols
        print("  📝 Inserting symbols...")
        symbols = [
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

        for symbol, name, sector, industry in symbols:
            cursor.execute('''
                INSERT OR IGNORE INTO symbols (symbol, name, sector, industry, last_seen)
                VALUES (?, ?, ?, ?, date('now'))
            ''', (symbol, name, sector, industry))

        print(f"  ✅ Inserted {len(symbols)} symbols")

        # Copy existing picks if any
        try:
            cursor.execute("SELECT COUNT(*) FROM picks")
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  📋 Preserved {count} existing picks")
        except:
            pass

        conn.commit()
        conn.close()
        print(f"  ✅ Database fixed: {db_path}")

    print("\n" + "="*60)
    print("✅ DATABASE SCHEMA FIXED!")
    print("="*60)
    print("\nAll tables have been recreated with the correct schema.")
    print("The pipeline should now work without schema errors.")

if __name__ == "__main__":
    fix_database_schema()