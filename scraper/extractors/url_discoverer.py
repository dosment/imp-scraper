"""
URL discovery for service scheduler, credit application, and Facebook.
"""

from typing import Optional
from playwright.async_api import Page
from bs4 import BeautifulSoup

from .base import BaseExtractor, ExtractionResult
from ..browser import DealerContext
from ..models import URLDiscovery, ConfidenceLevel
from ..services import URLNormalizer
from ..utils.patterns import (
    SERVICE_URL_PATTERNS,
    CREDIT_URL_PATTERNS,
    FACEBOOK_URL_PATTERN
)


class URLDiscoverer(BaseExtractor):
    """
    Discover key URLs on dealership website:
    - Service scheduler
    - Credit application
    - Facebook page
    """

    def __init__(self):
        super().__init__()
        self.normalizer = URLNormalizer()

    async def extract(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """Extract all URLs."""

        if not page:
            page = await dealer_context.navigate(dealer_context.dealer_url)
            if not page:
                return self._unsure_result("Failed to load homepage")

        html = await dealer_context.get_page_content()
        if not html:
            return self._unsure_result("Failed to get page content")

        soup = BeautifulSoup(html, 'lxml')

        urls = URLDiscovery()

        # Find service scheduler URL
        service_result = await self._find_service_url(soup, dealer_context)
        if service_result:
            urls.service_scheduler = service_result['url']
            urls.service_scheduler_source = service_result['source']

        # Find credit application URL
        credit_result = await self._find_credit_url(soup, dealer_context)
        if credit_result:
            urls.credit_app = credit_result['url']
            urls.credit_app_source = credit_result['source']

        # Find Facebook URL
        facebook_result = await self._find_facebook_url(soup, dealer_context)
        if facebook_result:
            urls.facebook = facebook_result['url']
            urls.facebook_source = facebook_result['source']

        return self._create_result(
            data=urls,
            confidence=ConfidenceLevel.MEDIUM,
            source=dealer_context.dealer_url
        )

    async def _find_service_url(
        self,
        soup: BeautifulSoup,
        dealer_context: DealerContext
    ) -> Optional[dict]:
        """Find service scheduler URL."""

        # Look for links matching service patterns
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()

            # Check if matches service patterns
            for pattern in SERVICE_URL_PATTERNS:
                if pattern.search(href) or 'service' in text or 'appointment' in text:
                    # Build full URL
                    full_url = self._build_full_url(href, dealer_context.dealer_url)

                    # Verify it's on dealer domain
                    if self.normalizer.is_dealer_domain(full_url, dealer_context.dealer_url):
                        normalized = self.normalizer.normalize(full_url)
                        return {
                            'url': normalized,
                            'source': dealer_context.dealer_url
                        }

        # Try direct navigation to common paths
        common_paths = [
            '/service-appointment',
            '/schedule-service',
            '/service/schedule',
            '/book-service',
        ]

        for path in common_paths:
            test_url = f"{dealer_context.dealer_url.rstrip('/')}{path}"
            page = await dealer_context.navigate(test_url)
            if page and page.url.startswith(dealer_context.dealer_url):
                normalized = self.normalizer.normalize(page.url)
                return {
                    'url': normalized,
                    'source': test_url
                }

        return None

    async def _find_credit_url(
        self,
        soup: BeautifulSoup,
        dealer_context: DealerContext
    ) -> Optional[dict]:
        """Find credit application URL."""

        # Look for links matching credit patterns
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()

            # Check if matches credit patterns
            for pattern in CREDIT_URL_PATTERNS:
                if pattern.search(href) or 'apply' in text or 'credit' in text or 'financing' in text:
                    # Build full URL
                    full_url = self._build_full_url(href, dealer_context.dealer_url)

                    # Verify it's on dealer domain
                    if self.normalizer.is_dealer_domain(full_url, dealer_context.dealer_url):
                        normalized = self.normalizer.normalize(full_url)
                        return {
                            'url': normalized,
                            'source': dealer_context.dealer_url
                        }

        # Try direct navigation
        common_paths = [
            '/finance/apply-for-financing',
            '/finance/apply',
            '/apply-for-financing',
            '/credit-application',
        ]

        for path in common_paths:
            test_url = f"{dealer_context.dealer_url.rstrip('/')}{path}"
            page = await dealer_context.navigate(test_url)
            if page and page.url.startswith(dealer_context.dealer_url):
                normalized = self.normalizer.normalize(page.url)
                return {
                    'url': normalized,
                    'source': test_url
                }

        return None

    async def _find_facebook_url(
        self,
        soup: BeautifulSoup,
        dealer_context: DealerContext
    ) -> Optional[dict]:
        """
        Find Facebook page URL.
        Per original_prompt.md: Follow icon redirect chain.
        """

        # Look for Facebook icon/link
        facebook_links = []

        # Find links with facebook in href
        links = soup.find_all('a', href=lambda x: x and 'facebook.com' in x.lower())
        facebook_links.extend(links)

        # Find links with facebook icon classes
        icon_links = soup.find_all('a', class_=lambda x: x and 'facebook' in x.lower())
        facebook_links.extend(icon_links)

        # Find links with fa-facebook icon
        fa_links = soup.find_all('a', class_=lambda x: x and 'fa-facebook' in x.lower())
        facebook_links.extend(fa_links)

        for link in facebook_links:
            href = link.get('href', '')

            if href:
                # Build full URL
                full_url = self._build_full_url(href, dealer_context.dealer_url)

                # Follow redirect if needed
                if 'facebook.com' in full_url.lower():
                    # Clean and normalize Facebook URL
                    normalized = self.normalizer.clean_facebook_url(full_url)
                    return {
                        'url': normalized,
                        'source': f"{dealer_context.dealer_url} → {normalized}"
                    }

        return None

    def _build_full_url(self, href: str, base_url: str) -> str:
        """Build full URL from href and base URL."""
        if href.startswith('http://') or href.startswith('https://'):
            return href
        elif href.startswith('//'):
            return f"https:{href}"
        elif href.startswith('/'):
            base = base_url.rstrip('/')
            return f"{base}{href}"
        else:
            base = base_url.rstrip('/')
            return f"{base}/{href}"
