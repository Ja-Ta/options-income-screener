#!/usr/bin/env python3
"""
Populate database with sample data for testing the dashboard.
"""

import sqlite3
from datetime import date, timedelta
import random

def populate_sample_data():
    """Add sample picks to the database."""
    print("\n" + "="*60)
    print("POPULATING SAMPLE DATA")
    print("="*60)

    # Connect to database
    conn = sqlite3.connect("python_app/data/screener.db")
    cursor = conn.cursor()

    # Sample data
    symbols = ['SPY', 'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'META', 'NVDA']
    today = date.today()

    print("\n📝 Adding sample picks...")

    picks_added = 0
    for symbol in symbols:
        # Add some CC picks
        for i in range(2):
            stock_price = random.uniform(100, 500)
            strike = stock_price * random.uniform(1.02, 1.05)
            expiry = today + timedelta(days=random.randint(30, 45))

            cursor.execute('''
                INSERT INTO picks (
                    date, asof, symbol, strategy, strike, expiry,
                    premium, stock_price, roi_30d, annualized_return,
                    iv_rank, score, trend, earnings_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                today, today, symbol, 'CC',
                round(strike, 2), expiry,
                round(random.uniform(1, 5), 2),
                round(stock_price, 2),
                random.uniform(0.005, 0.02),
                random.uniform(0.10, 0.20),
                random.uniform(40, 80),
                random.uniform(0.5, 0.9),
                'uptrend' if random.random() > 0.5 else 'neutral',
                random.randint(20, 60)
            ))
            picks_added += 1

        # Add some CSP picks
        for i in range(2):
            stock_price = random.uniform(100, 500)
            strike = stock_price * random.uniform(0.95, 0.98)
            expiry = today + timedelta(days=random.randint(30, 45))

            cursor.execute('''
                INSERT INTO picks (
                    date, asof, symbol, strategy, strike, expiry,
                    premium, stock_price, roi_30d, annualized_return,
                    iv_rank, score, trend, earnings_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                today, today, symbol, 'CSP',
                round(strike, 2), expiry,
                round(random.uniform(1, 4), 2),
                round(stock_price, 2),
                random.uniform(0.004, 0.015),
                random.uniform(0.08, 0.15),
                random.uniform(45, 85),
                random.uniform(0.5, 0.85),
                'neutral' if random.random() > 0.5 else 'downtrend',
                random.randint(20, 60)
            ))
            picks_added += 1

    # Commit changes
    conn.commit()
    print(f"  ✅ Added {picks_added} sample picks")

    # Also copy to Node.js database location
    conn2 = sqlite3.connect("data/screener.db")
    cursor2 = conn2.cursor()

    # Copy picks
    cursor.execute("SELECT * FROM picks")
    rows = cursor.fetchall()

    cursor2.execute("DELETE FROM picks")  # Clear existing
    cursor2.executemany('''
        INSERT INTO picks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', rows)

    conn2.commit()
    print("  ✅ Synced to Node.js database")

    conn.close()
    conn2.close()

    print("\n" + "="*60)
    print("✅ SAMPLE DATA POPULATED!")
    print("="*60)
    print(f"\n🎉 Added {picks_added} sample picks to the database")
    print("\n📊 Check your dashboard at: http://157.245.214.224:3000")

if __name__ == "__main__":
    populate_sample_data()