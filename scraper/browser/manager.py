"""
Browser pool manager for Playwright.
Handles browser lifecycle and concurrent contexts.
"""

import asyncio
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Playwright, BrowserContext

from ..models import ScraperConfig
from ..utils import get_logger


class BrowserManager:
    """
    Manages Playwright browser lifecycle and context pool.
    Supports concurrent contexts up to max_concurrent limit.
    """

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = get_logger()

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._active_contexts: List[BrowserContext] = []
        self._context_semaphore = asyncio.Semaphore(config.max_concurrent)

    async def start(self):
        """Initialize Playwright and launch browser."""
        self.logger.info("Starting browser manager...")

        try:
            self._playwright = await async_playwright().start()

            # Launch browser
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )

            self.logger.info(
                f"Browser launched (headless={self.config.headless})"
            )

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}", exc_info=True)
            raise

    async def stop(self):
        """Close browser and cleanup."""
        self.logger.info("Stopping browser manager...")

        # Close all active contexts
        for context in self._active_contexts:
            try:
                await context.close()
            except Exception as e:
                self.logger.warning(f"Error closing context: {e}")

        self._active_contexts.clear()

        # Close browser
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                self.logger.warning(f"Error closing browser: {e}")

        # Stop playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping playwright: {e}")

        self.logger.info("Browser manager stopped")

    async def create_context(self) -> BrowserContext:
        """
        Create a new browser context with semaphore control.
        Limits concurrent contexts to max_concurrent.
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        # Acquire semaphore (blocks if at max concurrent)
        await self._context_semaphore.acquire()

        try:
            # Create context with realistic settings
            context = await self._browser.new_context(
                user_agent=self.config.user_agent or self._get_default_user_agent(),
                viewport={'width': 1920, 'height': 1080},
                locale=self.config.locale,
                timezone_id=self.config.timezone,
                accept_downloads=False,
                ignore_https_errors=False,
            )

            # Set default timeout
            context.set_default_timeout(self.config.page_timeout_ms)

            # Track active context
            self._active_contexts.append(context)

            self.logger.debug(f"Created browser context ({len(self._active_contexts)} active)")

            return context

        except Exception as e:
            # Release semaphore if context creation failed
            self._context_semaphore.release()
            raise

    async def close_context(self, context: BrowserContext):
        """Close a browser context and release semaphore."""
        try:
            await context.close()

            # Remove from active contexts
            if context in self._active_contexts:
                self._active_contexts.remove(context)

            self.logger.debug(f"Closed browser context ({len(self._active_contexts)} active)")

        finally:
            # Always release semaphore
            self._context_semaphore.release()

    def _get_default_user_agent(self) -> str:
        """Get default realistic user agent."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
