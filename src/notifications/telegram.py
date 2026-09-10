import os
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

from ..database.models import Internship
from ..utils.helpers import format_currency
from ..utils.logger import get_logger

load_dotenv()
logger = get_logger("vtu_telegram")


class TelegramNotifier:
    """Dispatches real-time alerts via Telegram Bot API."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: int = 10,
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.timeout = timeout

    # ==============================================================
    # CONFIGURATION
    # ==============================================================

    def is_configured(self) -> bool:
        """Checks if valid credentials are provided."""
        return bool(self.bot_token and self.chat_id)

    # ==============================================================
    # COMMON TELEGRAM SENDER
    # ==============================================================

    def _send_message(self, message: str) -> bool:
        """Send a raw HTML-formatted Telegram message."""
        if not self.is_configured():
            logger.debug(
                "Telegram credentials not configured. Skipping message."
            )
            return False

        url = (
            f"https://api.telegram.org/bot"
            f"{self.bot_token}/sendMessage"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return True

            logger.error(
                f"Telegram API failed with code "
                f"{response.status_code}: {response.text}"
            )
            return False

        except requests.RequestException as exc:
            logger.error(
                f"Failed to deliver Telegram message: {exc}"
            )
            return False

    # ==============================================================
    # NEW INTERNSHIP MESSAGE
    # ==============================================================

    def format_message(self, item: Internship) -> str:
        """Formats a new internship into an alert message."""

        priority_emojis = {
            "VERY_HIGH": "🔥🔥🔥 VERY HIGH",
            "HIGH": "🟢 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW": "⚪ LOW",
            "IGNORE": "❌ IGNORE",
        }

        priority_display = priority_emojis.get(
            item.priority_level,
            item.priority_level,
        )

        # ----------------------------------------------------------
        # Money
        # ----------------------------------------------------------

        if item.stipend:
            money_line = f"💰 Stipend: {item.stipend}"

        elif item.fee > 0:
            money_line = (
                f"💳 Fee: {format_currency(item.fee)}"
            )

        else:
            money_line = "🆓 Free (No Fee)"

        # ----------------------------------------------------------
        # Mode
        # ----------------------------------------------------------

        mode_emojis = {
            "Remote": "🌐 Remote",
            "Hybrid": "🏢/🌐 Hybrid",
            "Onsite": "🏢 Onsite",
        }

        mode_line = mode_emojis.get(
            item.mode,
            f"📍 {item.mode}",
        )

        # ----------------------------------------------------------
        # Duration
        # ----------------------------------------------------------

        duration_line = (
            f"⏳ {item.duration}"
            if item.duration
            else "⏳ Duration: Not specified"
        )

        # ----------------------------------------------------------
        # Skills
        # ----------------------------------------------------------

        if item.matched_skills:
            skills_block = "\n".join(
                f"✓ {skill}"
                for skill in item.matched_skills[:6]
            )

        elif item.skills:
            skills_block = "\n".join(
                f"• {skill}"
                for skill in item.skills[:6]
            )

        else:
            skills_block = "• General Engineering"

        # ----------------------------------------------------------
        # Status
        # ----------------------------------------------------------

        status = (item.application_status or "UNKNOWN").upper()

        if status == "OPEN":
            status_text = "🟢 Applications OPEN"
        else:
            status_text = (
                f"⚠️ Status: {item.application_status}"
            )

        # ----------------------------------------------------------
        # URL
        # ----------------------------------------------------------

        link_text = (
            f"\n\n🔗 Apply: {item.url}"
            if item.url
            else ""
        )

        return (
            f"🚨 <b>NEW VTU INTERNSHIP</b>\n\n"
            f"<b>{item.title}</b>\n"
            f"Company: <i>{item.company}</i>\n\n"
            f"🎯 <b>Technical Match: "
            f"{item.technical_score:.0f}%</b>\n\n"
            f"{money_line}\n"
            f"{mode_line}\n"
            f"{duration_line}\n\n"
            f"<b>Skills:</b>\n"
            f"{skills_block}\n\n"
            f"{status_text}\n\n"
            f"<b>Priority: {priority_display}</b>"
            f"{link_text}"
        )

    # ==============================================================
    # NEW INTERNSHIP ALERT
    # ==============================================================

    def send_alert(self, item: Internship) -> bool:
        """Sends a new internship alert."""
        message = self.format_message(item)

        sent = self._send_message(message)

        if sent:
            logger.info(
                f"Telegram alert sent for: {item.title}"
            )

        return sent

    # ==============================================================
    # UPDATE MESSAGE
    # ==============================================================

    def format_update_message(
        self,
        item: Internship,
        changes: Dict[str, tuple],
    ) -> str:
        """
        Formats an internship change notification.

        changes:
            {
                "vacancy": ("10", "5"),
                "application_status": ("OPEN", "CLOSED"),
            }
        """

        lines = []

        field_labels = {
            "vacancy": "👥 Vacancy",
            "application_status": "📋 Application Status",
            "deadline": "📅 Deadline",
            "fee": "💳 Fee",
            "mode": "💻 Mode",
            "stipend": "💰 Stipend",
            "internship_type": "🏷️ Internship Type",
            "location": "📍 Location",
            "duration": "⏳ Duration",
        }

        for field, (old_value, new_value) in changes.items():

            label = field_labels.get(
                field,
                field.replace("_", " ").title(),
            )

            old_display = (
                str(old_value)
                if old_value not in ("", None)
                else "Not specified"
            )

            new_display = (
                str(new_value)
                if new_value not in ("", None)
                else "Not specified"
            )

            lines.append(
                f"{label}: "
                f"<s>{old_display}</s> → "
                f"<b>{new_display}</b>"
            )

        priority_emojis = {
            "VERY_HIGH": "🔥🔥🔥 VERY HIGH",
            "HIGH": "🟢 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW": "⚪ LOW",
            "IGNORE": "❌ IGNORE",
        }

        priority_display = priority_emojis.get(
            item.priority_level,
            item.priority_level,
        )

        status = (
            item.application_status
            or "UNKNOWN"
        )

        if status.upper() == "OPEN":
            status_line = "🟢 Applications OPEN"
        else:
            status_line = f"⚠️ Status: {status}"

        link_text = (
            f"\n\n🔗 View Internship: {item.url}"
            if item.url
            else ""
        )

        return (
            f"🔔 <b>VTU INTERNSHIP UPDATE</b>\n\n"
            f"<b>{item.title}</b>\n"
            f"Company: <i>{item.company}</i>\n\n"
            f"<b>Changes detected:</b>\n"
            f"{chr(10).join(lines)}\n\n"
            f"🎯 Technical Match: "
            f"<b>{item.technical_score:.0f}%</b>\n"
            f"{status_line}\n"
            f"<b>Priority: {priority_display}</b>"
            f"{link_text}"
        )

    # ==============================================================
    # UPDATE ALERT
    # ==============================================================

    def send_update_alert(
        self,
        item: Internship,
        changes: Dict[str, tuple],
    ) -> bool:
        """Sends a change/update notification."""
        message = self.format_update_message(
            item,
            changes,
        )

        sent = self._send_message(message)

        if sent:
            logger.info(
                f"Telegram update sent for: {item.title}"
            )

        return sent

    # ==============================================================
    # TEST MESSAGE
    # ==============================================================

    def send_test_message(self) -> bool:
        """Verifies Telegram bot credentials."""

        message = (
            "🤖 <b>VTU Internship Watcher</b> "
            "is connected and ready to monitor opportunities!"
        )

        return self._send_message(message)