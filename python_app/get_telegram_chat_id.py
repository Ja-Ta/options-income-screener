#!/usr/bin/env python3
"""
Helper script to get your Telegram chat ID.

Instructions:
1. Send a message to your bot
2. Run this script to see recent messages and their chat IDs
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN or BOT_TOKEN.startswith('mock'):
    print("❌ Please set a valid TELEGRAM_BOT_TOKEN in .env file")
    exit(1)

print("🤖 Getting recent messages sent to your bot...")
print("-" * 50)

# Get updates from the bot
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)

if response.status_code != 200:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

if not data.get('result'):
    print("📭 No messages found.")
    print("\nTo get your chat ID:")
    print("1. Open Telegram")
    print("2. Search for your bot and start a chat")
    print("3. Send any message to the bot")
    print("4. Run this script again")
    exit(0)

print("📬 Recent messages:\n")

# Display chat IDs from messages
chat_ids = set()
for update in data['result'][-10:]:  # Show last 10 updates
    if 'message' in update:
        msg = update['message']
        chat = msg['chat']
        chat_id = chat['id']
        chat_ids.add(chat_id)

        sender = msg.get('from', {})
        text = msg.get('text', 'N/A')

        print(f"Chat ID: {chat_id}")
        print(f"  From: {sender.get('first_name', '')} {sender.get('last_name', '')}")
        print(f"  Username: @{sender.get('username', 'N/A')}")
        print(f"  Message: {text}")
        print(f"  Type: {'Group' if chat.get('type') == 'group' else 'Private'}")
        print("-" * 50)

print("\n✅ Your chat ID(s):")
for chat_id in chat_ids:
    print(f"   {chat_id}")

print("\nUpdate your .env file with:")
print(f"TELEGRAM_CHAT_ID={list(chat_ids)[0] if chat_ids else 'YOUR_CHAT_ID'}")