#!/usr/bin/env python3
"""
Test Claude API integration and generate sample rationales.
"""

import sys
import os
from datetime import date

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.services.claude_service import ClaudeService

def test_claude_api():
    """Test Claude API connection and rationale generation."""
    print("\n" + "="*60)
    print("TESTING CLAUDE AI INTEGRATION")
    print("="*60)

    # Initialize Claude service
    claude = ClaudeService()

    # Test connection
    print("\n1. Testing API connection...")
    if claude.test_connection():
        print("   ✅ Claude API connection successful")
    else:
        print("   ❌ Claude API connection failed")
        return False

    # Create sample pick for testing
    sample_pick = {
        'id': 1,
        'symbol': 'AAPL',
        'strategy': 'CC',
        'spot_price': 270.37,
        'strike': 280.00,
        'expiry': '2024-12-05',
        'premium': 5.31,
        'roi_30d': 0.0173,
        'iv_rank': 63.0,
        'score': 0.75,
        'trend_strength': 0.3,
        'below_200sma': False,
        'dividend_yield': 0.0044,
        'notes': 'Test pick for Claude integration'
    }

    print("\n2. Generating rationale for sample pick...")
    print(f"   Symbol: {sample_pick['symbol']} {sample_pick['strategy']}")
    print(f"   Strike: ${sample_pick['strike']:.2f}")
    print(f"   ROI: {sample_pick['roi_30d']:.2%}")

    rationale = claude.generate_rationale(sample_pick)

    if rationale:
        print(f"\n   ✅ Rationale generated successfully:")
        print("-"*50)
        print(rationale)
        print("-"*50)
    else:
        print("   ❌ Failed to generate rationale")
        return False

    # Test with CSP
    sample_csp = {
        'id': 2,
        'symbol': 'MSFT',
        'strategy': 'CSP',
        'spot_price': 517.81,
        'strike': 500.00,
        'expiry': '2024-12-05',
        'premium': 10.45,
        'roi_30d': 0.0184,
        'iv_rank': 58.5,
        'score': 0.68,
        'margin_of_safety': 0.034,
        'trend_strength': -0.1,
        'below_200sma': False,
        'notes': 'Cash-secured put test'
    }

    print("\n3. Generating rationale for CSP...")
    print(f"   Symbol: {sample_csp['symbol']} {sample_csp['strategy']}")
    print(f"   Strike: ${sample_csp['strike']:.2f}")
    print(f"   ROI: {sample_csp['roi_30d']:.2%}")

    csp_rationale = claude.generate_rationale(sample_csp)

    if csp_rationale:
        print(f"\n   ✅ CSP rationale generated:")
        print("-"*50)
        print(csp_rationale)
        print("-"*50)
    else:
        print("   ❌ Failed to generate CSP rationale")

    # Test batch generation
    print("\n4. Testing batch generation...")
    picks = [sample_pick, sample_csp]
    rationales = claude.generate_batch_rationales(picks)

    print(f"   Generated {len(rationales)} rationales from {len(picks)} picks")

    print("\n" + "="*60)
    print("✅ CLAUDE AI INTEGRATION TEST COMPLETE")
    print("="*60)

    return True

if __name__ == "__main__":
    success = test_claude_api()
    if success:
        print("\n🎯 Claude AI is ready for production use!")
    else:
        print("\n⚠️ Claude AI integration needs attention")