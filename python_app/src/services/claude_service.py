"""
Claude AI service for generating pick rationales.

Generates human-readable explanations of option picks using Anthropic's Claude API.
Python 3.12 compatible following CLAUDE.md standards.
"""

import json
import time
from typing import Dict, Any, List, Optional
import requests
from ..config import ANTHROPIC_API_KEY
from ..utils.logging import get_logger


# Structured prompt following spec Section 15
CLAUDE_PROMPT = """You are an options mentor. Summarize this pick for a newer investor (≤120 words).
Explain why it's attractive, key risks, and when to re-evaluate. Use plain English.

DATA:
Symbol: {symbol}
Strategy: {strategy}
Current Price: ${spot_price:.2f}
Strike: ${strike:.2f}
Expiry: {expiry}
Premium: ${premium:.2f}

KEY METRICS:
- ROI (30-day): {roi_30d:.2%}
- IV Rank: {iv_rank:.1f}%
- Score: {score:.2f}/1.0
{extra_metrics}

TECHNICAL:
- Trend: {trend}
- Above/Below 200 SMA: {sma_position}

NOTES: {notes}
"""


class ClaudeService:
    """Service for generating AI-powered pick explanations using Claude API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude service.

        Args:
            api_key: Anthropic API key (defaults to env var)
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.logger = get_logger()
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.is_mock = not self.api_key or self.api_key.startswith("mock_")

    def _format_pick_data(self, pick: Dict[str, Any]) -> str:
        """
        Format pick data for Claude prompt.

        Args:
            pick: Pick dictionary from screener/database

        Returns:
            Formatted prompt string
        """
        # Extra metrics based on strategy
        extra_metrics = ""
        if pick['strategy'] == 'CSP' and 'margin_of_safety' in pick:
            extra_metrics = f"- Safety Margin: {pick['margin_of_safety']:.1%} OTM"
        elif pick['strategy'] == 'CC' and 'dividend_yield' in pick:
            extra_metrics = f"- Dividend Yield: {pick.get('dividend_yield', 0):.2%}"

        # Trend description
        trend_strength = pick.get('trend_strength', 0)
        if trend_strength > 0.5:
            trend = "Strong uptrend"
        elif trend_strength > 0:
            trend = "Mild uptrend"
        elif trend_strength > -0.5:
            trend = "Sideways/weak"
        else:
            trend = "Downtrend"

        # SMA position
        sma_position = "Above" if not pick.get('below_200sma', False) else "Below"

        return CLAUDE_PROMPT.format(
            symbol=pick['symbol'],
            strategy=pick['strategy'],
            spot_price=pick.get('spot_price', 0),
            strike=pick['strike'],
            expiry=pick['expiry'],
            premium=pick['premium'],
            roi_30d=pick['roi_30d'],
            iv_rank=pick['iv_rank'],
            score=pick.get('score', 0),
            extra_metrics=extra_metrics,
            trend=trend,
            sma_position=sma_position,
            notes=pick.get('notes', 'Standard setup')
        )

    def generate_rationale(self, pick: Dict[str, Any]) -> Optional[str]:
        """
        Generate AI rationale for a single pick.

        Args:
            pick: Pick dictionary from screener/database

        Returns:
            Generated rationale text or None if failed
        """
        if self.is_mock:
            # Generate mock rationale for testing
            return self._generate_mock_rationale(pick)

        try:
            prompt = self._format_pick_data(pick)

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": "claude-3-haiku-20240307",  # Fast, cost-effective model
                "max_tokens": 500,  # Increased to allow complete rationales without truncation
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }

            # Log what we're sending to Claude for debugging
            self.logger.debug(f"Generating rationale for {pick['symbol']} {pick['strategy']} ${pick['strike']}")

            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if 'content' in result and len(result['content']) > 0:
                rationale = result['content'][0].get('text', '').strip()

                # Validate response completeness
                if len(rationale) < 50:
                    self.logger.warning(f"Rationale too short ({len(rationale)} chars) for {pick['symbol']}")
                elif not rationale[-1] in ['.', '!', '?']:
                    self.logger.warning(f"Rationale may be truncated for {pick['symbol']} (ends with: '{rationale[-20:]}')")

                self.logger.debug(f"Generated rationale for {pick['symbol']} ({len(rationale)} chars)")
                return rationale
            else:
                self.logger.error(f"Invalid Claude API response: {result}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Claude API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error generating rationale: {e}")
            return None

    def generate_batch_rationales(
        self,
        picks: List[Dict[str, Any]],
        max_workers: int = 3
    ) -> Dict[int, str]:
        """
        Generate rationales for multiple picks.

        Args:
            picks: List of pick dictionaries
            max_workers: Maximum parallel API calls

        Returns:
            Dictionary mapping pick_id to rationale text
        """
        rationales = {}

        for pick in picks:
            pick_id = pick.get('id')
            if not pick_id:
                continue

            rationale = self.generate_rationale(pick)
            if rationale:
                rationales[pick_id] = rationale

            # Rate limiting to avoid API throttling
            if not self.is_mock:
                time.sleep(0.5)  # 2 requests per second max

        self.logger.info(f"Generated {len(rationales)} rationales for {len(picks)} picks")
        return rationales

    def _generate_mock_rationale(self, pick: Dict[str, Any]) -> str:
        """
        Generate mock rationale for testing.

        Args:
            pick: Pick dictionary

        Returns:
            Mock rationale text
        """
        if pick['strategy'] == 'CC':
            return (
                f"This covered call on {pick['symbol']} offers {pick['roi_30d']:.1%} monthly income "
                f"with {pick['iv_rank']:.0f}% IV rank, indicating elevated premium. "
                f"The ${pick['strike']:.2f} strike provides upside potential while generating income. "
                f"Monitor if stock approaches strike or IV drops below 40%. "
                f"Consider rolling if remaining premium falls below $0.10."
            )
        else:  # CSP
            return (
                f"This cash-secured put on {pick['symbol']} yields {pick['roi_30d']:.1%} monthly "
                f"with {pick.get('margin_of_safety', 0.07):.1%} downside buffer at ${pick['strike']:.2f}. "
                f"IV rank of {pick['iv_rank']:.0f}% suggests rich premiums. "
                f"Watch for support breaks or earnings announcements. "
                f"Re-evaluate if stock drops 5% or IV rank falls below 45%."
            )

    def test_connection(self) -> bool:
        """
        Test Claude API connection.

        Returns:
            True if connection successful
        """
        if self.is_mock:
            self.logger.info("Mock mode - Claude connection test skipped")
            return True

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            # Simple test message
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [
                    {"role": "user", "content": "Reply with 'OK'"}
                ]
            }

            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            self.logger.info("Claude API connection successful")
            return True

        except Exception as e:
            self.logger.error(f"Claude API connection test failed: {e}")
            return False


# Legacy function for backward compatibility
def summarize_pick_with_claude(pick: dict) -> str:
    """Legacy function for generating pick summary."""
    service = ClaudeService()
    return service.generate_rationale(pick) or "Summary generation failed."
