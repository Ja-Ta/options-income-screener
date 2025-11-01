#!/usr/bin/env python3
"""
Hybrid screening using real stock prices with estimated option premiums.
Works with Polygon free tier limitations.
"""

import sys
import os
import sqlite3
import time
import requests
import random
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import math

# Set to use real data where possible
os.environ['USE_MOCK_DATA'] = 'false'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.telegram_service import TelegramService
from src.services.claude_service import ClaudeService
from src.utils.logging import setup_logger, get_logger

# Setup logging
setup_logger()
logger = get_logger()

class HybridDataClient:
    """Client that uses real stock prices with estimated options."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.rate_limit_delay = 12  # 5 calls/minute for free tier
        self.last_call = 0

    def _rate_limit(self):
        """Enforce rate limiting for free tier."""
        elapsed = time.time() - self.last_call
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_call = time.time()

    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get real stock data from Polygon."""
        self._rate_limit()

        try:
            # Get previous close
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
            params = {"apiKey": self.api_key}

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    result = data['results'][0]

                    # Calculate historical volatility estimate
                    daily_change = abs(result['h'] - result['l']) / result['c']
                    hv_estimate = daily_change * math.sqrt(252)  # Annualized

                    return {
                        'symbol': symbol,
                        'close': result['c'],
                        'open': result['o'],
                        'high': result['h'],
                        'low': result['l'],
                        'volume': result['v'],
                        'timestamp': datetime.fromtimestamp(result['t']/1000),
                        'hv_estimate': hv_estimate
                    }
            else:
                logger.warning(f"Failed to get data for {symbol}: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")

        return None

    def get_market_iv_estimate(self, symbol: str) -> float:
        """Estimate current IV based on symbol and market conditions."""
        # Base IV by symbol type
        iv_base = {
            'SPY': 0.15,
            'QQQ': 0.18,
            'IWM': 0.20,
            'AAPL': 0.25,
            'MSFT': 0.22,
            'GOOGL': 0.24,
            'AMZN': 0.28,
            'TSLA': 0.45,
            'META': 0.35,
            'NVDA': 0.40
        }

        base_iv = iv_base.get(symbol, 0.25)

        # Add some randomness for market conditions
        market_adjustment = random.uniform(-0.05, 0.10)

        return max(0.10, min(0.60, base_iv + market_adjustment))

    def estimate_option_premium(self, stock_price: float, strike: float, dte: int,
                               option_type: str, iv: float) -> Dict:
        """Estimate option premium using simplified Black-Scholes approximation."""

        # Time to expiration in years
        t = dte / 365

        # Risk-free rate (simplified)
        r = 0.05

        # Moneyness
        moneyness = strike / stock_price

        # Simplified premium estimation
        if option_type == 'call':
            intrinsic = max(0, stock_price - strike)
            if moneyness > 1:  # OTM
                # Time value decreases as we go further OTM
                otm_factor = max(0, 1 - (moneyness - 1) * 10)
                time_value = stock_price * iv * math.sqrt(t) * otm_factor * 0.4
            else:  # ITM
                time_value = stock_price * iv * math.sqrt(t) * 0.3
        else:  # put
            intrinsic = max(0, strike - stock_price)
            if moneyness < 1:  # OTM
                # Time value decreases as we go further OTM
                otm_factor = max(0, 1 - (1 - moneyness) * 10)
                time_value = stock_price * iv * math.sqrt(t) * otm_factor * 0.4
            else:  # ITM
                time_value = stock_price * iv * math.sqrt(t) * 0.3

        premium = intrinsic + time_value

        # Estimate bid-ask spread
        spread_pct = 0.05 if stock_price > 100 else 0.08
        spread = premium * spread_pct

        bid = round(premium - spread/2, 2)
        ask = round(premium + spread/2, 2)
        mid = round(premium, 2)

        # Estimate delta
        if option_type == 'call':
            if moneyness < 0.95:
                delta = 0.7
            elif moneyness < 1.0:
                delta = 0.5
            elif moneyness < 1.05:
                delta = 0.3
            else:
                delta = 0.2
        else:
            if moneyness < 0.95:
                delta = -0.2
            elif moneyness < 1.0:
                delta = -0.3
            elif moneyness < 1.05:
                delta = -0.5
            else:
                delta = -0.7

        return {
            'bid': max(0.01, bid),
            'ask': max(0.01, ask),
            'mid': max(0.01, mid),
            'delta': delta,
            'iv': iv
        }

def generate_option_candidates(stock_price: float, strategy: str) -> List[Dict]:
    """Generate potential option strikes and expirations."""
    candidates = []

    # Strike increments
    if stock_price > 500:
        increment = 10
    elif stock_price > 100:
        increment = 5
    elif stock_price > 50:
        increment = 2.5
    else:
        increment = 1

    # Generate strikes
    if strategy == 'CC':
        # OTM calls: 1-5% above stock price
        start_strike = math.ceil(stock_price * 1.01 / increment) * increment
        for i in range(5):
            strike = start_strike + (i * increment)
            if strike > stock_price * 1.10:
                break

            # Generate multiple expirations
            for dte in [30, 35, 40, 45]:
                expiry = date.today() + timedelta(days=dte)
                candidates.append({
                    'strike': strike,
                    'expiry': expiry,
                    'dte': dte,
                    'type': 'call'
                })

    else:  # CSP
        # OTM puts: 1-5% below stock price
        start_strike = math.floor(stock_price * 0.99 / increment) * increment
        for i in range(5):
            strike = start_strike - (i * increment)
            if strike < stock_price * 0.90:
                break

            # Generate multiple expirations
            for dte in [30, 35, 40, 45]:
                expiry = date.today() + timedelta(days=dte)
                candidates.append({
                    'strike': strike,
                    'expiry': expiry,
                    'dte': dte,
                    'type': 'put'
                })

    return candidates

def screen_symbol(symbol: str, client: HybridDataClient) -> List[Dict]:
    """Screen a symbol for option opportunities."""
    picks = []

    # Get real stock data
    stock_data = client.get_stock_data(symbol)
    if not stock_data:
        logger.warning(f"No stock data for {symbol}")
        return picks

    stock_price = stock_data['close']

    # Get IV estimate
    current_iv = client.get_market_iv_estimate(symbol)

    # Calculate IV rank (estimated)
    iv_rank = 40 + random.uniform(0, 40)  # Assume moderate to high IV rank

    # Generate and evaluate covered call candidates
    cc_candidates = generate_option_candidates(stock_price, 'CC')
    for candidate in cc_candidates[:3]:  # Limit to top 3
        option_data = client.estimate_option_premium(
            stock_price, candidate['strike'], candidate['dte'], 'call', current_iv
        )

        premium = option_data['bid']
        roi_30d = premium / stock_price

        # Calculate score
        score = (
            (iv_rank / 100) * 0.4 +
            min(roi_30d * 50, 1.0) * 0.3 +
            (abs(option_data['delta']) * 0.3)
        )

        picks.append({
            'symbol': symbol,
            'strategy': 'CC',
            'strike': round(candidate['strike'], 2),
            'expiry': candidate['expiry'].isoformat(),
            'dte': candidate['dte'],
            'premium': premium,
            'stock_price': round(stock_price, 2),
            'roi_30d': roi_30d,
            'annualized_return': roi_30d * (365 / 30),
            'iv': current_iv,
            'iv_rank': iv_rank,
            'delta': option_data['delta'],
            'score': min(score, 1.0),
            'bid': option_data['bid'],
            'ask': option_data['ask'],
            'spread': option_data['ask'] - option_data['bid'],
            'trend': 'neutral',
            'earnings_days': 45,
            'data_type': 'hybrid'  # Mark as hybrid data
        })

    # Generate and evaluate cash-secured put candidates
    csp_candidates = generate_option_candidates(stock_price, 'CSP')
    for candidate in csp_candidates[:3]:  # Limit to top 3
        option_data = client.estimate_option_premium(
            stock_price, candidate['strike'], candidate['dte'], 'put', current_iv
        )

        premium = option_data['bid']
        roi_30d = premium / candidate['strike']

        # Calculate score
        score = (
            (iv_rank / 100) * 0.4 +
            min(roi_30d * 50, 1.0) * 0.3 +
            (abs(option_data['delta']) * 0.3)
        )

        picks.append({
            'symbol': symbol,
            'strategy': 'CSP',
            'strike': round(candidate['strike'], 2),
            'expiry': candidate['expiry'].isoformat(),
            'dte': candidate['dte'],
            'premium': premium,
            'stock_price': round(stock_price, 2),
            'roi_30d': roi_30d,
            'annualized_return': roi_30d * (365 / 30),
            'iv': current_iv,
            'iv_rank': iv_rank,
            'delta': option_data['delta'],
            'score': min(score, 1.0),
            'bid': option_data['bid'],
            'ask': option_data['ask'],
            'spread': option_data['ask'] - option_data['bid'],
            'trend': 'neutral',
            'earnings_days': 45,
            'data_type': 'hybrid'  # Mark as hybrid data
        })

    return picks

def save_picks_to_db(picks: List[Dict]) -> int:
    """Save picks to database."""
    conn = sqlite3.connect("python_app/data/screener.db")
    cursor = conn.cursor()

    today = date.today()
    inserted = 0

    # Clear today's picks
    cursor.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

    for pick in picks:
        try:
            cursor.execute('''
                INSERT INTO picks (
                    date, asof, symbol, strategy, strike, expiry,
                    premium, stock_price, roi_30d, annualized_return,
                    iv_rank, score, trend, earnings_days, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                today.isoformat(), today.isoformat(),
                pick['symbol'], pick['strategy'],
                pick['strike'], pick['expiry'],
                pick['premium'], pick['stock_price'],
                pick['roi_30d'], pick['annualized_return'],
                pick['iv_rank'], pick['score'],
                pick['trend'], pick['earnings_days'],
                pick.get('rationale', f"Hybrid analysis: Real stock price with estimated {pick['iv']:.1%} IV")
            ))
            inserted += 1
        except Exception as e:
            logger.error(f"Error inserting pick: {e}")

    conn.commit()

    # Sync to Node.js database
    try:
        conn2 = sqlite3.connect("data/screener.db")
        cursor2 = conn2.cursor()
        cursor2.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

        cursor.execute("SELECT * FROM picks WHERE date = ?", (today.isoformat(),))
        rows = cursor.fetchall()

        if rows:
            placeholders = ','.join(['?'] * len(rows[0]))
            cursor2.executemany(f'INSERT INTO picks VALUES ({placeholders})', rows)

        conn2.commit()
        conn2.close()
    except Exception as e:
        logger.error(f"Error syncing to Node.js DB: {e}")

    conn.close()
    return inserted

def run_hybrid_screening(symbols: List[str] = None):
    """Run hybrid screening with real stock prices and estimated options."""
    print("\n" + "="*60)
    print("HYBRID SCREENING (Real Prices + Estimated Options)")
    print("="*60)

    # Default symbols
    if not symbols:
        symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT']

    print(f"\n📊 Screening symbols: {', '.join(symbols)}")
    print(f"📅 Date: {date.today()}")
    print("🔄 Mode: Real stock prices with estimated option premiums")
    print("-"*60)

    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key or api_key.startswith('mock'):
        print("❌ Valid Polygon API key required")
        return None

    # Initialize client
    client = HybridDataClient(api_key)
    all_picks = []

    # Process each symbol
    for symbol in symbols:
        print(f"\n📈 Processing {symbol}...")

        # Screen the symbol
        picks = screen_symbol(symbol, client)

        if picks:
            print(f"  ✅ Generated {len(picks)} potential picks")
            print(f"  📊 Stock price: ${picks[0]['stock_price']:.2f}")
            print(f"  📈 Estimated IV: {picks[0]['iv']:.1%}")
            all_picks.extend(picks)
        else:
            print(f"  ❌ Failed to generate picks")

    # Sort by score
    all_picks.sort(key=lambda x: x['score'], reverse=True)

    # Filter to top picks only
    all_picks = all_picks[:20]  # Keep top 20

    # Separate by strategy
    cc_picks = [p for p in all_picks if p['strategy'] == 'CC']
    csp_picks = [p for p in all_picks if p['strategy'] == 'CSP']

    print(f"\n📊 Total picks generated: {len(all_picks)}")
    print(f"  📈 Covered Calls: {len(cc_picks)}")
    print(f"  💰 Cash-Secured Puts: {len(csp_picks)}")

    if all_picks:
        # Save to database
        print("\n💾 Saving to database...")
        saved = save_picks_to_db(all_picks)
        print(f"  ✅ Saved {saved} picks")

        # Send alerts
        print("\n📱 Sending alerts...")
        telegram = TelegramService()

        message = f"📊 **Hybrid Screening Results**\n"
        message += f"📅 {date.today()}\n"
        message += f"*Real stock prices + estimated options*\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        if cc_picks:
            message += f"📈 **Top Covered Calls**\n"
            for pick in cc_picks[:3]:
                message += f"• {pick['symbol']}: ${pick['strike']} ({pick['dte']}d)\n"
                message += f"  Stock: ${pick['stock_price']:.2f} | "
                message += f"Est Premium: ${pick['premium']:.2f}\n"
                message += f"  ROI: {pick['roi_30d']:.1%} | Score: {pick['score']:.2f}\n\n"

        if csp_picks:
            message += f"💰 **Top Cash-Secured Puts**\n"
            for pick in csp_picks[:3]:
                message += f"• {pick['symbol']}: ${pick['strike']} ({pick['dte']}d)\n"
                message += f"  Stock: ${pick['stock_price']:.2f} | "
                message += f"  Est Premium: ${pick['premium']:.2f}\n"
                message += f"  ROI: {pick['roi_30d']:.1%} | Score: {pick['score']:.2f}\n\n"

        message += f"⚠️ *Note: Option premiums are estimates*\n"
        message += f"📊 Dashboard: http://157.245.214.224:3000"

        if telegram.send_message(message):
            print("  ✅ Telegram alert sent")

        # Show top picks
        print("\n🏆 TOP PICKS:")
        print("-"*50)
        for pick in all_picks[:5]:
            emoji = "📈" if pick['strategy'] == 'CC' else "💰"
            print(f"{emoji} {pick['symbol']} {pick['strategy']}: ${pick['strike']} ({pick['dte']}d)")
            print(f"   Real Stock Price: ${pick['stock_price']:.2f}")
            print(f"   Est. Premium: ${pick['premium']:.2f}")
            print(f"   Est. ROI (30d): {pick['roi_30d']:.2%}")
            print(f"   Est. IV: {pick['iv']:.1%} | IVR: {pick['iv_rank']:.0f}%")
            print(f"   Score: {pick['score']:.3f}")
            print()

    print("="*60)
    print("✅ HYBRID SCREENING COMPLETE!")
    print("="*60)
    print(f"\n📊 Dashboard: http://157.245.214.224:3000")

    return {
        'total_picks': len(all_picks),
        'cc_picks': len(cc_picks),
        'csp_picks': len(csp_picks)
    }

if __name__ == "__main__":
    # Run hybrid screening with default symbols
    results = run_hybrid_screening()