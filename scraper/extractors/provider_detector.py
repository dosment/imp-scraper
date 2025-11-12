"""
Provider detection for website platforms and embedded credit applications.
Uses fingerprints from data/provider_fingerprints.yaml and data/credit_fingerprints.yaml.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict
from playwright.async_api import Page
from bs4 import BeautifulSoup

from .base import BaseExtractor, ExtractionResult
from ..browser import DealerContext
from ..models import WebsiteProvider, CreditAppProvider, ConfidenceLevel


class ProviderDetector(BaseExtractor):
    """
    Detect website provider using fingerprints.
    Checks: footer branding, legal pages, page source, network requests.
    """

    def __init__(self):
        super().__init__()
        self.fingerprints = self._load_fingerprints()

    def _load_fingerprints(self) -> Dict:
        """Load provider fingerprints from YAML file."""
        fingerprint_file = Path(__file__).parent.parent.parent / 'data' / 'provider_fingerprints.yaml'

        try:
            with open(fingerprint_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Error loading provider fingerprints: {e}")
            return {}

    async def extract(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """Detect website provider."""

        if not page:
            page = await dealer_context.navigate(dealer_context.dealer_url)
            if not page:
                return self._unsure_result("Failed to load homepage")

        html = await dealer_context.get_page_content()
        if not html:
            return self._unsure_result("Failed to get page content")

        soup = BeautifulSoup(html, 'lxml')

        # Try detection methods in order
        provider = None

        # Method 1: Footer branding
        provider = self._detect_from_footer(soup)
        if provider:
            return self._create_result(
                data=provider,
                confidence=ConfidenceLevel.HIGH,
                source="footer",
                evidence=dealer_context.dealer_url
            )

        # Method 2: Page source (meta tags, comments)
        provider = self._detect_from_source(soup)
        if provider:
            return self._create_result(
                data=provider,
                confidence=ConfidenceLevel.MEDIUM,
                source="page_source",
                evidence=dealer_context.dealer_url
            )

        # Method 3: Domain clues (CDN, scripts)
        provider = self._detect_from_domains(soup)
        if provider:
            return self._create_result(
                data=provider,
                confidence=ConfidenceLevel.MEDIUM,
                source="network",
                evidence=dealer_context.dealer_url
            )

        # Not found
        return self._create_result(
            data=WebsiteProvider(
                name="Unsure",
                display_name="Unsure",
                confidence=ConfidenceLevel.UNSURE
            ),
            confidence=ConfidenceLevel.UNSURE,
            source="none"
        )

    def _detect_from_footer(self, soup: BeautifulSoup) -> Optional[WebsiteProvider]:
        """Detect provider from footer text."""
        footer = soup.find('footer') or soup.find('div', class_=lambda x: x and 'footer' in x.lower())

        if footer:
            footer_text = footer.get_text().lower()

            for key, fingerprint in self.fingerprints.items():
                footer_clues = fingerprint.get('footer_text_contains', [])
                for clue in footer_clues:
                    if clue.lower() in footer_text:
                        return WebsiteProvider(
                            name=key,
                            display_name=fingerprint['display_name'],
                            detection_method="footer",
                            confidence=ConfidenceLevel.HIGH
                        )

        return None

    def _detect_from_source(self, soup: BeautifulSoup) -> Optional[WebsiteProvider]:
        """Detect provider from page source (meta tags, comments)."""
        # Check meta tags
        metas = soup.find_all('meta')
        meta_content = ' '.join([
            str(meta.get('content', '')) + str(meta.get('name', ''))
            for meta in metas
        ]).lower()

        for key, fingerprint in self.fingerprints.items():
            clues = fingerprint.get('structured_data_clues', [])
            for clue in clues:
                if clue.lower() in meta_content:
                    return WebsiteProvider(
                        name=key,
                        display_name=fingerprint['display_name'],
                        detection_method="meta_tags",
                        confidence=ConfidenceLevel.MEDIUM
                    )

        return None

    def _detect_from_domains(self, soup: BeautifulSoup) -> Optional[WebsiteProvider]:
        """Detect provider from domain clues (scripts, links)."""
        # Check script sources
        scripts = soup.find_all('script', src=True)
        script_srcs = ' '.join([script.get('src', '') for script in scripts]).lower()

        # Check link hrefs
        links = soup.find_all('link', href=True)
        link_hrefs = ' '.join([link.get('href', '') for link in links]).lower()

        combined = script_srcs + ' ' + link_hrefs

        for key, fingerprint in self.fingerprints.items():
            domain_clues = fingerprint.get('domain_clues', [])
            for clue in domain_clues:
                if clue.lower() in combined:
                    return WebsiteProvider(
                        name=key,
                        display_name=fingerprint['display_name'],
                        detection_method="domain",
                        confidence=ConfidenceLevel.MEDIUM
                    )

        return None


class CreditAppProviderDetector(BaseExtractor):
    """
    Detect embedded credit application provider.
    Checks: iframe src, script src, network requests, page source.
    """

    def __init__(self):
        super().__init__()
        self.fingerprints = self._load_fingerprints()

    def _load_fingerprints(self) -> Dict:
        """Load credit provider fingerprints from YAML file."""
        fingerprint_file = Path(__file__).parent.parent.parent / 'data' / 'credit_fingerprints.yaml'

        try:
            with open(fingerprint_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Error loading credit fingerprints: {e}")
            return {}

    async def extract(
        self,
        dealer_context: DealerContext,
        credit_app_url: Optional[str] = None
    ) -> ExtractionResult:
        """Detect credit app provider from credit application page."""

        if not credit_app_url:
            return self._unsure_result("No credit app URL provided")

        # Navigate to credit app page
        page = await dealer_context.navigate(credit_app_url)
        if not page:
            return self._unsure_result("Failed to load credit app page")

        html = await dealer_context.get_page_content()
        if not html:
            return self._unsure_result("Failed to get page content")

        soup = BeautifulSoup(html, 'lxml')

        # Method 1: Check iframes
        provider = self._detect_from_iframe(soup)
        if provider:
            return self._create_result(
                data=provider,
                confidence=ConfidenceLevel.HIGH,
                source="iframe",
                evidence=credit_app_url
            )

        # Method 2: Check scripts
        provider = self._detect_from_scripts(soup)
        if provider:
            return self._create_result(
                data=provider,
                confidence=ConfidenceLevel.MEDIUM,
                source="script",
                evidence=credit_app_url
            )

        # Method 3: Check page source
        provider = self._detect_from_source(html)
        if provider:
            return self._create_result(
                data=provider,
                confidence=ConfidenceLevel.LOW,
                source="page_source",
                evidence=credit_app_url
            )

        return self._create_result(
            data=CreditAppProvider(
                name="Unsure",
                display_name="Unsure",
                confidence=ConfidenceLevel.UNSURE
            ),
            confidence=ConfidenceLevel.UNSURE,
            source="none",
            evidence=f"No provider detected on {credit_app_url}"
        )

    def _detect_from_iframe(self, soup: BeautifulSoup) -> Optional[CreditAppProvider]:
        """Detect provider from iframe src."""
        iframes = soup.find_all('iframe', src=True)

        for iframe in iframes:
            src = iframe.get('src', '').lower()

            for key, fingerprint in self.fingerprints.items():
                domains = fingerprint.get('domains', [])
                for domain in domains:
                    if domain.lower() in src:
                        return CreditAppProvider(
                            name=key,
                            display_name=fingerprint['display_name'],
                            detection_method="iframe",
                            evidence=iframe.get('src', ''),
                            confidence=ConfidenceLevel.HIGH
                        )

        return None

    def _detect_from_scripts(self, soup: BeautifulSoup) -> Optional[CreditAppProvider]:
        """Detect provider from script src."""
        scripts = soup.find_all('script', src=True)

        for script in scripts:
            src = script.get('src', '').lower()

            for key, fingerprint in self.fingerprints.items():
                domains = fingerprint.get('domains', [])
                for domain in domains:
                    if domain.lower() in src:
                        return CreditAppProvider(
                            name=key,
                            display_name=fingerprint['display_name'],
                            detection_method="script",
                            evidence=script.get('src', ''),
                            confidence=ConfidenceLevel.MEDIUM
                        )

        return None

    def _detect_from_source(self, html: str) -> Optional[CreditAppProvider]:
        """Detect provider from page source text."""
        html_lower = html.lower()

        for key, fingerprint in self.fingerprints.items():
            domains = fingerprint.get('domains', [])
            for domain in domains:
                if domain.lower() in html_lower:
                    return CreditAppProvider(
                        name=key,
                        display_name=fingerprint['display_name'],
                        detection_method="page_source",
                        evidence=f"Domain '{domain}' found in page source",
                        confidence=ConfidenceLevel.LOW
                    )

        return None
