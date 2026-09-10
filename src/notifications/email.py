import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
from dotenv import load_dotenv

from ..database.models import Internship
from ..utils.logger import get_logger

load_dotenv()
logger = get_logger("vtu_email")


class EmailNotifier:
    """Sends immediate alerts or daily summaries via SMTP Email."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        receiver: Optional[str] = None,
    ):
        self.host = host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(port or os.getenv("SMTP_PORT", 587))
        self.user = user or os.getenv("SMTP_USER", "")
        self.password = password or os.getenv("SMTP_PASS", "")
        self.receiver = receiver or os.getenv("EMAIL_RECEIVER", "")

    def is_configured(self) -> bool:
        """Checks if SMTP credentials are provided."""
        return bool(self.user and self.password and self.receiver)

    def send_summary(self, new_items: List[Internship], total_count: int) -> bool:
        """Sends a consolidated summary email of newly discovered internships."""
        if not self.is_configured():
            logger.debug("Email credentials not configured. Skipping summary email.")
            return False

        very_high = [i for i in new_items if i.priority_level == "VERY_HIGH"]
        high = [i for i in new_items if i.priority_level == "HIGH"]
        medium = [i for i in new_items if i.priority_level == "MEDIUM"]
        ignored = [i for i in new_items if i.priority_level == "IGNORE"]

        subject = f"VTU Internship Summary: {len(new_items)} New Opportunities Found"

        body = f"""
VTU Internship Watcher Summary Report
======================================

Total Portal Listings: {total_count}
New Opportunities Evaluated: {len(new_items)}

Priority Breakdown:
- 🔥 Very High Priority: {len(very_high)}
- 🟢 High Priority: {len(high)}
- 🟡 Medium Priority: {len(medium)}
- ❌ Ignored / Filtered: {len(ignored)}

Top Recommended Internships:
--------------------------------------
"""
        for item in (very_high + high)[:10]:
            stipend_info = f"Stipend: {item.stipend}" if item.stipend else ("Free" if item.fee == 0 else f"Fee: ₹{item.fee}")
            body += f"""
* {item.title} ({item.company})
  Match: {item.technical_score:.0f}% | Priority: {item.priority_level} | Mode: {item.mode} | {stipend_info}
  Link: {item.url}
"""

        body += "\n--\nVTU Internship Watcher Automated System\n"

        return self._send_email(subject, body)

    def _send_email(self, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.user
            msg["To"] = self.receiver
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            logger.info(f"Summary email delivered to {self.receiver}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
