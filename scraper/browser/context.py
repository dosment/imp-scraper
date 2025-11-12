"""
Isolated browser context wrapper.
Provides utilities for page navigation and data extraction.
"""

import asyncio
from typing import Optional
from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from ..models import ScraperConfig
from ..utils import get_logger


class DealerContext:
    """
    Wrapper around Playwright BrowserContext for a single dealership.
    Provides navigation, retry logic, and debug capabilities.
    """

    def __init__(self, context: BrowserContext, dealer_url: str, config: ScraperConfig):
        self.context = context
        self.dealer_url = dealer_url
        self.config = config
        self.logger = get_logger()

        self._current_page: Optional[Page] = None

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> Optional[Page]:
        """
        Navigate to a URL with retry logic.

        Args:
            url: URL to navigate to
            wait_until: Playwright wait_until option

        Returns:
            Page object or None if navigation fails
        """
        for attempt in range(self.config.retry_attempts):
            try:
                # Create new page if needed
                if not self._current_page:
                    self._current_page = await self.context.new_page()

                self.logger.debug(f"Navigating to {url} (attempt {attempt + 1})")

                # Navigate with timeout
                response = await self._current_page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.config.page_timeout_ms
                )

                # Check response status
                if response and response.status >= 400:
                    self.logger.warning(f"HTTP {response.status} for {url}")
                    if response.status == 404:
                        return None  # Don't retry 404s

                # Successful navigation
                self.logger.debug(f"Successfully loaded {url}")

                # Add politeness delay
                if self.config.delay_between_pages_sec > 0:
                    await asyncio.sleep(self.config.delay_between_pages_sec)

                return self._current_page

            except PlaywrightTimeoutError:
                self.logger.warning(f"Timeout loading {url} (attempt {attempt + 1})")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # Save debug info on final failure
                    if self.config.debug_mode and self._current_page:
                        await self._save_debug_info(url, "timeout")
                    return None

            except Exception as e:
                self.logger.error(f"Error navigating to {url}: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    if self.config.debug_mode and self._current_page:
                        await self._save_debug_info(url, "error")
                    return None

        return None

    async def get_page_content(self) -> Optional[str]:
        """Get current page HTML content."""
        if not self._current_page:
            return None

        try:
            return await self._current_page.content()
        except Exception as e:
            self.logger.error(f"Error getting page content: {e}")
            return None

    async def get_page_text(self) -> Optional[str]:
        """Get current page text content."""
        if not self._current_page:
            return None

        try:
            return await self._current_page.inner_text('body')
        except Exception as e:
            self.logger.error(f"Error getting page text: {e}")
            return None

    async def evaluate_script(self, script: str) -> any:
        """Execute JavaScript in page context."""
        if not self._current_page:
            return None

        try:
            return await self._current_page.evaluate(script)
        except Exception as e:
            self.logger.error(f"Error evaluating script: {e}")
            return None

    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for a selector to appear on the page."""
        if not self._current_page:
            return False

        try:
            await self._current_page.wait_for_selector(selector, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for selector {selector}: {e}")
            return False

    async def screenshot(self) -> Optional[bytes]:
        """Take a screenshot of the current page."""
        if not self._current_page:
            return None

        try:
            return await self._current_page.screenshot(full_page=True)
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None

    async def _save_debug_info(self, url: str, reason: str):
        """Save debug information (screenshot + HTML) for failed page."""
        if not self.config.debug_mode or not self._current_page:
            return

        try:
            # Extract page name from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            page_name = parsed.path.strip('/').replace('/', '_') or 'homepage'
            page_name = f"{page_name}_{reason}"

            # Save screenshot
            if self.config.debug_save_screenshots:
                screenshot_data = await self.screenshot()
                if screenshot_data:
                    self.logger.save_debug_screenshot(
                        screenshot_data,
                        self.dealer_url,
                        page_name
                    )

            # Save HTML
            if self.config.debug_save_html:
                html = await self.get_page_content()
                if html:
                    self.logger.save_debug_html(
                        html,
                        self.dealer_url,
                        page_name
                    )

        except Exception as e:
            self.logger.error(f"Error saving debug info: {e}")

    async def close(self):
        """Close current page."""
        if self._current_page:
            try:
                await self._current_page.close()
            except Exception as e:
                self.logger.warning(f"Error closing page: {e}")

            self._current_page = None

    @property
    def current_url(self) -> Optional[str]:
        """Get current page URL."""
        if self._current_page:
            return self._current_page.url
        return None

    @property
    def page(self) -> Optional[Page]:
        """Get current page object."""
        return self._current_page
