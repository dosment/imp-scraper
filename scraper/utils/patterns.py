"""
Regular expression patterns for data extraction.
"""

import re

# ============================================================
# ADDRESS PATTERNS
# ============================================================

# US street address pattern
ADDRESS_STREET_PATTERN = re.compile(
    r'\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+'
    r'(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Court|Ct|Circle|Cir|Parkway|Pkwy|Place|Pl)',
    re.IGNORECASE
)

# State abbreviation (2 capital letters)
STATE_PATTERN = re.compile(r'\b[A-Z]{2}\b')

# ZIP code (5 digits or 5+4)
ZIP_PATTERN = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# Full address pattern (more comprehensive)
FULL_ADDRESS_PATTERN = re.compile(
    r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Court|Ct|Circle|Cir|Parkway|Pkwy|Place|Pl)'
    r'[,\s]+[A-Za-z\s]+[,\s]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)',
    re.IGNORECASE
)

# ============================================================
# PHONE NUMBER PATTERNS
# ============================================================

# Phone number extraction (per original_prompt.md specification)
PHONE_PATTERN = re.compile(r'\D*1?\D*(\d{3})\D*(\d{3})\D*(\d{4})\D*')

# Alternative phone patterns for validation
PHONE_STANDARD = re.compile(r'^\(\d{3}\)\s\d{3}-\d{4}$')  # (XXX) XXX-XXXX
PHONE_DIGITS_ONLY = re.compile(r'^\d{10}$')  # XXXXXXXXXX

# ============================================================
# HOURS PATTERNS
# ============================================================

# Time range pattern (e.g., "9:00 AM - 6:00 PM")
HOURS_RANGE_PATTERN = re.compile(
    r'(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)\s*[-–—]\s*(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)',
    re.IGNORECASE
)

# Alternative time pattern without minutes
HOURS_RANGE_SIMPLE = re.compile(
    r'(\d{1,2})\s*(AM|PM|am|pm)\s*[-–—]\s*(\d{1,2})\s*(AM|PM|am|pm)',
    re.IGNORECASE
)

# Day of week pattern
DAY_PATTERN = re.compile(
    r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b',
    re.IGNORECASE
)

# Day range pattern (e.g., "Mon-Fri", "Monday-Friday")
DAY_RANGE_PATTERN = re.compile(
    r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*[-–—]\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b',
    re.IGNORECASE
)

# Special hours patterns
HOURS_CLOSED = re.compile(r'\b(closed|by\s+appointment)\b', re.IGNORECASE)
HOURS_24_HOURS = re.compile(r'\b(24\s*hours?|open\s*24)\b', re.IGNORECASE)

# ============================================================
# URL PATTERNS
# ============================================================

# General URL pattern
URL_PATTERN = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

# Tracking parameters to remove
TRACKING_PARAMS = [
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'gclid', 'fbclid', 'mc_cid', 'mc_eid', '_ga', '_gl'
]

# Service scheduler URL patterns
SERVICE_URL_PATTERNS = [
    re.compile(r'/service[-_]?(?:appointment|scheduler?|booking)', re.IGNORECASE),
    re.compile(r'/schedule[-_]?service', re.IGNORECASE),
    re.compile(r'/book[-_]?(?:service|appointment)', re.IGNORECASE),
]

# Credit application URL patterns
CREDIT_URL_PATTERNS = [
    re.compile(r'/finance/apply', re.IGNORECASE),
    re.compile(r'/apply[-_]?(?:for[-_])?financing', re.IGNORECASE),
    re.compile(r'/credit[-_]?(?:app|application)', re.IGNORECASE),
    re.compile(r'/finance[-_]?application', re.IGNORECASE),
]

# Facebook URL pattern
FACEBOOK_URL_PATTERN = re.compile(
    r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+/?',
    re.IGNORECASE
)

# Google Maps URL pattern
GOOGLE_MAPS_PATTERN = re.compile(
    r'https?://(?:www\.)?(?:google\.com/maps|maps\.google\.com|goo\.gl/maps)',
    re.IGNORECASE
)

# ============================================================
# COUNTY PATTERNS
# ============================================================

# County name pattern
COUNTY_PATTERN = re.compile(
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(County|Parish|Borough)',
    re.IGNORECASE
)

# ============================================================
# PROVIDER DETECTION PATTERNS
# ============================================================

# Copyright/footer year
COPYRIGHT_YEAR = re.compile(r'©?\s*(?:Copyright\s+)?(\d{4})', re.IGNORECASE)

# Powered by / Website by
POWERED_BY_PATTERN = re.compile(
    r'(?:powered\s+by|website\s+by|designed\s+by|built\s+by)\s+([^<>\n]+)',
    re.IGNORECASE
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_day_name(day: str) -> str:
    """Normalize day abbreviations to full names."""
    day_map = {
        'mon': 'Monday',
        'tue': 'Tuesday',
        'wed': 'Wednesday',
        'thu': 'Thursday',
        'fri': 'Friday',
        'sat': 'Saturday',
        'sun': 'Sunday',
    }
    day_lower = day.lower().strip()
    return day_map.get(day_lower[:3], day.capitalize())


def is_valid_state(state: str) -> bool:
    """Check if a 2-letter state abbreviation is valid."""
    valid_states = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
    }
    return state.upper() in valid_states


def clean_whitespace(text: str) -> str:
    """Clean and normalize whitespace in text."""
    if not text:
        return ""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    return text.strip()
