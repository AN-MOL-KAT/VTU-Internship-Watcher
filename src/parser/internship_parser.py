import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..database.models import Internship
from ..utils.helpers import (
    clean_text,
    normalize_mode,
    normalize_type,
    parse_fee_amount,
)
from ..utils.logger import get_logger


logger = get_logger("vtu_parser")


class InternshipParser:
    """
    Parser for rendered VTU Internyet internship listings.

    Important:
    VTU Internyet can reuse numeric IDs such as 506 or 104
    for multiple internship programs.

    Therefore the full internship URL slug is used as the
    primary portal_id whenever possible.

    Example:

        /internships/506-data-science-+-ai-integration-program

    becomes:

        506-data-science-+-ai-integration-program

    rather than simply:

        506
    """

    DEFAULT_BASE_URL = "https://vtu.internyet.in"

    # ============================================================
    # MAIN HTML PARSER
    # ============================================================

    def parse_cards_html(
        self,
        html_content: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> List[Internship]:

        if not html_content:
            return []

        soup = BeautifulSoup(
            html_content,
            "html.parser",
        )

        internships: List[Internship] = []

        # --------------------------------------------------------
        # Find all actual internship detail links.
        #
        # The portal currently contains multiple links to the
        # same internship card, so URLs are deduplicated first.
        # --------------------------------------------------------

        detail_links = soup.select(
            'a[href*="/internships/"]'
        )

        if detail_links:

            logger.info(
                f"Found {len(detail_links)} internship link(s) "
                "before URL deduplication."
            )

        processed_urls = set()

        for link in detail_links:

            try:

                href = clean_text(
                    link.get("href", "")
                )

                if not href:
                    continue

                # Ignore the listing page itself.
                if href.rstrip("/") in {
                    "/internships",
                    f"{base_url.rstrip('/')}/internships",
                }:
                    continue

                absolute_url = urljoin(
                    base_url.rstrip("/") + "/",
                    href,
                )

                # Remove URL fragments.
                absolute_url = absolute_url.split("#")[0]

                # Remove trailing slash.
                absolute_url = absolute_url.rstrip("/")

                # ------------------------------------------------
                # Duplicate link.
                # The portal commonly has:
                #
                # 1. Title link
                # 2. Card / Apply link
                #
                # Both point to the same URL.
                # ------------------------------------------------

                if absolute_url in processed_urls:
                    continue

                processed_urls.add(absolute_url)

                # ------------------------------------------------
                # Parse this particular link/card.
                # ------------------------------------------------

                internship = self._parse_link(
                    link=link,
                    base_url=base_url,
                    forced_url=absolute_url,
                )

                if internship:
                    internships.append(internship)

            except Exception as exc:

                logger.debug(
                    f"Failed parsing internship link: {exc}"
                )

        # --------------------------------------------------------
        # Fallback:
        # Some older/test HTML may not contain the normal
        # /internships/ links.
        # --------------------------------------------------------

        if not internships:

            logger.warning(
                "No internship detail links were parsed. "
                "Trying generic card parsing."
            )

            internships = self._parse_generic_cards(
                soup=soup,
                base_url=base_url,
            )

        # --------------------------------------------------------
        # Final deduplication.
        #
        # URL is preferred because numeric portal IDs can be
        # reused by the portal.
        # --------------------------------------------------------

        unique: Dict[str, Internship] = {}

        for internship in internships:

            key = (
                internship.url.rstrip("/")
                if internship.url
                else internship.portal_id
            )

            if not key:
                key = (
                    f"{internship.title.lower()}|"
                    f"{internship.company.lower()}"
                )

            unique[key] = internship

        internships = list(unique.values())

        logger.info(
            f"Parser extracted "
            f"{len(internships)} unique internship(s)."
        )

        return internships

    # ============================================================
    # PARSE LINK
    # ============================================================

    def _parse_link(
        self,
        link,
        base_url: str,
        forced_url: str,
    ) -> Optional[Internship]:

        # --------------------------------------------------------
        # Find the smallest useful card around this link.
        # --------------------------------------------------------

        container = self._find_card_container(link)

        # --------------------------------------------------------
        # Important:
        #
        # If the container is too large, use the link itself for
        # title extraction. This prevents the first card's title
        # from being assigned to every internship.
        # --------------------------------------------------------

        title = self._extract_title_from_link(link)

        if not title:
            title = self._extract_title(container)

        if not title:
            return None

        # --------------------------------------------------------
        # Text used for metadata.
        # --------------------------------------------------------

        if container is not None:

            container_text = clean_text(
                container.get_text(
                    separator=" "
                )
            )

        else:

            container_text = clean_text(
                link.get_text(
                    separator=" "
                )
            )

        # --------------------------------------------------------
        # URL / ID
        # --------------------------------------------------------

        portal_id = self._extract_portal_id(
            forced_url
        )

        if not portal_id:

            data_id = (
                container.get("data-id")
                if container is not None
                else None
            )

            if data_id:
                portal_id = clean_text(
                    str(data_id)
                )

        if not portal_id:

            portal_id = self._stable_id(
                forced_url,
                title,
                container_text,
            )

        # --------------------------------------------------------
        # Company
        # --------------------------------------------------------

        company = self._extract_company(
            container,
            container_text,
        )

        # --------------------------------------------------------
        # Metadata
        # --------------------------------------------------------

        location = self._extract_value(
            container_text,
            [
                "Internship Location",
                "Location",
                "City",
            ],
        )

        mode = self._extract_mode(
            container_text
        )

        fee = self._extract_fee(
            container_text
        )

        stipend = self._extract_stipend(
            container_text
        )

        internship_type = self._extract_type(
            container_text,
            fee=fee,
            stipend=stipend,
        )

        duration = self._extract_duration(
            container_text
        )

        deadline = self._extract_deadline(
            container_text
        )

        vacancy = self._extract_vacancy(
            container_text
        )

        status = self._extract_status(
            container_text
        )

        description = self._extract_description(
            container,
            container_text,
            title,
        )

        # --------------------------------------------------------
        # Create Internship object.
        # --------------------------------------------------------

        return Internship(
            portal_id=portal_id,
            title=title,
            company=company,
            description=description,
            skills=[],
            category="",
            location=location,
            mode=mode,
            internship_type=internship_type,
            fee=fee,
            stipend=stipend,
            duration=duration,
            vacancy=vacancy,
            application_status=status,
            deadline=deadline,
            url=forced_url,
        )

    # ============================================================
    # FIND CARD CONTAINER
    # ============================================================

    def _find_card_container(
        self,
        element,
    ):

        current = element

        best_candidate = None

        for depth in range(8):

            if current is None:
                break

            if not hasattr(current, "get_text"):
                break

            text = clean_text(
                current.get_text(
                    separator=" "
                )
            )

            # Ignore extremely large page-level containers.
            #
            # A single internship card should normally not contain
            # thousands of characters or many internship links.
            internship_links = current.select(
                'a[href*="/internships/"]'
            )

            link_count = len(
                internship_links
            )

            # ----------------------------------------------------
            # Good candidate:
            # - has useful metadata
            # - does not contain many different internships
            # ----------------------------------------------------

            has_metadata = any(
                marker.lower() in text.lower()
                for marker in [
                    "Internship Location",
                    "Work mode",
                    "Duration",
                    "Fees",
                    "Stipend",
                    "Apply by",
                    "Vacancy",
                ]
            )

            if has_metadata and len(text) >= 40:

                if link_count <= 2:

                    return current

                # Keep a smaller candidate if available.
                if best_candidate is None:

                    best_candidate = current

            current = current.parent

        return best_candidate

    # ============================================================
    # TITLE FROM LINK
    # ============================================================

    def _extract_title_from_link(
        self,
        link,
    ) -> str:

        if link is None:
            return ""

        text = clean_text(
            link.get_text(
                separator=" "
            )
        )

        if not text:
            return ""

        # --------------------------------------------------------
        # Some links are title links:
        #
        # "Data Science + AI integration Program"
        #
        # Others are card links containing the entire card text.
        # --------------------------------------------------------

        if (
            "Internship Location" not in text
            and "Work mode" not in text
            and "Duration:" not in text
            and "Fees:" not in text
            and len(text) <= 250
        ):

            if text.lower() not in {
                "apply now",
                "view details",
                "details",
                "internships",
            }:
                return text

        # --------------------------------------------------------
        # Try first heading inside the link.
        # --------------------------------------------------------

        heading = link.select_one(
            "h1, h2, h3, h4, h5"
        )

        if heading:

            value = clean_text(
                heading.get_text(
                    separator=" "
                )
            )

            if value:
                return value

        return ""

    # ============================================================
    # GENERIC CARD FALLBACK
    # ============================================================

    def _parse_generic_cards(
        self,
        soup: BeautifulSoup,
        base_url: str,
    ) -> List[Internship]:

        results = []

        selectors = [
            ".internship-card",
            ".internship-card-container",
            ".listing-card",
            ".job-card",
            ".card",
            "[class*='internship-card']",
            "[class*='listing-card']",
        ]

        seen = set()

        for selector in selectors:

            cards = soup.select(
                selector
            )

            for card in cards:

                try:

                    title = self._extract_title(
                        card
                    )

                    if not title:
                        continue

                    link = card.select_one(
                        'a[href*="/internships/"]'
                    )

                    if link:

                        href = link.get(
                            "href",
                            ""
                        )

                        url = urljoin(
                            base_url.rstrip("/") + "/",
                            href,
                        )

                    else:

                        url = ""

                    key = (
                        url
                        or title.lower()
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    internship = (
                        self._parse_single_card(
                            card,
                            base_url,
                            forced_url=url,
                        )
                    )

                    if internship:
                        results.append(
                            internship
                        )

                except Exception as exc:

                    logger.debug(
                        f"Generic card skipped: {exc}"
                    )

        return results

    # ============================================================
    # SINGLE CARD
    # ============================================================

    def _parse_single_card(
        self,
        element,
        base_url: str,
        forced_url: Optional[str] = None,
    ) -> Optional[Internship]:

        if element is None:
            return None

        text_content = clean_text(
            element.get_text(
                separator=" "
            )
        )

        if not text_content:
            return None

        # --------------------------------------------------------
        # URL
        # --------------------------------------------------------

        url = forced_url or ""

        if not url:

            link_tag = element.select_one(
                'a[href*="/internships/"]'
            )

            if link_tag:

                raw_url = clean_text(
                    link_tag.get(
                        "href",
                        ""
                    )
                )

                if raw_url:

                    url = urljoin(
                        base_url.rstrip("/") + "/",
                        raw_url,
                    )

        url = url.rstrip("/")

        # --------------------------------------------------------
        # Portal ID
        # --------------------------------------------------------

        portal_id = self._extract_portal_id(
            url
        )

        if not portal_id:

            data_id = element.get(
                "data-id"
            )

            if data_id:

                portal_id = clean_text(
                    str(data_id)
                )

        title = self._extract_title(
            element
        )

        if not title:
            return None

        if not portal_id:

            portal_id = self._stable_id(
                url,
                title,
                text_content,
            )

        company = self._extract_company(
            element,
            text_content,
        )

        location = self._extract_value(
            text_content,
            [
                "Internship Location",
                "Location",
                "City",
            ],
        )

        mode = self._extract_mode(
            text_content
        )

        fee = self._extract_fee(
            text_content
        )

        stipend = self._extract_stipend(
            text_content
        )

        internship_type = self._extract_type(
            text_content,
            fee=fee,
            stipend=stipend,
        )

        duration = self._extract_duration(
            text_content
        )

        deadline = self._extract_deadline(
            text_content
        )

        vacancy = self._extract_vacancy(
            text_content
        )

        status = self._extract_status(
            text_content
        )

        description = self._extract_description(
            element,
            text_content,
            title,
        )

        return Internship(
            portal_id=portal_id,
            title=title,
            company=company,
            description=description,
            skills=[],
            category="",
            location=location,
            mode=mode,
            internship_type=internship_type,
            fee=fee,
            stipend=stipend,
            duration=duration,
            vacancy=vacancy,
            application_status=status,
            deadline=deadline,
            url=url,
        )

    # ============================================================
    # TITLE
    # ============================================================

    def _extract_title(
        self,
        element,
    ) -> str:

        if element is None:
            return ""

        selectors = [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            ".title",
            ".card-title",
            "[class*='title']",
        ]

        for selector in selectors:

            try:

                tag = element.select_one(
                    selector
                )

            except Exception:
                tag = None

            if not tag:
                continue

            value = clean_text(
                tag.get_text(
                    separator=" "
                )
            )

            if not value:
                continue

            if value.lower() in {
                "internships",
                "apply now",
                "view details",
                "details",
            }:
                continue

            # Don't accidentally return metadata as title.
            if value.lower().startswith(
                (
                    "internship location",
                    "work mode",
                    "duration",
                    "fees",
                    "stipend",
                )
            ):
                continue

            return value

        # --------------------------------------------------------
        # Try "Title at Company" pattern.
        # --------------------------------------------------------

        text = clean_text(
            element.get_text(
                separator=" "
            )
        )

        match = re.search(
            r"^(.+?)\s+at\s+(.+?)"
            r"(?=\s+Internship Location"
            r"|\s+Work mode"
            r"|\s+Duration"
            r"|\s+Fees"
            r"|$)",
            text,
            re.I,
        )

        if match:

            return clean_text(
                match.group(1)
            )

        return ""

    # ============================================================
    # COMPANY
    # ============================================================

    def _extract_company(
        self,
        element,
        text: str,
    ) -> str:

        if element is not None:

            company_tag = element.select_one(
                "[class*='company'], "
                "[class*='employer'], "
                "[class*='organization']"
            )

            if company_tag:

                company = clean_text(
                    company_tag.get_text(
                        separator=" "
                    )
                )

                if company:
                    return company

        # --------------------------------------------------------
        # Typical portal format:
        #
        # Data Science + AI at QSpiders
        # Internship Location: ...
        # --------------------------------------------------------

        match = re.search(
            r"\bat\s+(.+?)"
            r"(?=\s+Internship Location"
            r"|\s+Work mode"
            r"|\s+Duration"
            r"|\s+Fees"
            r"|\s+Stipend"
            r"|\s+Apply by"
            r"|$)",
            text,
            re.I,
        )

        if match:

            company = clean_text(
                match.group(1)
            )

            if company:
                return company

        return "VTU Affiliated Organization"

    # ============================================================
    # GENERIC VALUE
    # ============================================================

    def _extract_value(
        self,
        text: str,
        labels: List[str],
    ) -> str:

        if not text:
            return ""

        labels_pattern = (
            r"Internship Location"
            r"|Location"
            r"|City"
            r"|Work mode"
            r"|Duration"
            r"|Fees?"
            r"|Stipend"
            r"|Apply by"
            r"|Deadline"
            r"|Last Date"
            r"|Vacanc(?:y|ies)"
            r"|Description"
        )

        for label in labels:

            pattern = (
                rf"{re.escape(label)}"
                rf"\s*:\s*"
                rf"(.+?)"
                rf"(?=\s+(?:{labels_pattern})"
                rf"|$)"
            )

            match = re.search(
                pattern,
                text,
                re.I,
            )

            if match:

                value = clean_text(
                    match.group(1)
                )

                if value:
                    return value

        return ""

    # ============================================================
    # MODE
    # ============================================================

    def _extract_mode(
        self,
        text: str,
    ) -> str:

        if not text:
            return "Onsite"

        # Remote (Online)
        match = re.search(
            r"Work\s*mode\s*:\s*"
            r"(Remote(?:\s*\(Online\))?|Hybrid|Onsite)",
            text,
            re.I,
        )

        if match:

            return normalize_mode(
                match.group(1)
            )

        # Fallback if only the mode is present.
        lowered = text.lower()

        if "remote" in lowered:

            return "Remote"

        if "hybrid" in lowered:

            return "Hybrid"

        if "onsite" in lowered:

            return "Onsite"

        return "Onsite"

    # ============================================================
    # TYPE
    # ============================================================

    def _extract_type(
        self,
        text: str,
        fee: float = 0.0,
        stipend: str = "",
    ) -> str:

        # --------------------------------------------------------
        # STIPEND MUST BE CHECKED FIRST.
        #
        # Example:
        #
        # Type: Free
        # Stipend: ₹15,000
        #
        # We want:
        #
        # internship_type = Stipend
        # --------------------------------------------------------

        if stipend and stipend.strip():

            return "Stipend"

        # --------------------------------------------------------
        # Explicit "Stipend:" label.
        # --------------------------------------------------------

        if re.search(
            r"\bStipend\s*:",
            text,
            re.I,
        ):

            stipend_value = self._extract_stipend(
                text
            )

            if stipend_value:
                return "Stipend"

        # --------------------------------------------------------
        # Explicit Paid / Free.
        # --------------------------------------------------------

        match = re.search(
            r"\b(Paid|Free)\b",
            text,
            re.I,
        )

        if match:

            value = match.group(1)

            return normalize_type(
                value,
                fee=fee,
                stipend=stipend,
            )

        # --------------------------------------------------------
        # Infer paid from a positive fee.
        # --------------------------------------------------------

        if fee > 0:

            return "Paid"

        return "Free"

    # ============================================================
    # FEE
    # ============================================================

    def _extract_fee(
        self,
        text: str,
    ) -> float:

        if not text:
            return 0.0

        # --------------------------------------------------------
        # Normal portal format:
        #
        # Fees: ₹3,999
        # --------------------------------------------------------

        match = re.search(
            r"Fees?\s*:\s*"
            r"(?:₹|Rs\.?|INR)?\s*"
            r"([\d,]+(?:\.\d+)?)",
            text,
            re.I,
        )

        if match:

            try:

                return parse_fee_amount(
                    match.group(1)
                )

            except Exception:

                pass

        # --------------------------------------------------------
        # Alternative:
        #
        # Fee: 3999
        # Application Fee: ₹3999
        # --------------------------------------------------------

        match = re.search(
            r"(?:Fee|Application\s+Fee)"
            r"\s*:\s*"
            r"(?:₹|Rs\.?|INR)?\s*"
            r"([\d,]+(?:\.\d+)?)",
            text,
            re.I,
        )

        if match:

            try:

                return parse_fee_amount(
                    match.group(1)
                )

            except Exception:

                pass

        return 0.0

    # ============================================================
    # STIPEND
    # ============================================================

    def _extract_stipend(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        match = re.search(
            r"Stipend\s*:\s*"
            r"(.+?)"
            r"(?=\s+(?:Duration|Fees?|Apply by|"
            r"Deadline|Vacancy|Description|"
            r"Internship Location|Work mode)"
            r"|$)",
            text,
            re.I,
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:
                return value

        return ""

    # ============================================================
    # DURATION
    # ============================================================

    def _extract_duration(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        match = re.search(
            r"Duration\s*:\s*"
            r"(.+?)"
            r"(?=\s+(?:Fees?|Stipend|"
            r"Apply by|Deadline|Vacancy|"
            r"Description|Internship Location|"
            r"Work mode)"
            r"|$)",
            text,
            re.I,
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:
                return value

        # Example:
        # 3 Months
        # 12 Weeks
        # 6 months
        match = re.search(
            r"\b(\d+\s+"
            r"(?:Weeks?|Months?|Days?))\b",
            text,
            re.I,
        )

        if match:

            return clean_text(
                match.group(1)
            )

        return ""

    # ============================================================
    # DEADLINE
    # ============================================================

    def _extract_deadline(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        # YYYY-MM-DD
        match = re.search(
            r"(?:Apply\s+by|Deadline|Last\s+Date)"
            r"\s*:?\s*"
            r"(\d{4}-\d{2}-\d{2})",
            text,
            re.I,
        )

        if match:

            return match.group(1)

        # DD-MM-YYYY
        match = re.search(
            r"(?:Apply\s+by|Deadline|Last\s+Date)"
            r"\s*:?\s*"
            r"(\d{1,2}-\d{1,2}-\d{4})",
            text,
            re.I,
        )

        if match:

            return match.group(1)

        # DD/MM/YYYY
        match = re.search(
            r"(?:Apply\s+by|Deadline|Last\s+Date)"
            r"\s*:?\s*"
            r"(\d{1,2}/\d{1,2}/\d{4})",
            text,
            re.I,
        )

        if match:

            return match.group(1)

        return ""

    # ============================================================
    # VACANCY
    # ============================================================

    def _extract_vacancy(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        match = re.search(
            r"Vacanc(?:y|ies)"
            r"\s*:?\s*"
            r"(\d+)",
            text,
            re.I,
        )

        if match:

            return match.group(1)

        # Common alternative:
        # 10 vacancies
        match = re.search(
            r"\b(\d+)\s+vacanc(?:y|ies)\b",
            text,
            re.I,
        )

        if match:

            return match.group(1)

        return ""

    # ============================================================
    # STATUS
    # ============================================================

    def _extract_status(
        self,
        text: str,
    ) -> str:

        if not text:
            return "OPEN"

        lowered = text.lower()

        closed_phrases = [
            "application closed",
            "applications closed",
            "registration closed",
            "not accepting applications",
            "closed",
        ]

        for phrase in closed_phrases:

            if phrase in lowered:
                return "CLOSED"

        open_phrases = [
            "apply now",
            "applications open",
            "registration open",
            "open",
        ]

        for phrase in open_phrases:

            if phrase in lowered:
                return "OPEN"

        # Until the portal explicitly says otherwise,
        # a listing appearing in the internship catalogue
        # is treated as open.
        return "OPEN"

    # ============================================================
    # DESCRIPTION
    # ============================================================

    def _extract_description(
        self,
        element,
        full_text: str,
        title: str,
    ) -> str:

        if element is None:

            description = full_text

            if title:

                description = description.replace(
                    title,
                    "",
                    1,
                )

            return clean_text(
                description
            )

        # --------------------------------------------------------
        # Prefer explicit description elements.
        # --------------------------------------------------------

        selectors = [
            "[class*='description']",
            "[class*='desc']",
            "[class*='summary']",
            "[class*='content']",
        ]

        for selector in selectors:

            try:

                tag = element.select_one(
                    selector
                )

            except Exception:

                tag = None

            if not tag:
                continue

            description = clean_text(
                tag.get_text(
                    separator=" "
                )
            )

            if (
                description
                and description.lower()
                != title.lower()
            ):

                return description

        # --------------------------------------------------------
        # Fallback: remove obvious metadata from card text.
        # --------------------------------------------------------

        description = full_text

        if title:

            description = description.replace(
                title,
                "",
                1,
            )

        # Remove company prefix.
        description = re.sub(
            r"\bat\s+.+?"
            r"(?=\s+Internship Location"
            r"|\s+Work mode"
            r"|$)",
            "",
            description,
            flags=re.I,
        )

        # Remove common metadata.
        description = re.sub(
            r"Internship Location\s*:\s*.+?"
            r"(?=\s+Work mode|\s+Duration|\s+Fees|\s+Stipend|$)",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"Work\s*mode\s*:\s*.+?"
            r"(?=\s+Duration|\s+Fees|\s+Stipend|$)",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"Duration\s*:\s*.+?"
            r"(?=\s+Fees|\s+Stipend|\s+Apply by|$)",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"Fees?\s*:\s*.+?"
            r"(?=\s+Stipend|\s+Apply by|\s+Vacancy|$)",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"Stipend\s*:\s*.+?"
            r"(?=\s+Duration|\s+Apply by|\s+Vacancy|$)",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"Apply\s+by\s+\S+",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"Vacanc(?:y|ies)\s*:?\s*\d+",
            "",
            description,
            flags=re.I,
        )

        description = re.sub(
            r"\bApply\s+Now\b",
            "",
            description,
            flags=re.I,
        )

        return clean_text(
            description
        )

    # ============================================================
    # PORTAL ID
    # ============================================================

    def _extract_portal_id(
        self,
        url: str,
    ) -> str:

        if not url:
            return ""

        # --------------------------------------------------------
        # CURRENT VTU FORMAT:
        #
        # /internships/506-data-science-+-ai-integration-program
        #
        # IMPORTANT:
        # Do NOT return only "506".
        # --------------------------------------------------------

        match = re.search(
            r"/internships/([^/?#]+)",
            url,
            re.I,
        )

        if match:

            slug = clean_text(
                match.group(1)
            ).strip("/")

            if slug:
                return slug

        # --------------------------------------------------------
        # Older format:
        #
        # /internship/506
        # --------------------------------------------------------

        match = re.search(
            r"/internship/(\d+)",
            url,
            re.I,
        )

        if match:

            return match.group(1)

        # --------------------------------------------------------
        # Query-string fallback.
        #
        # ?id=506
        # --------------------------------------------------------

        match = re.search(
            r"[?&]id=(\d+)",
            url,
            re.I,
        )

        if match:

            return match.group(1)

        return ""

    # ============================================================
    # STABLE FALLBACK ID
    # ============================================================

    def _stable_id(
        self,
        url: str,
        title: str,
        text: str,
    ) -> str:

        value = (
            f"{url}|"
            f"{title}|"
            f"{text[:300]}"
        )

        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:16]

    # ============================================================
    # DICTIONARY PARSER
    # ============================================================

    def parse_dict(
        self,
        data: Dict[str, Any],
    ) -> Internship:

        # --------------------------------------------------------
        # ID
        # --------------------------------------------------------

        url = clean_text(
            data.get(
                "url",
                "",
            )
        )

        portal_id = clean_text(
            str(
                data.get("portal_id")
                or data.get("id")
                or ""
            )
        )

        # If ID is numeric but URL contains a unique slug,
        # prefer the URL slug.
        url_id = self._extract_portal_id(
            url
        )

        if url_id:

            portal_id = url_id

        if not portal_id:

            portal_id = self._stable_id(
                url,
                str(
                    data.get(
                        "title",
                        "",
                    )
                ),
                str(data),
            )

        # --------------------------------------------------------
        # Basic fields
        # --------------------------------------------------------

        title = clean_text(
            data.get(
                "title",
                "",
            )
        )

        company = clean_text(
            data.get(
                "company",
                "",
            )
        )

        description = clean_text(
            data.get(
                "description",
                "",
            )
        )

        category = clean_text(
            data.get(
                "category",
                "",
            )
        )

        location = clean_text(
            data.get(
                "location",
                "",
            )
        )

        # --------------------------------------------------------
        # Fee
        # --------------------------------------------------------

        fee = parse_fee_amount(
            str(
                data.get(
                    "fee",
                    0,
                )
            )
        )

        # --------------------------------------------------------
        # Stipend
        # --------------------------------------------------------

        stipend = clean_text(
            data.get(
                "stipend",
                "",
            )
        )

        # --------------------------------------------------------
        # Mode
        # --------------------------------------------------------

        mode = normalize_mode(
            data.get(
                "mode",
                "",
            )
        )

        # --------------------------------------------------------
        # Type
        # --------------------------------------------------------

        raw_type = (
            data.get("type")
            or data.get("internship_type")
            or ""
        )

        internship_type = normalize_type(
            raw_type,
            fee=fee,
            stipend=stipend,
        )

        # Explicit stipend should win.
        if stipend:

            internship_type = "Stipend"

        # --------------------------------------------------------
        # Skills
        # --------------------------------------------------------

        skills = data.get(
            "skills",
            [],
        )

        if skills is None:

            skills = []

        if isinstance(
            skills,
            str,
        ):

            skills = [
                clean_text(skill)
                for skill in re.split(
                    r"[,;|]",
                    skills,
                )
                if clean_text(skill)
            ]

        elif isinstance(
            skills,
            (tuple, set),
        ):

            skills = list(skills)

        # Clean and deduplicate.
        cleaned_skills = []

        seen_skills = set()

        for skill in skills:

            skill = clean_text(
                str(skill)
            )

            if not skill:
                continue

            key = skill.lower()

            if key in seen_skills:
                continue

            seen_skills.add(key)

            cleaned_skills.append(
                skill
            )

        # --------------------------------------------------------
        # Remaining fields
        # --------------------------------------------------------

        duration = clean_text(
            data.get(
                "duration",
                "",
            )
        )

        vacancy = clean_text(
            data.get(
                "vacancy",
                "",
            )
        )

        application_status = clean_text(
            data.get(
                "application_status",
                "OPEN",
            )
        ) or "OPEN"

        deadline = clean_text(
            data.get(
                "deadline",
                "",
            )
        )

        # --------------------------------------------------------
        # Return model
        # --------------------------------------------------------

        return Internship(
            portal_id=portal_id,
            title=title,
            company=company,
            description=description,
            skills=cleaned_skills,
            category=category,
            location=location,
            mode=mode,
            internship_type=internship_type,
            fee=fee,
            stipend=stipend,
            duration=duration,
            vacancy=vacancy,
            application_status=application_status,
            deadline=deadline,
            url=url,
        )