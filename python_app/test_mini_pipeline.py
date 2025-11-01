#!/usr/bin/env python3
"""
Mini test of the pipeline with real data using free tier endpoints.
"""

import sys
import os
from datetime import date

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pipelines.daily_job import run_daily_job

def run_mini_test():
    """Run a minimal test with just 2 symbols."""
    print("\n" + "="*60)
    print("MINI PRODUCTION TEST - REAL DATA")
    print("="*60)

    # Use just 2 symbols for testing
    test_symbols = ['SPY', 'AAPL']
    print(f"\n📊 Testing with symbols: {', '.join(test_symbols)}")
    print(f"📅 Date: {date.today()}")
    print("-"*60)

    print("\n⚠️ NOTE: Using limited test due to API tier restrictions")
    print("• Polygon free tier: 5 calls/minute")
    print("• Data may be delayed")
    print("-"*60)

    try:
        print("\n🚀 Running screening pipeline...")
        results = run_daily_job(symbols=test_symbols)

        print("\n✅ Pipeline completed!")
        print("-"*60)

        print("\n📊 RESULTS:")
        print(f"  • Symbols processed: {results['symbols_processed']}")
        print(f"  • CC picks: {len(results['cc_picks'])}")
        print(f"  • CSP picks: {len(results['csp_picks'])}")
        print(f"  • Duration: {results['duration']:.2f} seconds")

        # Show picks if any
        if results['cc_picks']:
            print("\n📈 COVERED CALLS:")
            for pick in results['cc_picks'][:2]:
                print(f"  • {pick['symbol']}: ${pick['strike']} ({pick['expiry']})")
                print(f"    ROI: {pick['roi_30d']:.2%}, Score: {pick.get('score', 0):.2f}")

        if results['csp_picks']:
            print("\n💰 CASH-SECURED PUTS:")
            for pick in results['csp_picks'][:2]:
                print(f"  • {pick['symbol']}: ${pick['strike']} ({pick['expiry']})")
                print(f"    ROI: {pick['roi_30d']:.2%}, Score: {pick.get('score', 0):.2f}")

        # Check database
        print("\n🗄️ Database check:")
        from src.storage.database import Database
        db = Database()
        latest_picks = db.get_latest_picks(limit=1)
        if latest_picks:
            print(f"  ✅ Found {len(latest_picks)} picks in database")
        else:
            print("  ⚠️ No data in database yet")

        print("\n" + "="*60)
        print("✅ MINI TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_mini_test()
    if success:
        print("\n🎉 System is working with real data!")
        print("\nTo run full production screening:")
        print("1. Update Telegram chat ID in .env")
        print("2. Consider upgrading Polygon API tier for full options data")
        print("3. Run: python3.12 python_app/src/pipelines/daily_job.py")
    else:
        print("\n⚠️ Check the errors above")
        print("You may need to:")
        print("• Upgrade your Polygon API tier")
        print("• Adjust API call limits")
        print("• Use mock mode for development")