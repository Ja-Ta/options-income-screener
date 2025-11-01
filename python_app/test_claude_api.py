#!/usr/bin/env python3
"""
Test Claude AI API connection.
"""

import sys
import os
from datetime import date

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.claude_service import ClaudeService

def test_claude_api():
    """Test Claude AI API with a sample pick."""
    print("\n" + "="*60)
    print("CLAUDE AI API TEST")
    print("="*60)

    # Check API key
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    print(f"\n🔑 API Key: {'✅ Configured' if api_key and not api_key.startswith('mock') else '❌ Missing'}")

    if not api_key or api_key.startswith('mock'):
        print("❌ Please set a valid ANTHROPIC_API_KEY in .env file")
        return False

    # Initialize Claude service
    print("\n🤖 Initializing Claude service...")
    claude = ClaudeService()

    # Test connection
    print("\n1️⃣ Testing connection...")
    if claude.test_connection():
        print("   ✅ Claude AI connected successfully!")
    else:
        print("   ❌ Connection failed")
        return False

    # Test generating a rationale
    print("\n2️⃣ Testing rationale generation...")

    # Sample pick data
    sample_pick = {
        'symbol': 'AAPL',
        'strategy': 'CC',
        'strike': 185.0,
        'expiry': '2024-02-16',
        'premium': 2.45,
        'roi_30d': 0.013,
        'iv_rank': 65.5,
        'score': 0.72,
        'trend': 'uptrend',
        'earnings_days': 45
    }

    try:
        rationale = claude.generate_rationale(sample_pick)

        if rationale:
            print("   ✅ Generated rationale:")
            print("-" * 50)
            print(rationale)
            print("-" * 50)
            print(f"   Length: {len(rationale.split())} words")
        else:
            print("   ❌ Failed to generate rationale")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Test batch processing
    print("\n3️⃣ Testing batch processing...")

    sample_picks = [
        {
            'symbol': 'SPY',
            'strategy': 'CSP',
            'strike': 420.0,
            'expiry': '2024-02-16',
            'premium': 3.50,
            'roi_30d': 0.008,
            'iv_rank': 42.0,
            'score': 0.65
        },
        {
            'symbol': 'MSFT',
            'strategy': 'CC',
            'strike': 410.0,
            'expiry': '2024-02-23',
            'premium': 4.20,
            'roi_30d': 0.010,
            'iv_rank': 58.0,
            'score': 0.69
        }
    ]

    try:
        enriched = claude.enrich_picks_batch(sample_picks)

        if enriched:
            print(f"   ✅ Enriched {len(enriched)} picks")
            for pick in enriched:
                if 'rationale' in pick:
                    print(f"      {pick['symbol']}: {len(pick['rationale'].split())} words")
        else:
            print("   ⚠️ No picks enriched")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("✅ CLAUDE AI IS WORKING!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_claude_api()
    if success:
        print("\n🎉 Claude AI integration successful!")
        print("   The AI can generate rationales for option picks.")
    else:
        print("\n❌ Please check your Anthropic API key and try again.")