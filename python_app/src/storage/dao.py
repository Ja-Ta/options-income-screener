"""
Data Access Objects (DAOs) for the Options Income Screener database.

Provides structured access to all database tables with proper error handling.
Python 3.12 compatible following CLAUDE.md standards.
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime
from .database import get_database
from ..utils.logging import get_logger


class BaseDAO:
    """Base class for all DAOs."""

    def __init__(self):
        self.db = get_database()
        self.logger = get_logger()


class SymbolsDAO(BaseDAO):
    """DAO for symbols table operations."""

    def upsert_symbol(self, symbol: str, name: str = None, sector: str = None) -> None:
        """
        Insert or update a symbol.

        Args:
            symbol: Stock symbol
            name: Company name
            sector: Industry sector
        """
        query = """
            INSERT INTO symbols (symbol, name, sector, last_seen)
            VALUES (?, ?, ?, DATE('now'))
            ON CONFLICT(symbol) DO UPDATE SET
                name = COALESCE(excluded.name, name),
                sector = COALESCE(excluded.sector, sector),
                last_seen = excluded.last_seen
        """
        self.db.execute(query, (symbol, name, sector))

    def get_active_symbols(self) -> List[str]:
        """Get list of active symbols."""
        query = "SELECT symbol FROM symbols WHERE is_active = 1"
        rows = self.db.execute(query)
        return [row['symbol'] for row in rows] if rows else []

    def deactivate_symbol(self, symbol: str) -> None:
        """Mark a symbol as inactive."""
        query = "UPDATE symbols SET is_active = 0 WHERE symbol = ?"
        self.db.execute(query, (symbol,))


class PricesDAO(BaseDAO):
    """DAO for prices table operations."""

    def insert_prices(self, prices_data: List[Dict[str, Any]]) -> None:
        """
        Batch insert price data.

        Args:
            prices_data: List of price records with keys:
                symbol, asof, close, volume, sma20, sma50, sma200, hv_20, hv_60
        """
        query = """
            INSERT OR REPLACE INTO prices
            (symbol, asof, close, volume, sma20, sma50, sma200, hv_20, hv_60)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params_list = [
            (
                p['symbol'], p['asof'], p['close'], p.get('volume'),
                p.get('sma20'), p.get('sma50'), p.get('sma200'),
                p.get('hv_20'), p.get('hv_60')
            )
            for p in prices_data
        ]
        self.db.execute_many(query, params_list)
        self.logger.info(f"Inserted {len(prices_data)} price records")

    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get most recent price data for a symbol."""
        query = """
            SELECT * FROM prices
            WHERE symbol = ?
            ORDER BY asof DESC
            LIMIT 1
        """
        rows = self.db.execute(query, (symbol,))
        return rows[0] if rows else None

    def get_prices_by_date(self, asof: date) -> List[Dict[str, Any]]:
        """Get all prices for a specific date."""
        query = "SELECT * FROM prices WHERE asof = ?"
        return self.db.execute(query, (asof,)) or []


class OptionsDAO(BaseDAO):
    """DAO for options table operations."""

    def insert_options_chain(self, options_data: List[Dict[str, Any]]) -> None:
        """
        Batch insert option chain data.

        Args:
            options_data: List of option contracts with keys:
                symbol, asof, expiry, side, strike, bid, ask, mid, delta, iv, oi, vol, dte
        """
        query = """
            INSERT OR REPLACE INTO options
            (symbol, asof, expiry, side, strike, bid, ask, mid, delta, iv, oi, vol, dte)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params_list = [
            (
                o['symbol'], o['asof'], o['expiry'], o['side'], o['strike'],
                o['bid'], o['ask'], o['mid'], o['delta'], o['iv'],
                o['oi'], o['vol'], o['dte']
            )
            for o in options_data
        ]
        self.db.execute_many(query, params_list)
        self.logger.info(f"Inserted {len(options_data)} option contracts")

    def get_option_chain(self, symbol: str, asof: date) -> List[Dict[str, Any]]:
        """Get full option chain for a symbol on a date."""
        query = """
            SELECT * FROM options
            WHERE symbol = ? AND asof = ?
            ORDER BY expiry, side, strike
        """
        return self.db.execute(query, (symbol, asof)) or []

    def cleanup_old_options(self, days_to_keep: int = 30) -> None:
        """Remove expired options older than specified days."""
        query = """
            DELETE FROM options
            WHERE expiry < DATE('now', ? || ' days')
        """
        self.db.execute(query, (-days_to_keep,))


class IVMetricsDAO(BaseDAO):
    """DAO for IV metrics table operations."""

    def insert_iv_metrics(self, metrics_data: List[Dict[str, Any]]) -> None:
        """
        Batch insert IV metrics.

        Args:
            metrics_data: List of IV metrics with keys:
                symbol, asof, iv_rank, iv_percentile
        """
        query = """
            INSERT OR REPLACE INTO iv_metrics
            (symbol, asof, iv_rank, iv_percentile)
            VALUES (?, ?, ?, ?)
        """
        params_list = [
            (m['symbol'], m['asof'], m['iv_rank'], m['iv_percentile'])
            for m in metrics_data
        ]
        self.db.execute_many(query, params_list)

    def get_iv_metrics(self, symbol: str, asof: date) -> Optional[Dict[str, Any]]:
        """Get IV metrics for a symbol on a date."""
        query = """
            SELECT * FROM iv_metrics
            WHERE symbol = ? AND asof = ?
        """
        rows = self.db.execute(query, (symbol, asof))
        return rows[0] if rows else None


class EarningsDAO(BaseDAO):
    """DAO for earnings table operations."""

    def upsert_earnings_date(self, symbol: str, earnings_date: date, confirmed: bool = False) -> None:
        """
        Insert or update earnings date.

        Args:
            symbol: Stock symbol
            earnings_date: Next earnings date
            confirmed: Whether date is confirmed
        """
        query = """
            INSERT OR REPLACE INTO earnings
            (symbol, earnings_date, confirmed)
            VALUES (?, ?, ?)
        """
        self.db.execute(query, (symbol, earnings_date, int(confirmed)))

    def get_earnings_date(self, symbol: str) -> Optional[date]:
        """Get next earnings date for a symbol."""
        query = "SELECT earnings_date FROM earnings WHERE symbol = ?"
        rows = self.db.execute(query, (symbol,))
        if rows and rows[0]['earnings_date']:
            return datetime.strptime(rows[0]['earnings_date'], '%Y-%m-%d').date()
        return None

    def get_upcoming_earnings(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get symbols with earnings in next N days."""
        query = """
            SELECT * FROM earnings
            WHERE earnings_date BETWEEN DATE('now') AND DATE('now', ? || ' days')
            ORDER BY earnings_date
        """
        return self.db.execute(query, (days_ahead,)) or []


class PicksDAO(BaseDAO):
    """DAO for picks table operations."""

    def insert_picks(self, picks: List[Dict[str, Any]]) -> List[int]:
        """
        Insert screened picks.

        Args:
            picks: List of pick dictionaries from screeners

        Returns:
            List of inserted pick IDs
        """
        query = """
            INSERT INTO picks
            (asof, symbol, strategy, selected_option, strike, expiry, premium,
             roi_30d, iv_rank, score, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        pick_ids = []
        for pick in picks:
            params = (
                pick.get('asof', date.today()),
                pick['symbol'],
                pick['strategy'],
                pick['selected_option'],
                pick['strike'],
                pick['expiry'],
                pick['premium'],
                pick['roi_30d'],
                pick['iv_rank'],
                pick.get('score', 0),
                pick.get('notes', '')
            )
            self.db.execute(query, params)

            # Get last inserted ID
            id_rows = self.db.execute("SELECT last_insert_rowid() as id")
            if id_rows:
                pick_ids.append(id_rows[0]['id'])

        self.logger.info(f"Inserted {len(picks)} picks")
        return pick_ids

    def get_picks_by_date(self, asof: date, strategy: str = None) -> List[Dict[str, Any]]:
        """
        Get picks for a specific date.

        Args:
            asof: Date to query
            strategy: Optional filter by strategy (CC or CSP)

        Returns:
            List of pick records
        """
        if strategy:
            query = """
                SELECT * FROM picks
                WHERE asof = ? AND strategy = ?
                ORDER BY score DESC
            """
            return self.db.execute(query, (asof, strategy)) or []
        else:
            query = """
                SELECT * FROM picks
                WHERE asof = ?
                ORDER BY strategy, score DESC
            """
            return self.db.execute(query, (asof,)) or []

    def get_top_picks(self, asof: date, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N picks by score for a date."""
        query = """
            SELECT * FROM picks
            WHERE asof = ?
            ORDER BY score DESC
            LIMIT ?
        """
        return self.db.execute(query, (asof, limit)) or []

    def update_pick_score(self, pick_id: int, score: float) -> None:
        """Update the score for a pick."""
        query = "UPDATE picks SET score = ? WHERE id = ?"
        self.db.execute(query, (score, pick_id))


class RationalesDAO(BaseDAO):
    """DAO for rationales table operations."""

    def insert_rationale(self, pick_id: int, summary: str) -> None:
        """
        Insert AI-generated rationale for a pick.

        Args:
            pick_id: ID of the associated pick
            summary: Generated summary text
        """
        query = """
            INSERT INTO rationales (pick_id, summary)
            VALUES (?, ?)
        """
        self.db.execute(query, (pick_id, summary))

    def get_rationale(self, pick_id: int) -> Optional[str]:
        """Get rationale for a pick."""
        query = "SELECT summary FROM rationales WHERE pick_id = ?"
        rows = self.db.execute(query, (pick_id,))
        return rows[0]['summary'] if rows else None

    def get_picks_needing_rationales(self) -> List[int]:
        """Get pick IDs that don't have rationales yet."""
        query = """
            SELECT p.id FROM picks p
            LEFT JOIN rationales r ON p.id = r.pick_id
            WHERE r.pick_id IS NULL
            ORDER BY p.score DESC
        """
        rows = self.db.execute(query)
        return [row['id'] for row in rows] if rows else []


class AlertsDAO(BaseDAO):
    """DAO for alerts table operations."""

    def record_alert(self, pick_id: int, channel: str, status: str, error: str = None) -> None:
        """
        Record alert attempt.

        Args:
            pick_id: ID of the pick
            channel: Alert channel (telegram, email, etc.)
            status: Status (sent, failed, pending)
            error: Error message if failed
        """
        query = """
            INSERT INTO alerts (pick_id, channel, status, sent_at, error)
            VALUES (?, ?, ?, DATETIME('now'), ?)
        """
        self.db.execute(query, (pick_id, channel, status, error))

    def get_sent_alerts(self, asof: date, channel: str = 'telegram') -> List[int]:
        """Get pick IDs that have been alerted."""
        query = """
            SELECT DISTINCT a.pick_id
            FROM alerts a
            JOIN picks p ON a.pick_id = p.id
            WHERE p.asof = ? AND a.channel = ? AND a.status = 'sent'
        """
        rows = self.db.execute(query, (asof, channel))
        return [row['pick_id'] for row in rows] if rows else []

    def mark_alert_sent(self, pick_id: int, channel: str = 'telegram') -> None:
        """Mark an alert as successfully sent."""
        self.record_alert(pick_id, channel, 'sent')


class StatsDAO(BaseDAO):
    """DAO for aggregate statistics and reporting."""

    def get_daily_summary(self, asof: date) -> Dict[str, Any]:
        """
        Get daily screening summary statistics.

        Args:
            asof: Date to summarize

        Returns:
            Dictionary with summary stats
        """
        # Count picks by strategy
        count_query = """
            SELECT strategy, COUNT(*) as count, AVG(score) as avg_score
            FROM picks
            WHERE asof = ?
            GROUP BY strategy
        """
        counts = self.db.execute(count_query, (asof,)) or []

        # Get top performers
        top_query = """
            SELECT symbol, strategy, roi_30d, score
            FROM picks
            WHERE asof = ?
            ORDER BY score DESC
            LIMIT 3
        """
        top_picks = self.db.execute(top_query, (asof,)) or []

        return {
            'date': asof,
            'counts_by_strategy': {row['strategy']: row['count'] for row in counts},
            'avg_scores': {row['strategy']: row['avg_score'] for row in counts},
            'top_picks': top_picks
        }

    def get_historical_performance(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get historical pick counts and average scores."""
        query = """
            SELECT asof, strategy, COUNT(*) as count, AVG(score) as avg_score
            FROM picks
            WHERE asof >= DATE('now', ? || ' days')
            GROUP BY asof, strategy
            ORDER BY asof DESC
        """
        return self.db.execute(query, (-days_back,)) or []