"""
Census Bureau API client for county lookup.
Uses the U.S. Census Bureau Geocoder "Find Geographies" service.
"""

import asyncio
from typing import Optional, Tuple
import httpx

from ..models import County, ConfidenceLevel
from ..utils import get_logger, CountyValidator


class CensusBureauClient:
    """
    Client for U.S. Census Bureau Geocoder API.
    Primary source of truth for county information.
    """

    def __init__(self, api_url: str = "https://geocoding.geo.census.gov/geocoder"):
        self.api_url = api_url.rstrip('/')
        self.logger = get_logger()

    async def lookup_county_by_address(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: Optional[str] = None
    ) -> Optional[County]:
        """
        Look up county using street address.

        Args:
            street: Street address
            city: City name
            state: State abbreviation (2 letters)
            zip_code: ZIP code (optional, improves accuracy)

        Returns:
            County object or None if lookup fails
        """
        # Build address string
        address_parts = [street, city, state]
        if zip_code:
            address_parts.append(zip_code)

        address = ', '.join(filter(None, address_parts))

        self.logger.debug(f"Census lookup for address: {address}")

        # Call Census API
        endpoint = f"{self.api_url}/geographies/onelineaddress"

        params = {
            'address': address,
            'benchmark': 'Public_AR_Current',  # Most recent benchmark
            'vintage': 'Current_Current',       # Most recent vintage
            'format': 'json'
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

            # Parse response
            return self._parse_census_response(data, state)

        except httpx.TimeoutException:
            self.logger.warning(f"Census API timeout for address: {address}")
            return None
        except httpx.HTTPError as e:
            self.logger.warning(f"Census API HTTP error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Census API error: {e}", exc_info=True)
            return None

    async def lookup_county_by_coordinates(
        self,
        latitude: float,
        longitude: float,
        state: Optional[str] = None
    ) -> Optional[County]:
        """
        Look up county using latitude/longitude coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude
            state: State abbreviation (optional, for label determination)

        Returns:
            County object or None if lookup fails
        """
        self.logger.debug(f"Census lookup for coordinates: ({latitude}, {longitude})")

        endpoint = f"{self.api_url}/geographies/coordinates"

        params = {
            'x': longitude,
            'y': latitude,
            'benchmark': 'Public_AR_Current',
            'vintage': 'Current_Current',
            'format': 'json'
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

            return self._parse_census_response(data, state)

        except Exception as e:
            self.logger.error(f"Census API error for coordinates: {e}", exc_info=True)
            return None

    def _parse_census_response(self, data: dict, state: Optional[str] = None) -> Optional[County]:
        """
        Parse Census Bureau API response.

        Response structure:
        {
          "result": {
            "addressMatches": [{
              "geographies": {
                "Counties": [{
                  "NAME": "Cook County",
                  "COUNTY": "031",
                  ...
                }]
              }
            }]
          }
        }
        """
        try:
            # Navigate response structure
            result = data.get('result', {})

            # Try addressMatches first (onelineaddress endpoint)
            address_matches = result.get('addressMatches', [])
            if address_matches and len(address_matches) > 0:
                geographies = address_matches[0].get('geographies', {})
            else:
                # Try geographies directly (coordinates endpoint)
                geographies = result.get('geographies', {})

            # Extract county data
            counties = geographies.get('Counties', [])
            if not counties or len(counties) == 0:
                self.logger.debug("No county found in Census response")
                return None

            county_data = counties[0]
            county_name = county_data.get('NAME', '')

            if not county_name:
                return None

            # Clean county name (remove " County" suffix if present)
            clean_name = county_name.replace(' County', '').replace(' Parish', '').replace(' Borough', '')

            # Determine appropriate suffix
            suffix = self._determine_county_suffix(clean_name, state)

            # Build full name
            full_name = f"{clean_name} {suffix}"

            # Build verification URL
            verification_url = self._build_verification_url(county_data)

            self.logger.debug(f"Census found county: {full_name}")

            return County(
                name=clean_name,
                label=suffix,
                full_name=full_name,
                source="Census Bureau Geocoder",
                verification_url=verification_url,
                confidence=ConfidenceLevel.HIGH
            )

        except Exception as e:
            self.logger.error(f"Error parsing Census response: {e}", exc_info=True)
            return None

    def _determine_county_suffix(self, county_name: str, state: Optional[str]) -> str:
        """
        Determine appropriate county suffix based on state.

        Louisiana: Parish
        Alaska: Borough
        Virginia (independent cities): Independent City
        Others: County
        """
        if not state:
            return "County"

        state = state.upper()

        # Louisiana uses Parish
        if state == 'LA':
            return "Parish"

        # Alaska uses Borough
        if state == 'AK':
            return "Borough"

        # Virginia independent cities
        va_independent_cities = {
            'Alexandria', 'Bristol', 'Buena Vista', 'Charlottesville', 'Chesapeake',
            'Colonial Heights', 'Covington', 'Danville', 'Emporia', 'Fairfax',
            'Falls Church', 'Franklin', 'Fredericksburg', 'Galax', 'Hampton',
            'Harrisonburg', 'Hopewell', 'Lexington', 'Lynchburg', 'Manassas',
            'Manassas Park', 'Martinsville', 'Newport News', 'Norfolk', 'Norton',
            'Petersburg', 'Poquoson', 'Portsmouth', 'Radford', 'Richmond',
            'Roanoke', 'Salem', 'Staunton', 'Suffolk', 'Virginia Beach',
            'Waynesboro', 'Williamsburg', 'Winchester'
        }

        if state == 'VA' and county_name in va_independent_cities:
            return "Independent City"

        # Default to County
        return "County"

    def _build_verification_url(self, county_data: dict) -> str:
        """Build a verification URL for the county data."""
        # Could build a URL to Census Bureau or other authoritative source
        # For now, return the geocoder endpoint
        county_name = county_data.get('NAME', '')
        state_fips = county_data.get('STATE', '')
        county_fips = county_data.get('COUNTY', '')

        if state_fips and county_fips:
            # Build URL to Census Bureau
            return f"https://www.census.gov/quickfacts/fact/table/{state_fips}{county_fips}"

        return self.api_url


class CountyLookupService:
    """
    High-level service for county lookup with fallback strategies.
    Implements the source-of-truth hierarchy from original_prompt.md.
    """

    def __init__(self, census_client: CensusBureauClient):
        self.census = census_client
        self.logger = get_logger()

    async def lookup_county(
        self,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Optional[County]:
        """
        Look up county with fallback strategies.

        Priority order (per original_prompt.md):
        1. U.S. Census Bureau Geocoder (by address)
        2. U.S. Census Bureau Geocoder (by coordinates)
        3. Return Unsure if all methods fail

        Args:
            street, city, state, zip_code: Address components
            latitude, longitude: Coordinates (fallback)

        Returns:
            County object or None
        """

        # Try Census by address first
        if street and city and state:
            self.logger.debug("Attempting Census lookup by address")
            county = await self.census.lookup_county_by_address(street, city, state, zip_code)
            if county:
                return county

        # Fallback to coordinates
        if latitude and longitude:
            self.logger.debug("Attempting Census lookup by coordinates")
            county = await self.census.lookup_county_by_coordinates(latitude, longitude, state)
            if county:
                return county

        # All methods failed
        self.logger.warning("County lookup failed for all methods")
        return County(
            name=None,
            label=None,
            full_name="Unsure",
            source="Census lookup failed",
            verification_url=None,
            confidence=ConfidenceLevel.UNSURE
        )
