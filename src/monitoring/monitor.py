import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from ..collector.vtu_scraper import VTUScraper
from ..database.database import Database
from ..database.models import Internship
from ..matching.priority_scorer import PriorityScorer
from ..matching.skill_matcher import SkillMatcher
from ..matching.skill_profile import SkillProfile
from ..notifications.email import EmailNotifier
from ..notifications.telegram import TelegramNotifier
from ..utils.logger import get_logger


logger = get_logger("vtu_monitor")


class InternshipMonitor:
    """Master orchestrator for the VTU Internship Watcher."""

    # ==============================================================
    # FIELDS THAT SHOULD TRIGGER UPDATE NOTIFICATIONS
    # ==============================================================

    TRACKED_FIELDS = (
        "vacancy",
        "application_status",
        "deadline",
        "fee",
        "mode",
        "stipend",
        "internship_type",
        "location",
        "duration",
    )

    def __init__(
        self,
        db_path: str = "data/internships.db",
        config_path: str = "config/config.yaml",
        skills_path: str = "config/skills.yaml",
    ):
        self.db = Database(db_path)

        self.skill_profile = SkillProfile(
            skills_path
        )

        self.matcher = SkillMatcher(
            self.skill_profile
        )

        self.scorer = PriorityScorer(
            config_path
        )

        self.scraper = VTUScraper()

        self.telegram = TelegramNotifier()

        self.email = EmailNotifier()

    # ==============================================================
    # NORMALIZATION
    # ==============================================================

    @staticmethod
    def _normalize_value(value: Any) -> str:
        """
        Convert a database/portal value into a stable string
        for comparison.
        """
        if value is None:
            return ""

        if isinstance(value, float):
            return f"{value:.4f}"

        return str(value).strip()

    # ==============================================================
    # CHANGE DETECTION
    # ==============================================================

    def detect_changes(
        self,
        old_item: Internship,
        new_item: Internship,
    ) -> Dict[str, Tuple[str, str]]:
        """
        Compare an existing internship with its latest portal data.

        Returns:
            {
                "vacancy": ("10", "5"),
                "application_status": ("OPEN", "CLOSED"),
            }
        """

        changes: Dict[str, Tuple[str, str]] = {}

        for field in self.TRACKED_FIELDS:

            old_value = self._normalize_value(
                getattr(old_item, field, "")
            )

            new_value = self._normalize_value(
                getattr(new_item, field, "")
            )

            if old_value != new_value:
                changes[field] = (
                    old_value,
                    new_value,
                )

        return changes

    # ==============================================================
    # EVENT ID
    # ==============================================================

    def build_event_key(
        self,
        portal_id: str,
        changes: Dict[str, Tuple[str, str]],
    ) -> str:
        """
        Creates a deterministic notification key.

        Different changes produce different keys.

        Example:

            vacancy 10 -> 5
        !=
            vacancy 5 -> 2
        """

        parts = []

        for field in sorted(changes):

            old_value, new_value = changes[field]

            parts.append(
                f"{field}|{old_value}|{new_value}"
            )

        raw_key = (
            f"{portal_id}::"
            + "::".join(parts)
        )

        digest = hashlib.sha256(
            raw_key.encode("utf-8")
        ).hexdigest()[:16]

        return f"telegram_update_{digest}"

    # ==============================================================
    # SHOULD NOTIFY?
    # ==============================================================

    def should_notify_update(
        self,
        old_item: Internship,
        new_item: Internship,
    ) -> bool:
        """
        Avoid unnecessary notifications for internships that are
        completely irrelevant both before and after the update.

        If an internship was relevant before OR becomes relevant
        after the update, important changes are eligible for alerts.
        """

        return (
            old_item.priority_level != "IGNORE"
            or new_item.priority_level != "IGNORE"
        )

    # ==============================================================
    # SEND UPDATE
    # ==============================================================

    def _send_update_notification(
        self,
        old_item: Internship,
        new_item: Internship,
        changes: Dict[str, Tuple[str, str]],
    ) -> bool:
        """
        Send a change notification only once for the exact
        old -> new transition.
        """

        if not changes:
            return False

        if not self.should_notify_update(
            old_item,
            new_item,
        ):
            logger.debug(
                f"Skipping update for irrelevant internship: "
                f"{new_item.title}"
            )
            return False

        notification_type = self.build_event_key(
            new_item.portal_id,
            changes,
        )

        # ----------------------------------------------------------
        # EVENT-SPECIFIC DEDUPLICATION
        # ----------------------------------------------------------

        if self.db.is_notification_sent(
            new_item.portal_id,
            notification_type,
        ):
            logger.info(
                f"Update already notified: "
                f"{new_item.title}"
            )
            return False

        # ----------------------------------------------------------
        # SEND TELEGRAM
        # ----------------------------------------------------------

        sent = self.telegram.send_update_alert(
            new_item,
            changes,
        )

        if not sent:
            return False

        # ----------------------------------------------------------
        # RECORD ONLY AFTER SUCCESS
        # ----------------------------------------------------------

        self.db.record_notification(
            new_item.id,
            new_item.portal_id,
            notification_type,
            status="SUCCESS",
        )

        logger.info(
            f"Update notification recorded: "
            f"{new_item.title}"
        )

        return True

    # ==============================================================
    # PROCESS NEW INTERNSHIP
    # ==============================================================

    def _process_new_internship(
        self,
        item: Internship,
        dry_run: bool,
    ) -> Tuple[Internship, bool]:
        """
        Process a newly discovered internship.
        """

        enriched_item = self.scraper.fetch_detail(
            item
        )

        # ----------------------------------------------------------
        # TECHNICAL MATCH
        # ----------------------------------------------------------

        technical_score, matched_skills = (
            self.matcher.evaluate_internship(
                enriched_item
            )
        )

        enriched_item.technical_score = (
            technical_score
        )

        enriched_item.matched_skills = (
            matched_skills
        )

        # ----------------------------------------------------------
        # PRIORITY
        # ----------------------------------------------------------

        priority_score, priority_level = (
            self.scorer.calculate_priority(
                enriched_item
            )
        )

        enriched_item.priority_score = (
            priority_score
        )

        enriched_item.priority_level = (
            priority_level
        )

        # ----------------------------------------------------------
        # SAVE
        # ----------------------------------------------------------

        if not dry_run:

            row_id = self.db.save_internship(
                enriched_item
            )

            enriched_item.id = row_id

        # ----------------------------------------------------------
        # NOTIFY
        # ----------------------------------------------------------

        alert_sent = False

        if priority_level in (
            "VERY_HIGH",
            "HIGH",
            "MEDIUM",
        ):

            if dry_run:

                logger.info(
                    f"[DRY-RUN] Would notify: "
                    f"{enriched_item.title} "
                    f"({priority_level}, "
                    f"Match: {technical_score}%)"
                )

                alert_sent = True

            else:

                already_sent = (
                    self.db.is_notification_sent(
                        enriched_item.portal_id,
                        "telegram",
                    )
                )

                if not already_sent:

                    sent = self.telegram.send_alert(
                        enriched_item
                    )

                    if sent:

                        alert_sent = True

                        self.db.record_notification(
                            enriched_item.id,
                            enriched_item.portal_id,
                            "telegram",
                            status="SUCCESS",
                        )

        return enriched_item, alert_sent

    # ==============================================================
    # PROCESS EXISTING INTERNSHIP
    # ==============================================================

    def _process_existing_internship(
        self,
        old_item: Internship,
        scraped_item: Internship,
        dry_run: bool,
    ) -> Tuple[Internship, Dict[str, Tuple[str, str]], bool]:
        """
        Fetch latest details, calculate scores, compare with the
        database record, and notify about important changes.
        """

        # ----------------------------------------------------------
        # FETCH DETAIL PAGE
        # ----------------------------------------------------------

        current_item = self.scraper.fetch_detail(
            scraped_item
        )

        # ----------------------------------------------------------
        # RE-CALCULATE TECHNICAL MATCH
        # ----------------------------------------------------------

        technical_score, matched_skills = (
            self.matcher.evaluate_internship(
                current_item
            )
        )

        current_item.technical_score = (
            technical_score
        )

        current_item.matched_skills = (
            matched_skills
        )

        # ----------------------------------------------------------
        # RE-CALCULATE PRIORITY
        # ----------------------------------------------------------

        priority_score, priority_level = (
            self.scorer.calculate_priority(
                current_item
            )
        )

        current_item.priority_score = (
            priority_score
        )

        current_item.priority_level = (
            priority_level
        )

        # Preserve database row ID.
        current_item.id = old_item.id

        # ----------------------------------------------------------
        # COMPARE BEFORE DATABASE UPDATE
        # ----------------------------------------------------------

        changes = self.detect_changes(
            old_item,
            current_item,
        )

        alert_sent = False

        if changes:

            logger.info(
                f"Detected {len(changes)} change(s) "
                f"for: {current_item.title}"
            )

            for field, (
                old_value,
                new_value,
            ) in changes.items():

                logger.info(
                    f"  {field}: "
                    f"{old_value!r} -> {new_value!r}"
                )

            # ------------------------------------------------------
            # DRY RUN
            # ------------------------------------------------------

            if dry_run:

                if self.should_notify_update(
                    old_item,
                    current_item,
                ):
                    logger.info(
                        f"[DRY-RUN] Would send update: "
                        f"{current_item.title}"
                    )
                    alert_sent = True

            else:

                alert_sent = (
                    self._send_update_notification(
                        old_item,
                        current_item,
                        changes,
                    )
                )

        # ----------------------------------------------------------
        # ALWAYS UPDATE CURRENT DATABASE SNAPSHOT
        # ----------------------------------------------------------

        if not dry_run:

            row_id = self.db.save_internship(
                current_item
            )

            current_item.id = row_id

        return (
            current_item,
            changes,
            alert_sent,
        )

    # ==============================================================
    # MAIN CHECK
    # ==============================================================

    def run_check(
        self,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Run one complete monitoring cycle."""

        listings = self.scraper.fetch_listings()

        total_found = len(listings)

        new_items: List[Internship] = []

        changed_items: List[Internship] = []

        relevant_count = 0

        high_priority_count = 0

        alerts_sent = 0

        # ----------------------------------------------------------
        # NO DATA SAFETY
        # ----------------------------------------------------------

        if not listings:

            logger.warning(
                "No internships returned from portal. "
                "Database will NOT be modified."
            )

            return {
                "total_found": 0,
                "new_count": 0,
                "changed_count": 0,
                "relevant_count": 0,
                "high_priority_count": 0,
                "alerts_sent": 0,
                "items": [],
                "changed_items": [],
            }

        # ----------------------------------------------------------
        # PROCESS LISTINGS
        # ----------------------------------------------------------

        for scraped_item in listings:

            old_item = self.db.get_internship_by_portal_id(
                scraped_item.portal_id
            )

            # ======================================================
            # NEW
            # ======================================================

            if old_item is None:

                processed_item, alert_sent = (
                    self._process_new_internship(
                        scraped_item,
                        dry_run,
                    )
                )

                new_items.append(
                    processed_item
                )

                if (
                    processed_item.priority_level
                    != "IGNORE"
                ):
                    relevant_count += 1

                if processed_item.priority_level in (
                    "VERY_HIGH",
                    "HIGH",
                ):
                    high_priority_count += 1

                if alert_sent:
                    alerts_sent += 1

                continue

            # ======================================================
            # EXISTING
            # ======================================================

            (
                current_item,
                changes,
                alert_sent,
            ) = self._process_existing_internship(
                old_item,
                scraped_item,
                dry_run,
            )

            if changes:

                changed_items.append(
                    current_item
                )

            if (
                current_item.priority_level
                != "IGNORE"
            ):
                relevant_count += 1

            if current_item.priority_level in (
                "VERY_HIGH",
                "HIGH",
            ):
                high_priority_count += 1

            if alert_sent:
                alerts_sent += 1

        # ----------------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------------

        summary = {
            "total_found": total_found,
            "new_count": len(new_items),
            "changed_count": len(changed_items),
            "relevant_count": relevant_count,
            "high_priority_count": high_priority_count,
            "alerts_sent": alerts_sent,
            "items": new_items,
            "changed_items": changed_items,
        }

        logger.info(
            f"Cycle finished: "
            f"{total_found} total, "
            f"{len(new_items)} new, "
            f"{len(changed_items)} changed, "
            f"{relevant_count} relevant, "
            f"{high_priority_count} high-priority, "
            f"{alerts_sent} alerts sent."
        )

        return summary

    # ==============================================================
    # CONTINUOUS LOOP
    # ==============================================================

    def start_loop(
        self,
        interval_minutes: int = 30,
    ) -> None:
        """Continuously monitor the VTU portal."""

        logger.info(
            f"Starting continuous watcher "
            f"(interval: {interval_minutes} minutes)"
        )

        try:

            while True:

                try:
                    self.run_check()

                except Exception as exc:

                    logger.exception(
                        f"Monitoring cycle failed: {exc}"
                    )

                time.sleep(
                    interval_minutes * 60
                )

        except KeyboardInterrupt:

            logger.info(
                "Watcher stopped by user."
            )