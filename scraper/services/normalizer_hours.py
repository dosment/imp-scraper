"""
Business hours normalization service.
Implements the normalization rules from original_prompt.md.
"""

from typing import Dict, Optional
from ..models import Hours, ConfidenceLevel
from ..utils.patterns import normalize_day_name


class HoursNormalizer:
    """
    Normalize business hours to standard format.
    Per original_prompt.md:
    - Use en dash (–) for time ranges
    - Monday→Sunday order
    - "Closed" for missing/by appointment
    - "Open 24 hours" for 24-hour operation
    """

    # Day order as specified
    DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    @staticmethod
    def normalize_time_range(time_str: str) -> str:
        """
        Normalize a time range string.
        Examples:
          "9:00 AM - 6:00 PM" → "9:00 AM – 6:00 PM"  (use en dash)
          "closed" → "Closed"
          "by appointment" → "Closed"
          "24 hours" → "Open 24 hours"
        """
        if not time_str:
            return "Closed"

        normalized = time_str.strip()

        # Handle special cases (case-insensitive)
        lower = normalized.lower()

        if 'closed' in lower or 'by appointment' in lower:
            return "Closed"

        if '24' in lower and 'hour' in lower:
            return "Open 24 hours"

        # Replace hyphens and em dashes with en dash
        normalized = normalized.replace(' - ', ' – ')
        normalized = normalized.replace(' — ', ' – ')
        normalized = normalized.replace('-', '–')

        # Ensure consistent spacing around en dash
        normalized = normalized.replace('–', ' – ')
        while '  ' in normalized:
            normalized = normalized.replace('  ', ' ')

        return normalized.strip()

    @staticmethod
    def normalize_hours_dict(hours_dict: Dict[str, str]) -> Hours:
        """
        Normalize a dictionary of hours to Hours model.

        Args:
            hours_dict: Dictionary with day names as keys and hour ranges as values

        Returns:
            Hours object with normalized values in Monday-Sunday order
        """
        normalized = {}

        for day in HoursNormalizer.DAY_ORDER:
            # Look for the day in the input dict (case-insensitive)
            day_lower = day.lower()
            value = None

            for key, val in hours_dict.items():
                if key.lower() == day_lower or key.lower().startswith(day_lower[:3]):
                    value = val
                    break

            # Normalize the value
            if value:
                normalized[day_lower] = HoursNormalizer.normalize_time_range(value)
            else:
                normalized[day_lower] = "Closed"

        return Hours(
            monday=normalized.get('monday', 'Closed'),
            tuesday=normalized.get('tuesday', 'Closed'),
            wednesday=normalized.get('wednesday', 'Closed'),
            thursday=normalized.get('thursday', 'Closed'),
            friday=normalized.get('friday', 'Closed'),
            saturday=normalized.get('saturday', 'Closed'),
            sunday=normalized.get('sunday', 'Closed'),
            confidence=ConfidenceLevel.HIGH
        )

    @staticmethod
    def normalize_split_hours(hours_str: str) -> str:
        """
        Normalize split hours (multiple ranges in one day).
        Example: "9-1, 2-6" → "9:00 AM – 1:00 PM; 2:00 PM – 6:00 PM"
        """
        # Split on commas or semicolons
        parts = [p.strip() for p in hours_str.replace(';', ',').split(',')]

        # Normalize each part
        normalized_parts = [HoursNormalizer.normalize_time_range(p) for p in parts if p]

        # Join with semicolon + space
        return '; '.join(normalized_parts)

    @staticmethod
    def create_empty_hours() -> Hours:
        """Create Hours object with all days marked as Closed."""
        return Hours(
            monday="Closed",
            tuesday="Closed",
            wednesday="Closed",
            thursday="Closed",
            friday="Closed",
            saturday="Closed",
            sunday="Closed",
            confidence=ConfidenceLevel.UNSURE
        )

    @staticmethod
    def merge_hours(base: Hours, override: Hours) -> Hours:
        """
        Merge two Hours objects, with override taking precedence.
        Useful for combining default hours with specific department hours.
        """
        return Hours(
            monday=override.monday if override.monday and override.monday != "Closed" else base.monday,
            tuesday=override.tuesday if override.tuesday and override.tuesday != "Closed" else base.tuesday,
            wednesday=override.wednesday if override.wednesday and override.wednesday != "Closed" else base.wednesday,
            thursday=override.thursday if override.thursday and override.thursday != "Closed" else base.thursday,
            friday=override.friday if override.friday and override.friday != "Closed" else base.friday,
            saturday=override.saturday if override.saturday and override.saturday != "Closed" else base.saturday,
            sunday=override.sunday if override.sunday and override.sunday != "Closed" else base.sunday,
            source_url=override.source_url or base.source_url,
            confidence=max(override.confidence, base.confidence) if hasattr(ConfidenceLevel, 'HIGH') else ConfidenceLevel.HIGH
        )
