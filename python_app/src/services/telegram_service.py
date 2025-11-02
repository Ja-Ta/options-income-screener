"""
Telegram Bot service for sending alerts.

Sends formatted option picks to Telegram channel/chat.
Python 3.12 compatible following CLAUDE.md standards.
"""

import os
import time
from typing import Dict, Any, List, Optional, Union
import requests
from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_CHAT_IDS
from ..utils.logging import get_logger


class TelegramService:
    """Service for sending alerts via Telegram Bot API."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[Union[str, List[str]]] = None):
        """
        Initialize Telegram service.

        Args:
            bot_token: Telegram bot token (defaults to env var)
            chat_id: Telegram chat/channel ID(s) - can be single ID or list (defaults to env vars)
        """
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN

        # Handle multiple chat IDs
        if chat_id:
            # If a single chat_id is provided
            if isinstance(chat_id, str):
                self.chat_ids = [chat_id]
            else:
                self.chat_ids = chat_id
        else:
            # Use multiple IDs if configured, otherwise fall back to single ID
            if TELEGRAM_CHAT_IDS:
                self.chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_IDS if cid.strip()]
            elif TELEGRAM_CHAT_ID:
                self.chat_ids = [TELEGRAM_CHAT_ID]
            else:
                self.chat_ids = []

        # Keep backward compatibility
        self.chat_id = self.chat_ids[0] if self.chat_ids else None

        self.logger = get_logger()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.is_mock = not self.bot_token or self.bot_token.startswith("mock_")

    def format_pick_message(self, pick: Dict[str, Any], rationale: str = None) -> str:
        """
        Format a pick into Telegram message.

        Args:
            pick: Pick dictionary from screener/database
            rationale: Optional AI-generated rationale

        Returns:
            Formatted message string
        """
        # Strategy emoji
        strategy_emoji = "📈" if pick['strategy'] == 'CC' else "💰"

        # Format the message following spec Section 16
        message = f"{strategy_emoji} **{pick['strategy']} Pick: {pick['symbol']}**\n"
        message += f"━━━━━━━━━━━━━━━\n"

        # Price and strike info
        message += f"📊 Spot: ${pick.get('spot_price', 0):.2f}\n"
        message += f"🎯 Strike: ${pick['strike']:.2f} ({pick['expiry']})\n"
        message += f"💵 Premium: ${pick['premium']:.2f}\n"

        # Key metrics
        message += f"\n📈 **Metrics:**\n"
        message += f"• ROI (30d): {pick['roi_30d']:.2%}\n"
        message += f"• IV Rank: {pick['iv_rank']:.1f}%\n"
        message += f"• Score: {pick.get('score', 0):.2f}/1.0\n"

        # Add margin of safety for CSP
        if pick['strategy'] == 'CSP' and 'margin_of_safety' in pick:
            message += f"• Safety: {pick['margin_of_safety']:.1%} OTM\n"

        # Notes section
        if pick.get('notes'):
            message += f"\n📝 **Notes:** {pick['notes']}\n"

        # AI rationale if available
        if rationale:
            message += f"\n🤖 **Analysis:**\n{rationale}\n"

        # Footer
        message += f"\n━━━━━━━━━━━━━━━\n"
        message += f"⏰ {pick.get('asof', 'Today')}"

        return message

    def send_message(self, text: str, parse_mode: str = "Markdown", chat_ids: Optional[List[str]] = None) -> bool:
        """
        Send a message to Telegram chat(s).

        Args:
            text: Message text to send
            parse_mode: Telegram parse mode (Markdown or HTML)
            chat_ids: Optional list of specific chat IDs to send to (defaults to all configured)

        Returns:
            True if sent successfully to at least one destination, False otherwise
        """
        if self.is_mock:
            self.logger.info(f"MOCK Telegram message:\n{text}")
            return True

        # Use provided chat_ids or default to all configured IDs
        target_chat_ids = chat_ids or self.chat_ids
        if not target_chat_ids:
            self.logger.error("No chat IDs configured for Telegram")
            return False

        success_count = 0
        failed_chats = []

        for chat_id in target_chat_ids:
            try:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True
                }

                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()

                result = response.json()
                if result.get('ok'):
                    chat_type = "group" if chat_id.startswith("-") else "user"
                    self.logger.info(f"Telegram message sent to {chat_type} {chat_id}")
                    success_count += 1
                else:
                    self.logger.error(f"Telegram API error for chat {chat_id}: {result}")
                    failed_chats.append(chat_id)

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to send to chat {chat_id}: {e}")
                failed_chats.append(chat_id)
            except Exception as e:
                self.logger.error(f"Unexpected error sending to chat {chat_id}: {e}")
                failed_chats.append(chat_id)

        if failed_chats:
            self.logger.warning(f"Failed to send to {len(failed_chats)} chat(s): {', '.join(failed_chats)}")

        # Return True if at least one message was sent successfully
        return success_count > 0

    def send_picks(self, picks: List[Dict[str, Any]], rationales: Dict[int, str] = None) -> Dict[str, Any]:
        """
        Send multiple picks as alerts.

        Args:
            picks: List of pick dictionaries
            rationales: Optional dict mapping pick_id to rationale text

        Returns:
            Dictionary with send results
        """
        rationales = rationales or {}
        results = {
            'sent': [],
            'failed': [],
            'total': len(picks)
        }

        # Send header message
        header = f"🎯 **Daily Options Picks - {picks[0].get('asof', 'Today')}**\n"
        header += f"Found {len(picks)} opportunities\n"
        header += "━━━━━━━━━━━━━━━━━━━\n"

        if not self.send_message(header):
            self.logger.warning("Failed to send header message")

        # Send individual picks with rate limiting
        for pick in picks:
            pick_id = pick.get('id')
            rationale = rationales.get(pick_id) if pick_id else None

            message = self.format_pick_message(pick, rationale)

            if self.send_message(message):
                results['sent'].append(pick['symbol'])
            else:
                results['failed'].append(pick['symbol'])

            # Rate limit to avoid Telegram API throttling
            time.sleep(1)

        # Send summary
        summary = f"\n✅ Sent: {len(results['sent'])} picks"
        if results['failed']:
            summary += f"\n❌ Failed: {len(results['failed'])} picks"

        self.send_message(summary)

        self.logger.info(f"Telegram alerts complete: {len(results['sent'])} sent, "
                        f"{len(results['failed'])} failed")

        return results

    def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """
        Send daily summary statistics.

        Args:
            stats: Statistics dictionary from StatsDAO

        Returns:
            True if sent successfully
        """
        message = f"📊 **Daily Summary - {stats['date']}**\n"
        message += "━━━━━━━━━━━━━━━━━━━\n\n"

        # Counts by strategy
        message += "**Picks Found:**\n"
        for strategy, count in stats.get('counts_by_strategy', {}).items():
            avg_score = stats.get('avg_scores', {}).get(strategy, 0)
            message += f"• {strategy}: {count} picks (avg score: {avg_score:.2f})\n"

        # Top performers
        if stats.get('top_picks'):
            message += "\n**Top Performers:**\n"
            for i, pick in enumerate(stats['top_picks'][:3], 1):
                emoji = ["🥇", "🥈", "🥉"][i-1]
                message += f"{emoji} {pick['symbol']} ({pick['strategy']}): "
                message += f"{pick['roi_30d']:.2%} ROI, Score: {pick['score']:.2f}\n"

        message += "\n━━━━━━━━━━━━━━━━━━━\n"
        message += "Use /picks to see all picks"

        return self.send_message(message)

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection.

        Returns:
            True if connection successful
        """
        if self.is_mock:
            self.logger.info("Mock mode - connection test skipped")
            return True

        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                bot_info = result.get('result', {})
                self.logger.info(f"Telegram bot connected: @{bot_info.get('username')}")
                return True
            else:
                self.logger.error(f"Telegram connection test failed: {result}")
                return False

        except Exception as e:
            self.logger.error(f"Telegram connection test error: {e}")
            return False


# Keep backward compatibility with existing code
def format_pick_telegram(pick, summary):
    """Legacy function for formatting picks."""
    service = TelegramService()
    return service.format_pick_message(pick, summary)


def send_telegram(message: str) -> bool:
    """Legacy function for sending messages."""
    service = TelegramService()
    return service.send_message(message)
