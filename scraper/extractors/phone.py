"""
Phone number extractor.
Extracts sales phone number from dealer website.
Priority: header > footer > contact page
"""

from typing import Optional
from playwright.async_api import Page
from bs4 import BeautifulSoup

from .base import BaseExtractor, ExtractionResult
from ..browser import DealerContext
from ..models import Phone, ConfidenceLevel, ExtractionStrategy
from ..services import PhoneNormalizer
from ..utils.patterns import PHONE_PATTERN


class PhoneExtractor(BaseExtractor):
    """
    Extract sales phone number from dealer website.
    Per original_prompt.md: header > footer > contact page.
    """

    def __init__(self):
        super().__init__()
        self.normalizer = PhoneNormalizer()

    async def extract(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """Extract phone number with priority-based strategy."""

        # Use current page or navigate to homepage
        if not page:
            page = await dealer_context.navigate(dealer_context.dealer_url)
            if not page:
                return self._unsure_result("Failed to load homepage")

        # Get page HTML
        html = await dealer_context.get_page_content()
        if not html:
            return self._unsure_result("Failed to get page content")

        soup = BeautifulSoup(html, 'lxml')

        # Strategy 1: Header
        phone = await self._extract_from_header(soup, dealer_context.dealer_url)
        if phone:
            return self._create_result(
                data=phone,
                confidence=ConfidenceLevel.HIGH,
                source=ExtractionStrategy.HEADER.value,
                evidence=dealer_context.dealer_url
            )

        # Strategy 2: Footer
        phone = await self._extract_from_footer(soup, dealer_context.dealer_url)
        if phone:
            return self._create_result(
                data=phone,
                confidence=ConfidenceLevel.HIGH,
                source=ExtractionStrategy.FOOTER.value,
                evidence=dealer_context.dealer_url
            )

        # Strategy 3: Contact page
        phone = await self._extract_from_contact_page(dealer_context)
        if phone:
            return phone  # Already wrapped in ExtractionResult

        return self._unsure_result("No phone number found")

    async def _extract_from_header(self, soup: BeautifulSoup, source_url: str) -> Optional[Phone]:
        """Extract phone from header element."""
        header = soup.find('header')
        if not header:
            # Try common header patterns
            header = (
                soup.find('div', class_=lambda x: x and 'header' in x.lower()) or
                soup.find('nav') or
                soup.find('div', id=lambda x: x and 'header' in x.lower())
            )

        if header:
            phone_numbers = self._find_phone_numbers(str(header))
            if phone_numbers:
                return self.normalizer.normalize(phone_numbers[0], ExtractionStrategy.HEADER)

        return None

    async def _extract_from_footer(self, soup: BeautifulSoup, source_url: str) -> Optional[Phone]:
        """Extract phone from footer element."""
        footer = soup.find('footer')
        if not footer:
            # Try common footer patterns
            footer = (
                soup.find('div', class_=lambda x: x and 'footer' in x.lower()) or
                soup.find('div', id=lambda x: x and 'footer' in x.lower())
            )

        if footer:
            phone_numbers = self._find_phone_numbers(str(footer))
            if phone_numbers:
                return self.normalizer.normalize(phone_numbers[0], ExtractionStrategy.FOOTER)

        return None

    async def _extract_from_contact_page(self, dealer_context: DealerContext) -> Optional[ExtractionResult]:
        """Extract phone from contact page."""
        # Try common contact page URLs
        contact_urls = [
            f"{dealer_context.dealer_url.rstrip('/')}/contact",
            f"{dealer_context.dealer_url.rstrip('/')}/contact-us",
            f"{dealer_context.dealer_url.rstrip('/')}/about/contact",
        ]

        for contact_url in contact_urls:
            page = await dealer_context.navigate(contact_url)
            if page:
                html = await dealer_context.get_page_content()
                if html:
                    phone_numbers = self._find_phone_numbers(html)
                    if phone_numbers:
                        phone = self.normalizer.normalize(phone_numbers[0], ExtractionStrategy.CONTACT_PAGE)
                        return self._create_result(
                            data=phone,
                            confidence=ConfidenceLevel.MEDIUM,
                            source=ExtractionStrategy.CONTACT_PAGE.value,
                            evidence=contact_url
                        )

        return None

    def _find_phone_numbers(self, text: str) -> list:
        """Find all phone numbers in text."""
        matches = PHONE_PATTERN.findall(text)
        phone_numbers = []

        for match in matches:
            if isinstance(match, tuple):
                # Extract groups from regex match
                phone = ''.join(match)
            else:
                phone = match

            # Filter out obviously wrong numbers
            if len(phone) >= 10 and phone[:3] not in ['000', '111', '555']:
                phone_numbers.append(phone)

        return phone_numbers
