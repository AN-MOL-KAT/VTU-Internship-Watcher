from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml

from ..database.models import Internship
from ..utils.logger import get_logger

logger = get_logger("vtu_scorer")


class PriorityScorer:
    """Calculates actionable application priority and enforces filtering rules."""

    DEFAULT_CONFIG_PATH = "config/config.yaml"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or self.DEFAULT_CONFIG_PATH)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {
                "filters": {
                    "max_paid_fee": 1500,
                    "minimum_match_score": 50,
                },
                "preferences": {
                    "stipend_priority_bonus": 30,
                    "free_priority_bonus": 15,
                    "paid_priority_penalty": -20,
                    "remote_bonus": 20,
                    "hybrid_bonus": 10,
                    "onsite_bonus": 0,
                },
            }

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error reading {self.config_path}: {e}")
            return {}

    def should_ignore(self, internship: Internship) -> Tuple[bool, str]:
        """
        Applies hard exclusion filters:
        - Paid internships costing more than max_paid_fee (> ₹1500)
        - Internships below minimum technical threshold
        """
        filters = self.config.get("filters", {})
        max_paid_fee = float(filters.get("max_paid_fee", 1500))
        min_score = float(filters.get("minimum_match_score", 50))

        # Check fee limit
        if (internship.internship_type == "Paid" or internship.fee > 0) and internship.fee > max_paid_fee:
            return True, f"Fee (₹{internship.fee}) exceeds limit of ₹{max_paid_fee}"

        # Check technical score
        if internship.technical_score < min_score:
            return True, f"Technical match ({internship.technical_score}%) below minimum threshold of {min_score}%"

        return False, ""

    def calculate_priority(
        self, internship: Internship
    ) -> Tuple[float, str]:
        """
        Returns (priority_score, priority_level)
        Priority Levels: 'VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW', 'IGNORE'
        """
        ignored, reason = self.should_ignore(internship)
        if ignored:
            return 0.0, "IGNORE"

        prefs = self.config.get("preferences", {})
        stipend_bonus = prefs.get("stipend_priority_bonus", 30)
        free_bonus = prefs.get("free_priority_bonus", 15)
        paid_penalty = prefs.get("paid_priority_penalty", -20)
        remote_bonus = prefs.get("remote_bonus", 20)
        hybrid_bonus = prefs.get("hybrid_bonus", 10)
        onsite_bonus = prefs.get("onsite_bonus", 0)

        # Base is technical match percentage
        score = internship.technical_score

        # Type adjustment
        itype = (internship.internship_type or "Free").capitalize()
        if itype == "Stipend" or (internship.stipend and "stipend" in internship.stipend.lower()):
            score += stipend_bonus
        elif itype == "Free":
            score += free_bonus
        elif itype == "Paid":
            score += paid_penalty

        # Mode adjustment
        mode = (internship.mode or "Onsite").capitalize()
        if mode == "Remote":
            score += remote_bonus
        elif mode == "Hybrid":
            score += hybrid_bonus
        elif mode == "Onsite":
            score += onsite_bonus

        # Normalize score
        final_score = max(0.0, min(round(score, 1), 100.0))

        # Determine level based on priority hierarchy
        # STIPEND + REMOTE -> VERY_HIGH
        # STIPEND + HYBRID -> VERY_HIGH (if high match) or HIGH
        # STIPEND + ONSITE -> HIGH
        # FREE + REMOTE -> HIGH
        # FREE + HYBRID/ONSITE -> MEDIUM
        # PAID <= 1500 -> LOW
        is_stipend = itype == "Stipend" or (internship.stipend and "stipend" in internship.stipend.lower())
        is_free = itype == "Free" and not is_stipend
        is_paid = itype == "Paid" and not is_stipend

        if is_stipend:
            if mode == "Remote":
                level = "VERY_HIGH"
            elif mode == "Hybrid":
                level = "VERY_HIGH" if internship.technical_score >= 75 else "HIGH"
            else:  # Onsite
                level = "HIGH" if internship.technical_score >= 70 else "MEDIUM"
        elif is_free:
            if mode == "Remote":
                level = "HIGH" if internship.technical_score >= 65 else "MEDIUM"
            elif mode == "Hybrid":
                level = "MEDIUM"
            else:  # Onsite
                level = "MEDIUM" if internship.technical_score >= 60 else "LOW"
        elif is_paid:
            # Paid <= 1500
            level = "LOW"
        else:
            level = "MEDIUM"

        return final_score, level
