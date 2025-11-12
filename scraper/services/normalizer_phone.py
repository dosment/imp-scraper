"""
Phone number normalization service.
Implements the normalization rules from original_prompt.md.
"""

from typing import Optional, Tuple
from ..models import Phone, ConfidenceLevel, ExtractionStrategy
from ..utils import PhoneValidator


class PhoneNormalizer:
    """
    Normalize phone numbers to standard formats.
    Per original_prompt.md: (XXX) XXX-XXXX and XXXXXXXXXX
    """

    @staticmethod
    def normalize(
        raw_phone: str,
        source: Optional[ExtractionStrategy] = None
    ) -> Optional[Phone]:
        """
        Normalize a phone number to standardized formats.

        Args:
            raw_phone: Raw phone number string
            source: Source of the phone number

        Returns:
            Phone object with pretty and digits-only formats, or None if invalid
        """
        if not raw_phone:
            return None

        # Extract and validate
        if not PhoneValidator.validate_phone(raw_phone):
            return Phone(
                raw=raw_phone,
                pretty=None,
                digits=None,
                source=source,
                confidence=ConfidenceLevel.UNSURE
            )

        # Format both versions
        pretty = PhoneValidator.format_pretty(raw_phone)
        digits = PhoneValidator.format_digits_only(raw_phone)

        if not pretty or not digits:
            return Phone(
                raw=raw_phone,
                pretty=None,
                digits=None,
                source=source,
                confidence=ConfidenceLevel.LOW
            )

        return Phone(
            raw=raw_phone,
            pretty=pretty,
            digits=digits,
            source=source,
            confidence=ConfidenceLevel.HIGH
        )

    @staticmethod
    def normalize_multiple(phones: list, source: Optional[ExtractionStrategy] = None) -> Optional[Phone]:
        """
        Normalize the first valid phone from a list.
        Returns the first successfully normalized phone, or None.
        """
        for phone_str in phones:
            result = PhoneNormalizer.normalize(phone_str, source)
            if result and result.confidence != ConfidenceLevel.UNSURE:
                return result

        # If all failed, return the first attempt with UNSURE confidence
        if phones:
            return Phone(
                raw=phones[0],
                pretty=None,
                digits=None,
                source=source,
                confidence=ConfidenceLevel.UNSURE
            )

        return None
