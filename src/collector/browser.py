import asyncio
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger("vtu_browser")


class BrowserCollector:
    """Optional Playwright browser automation for JavaScript rendered pages."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_page_html_async(self, url: str, wait_selector: Optional[str] = None) -> str:
        """Asynchronously fetches rendered HTML using Playwright."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=10000)
                    except Exception:
                        pass
                content = await page.content()
                await browser.close()
                return content
        except ImportError:
            logger.warning("Playwright is not installed. To use browser automation, run: pip install playwright && playwright install chromium")
            return ""
        except Exception as e:
            logger.error(f"Playwright fetch error on {url}: {e}")
            return ""

    def fetch_page_html(self, url: str, wait_selector: Optional[str] = None) -> str:
        """Synchronous wrapper for page HTML fetching."""
        return asyncio.run(self.fetch_page_html_async(url, wait_selector))
