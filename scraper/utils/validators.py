"""
Data validation utilities.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from .patterns import (
    PHONE_PATTERN,
    PHONE_DIGITS_ONLY,
    ZIP_PATTERN,
    is_valid_state,
)


class AddressValidator:
    """Validates address data."""

    @staticmethod
    def validate_street(street: str) -> bool:
        """Validate street address."""
        if not street:
            return False

        # Must contain at least a number and some text
        has_number = bool(re.search(r'\d+', street))
        has_text = bool(re.search(r'[A-Za-z]+', street))

        return has_number and has_text

    @staticmethod
    def validate_city(city: str) -> bool:
        """Validate city name."""
        if not city:
            return False

        # City should be at least 2 characters and contain only letters, spaces, hyphens
        return len(city) >= 2 and bool(re.match(r'^[A-Za-z\s\-\.]+$', city))

    @staticmethod
    def validate_state(state: str) -> bool:
        """Validate state abbreviation."""
        if not state:
            return False
        return len(state) == 2 and is_valid_state(state)

    @staticmethod
    def validate_zip(zip_code: str) -> bool:
        """Validate ZIP code."""
        if not zip_code:
            return False
        return bool(ZIP_PATTERN.match(zip_code))

    @staticmethod
    def validate_full_address(street: str, city: str, state: str, zip_code: str) -> Tuple[bool, str]:
        """
        Validate complete address.
        Returns (is_valid, error_message).
        """
        errors = []

        if not AddressValidator.validate_street(street):
            errors.append("Invalid street address")

        if not AddressValidator.validate_city(city):
            errors.append("Invalid city")

        if not AddressValidator.validate_state(state):
            errors.append("Invalid state")

        if not AddressValidator.validate_zip(zip_code):
            errors.append("Invalid ZIP code")

        is_valid = len(errors) == 0
        error_msg = "; ".join(errors) if errors else ""

        return is_valid, error_msg


class PhoneValidator:
    """Validates phone numbers."""

    @staticmethod
    def extract_digits(phone: str) -> Optional[str]:
        """Extract 10 digits from phone number."""
        if not phone:
            return None

        match = PHONE_PATTERN.match(phone)
        if match:
            return ''.join(match.groups())

        return None

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number (must be 10 digits)."""
        if not phone:
            return False

        digits = PhoneValidator.extract_digits(phone)
        return digits is not None and len(digits) == 10

    @staticmethod
    def format_pretty(phone: str) -> Optional[str]:
        """Format phone as (XXX) XXX-XXXX."""
        digits = PhoneValidator.extract_digits(phone)
        if not digits or len(digits) != 10:
            return None

        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    @staticmethod
    def format_digits_only(phone: str) -> Optional[str]:
        """Format phone as XXXXXXXXXX (digits only)."""
        digits = PhoneValidator.extract_digits(phone)
        if not digits or len(digits) != 10:
            return None

        return digits


class URLValidator:
    """Validates and cleans URLs."""

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        if not url:
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        try:
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()

            # Remove www. prefix for comparison
            domain1 = domain1.replace('www.', '')
            domain2 = domain2.replace('www.', '')

            return domain1 == domain2
        except Exception:
            return False

    @staticmethod
    def get_domain(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            netloc = urlparse(url).netloc.lower()
            # Remove www. prefix
            return netloc.replace('www.', '')
        except Exception:
            return None

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL:
        - Force HTTPS
        - Remove tracking parameters
        - Keep trailing slash if present
        """
        if not url:
            return url

        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

            parsed = urlparse(url)

            # Force HTTPS
            scheme = 'https'

            # Remove tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'gclid', 'fbclid', 'mc_cid', 'mc_eid', '_ga', '_gl'
            }

            query_params = parse_qs(parsed.query)
            clean_params = {
                k: v for k, v in query_params.items()
                if k not in tracking_params
            }

            # Rebuild query string
            query = urlencode(clean_params, doseq=True) if clean_params else ''

            # Preserve trailing slash
            path = parsed.path
            if not path:
                path = '/'

            return urlunparse((
                scheme,
                parsed.netloc,
                path,
                parsed.params,
                query,
                ''  # Remove fragment
            ))

        except Exception:
            return url


class HoursValidator:
    """Validates business hours."""

    @staticmethod
    def is_valid_time(time_str: str) -> bool:
        """Check if time string is valid."""
        if not time_str:
            return False

        # Accept special values
        if time_str.lower() in ['closed', 'by appointment', 'open 24 hours']:
            return True

        # Check for time pattern (e.g., "9:00 AM")
        pattern = re.compile(r'^\d{1,2}:\d{2}\s*(?:AM|PM)$', re.IGNORECASE)
        return bool(pattern.match(time_str.strip()))

    @staticmethod
    def is_valid_range(hours_str: str) -> bool:
        """Check if hours range is valid (e.g., '9:00 AM – 6:00 PM')."""
        if not hours_str:
            return False

        # Accept special values
        if hours_str.lower() in ['closed', 'by appointment', 'open 24 hours']:
            return True

        # Check for range pattern
        pattern = re.compile(
            r'^\d{1,2}:\d{2}\s*(?:AM|PM)\s*[–-]\s*\d{1,2}:\d{2}\s*(?:AM|PM)$',
            re.IGNORECASE
        )
        return bool(pattern.match(hours_str.strip()))


class CountyValidator:
    """Validates county names."""

    @staticmethod
    def normalize_suffix(county: str, state: Optional[str] = None) -> str:
        """
        Add appropriate suffix to county name.
        Uses "Parish" for LA, "Borough" for AK, "Independent City" for some VA cities.
        """
        if not county:
            return county

        # If already has suffix, return as-is
        if any(suffix in county for suffix in ['County', 'Parish', 'Borough', 'Independent City']):
            return county

        # Louisiana uses Parish
        if state == 'LA':
            return f"{county} Parish"

        # Alaska uses Borough
        if state == 'AK':
            return f"{county} Borough"

        # Virginia independent cities (partial list)
        va_independent_cities = {
            'Alexandria', 'Bristol', 'Charlottesville', 'Chesapeake',
            'Hampton', 'Newport News', 'Norfolk', 'Portsmouth',
            'Richmond', 'Roanoke', 'Suffolk', 'Virginia Beach'
        }
        if state == 'VA' and county in va_independent_cities:
            return f"{county} Independent City"

        # Default to County
        return f"{county} County"

    @staticmethod
    def validate_county(county: str) -> bool:
        """Validate county name."""
        if not county:
            return False

        # Should have at least 3 characters
        if len(county) < 3:
            return False

        # Should contain only letters, spaces, and possibly a suffix
        return bool(re.match(r'^[A-Za-z\s]+(County|Parish|Borough|Independent City)?$', county))
