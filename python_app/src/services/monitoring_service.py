"""
Monitoring and error tracking service for the Options Income Screener.

Provides health checks, failure tracking, performance metrics, and alerting.
Python 3.12 compatible following CLAUDE.md standards.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from pathlib import Path

from .telegram_service import TelegramService


logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Comprehensive monitoring service for pipeline health and performance.

    Features:
    - Execution history tracking
    - Failure detection and alerting
    - Performance metrics
    - Dead man's switch (alert if pipeline hasn't run)
    - Health status reporting
    """

    def __init__(self, db_path: str = None):
        """
        Initialize monitoring service.

        Args:
            db_path: Path to SQLite database (defaults to project data/screener.db)
        """
        # Use absolute path by default
        if db_path is None:
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = str(project_root / "python_app" / "data" / "screener.db")

        self.db_path = db_path
        self.telegram = TelegramService()

        # Configuration
        self.max_consecutive_failures = 3
        self.max_hours_without_run = 26  # Alert if no run in 26 hours (> 1 day)
        self.performance_threshold_seconds = 300  # Alert if run takes > 5 minutes

        # Ensure monitoring tables exist
        self._init_monitoring_tables()

    def _init_monitoring_tables(self):
        """Create monitoring tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Pipeline execution history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date DATE NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL,
                    symbols_attempted INTEGER DEFAULT 0,
                    symbols_succeeded INTEGER DEFAULT 0,
                    symbols_failed INTEGER DEFAULT 0,
                    total_picks INTEGER DEFAULT 0,
                    cc_picks INTEGER DEFAULT 0,
                    csp_picks INTEGER DEFAULT 0,
                    api_calls INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    error_message TEXT,
                    error_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Performance metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_unit TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id)
                )
            ''')

            # Alert history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    sent_via TEXT,
                    acknowledged BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            conn.close()
            logger.info("Monitoring tables initialized")

        except Exception as e:
            logger.error(f"Error initializing monitoring tables: {e}")

    def record_pipeline_start(self, run_date: date = None) -> int:
        """
        Record the start of a pipeline run.

        Args:
            run_date: Date of the run (defaults to today)

        Returns:
            Run ID for tracking
        """
        run_date = run_date or date.today()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pipeline_runs (
                    run_date, started_at, status
                ) VALUES (?, ?, ?)
            ''', (
                run_date.isoformat(),
                datetime.now().isoformat(),
                'running'
            ))

            run_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Pipeline run {run_id} started")
            return run_id

        except Exception as e:
            logger.error(f"Error recording pipeline start: {e}")
            return -1

    def record_pipeline_completion(
        self,
        run_id: int,
        status: str,
        stats: Dict[str, Any],
        error_message: str = None
    ):
        """
        Record the completion of a pipeline run.

        Args:
            run_id: Run ID from record_pipeline_start
            status: 'success', 'partial', or 'failed'
            stats: Pipeline statistics dictionary
            error_message: Error message if failed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE pipeline_runs
                SET completed_at = ?,
                    status = ?,
                    symbols_attempted = ?,
                    symbols_succeeded = ?,
                    symbols_failed = ?,
                    total_picks = ?,
                    cc_picks = ?,
                    csp_picks = ?,
                    api_calls = ?,
                    duration_seconds = ?,
                    error_message = ?,
                    error_details = ?
                WHERE id = ?
            ''', (
                datetime.now().isoformat(),
                status,
                stats.get('symbols_attempted', 0),
                stats.get('symbols_succeeded', 0),
                stats.get('symbols_failed', 0),
                stats.get('total_picks', 0),
                stats.get('cc_picks', 0),
                stats.get('csp_picks', 0),
                stats.get('api_calls', 0),
                stats.get('duration', 0),
                error_message,
                json.dumps(stats.get('errors', [])),
                run_id
            ))

            conn.commit()
            conn.close()

            logger.info(f"Pipeline run {run_id} completed with status: {status}")

            # Check for alerting conditions
            self._check_failure_alerts(run_id, status, stats)
            self._check_performance_alerts(run_id, stats)

        except Exception as e:
            logger.error(f"Error recording pipeline completion: {e}")

    def record_metric(self, run_id: int, metric_name: str, value: float, unit: str = None):
        """
        Record a performance metric.

        Args:
            run_id: Run ID
            metric_name: Name of the metric
            value: Metric value
            unit: Optional unit (e.g., 'seconds', 'count')
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO performance_metrics (
                    run_id, metric_name, metric_value, metric_unit
                ) VALUES (?, ?, ?, ?)
            ''', (run_id, metric_name, value, unit))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error recording metric: {e}")

    def _check_failure_alerts(self, run_id: int, status: str, stats: Dict):
        """Check if failure alerts should be sent."""
        if status == 'failed':
            # Get consecutive failure count
            consecutive_failures = self._get_consecutive_failures()

            if consecutive_failures >= self.max_consecutive_failures:
                self._send_alert(
                    alert_type='consecutive_failures',
                    severity='critical',
                    message=f"⚠️ **{consecutive_failures} Consecutive Pipeline Failures**",
                    details={
                        'consecutive_failures': consecutive_failures,
                        'threshold': self.max_consecutive_failures,
                        'last_run_id': run_id
                    }
                )

        # Check symbol failure rate
        if stats.get('symbols_attempted', 0) > 0:
            failure_rate = stats.get('symbols_failed', 0) / stats['symbols_attempted']
            if failure_rate > 0.5:  # More than 50% failed
                self._send_alert(
                    alert_type='high_failure_rate',
                    severity='warning',
                    message=f"⚠️ **High Symbol Failure Rate: {failure_rate:.1%}**",
                    details={
                        'symbols_attempted': stats['symbols_attempted'],
                        'symbols_failed': stats['symbols_failed'],
                        'failure_rate': failure_rate
                    }
                )

    def _check_performance_alerts(self, run_id: int, stats: Dict):
        """Check if performance alerts should be sent."""
        duration = stats.get('duration', 0)

        if duration > self.performance_threshold_seconds:
            self._send_alert(
                alert_type='slow_performance',
                severity='info',
                message=f"⏱️ **Slow Pipeline Execution: {duration:.1f}s**",
                details={
                    'duration_seconds': duration,
                    'threshold_seconds': self.performance_threshold_seconds,
                    'run_id': run_id
                }
            )

    def check_dead_mans_switch(self):
        """
        Check if pipeline hasn't run recently (dead man's switch).
        Should be called independently of pipeline execution.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get last run
            cursor.execute('''
                SELECT started_at, status
                FROM pipeline_runs
                ORDER BY started_at DESC
                LIMIT 1
            ''')

            result = cursor.fetchone()
            conn.close()

            if not result:
                # No runs recorded
                self._send_alert(
                    alert_type='dead_mans_switch',
                    severity='critical',
                    message="🚨 **No Pipeline Runs Recorded**",
                    details={'message': 'No pipeline execution history found'}
                )
                return

            last_run_time = datetime.fromisoformat(result[0])
            hours_since_run = (datetime.now() - last_run_time).total_seconds() / 3600

            if hours_since_run > self.max_hours_without_run:
                self._send_alert(
                    alert_type='dead_mans_switch',
                    severity='critical',
                    message=f"🚨 **Pipeline Not Running**\n\nLast run: {hours_since_run:.1f} hours ago",
                    details={
                        'last_run_time': last_run_time.isoformat(),
                        'hours_since_run': hours_since_run,
                        'threshold_hours': self.max_hours_without_run
                    }
                )

        except Exception as e:
            logger.error(f"Error checking dead man's switch: {e}")

    def _get_consecutive_failures(self) -> int:
        """Get count of consecutive failures."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT status
                FROM pipeline_runs
                ORDER BY started_at DESC
                LIMIT 10
            ''')

            rows = cursor.fetchall()
            conn.close()

            consecutive = 0
            for row in rows:
                if row[0] == 'failed':
                    consecutive += 1
                else:
                    break

            return consecutive

        except Exception as e:
            logger.error(f"Error getting consecutive failures: {e}")
            return 0

    def _send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict = None
    ):
        """
        Send an alert via Telegram and record it.

        Args:
            alert_type: Type of alert
            severity: 'info', 'warning', or 'critical'
            message: Alert message
            details: Additional details dictionary
        """
        try:
            # Format alert message
            severity_emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'critical': '🚨'
            }

            full_message = f"{severity_emoji.get(severity, '📊')} **Monitoring Alert**\n"
            full_message += f"━━━━━━━━━━━━━━━━━━━━\n"
            full_message += f"{message}\n"
            full_message += f"━━━━━━━━━━━━━━━━━━━━\n"
            full_message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            full_message += f"🔔 Type: {alert_type}\n"
            full_message += f"📊 Severity: {severity.upper()}"

            # Send via Telegram
            sent = self.telegram.send_message(full_message)

            # Record alert
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO monitoring_alerts (
                    alert_type, severity, message, details, sent_via
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                alert_type,
                severity,
                message,
                json.dumps(details) if details else None,
                'telegram' if sent else 'failed'
            ))

            conn.commit()
            conn.close()

            logger.info(f"Alert sent: {alert_type} ({severity})")

        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the system.

        Returns:
            Dictionary with health status information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Last run info
            cursor.execute('''
                SELECT id, run_date, started_at, completed_at, status,
                       symbols_attempted, symbols_succeeded, symbols_failed,
                       total_picks, duration_seconds
                FROM pipeline_runs
                ORDER BY started_at DESC
                LIMIT 1
            ''')

            last_run = cursor.fetchone()

            # Success rate (last 7 days)
            cursor.execute('''
                SELECT
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs
                FROM pipeline_runs
                WHERE started_at >= datetime('now', '-7 days')
            ''')

            week_stats = cursor.fetchone()

            # Recent alerts
            cursor.execute('''
                SELECT COUNT(*)
                FROM monitoring_alerts
                WHERE created_at >= datetime('now', '-24 hours')
                AND severity IN ('warning', 'critical')
            ''')

            recent_alerts = cursor.fetchone()[0]

            conn.close()

            # Calculate health score
            health_score = 100
            status = 'healthy'

            if last_run:
                last_run_time = datetime.fromisoformat(last_run[2])
                hours_since_run = (datetime.now() - last_run_time).total_seconds() / 3600

                if hours_since_run > self.max_hours_without_run:
                    health_score -= 50
                    status = 'critical'
                elif last_run[4] == 'failed':
                    health_score -= 30
                    status = 'degraded'

                # Check symbol success rate
                if last_run[5] > 0:  # symbols_attempted
                    success_rate = last_run[6] / last_run[5]  # succeeded / attempted
                    if success_rate < 0.5:
                        health_score -= 20
                        if status == 'healthy':
                            status = 'degraded'
            else:
                health_score = 0
                status = 'critical'

            # Weekly success rate
            weekly_success_rate = 0
            if week_stats and week_stats[0] > 0:
                weekly_success_rate = (week_stats[1] / week_stats[0]) * 100
                if weekly_success_rate < 80:
                    health_score -= 15

            # Recent alerts
            if recent_alerts > 5:
                health_score -= 10

            health_score = max(0, health_score)

            return {
                'status': status,
                'health_score': health_score,
                'last_run': {
                    'id': last_run[0] if last_run else None,
                    'date': last_run[1] if last_run else None,
                    'started_at': last_run[2] if last_run else None,
                    'completed_at': last_run[3] if last_run else None,
                    'status': last_run[4] if last_run else None,
                    'symbols_attempted': last_run[5] if last_run else 0,
                    'symbols_succeeded': last_run[6] if last_run else 0,
                    'total_picks': last_run[8] if last_run else 0,
                    'duration_seconds': last_run[9] if last_run else 0
                } if last_run else None,
                'weekly_stats': {
                    'total_runs': week_stats[0] if week_stats else 0,
                    'successful_runs': week_stats[1] if week_stats else 0,
                    'success_rate': weekly_success_rate
                },
                'recent_alerts_24h': recent_alerts,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                'status': 'unknown',
                'health_score': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get performance summary for the last N days.

        Args:
            days: Number of days to include

        Returns:
            Performance summary dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    AVG(api_calls) as avg_api_calls,
                    AVG(total_picks) as avg_picks,
                    COUNT(*) as total_runs
                FROM pipeline_runs
                WHERE started_at >= datetime('now', ? || ' days')
                AND status = 'success'
            ''', (f'-{days}',))

            stats = cursor.fetchone()
            conn.close()

            return {
                'period_days': days,
                'total_runs': stats[5] if stats else 0,
                'avg_duration_seconds': round(stats[0], 2) if stats and stats[0] else 0,
                'min_duration_seconds': round(stats[1], 2) if stats and stats[1] else 0,
                'max_duration_seconds': round(stats[2], 2) if stats and stats[2] else 0,
                'avg_api_calls': round(stats[3], 2) if stats and stats[3] else 0,
                'avg_picks': round(stats[4], 2) if stats and stats[4] else 0
            }

        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
