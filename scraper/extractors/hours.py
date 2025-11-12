"""
Business hours extractor and parser.
Extracts sales, service, and parts hours from dealer pages.
"""

import re
from typing import Optional, Dict
from playwright.async_api import Page
from bs4 import BeautifulSoup

from .base import BaseExtractor, ExtractionResult
from ..browser import DealerContext
from ..models import Hours, DepartmentHours, ConfidenceLevel
from ..services import HoursNormalizer
from ..utils.patterns import DAY_PATTERN, HOURS_RANGE_PATTERN, DAY_RANGE_PATTERN


class HoursExtractor(BaseExtractor):
    """
    Extract business hours for sales, service, and parts departments.
    """

    def __init__(self):
        super().__init__()
        self.normalizer = HoursNormalizer()

    async def extract(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """Extract department hours."""

        # Try to find hours page
        hours_urls = [
            f"{dealer_context.dealer_url.rstrip('/')}/hours",
            f"{dealer_context.dealer_url.rstrip('/')}/contact",
            f"{dealer_context.dealer_url.rstrip('/')}/about",
            dealer_context.dealer_url,  # Try homepage last
        ]

        for url in hours_urls:
            page = await dealer_context.navigate(url)
            if page:
                html = await dealer_context.get_page_content()
                if html and ('hours' in html.lower() or 'open' in html.lower()):
                    # Found page with hours
                    dept_hours = self._parse_department_hours(html)

                    if dept_hours and (dept_hours.sales or dept_hours.service or dept_hours.parts):
                        return self._create_result(
                            data=dept_hours,
                            confidence=ConfidenceLevel.MEDIUM,
                            source=url,
                            evidence=url
                        )

        return self._unsure_result("No hours found")

    def _parse_department_hours(self, html: str) -> Optional[DepartmentHours]:
        """
        Parse hours for all departments from HTML.

        Looks for sections labeled:
        - Sales Hours / Sales Department
        - Service Hours / Service Department
        - Parts Hours / Parts Department
        """
        soup = BeautifulSoup(html, 'lxml')

        dept_hours = DepartmentHours()

        # Try to find department-specific hours
        dept_hours.sales = self._find_department_hours(soup, ['sales', 'showroom'])
        dept_hours.service = self._find_department_hours(soup, ['service', 'repair'])
        dept_hours.parts = self._find_department_hours(soup, ['parts', 'accessories'])

        # If no department-specific hours, try to find general hours
        if not (dept_hours.sales or dept_hours.service or dept_hours.parts):
            general_hours = self._find_general_hours(soup)
            if general_hours:
                # Use general hours for all departments
                dept_hours.sales = general_hours
                dept_hours.service = general_hours
                dept_hours.parts = general_hours

        return dept_hours

    def _find_department_hours(self, soup: BeautifulSoup, keywords: list) -> Optional[Hours]:
        """Find hours for a specific department."""
        # Look for headings containing keywords
        for keyword in keywords:
            # Find heading
            heading = soup.find(
                ['h1', 'h2', 'h3', 'h4', 'div', 'span'],
                string=lambda x: x and keyword in x.lower() and 'hour' in x.lower()
            )

            if heading:
                # Get text after heading
                text = self._get_text_after_element(heading)
                if text:
                    hours_dict = self._parse_hours_text(text)
                    if hours_dict:
                        hours = self.normalizer.normalize_hours_dict(hours_dict)
                        hours.confidence = ConfidenceLevel.MEDIUM
                        return hours

        return None

    def _find_general_hours(self, soup: BeautifulSoup) -> Optional[Hours]:
        """Find general business hours (not department-specific)."""
        # Look for "Hours" heading
        heading = soup.find(
            ['h1', 'h2', 'h3', 'h4', 'div', 'span'],
            string=lambda x: x and 'hour' in x.lower()
        )

        if heading:
            text = self._get_text_after_element(heading)
            if text:
                hours_dict = self._parse_hours_text(text)
                if hours_dict:
                    hours = self.normalizer.normalize_hours_dict(hours_dict)
                    hours.confidence = ConfidenceLevel.LOW
                    return hours

        return None

    def _get_text_after_element(self, element, max_length: int = 1000) -> str:
        """Get text content after an element (for parsing hours after heading)."""
        # Get next sibling or parent's next sibling
        text_parts = []

        # Try getting next siblings
        for sibling in element.next_siblings:
            if hasattr(sibling, 'get_text'):
                text_parts.append(sibling.get_text())
            elif isinstance(sibling, str):
                text_parts.append(sibling)

            # Stop if we've collected enough text
            if sum(len(p) for p in text_parts) > max_length:
                break

        # If nothing found, try parent's content
        if not text_parts and element.parent:
            text_parts.append(element.parent.get_text())

        return ' '.join(text_parts)

    def _parse_hours_text(self, text: str) -> Optional[Dict[str, str]]:
        """
        Parse hours from free text.

        Examples:
        - "Monday: 9:00 AM - 6:00 PM"
        - "Mon-Fri: 9am-6pm"
        - "Monday - Friday: 9:00 AM - 6:00 PM"
        """
        hours_dict = {}

        # Split text into lines
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for day pattern
            day_match = DAY_PATTERN.search(line)
            if not day_match:
                continue

            day = day_match.group(0)

            # Look for time range
            time_match = HOURS_RANGE_PATTERN.search(line)
            if time_match:
                # Extract time string (everything after the colon or dash)
                if ':' in line:
                    time_str = line.split(':', 1)[1].strip()
                else:
                    time_str = line[day_match.end():].strip()

                # Check for day range (Mon-Fri)
                day_range_match = DAY_RANGE_PATTERN.search(line)
                if day_range_match:
                    # Expand day range
                    start_day = day_range_match.group(1)
                    end_day = day_range_match.group(2)
                    days = self._expand_day_range(start_day, end_day)
                    for d in days:
                        hours_dict[d] = time_str
                else:
                    hours_dict[day] = time_str

            elif 'closed' in line.lower():
                hours_dict[day] = 'Closed'

        return hours_dict if hours_dict else None

    def _expand_day_range(self, start_day: str, end_day: str) -> list:
        """
        Expand a day range like "Mon-Fri" to individual days.

        Returns:
            List of day names
        """
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_abbr = {
            'mon': 'Monday',
            'tue': 'Tuesday',
            'wed': 'Wednesday',
            'thu': 'Thursday',
            'fri': 'Friday',
            'sat': 'Saturday',
            'sun': 'Sunday',
        }

        # Normalize day names
        start = day_abbr.get(start_day.lower()[:3], start_day.title())
        end = day_abbr.get(end_day.lower()[:3], end_day.title())

        try:
            start_idx = day_order.index(start)
            end_idx = day_order.index(end)

            if start_idx <= end_idx:
                return day_order[start_idx:end_idx + 1]
            else:
                # Wrap around (e.g., Sat-Mon)
                return day_order[start_idx:] + day_order[:end_idx + 1]
        except ValueError:
            return []
