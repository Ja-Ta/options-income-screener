#!/usr/bin/env python3
"""
Real options screening using Polygon.io Options API.
Fetches actual options data and saves best picks to database.
"""

import sys
import os
import sqlite3
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.data.real_options_fetcher import RealOptionsFetcher
from src.services.telegram_service import TelegramService
from src.services.claude_service import ClaudeService


class RealPolygonScreener:
    """Screens options using real Polygon data."""

    def __init__(self, api_key: str):
        """Initialize screener."""
        self.fetcher = RealOptionsFetcher(api_key)
        self.telegram = TelegramService()
        self.claude = ClaudeService()

    def calculate_score(self, option: Dict, strategy: str) -> float:
        """Calculate composite score for an option."""
        score = 0.0

        # ROI component (30%)
        roi_score = min(option.get('roi_30d', 0) * 10, 1.0) * 0.3

        # IV component (40%)
        iv = option.get('iv', 0)
        if strategy == 'CC':
            # Higher IV is better for selling
            iv_score = min(iv * 2, 1.0) * 0.4
        else:
            # Moderate IV is better for CSPs
            iv_score = min(iv * 2.5, 1.0) * 0.4

        # Moneyness component (20%)
        moneyness = abs(option.get('moneyness', 0))
        # Prefer 2-4% OTM
        if 0.02 <= moneyness <= 0.04:
            moneyness_score = 1.0 * 0.2
        elif 0.01 <= moneyness <= 0.05:
            moneyness_score = 0.7 * 0.2
        else:
            moneyness_score = 0.3 * 0.2

        # Delta component (10%)
        delta = abs(option.get('delta', 0))
        # Prefer delta around 0.20-0.35
        if 0.20 <= delta <= 0.35:
            delta_score = 1.0 * 0.1
        elif 0.15 <= delta <= 0.40:
            delta_score = 0.7 * 0.1
        else:
            delta_score = 0.3 * 0.1

        score = roi_score + iv_score + moneyness_score + delta_score

        return min(score, 1.0)

    def screen_symbol(self, symbol: str) -> Dict:
        """Screen a single symbol for options opportunities."""
        logger.info(f"\n📊 Screening {symbol}...")

        # Get stock price
        stock_price = self.fetcher.get_stock_price(symbol)
        if not stock_price:
            logger.warning(f"Could not get stock price for {symbol}")
            return {'symbol': symbol, 'cc_picks': [], 'csp_picks': []}

        # Find covered calls
        cc_candidates = self.fetcher.find_covered_call_candidates(symbol, stock_price)
        cc_picks = []

        for candidate in cc_candidates:
            if candidate['mid'] > 0:  # Only include options with valid premiums
                candidate['strategy'] = 'CC'
                candidate['premium'] = candidate['mid']
                candidate['score'] = self.calculate_score(candidate, 'CC')

                # Estimate trend (simplified)
                candidate['trend'] = 'neutral'

                # Add earnings days estimate
                candidate['earnings_days'] = 45  # Placeholder

                cc_picks.append(candidate)

        # Find cash-secured puts
        csp_candidates = self.fetcher.find_cash_secured_put_candidates(symbol, stock_price)
        csp_picks = []

        for candidate in csp_candidates:
            if candidate['mid'] > 0:  # Only include options with valid premiums
                candidate['strategy'] = 'CSP'
                candidate['premium'] = candidate['mid']
                candidate['score'] = self.calculate_score(candidate, 'CSP')

                # Estimate trend (simplified)
                candidate['trend'] = 'neutral'

                # Add earnings days estimate
                candidate['earnings_days'] = 45  # Placeholder

                csp_picks.append(candidate)

        # Sort by score
        cc_picks.sort(key=lambda x: x['score'], reverse=True)
        csp_picks.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"  ✅ Found {len(cc_picks)} CC and {len(csp_picks)} CSP candidates")

        return {
            'symbol': symbol,
            'cc_picks': cc_picks[:2],  # Top 2 of each
            'csp_picks': csp_picks[:2]
        }

    def save_picks_to_db(self, all_picks: List[Dict]):
        """Save picks to database."""
        conn = sqlite3.connect("python_app/data/screener.db")
        cursor = conn.cursor()

        today = date.today()
        inserted = 0

        # Clear today's picks
        cursor.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

        for pick in all_picks:
            try:
                # Get IV rank (using IV as proxy for now)
                iv_rank = min(pick.get('iv', 0.5) * 100, 100) if pick.get('iv') else 50

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
                    iv_rank, pick['score'],
                    pick['trend'], pick['earnings_days']
                ))
                inserted += 1
            except Exception as e:
                logger.error(f"Error inserting pick: {e}")

        conn.commit()

        # Also sync to Node.js database
        try:
            conn2 = sqlite3.connect("data/screener.db")
            cursor2 = conn2.cursor()
            cursor2.execute("DELETE FROM picks WHERE date = ?", (today.isoformat(),))

            for pick in all_picks:
                try:
                    iv_rank = min(pick.get('iv', 0.5) * 100, 100) if pick.get('iv') else 50

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
                        iv_rank, pick['score'],
                        pick['trend'], pick['earnings_days']
                    ))
                except:
                    pass

            conn2.commit()
            conn2.close()
        except Exception as e:
            logger.error(f"Error syncing to Node database: {e}")

        conn.close()
        return inserted

    def send_alerts(self, cc_picks: List[Dict], csp_picks: List[Dict]):
        """Send alerts via Telegram."""
        if not cc_picks and not csp_picks:
            return False

        # Format message
        message = f"🎯 **Daily Options Screening Results**\n"
        message += f"📅 {date.today()}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        if cc_picks:
            message += f"📈 **Top Covered Calls ({len(cc_picks)})**\n"
            for pick in cc_picks[:3]:
                message += f"• {pick['symbol']}: ${pick['strike']:.2f} "
                message += f"(Premium: ${pick.get('premium', 0):.2f}, "
                message += f"ROI: {pick.get('roi_30d', 0):.1%})\n"
                if pick.get('iv'):
                    message += f"  IV: {pick['iv']:.1%}, Delta: {pick.get('delta', 'N/A')}\n"
            message += "\n"

        if csp_picks:
            message += f"💰 **Top Cash-Secured Puts ({len(csp_picks)})**\n"
            for pick in csp_picks[:3]:
                message += f"• {pick['symbol']}: ${pick['strike']:.2f} "
                message += f"(Premium: ${pick.get('premium', 0):.2f}, "
                message += f"ROI: {pick.get('roi_30d', 0):.1%})\n"
                if pick.get('iv'):
                    message += f"  IV: {pick['iv']:.1%}, Delta: {pick.get('delta', 'N/A')}\n"

        message += f"\n📊 View dashboard: http://157.245.214.224:3000"

        # Send message
        return self.telegram.send_message(message)

    def run_screening(self, symbols: List[str]):
        """Run screening for multiple symbols."""
        print("\n" + "="*60)
        print("REAL POLYGON OPTIONS SCREENING")
        print("="*60)
        print(f"📅 Date: {date.today()}")
        print(f"📊 Screening {len(symbols)} symbols")
        print("-"*60)

        all_picks = []

        for symbol in symbols:
            try:
                result = self.screen_symbol(symbol)

                # Collect all picks
                all_picks.extend(result['cc_picks'])
                all_picks.extend(result['csp_picks'])

                # Rate limiting (be conservative with API calls)
                import time
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error screening {symbol}: {e}")

        # Sort all picks by score
        all_picks.sort(key=lambda x: x['score'], reverse=True)

        # Separate by strategy
        cc_picks = [p for p in all_picks if p['strategy'] == 'CC']
        csp_picks = [p for p in all_picks if p['strategy'] == 'CSP']

        print(f"\n✅ Found {len(cc_picks)} CC and {len(csp_picks)} CSP picks")

        # Save to database
        if all_picks:
            print("\n💾 Saving to database...")
            saved = self.save_picks_to_db(all_picks)
            print(f"  ✅ Saved {saved} picks")

            # Send alerts
            print("\n📱 Sending alerts...")
            if self.send_alerts(cc_picks, csp_picks):
                print("  ✅ Telegram alert sent")

        # Show top picks
        print("\n📈 TOP PICKS:")
        print("-"*40)
        for pick in all_picks[:5]:
            emoji = "📈" if pick['strategy'] == 'CC' else "💰"
            print(f"{emoji} {pick['symbol']} {pick['strategy']}: ${pick['strike']:.2f}")
            print(f"   Premium: ${pick.get('premium', 0):.2f}")
            print(f"   ROI (30d): {pick.get('roi_30d', 0):.2%}")
            if pick.get('iv'):
                print(f"   IV: {pick['iv']:.2%}, Delta: {pick.get('delta', 'N/A')}")
            print(f"   Score: {pick['score']:.3f}")
            print()

        print("="*60)
        print("✅ REAL OPTIONS SCREENING COMPLETE!")
        print("="*60)
        print(f"\n📊 Dashboard: http://157.245.214.224:3000")

        return {
            'total_picks': len(all_picks),
            'cc_picks': len(cc_picks),
            'csp_picks': len(csp_picks)
        }


def main():
    """Main entry point."""
    # Get API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.error("No POLYGON_API_KEY found in environment")
        return

    # Initialize screener
    screener = RealPolygonScreener(api_key)

    # Test symbols (start with a few to avoid rate limits)
    symbols = ['SPY', 'AAPL', 'MSFT']  # Start small

    # Run screening
    results = screener.run_screening(symbols)

    print(f"\nProcessed {results['total_picks']} total picks")


if __name__ == "__main__":
    main()