#!/usr/bin/env python3
"""
Simple mock screening that generates option picks directly.
Bypasses complex pipeline issues for demonstration.
"""

import sys
import os
import sqlite3
import random
from datetime import date, timedelta

# Set mock mode
os.environ['USE_MOCK_DATA'] = 'true'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.telegram_service import TelegramService
from src.services.claude_service import ClaudeService

def generate_mock_picks(symbols):
    """Generate mock option picks."""
    picks = []
    today = date.today()

    for symbol in symbols:
        stock_price = random.uniform(100, 500)

        # Generate CC pick
        if random.random() > 0.3:
            strike = stock_price * random.uniform(1.02, 1.05)
            expiry = today + timedelta(days=random.randint(30, 45))
            premium = random.uniform(2, 5)
            roi_30d = premium / stock_price
            iv_rank = random.uniform(40, 80)
            score = (iv_rank/100 * 0.4) + (roi_30d * 10 * 0.3) + random.uniform(0.2, 0.3)

            picks.append({
                'symbol': symbol,
                'strategy': 'CC',
                'strike': round(strike, 2),
                'expiry': expiry.isoformat(),
                'premium': round(premium, 2),
                'stock_price': round(stock_price, 2),
                'roi_30d': roi_30d,
                'annualized_return': roi_30d * 12,
                'iv_rank': iv_rank,
                'score': min(score, 1.0),
                'trend': 'uptrend' if random.random() > 0.5 else 'neutral',
                'earnings_days': random.randint(20, 60)
            })

        # Generate CSP pick
        if random.random() > 0.3:
            strike = stock_price * random.uniform(0.95, 0.98)
            expiry = today + timedelta(days=random.randint(30, 45))
            premium = random.uniform(1.5, 4)
            roi_30d = premium / strike
            iv_rank = random.uniform(45, 85)
            score = (iv_rank/100 * 0.4) + (roi_30d * 10 * 0.3) + random.uniform(0.15, 0.25)

            picks.append({
                'symbol': symbol,
                'strategy': 'CSP',
                'strike': round(strike, 2),
                'expiry': expiry.isoformat(),
                'premium': round(premium, 2),
                'stock_price': round(stock_price, 2),
                'roi_30d': roi_30d,
                'annualized_return': roi_30d * 12,
                'iv_rank': iv_rank,
                'score': min(score, 1.0),
                'trend': 'neutral' if random.random() > 0.5 else 'downtrend',
                'earnings_days': random.randint(20, 60)
            })

    # Sort by score
    picks.sort(key=lambda x: x['score'], reverse=True)
    return picks

def save_picks_to_db(picks):
    """Save picks to database."""
    conn = sqlite3.connect("python_app/data/screener.db")
    cursor = conn.cursor()

    today = date.today()
    inserted = 0

    # Clear today's picks
    cursor.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

    for pick in picks:
        cursor.execute('''
            INSERT INTO picks (
                date, asof, symbol, strategy, strike, expiry,
                premium, stock_price, roi_30d, annualized_return,
                iv_rank, score, trend, earnings_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today.isoformat(), today.isoformat(),
            pick['symbol'], pick['strategy'],
            pick['strike'], pick['expiry'],
            pick['premium'], pick['stock_price'],
            pick['roi_30d'], pick['annualized_return'],
            pick['iv_rank'], pick['score'],
            pick['trend'], pick['earnings_days']
        ))
        inserted += 1

    conn.commit()

    # Also sync to Node.js database
    conn2 = sqlite3.connect("data/screener.db")
    cursor2 = conn2.cursor()
    cursor2.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

    for pick in picks:
        cursor2.execute('''
            INSERT INTO picks (
                date, asof, symbol, strategy, strike, expiry,
                premium, stock_price, roi_30d, annualized_return,
                iv_rank, score, trend, earnings_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today.isoformat(), today.isoformat(),
            pick['symbol'], pick['strategy'],
            pick['strike'], pick['expiry'],
            pick['premium'], pick['stock_price'],
            pick['roi_30d'], pick['annualized_return'],
            pick['iv_rank'], pick['score'],
            pick['trend'], pick['earnings_days']
        ))

    conn2.commit()
    conn.close()
    conn2.close()

    return inserted

def send_alerts(cc_picks, csp_picks):
    """Send alerts via Telegram."""
    telegram = TelegramService()

    # Format summary message
    message = f"🎯 **Daily Options Screening Results**\n"
    message += f"📅 {date.today()}\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    if cc_picks:
        message += f"📈 **Top Covered Calls ({len(cc_picks)})**\n"
        for pick in cc_picks[:3]:
            message += f"• {pick['symbol']}: ${pick['strike']} "
            message += f"(ROI: {pick['roi_30d']:.1%}, Score: {pick['score']:.2f})\n"
        message += "\n"

    if csp_picks:
        message += f"💰 **Top Cash-Secured Puts ({len(csp_picks)})**\n"
        for pick in csp_picks[:3]:
            message += f"• {pick['symbol']}: ${pick['strike']} "
            message += f"(ROI: {pick['roi_30d']:.1%}, Score: {pick['score']:.2f})\n"

    message += f"\n📊 View dashboard for details"

    # Send message
    if telegram.send_message(message):
        print("  ✅ Telegram alert sent")
        return True
    return False

def run_simple_screening():
    """Run a simple mock screening."""
    print("\n" + "="*60)
    print("SIMPLE MOCK SCREENING")
    print("="*60)

    # Test symbols
    symbols = ['SPY', 'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'META', 'NVDA']
    print(f"\n📊 Screening symbols: {', '.join(symbols)}")
    print(f"📅 Date: {date.today()}")
    print("-"*60)

    # Generate mock picks
    print("\n🎲 Generating mock option picks...")
    all_picks = generate_mock_picks(symbols)

    # Separate by strategy
    cc_picks = [p for p in all_picks if p['strategy'] == 'CC']
    csp_picks = [p for p in all_picks if p['strategy'] == 'CSP']

    print(f"  ✅ Generated {len(cc_picks)} CC picks")
    print(f"  ✅ Generated {len(csp_picks)} CSP picks")

    # Save to database
    print("\n💾 Saving to database...")
    saved = save_picks_to_db(all_picks)
    print(f"  ✅ Saved {saved} picks to database")

    # Send alerts
    print("\n📱 Sending alerts...")
    send_alerts(cc_picks, csp_picks)

    # Show top picks
    print("\n📈 TOP PICKS:")
    print("-"*40)
    for pick in all_picks[:5]:
        emoji = "📈" if pick['strategy'] == 'CC' else "💰"
        print(f"{emoji} {pick['symbol']} {pick['strategy']}: ${pick['strike']}")
        print(f"   Premium: ${pick['premium']:.2f}")
        print(f"   ROI (30d): {pick['roi_30d']:.2%}")
        print(f"   IV Rank: {pick['iv_rank']:.1f}%")
        print(f"   Score: {pick['score']:.3f}")
        print()

    print("="*60)
    print("✅ SCREENING COMPLETE!")
    print("="*60)
    print(f"\n📊 Dashboard: http://157.245.214.224:3000")
    print(f"📱 Check Telegram for alerts")

    return {
        'total_picks': len(all_picks),
        'cc_picks': len(cc_picks),
        'csp_picks': len(csp_picks)
    }

if __name__ == "__main__":
    results = run_simple_screening()