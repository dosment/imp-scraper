"""
Address extractor with multiple fallback strategies.
Per original_prompt.md: Address must come from Google Maps business listing.
"""

import json
from typing import Optional
from playwright.async_api import Page
from bs4 import BeautifulSoup

from .base import BaseExtractor, ExtractionResult
from ..browser import DealerContext
from ..models import Address, ConfidenceLevel, ExtractionStrategy
from ..utils import AddressValidator
from ..utils.patterns import (
    ADDRESS_STREET_PATTERN,
    STATE_PATTERN,
    ZIP_PATTERN,
    GOOGLE_MAPS_PATTERN
)


class AddressExtractor(BaseExtractor):
    """
    Extract address using multiple strategies.
    Priority per original_prompt.md: Google Maps business listing is source of truth.

    Fallback strategies:
    1. Google Maps search/link
    2. Schema.org JSON-LD
    3. Microdata
    4. Contact page
    5. Footer
    6. Header
    """

    def __init__(self):
        super().__init__()
        self.validator = AddressValidator()

    async def extract(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """Extract address with fallback strategies."""

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

        # Strategy 1: Find Google Maps link on the page
        result = await self._extract_from_google_maps_link(soup, dealer_context)
        if result and result.success:
            return result

        # Strategy 2: Schema.org JSON-LD
        result = await self._extract_from_schema_org(soup, dealer_context.dealer_url)
        if result and result.success:
            return result

        # Strategy 3: Microdata
        result = await self._extract_from_microdata(soup, dealer_context.dealer_url)
        if result and result.success:
            return result

        # Strategy 4: Contact page
        result = await self._extract_from_contact_page(dealer_context)
        if result and result.success:
            return result

        # Strategy 5: Footer
        result = await self._extract_from_footer(soup, dealer_context.dealer_url)
        if result and result.success:
            return result

        # Strategy 6: Header
        result = await self._extract_from_header(soup, dealer_context.dealer_url)
        if result and result.success:
            return result

        return self._unsure_result("No valid address found")

    async def _extract_from_google_maps_link(
        self,
        soup: BeautifulSoup,
        dealer_context: DealerContext
    ) -> Optional[ExtractionResult]:
        """
        Find Google Maps link on page and extract address.
        This is the source of truth per original_prompt.md.
        """
        # Find Google Maps links
        maps_links = soup.find_all('a', href=lambda x: x and 'maps.google.com' in x.lower() or 'google.com/maps' in x.lower())

        for link in maps_links:
            maps_url = link.get('href', '')

            # Navigate to Google Maps link
            # TODO: This would require actual Google Maps scraping
            # For now, we'll note the URL for evidence
            self.logger.debug(f"Found Google Maps link: {maps_url}")

            # Return placeholder for now
            # In full implementation, this would scrape the Maps page
            # and extract the printed address text

        return None

    async def _extract_from_schema_org(
        self,
        soup: BeautifulSoup,
        source_url: str
    ) -> Optional[ExtractionResult]:
        """Extract address from Schema.org JSON-LD."""
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle single object or array
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # Look for LocalBusiness or Organization
                    if item.get('@type') in ['LocalBusiness', 'Organization', 'AutomotiveBusiness', 'AutoDealer']:
                        address_data = item.get('address', {})

                        if isinstance(address_data, dict):
                            street = address_data.get('streetAddress', '')
                            city = address_data.get('addressLocality', '')
                            state = address_data.get('addressRegion', '')
                            zip_code = address_data.get('postalCode', '')

                            if self._validate_address_components(street, city, state, zip_code):
                                address = self._build_address(street, city, state, zip_code)
                                address.source = ExtractionStrategy.SCHEMA_ORG

                                return self._create_result(
                                    data=address,
                                    confidence=ConfidenceLevel.HIGH,
                                    source=ExtractionStrategy.SCHEMA_ORG.value,
                                    evidence=source_url
                                )

            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                self.logger.debug(f"Error parsing schema.org: {e}")
                continue

        return None

    async def _extract_from_microdata(
        self,
        soup: BeautifulSoup,
        source_url: str
    ) -> Optional[ExtractionResult]:
        """Extract address from microdata attributes."""
        # Look for elements with itemprop
        street_elem = soup.find(itemprop='streetAddress')
        city_elem = soup.find(itemprop='addressLocality')
        state_elem = soup.find(itemprop='addressRegion')
        zip_elem = soup.find(itemprop='postalCode')

        if street_elem and city_elem:
            street = street_elem.get_text(strip=True)
            city = city_elem.get_text(strip=True)
            state = state_elem.get_text(strip=True) if state_elem else ''
            zip_code = zip_elem.get_text(strip=True) if zip_elem else ''

            if self._validate_address_components(street, city, state, zip_code):
                address = self._build_address(street, city, state, zip_code)
                address.source = ExtractionStrategy.MICRODATA

                return self._create_result(
                    data=address,
                    confidence=ConfidenceLevel.HIGH,
                    source=ExtractionStrategy.MICRODATA.value,
                    evidence=source_url
                )

        return None

    async def _extract_from_contact_page(
        self,
        dealer_context: DealerContext
    ) -> Optional[ExtractionResult]:
        """Extract address from contact page."""
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
                    address = self._parse_address_from_text(html)
                    if address:
                        return self._create_result(
                            data=address,
                            confidence=ConfidenceLevel.MEDIUM,
                            source=ExtractionStrategy.CONTACT_PAGE.value,
                            evidence=contact_url
                        )

        return None

    async def _extract_from_footer(
        self,
        soup: BeautifulSoup,
        source_url: str
    ) -> Optional[ExtractionResult]:
        """Extract address from footer."""
        footer = soup.find('footer') or soup.find('div', class_=lambda x: x and 'footer' in x.lower())

        if footer:
            address = self._parse_address_from_text(str(footer))
            if address:
                return self._create_result(
                    data=address,
                    confidence=ConfidenceLevel.MEDIUM,
                    source=ExtractionStrategy.FOOTER.value,
                    evidence=source_url
                )

        return None

    async def _extract_from_header(
        self,
        soup: BeautifulSoup,
        source_url: str
    ) -> Optional[ExtractionResult]:
        """Extract address from header."""
        header = soup.find('header') or soup.find('div', class_=lambda x: x and 'header' in x.lower())

        if header:
            address = self._parse_address_from_text(str(header))
            if address:
                return self._create_result(
                    data=address,
                    confidence=ConfidenceLevel.LOW,
                    source=ExtractionStrategy.HEADER.value,
                    evidence=source_url
                )

        return None

    def _parse_address_from_text(self, text: str) -> Optional[Address]:
        """Parse address components from free text."""
        # Find street address
        street_match = ADDRESS_STREET_PATTERN.search(text)
        if not street_match:
            return None

        street = street_match.group(0)

        # Find state
        state_matches = STATE_PATTERN.findall(text)
        state = state_matches[0] if state_matches else ''

        # Find ZIP
        zip_matches = ZIP_PATTERN.findall(text)
        zip_code = zip_matches[0] if zip_matches else ''

        # Try to extract city (text between street and state)
        # This is simplified - full implementation would be more robust
        city = ''
        if state:
            parts = text.split(state)
            if len(parts) > 0:
                before_state = parts[0]
                city_parts = before_state.split(street)
                if len(city_parts) > 1:
                    city = city_parts[-1].strip(' ,')

        if self._validate_address_components(street, city, state, zip_code):
            return self._build_address(street, city, state, zip_code)

        return None

    def _validate_address_components(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str
    ) -> bool:
        """Validate address components."""
        is_valid, _ = self.validator.validate_full_address(street, city, state, zip_code)
        return is_valid

    def _build_address(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str
    ) -> Address:
        """Build Address object from components."""
        full_address = f"{street}, {city}, {state} {zip_code}"

        return Address(
            street=street.strip(),
            city=city.strip(),
            state=state.strip().upper(),
            zip_code=zip_code.strip(),
            full_address=full_address,
            confidence=ConfidenceLevel.MEDIUM
        )
