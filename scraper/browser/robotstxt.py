"""
Robots.txt parser and checker.
Respects website scraping policies per original_prompt.md.
"""

import asyncio
from typing import Optional, Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx

from ..utils import get_logger


class RobotsTxtChecker:
    """
    Check robots.txt compliance before scraping.
    Implements politeness and respects website policies.
    """

    def __init__(self, user_agent: str = "DealershipScraper"):
        self.user_agent = user_agent
        self.logger = get_logger()
        self._cache: Dict[str, RobotFileParser] = {}

    async def is_allowed(self, url: str, respect_robots: bool = True) -> tuple[bool, Optional[int]]:
        """
        Check if scraping is allowed for a URL.

        Args:
            url: URL to check
            respect_robots: Whether to respect robots.txt (can be overridden)

        Returns:
            Tuple of (is_allowed, crawl_delay_seconds)
        """
        if not respect_robots:
            self.logger.debug(f"Robots.txt check bypassed for {url}")
            return True, None

        try:
            # Parse URL to get domain
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            # Get or fetch robots.txt parser
            parser = await self._get_parser(domain)

            if parser is None:
                # No robots.txt found, allow scraping
                self.logger.debug(f"No robots.txt for {domain}, allowing access")
                return True, None

            # Check if URL is allowed
            is_allowed = parser.can_fetch(self.user_agent, url)

            # Get crawl delay
            crawl_delay = parser.crawl_delay(self.user_agent)

            if not is_allowed:
                self.logger.warning(
                    f"robots.txt disallows scraping {url} for user-agent '{self.user_agent}'"
                )

            if crawl_delay:
                self.logger.info(f"robots.txt specifies crawl-delay of {crawl_delay}s for {domain}")

            return is_allowed, crawl_delay

        except Exception as e:
            self.logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, allow access but log the issue
            return True, None

    async def _get_parser(self, domain: str) -> Optional[RobotFileParser]:
        """
        Get cached parser or fetch and parse robots.txt.

        Args:
            domain: Domain to fetch robots.txt from

        Returns:
            RobotFileParser or None if not found
        """
        # Check cache
        if domain in self._cache:
            return self._cache[domain]

        # Fetch robots.txt
        robots_url = f"{domain}/robots.txt"
        self.logger.debug(f"Fetching robots.txt from {robots_url}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url, follow_redirects=True)

                if response.status_code == 404:
                    # No robots.txt, cache None
                    self._cache[domain] = None
                    return None

                if response.status_code != 200:
                    self.logger.warning(f"HTTP {response.status_code} fetching {robots_url}")
                    self._cache[domain] = None
                    return None

                # Parse robots.txt
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())

                # Cache parser
                self._cache[domain] = parser

                return parser

        except httpx.TimeoutException:
            self.logger.warning(f"Timeout fetching robots.txt from {robots_url}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching robots.txt from {robots_url}: {e}")
            return None

    def clear_cache(self):
        """Clear the robots.txt cache."""
        self._cache.clear()
