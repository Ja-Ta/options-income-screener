"""
Database connection manager for the Options Income Screener.

Manages SQLite connections with WAL mode and thread safety.
Python 3.12 compatible following CLAUDE.md standards.
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, Generator
from ..config import DB_URL
from ..utils.logging import get_logger


class Database:
    """SQLite database connection manager with WAL mode support."""

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection manager.

        Args:
            db_url: Database file path (defaults to config.DB_URL)
        """
        self.db_url = db_url or DB_URL
        self.logger = get_logger()

        # Ensure database directory exists
        db_path = os.path.dirname(os.path.abspath(self.db_url))
        os.makedirs(db_path, exist_ok=True)

        self._ensure_wal_mode()

    def _ensure_wal_mode(self) -> None:
        """Enable WAL mode for concurrent access."""
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=10000")  # 10 seconds
            self.logger.debug(f"Database initialized with WAL mode: {self.db_url}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get a database connection with proper error handling.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_url,
                timeout=30.0,
                isolation_level=None,  # Autocommit mode
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # Return rows as dicts
            yield conn
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def execute(self, query: str, params: tuple = ()) -> Optional[list]:
        """
        Execute a query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters (parameterized queries only)

        Returns:
            List of rows for SELECT queries, None for others
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                return None

    def execute_many(self, query: str, params_list: list[tuple]) -> None:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()

    def begin_transaction(self) -> sqlite3.Connection:
        """Begin an explicit transaction."""
        conn = sqlite3.connect(self.db_url)
        conn.isolation_level = 'DEFERRED'
        return conn

    def vacuum(self) -> None:
        """Vacuum the database to reclaim space."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            self.logger.info("Database vacuumed successfully")


# Global database instance
_db_instance = None


def get_database() -> Database:
    """Get singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance