#!/usr/bin/env python3
"""
Test the pipeline with mock data to verify system functionality.
"""

import sys
import os
from datetime import date

# Set environment to use mock data
os.environ['USE_MOCK_DATA'] = 'true'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pipelines.daily_job import run_daily_job

def run_mock_test():
    """Run test with mock data."""
    print("\n" + "="*60)
    print("MOCK DATA TEST")
    print("="*60)

    # Use just 3 symbols for testing
    test_symbols = ['SPY', 'AAPL', 'MSFT']
    print(f"\n📊 Testing with mock data for: {', '.join(test_symbols)}")
    print(f"📅 Date: {date.today()}")
    print("-"*60)

    try:
        print("\n🚀 Running screening pipeline with mock data...")
        results = run_daily_job(symbols=test_symbols)

        print("\n✅ Pipeline completed!")
        print("-"*60)

        print("\n📊 RESULTS:")
        print(f"  • Symbols processed: {results['symbols_processed']}")
        print(f"  • CC picks: {len(results['cc_picks'])}")
        print(f"  • CSP picks: {len(results['csp_picks'])}")
        print(f"  • Alerts sent: {results['alerts_sent']}")
        print(f"  • Duration: {results['duration']:.2f} seconds")

        # Show top picks if any
        if results['cc_picks']:
            print("\n📈 TOP COVERED CALLS:")
            for pick in results['cc_picks'][:3]:
                print(f"  • {pick['symbol']}: ${pick['strike']} ({pick['expiry']})")
                print(f"    ROI: {pick['roi_30d']:.2%}, IVR: {pick['iv_rank']:.0f}%, Score: {pick.get('score', 0):.2f}")

        if results['csp_picks']:
            print("\n💰 TOP CASH-SECURED PUTS:")
            for pick in results['csp_picks'][:3]:
                print(f"  • {pick['symbol']}: ${pick['strike']} ({pick['expiry']})")
                print(f"    ROI: {pick['roi_30d']:.2%}, IVR: {pick['iv_rank']:.0f}%, Score: {pick.get('score', 0):.2f}")

        print("\n" + "="*60)
        print("✅ MOCK TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_mock_test()
    if success:
        print("\n🎉 System is working with mock data!")
        print("\nNext steps:")
        print("1. Fix database schema for real data")
        print("2. Upgrade Polygon API tier if needed")
        print("3. Run with real data")