#!/usr/bin/env python3
"""
Test Telegram multi-destination messaging.

Tests sending messages to:
- Individual chats
- Groups
- Multiple destinations simultaneously
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.services.telegram_service import TelegramService

def test_multi_destination():
    """Test sending to multiple destinations."""
    print("=" * 60)
    print("TESTING TELEGRAM MULTI-DESTINATION SUPPORT")
    print("=" * 60)

    # Initialize service
    telegram = TelegramService()

    # Check configuration
    print("\n1. Current Configuration:")
    print(f"   Bot Token: {'✅ Configured' if telegram.bot_token else '❌ Not configured'}")

    if telegram.chat_ids:
        print(f"   Destinations: {len(telegram.chat_ids)} configured")
        for chat_id in telegram.chat_ids:
            chat_type = "Group/Channel" if chat_id.startswith("-") else "Individual"
            print(f"     - {chat_id} ({chat_type})")
    else:
        print("   ❌ No chat IDs configured")
        print("\n   To configure multiple destinations, add to .env:")
        print("   TELEGRAM_CHAT_IDS=-100123456789,987654321,-200987654321")
        print("   (comma-separated list of chat IDs)")
        return False

    # Test connection
    print("\n2. Testing Bot Connection...")
    if telegram.test_connection():
        print("   ✅ Bot connection successful")
    else:
        print("   ❌ Bot connection failed")
        return False

    # Send test message to all destinations
    print("\n3. Sending test message to all configured destinations...")

    test_message = f"""🧪 **Multi-Destination Test**
━━━━━━━━━━━━━━━━━━━
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 Purpose: Testing multi-destination support
📊 Destinations: {len(telegram.chat_ids)}

This message should appear in:
"""
    for i, chat_id in enumerate(telegram.chat_ids, 1):
        chat_type = "Group/Channel" if chat_id.startswith("-") else "Individual Chat"
        test_message += f"{i}. {chat_type} (ID: {chat_id})\n"

    test_message += """
━━━━━━━━━━━━━━━━━━━
✅ If you see this, multi-destination is working!"""

    if telegram.send_message(test_message):
        print("   ✅ Message sent successfully")
    else:
        print("   ❌ Failed to send message")
        return False

    # Test sending to specific destinations only
    if len(telegram.chat_ids) > 1:
        print("\n4. Testing selective sending (first destination only)...")
        selective_message = f"""🎯 **Selective Send Test**
━━━━━━━━━━━━━━━
This message should only appear in:
Chat ID: {telegram.chat_ids[0]}

Other configured chats should NOT receive this."""

        if telegram.send_message(selective_message, chat_ids=[telegram.chat_ids[0]]):
            print(f"   ✅ Sent to {telegram.chat_ids[0]} only")
        else:
            print("   ❌ Failed to send selective message")

    # Test with sample pick data
    print("\n5. Testing with sample pick data...")
    sample_pick = {
        'symbol': 'TEST',
        'strategy': 'CC',
        'spot_price': 100.00,
        'strike': 105.00,
        'expiry': '2024-12-20',
        'premium': 2.50,
        'roi_30d': 0.025,
        'iv_rank': 65.0,
        'score': 0.75,
        'asof': datetime.now().strftime('%Y-%m-%d'),
        'notes': 'Test pick for multi-destination'
    }

    formatted_message = telegram.format_pick_message(sample_pick)
    if telegram.send_message(formatted_message):
        print("   ✅ Sample pick sent to all destinations")
    else:
        print("   ❌ Failed to send sample pick")

    print("\n" + "=" * 60)
    print("✅ MULTI-DESTINATION TEST COMPLETE")
    print("=" * 60)
    print("\nCheck your Telegram chats/groups to verify messages were received!")

    return True

def show_configuration_help():
    """Show help for configuration."""
    print("\n📚 Configuration Help:")
    print("-" * 40)
    print("To use multiple destinations, update your .env file:")
    print()
    print("Option 1: Single destination (backward compatible)")
    print("   TELEGRAM_CHAT_ID=123456789")
    print()
    print("Option 2: Multiple destinations")
    print("   TELEGRAM_CHAT_IDS=-100123456789,987654321,-200987654321")
    print()
    print("Chat ID formats:")
    print("   • Individual: Positive number (e.g., 123456789)")
    print("   • Group: Negative number (e.g., -123456789)")
    print("   • Supergroup/Channel: -100 prefix (e.g., -1001234567890)")
    print()
    print("To find your chat/group ID, run:")
    print("   python python_app/get_telegram_group_id.py")
    print("-" * 40)

if __name__ == "__main__":
    success = test_multi_destination()

    if not success:
        show_configuration_help()