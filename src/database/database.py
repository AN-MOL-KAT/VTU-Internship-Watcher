import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Internship, Notification
from ..utils.logger import get_logger


logger = get_logger("vtu_database")


class Database:
    """SQLite Database manager for VTU Internship Watcher."""

    def __init__(self, db_path: str = "data/internships.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ==============================================================
    # CONNECTION
    # ==============================================================

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==============================================================
    # DATABASE INITIALIZATION
    # ==============================================================

    def _init_db(self) -> None:
        """Initializes database schema if tables do not exist."""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ------------------------------------------------------
            # Internships table
            # ------------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portal_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    description TEXT,
                    skills TEXT,
                    category TEXT,
                    location TEXT,
                    mode TEXT,
                    internship_type TEXT,
                    fee REAL DEFAULT 0.0,
                    stipend TEXT,
                    duration TEXT,
                    vacancy TEXT,
                    application_status TEXT,
                    deadline TEXT,
                    url TEXT,
                    technical_score REAL DEFAULT 0.0,
                    matched_skills TEXT,
                    priority_score REAL DEFAULT 0.0,
                    priority_level TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )

            # ------------------------------------------------------
            # Notifications table
            # ------------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    internship_id INTEGER NOT NULL,
                    portal_id TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    status TEXT DEFAULT 'SUCCESS',
                    FOREIGN KEY (internship_id) REFERENCES internships(id)
                )
                """
            )

            # ------------------------------------------------------
            # Indexes
            # ------------------------------------------------------

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_portal_id
                ON internships(portal_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_priority
                ON internships(priority_level)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_notif_lookup
                ON notifications(portal_id, notification_type)
                """
            )

            conn.commit()

    # ==============================================================
    # ROW -> INTERNSHIP
    # ==============================================================

    def _row_to_internship(
        self,
        row: sqlite3.Row,
    ) -> Internship:
        """Converts a SQLite row into an Internship object."""

        skills = (
            json.loads(row["skills"])
            if row["skills"]
            else []
        )

        matched_skills = (
            json.loads(row["matched_skills"])
            if row["matched_skills"]
            else []
        )

        return Internship(
            id=row["id"],
            portal_id=row["portal_id"],
            title=row["title"],
            company=row["company"],
            description=row["description"] or "",
            skills=skills,
            category=row["category"] or "",
            location=row["location"] or "",
            mode=row["mode"] or "Onsite",
            internship_type=row["internship_type"] or "Free",
            fee=row["fee"] or 0.0,
            stipend=row["stipend"] or "",
            duration=row["duration"] or "",
            vacancy=row["vacancy"] or "",
            application_status=(
                row["application_status"] or "OPEN"
            ),
            deadline=row["deadline"] or "",
            url=row["url"] or "",
            technical_score=row["technical_score"] or 0.0,
            matched_skills=matched_skills,
            priority_score=row["priority_score"] or 0.0,
            priority_level=(
                row["priority_level"] or "IGNORE"
            ),
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )

    # ==============================================================
    # CHECK EXISTING INTERNSHIP
    # ==============================================================

    def is_internship_seen(
        self,
        portal_id: str,
    ) -> bool:
        """Checks if an internship already exists."""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 1
                FROM internships
                WHERE portal_id = ?
                """,
                (str(portal_id),),
            )

            return cursor.fetchone() is not None

    # ==============================================================
    # GET INTERNSHIP
    # ==============================================================

    def get_internship_by_portal_id(
        self,
        portal_id: str,
    ) -> Optional[Internship]:
        """Retrieves an internship using its portal ID."""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM internships
                WHERE portal_id = ?
                """,
                (str(portal_id),),
            )

            row = cursor.fetchone()

            if row:
                return self._row_to_internship(row)

            return None

    # ==============================================================
    # SAVE / UPDATE INTERNSHIP
    # ==============================================================

    def save_internship(
        self,
        item: Internship,
    ) -> int:
        """
        Inserts a new internship or updates an existing internship.

        Returns:
            Database row ID.
        """

        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ------------------------------------------------------
            # Check whether internship already exists
            # ------------------------------------------------------

            cursor.execute(
                """
                SELECT id, first_seen
                FROM internships
                WHERE portal_id = ?
                """,
                (str(item.portal_id),),
            )

            row = cursor.fetchone()

            # ------------------------------------------------------
            # Serialize lists
            # ------------------------------------------------------

            skills_json = json.dumps(item.skills)

            matched_skills_json = json.dumps(
                item.matched_skills
            )

            # ======================================================
            # UPDATE EXISTING INTERNSHIP
            # ======================================================

            if row:

                internship_id = row["id"]

                cursor.execute(
                    """
                    UPDATE internships SET
                        title = ?,
                        company = ?,
                        description = ?,
                        skills = ?,
                        category = ?,
                        location = ?,
                        mode = ?,
                        internship_type = ?,
                        fee = ?,
                        stipend = ?,
                        duration = ?,
                        vacancy = ?,
                        application_status = ?,
                        deadline = ?,
                        url = ?,
                        technical_score = ?,
                        matched_skills = ?,
                        priority_score = ?,
                        priority_level = ?,
                        last_seen = ?
                    WHERE id = ?
                    """,
                    (
                        item.title,
                        item.company,
                        item.description,
                        skills_json,
                        item.category,

                        # IMPORTANT:
                        # Save the actual location here.
                        item.location,

                        item.mode,
                        item.internship_type,
                        item.fee,
                        item.stipend,
                        item.duration,
                        item.vacancy,
                        item.application_status,
                        item.deadline,
                        item.url,
                        item.technical_score,
                        matched_skills_json,
                        item.priority_score,
                        item.priority_level,
                        now,
                        internship_id,
                    ),
                )

                conn.commit()

                return internship_id

            # ======================================================
            # INSERT NEW INTERNSHIP
            # ======================================================

            else:

                cursor.execute(
                    """
                    INSERT INTO internships (
                        portal_id,
                        title,
                        company,
                        description,
                        skills,
                        category,
                        location,
                        mode,
                        internship_type,
                        fee,
                        stipend,
                        duration,
                        vacancy,
                        application_status,
                        deadline,
                        url,
                        technical_score,
                        matched_skills,
                        priority_score,
                        priority_level,
                        first_seen,
                        last_seen
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        str(item.portal_id),
                        item.title,
                        item.company,
                        item.description,
                        skills_json,
                        item.category,
                        item.location,
                        item.mode,
                        item.internship_type,
                        item.fee,
                        item.stipend,
                        item.duration,
                        item.vacancy,
                        item.application_status,
                        item.deadline,
                        item.url,
                        item.technical_score,
                        matched_skills_json,
                        item.priority_score,
                        item.priority_level,
                        item.first_seen or now,
                        item.last_seen or now,
                    ),
                )

                conn.commit()

                return cursor.lastrowid

    # ==============================================================
    # NOTIFICATION CHECK
    # ==============================================================

    def is_notification_sent(
        self,
        portal_id: str,
        notification_type: str,
    ) -> bool:
        """
        Checks whether a successful notification of the specified
        type has already been recorded for an internship.
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 1
                FROM notifications
                WHERE portal_id = ?
                  AND notification_type = ?
                  AND status = 'SUCCESS'
                """,
                (
                    str(portal_id),
                    notification_type,
                ),
            )

            return cursor.fetchone() is not None

    # ==============================================================
    # RECORD NOTIFICATION
    # ==============================================================

    def record_notification(
        self,
        internship_id: int,
        portal_id: str,
        notification_type: str,
        status: str = "SUCCESS",
    ) -> int:
        """Records that a notification was dispatched."""

        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO notifications (
                    internship_id,
                    portal_id,
                    notification_type,
                    sent_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    internship_id,
                    str(portal_id),
                    notification_type,
                    now,
                    status,
                ),
            )

            conn.commit()

            return cursor.lastrowid

    # ==============================================================
    # GET ALL INTERNSHIPS
    # ==============================================================

    def get_all_internships(
        self,
        priority_level: Optional[str] = None,
    ) -> List[Internship]:
        """Retrieves all internships."""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if priority_level:

                cursor.execute(
                    """
                    SELECT *
                    FROM internships
                    WHERE priority_level = ?
                    ORDER BY priority_score DESC
                    """,
                    (priority_level,),
                )

            else:

                cursor.execute(
                    """
                    SELECT *
                    FROM internships
                    ORDER BY priority_score DESC
                    """
                )

            rows = cursor.fetchall()

            return [
                self._row_to_internship(row)
                for row in rows
            ]

    # ==============================================================
    # DATABASE STATISTICS
    # ==============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistical breakdown of internships."""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ------------------------------------------------------
            # Total internships
            # ------------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM internships
                """
            )

            total = cursor.fetchone()["total"]

            # ------------------------------------------------------
            # Priority breakdown
            # ------------------------------------------------------

            cursor.execute(
                """
                SELECT
                    priority_level,
                    COUNT(*) AS count
                FROM internships
                GROUP BY priority_level
                """
            )

            priority_counts = {
                row["priority_level"]: row["count"]
                for row in cursor.fetchall()
            }

            # ------------------------------------------------------
            # Notifications
            # ------------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM notifications
                """
            )

            notifications_sent = (
                cursor.fetchone()["total"]
            )

            return {
                "total_internships": total,
                "priority_counts": priority_counts,
                "notifications_sent": notifications_sent,
            }