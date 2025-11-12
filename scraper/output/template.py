"""
Markdown template builder.
Builds dealer blocks exactly matching output_format from original_prompt.md.
"""

from datetime import datetime
from typing import Optional
import pytz

from ..models import DealerData, Hours
from ..utils import get_logger


class MarkdownTemplateBuilder:
    """
    Builds markdown output blocks matching original_prompt.md template exactly.
    Guards against template drift with validation.
    """

    def __init__(self, timezone: str = "America/Chicago"):
        self.timezone = timezone
        self.logger = get_logger()

    def build_dealer_block(self, dealer: DealerData) -> str:
        """
        Build a single dealer markdown block wrapped in fenced code block.

        Returns output exactly matching this format from original_prompt.md:
        ```markdown
        [DEALERSHIP NAME]
        [GOOGLE MAPS ADDRESS]
        County: [COUNTY NAME]
        Phone: (XXX) XXX-XXXX
        Phone (no dashes): XXXXXXXXXX
        Website: https://www.exampledealer.com/
        Provider: Example Provider

        Sales Hours
        ...
        ```
        """
        lines = []

        # Name
        name = dealer.name or "Unsure"
        lines.append(name)

        # Address (from Google Maps)
        if dealer.address and dealer.address.full_address:
            lines.append(dealer.address.full_address)
        else:
            lines.append("Unsure")

        # County (directly under address)
        county = self._format_county(dealer.county)
        lines.append(f"County: {county}")

        # Phone
        if dealer.phone and dealer.phone.pretty and dealer.phone.digits:
            lines.append(f"Phone: {dealer.phone.pretty}")
            lines.append(f"Phone (no dashes): {dealer.phone.digits}")
        else:
            lines.append("Phone: Unsure")
            lines.append("Phone (no dashes): Unsure")

        # Website
        lines.append(f"Website: {dealer.website}")

        # Provider
        provider = dealer.website_provider.display_name if dealer.website_provider and dealer.website_provider.display_name else "Unsure"
        lines.append(f"Provider: {provider}")

        # Blank line before hours
        lines.append("")

        # Sales Hours
        lines.extend(self._format_hours_section("Sales Hours", dealer.hours.sales if dealer.hours else None))

        # Service Hours
        lines.extend(self._format_hours_section("Service Hours", dealer.hours.service if dealer.hours else None))

        # Parts Hours
        lines.extend(self._format_hours_section("Parts Hours", dealer.hours.parts if dealer.hours else None))

        # Schedule Service URL
        service_url = dealer.urls.service_scheduler if dealer.urls and dealer.urls.service_scheduler else "Unsure"
        lines.append(f"Schedule Service: {service_url}")

        # Credit App URL + Embedded provider
        credit_url = dealer.urls.credit_app if dealer.urls and dealer.urls.credit_app else "Unsure"
        lines.append(f"Credit App: {credit_url}")

        embedded_provider = dealer.credit_app_provider.display_name if dealer.credit_app_provider and dealer.credit_app_provider.display_name else ""
        if embedded_provider:
            lines.append(f"  • Embedded provider (if any): {embedded_provider}")
        else:
            lines.append("  • Embedded provider (if any):")

        # Facebook
        facebook_url = dealer.urls.facebook if dealer.urls and dealer.urls.facebook else ""
        lines.append(f"Facebook: {facebook_url}")
        lines.append("Facebook Page ID:")

        # Blank line before Evidence
        lines.append("")

        # Evidence section
        lines.append("Evidence")
        lines.extend(self._format_evidence(dealer))

        # Wrap in fenced markdown code block
        block_content = "\n".join(lines)
        return f"```markdown\n{block_content}\n```"

    def _format_county(self, county) -> str:
        """Format county name."""
        if not county:
            return "Unsure"
        if county.full_name:
            return county.full_name
        if county.name:
            return county.name
        return "Unsure"

    def _format_hours_section(self, title: str, hours: Optional[Hours]) -> list:
        """
        Format a hours section (Sales/Service/Parts).
        Returns list of lines.
        """
        lines = [title]

        if not hours:
            # All days closed/unsure
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                lines.append(f"{day}: Closed")
        else:
            lines.append(f"Monday: {hours.monday or 'Closed'}")
            lines.append(f"Tuesday: {hours.tuesday or 'Closed'}")
            lines.append(f"Wednesday: {hours.wednesday or 'Closed'}")
            lines.append(f"Thursday: {hours.thursday or 'Closed'}")
            lines.append(f"Friday: {hours.friday or 'Closed'}")
            lines.append(f"Saturday: {hours.saturday or 'Closed'}")
            lines.append(f"Sunday: {hours.sunday or 'Closed'}")

        # Blank line after section
        lines.append("")

        return lines

    def _format_evidence(self, dealer: DealerData) -> list:
        """
        Format evidence section.
        Returns list of evidence bullet points.
        """
        lines = []
        evidence = dealer.evidence

        if not evidence:
            lines.append("- No evidence collected")
            return lines

        # Google Maps address
        if evidence.google_maps_address:
            lines.append(f"- Google Maps (address): {evidence.google_maps_address}")

        # County verification
        if evidence.county_verification:
            lines.append(f"- County verification: {evidence.county_verification}")

        # Dealer homepage phone
        if evidence.dealer_homepage_phone:
            lines.append(f"- Dealer homepage (header phone): {evidence.dealer_homepage_phone}")

        # Hours page
        if evidence.dealer_hours_page:
            lines.append(f"- Dealer hours page (hours): {evidence.dealer_hours_page}")

        # Service verified
        if evidence.service_verified_on:
            lines.append(f"- Service verified on: {evidence.service_verified_on}")

        # Credit app verified
        if evidence.credit_app_verified_on:
            lines.append(f"- Credit app verified on: {evidence.credit_app_verified_on}")

        # Credit app embedded provider evidence
        if evidence.credit_app_embedded_evidence:
            lines.append(f"- Credit app embedded provider evidence: {evidence.credit_app_embedded_evidence}")

        # Facebook
        if evidence.facebook_start and evidence.facebook_final:
            lines.append(f"- Facebook start: {evidence.facebook_start} → final FB: {evidence.facebook_final}")
        elif evidence.facebook_final:
            lines.append(f"- Facebook: {evidence.facebook_final}")

        # Provider verification
        if evidence.provider_verification:
            lines.append(f"- Provider verification: {evidence.provider_verification}")

        # Captured timestamp
        timestamp = evidence.captured_timestamp or self._get_current_timestamp()
        lines.append(f"- Captured: {timestamp}")

        # Additional notes
        for note in evidence.notes:
            lines.append(f"- Note: {note}")

        return lines

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in configured timezone."""
        try:
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
            return now.strftime("%Y-%m-%d %H:%M") + f" ({self.timezone})"
        except Exception:
            # Fallback to UTC
            return datetime.utcnow().strftime("%Y-%m-%d %H:%M (UTC)")

    def build_run_header(self) -> str:
        """Build optional run header for output file."""
        timestamp = self._get_current_timestamp()
        return f"# Dealership Data + URL Discovery — Run started at {timestamp}\n\n"
