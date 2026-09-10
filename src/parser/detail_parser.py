import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from ..database.models import Internship
from ..utils.helpers import (
    clean_text,
    normalize_mode,
    normalize_type,
    parse_fee_amount,
)
from ..utils.logger import get_logger

logger = get_logger("vtu_detail_parser")


class DetailParser:
    """Parses detailed internship pages from VTU Portal."""

    def enrich_internship(
        self, internship: Internship, detail_html: str
    ) -> Internship:
        """
        Enriches an existing Internship dataclass with deep details extracted
        from the full page HTML.
        """
        if not detail_html:
            return internship

        soup = BeautifulSoup(detail_html, "html.parser")
        text_content = clean_text(soup.get_text(separator=" "))

        # Extract Skills list
        skills = self._extract_skills(soup, text_content)
        if skills:
            # Merge with existing skills if any
            all_skills = list(dict.fromkeys(internship.skills + skills))
            internship.skills = all_skills

        # Extract Application Status
        status = self._extract_status(soup, text_content)
        if status:
            internship.application_status = status

        # Extract Vacancy
        vacancy = self._extract_vacancy(text_content)
        if vacancy:
            internship.vacancy = vacancy

        # Extract Full Description
        description = self._extract_description(soup, text_content)
        if description and len(description) > len(internship.description):
            internship.description = description

        # Extract Categories
        category = self._extract_category(soup, text_content)
        if category:
            internship.category = category

        # Refine Fee and Stipend if detailed page has more info
        detailed_fee = self._extract_fee(text_content)
        if detailed_fee > 0 and internship.fee == 0:
            internship.fee = detailed_fee

        detailed_stipend = self._extract_stipend(soup, text_content)
        if detailed_stipend and not internship.stipend:
            internship.stipend = detailed_stipend

        # Re-evaluate mode and type
        internship.mode = normalize_mode(text_content) if internship.mode == "Onsite" else internship.mode
        internship.internship_type = normalize_type(
            internship.internship_type, fee=internship.fee, stipend=internship.stipend
        )

        return internship

    def _extract_skills(self, soup: BeautifulSoup, text: str) -> List[str]:
        skills: List[str] = []

        # 1. Look for skill tags/badges
        badge_elements = soup.select(".badge, .skill-tag, .tag, .chip, .skill-item, li.skill")
        for badge in badge_elements:
            t = clean_text(badge.get_text())
            if t and len(t) < 40:
                skills.append(t)

        # 2. Look for "Skills Required" or "Key Skills" sections
        skill_section = soup.find(string=re.compile(r"skills?\s*(?:required|needed)?", re.I))
        if skill_section and skill_section.parent:
            parent = skill_section.parent
            # Check siblings or child list items
            sibling = parent.find_next(["ul", "ol", "div", "p"])
            if sibling:
                for li in sibling.find_all("li"):
                    t = clean_text(li.get_text())
                    if t:
                        skills.append(t)

        # 3. Regex match for "Skills: Python, ML, OpenCV"
        skills_match = re.search(r"(?:Skills|Key Skills|Prerequisites)\s*:\s*([^.\n]+)", text, re.I)
        if skills_match:
            parts = re.split(r"[,;|/•]", skills_match.group(1))
            for p in parts:
                cleaned = clean_text(p)
                if cleaned and len(cleaned) < 40:
                    skills.append(cleaned)

        return list(dict.fromkeys(skills))

    def _extract_status(self, soup: BeautifulSoup, text: str) -> str:
        # Check for apply buttons or closed status
        apply_btn = soup.find("a", string=re.compile(r"apply\s*now|register|apply", re.I))
        if apply_btn and not apply_btn.get("disabled"):
            return "OPEN"

        lower = text.lower()
        if any(k in lower for k in ["applications closed", "registration closed", "closed", "expired"]):
            return "CLOSED"
        if any(k in lower for k in ["applications open", "registration open", "open for registration"]):
            return "OPEN"
        if any(k in lower for k in ["upcoming", "opening soon"]):
            return "UPCOMING"

        return "OPEN"

    def _extract_vacancy(self, text: str) -> str:
        vac_match = re.search(r"(?:Vacanc(?:y|ies)|No\.?\s*of\s*Posts?|Openings?)\s*:\s*(\d+)", text, re.I)
        if vac_match:
            return vac_match.group(1)
        return ""

    def _extract_description(self, soup: BeautifulSoup, full_text: str) -> str:
        desc_container = soup.find(class_=re.compile(r"description|details|job-body|content", re.I))
        if desc_container:
            return clean_text(desc_container.get_text(separator="\n"))
        return full_text

    def _extract_category(self, soup: BeautifulSoup, text: str) -> str:
        # Check for explicit category element
        cat_elem = soup.find(class_=re.compile(r"category|domain|sector", re.I))
        if cat_elem:
            return clean_text(cat_elem.get_text())

        # Check in paragraphs
        for p in soup.find_all(["p", "div", "span", "li"]):
            p_text = clean_text(p.get_text())
            cat_match = re.search(r"^(?:Category|Domain|Field|Sector)\s*:\s*(.+)$", p_text, re.I)
            if cat_match:
                return clean_text(cat_match.group(1))

        # Fallback with strict boundary stopping at next label
        cat_match = re.search(
            r"(?:Category|Domain|Field|Sector)\s*:\s*([^|•\n,]+?)(?=\s+(?:Stipend|Salary|Fee|Location|Mode|Duration|Vacancy|Apply|Deadline)|$)",
            text,
            re.I,
        )
        if cat_match:
            return clean_text(cat_match.group(1))
        return ""

    def _extract_fee(self, text: str) -> float:
        fee_match = re.search(r"(?:Fee|Cost|Registration Fee|Charges)\s*:\s*([^|•\n]+)", text, re.I)
        if fee_match:
            return parse_fee_amount(fee_match.group(1))
        return 0.0

    def _extract_stipend(self, soup: BeautifulSoup, text: str) -> str:
        # Check in paragraphs or spans
        for p in soup.find_all(["p", "div", "span", "li"]):
            p_text = clean_text(p.get_text())
            stip_match = re.search(r"^(?:Stipend|Salary|Allowance)\s*:\s*(.+)$", p_text, re.I)
            if stip_match:
                return clean_text(stip_match.group(1))

        # Fallback with boundary
        stip_match = re.search(
            r"(?:Stipend|Salary|Allowance)\s*:\s*([^|•\n,]+?)(?=\s+(?:Category|Domain|Location|Mode|Duration|Vacancy|Apply|Deadline)|$)",
            text,
            re.I,
        )
        if stip_match:
            return clean_text(stip_match.group(1))
        return ""
