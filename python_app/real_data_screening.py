#!/usr/bin/env python3
"""
Real data screening using Polygon API.
Designed to work with API tier limitations.
"""

import sys
import os
import sqlite3
import time
import requests
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

# Set to use real data
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

class PolygonRealDataClient:
    """Simplified Polygon client for real data fetching."""

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

    def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """Get latest stock price."""
        self._rate_limit()

        try:
            # Get previous close (most reliable for free tier)
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
            params = {"apiKey": self.api_key}

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    result = data['results'][0]
                    return {
                        'symbol': symbol,
                        'close': result['c'],
                        'open': result['o'],
                        'high': result['h'],
                        'low': result['l'],
                        'volume': result['v'],
                        'timestamp': datetime.fromtimestamp(result['t']/1000)
                    }
            else:
                logger.warning(f"Failed to get price for {symbol}: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")

        return None

    def get_options_contracts(self, symbol: str) -> List[Dict]:
        """Get options contracts for a symbol."""
        self._rate_limit()

        contracts = []
        try:
            # Get options contracts list
            url = f"{self.base_url}/v3/reference/options/contracts"
            params = {
                "underlying_ticker": symbol,
                "expired": "false",
                "limit": 100,
                "apiKey": self.api_key
            }

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    for contract in data['results']:
                        # Parse contract details
                        ticker = contract['ticker']

                        # Extract expiry date (format: O:AAPL230120C00150000)
                        # Skip the O: prefix and symbol
                        remaining = ticker[2+len(symbol):]
                        exp_date_str = remaining[:6]  # YYMMDD

                        try:
                            exp_date = datetime.strptime(exp_date_str, '%y%m%d').date()
                            dte = (exp_date - date.today()).days

                            # Skip if DTE not in range
                            if dte < 25 or dte > 50:
                                continue

                            # Determine type and strike
                            if 'C' in remaining[6:]:
                                option_type = 'call'
                                strike_str = remaining.split('C')[1]
                            else:
                                option_type = 'put'
                                strike_str = remaining.split('P')[1]

                            strike = float(strike_str) / 1000

                            contracts.append({
                                'ticker': ticker,
                                'underlying': symbol,
                                'type': option_type,
                                'strike': strike,
                                'expiry': exp_date,
                                'dte': dte
                            })

                        except Exception as e:
                            logger.debug(f"Error parsing contract {ticker}: {e}")
                            continue

            else:
                logger.warning(f"Failed to get options for {symbol}: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching options for {symbol}: {e}")

        return contracts

    def get_option_quote(self, ticker: str) -> Optional[Dict]:
        """Get quote for specific option contract."""
        self._rate_limit()

        try:
            # Get last quote
            url = f"{self.base_url}/v3/quotes/{ticker}"
            params = {
                "limit": 1,
                "order": "desc",
                "apiKey": self.api_key
            }

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    quote = data['results'][0]
                    return {
                        'bid': quote.get('bid', 0),
                        'ask': quote.get('ask', 0),
                        'mid': (quote.get('bid', 0) + quote.get('ask', 0)) / 2
                    }

        except Exception as e:
            logger.debug(f"Error getting quote for {ticker}: {e}")

        return None

def calculate_greeks_estimate(stock_price: float, strike: float, dte: int, option_type: str) -> Dict:
    """Estimate Greeks based on moneyness and DTE."""
    moneyness = strike / stock_price

    # Simple delta estimation
    if option_type == 'call':
        if moneyness < 0.95:
            delta = 0.7
        elif moneyness < 1.0:
            delta = 0.5
        elif moneyness < 1.05:
            delta = 0.3
        else:
            delta = 0.15
    else:  # put
        if moneyness < 0.95:
            delta = -0.15
        elif moneyness < 1.0:
            delta = -0.3
        elif moneyness < 1.05:
            delta = -0.5
        else:
            delta = -0.7

    # Estimate IV based on typical values
    iv = 0.25 + (abs(1 - moneyness) * 0.5)

    # Simple theta estimate (time decay)
    theta = -0.01 * (30 / dte) if dte > 0 else -0.05

    return {
        'delta': delta,
        'iv': iv,
        'theta': theta,
        'gamma': 0.02,
        'vega': 0.1
    }

def calculate_iv_rank_estimate(current_iv: float) -> float:
    """Estimate IV rank based on typical ranges."""
    # Assume typical IV range of 15-45%
    min_iv = 0.15
    max_iv = 0.45

    if current_iv <= min_iv:
        return 0
    elif current_iv >= max_iv:
        return 100
    else:
        return ((current_iv - min_iv) / (max_iv - min_iv)) * 100

def screen_options(symbol: str, stock_data: Dict, contracts: List[Dict], client: PolygonRealDataClient) -> List[Dict]:
    """Screen options for a symbol."""
    picks = []
    stock_price = stock_data['close']

    # Limit contracts to check (API rate limits)
    max_contracts = 5
    checked = 0

    for contract in contracts[:max_contracts]:
        if checked >= max_contracts:
            break

        # Skip if not right type for strategy
        if contract['type'] == 'call' and contract['strike'] < stock_price * 1.01:
            continue  # CC needs OTM calls
        if contract['type'] == 'put' and contract['strike'] > stock_price * 0.99:
            continue  # CSP needs OTM puts

        # Get quote (this uses API call)
        quote = client.get_option_quote(contract['ticker'])

        if not quote or quote['mid'] <= 0:
            continue

        checked += 1

        # Calculate metrics
        greeks = calculate_greeks_estimate(stock_price, contract['strike'], contract['dte'], contract['type'])

        # Determine strategy
        if contract['type'] == 'call':
            strategy = 'CC'
            premium = quote['bid'] if quote['bid'] > 0 else quote['mid']
            roi_30d = premium / stock_price
        else:
            strategy = 'CSP'
            premium = quote['bid'] if quote['bid'] > 0 else quote['mid']
            roi_30d = premium / contract['strike']

        # Calculate IV rank estimate
        iv_rank = calculate_iv_rank_estimate(greeks['iv'])

        # Skip if IV rank too low
        min_ivr = 40 if strategy == 'CC' else 50
        if iv_rank < min_ivr:
            continue

        # Calculate score
        score = (
            (iv_rank / 100) * 0.4 +  # IV rank weight
            min(roi_30d * 50, 1.0) * 0.3 +  # ROI weight (capped)
            (abs(greeks['delta']) * 0.3)  # Delta weight
        )

        pick = {
            'symbol': symbol,
            'strategy': strategy,
            'strike': round(contract['strike'], 2),
            'expiry': contract['expiry'].isoformat(),
            'dte': contract['dte'],
            'premium': round(premium, 2),
            'stock_price': round(stock_price, 2),
            'roi_30d': roi_30d,
            'annualized_return': roi_30d * (365 / 30),
            'iv': greeks['iv'],
            'iv_rank': iv_rank,
            'delta': greeks['delta'],
            'score': min(score, 1.0),
            'bid': quote['bid'],
            'ask': quote['ask'],
            'spread': quote['ask'] - quote['bid'],
            'trend': 'neutral',
            'earnings_days': 45  # Placeholder
        }

        picks.append(pick)
        logger.info(f"Found {strategy} pick for {symbol}: Strike ${pick['strike']}, ROI {roi_30d:.2%}")

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
            # Get column count from first row
            placeholders = ','.join(['?'] * len(rows[0]))
            cursor2.executemany(f'INSERT INTO picks VALUES ({placeholders})', rows)

        conn2.commit()
        conn2.close()
    except Exception as e:
        logger.error(f"Error syncing to Node.js DB: {e}")

    conn.close()
    return inserted

def generate_rationales(picks: List[Dict]) -> None:
    """Generate AI rationales for top picks."""
    try:
        claude = ClaudeService()

        # Generate rationales for top 3 picks
        for pick in picks[:3]:
            try:
                rationale = claude.generate_rationale(pick)
                if rationale:
                    pick['rationale'] = rationale
                    logger.info(f"Generated rationale for {pick['symbol']}")
            except Exception as e:
                logger.error(f"Error generating rationale: {e}")

    except Exception as e:
        logger.error(f"Claude service error: {e}")

def send_alerts(cc_picks: List[Dict], csp_picks: List[Dict]) -> bool:
    """Send alerts via Telegram."""
    try:
        telegram = TelegramService()

        # Format message
        message = f"🎯 **Real Market Screening Results**\n"
        message += f"📅 {date.today()}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        if cc_picks:
            message += f"📈 **Top Covered Calls ({len(cc_picks)})**\n"
            for pick in cc_picks[:3]:
                message += f"• {pick['symbol']}: ${pick['strike']} ({pick['dte']}d)\n"
                message += f"  Premium: ${pick['premium']:.2f} | "
                message += f"ROI: {pick['roi_30d']:.1%} | "
                message += f"IVR: {pick['iv_rank']:.0f}%\n"
                if pick.get('rationale'):
                    # Add first sentence of rationale
                    first_sentence = pick['rationale'].split('.')[0] + '.'
                    message += f"  💡 {first_sentence}\n"
                message += "\n"

        if csp_picks:
            message += f"💰 **Top Cash-Secured Puts ({len(csp_picks)})**\n"
            for pick in csp_picks[:3]:
                message += f"• {pick['symbol']}: ${pick['strike']} ({pick['dte']}d)\n"
                message += f"  Premium: ${pick['premium']:.2f} | "
                message += f"ROI: {pick['roi_30d']:.1%} | "
                message += f"IVR: {pick['iv_rank']:.0f}%\n"
                if pick.get('rationale'):
                    # Add first sentence of rationale
                    first_sentence = pick['rationale'].split('.')[0] + '.'
                    message += f"  💡 {first_sentence}\n"
                message += "\n"

        message += f"📊 Dashboard: http://157.245.214.224:3000"

        if telegram.send_message(message):
            logger.info("Telegram alert sent successfully")
            return True

    except Exception as e:
        logger.error(f"Error sending alerts: {e}")

    return False

def run_real_screening(symbols: List[str] = None):
    """Run screening with real Polygon data."""
    print("\n" + "="*60)
    print("REAL MARKET DATA SCREENING")
    print("="*60)

    # Default symbols (limited due to API constraints)
    if not symbols:
        symbols = ['SPY', 'AAPL']  # Start with just 2 for testing

    print(f"\n📊 Screening symbols: {', '.join(symbols)}")
    print(f"📅 Date: {date.today()}")
    print("⚠️  Using Polygon API (rate limited)")
    print("-"*60)

    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key or api_key.startswith('mock'):
        print("❌ Valid Polygon API key required")
        return None

    # Initialize client
    client = PolygonRealDataClient(api_key)
    all_picks = []

    # Process each symbol
    for symbol in symbols:
        print(f"\n📈 Processing {symbol}...")

        # Get stock price
        print(f"  📊 Fetching stock price...")
        stock_data = client.get_stock_price(symbol)

        if not stock_data:
            print(f"  ❌ Failed to get stock data")
            continue

        print(f"  ✅ Stock price: ${stock_data['close']:.2f}")

        # Get options contracts
        print(f"  📑 Fetching options contracts...")
        contracts = client.get_options_contracts(symbol)

        if not contracts:
            print(f"  ⚠️ No suitable options found")
            continue

        print(f"  ✅ Found {len(contracts)} contracts (30-45 DTE)")

        # Screen options
        print(f"  🔍 Screening options...")
        picks = screen_options(symbol, stock_data, contracts, client)

        if picks:
            print(f"  ✅ Found {len(picks)} picks")
            all_picks.extend(picks)
        else:
            print(f"  ⚠️ No picks met criteria")

    # Sort by score
    all_picks.sort(key=lambda x: x['score'], reverse=True)

    # Separate by strategy
    cc_picks = [p for p in all_picks if p['strategy'] == 'CC']
    csp_picks = [p for p in all_picks if p['strategy'] == 'CSP']

    print(f"\n📊 Total picks found: {len(all_picks)}")
    print(f"  📈 Covered Calls: {len(cc_picks)}")
    print(f"  💰 Cash-Secured Puts: {len(csp_picks)}")

    if all_picks:
        # Generate AI rationales for top picks
        print("\n🤖 Generating AI rationales...")
        generate_rationales(all_picks)

        # Save to database
        print("\n💾 Saving to database...")
        saved = save_picks_to_db(all_picks)
        print(f"  ✅ Saved {saved} picks")

        # Send alerts
        print("\n📱 Sending alerts...")
        send_alerts(cc_picks, csp_picks)

        # Show top picks
        print("\n🏆 TOP PICKS:")
        print("-"*50)
        for pick in all_picks[:5]:
            emoji = "📈" if pick['strategy'] == 'CC' else "💰"
            print(f"{emoji} {pick['symbol']} {pick['strategy']}: ${pick['strike']} ({pick['dte']}d)")
            print(f"   Premium: ${pick['premium']:.2f} (Bid: ${pick['bid']:.2f}, Ask: ${pick['ask']:.2f})")
            print(f"   ROI (30d): {pick['roi_30d']:.2%}")
            print(f"   IV Rank: {pick['iv_rank']:.1f}%")
            print(f"   Delta: {pick['delta']:.2f}")
            print(f"   Score: {pick['score']:.3f}")
            if pick.get('rationale'):
                print(f"   💡 {pick['rationale'][:100]}...")
            print()
    else:
        print("\n⚠️ No picks found meeting criteria")

    print("="*60)
    print("✅ SCREENING COMPLETE!")
    print("="*60)
    print(f"\n📊 Dashboard: http://157.245.214.224:3000")

    return {
        'total_picks': len(all_picks),
        'cc_picks': len(cc_picks),
        'csp_picks': len(csp_picks)
    }

if __name__ == "__main__":
    # Run with limited symbols due to API constraints
    results = run_real_screening(['SPY'])  # Start with just SPY