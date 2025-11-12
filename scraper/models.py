"""
Data models for the dealership scraper.
All models use Pydantic for validation and serialization.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator


class ConfidenceLevel(str, Enum):
    """Confidence level for extracted data."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSURE = "unsure"


class ExtractionStrategy(str, Enum):
    """Strategy used for data extraction."""
    SCHEMA_ORG = "schema_org"
    MICRODATA = "microdata"
    GOOGLE_MAPS = "google_maps"
    CONTACT_PAGE = "contact_page"
    FOOTER = "footer"
    HEADER = "header"
    ABOUT_PAGE = "about_page"
    HOURS_PAGE = "hours_page"
    SERVICE_PAGE = "service_page"
    IFRAME = "iframe"
    SCRIPT_SRC = "script_src"
    NETWORK_REQUEST = "network_request"
    PAGE_SOURCE = "page_source"


class Address(BaseModel):
    """Structured address data."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    full_address: Optional[str] = None

    # Metadata
    source: Optional[ExtractionStrategy] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNSURE
    google_maps_url: Optional[str] = None


class County(BaseModel):
    """County information."""
    name: Optional[str] = None
    label: Optional[str] = None  # "County", "Parish", "Borough", "Independent City"
    full_name: Optional[str] = None  # e.g., "Cook County"

    # Metadata
    source: Optional[str] = None  # "Census", "GIS", "Google Maps"
    verification_url: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNSURE


class Phone(BaseModel):
    """Phone number with multiple formats."""
    raw: Optional[str] = None
    pretty: Optional[str] = None  # (XXX) XXX-XXXX
    digits: Optional[str] = None  # XXXXXXXXXX

    # Metadata
    source: Optional[ExtractionStrategy] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNSURE


class Hours(BaseModel):
    """Business hours for a department."""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None

    # Metadata
    source_url: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNSURE


class DepartmentHours(BaseModel):
    """Hours for all departments."""
    sales: Optional[Hours] = None
    service: Optional[Hours] = None
    parts: Optional[Hours] = None


class URLDiscovery(BaseModel):
    """Discovered URLs."""
    service_scheduler: Optional[str] = None
    service_scheduler_source: Optional[str] = None

    credit_app: Optional[str] = None
    credit_app_source: Optional[str] = None

    facebook: Optional[str] = None
    facebook_page_id: Optional[str] = None
    facebook_source: Optional[str] = None


class WebsiteProvider(BaseModel):
    """Website provider information."""
    name: Optional[str] = None
    display_name: Optional[str] = None

    # Detection metadata
    detection_method: Optional[str] = None  # "footer", "legal", "network", etc.
    verification_url: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNSURE


class CreditAppProvider(BaseModel):
    """Embedded credit application provider."""
    name: Optional[str] = None
    display_name: Optional[str] = None

    # Detection metadata
    detection_method: Optional[str] = None  # "iframe", "script", "network", etc.
    evidence: Optional[str] = None  # iframe src, script src, or other evidence
    confidence: ConfidenceLevel = ConfidenceLevel.UNSURE


class Evidence(BaseModel):
    """Evidence and source URLs for all extracted data."""
    google_maps_address: Optional[str] = None
    county_verification: Optional[str] = None
    dealer_homepage_phone: Optional[str] = None
    dealer_hours_page: Optional[str] = None
    service_verified_on: Optional[str] = None
    credit_app_verified_on: Optional[str] = None
    credit_app_embedded_evidence: Optional[str] = None
    facebook_start: Optional[str] = None
    facebook_final: Optional[str] = None
    provider_verification: Optional[str] = None
    captured_timestamp: Optional[str] = None

    # Additional notes
    notes: List[str] = Field(default_factory=list)


class LocationInfo(BaseModel):
    """Information about a specific location (for multi-location dealerships)."""
    location_id: Optional[str] = None
    location_url: Optional[str] = None
    location_name: Optional[str] = None
    is_primary: bool = False


class DealerData(BaseModel):
    """Complete data for a single dealership location."""

    # Basic info
    name: Optional[str] = None
    website: str

    # Location data
    address: Optional[Address] = None
    county: Optional[County] = None

    # Contact
    phone: Optional[Phone] = None

    # Hours
    hours: Optional[DepartmentHours] = None

    # URLs
    urls: Optional[URLDiscovery] = None

    # Providers
    website_provider: Optional[WebsiteProvider] = None
    credit_app_provider: Optional[CreditAppProvider] = None

    # Evidence
    evidence: Optional[Evidence] = None

    # Multi-location metadata
    location_info: Optional[LocationInfo] = None

    # Processing metadata
    processed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    errors: List[str] = Field(default_factory=list)


class ScraperConfig(BaseModel):
    """Configuration for the scraper."""

    # Input
    urls: List[str] = Field(default_factory=list)

    # Scraping behavior
    max_concurrent: int = 5
    page_timeout_ms: int = 30000
    delay_between_pages_sec: int = 3
    retry_attempts: int = 3
    respect_robots_txt: bool = True
    headless: bool = True
    user_agent: Optional[str] = None

    # Output
    output_file: str = "./output/dealership-data.md"
    timezone: str = "America/Chicago"
    locale: str = "en-US"

    # Normalization
    normalize_phone: bool = True
    normalize_hours: bool = True
    normalize_urls: bool = True

    # Evidence
    evidence_links_required: bool = True
    capture_confidence_scores: bool = True

    # External services
    census_enabled: bool = True
    census_api_url: str = "https://geocoding.geo.census.gov/geocoder"

    # Multi-location
    multi_location_enabled: bool = True
    max_locations_per_site: int = 10

    # Regional
    use_regional_county_labels: bool = False

    # Debug
    debug_mode: bool = False
    debug_save_screenshots: bool = True
    debug_save_html: bool = True
    debug_log_file: str = "./debug/debug.log"
    debug_log_network: bool = True


class CheckpointEntry(BaseModel):
    """Single checkpoint entry for a dealership."""
    url: str
    status: str  # "success", "failed", "pending"
    error: Optional[str] = None
    locations_found: Optional[int] = None
    completed_at: Optional[datetime] = None
    attempted_at: Optional[datetime] = None


class Checkpoint(BaseModel):
    """Checkpoint data for crash recovery."""
    session_id: str
    started: datetime
    completed: List[CheckpointEntry] = Field(default_factory=list)
    failed: List[CheckpointEntry] = Field(default_factory=list)
    pending: List[str] = Field(default_factory=list)
