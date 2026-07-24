import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.logger import logger


class HistoryDatabase:
    """Thread-safe SQLite storage for notification history."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates the notification history table if it doesn't exist."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS notification_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_name TEXT NOT NULL,
                        message TEXT NOT NULL,
                        icon_path TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(
                "Failed to initialize notification database",
                extra={"error_type": type(e).__name__},
            )

    def add_notification(
        self, app_name: str, message: str, icon_path: Optional[str] = None
    ) -> Optional[int]:
        """Saves a notification to history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO notification_history (app_name, message, icon_path, timestamp)
                    VALUES (?, ?, ?, ?)
                """,
                    (app_name, message, icon_path, datetime.now().isoformat()),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(
                "Error inserting notification into history",
                extra={"error_type": type(e).__name__},
            )
            return None

    def get_notifications_count(self) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM notification_history")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(
                "Error fetching notification count",
                extra={"error_type": type(e).__name__},
            )
            return 0

    def get_notifications_by_range(self, time_range: str) -> List[Dict[str, Any]]:
        """Fetches notifications filtered by date range."""
        now = datetime.now()
        where_clause = ""
        params: list = []

        if time_range == "Today":
            start_of_day = datetime(now.year, now.month, now.day)
            where_clause = "WHERE timestamp >= ?"
            params.append(start_of_day.isoformat())

        elif time_range == "Yesterday":
            start_today = datetime(now.year, now.month, now.day)
            start_yesterday = start_today - timedelta(days=1)
            where_clause = "WHERE timestamp >= ? AND timestamp < ?"
            params.extend([start_yesterday.isoformat(), start_today.isoformat()])

        elif time_range == "Last 7 Days":
            seven_days_ago = now - timedelta(days=7)
            where_clause = "WHERE timestamp >= ?"
            params.append(seven_days_ago.isoformat())

        elif time_range == "This Month":
            start_of_month = datetime(now.year, now.month, 1)
            where_clause = "WHERE timestamp >= ?"
            params.append(start_of_month.isoformat())

        query = f"""
            SELECT id, app_name, message, icon_path, timestamp 
            FROM notification_history 
            {where_clause} 
            ORDER BY timestamp DESC
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(
                "Error querying notifications by range",
                extra={
                    "range_requested": time_range,
                    "error_type": type(e).__name__,
                },
            )
            return []

    def delete_notification(self, notification_id: int) -> None:
        """Deletes a single notification by ID."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM notification_history WHERE id = ?",
                    (notification_id,),
                )
                conn.commit()
        except Exception as e:
            logger.error(
                "Error deleting notification",
                extra={"error_type": type(e).__name__},
            )

    def delete_notifications_by_ids(self, notification_ids: List[int]) -> None:
        """Delete specific notifications by their IDs."""
        if not notification_ids:
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    "DELETE FROM notification_history WHERE id = ?",
                    [(nid,) for nid in notification_ids],
                )
                conn.commit()
        except Exception as e:
            logger.error(
                "Error batch deleting notifications",
                extra={"error_type": type(e).__name__},
            )

    def clear_all(self) -> None:
        """Wipes all notification history."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM notification_history")
                conn.commit()
            logger.info("Cleared all notification history.")
        except Exception as e:
            logger.error(
                "Error clearing notification history",
                extra={"error_type": type(e).__name__},
            )
