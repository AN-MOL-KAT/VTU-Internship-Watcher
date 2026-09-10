import os
import time
from typing import List, Optional
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

from ..database.models import Internship
from ..parser.detail_parser import DetailParser
from ..parser.internship_parser import InternshipParser
from ..utils.logger import get_logger

load_dotenv()

logger = get_logger("vtu_scraper")


class VTUScraper:
    """
    Scraper for the VTU Internyet portal.

    The portal is a React application, so requests.get() only returns
    the initial HTML shell. Playwright is therefore used to render the
    page before parsing internship cards.
    """

    DEFAULT_BASE_URL = os.getenv(
        "VTU_PORTAL_URL",
        "https://vtu.internyet.in"
    )

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        use_mock_fallback: bool = False,
        headless: bool = True,
    ):
        self.base_url = (
            base_url or self.DEFAULT_BASE_URL
        ).rstrip("/")

        self.timeout = timeout
        self.max_retries = max_retries
        self.use_mock_fallback = use_mock_fallback
        self.headless = headless

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        self.parser = InternshipParser()
        self.detail_parser = DetailParser()

    # ============================================================
    # PLAYWRIGHT
    # ============================================================

    def _fetch_rendered_html(self, url: str) -> str:
        """
        Open the page using Chromium and return the fully rendered HTML.
        """

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. "
                "Run: pip install playwright"
            ) from exc

        logger.info(f"Opening rendered page: {url}")

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=self.headless
            )

            context = browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 900,
                },
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )

            page = context.new_page()

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout * 1000,
                )

                # Give React time to initialize.
                page.wait_for_timeout(3000)

                # Wait for the application to finish network activity.
                try:
                    page.wait_for_load_state(
                        "networkidle",
                        timeout=20000,
                    )
                except Exception:
                    logger.debug(
                        "Network did not become completely idle; "
                        "continuing with rendered page."
                    )

                # Scroll to trigger lazy-loaded content if present.
                self._scroll_page(page)

                # Allow newly loaded cards to render.
                page.wait_for_timeout(2000)

                html = page.content()

                logger.info(
                    f"Rendered page HTML size: {len(html)} characters"
                )

                return html

            finally:
                browser.close()

    def _scroll_page(self, page) -> None:
        """
        Slowly scroll through the page so lazy-loaded internship
        cards have a chance to appear.
        """

        try:
            previous_height = 0

            for _ in range(10):

                current_height = page.evaluate(
                    "document.body.scrollHeight"
                )

                if current_height == previous_height:
                    break

                previous_height = current_height

                page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )

                page.wait_for_timeout(500)

        except Exception as exc:
            logger.debug(
                f"Page scrolling skipped: {exc}"
            )

    # ============================================================
    # LISTINGS
    # ============================================================

    def fetch_listings(self) -> List[Internship]:
        """
        Fetch all currently visible internships from the live
        VTU Internyet portal.
        """

        url = f"{self.base_url}/internships"

        logger.info(
            f"Connecting to VTU Internyet: {url}"
        )

        for attempt in range(
            1,
            self.max_retries + 1
        ):

            try:

                html = self._fetch_rendered_html(url)

                if not html:
                    logger.warning(
                        "Rendered HTML was empty."
                    )
                    continue

                items = self.parser.parse_cards_html(
                    html,
                    base_url=self.base_url,
                )

                if items:

                    logger.info(
                        f"Successfully scraped "
                        f"{len(items)} internships "
                        f"from live VTU portal."
                    )

                    return items

                logger.warning(
                    f"Attempt {attempt}: "
                    f"page rendered successfully but "
                    f"parser found 0 internships."
                )

            except Exception as exc:

                logger.warning(
                    f"Scraping attempt "
                    f"{attempt}/{self.max_retries} failed: "
                    f"{exc}"
                )

                if attempt < self.max_retries:
                    time.sleep(2)

        # --------------------------------------------------------
        # IMPORTANT:
        # Mock fallback is disabled by default.
        # --------------------------------------------------------

        if self.use_mock_fallback:

            logger.warning(
                "Using mock internship data because "
                "use_mock_fallback=True."
            )

            return self.get_mock_listings()

        logger.error(
            "Unable to extract internships from live portal."
        )

        return []

    # ============================================================
    # DETAILS
    # ============================================================

    def fetch_detail(
        self,
        internship: Internship
    ) -> Internship:
        """
        Fetch and enrich an individual internship.

        Uses Playwright because individual internship pages
        are also React-rendered.
        """

        if not internship.url:
            return internship

        if internship.url.startswith("mock://"):
            return internship

        try:

            html = self._fetch_rendered_html(
                internship.url
            )

            if html:

                internship = (
                    self.detail_parser.enrich_internship(
                        internship,
                        html
                    )
                )

        except Exception as exc:

            logger.warning(
                f"Failed to fetch detail for "
                f"{internship.portal_id}: {exc}"
            )

        return internship

    # ============================================================
    # MOCK DATA
    # ============================================================

    def get_mock_listings(self) -> List[Internship]:
        """
        Mock data retained only for explicit development/testing.

        It is NEVER used unless use_mock_fallback=True.
        """

        mock_data = [
            {
                "id": "506",
                "title": "Gen AI with Python & Deep Learning Intern",
                "company": "QSpiders Global",
                "description": (
                    "Hands-on internship on Generative AI, "
                    "Large Language Models, PyTorch, Python, "
                    "and RAG architectures."
                ),
                "skills": [
                    "Python",
                    "Machine Learning",
                    "Generative AI",
                    "PyTorch",
                    "LLM",
                ],
                "category": "Artificial Intelligence",
                "location": "Bengaluru",
                "mode": "Remote",
                "type": "Stipend",
                "stipend": "₹15,000 / month",
                "fee": 0.0,
                "duration": "3 Months",
                "vacancy": "10",
                "application_status": "OPEN",
                "deadline": "2026-09-30",
                "url": "mock://506",
            },
        ]

        return [
            self.parser.parse_dict(data)
            for data in mock_data
        ]