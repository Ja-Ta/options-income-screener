# Telegram Bot Setup & Configuration Guide

## Overview

The Options Income Screener supports sending alerts via Telegram to:
- **Individual chats** (private messages)
- **Groups** (standard Telegram groups)
- **Supergroups** (large groups with advanced features)
- **Channels** (broadcast channels)
- **Multiple destinations simultaneously** (new feature!)

## Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` to BotFather
3. Choose a name for your bot (e.g., "Options Screener Bot")
4. Choose a username ending in `bot` (e.g., `options_screener_bot`)
5. Copy the bot token that BotFather provides

### 2. Configure Your Bot Token

Add the bot token to your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. Get Your Chat ID

#### For Individual Chat
1. Send a message to your bot
2. Run the helper script:
```bash
python python_app/get_telegram_chat_id.py
```
3. Send another message to your bot
4. Copy the chat ID shown (positive number)

#### For Groups
1. Add your bot to the group
2. Make the bot an admin (required for some groups)
3. Send a message in the group mentioning the bot
4. Run the helper script:
```bash
python python_app/get_telegram_group_id.py
```
5. Copy the chat ID shown (negative number)

### 4. Configure Chat IDs

#### Single Destination (Backward Compatible)
```bash
# In .env file
TELEGRAM_CHAT_ID=123456789
```

#### Multiple Destinations (New Feature!)
```bash
# In .env file
TELEGRAM_CHAT_IDS=-1001234567890,987654321,-200987654321
```
Comma-separated list of chat IDs. Can mix individuals, groups, and channels.

## Chat ID Formats

| Type | Format | Example | Description |
|------|--------|---------|-------------|
| **Individual** | Positive number | `123456789` | Private chat with user |
| **Group** | Negative number | `-123456789` | Standard group chat |
| **Supergroup** | -100 prefix | `-1001234567890` | Large group with admin features |
| **Channel** | -100 prefix | `-1001234567890` | Broadcast channel |

## Testing Your Configuration

### Test Basic Connection
```bash
python python_app/get_telegram_chat_id.py
```
This shows your bot is working and displays chat IDs.

### Test Multi-Destination Support
```bash
python python_app/test_telegram_multi.py
```
This sends test messages to all configured destinations.

### Test with Real Screening Data
```bash
python python_app/test_claude_integration.py
```
This tests the complete flow including AI rationales.

## Advanced Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your bot's API token | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_CHAT_ID` | Single destination (legacy) | `123456789` |
| `TELEGRAM_CHAT_IDS` | Multiple destinations | `-100123,456789,-200987` |
| `TELEGRAM_ENABLED` | Enable/disable alerts | `true` or `false` |
| `MAX_PICKS_TO_ALERT` | Max picks per alert | `10` |

### Using Groups vs Channels

**Groups** are best for:
- Interactive discussions about picks
- Teams sharing the same alerts
- Getting feedback from users

**Channels** are best for:
- One-way broadcast of alerts
- Large subscriber base
- Public announcements

## Troubleshooting

### Bot Not Receiving Messages in Group

1. **Make bot admin**: Some groups require the bot to be an admin
2. **Privacy mode**: Send commands with `/` or mention the bot with `@`
3. **Group type**: Ensure it's a supergroup if having issues

### Getting "Chat not found" Error

1. Ensure bot is in the group/channel
2. For channels, bot must be added as admin
3. Double-check the chat ID (especially the negative sign)

### Messages Not Formatting Correctly

The bot uses Markdown formatting. Special characters may need escaping:
- Use `\_` for underscore
- Use `\*` for asterisk
- Use `\[` for square brackets

## Security Notes

1. **Keep your bot token secret** - Never commit it to version control
2. **Use environment variables** - Store sensitive data in `.env`
3. **Limit bot permissions** - Only grant necessary permissions in groups
4. **Monitor usage** - Check bot activity regularly

## Example Configurations

### Personal Setup (Individual + Trading Group)
```bash
# Individual chat for high-priority alerts
TELEGRAM_CHAT_ID=123456789

# Or multiple destinations
TELEGRAM_CHAT_IDS=123456789,-987654321
```

### Team Setup (Multiple Groups)
```bash
# Send to multiple team groups
TELEGRAM_CHAT_IDS=-1001234567890,-1009876543210,-200123456789
```

### Public Channel Broadcasting
```bash
# Broadcast to public channel
TELEGRAM_CHAT_ID=-1001234567890
```

## Helper Scripts

| Script | Purpose |
|--------|---------|
| `get_telegram_chat_id.py` | Find individual chat IDs |
| `get_telegram_group_id.py` | Find group/channel IDs |
| `test_telegram_multi.py` | Test multi-destination setup |

## Integration with Screening Pipeline

The Telegram service is automatically called when:
1. Daily screening completes (`real_polygon_screening.py`)
2. Picks are saved to database
3. AI rationales are generated

Alerts include:
- Top picks for CC and CSP strategies
- Key metrics (ROI, IV, Score)
- AI-generated explanations
- Link to web dashboard

## Support

If you encounter issues:
1. Check the logs for error messages
2. Verify bot token and chat IDs
3. Test with helper scripts
4. Ensure bot has proper permissions

---

**Last Updated:** November 2025
**Compatible with:** Options Income Screener v1.0