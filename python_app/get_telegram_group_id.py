#!/usr/bin/env python3
"""
Helper script to get Telegram chat/group IDs.

This script helps you find the chat ID for:
- Individual chats (positive numbers)
- Groups (negative numbers starting with -)
- Channels (negative numbers starting with -100)

Usage:
1. Run this script
2. Send a message to your bot in the desired chat/group
3. The script will show the chat ID
"""

import os
import sys
import requests
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def get_updates(bot_token, offset=None):
    """Get updates from Telegram bot."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": 10}
    if offset:
        params["offset"] = offset

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting updates: {e}")
        return None

def main():
    """Main function to get chat IDs."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file")
        print("Please add your bot token to the .env file")
        return

    print("=" * 60)
    print("TELEGRAM CHAT/GROUP ID FINDER")
    print("=" * 60)
    print()
    print("Instructions:")
    print("1. Add your bot to the group (if not already added)")
    print("2. Send a message in the group/chat mentioning the bot")
    print("3. This script will show the chat ID")
    print()
    print("Listening for messages...")
    print("-" * 60)

    seen_updates = set()
    offset = None

    try:
        while True:
            result = get_updates(bot_token, offset)

            if result and result.get("ok"):
                updates = result.get("result", [])

                for update in updates:
                    update_id = update.get("update_id")

                    # Update offset for next request
                    if offset is None or update_id >= offset:
                        offset = update_id + 1

                    # Skip if we've seen this update
                    if update_id in seen_updates:
                        continue

                    seen_updates.add(update_id)

                    # Extract message info
                    message = update.get("message") or update.get("channel_post")
                    if message:
                        chat = message.get("chat", {})
                        chat_id = chat.get("id")
                        chat_type = chat.get("type")
                        chat_title = chat.get("title", "Direct Message")
                        username = chat.get("username", "N/A")

                        from_user = message.get("from", {})
                        sender = from_user.get("username", from_user.get("first_name", "Unknown"))
                        text = message.get("text", "")

                        # Format timestamp
                        timestamp = datetime.now().strftime("%H:%M:%S")

                        # Determine chat type emoji
                        if chat_type == "private":
                            emoji = "👤"
                            type_desc = "Private Chat"
                        elif chat_type == "group":
                            emoji = "👥"
                            type_desc = "Group"
                        elif chat_type == "supergroup":
                            emoji = "👥"
                            type_desc = "Supergroup"
                        elif chat_type == "channel":
                            emoji = "📢"
                            type_desc = "Channel"
                        else:
                            emoji = "❓"
                            type_desc = chat_type.title()

                        # Display the chat info
                        print(f"\n[{timestamp}] New message received!")
                        print(f"{emoji} Type: {type_desc}")
                        print(f"📍 Chat ID: {chat_id}")
                        print(f"💬 Title: {chat_title}")
                        if username != "N/A":
                            print(f"🔗 Username: @{username}")
                        print(f"👤 Sender: {sender}")
                        print(f"📝 Message: {text[:50]}..." if len(text) > 50 else f"📝 Message: {text}")
                        print("-" * 60)

                        # Show how to use this ID
                        print("✅ To use this chat ID:")
                        print(f"   Add to .env file:")
                        print(f"   TELEGRAM_CHAT_ID={chat_id}")
                        print()
                        print("   Or for multiple chats:")
                        print(f"   TELEGRAM_CHAT_IDS={chat_id},<other_id>,<other_id>")
                        print("-" * 60)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n✋ Stopped listening")
        print("=" * 60)

        if seen_updates:
            print("\n📋 Summary of discovered chat IDs:")
            print("Copy the ID you want to use to your .env file")
        else:
            print("\n⚠️ No messages received")
            print("Make sure to send a message to your bot in the desired chat/group")

if __name__ == "__main__":
    main()